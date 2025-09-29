"""LangGraph Voice Agent - Optimized Implementation

An enterprise-grade voice agent for property claims intake using:
- OpenAI Realtime API (via Azure) for full-duplex audio + ASR + TTS
- LangGraph for optimized multi-agent supervisor-worker architecture
- Trustcall for robust JSON extraction with nested schema support
- Comprehensive error handling and recovery mechanisms

Key Optimizations:
✅ Proper supervisor-worker multi-agent pattern
✅ Simplified state management with better type safety
✅ Centralized error handling with graceful fallbacks  
✅ Load environment variables via python-dotenv
✅ Enhanced tool calling patterns following LangGraph best practices
✅ Improved developer experience with better documentation

Architecture:
- Worker Agent: Handles data extraction and claim updates
- Supervisor Agent: Makes decisions and composes responses
- Voice Agent: Manages realtime audio and WebSocket communication

Run:
  python run_voice_agent_langgraph.py [--display-json] [--display-interval SECONDS]

Requirements:
- Azure OpenAI Realtime API credentials
- Audio device access (microphone/speakers)
- Configuration in .env file (loaded automatically via python-dotenv)
"""

from __future__ import annotations

import asyncio
import base64
import json
import ssl
import threading
from typing import Any, Dict, List, Optional, TypedDict, Union
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
    """Simplified state for the supervisor LangGraph pipeline."""
    
    # Input data
    conversation_history: List[Dict[str, Any]]
    user_context: str
    claim_data: Dict[str, Any]
    
    # Processing results
    updated_claim_data: Dict[str, Any]
    is_complete: bool
    next_message: str
    
    # Error handling
    error: Optional[str]


