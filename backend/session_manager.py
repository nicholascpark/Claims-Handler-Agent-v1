"""Session Manager for Voice Agent

Manages individual user sessions, integrating the voice_langgraph agent
with WebSocket communication to the frontend.

This implementation mirrors the orchestration used by the CLI agent in
`voice_langgraph/voice_agent.py` to ensure consistent behavior between
`python run_langgraph_agent.py` and the web frontend. Key aspects:
- Local VAD with manual `input_audio_buffer.commit` (server VAD disabled)
- LangGraph-driven greeting turn
- Realtime as pure talker: speak verbatim using `response.create` with
  `conversation: none` and explicit instructions
- Response tracking to cancel unexpected server-initiated responses
"""

import asyncio
import base64
import json
import logging
from typing import Dict, Optional
from datetime import datetime
from uuid import uuid4
from time import monotonic

from fastapi import WebSocket
import sys
import os
import numpy as np

# Add parent directory to path to import voice_langgraph
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from voice_langgraph.graph_builder import default_graph
from voice_langgraph.state import VoiceAgentState
from voice_langgraph.schema import PropertyClaim
from voice_langgraph.settings import voice_settings, validate_voice_settings
from voice_langgraph.utils import (
    WebSocketManager as RealtimeWSManager,
    AudioPlayback,
    encode_audio,
    decode_audio,
    get_timestamp
)
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

logger = logging.getLogger(__name__)


