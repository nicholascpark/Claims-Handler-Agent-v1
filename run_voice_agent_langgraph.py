"""LangGraph Voice Agent Demo

Graph-based supervisor workflow for a low-latency voice agent using:
- OpenAI Realtime API (via Azure endpoint) for full-duplex audio + ASR + TTS
- LangGraph for resilient, explicit state management of supervisor logic
- trustcall for robust JSON-patch style extraction on a nested claim schema

How this differs from src/voice_agent.py:
- Keeps the same realtime audio loop and tool-calling pattern for stability
- Replaces the supervisor decisioning with a LangGraph pipeline that:
  1) Updates structured claim data with trustcall
  2) Validates completeness
  3) Composes the next response message

Run:
  python run_voice_agent_langgraph.py

Requires Azure OpenAI Realtime credentials and audio device access.
Reads configuration from src/config/settings.py and honors LangSmith envs.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import ssl
import threading
from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime
import argparse

import numpy as np  # type: ignore
import sounddevice as sd  # type: ignore
import websockets  # type: ignore
from websockets.exceptions import ConnectionClosed  # type: ignore

from src.config.settings import settings, validate_required_settings
from src.prompts import AgentPrompts
from src.agents.trustcall_agent import create_trustcall_agent, TrustcallExtractionAgent

# LangGraph
from langgraph.graph import StateGraph, START, END  # type: ignore


class SupervisorState(TypedDict, total=False):
    """State for the supervisor LangGraph pipeline."""

    conversation_history: List[Dict[str, Any]]
    relevant_context: str
    latest_user_input: str
    claim_data: Dict[str, Any]
    is_complete: bool
    missing_fields: List[str]
    message: str
    error: str


class LangGraphSupervisor:
    """Supervisor implemented as a LangGraph pipeline with trustcall updates."""

    def __init__(self) -> None:
        self.trustcall_agent: TrustcallExtractionAgent = create_trustcall_agent()
        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(SupervisorState)

        async def extract_latest_user_input(state: SupervisorState) -> SupervisorState:
            history = state.get("conversation_history", [])
            latest_user = ""
            for msg in reversed(history):
                if msg.get("role") == "user" and msg.get("content"):
                    latest_user = str(msg.get("content"))
                    break
            state["latest_user_input"] = latest_user
            return state

        async def trustcall_update(state: SupervisorState) -> SupervisorState:
            try:
                latest = state.get("latest_user_input", "")
                existing = state.get("claim_data", {})
                context = state.get("relevant_context", "")
                result = await self.trustcall_agent.extract_and_patch_claim_data(
                    user_input=latest,
                    existing_data=existing,
                    conversation_context=context,
                )
                if result.extraction_successful:
                    state["claim_data"] = result.updated_data
                return state
            except Exception as e:  # Never fail the flow
                state["error"] = f"trustcall_update_failed: {e}"
                return state

        async def validate_and_decide(state: SupervisorState) -> SupervisorState:
            try:
                current = state.get("claim_data", {})
                validation = self.trustcall_agent.validate_extraction_completeness(current)
                state["is_complete"] = bool(validation.get("is_complete", False))
                state["missing_fields"] = list(validation.get("missing_fields", []))
                return state
            except Exception as e:
                state["is_complete"] = False
                state["missing_fields"] = ["validation_error"]
                state["error"] = f"validate_failed: {e}"
                return state

        async def compose_message(state: SupervisorState) -> SupervisorState:
            try:
                context_lower = state.get("relevant_context", "").lower()
                is_complete = bool(state.get("is_complete", False))

                if is_complete:
                    state["message"] = (
                        "Thank you for providing all that information. I have everything needed for your claim. "
                        "I'm submitting this now."
                    )
                    return state

                # Simple, empathetic prompting aligned with prompts.py style
                if "accident" in context_lower or "incident" in context_lower or "claim" in context_lower:
                    state["message"] = (
                        "I'm sorry to hear about your situation. I'll help you get this reported. "
                        "What's your full name and the best phone number to reach you?"
                    )
                    return state

                if "coverage" in context_lower or "deductible" in context_lower:
                    state["message"] = (
                        "I can help with coverage details once I have your claim information. "
                        "Let's start with what happened and your contact details."
                    )
                    return state

                state["message"] = (
                    "I'm here to help with your claim. Can you tell me more about what happened?"
                )
                return state
            except Exception as e:
                state["message"] = (
                    "I'm having some difficulty formulating the next step. Let's continue with what happened and your contact information."
                )
                state["error"] = f"compose_failed: {e}"
                return state

        graph.add_node("extract_latest_user_input", extract_latest_user_input)
        graph.add_node("trustcall_update", trustcall_update)
        graph.add_node("validate_and_decide", validate_and_decide)
        graph.add_node("compose_message", compose_message)

        graph.add_edge(START, "extract_latest_user_input")
        graph.add_edge("extract_latest_user_input", "trustcall_update")
        graph.add_edge("trustcall_update", "validate_and_decide")
        graph.add_edge("validate_and_decide", "compose_message")
        graph.add_edge("compose_message", END)

        return graph.compile()

    async def get_next_response(self, conversation_history: List[Dict[str, Any]], relevant_context: str, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        init: SupervisorState = {
            "conversation_history": conversation_history or [],
            "relevant_context": relevant_context or "",
            "claim_data": claim_data or {},
        }
        final_state: SupervisorState = await self._graph.ainvoke(init)
        return {
            "message": final_state.get("message", "I'm here to help with your claim."),
            "is_complete": bool(final_state.get("is_complete", False)),
            "claim_data": final_state.get("claim_data", {}),
            "missing_fields": final_state.get("missing_fields", []),
        }


class LangGraphVoiceAgent:
    """Realtime voice agent that delegates supervisor logic to LangGraphSupervisor."""

    def __init__(self) -> None:
        self.voice = settings.JUNIOR_AGENT_VOICE
        self.instructions = AgentPrompts.get_realtime_agent_instructions()
        self.supervisor = LangGraphSupervisor()

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._closing = False

        # Audio
        self.sample_rate = settings.SAMPLE_RATE
        self.channels = settings.AUDIO_CHANNELS
        self.dtype = "int16"
        self.chunk_size = settings.AUDIO_CHUNK_SIZE
        self._output_stream: Optional[sd.OutputStream] = None
        self._playback_lock = threading.Lock()
        self.playback_buffer = bytearray()
        self._ai_state = "listening"
        self._greeting_sent = False
        self._listening_logged = False
        self.selected_input_device: Optional[int] = None
        self.display_json_enabled: bool = (
            bool(getattr(settings, "DISPLAY_CLAIM_JSON", False))
            or os.getenv("DISPLAY_CLAIM_JSON", "").lower() == "true"
        )
        self.display_interval: float = float(os.getenv("DISPLAY_JSON_INTERVAL", "1.0") or 1.0)
        self._json_task: Optional[asyncio.Task] = None

        # Conversation and claim state
        self.conversation_history: List[Dict[str, Any]] = []
        self.current_claim_data: Dict[str, Any] = {}
        self._last_claim_print: Optional[str] = None

    def select_microphone_device(self) -> bool:
        """Minimal microphone selector: list input devices and allow choosing or default."""
        try:
            devices = sd.query_devices()
            input_devices = []
            for i, device in enumerate(devices):
                if device.get('max_input_channels', 0) > 0:
                    input_devices.append((i, device))
            if not input_devices:
                print("❌ No input-capable microphones found. Falling back to system default.")
                self.selected_input_device = None
                return True

            # Determine default input index from sounddevice
            try:
                default_in = sd.default.device[0]
            except Exception:
                default_in = None

            print("\n🎤 Select microphone (press Enter for default):")
            for idx, (device_id, device) in enumerate(input_devices, 1):
                name = device.get('name', f'Device {device_id}')
                default_marker = " [DEFAULT]" if default_in is not None and device_id == default_in else ""
                print(f"   {idx}: {name}{default_marker}")

            while True:
                try:
                    choice = input("🎯 Choice: ").strip()
                    if choice == "":
                        self.selected_input_device = None
                        if default_in is not None:
                            print("✅ Using default microphone")
                        else:
                            print("✅ Using system default microphone")
                        return True
                    num = int(choice)
                    if 1 <= num <= len(input_devices):
                        device_id, device = input_devices[num - 1]
                        # Quick validation: attempt to open/close a tiny stream
                        try:
                            with sd.InputStream(
                                device=device_id,
                                channels=self.channels,
                                samplerate=self.sample_rate,
                                dtype=self.dtype,
                                blocksize=256,
                            ):
                                pass
                            self.selected_input_device = device_id
                            print(f"✅ Selected microphone: {device.get('name','(unknown)')}")
                            return True
                        except Exception:
                            print("⚠️  Could not access that device. Please choose another.")
                    else:
                        print(f"❌ Please enter a number between 1 and {len(input_devices)}")
                except ValueError:
                    print("❌ Please enter a valid number or press Enter for default")
                except KeyboardInterrupt:
                    print("\n❌ Selection cancelled")
                    return False
        except Exception as e:
            print(f"❌ Microphone selection error: {e}")
            return False

    def _get_timestamp(self) -> str:
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

    def _get_supervisor_tool_def(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "name": "getNextResponseFromSupervisor",
            "description": "Determines the next response whenever the agent faces a non-trivial decision, produced by a highly intelligent supervisor agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relevantContextFromLastUserMessage": {
                        "type": "string",
                        "description": "Key information from the user described in their most recent message."
                    }
                },
                "required": ["relevantContextFromLastUserMessage"],
                "additionalProperties": False
            }
        }

    def _get_session_config(self) -> Dict[str, Any]:
        return {
            "modalities": ["text", "audio"],
            "instructions": self.instructions,
            "voice": self.voice,
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": settings.TRANSCRIPTION_MODEL,
                "language": settings.TRANSCRIPTION_LANGUAGE,
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": settings.VAD_THRESHOLD,
                "prefix_padding_ms": settings.VAD_PREFIX_PADDING_MS,
                "silence_duration_ms": settings.VAD_SILENCE_DURATION_MS,
            },
            "tools": [self._get_supervisor_tool_def()],
            "tool_choice": "auto",
        }

    async def _send(self, event: Dict[str, Any]) -> None:
        if self.ws:
            await self.ws.send(json.dumps(event))

    async def _session_update(self) -> None:
        await self._send({
            "type": "session.update",
            "session": self._get_session_config(),
        })

    def _output_callback(self, outdata, frames, time_info, status):
        try:
            outdata[:] = 0
            bytes_needed = frames * self.channels * 2
            with self._playback_lock:
                to_copy = min(bytes_needed, len(self.playback_buffer))
                if to_copy > 0:
                    chunk = bytes(self.playback_buffer[:to_copy])
                    del self.playback_buffer[:to_copy]
                else:
                    chunk = b""
            if chunk:
                total_samples = frames * self.channels
                out_arr = np.zeros(total_samples, dtype=np.int16)
                chunk_arr = np.frombuffer(chunk, dtype=np.int16)
                max_samples = min(total_samples, chunk_arr.size)
                out_arr[:max_samples] = chunk_arr[:max_samples]
                outdata[:] = out_arr.reshape(frames, self.channels)
        except Exception:
            pass

    def _open_output_stream(self) -> None:
        try:
            if self._output_stream is None:
                self._output_stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=self.dtype,
                    blocksize=self.chunk_size,
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
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype=self.dtype,
                blocksize=self.chunk_size,
            ) as stream:
                while not self._closing:
                    data, _ = stream.read(self.chunk_size)
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

    def _append_conversation(self, role: str, content: str) -> None:
        if not content:
            return
        self.conversation_history.append({"type": "message", "role": role, "content": content})

    async def _handle_function_call(self, function_call: Dict[str, Any]) -> None:
        name = (function_call or {}).get("name")
        if name != "getNextResponseFromSupervisor":
            return
        args_str = (function_call or {}).get("arguments", "{}")
        try:
            args = json.loads(args_str)
        except Exception:
            args = {}
        relevant = args.get("relevantContextFromLastUserMessage", "")

        result = await self.supervisor.get_next_response(
            conversation_history=[
                {"role": m.get("role", "user"), "content": m.get("content", "")}
                for m in self.conversation_history if m.get("type") == "message"
            ],
            relevant_context=relevant,
            claim_data=self.current_claim_data,
        )

        # Update claim data and print diffs if enabled
        previous_data = json.loads(json.dumps(self.current_claim_data))
        self.current_claim_data = result.get("claim_data", self.current_claim_data)
        if self.display_json_enabled:
            self._print_field_updates(previous_data, self.current_claim_data)
            # Prevent duplicate prints by aligning last-print snapshot
            self._last_claim_print = json.dumps(self.current_claim_data, sort_keys=True, ensure_ascii=False)

        # Create tool output for the Realtime API
        call_id = (function_call or {}).get("id", "")
        tool_output_event = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": result.get("message", "I'm here to help with your claim. How can I assist you?"),
            },
        }
        await self._send(tool_output_event)

        # Trigger the assistant to speak the tool output message
        await self._send({"type": "response.create"})

        # Record assistant message in history
        self._append_conversation("assistant", result.get("message", ""))

    async def _event_loop(self) -> None:
        while not self._closing and self.ws:
            try:
                raw = await self.ws.recv()
                event = json.loads(raw)
                etype = event.get("type", "")

                if etype == "session.created":
                    await self._session_update()

                elif etype == "session.updated":
                    if not self._greeting_sent:
                        try:
                            await self._send({
                                "type": "response.create",
                                "response": {
                                    "instructions": self.instructions + "\n\nIMPORTANT: Start this conversation with the company greeting immediately.",
                                    "tool_choice": "auto",
                                },
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
                        print(f"[{self._get_timestamp()}] 🗣️ AI speaking…")

                elif etype == "response.completed":
                    self._ai_state = "listening"
                    print(f"[{self._get_timestamp()}] 🎙️ AI listening…")

                elif etype == "response.content_part.done":
                    part = event.get("part", {})
                    if part.get("type") == "audio" and part.get("transcript"):
                        transcript = part["transcript"].strip()
                        if transcript:
                            print(f"[{self._get_timestamp()}] 🤖 AI: {transcript}")
                            self._append_conversation("assistant", transcript)

                elif etype == "response.function_call.done":
                    await self._handle_function_call(event.get("function_call", {}))

                elif etype == "conversation.item.input_audio_transcription.delta":
                    # Partial user text; we keep UI quiet here for smoothness
                    pass

                elif etype == "conversation.item.input_audio_transcription.completed":
                    text = (event.get("transcript", {}) or event.get("text", "") or "").strip()
                    if text:
                        print(f"[{self._get_timestamp()}] 👤 User: {text}")
                        self._append_conversation("user", text)
                        # Kick off background trustcall update so JSON and diffs reflect progress
                        try:
                            asyncio.create_task(self._apply_trustcall_from_user_text(text))
                        except Exception:
                            pass

                elif etype == "input_audio_buffer.speech_stopped":
                    try:
                        await self._send({"type": "input_audio_buffer.commit"})
                        await self._send({
                            "type": "response.create",
                            "response": {
                                "instructions": self.instructions,
                                "tool_choice": {"type": "function", "name": "getNextResponseFromSupervisor"},
                            },
                        })
                    except Exception:
                        pass

                # Optional periodic display handled in background loop

            except ConnectionClosed:
                break
            except Exception:
                continue

    def _maybe_print_claim_json(self) -> None:
        try:
            if not self.display_json_enabled:
                return
            blob = json.dumps(self.current_claim_data, sort_keys=True, ensure_ascii=False)
            if blob != self._last_claim_print:
                print("🧾 Current Claim JSON:")
                print(json.dumps(self.current_claim_data, indent=2, ensure_ascii=False))
                self._last_claim_print = blob
        except Exception:
            pass

    def _print_field_updates(self, before: Dict[str, Any], after: Dict[str, Any]) -> None:
        try:
            def flatten(prefix: str, obj: Any, out: Dict[str, Any]) -> None:
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        path = f"{prefix}.{k}" if prefix else k
                        flatten(path, v, out)
                elif isinstance(obj, list):
                    out[prefix] = obj
                else:
                    out[prefix] = obj

            fb: Dict[str, Any] = {}
            fa: Dict[str, Any] = {}
            flatten("", before or {}, fb)
            flatten("", after or {}, fa)

            changes: List[str] = []
            keys = set(fb.keys()) | set(fa.keys())
            for k in sorted(keys):
                vb = fb.get(k, None)
                va = fa.get(k, None)
                if vb != va:
                    if vb is None:
                        changes.append(f"➕ {k}: {va}")
                    elif va is None:
                        changes.append(f"➖ {k}: {vb} -> (removed)")
                    else:
                        changes.append(f"✏️  {k}: {vb} -> {va}")

            if changes:
                print("🔄 Field updates:")
                for line in changes:
                    print(f"   {line}")
                print("🧾 Updated Claim JSON:")
                print(json.dumps(after or {}, indent=2, ensure_ascii=False))
        except Exception:
            pass

    async def _json_display_loop(self) -> None:
        try:
            while not self._closing:
                if not self.display_json_enabled:
                    await asyncio.sleep(0.5)
                    continue
                try:
                    blob = json.dumps(self.current_claim_data, sort_keys=True, ensure_ascii=False)
                    if blob != self._last_claim_print:
                        is_complete = False
                        missing_count = 0
                        try:
                            validation = self.supervisor.trustcall_agent.validate_extraction_completeness(self.current_claim_data)
                            is_complete = bool(validation.get("is_complete", False))
                            missing_count = len(validation.get("missing_fields", []))
                        except Exception:
                            pass
                        print("🧾 Current Claim JSON:")
                        print(json.dumps(self.current_claim_data, indent=2, ensure_ascii=False))
                        print(f"📊 Complete: {is_complete} | Missing fields: {missing_count}")
                        self._last_claim_print = blob
                except Exception:
                    pass
                await asyncio.sleep(max(0.2, float(self.display_interval)))
        except asyncio.CancelledError:
            return

    async def start(self) -> None:
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
            if self.display_json_enabled:
                self._json_task = asyncio.create_task(self._json_display_loop())
            try:
                await events
            finally:
                self._closing = True
                self._close_output_stream()
                for t in (mic, events, self._json_task):
                    if t and not t.done():
                        t.cancel()


def _wire_langsmith_envs() -> None:
    try:
        if settings.LANGSMITH_PROJECT:
            os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
        if settings.LANGSMITH_ENDPOINT:
            os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
        if settings.LANGCHAIN_TRACING:
            os.environ["LANGCHAIN_TRACING"] = settings.LANGCHAIN_TRACING
        if settings.LANGSMITH_API_KEY:
            os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    except Exception:
        pass


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--display-json", action="store_true", help="Periodically print claim JSON on change")
    parser.add_argument("--display-interval", type=float, default=None, help="Seconds between JSON checks (default 1.0)")
    args = parser.parse_args()

    validate_required_settings()
    _wire_langsmith_envs()
    agent = LangGraphVoiceAgent()
    if args.display_json:
        agent.display_json_enabled = True
    if args.display_interval:
        agent.display_interval = float(args.display_interval)

    # Minimal microphone selection prompt
    if not agent.select_microphone_device():
        return

    await agent.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


