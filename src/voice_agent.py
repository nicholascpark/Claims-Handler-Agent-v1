"""Low-latency Voice Agent with Parallel JSON Processing

This implementation prioritizes uninterrupted, low-latency voice conversation
while decoupling JSON extraction/patching. The junior realtime agent handles
voice I/O and tool calls; the supervisor runs background trustcall extraction
in parallel based on transcript updates.

Public APIs preserved:
- create_voice_agent() -> ClaimsVoiceAgent
- async def main()
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import ssl
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional
import hashlib
from datetime import datetime

try:
    import numpy as np
    import sounddevice as sd
    import websockets
    from websockets.exceptions import ConnectionClosed
except Exception as e:
    raise

from src.agents.realtime_agent import create_claims_realtime_agent
from src.agents.supervisor_agent import create_supervisor_agent
from src.tools.supervisor_tool import get_supervisor_tool_handler, create_realtime_tool_response
from src.config.settings import settings, validate_required_settings


@dataclass
class AudioConfig:
    sample_rate: int = settings.SAMPLE_RATE
    channels: int = settings.AUDIO_CHANNELS
    dtype: str = "int16"
    chunk_size: int = settings.AUDIO_CHUNK_SIZE
    # Amount of audio to accumulate before starting playback of each assistant turn (ms)
    playback_prebuffer_ms: int = 200


class ClaimsVoiceAgent:
    def __init__(self) -> None:
        self.junior = create_claims_realtime_agent()
        self.supervisor = create_supervisor_agent()
        self.audio = AudioConfig()

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.playback_buffer = bytearray()
        self._closing = False

        # Mic selection support
        self.selected_input_device: Optional[int] = None
        self._greeting_sent = False
        self._listening_logged = False

        # Persistent output stream and lock for smooth playbook
        self._output_stream: Optional[sd.OutputStream] = None
        self._playback_lock = threading.Lock()
        self._prebuffering: bool = False
        # Bytes of audio required before we begin playback for a new assistant turn
        self._prebuffer_bytes: int = int(
            (self.audio.sample_rate * self.audio.channels * 2)
            * (self.audio.playback_prebuffer_ms / 1000.0)
        )

        # Live logging buffers and state
        self._user_partial: str = ""
        self._ai_state: str = "listening"  # or "speaking"

        # JSON display change detection
        self._last_claim_hash: Optional[str] = None
        self._last_pending: Optional[int] = None

    def _get_timestamp(self) -> str:
        """Get current timestamp for logging"""
        return datetime.now().strftime('%H:%M:%S')

    def _build_ws_url(self) -> str:
        endpoint = (settings.AZURE_OPENAI_ENDPOINT or "").rstrip("/")
        api_version = settings.AZURE_OPENAI_REALTIME_API_VERSION
        deployment = settings.AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME
        base_https = f"{endpoint}/openai/realtime?api-version={api_version}&deployment={deployment}"
        return base_https.replace("https://", "wss://").replace("http://", "ws://")

    def _ssl_context(self) -> Optional[ssl.SSLContext]:
        if os.getenv("OPENAI_DISABLE_SSL_VERIFY", "").lower() == "true":
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx
        return None

    async def _send(self, event: Dict[str, Any]) -> None:
        if not self.ws:
            return
        await self.ws.send(json.dumps(event))

    async def _session_update(self) -> None:
        await self._send({
            "type": "session.update",
            "session": self.junior.get_session_config(),
        })

    def select_microphone_device(self) -> bool:
        try:
            devices = sd.query_devices()
            input_devices = []
            for i, device in enumerate(devices):
                if device.get('max_input_channels', 0) > 0:
                    input_devices.append((i, device))
            if not input_devices:
                print("❌ No input devices found!")
                return False

            print("\n🎤 MICROPHONE DEVICE SELECTION")
            print("=" * 50)
            print("Available microphone devices:\n")
            try:
                default_in = sd.default.device[0]
            except Exception:
                default_in = None

            for idx, (device_id, device) in enumerate(input_devices):
                default_marker = " [DEFAULT]" if default_in is not None and device_id == default_in else ""
                print(f"   {idx + 1}: {device['name']}{default_marker}")
                print(f"      Device ID: {device_id}")
                print(f"      Max Input Channels: {device['max_input_channels']}")
                print(f"      Default Sample Rate: {device.get('default_samplerate', 'n/a')}")
                print()

            while True:
                try:
                    print("Select microphone device (Enter number or press Enter for default):")
                    choice = input("🎯 Choice: ").strip()
                    if choice == "":
                        self.selected_input_device = None
                        if default_in is not None:
                            print("✅ Using default microphone")
                        else:
                            print("✅ Using system default microphone")
                        break
                    num = int(choice)
                    if 1 <= num <= len(input_devices):
                        device_id, device = input_devices[num - 1]
                        if self._test_microphone_device(device_id):
                            self.selected_input_device = device_id
                            print(f"✅ Selected microphone: {device['name']}")
                            break
                        else:
                            print("⚠️  Device test failed. Please choose another device.")
                    else:
                        print(f"❌ Please enter a number between 1 and {len(input_devices)}")
                except ValueError:
                    print("❌ Please enter a valid number")
                except KeyboardInterrupt:
                    print("\n❌ Device selection cancelled")
                    return False

            print("-" * 50)
            return True
        except Exception as e:
            print(f"❌ Device selection error: {e}")
            return False

    def _test_microphone_device(self, device_id: int) -> bool:
        try:
            with sd.InputStream(
                device=device_id,
                channels=1,
                samplerate=self.audio.sample_rate,
                dtype='float32',
                blocksize=256,
            ) as stream:
                data, _ = stream.read(256)
                return data is not None and len(data) > 0
        except Exception:
            return False

    def _output_callback(self, outdata, frames, time_info, status):
        try:
            outdata[:] = 0
            bytes_needed = frames * self.audio.channels * 2
            with self._playback_lock:
                # If we are prebuffering a new assistant turn, wait until we have
                # enough audio to avoid an early underflow that causes a perceptible pause
                if self._prebuffering and len(self.playback_buffer) < self._prebuffer_bytes:
                    return
                elif self._prebuffering and len(self.playback_buffer) >= self._prebuffer_bytes:
                    self._prebuffering = False
                if len(self.playback_buffer) > 0:
                    to_copy = min(bytes_needed, len(self.playback_buffer))
                    chunk = bytes(self.playback_buffer[:to_copy])
                    del self.playback_buffer[:to_copy]
                else:
                    chunk = b""
            if chunk:
                total_samples = frames * self.audio.channels
                out_arr = np.zeros(total_samples, dtype=np.int16)
                chunk_arr = np.frombuffer(chunk, dtype=np.int16)
                max_samples = min(total_samples, chunk_arr.size)
                out_arr[:max_samples] = chunk_arr[:max_samples]
                outdata[:] = out_arr.reshape(frames, self.audio.channels)
        except Exception:
            pass

    def _open_output_stream(self) -> None:
        try:
            if self._output_stream is None:
                self._output_stream = sd.OutputStream(
                    samplerate=self.audio.sample_rate,
                    channels=self.audio.channels,
                    dtype=self.audio.dtype,
                    blocksize=self.audio.chunk_size,
                    callback=self._output_callback,
                )
                self._output_stream.start()
        except Exception:
            self._output_stream = None

    def _close_output_stream(self) -> None:
        try:
            if self._output_stream is not None:
                try:
                    self._output_stream.stop()
                finally:
                    self._output_stream.close()
        except Exception:
            pass
        finally:
            self._output_stream = None

    async def _mic_stream_loop(self) -> None:
        try:
            with sd.InputStream(
                device=self.selected_input_device,
                channels=self.audio.channels,
                samplerate=self.audio.sample_rate,
                dtype=self.audio.dtype,
                blocksize=self.audio.chunk_size,
            ) as stream:
                while not self._closing:
                    data, _ = stream.read(self.audio.chunk_size)
                    if data is None:
                        await asyncio.sleep(0.005)
                        continue
                    b = data.tobytes()
                    if not b:
                        continue
                    await self._send({
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(b).decode("ascii"),
                    })
        except Exception:
            pass

    async def _event_loop(self) -> None:
        tool_handler = get_supervisor_tool_handler()
        while not self._closing and self.ws:
            try:
                raw = await self.ws.recv()
                event = json.loads(raw)
                etype = event.get("type", "")

                if etype == "session.created":
                    # Session will be updated once; avoid duplicate updates that double-log listening
                    await self._session_update()

                elif etype == "session.updated":
                    if not self._greeting_sent:
                        try:
                            # Force initial greeting by creating a response with greeting instruction
                            await self._send({
                                "type": "response.create",
                                "response": {
                                    "instructions": self.junior.instructions + "\n\nIMPORTANT: Start this conversation with the company greeting immediately.",
                                    "tool_choice": "auto"
                                }
                            })
                            self._greeting_sent = True
                        except Exception:
                            pass
                    if not self._listening_logged:
                        self._ai_state = "listening"
                        print(f"[{self._get_timestamp()}] 🎙️ AI listening…")
                        self._listening_logged = True

                elif etype == "response.audio.delta":
                    b64 = event.get("delta", "") or event.get("audio", "")
                    if b64:
                        try:
                            data = base64.b64decode(b64)
                            with self._playback_lock:
                                self.playback_buffer.extend(data)
                        except Exception:
                            pass
                    if self._ai_state != "speaking":
                        self._ai_state = "speaking"
                        # Start prebuffering at the moment we begin an assistant turn
                        with self._playback_lock:
                            self._prebuffering = True
                        print(f"[{self._get_timestamp()}] 🗣️ AI speaking…")

                # Omit handling of response.created to avoid premature 'speaking' logs for tool-only turns

                elif etype == "response.completed":
                    self._ai_state = "listening"
                    # Prepare to prebuffer the start of the next assistant turn
                    with self._playback_lock:
                        self._prebuffering = True
                    print(f"[{self._get_timestamp()}] 🎙️ AI listening…")

                elif etype == "response.content_part.done":
                    # Extract AI transcript from completed content part
                    part = event.get("part", {})
                    if part.get("type") == "audio" and part.get("transcript"):
                        transcript = part["transcript"].strip()
                        if transcript:
                            print(f"[{self._get_timestamp()}] 🤖 AI: {transcript}")

                elif etype == "response.function_call.done":
                    fn = (event.get("function_call", {}) or {}).get("name")
                    if fn == "getNextResponseFromSupervisor":
                        ctx = {"history": self.junior.get_conversation_history_for_supervisor()}
                        result = await tool_handler.handle_tool_call(event.get("function_call", {}), ctx)
                        tool_resp = create_realtime_tool_response(
                            (event.get("function_call", {}) or {}).get("id", ""),
                            result,
                        )
                        await self._send(tool_resp)
                        await self._send({"type": "response.create"})

                elif etype == "conversation.item.input_audio_transcription.completed":
                    text = (event.get("transcript", {}) or event.get("text", "") or "").strip()
                    if text:
                        print(f"[{self._get_timestamp()}] 👤 User: {text}")
                        # Update junior history so supervisor tool has full context
                        _ = self.junior.process_user_message(text)

                elif etype == "conversation.item.input_audio_transcription.delta":
                    delta = event.get("delta", "") or event.get("text", "")
                    if isinstance(delta, str) and delta:
                        self._user_partial += delta

                elif etype == "input_audio_buffer.speech_stopped":
                    try:
                        await self._send({"type": "input_audio_buffer.commit"})
                        # Trigger a single model response for this user turn
                        await self._send({
                            "type": "response.create",
                            "response": {
                                "instructions": self.junior.instructions,
                                "tool_choice": {"type": "function", "name": "getNextResponseFromSupervisor"}
                            }
                        })
                    except Exception:
                        pass
                    self._user_partial = ""

                elif etype == "input_audio_buffer.speech_started":
                    print(f"[{self._get_timestamp()}] 🎙️ Listening… (capturing speech)")

            except ConnectionClosed:
                break
            except Exception:
                continue

    async def start_voice_conversation(self) -> None:
        url = self._build_ws_url()
        headers = [("api-key", settings.AZURE_OPENAI_API_KEY or ""), ("OpenAI-Beta", "realtime=v1")]
        async with websockets.connect(
            url,
            additional_headers=headers,
            subprotocols=["realtime"],
            ssl=self._ssl_context(),
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
            max_size=10_000_000,
        ) as ws:
            self.ws = ws
            await self._session_update()
            self._open_output_stream()
            mic = asyncio.create_task(self._mic_stream_loop())
            events = asyncio.create_task(self._event_loop())
            json_display = asyncio.create_task(self._json_display_loop())
            try:
                await events
            finally:
                self._closing = True
                self._close_output_stream()
                for t in (mic, events, json_display):
                    if not t.done():
                        t.cancel()

    def _should_show_json(self) -> bool:
        try:
            return bool(getattr(settings, "DISPLAY_CLAIM_JSON", False)) or os.getenv("DISPLAY_CLAIM_JSON", "").lower() == "true"
        except Exception:
            return False

    async def _json_display_loop(self) -> None:
        try:
            while not self._closing:
                if not self._should_show_json():
                    await asyncio.sleep(1.0)
                    continue
                try:
                    status = self.supervisor.get_current_payload_status()
                    claim = status.get("claim_data", {})
                    pending = status.get("pending_inputs", 0)
                    blob = json.dumps(claim, sort_keys=True, ensure_ascii=False)
                    claim_hash = hashlib.sha256(blob.encode("utf-8")).hexdigest()
                    changed = (claim_hash != self._last_claim_hash) or (pending != self._last_pending)
                    if changed:
                        print("🧾 Current Claim JSON:")
                        print(json.dumps(claim, indent=2, ensure_ascii=False))
                        print(f"📊 Status: {status.get('processing_status')} | Pending: {pending}")
                        self._last_claim_hash = claim_hash
                        self._last_pending = pending
                except Exception:
                    pass
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            return


def create_voice_agent() -> ClaimsVoiceAgent:
    return ClaimsVoiceAgent()


async def main() -> None:
    validate_required_settings()
    agent = create_voice_agent()
    if not agent.select_microphone_device():
        return
    await agent.start_voice_conversation()