class VoiceSession:
    """Manages a single voice agent session."""
    
    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket
        self.is_active = False
        
        # Voice agent state
        self.conversation_history = []
        self.current_claim_data = PropertyClaim.create_empty().model_dump()
        self.is_claim_complete = False
        self.current_timezone = "America/Toronto"
        
        # Realtime API connection
        self.realtime_ws: Optional[RealtimeWSManager] = None
        self.audio_playback: Optional[AudioPlayback] = None
        
        # Vision-capable chat model (for image captioning to feed LangGraph)
        self._vision_llm = AzureChatOpenAI(
            azure_deployment=voice_settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
            azure_endpoint=voice_settings.AZURE_OPENAI_ENDPOINT,
            api_key=voice_settings.AZURE_OPENAI_API_KEY,
            api_version=voice_settings.AZURE_OPENAI_CHAT_API_VERSION,
            temperature=0.0,
        )
        
        # Control flags
        self._greeting_sent = False
        self._response_in_progress = False  # Prevent overlapping response.create
        self._accept_audio_streaming = True  # Gate incoming mic chunks

        # Turn management
        self._turn_locked = False
        self._turn_source: Optional[str] = None  # 'audio' | 'text'
        self._awaiting_transcript = False

        # Response tracking
        self._current_response_id: Optional[str] = None
        self._unexpected_response_ids = set()
        self._resp_delta_counter = 0
        self._resp_total_bytes = 0
        self._resp_started_at = 0.0
        self._resp_first_delta_at = 0.0
        self._resp_last_delta_at = 0.0

        # Server-side TTS pacing (prevent overspeed to browser)
        self._tts_buffer = bytearray()
        self._tts_lock = asyncio.Lock()
        self._tts_task: Optional[asyncio.Task] = None
        self._tts_send_interval_s = 0.02  # scheduler tick ~20ms, dynamic send size
        self._bytes_per_second = 24000 * 2  # 24kHz mono int16
        self._tts_chunk_bytes = int(self._bytes_per_second * 0.05)  # nominal 50ms
        self._tts_prebuffer_bytes = int(self._bytes_per_second * 0.40)  # ~400ms
        self._tts_max_send_bytes = int(self._bytes_per_second * 0.12)  # cap per tick ~120ms
        self._tts_playback_started = False
        self._tts_streaming_active = False
        self._tts_drain_after_response = False
        self._tts_stream_rid: Optional[str] = None
        self._tts_last_send_ts = 0.0
        # Allow large per-response buffer to avoid frame dropping (cap ~16MB)
        self._tts_max_buffer_bytes = 16 * 1024 * 1024

        # Local VAD state (RMS-based)
        self._vad_rms_threshold = 0.02  # normalized RMS as in CLI agent
        self._vad_silence_duration_sec = voice_settings.VAD_SILENCE_DURATION_MS / 1000.0
        self._vad_min_speech_sec = 0.20
        self._vad_speech_active = False
        self._vad_speech_start_ts = 0.0
        self._vad_last_speech_ts = 0.0
        self._last_pause_log_ts = 0.0

        # Server-side paced audio streaming to frontend to avoid blending/underruns
        self._audio_buffer = bytearray()
        self._audio_buffer_lock = asyncio.Lock()
        self._audio_stream_task: Optional[asyncio.Task] = None
        # Match CLI playback cadence and buffering more closely
        # ~1024 frames @ 24kHz ≈ 42.67ms
        self._pace_interval_s = 1024 / 24000.0
        # Prebuffer ~600ms as in CLI AudioPlayback
        self._min_prebuffer_s = 0.60
        # Cap jitter buffer to ~2.0s as in CLI
        self._max_buffer_s = 2.0
        self._bytes_per_second = 24000 * 1 * 2  # 24kHz, mono, int16
        self._min_prebuffer_bytes = int(self._bytes_per_second * self._min_prebuffer_s)
        self._max_buffer_bytes = int(self._bytes_per_second * self._max_buffer_s)
        self._playback_started = False
        self._drain_after_response = False
        
    async def start(self):
        """Start the voice session."""
        try:
            # Initialize Realtime API connection
            ws_url = self._build_ws_url()
            self.realtime_ws = RealtimeWSManager(ws_url, voice_settings.AZURE_OPENAI_API_KEY)
            
            # Connect to Realtime API
            await self.realtime_ws.connect()
            logger.info(f"[{self.session_id}] Connected to Realtime API")
            
            # Initialize audio playback (for console testing, not used in web)
            # Web frontend handles its own audio playback via worklets
            
            self.is_active = True
            
            # Start event handling loop
            asyncio.create_task(self._realtime_event_loop())
            # Start TTS pacing loop
            self._start_tts_streamer()
            
            logger.info(f"[{self.session_id}] Voice session started")
            
        except Exception as e:
            logger.error(f"[{self.session_id}] Failed to start session: {e}", exc_info=True)
            await self.websocket.send_json({
                "type": "error",
                "data": {"message": f"Failed to start session: {str(e)}"}
            })
            raise
    
    async def stop(self):
        """Stop the voice session."""
        self.is_active = False
        
        if self.realtime_ws:
            await self.realtime_ws.close()
            self.realtime_ws = None
        # Stop TTS pacing loop
        await self._stop_tts_streamer()
        
        logger.info(f"[{self.session_id}] Voice session stopped")
    
    def _build_ws_url(self) -> str:
        """Build WebSocket URL for Azure OpenAI Realtime API."""
        endpoint = voice_settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        api_version = voice_settings.AZURE_OPENAI_REALTIME_API_VERSION
        deployment = voice_settings.AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME
        
        https_url = f"{endpoint}/openai/realtime?api-version={api_version}&deployment={deployment}"
        return https_url.replace("https://", "wss://").replace("http://", "ws://")
    
    def _get_session_config(self) -> Dict:
        """Get Realtime API session configuration."""
        from voice_langgraph.prompts import Prompts
        
        return {
            "modalities": ["text", "audio"],
            "instructions": Prompts.get_supervisor_system_prompt(),
            "voice": voice_settings.JUNIOR_AGENT_VOICE,
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            # Disable server-side turn detection. We do local VAD + manual commit.
            "turn_detection": {"type": "none"},
            "input_audio_transcription": {
                "language": voice_settings.TRANSCRIPTION_LANGUAGE,
                "model": voice_settings.TRANSCRIPTION_MODEL,
            },
            # Disable server VAD to avoid unintended model-initiated responses
            # We orchestrate turns via LangGraph and explicit events
        }
    
    def _extract_response_id(self, event: Dict) -> Optional[str]:
        """Best-effort extraction of response id from a Realtime event."""
        try:
            rid = (
                event.get("response", {}).get("id")
                or event.get("response_id")
                or event.get("item", {}).get("response_id")
                or event.get("id")
            )
            if isinstance(rid, str) and rid.strip():
                return rid
        except Exception:
            pass
        return None

    def _lock_turn(self, source: str, pause_mic: bool = True):
        """Lock the conversation turn to the specified source ('audio' or 'text')."""
        if not self._turn_locked:
            self._turn_locked = True
            self._turn_source = source
            if pause_mic:
                self._accept_audio_streaming = False
            try:
                logger.debug(f"[{self.session_id}] 🔒 Turn locked by {source} (pause_mic={pause_mic})")
            except Exception:
                pass

    def _unlock_turn(self):
        """Unlock the conversation turn and resume mic acceptance."""
        if self._turn_locked:
            self._turn_locked = False
            self._turn_source = None
        self._accept_audio_streaming = True
        try:
            logger.debug(f"[{self.session_id}] 🔓 Turn unlocked; mic accept={self._accept_audio_streaming}")
        except Exception:
            pass

    def _start_tts_streamer(self):
        """Start background loop to pace TTS audio to frontend."""
        if self._tts_task is None or self._tts_task.done():
            self._tts_task = asyncio.create_task(self._tts_flush_loop())

    async def _stop_tts_streamer(self):
        """Stop background TTS pacing loop."""
        if self._tts_task and not self._tts_task.done():
            self._tts_task.cancel()
            try:
                await self._tts_task
            except Exception:
                pass
        self._tts_task = None

    async def _enqueue_tts_audio(self, audio_b64: str):
        """Decode a TTS delta and append to pacing buffer (no immediate send)."""
        try:
            audio_bytes = base64.b64decode(audio_b64)
        except Exception:
            return
        async with self._tts_lock:
            # Append and cap to prevent runaway memory growth
            self._tts_buffer.extend(audio_bytes)
            if len(self._tts_buffer) > self._tts_max_buffer_bytes:
                # Keep latest tail; drop oldest (rare)
                drop = len(self._tts_buffer) - self._tts_max_buffer_bytes
                del self._tts_buffer[:drop]

    async def _tts_flush_loop(self):
        """Periodically flush paced chunks to the frontend to keep overspeed ≈ 1.0x."""
        try:
            while True:
                await asyncio.sleep(self._tts_send_interval_s)
                send_chunk = None
                should_finalize = False
                async with self._tts_lock:
                    if not self._tts_streaming_active:
                        continue
                    # Start playback after prebuffer is filled
                    if not self._tts_playback_started and len(self._tts_buffer) >= self._tts_prebuffer_bytes:
                        self._tts_playback_started = True
                        self._tts_last_send_ts = monotonic()
                        try:
                            logger.info(f"[{self.session_id}] 🔊 TTS prebuffer ready: {len(self._tts_buffer)} bytes")
                        except Exception:
                            pass
                    # Send dynamically sized chunk based on elapsed time to target 1.0x
                    if self._tts_playback_started and len(self._tts_buffer) > 0:
                        now = monotonic()
                        if self._tts_last_send_ts == 0.0:
                            self._tts_last_send_ts = now
                        bytes_allowed = int((now - self._tts_last_send_ts) * self._bytes_per_second)
                        if bytes_allowed >= int(self._tts_chunk_bytes / 2):  # avoid tiny sends
                            bytes_to_send = min(bytes_allowed, len(self._tts_buffer), self._tts_max_send_bytes)
                            # Ensure we send whole samples (2-byte aligned) to avoid static
                            if bytes_to_send % 2 != 0:
                                bytes_to_send -= 1
                            if bytes_to_send >= 2:
                                send_chunk = bytes(self._tts_buffer[:bytes_to_send])
                                del self._tts_buffer[:bytes_to_send]
                                self._tts_last_send_ts += bytes_to_send / self._bytes_per_second
                    # Finalize when draining is requested and buffer emptied
                    if self._tts_drain_after_response and self._tts_playback_started and len(self._tts_buffer) == 0:
                        should_finalize = True
                        # Reset pacing state for next response
                        self._tts_streaming_active = False
                        self._tts_playback_started = False
                        self._tts_drain_after_response = False
                        self._tts_last_send_ts = 0.0
                if send_chunk:
                    try:
                        b64 = base64.b64encode(send_chunk).decode("ascii")
                        await self.websocket.send_json({"type": "audio_delta", "data": {"audio": b64}})
                        try:
                            logger.debug(f"[{self.session_id}] 📤 TTS sent {len(send_chunk)} bytes")
                        except Exception:
                            pass
                    except Exception:
                        pass
                if should_finalize:
                    try:
                        logger.debug(f"[{self.session_id}] 🔚 TTS drain complete; sending agent_ready")
                        await self.websocket.send_json({"type": "agent_ready", "data": {}})
                    except Exception:
                        pass
                    # Reset response metrics after drain
                    self._response_in_progress = False
                    self._current_response_id = None
                    self._resp_delta_counter = 0
                    self._resp_total_bytes = 0
                    self._resp_started_at = 0.0
                    self._resp_first_delta_at = 0.0
                    self._resp_last_delta_at = 0.0
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error(f"[{self.session_id}] TTS flush loop error: {e}", exc_info=True)

    def _start_audio_streamer(self):
        """Start background task to flush server-side audio to frontend."""
        if self._audio_stream_task is None or self._audio_stream_task.done():
            self._audio_stream_task = asyncio.create_task(self._audio_flush_loop())

    async def _stop_audio_streamer(self):
        """Stop background audio streamer task."""
        try:
            if self._audio_stream_task and not self._audio_stream_task.done():
                self._audio_stream_task.cancel()
                try:
                    await self._audio_stream_task
                except Exception:
                    pass
        finally:
            self._audio_stream_task = None

    async def _audio_flush_loop(self):
        """Flush buffered TTS audio to frontend at a fixed pace (20ms packets)."""
        chunk_bytes = int(self._bytes_per_second * self._pace_interval_s)
        try:
            while self.is_active:
                await asyncio.sleep(self._pace_interval_s)
                # Copy a chunk under lock
                send_chunk = None
                async with self._audio_buffer_lock:
                    if not self._playback_started:
                        if len(self._audio_buffer) >= self._min_prebuffer_bytes:
                            self._playback_started = True
                    if self._playback_started and len(self._audio_buffer) >= chunk_bytes:
                        send_chunk = bytes(self._audio_buffer[:chunk_bytes])
                        del self._audio_buffer[:chunk_bytes]
                    # If we are draining and buffer is empty, signal agent_ready once
                    if self._drain_after_response and self._playback_started and len(self._audio_buffer) == 0:
                        # Reset flags for next response
                        self._drain_after_response = False
                        self._playback_started = False
                        # Unlock turn and notify frontend ready
                        self._unlock_turn()
                        await self.websocket.send_json({"type": "agent_ready", "data": {}})
                if send_chunk:
                    # Encode to base64 and send to frontend
                    try:
                        b64 = base64.b64encode(send_chunk).decode("ascii")
                        await self.websocket.send_json({
                            "type": "audio_delta",
                            "data": {"audio": b64}
                        })
                    except Exception:
                        pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[{self.session_id}] Audio flush loop error: {e}", exc_info=True)

    async def _ingest_tts_audio_chunk(self, audio_b64: str):
        """Decode and enqueue TTS audio chunk for paced streaming."""
        try:
            audio_bytes = base64.b64decode(audio_b64)
        except Exception:
            return
        async with self._audio_buffer_lock:
            # Append and cap buffer to bound latency
            self._audio_buffer.extend(audio_bytes)
            if len(self._audio_buffer) > self._max_buffer_bytes:
                # Drop oldest to keep at most max_buffer
                excess = len(self._audio_buffer) - self._max_buffer_bytes
                if excess > 0:
                    del self._audio_buffer[:excess]
            # Mark that we are in playback mode
            if not self._playback_started and len(self._audio_buffer) >= self._min_prebuffer_bytes:
                self._playback_started = True

    async def _reset_tts_stream_for_new_response(self):
        """Reset paced streamer buffer at response start to avoid blending across turns."""
        async with self._audio_buffer_lock:
            self._audio_buffer.clear()
            self._playback_started = False
    
    async def handle_audio_data(self, audio_base64: str):
        """Handle incoming audio data from client."""
        if not self.is_active or not self.realtime_ws:
            return

        # Drop mic chunks while assistant is speaking or mic gated
        if not self._accept_audio_streaming:
            now = monotonic()
            if now - self._last_pause_log_ts >= 2.0:
                logger.debug(f"[{self.session_id}] Mic streaming paused (turn_locked={self._turn_locked}, response_in_progress={self._response_in_progress})")
                self._last_pause_log_ts = now
            return

        try:
            # Forward audio to Realtime API immediately
            await self.realtime_ws.send({
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            })

            # Local VAD on the server side (backend) to drive commit
            try:
                audio_bytes = base64.b64decode(audio_base64)
                # Compute normalized RMS
                samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0
            except Exception:
                rms = 0.0

            now = monotonic()
            if rms >= self._vad_rms_threshold:
                # Speech energy detected
                self._vad_last_speech_ts = now
                if not self._vad_speech_active:
                    self._vad_speech_active = True
                    self._vad_speech_start_ts = now
                    # Inform UI
                    await self.websocket.send_json({"type": "user_speech_started", "data": {}})
            else:
                # Silence region
                if self._vad_speech_active and (now - self._vad_last_speech_ts) >= self._vad_silence_duration_sec:
                    # Ensure minimum speech duration
                    speech_duration = now - self._vad_speech_start_ts
                    self._vad_speech_active = False
                    await self.websocket.send_json({"type": "user_speech_stopped", "data": {}})

                    if speech_duration >= self._vad_min_speech_sec:
                        # End of speech: lock turn and commit buffer for transcription
                        if not self._turn_locked:
                            # Keep mic accepting until commit is sent
                            self._lock_turn("audio", pause_mic=False)
                        try:
                            await self.realtime_ws.send({"type": "input_audio_buffer.commit"})
                            # Pause mic streaming after commit to avoid extra trailing audio
                            self._accept_audio_streaming = False
                            # Start transcript wait guard
                            self._awaiting_transcript = True
                            asyncio.create_task(self._transcript_timeout_guard(6.0))
                        except Exception as _:
                            # On commit error, unlock so user can retry
                            self._unlock_turn()
        except Exception as e:
            logger.error(f"[{self.session_id}] Error handling audio: {e}")
    
    async def handle_text_input(self, text: str):
        """Handle text input from client."""
        if not self.is_active or not self.realtime_ws:
            return
        
        try:
            # Lock turn for text and pause mic streaming
            self._lock_turn("text")
            # Send as conversation item
            await self.realtime_ws.send({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": text}]
                }
            })
            
            logger.info(f"[{self.session_id}] Sent text input: {text}")
        except Exception as e:
            logger.error(f"[{self.session_id}] Error sending text: {e}")
    
    async def _describe_image(self, image_b64: str, mime_type: str) -> str:
        """Summarize the uploaded image into a short, claim-relevant phrase."""
        try:
            messages = [
                SystemMessage(content=(
                    "You are an insurance claim intake assistant. "
                    "Describe, in at most 12 words, the most relevant damage or injury indicators visible. "
                    "Return a concise noun phrase only (no punctuation, no extra commentary)."
                )),
                HumanMessage(content=[
                    {"type": "text", "text": "Describe this image for insurance claim intake."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
                ]),
            ]
            resp = await self._vision_llm.ainvoke(messages)
            desc = str(getattr(resp, "content", "")).strip()
            return desc or "image provided"
        except Exception as e:
            logger.error(f"[{self.session_id}] Image captioning failed: {e}")
            return "image provided"

    async def handle_image_input(self, image_data: str, mime_type: str, name: str = None):
        """Handle image input from client."""
        if not self.is_active or not self.realtime_ws:
            return
        
        try:
            # Add to conversation history (for UI and logs)
            self.conversation_history.append({
                "role": "user",
                "content": f"Sent image: {name or 'Unnamed'}",
                "type": "image",
                "image": f"data:{mime_type};base64,{image_data}",
                "imageName": name,
                "timestamp": get_timestamp()
            })
            
            # Notify frontend (confirm receipt)
            await self.websocket.send_json({
                "type": "chat_message",
                "data": {
                    "role": "user",
                    "content": f"Sent image: {name or 'Unnamed'}",
                    "type": "image",
                    "image": f"data:{mime_type};base64,{image_data}",
                    "imageName": name,
                    "timestamp": get_timestamp()
                }
            })

            # Generate a concise description for LangGraph and process as a text turn
            description = await self._describe_image(image_data, mime_type)
            user_text = f"User attached an image file: {description}."

            # Lock the turn as text and route via LangGraph (Realtime remains talker only)
            self._lock_turn("text")
            await self._run_langgraph_workflow(user_text)

            logger.info(f"[{self.session_id}] Processed image: {name} ({mime_type}) -> {description}")
        except Exception as e:
            logger.error(f"[{self.session_id}] Error handling image: {e}")
    
    async def _realtime_event_loop(self):
        """Process events from Realtime API."""
        while self.is_active and self.realtime_ws:
            try:
                event = await self.realtime_ws.receive()
                await self._handle_realtime_event(event)
            except Exception as e:
                if self.is_active:
                    logger.error(f"[{self.session_id}] Realtime event error: {e}", exc_info=True)
                break
    
    async def _handle_realtime_event(self, event: Dict):
        """Handle incoming event from Realtime API."""
        event_type = event.get("type", "")
        
        try:
            if event_type == "session.created":
                # Configure session
                await self.realtime_ws.send({
                    "type": "session.update",
                    "session": self._get_session_config()
                })
            
            elif event_type == "session.updated":
                # Do not auto-greet via Realtime; LangGraph will drive assistant speech
                if not self._greeting_sent:
                    self._greeting_sent = True
                    # Lock turn for text greeting and pause mic
                    self._lock_turn("text")
                    # Trigger LangGraph initial greeting (no user message)
                    await self._run_langgraph_workflow("", init_greeting=True)
            
            elif event_type == "response.audio.delta":
                # Enqueue audio for paced streaming; log metrics
                rid = self._extract_response_id(event)
                # Drop audio from unexpected/cancelled responses to avoid blending
                if self._current_response_id is not None and rid and rid != self._current_response_id:
                    logger.debug(f"[{self.session_id}] Drop audio delta (non-current rid={rid})")
                    return
                if rid and rid in self._unexpected_response_ids:
                    logger.debug(f"[{self.session_id}] Drop audio delta (unexpected rid={rid})")
                    return
                audio_b64 = event.get("delta", "") or event.get("audio", "") or event.get("chunk", "")
                if audio_b64:
                    self._resp_delta_counter += 1
                    # Best-effort size logging
                    try:
                        chunk_bytes = len(base64.b64decode(audio_b64))
                    except Exception:
                        chunk_bytes = int(len(audio_b64) * 0.75)
                    self._resp_total_bytes += chunk_bytes
                    now = monotonic()
                    if self._resp_first_delta_at == 0.0:
                        self._resp_first_delta_at = now
                    interval_ms = int((now - self._resp_last_delta_at) * 1000) if self._resp_last_delta_at else 0
                    self._resp_last_delta_at = now
                    # Overspeed factor (audio duration vs elapsed wall time)
                    bytes_per_second = 24000 * 2
                    audio_ms = int(self._resp_total_bytes / bytes_per_second * 1000)
                    elapsed_ms = int((now - self._resp_started_at) * 1000) if self._resp_started_at else -1
                    overspeed = (round(audio_ms / elapsed_ms, 2) if elapsed_ms > 0 else -1)
                    if self._resp_delta_counter <= 2 or (self._resp_delta_counter % 200 == 0):
                        logger.debug(
                            f"[{self.session_id}] 🔈 delta#{self._resp_delta_counter} {chunk_bytes}B intv={interval_ms}ms audio={audio_ms}ms elaps={elapsed_ms}ms x{overspeed}"
                        )
                    await self._enqueue_tts_audio(audio_b64)
            
            elif event_type == "response.audio_transcript.done":
                # Capture assistant transcript
                transcript = event.get("transcript", "")
                if transcript and isinstance(transcript, str):
                    transcript = transcript.strip()
                    if transcript:
                        # Log response summary timing
                        try:
                            first_ms = int((self._resp_first_delta_at - self._resp_started_at) * 1000) if self._resp_first_delta_at and self._resp_started_at else -1
                            last_ms = int((monotonic() - self._resp_first_delta_at) * 1000) if self._resp_first_delta_at else -1
                            bytes_per_second = 24000 * 2
                            audio_ms = int(self._resp_total_bytes / bytes_per_second * 1000)
                            overspeed = (round(audio_ms / last_ms, 2) if last_ms > 0 else -1)
                            logger.debug(
                                f"[{self.session_id}] ✅ transcript.done (rid={self._current_response_id or 'unknown'}) "
                                f"deltas={self._resp_delta_counter}, total={self._resp_total_bytes}B, first={first_ms}ms, dur={last_ms}ms, audio={audio_ms}ms, x{overspeed}"
                            )
                        except Exception:
                            pass
                        logger.info(f"[{self.session_id}] AI: {transcript}")
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": transcript,
                            "timestamp": get_timestamp()
                        })
                        
                        # Send to frontend
                        await self.websocket.send_json({
                            "type": "chat_message",
                            "data": {
                                "role": "assistant",
                                "content": transcript,
                                "timestamp": get_timestamp()
                            }
                        })
                        # Assistant finished speaking; unlock (let pacing drain buffer)
                        self._unlock_turn()
                        # Request drain of remaining paced audio before agent_ready
                        self._tts_drain_after_response = True

            elif event_type == "response.content_part.done":
                # Fallback: Capture assistant transcript if provided on content part events
                part = event.get("part", {})
                if part.get("type") == "audio":
                    transcript = part.get("transcript")
                    if transcript and isinstance(transcript, str):
                        transcript = transcript.strip()
                        if transcript:
                            # Deduplicate against last assistant message
                            is_duplicate = (
                                self.conversation_history and
                                self.conversation_history[-1].get("role") == "assistant" and
                                self.conversation_history[-1].get("content") == transcript
                            )
                            if not is_duplicate:
                                logger.info(f"[{self.session_id}] AI: {transcript}")
                                self.conversation_history.append({
                                    "role": "assistant",
                                    "content": transcript,
                                    "timestamp": get_timestamp()
                                })

                                # Forward to frontend
                                await self.websocket.send_json({
                                    "type": "chat_message",
                                    "data": {
                                        "role": "assistant",
                                        "content": transcript,
                                        "timestamp": get_timestamp()
                                    }
                                })
                                # Ensure turn unlocked (let pacing drain buffer)
                                self._unlock_turn()
                                self._tts_drain_after_response = True
            
            elif event_type == "input_audio_buffer.speech_started":
                # User started speaking
                await self.websocket.send_json({
                    "type": "user_speech_started",
                    "data": {}
                })
                
                # Cancel any ongoing response only if one is active
                self._accept_audio_streaming = True
                if self._response_in_progress:
                    await self.realtime_ws.send({"type": "response.cancel"})
            
            elif event_type == "input_audio_buffer.speech_stopped":
                # User stopped speaking
                await self.websocket.send_json({
                    "type": "user_speech_stopped",
                    "data": {}
                })
                self._accept_audio_streaming = False
                # Cancel any model-initiated response (autopilot) to ensure only LangGraph responses are spoken
                try:
                    await self.realtime_ws.send({"type": "response.cancel"})
                except Exception:
                    pass
                # Prevent Realtime from auto-generating a response; LangGraph will drive the reply
                try:
                    await self.realtime_ws.send({"type": "response.cancel"})
                except Exception:
                    pass

            elif event_type == "response.created":
                # Track response creation to distinguish ours vs server-initiated
                rid = (
                    event.get("response", {}).get("id")
                    or event.get("response_id")
                    or event.get("item", {}).get("response_id")
                    or event.get("id")
                )
                if not self._response_in_progress:
                    # Unexpected server-initiated response; cancel and ignore
                    logger.info(f"[{self.session_id}] Unexpected response.created id={rid}")
                    if rid:
                        self._unexpected_response_ids.add(rid)
                    await self.realtime_ws.send({
                        "type": "response.cancel",
                        **({"response_id": rid} if rid else {})
                    })
                    return
                # Expected response for our LangGraph reply
                self._current_response_id = rid
                if rid:
                    self._unexpected_response_ids.discard(rid)
                # Reset audio delta counter and log
                self._resp_delta_counter = 0
                self._resp_total_bytes = 0
                self._resp_started_at = monotonic()
                self._resp_first_delta_at = 0.0
                self._resp_last_delta_at = 0.0
                # Reset TTS pacing buffer for this response
                async with self._tts_lock:
                    self._tts_buffer.clear()
                    self._tts_playback_started = False
                    self._tts_streaming_active = True
                    self._tts_drain_after_response = False
                    self._tts_stream_rid = rid
                    self._tts_last_send_ts = 0.0
                logger.info(f"[{self.session_id}] 🟢 response.created (id={rid or 'unknown'})")
            
            elif event_type == "conversation.item.created":
                # Handle user message
                item = event.get("item", {})
                if item.get("type") == "message" and item.get("role") == "user":
                    content = item.get("content", [])
                    for content_part in content:
                        if content_part.get("type") == "input_audio":
                            transcript = content_part.get("transcript")
                            if transcript and isinstance(transcript, str):
                                transcript = transcript.strip()
                                if transcript:
                                    # Transcript received; clear awaiting flag
                                    self._awaiting_transcript = False
                                    await self._run_langgraph_workflow(transcript)
                                    break
                        elif content_part.get("type") in ["input_text", "text"]:
                            text = content_part.get("text")
                            if text and isinstance(text, str):
                                text = text.strip()
                                if text:
                                    # For typed input, process but do not echo back (UI already optimistically adds)
                                    await self._run_langgraph_workflow(text)
                                    break
            
            elif event_type == "conversation.item.input_audio_transcription.completed":
                # Fallback transcription
                transcript = event.get("transcript")
                if transcript and isinstance(transcript, str):
                    transcript = transcript.strip()
                    if transcript:
                        # Check if not already processed
                        if not (self.conversation_history and 
                               self.conversation_history[-1].get("role") == "user" and
                               self.conversation_history[-1].get("content") == transcript):
                            await self._run_langgraph_workflow(transcript)

            elif event_type == "input_audio_transcription.completed":
                # Accept top-level transcription completion events as well
                transcript = event.get("transcript")
                if transcript and isinstance(transcript, str):
                    transcript = transcript.strip()
                    if transcript:
                        if not (self.conversation_history and 
                               self.conversation_history[-1].get("role") == "user" and
                               self.conversation_history[-1].get("content") == transcript):
                            await self._run_langgraph_workflow(transcript)
            
            elif event_type == "response.done":
                # Response completed - unlock and notify frontend
                rid = self._extract_response_id(event)
                try:
                    base = self._resp_first_delta_at or self._resp_started_at
                    duration_ms = int((monotonic() - base) * 1000) if base else -1
                    bytes_per_second = 24000 * 2
                    audio_ms = int(self._resp_total_bytes / bytes_per_second * 1000)
                    overspeed = (round(audio_ms / duration_ms, 2) if duration_ms > 0 else -1)
                    logger.debug(
                        f"[{self.session_id}] 🏁 response.done (rid={rid or 'unknown'}) deltas={self._resp_delta_counter}, total={self._resp_total_bytes}B, dur={duration_ms}ms, audio={audio_ms}ms, x{overspeed}"
                    )
                except Exception:
                    pass
                # Allow next turn to create a response; let pacing drain remaining audio
                self._response_in_progress = False
                self._current_response_id = None
                self._tts_drain_after_response = True
            
            elif event_type == "error":
                error = event.get("error", {})
                error_message = error.get("message", "Unknown error")
                logger.error(f"[{self.session_id}] Realtime API error: {error_message}")
                
                await self.websocket.send_json({
                    "type": "error",
                    "data": {"message": error_message}
                })
        
        except Exception as e:
            logger.error(f"[{self.session_id}] Error handling event {event_type}: {e}", exc_info=True)

    async def _transcript_timeout_guard(self, timeout_seconds: float = 6.0):
        """If no transcript arrives within timeout, unlock and resume mic."""
        try:
            start = monotonic()
            while self._awaiting_transcript and self.is_active:
                if monotonic() - start >= timeout_seconds:
                    self._awaiting_transcript = False
                    self._unlock_turn()
                    return
                await asyncio.sleep(0.1)
        except Exception:
            self._awaiting_transcript = False
    
    async def _run_langgraph_workflow(self, user_message: str, init_greeting: bool = False):
        """Run the LangGraph workflow and speak the assistant reply via Realtime."""
        # Record the user message locally and only echo to UI when it originates from voice
        # Typed inputs are already optimistically rendered by the frontend
        if not init_greeting and user_message:
            is_audio_turn = (self._turn_source == "audio")
            self.conversation_history.append({
                "role": "user",
                "content": user_message,
                "type": "voice" if is_audio_turn else "text",
                "timestamp": get_timestamp()
            })
            if is_audio_turn:
                await self.websocket.send_json({
                    "type": "chat_message",
                    "data": {
                        "role": "user",
                        "content": user_message,
                        "type": "voice",
                        "timestamp": get_timestamp()
                    }
                })

        try:
            # Build state
            state: VoiceAgentState = {
                "messages": ([] if init_greeting else [HumanMessage(content=user_message)]),
                "claim_data": self.current_claim_data,
                "timestamp": datetime.now().isoformat(),
                "current_timezone": self.current_timezone,
                "is_claim_complete": False,
                "escalation_requested": False,
                "retry_count": 0,
                "init_greeting": init_greeting,
            }

            config = {"configurable": {"thread_id": self.session_id}}
            result = await default_graph.ainvoke(state, config)

            # Update claim data if changed
            if result.get("claim_data") != self.current_claim_data:
                self.current_claim_data = result["claim_data"]
                self.is_claim_complete = result.get("is_claim_complete", False)
                await self.websocket.send_json({
                    "type": "claim_data_update",
                    "data": {
                        "claim_data": self.current_claim_data,
                        "is_complete": self.is_claim_complete
                    }
                })

            # Extract last assistant message
            response_message = "I'm here to help with your claim."
            for m in reversed(result.get("messages", [])):
                if isinstance(m, AIMessage):
                    response_message = m.content
                    break

            # Speak via Realtime as pure talker if enabled
            if voice_settings.REALTIME_AS_TALKER:
                if not self._response_in_progress:
                    # Pause mic streaming during TTS
                    self._response_in_progress = True
                    self._accept_audio_streaming = False
                    await self.realtime_ws.send({
                        "type": "response.create",
                        "response": {
                            "instructions": f"Speak verbatim: {response_message}",
                            "conversation": "none",
                            "modalities": ["audio", "text"],
                            "tool_choice": "none"
                        }
                    })

            # If claim is complete and we have submission details, notify UI
            if result.get("is_claim_complete"):
                submission_result = result.get("submission_result")
                if submission_result:
                    await self.websocket.send_json({
                        "type": "claim_complete",
                        "data": {
                            "claim_data": self.current_claim_data,
                            "submission_result": submission_result
                        }
                    })

        except Exception as e:
            logger.error(f"[{self.session_id}] Workflow error: {e}", exc_info=True)
            # Fallback speech
            if not self._response_in_progress:
                self._response_in_progress = True
                self._accept_audio_streaming = False
                await self.realtime_ws.send({
                    "type": "response.create",
                    "response": {
                        "instructions": "I'm here to help with your claim. Could you please tell me what happened?",
                        "conversation": "none",
                        "modalities": ["audio"],
                        "tool_choice": "none"
                    }
                })