class LangGraphSupervisor:
    """Optimized supervisor using LangGraph with proper multi-agent patterns."""

    def __init__(self) -> None:
        self.trustcall_agent: TrustcallExtractionAgent = create_trustcall_agent()
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        """Build an optimized LangGraph following supervisor-worker pattern."""
        graph = StateGraph(SupervisorState)

        # Worker node: Data extraction and updating
        async def trustcall_worker(state: SupervisorState) -> SupervisorState:
            """Worker agent that handles claim data extraction."""
            try:
                # Extract latest user input from conversation history
                history = state.get("conversation_history", [])
                user_input = ""
                for msg in reversed(history):
                    if msg.get("role") == "user" and msg.get("content"):
                        user_input = str(msg.get("content"))
                        break

                # Update claim data using trustcall
                if user_input:
                    result = await self.trustcall_agent.extract_and_patch_claim_data(
                        user_input=user_input,
                        existing_data=state.get("claim_data", {}),
                        conversation_context=state.get("user_context", ""),
                    )
                    
                    if result.extraction_successful:
                        state["updated_claim_data"] = result.updated_data
                    else:
                        state["updated_claim_data"] = state.get("claim_data", {})
                        state["error"] = result.error_message
                else:
                    state["updated_claim_data"] = state.get("claim_data", {})
                    
                return state
            except Exception as e:
                state["error"] = f"Trustcall worker failed: {e}"
                state["updated_claim_data"] = state.get("claim_data", {})
                return state

        # Supervisor node: Decision making and response composition
        async def supervisor_decision(state: SupervisorState) -> SupervisorState:
            """Supervisor agent that validates completeness and composes responses."""
            try:
                claim_data = state.get("updated_claim_data", {})
                context = state.get("user_context", "").lower()
                
                # Validate completeness
                validation = self.trustcall_agent.validate_extraction_completeness(claim_data)
                is_complete = bool(validation.get("is_complete", False))
                state["is_complete"] = is_complete
                
                # Compose appropriate response
                if is_complete:
                    state["next_message"] = (
                        "Thank you for providing all that information. I have everything needed for your claim. "
                        "I'm submitting this now."
                    )
                elif "accident" in context or "incident" in context or "claim" in context:
                    state["next_message"] = (
                        "I'm sorry to hear about your situation. I'll help you get this reported. "
                        "What's your full name and the best phone number to reach you?"
                    )
                elif "coverage" in context or "deductible" in context:
                    state["next_message"] = (
                        "I can help with coverage details once I have your claim information. "
                        "Let's start with what happened and your contact details."
                    )
                else:
                    state["next_message"] = (
                        "I'm here to help with your claim. Can you tell me more about what happened?"
                    )
                    
                return state
            except Exception as e:
                state["error"] = f"Supervisor decision failed: {e}"
                state["next_message"] = (
                    "I'm here to help with your claim. Let's start with what happened and your contact information."
                )
                state["is_complete"] = False
                return state

        # Add nodes to graph
        graph.add_node("trustcall_worker", trustcall_worker)
        graph.add_node("supervisor_decision", supervisor_decision)

        # Define flow: worker processes data, then supervisor makes decisions
        graph.add_edge(START, "trustcall_worker")
        graph.add_edge("trustcall_worker", "supervisor_decision")
        graph.add_edge("supervisor_decision", END)

        return graph.compile()

    async def get_next_response(
        self, 
        conversation_history: Optional[List[Dict[str, Any]]] = None, 
        user_context: Optional[str] = None, 
        claim_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Simplified interface for getting supervisor response with better type safety."""
        initial_state: SupervisorState = {
            "conversation_history": conversation_history or [],
            "user_context": user_context or "",
            "claim_data": claim_data or {},
        }
        
        try:
            final_state: SupervisorState = await self._graph.ainvoke(initial_state)
            
            return {
                "message": final_state.get("next_message", "I'm here to help with your claim."),
                "is_complete": bool(final_state.get("is_complete", False)),
                "claim_data": final_state.get("updated_claim_data", claim_data or {}),
                "error": final_state.get("error"),
            }
        except Exception as e:
            # Fallback response on graph failure
            return {
                "message": "I'm here to help with your claim. Let's start with what happened.",
                "is_complete": False,
                "claim_data": claim_data or {},
                "error": f"Graph execution failed: {e}",
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
        self.display_json_enabled: bool = bool(getattr(settings, "DISPLAY_CLAIM_JSON", False))
        self.display_interval: float = 1.0
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
        # SSL verification is enabled by default for production security
        return None

    def _get_supervisor_tool_def(self) -> Dict[str, Any]:
        """Define the supervisor tool with improved documentation."""
        return {
            "type": "function",
            "name": "getNextResponseFromSupervisor",
            "description": (
                "Consult the expert supervisor to determine the next response for complex decisions. "
                "The supervisor analyzes conversation context and claim data to provide appropriate guidance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "relevantContextFromLastUserMessage": {
                        "type": "string",
                        "description": "Key information or context from the user's most recent message that needs analysis."
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
        """Send event with error handling."""
        try:
            if self.ws and not self.ws.closed:
                await self.ws.send(json.dumps(event))
        except Exception as e:
            print(f"⚠️ WebSocket send failed: {e}")

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
        """Safely append conversation history with error handling."""
        try:
            if not content or not content.strip():
                return
            self.conversation_history.append({
                "type": "message", 
                "role": role, 
                "content": content.strip()
            })
            # Limit conversation history size for memory management
            max_history = getattr(settings, "MAX_CONVERSATION_HISTORY", 50)
            if len(self.conversation_history) > max_history:
                self.conversation_history = self.conversation_history[-max_history:]
        except Exception as e:
            print(f"⚠️ Failed to append conversation: {e}")

    async def _handle_function_call(self, function_call: Dict[str, Any]) -> None:
        """Handle function calls with comprehensive error recovery."""
        try:
            name = (function_call or {}).get("name")
            if name != "getNextResponseFromSupervisor":
                return

            # Parse arguments safely
            args_str = (function_call or {}).get("arguments", "{}")
            try:
                args = json.loads(args_str)
            except json.JSONDecodeError:
                print("⚠️ Invalid JSON in function call arguments")
                args = {}

            relevant = args.get("relevantContextFromLastUserMessage", "")

            # Get supervisor response with error handling
            result = await self.supervisor.get_next_response(
                conversation_history=[
                    {"role": m.get("role", "user"), "content": m.get("content", "")}
                    for m in self.conversation_history if m.get("type") == "message"
                ],
                user_context=relevant,
                claim_data=self.current_claim_data,
            )

            # Handle supervisor errors
            if result.get("error"):
                print(f"⚠️ Supervisor error: {result['error']}")

            # Update claim data safely
            try:
                previous_data = json.loads(json.dumps(self.current_claim_data))
                self.current_claim_data = result.get("claim_data", self.current_claim_data)
                if self.display_json_enabled:
                    self._print_field_updates(previous_data, self.current_claim_data)
                    self._last_claim_print = json.dumps(self.current_claim_data, sort_keys=True, ensure_ascii=False)
            except Exception as e:
                print(f"⚠️ Failed to update claim data: {e}")

            # Send response to Realtime API
            call_id = (function_call or {}).get("id", "")
            message_content = result.get("message", "I'm here to help with your claim. How can I assist you?")
            
            await self._send_tool_response(call_id, message_content)
            
            # Record assistant message in history
            self._append_conversation("assistant", message_content)

        except Exception as e:
            # Last resort fallback
            print(f"❌ Function call handler failed: {e}")
            await self._send_fallback_response(function_call)

    async def _send_tool_response(self, call_id: str, message: str) -> None:
        """Send tool response with error handling."""
        try:
            tool_output_event = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": message,
                },
            }
            await self._send(tool_output_event)
            await self._send({"type": "response.create"})
        except Exception as e:
            print(f"⚠️ Failed to send tool response: {e}")

    async def _send_fallback_response(self, function_call: Dict[str, Any]) -> None:
        """Send a fallback response when function call handling fails."""
        try:
            call_id = (function_call or {}).get("id", "")
            fallback_message = "I'm here to help with your claim. Could you please tell me what happened?"
            await self._send_tool_response(call_id, fallback_message)
            self._append_conversation("assistant", fallback_message)
        except Exception as e:
            print(f"❌ Fallback response failed: {e}")

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
                        # Kick off background trustcall update for real-time JSON display
                        try:
                            asyncio.create_task(self._background_trustcall_update(text))
                        except Exception as e:
                            print(f"⚠️ Failed to start background update: {e}")

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
            pass

    async def _background_trustcall_update(self, user_text: str) -> None:
        """Background task to update claim data for real-time display."""
        try:
            result = await self.supervisor.trustcall_agent.extract_and_patch_claim_data(
                user_input=user_text,
                existing_data=self.current_claim_data,
                conversation_context="Background update",
            )
            
            if result.extraction_successful:
                previous_data = json.loads(json.dumps(self.current_claim_data))
                self.current_claim_data = result.updated_data
                
                if self.display_json_enabled:
                    self._print_field_updates(previous_data, self.current_claim_data)
                    self._last_claim_print = json.dumps(self.current_claim_data, sort_keys=True, ensure_ascii=False)
                    
        except Exception as e:
            # Silent fail for background updates to avoid UI noise
            pass

    async def start(self) -> None:
        url = self._build_ws_url()
        headers = [("api-key", settings.AZURE_OPENAI_API_KEY or ""), ("OpenAI-Beta", "realtime=v1")]
        async with websockets.connect(
            url,
            extra_headers=headers,
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
                for task in (mic, events, self._json_task):
                    if task and not task.done():
                        task.cancel()


def _ensure_langsmith_envs() -> None:
    """Ensure LangSmith environment variables are set for tracing."""
    try:
        # Environment variables are now loaded via load_dotenv in settings.py
        # This function just validates they're available if needed
        if settings.LANGCHAIN_TRACING and settings.LANGCHAIN_TRACING.lower() == "true":
            if not settings.LANGSMITH_API_KEY:
                print("⚠️  Warning: LANGCHAIN_TRACING enabled but LANGSMITH_API_KEY not set")
    except Exception:
        pass


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--display-json", action="store_true", help="Periodically print claim JSON on change")
    parser.add_argument("--display-interval", type=float, default=None, help="Seconds between JSON checks (default 1.0)")
    args = parser.parse_args()

    validate_required_settings()
    _ensure_langsmith_envs()
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