class SessionManager:
    """Manages all active voice sessions."""
    
    def __init__(self):
        self.active_sessions: Dict[str, VoiceSession] = {}
        
        # Validate settings on startup
        try:
            validate_voice_settings()
            logger.info("✅ Voice settings validated")
        except Exception as e:
            logger.error(f"❌ Invalid voice settings: {e}")
            raise
    
    async def create_session(self, websocket: WebSocket) -> str:
        """Create a new voice session."""
        session_id = str(uuid4())
        session = VoiceSession(session_id, websocket)
        self.active_sessions[session_id] = session
        
        logger.info(f"Created session: {session_id}")
        return session_id
    
    async def remove_session(self, session_id: str):
        """Remove and cleanup a session."""
        session = self.active_sessions.get(session_id)
        if session:
            await session.stop()
            del self.active_sessions[session_id]
            logger.info(f"Removed session: {session_id}")
    
    async def cleanup_all_sessions(self):
        """Cleanup all active sessions."""
        for session_id in list(self.active_sessions.keys()):
            await self.remove_session(session_id)
    
    async def handle_client_message(self, session_id: str, message: Dict):
        """Handle message from client."""
        session = self.active_sessions.get(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return
        
        msg_type = message.get("type")
        
        if msg_type == "start_session":
            await session.start()
        
        elif msg_type == "stop_session":
            await session.stop()
        
        elif msg_type == "audio_data":
            audio_b64 = message.get("audio", "")
            await session.handle_audio_data(audio_b64)
        
        elif msg_type == "text_input":
            text = message.get("text", "")
            await session.handle_text_input(text)
        
        elif msg_type == "image_input":
            image_data = message.get("image", "")
            mime_type = message.get("mimeType", "image/jpeg")
            name = message.get("name", "image")
            await session.handle_image_input(image_data, mime_type, name)
        
        else:
            logger.warning(f"Unknown message type: {msg_type}")


