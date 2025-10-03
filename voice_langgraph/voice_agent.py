"""Main entry point for the LangGraph voice agent.

This module provides the VoiceAgent class that integrates:
- OpenAI Realtime API for voice interaction
- LangGraph workflow for conversation orchestration
- Trustcall for data extraction (without redundancy)
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage

from .settings import voice_settings, validate_voice_settings
from .graph_builder import default_graph
from .state import VoiceAgentState
from .prompts import Prompts
from .schema import PropertyClaim
from .utils import (
    AudioProcessor,
    AudioPlayback,
    WebSocketManager,
    encode_audio,
    decode_audio,
    get_timestamp,
    get_current_time_context,
    format_claim_summary,
    print_field_updates
)


class VoiceAgent:
    """Main voice agent that orchestrates the conversation workflow.
    
    Key improvements over the original implementation:
    - No redundant trustcall operations
    - Clean separation of concerns with LangGraph
    - Better error handling and recovery
    - Modular architecture
    """
    
    def __init__(self, display_json: bool = False, display_interval: float = 1.0):
        # Configuration
        self.voice = voice_settings.JUNIOR_AGENT_VOICE
        self.instructions = Prompts.get_supervisor_system_prompt()
        self.display_json = display_json
        self.display_interval = display_interval
        
        # Components
        self.audio_processor = AudioProcessor()
        self.audio_playback = AudioPlayback()
        self.ws_manager: Optional[WebSocketManager] = None
        
        # State
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.conversation_history: List[dict] = []
        # Initialize with empty structure using factory method
        self.current_claim_data: Dict[str, Any] = PropertyClaim.create_empty().model_dump()
        self._processed_messages = set()  # Track processed messages to avoid duplicates
        self.current_timezone: str = "America/Toronto"  # Default timezone
        self._greeting_sent = False
        self._is_running = False
        # Turn gating (process first-arriving user input per turn)
        self._turn_locked: bool = False
        self._response_in_progress: bool = False  # Prevent overlapping response.create calls
        self._turn_source: Optional[str] = None  # 'audio' | 'text'
        # Control whether microphone audio is forwarded to the server
        self._accept_audio_streaming: bool = True
        # Pending image attachments to include with the next user message
        self._attached_images: List[Dict[str, Any]] = []
        
    def _build_ws_url(self) -> str:
        """Build WebSocket URL for Azure OpenAI Realtime API."""
        endpoint = voice_settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        api_version = voice_settings.AZURE_OPENAI_REALTIME_API_VERSION
        deployment = voice_settings.AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME
        
        https_url = f"{endpoint}/openai/realtime?api-version={api_version}&deployment={deployment}"
        return https_url.replace("https://", "wss://").replace("http://", "ws://")
        
    def _get_session_config(self) -> Dict[str, Any]:
        """Get Realtime API session configuration.
        
        Optimized for real-time audio:
        - Uses input_audio_transcription for reliable transcripts
        - Transcripts available via conversation.item.input_audio_transcription.completed
        - Using server VAD for natural turn detection
        """
        return {
            "modalities": ["text", "audio"],
            "instructions": self.instructions,
            "voice": self.voice,
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {
                "language": voice_settings.TRANSCRIPTION_LANGUAGE,
                "model": voice_settings.TRANSCRIPTION_MODEL,
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": voice_settings.VAD_THRESHOLD,
                "prefix_padding_ms": voice_settings.VAD_PREFIX_PADDING_MS,
                "silence_duration_ms": voice_settings.VAD_SILENCE_DURATION_MS,
            },
        }

    def _lock_turn(self, source: str):
        """Lock the conversation turn to the specified source ('audio' or 'text')."""
        if not self._turn_locked:
            self._turn_locked = True
            self._turn_source = source
            # Pause audio streaming while a turn is being processed
            self._accept_audio_streaming = False
            print(f"[{get_timestamp()}] 🔒 Turn locked by {source}")

    def _unlock_turn(self):
        """Unlock the conversation turn and resume audio streaming."""
        if self._turn_locked:
            print(f"[{get_timestamp()}] 🔓 Turn unlocked")
        self._turn_locked = False
        self._turn_source = None
        self._accept_audio_streaming = True
        # Clear any pending image attachments after a completed turn
        self._attached_images.clear()

    async def attach_image_from_path(self, file_path: str, mime_type: Optional[str] = None) -> Tuple[bool, str]:
        """Attach an image from local path to include with the next user message.

        Returns (success, message).
        """
        import os
        import mimetypes
        try:
            if not os.path.isfile(file_path):
                return False, f"File not found: {file_path}"
            if not mime_type:
                guessed, _ = mimetypes.guess_type(file_path)
                mime_type = guessed or "application/octet-stream"
            with open(file_path, "rb") as f:
                data = f.read()
            import base64
            b64 = base64.b64encode(data).decode("ascii")
            self._attached_images.append({
                "type": "input_image",
                "image": b64,
                "mime_type": mime_type,
            })
            return True, f"Attached image ({mime_type}): {os.path.basename(file_path)}"
        except Exception as e:
            return False, f"Failed to attach image: {e}"
        
    async def _run_langgraph_workflow(self, user_message: str):
        """Run the LangGraph workflow with the user's message.
        
        Triggered by transcription completion events from Realtime API.
        """
        # Create state for LangGraph workflow
        # Note: Only pass NEW messages - LangGraph's checkpointer handles history
        state: VoiceAgentState = {
            "messages": [HumanMessage(content=user_message)],
            "claim_data": self.current_claim_data,
            "timestamp": datetime.now().isoformat(),
            "current_timezone": self.current_timezone,
            "is_claim_complete": False,
            "escalation_requested": False,
            "retry_count": 0,
        }
        
        # Config with thread_id required for checkpointer
        config = {"configurable": {"thread_id": self.session_id}}
        
        # Run the workflow
        try:
            result = await default_graph.ainvoke(state, config)
            
            # Update claim data if changed
            if result.get("claim_data") != self.current_claim_data:
                previous_data = self.current_claim_data.copy()
                self.current_claim_data = result["claim_data"]
                
                if self.display_json:
                    print_field_updates(previous_data, self.current_claim_data)
                    print("\n" + format_claim_summary(self.current_claim_data))
                    
            # Handle assistant speech depending on orchestration mode
            # Extract last assistant message from messages
            response_message = "I'm here to help with your claim."
            try:
                for m in reversed(result.get("messages", [])):
                    if isinstance(m, AIMessage):
                        response_message = m.content
                        break
            except Exception:
                pass
            
            # LangGraph orchestrates responses, Realtime speaks them
            if voice_settings.REALTIME_AS_TALKER:
                # Prefer explicit instructions to make Realtime speak exactly the provided text
                # Avoid creating an assistant message first to prevent duplicate items
                if not self._response_in_progress:
                    self._response_in_progress = True
                    await self.ws_manager.send({
                        "type": "response.create",
                        "response": {
                            "instructions": response_message,
                            "tool_choice": "none"
                        }
                    })
                else:
                    print(f"[{get_timestamp()}] ⚠️ Skipping response.create - already in progress")
            
            # Check if claim is complete
            if result.get("is_claim_complete"):
                print("\n✅ Claim intake complete!")
                # Display submission result if available
                submission_result = result.get("submission_result")
                if submission_result:
                    print(f"\n📝 Claim Submitted:")
                    print(f"   • Claim ID: {submission_result.get('claim_id')}")
                    print(f"   • Status: {submission_result.get('status')}")
                    print(f"   • Submitted at: {submission_result.get('submitted_at')}")
                    print(f"   • Next steps: {submission_result.get('next_steps')}")
                    if submission_result.get("summary_two_sentences"):
                        print(f"   • Summary: {submission_result.get('summary_two_sentences')}")
                
                print("\n" + format_claim_summary(self.current_claim_data))
                
        except Exception as e:
            print(f"⚠️ Workflow error: {e}")
            # Send fallback response
            await self.ws_manager.send({
                "type": "conversation.item.create", 
                "item": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "I'm here to help with your claim. Could you please tell me what happened?"}]
                },
            })
            if not self._response_in_progress:
                self._response_in_progress = True
                await self.ws_manager.send({"type": "response.create"})
            else:
                print(f"[{get_timestamp()}] ⚠️ Skipping response.create - already in progress")
            
    async def _handle_websocket_event(self, event: Dict[str, Any]):
        """Handle incoming WebSocket events.
        
        Optimized for real-time audio:
        - Uses conversation.item.created for faster transcript access
        - Handles response.done for assistant transcripts
        - Better interruption handling
        """
        event_type = event.get("type", "")
        
        if event_type == "session.created":
            # Configure session
            await self.ws_manager.send({
                "type": "session.update",
                "session": self._get_session_config(),
            })
            
        elif event_type == "session.updated":
            # Trigger greeting if not sent
            if not self._greeting_sent:
                if voice_settings.REALTIME_AS_TALKER:
                    # Let Realtime produce the greeting immediately for minimal latency
                    if not self._response_in_progress:
                        self._response_in_progress = True
                        await self.ws_manager.send({
                            "type": "response.create",
                            "response": {
                                "instructions": self.instructions + "\n\nStart with the greeting immediately.",
                            "tool_choice": "none"
                        },
                    })
                else:
                    # If Realtime is not the talker, do not auto-speak here; the graph will drive speech
                    pass
                self._greeting_sent = True
                print(f"[{get_timestamp()}] 🎙️ AI listening...")
                
        elif event_type == "response.audio.delta":
            # Handle audio playback - stream immediately for lowest latency
            audio_b64 = event.get("delta", "") or event.get("audio", "")
            if audio_b64:
                audio_data = decode_audio(audio_b64)
                await self.audio_playback.add_audio(audio_data)
                
        elif event_type == "response.audio_transcript.done":
            # OPTIMIZED: Capture assistant transcript from audio transcript done event
            # This is faster than waiting for content_part.done
            self._response_in_progress = False  # Reset response flag
            transcript = event.get("transcript", "")
            if transcript and isinstance(transcript, str):
                transcript = transcript.strip()
                if transcript:
                    print(f"[{get_timestamp()}] 🤖 AI: {transcript}")
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": transcript,
                        "timestamp": get_timestamp()
                    })
                    # Assistant finished speaking; unlock turn for next input
                    self._unlock_turn()
            else:
                print(f"[{get_timestamp()}] 🐛 DEBUG: response.audio_transcript.done - transcript is None or not string")
                
        elif event_type == "response.content_part.done":
            # Fallback: Capture assistant transcript if not already captured
            part = event.get("part", {})
            if part.get("type") == "audio":
                transcript = part.get("transcript")
                if transcript and isinstance(transcript, str):
                    transcript = transcript.strip()
                    if transcript:
                        # Check if already added via response.audio_transcript.done
                        if not (self.conversation_history and 
                               self.conversation_history[-1].get("content") == transcript):
                            print(f"[{get_timestamp()}] 🤖 AI: {transcript}")
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": transcript,
                                "timestamp": get_timestamp()
                            })
                    
        elif event_type == "input_audio_buffer.speech_stopped":
            # Cancel VAD-triggered auto-response immediately when speech stops
            # This prevents Realtime from creating its own response
            # LangGraph will generate the intelligent response instead
            if not self._turn_locked:
                self._lock_turn("audio")
                await self.ws_manager.send({"type": "response.cancel"})
                print(f"[{get_timestamp()}] 🎤 Speech stopped, processing...")
                    
        elif event_type == "conversation.item.created":
            # OPTIMIZED: Get user transcripts from conversation items (faster than transcription.completed)
            item = event.get("item", {})
            print(f"[{get_timestamp()}] 🐛 DEBUG: conversation.item.created - item type: {item.get('type')}, role: {item.get('role')}")
            
            if item.get("type") == "message" and item.get("role") == "user":
                # Check for audio content with transcript
                content = item.get("content", [])
                print(f"[{get_timestamp()}] 🐛 DEBUG: User message content: {len(content)} parts")
                
                for idx, content_part in enumerate(content):
                    content_type = content_part.get("type")
                    print(f"[{get_timestamp()}] 🐛 DEBUG: Content part {idx}: type={content_type}")
                    
                    if content_type == "input_audio":
                        transcript = content_part.get("transcript")
                        print(f"[{get_timestamp()}] 🐛 DEBUG: Transcript value: {transcript} (type: {type(transcript)})")
                        
                        if transcript and isinstance(transcript, str):
                            transcript = transcript.strip()
                            if transcript:
                                print(f"[{get_timestamp()}] 👤 User: {transcript}")
                                self.conversation_history.append({
                                    "role": "user", 
                                    "content": transcript,
                                    "timestamp": get_timestamp()
                                })
                                
                                # Trigger LangGraph workflow directly
                                await self._run_langgraph_workflow(transcript)
                                break
                        else:
                            print(f"[{get_timestamp()}] 🐛 DEBUG: Transcript not available yet in conversation.item.created")
                            # Transcript might not be available yet - will be captured by other events
                    elif content_type == "input_text" or content_type == "text":
                        # Handle typed text items (from our text input loop or future UIs)
                        text = content_part.get("text")
                        if isinstance(text, str) and text.strip():
                            text = text.strip()
                            # Create message hash for deduplication
                            msg_hash = hash(f"user:{text}:{get_timestamp()[:10]}")  # Include minute precision
                            if msg_hash not in self._processed_messages:
                                self._processed_messages.add(msg_hash)
                                print(f"[{get_timestamp()}] 👤 User (typed): {text}")
                                self.conversation_history.append({
                                    "role": "user",
                                    "content": text,
                                    "timestamp": get_timestamp()
                                })
                                await self._run_langgraph_workflow(text)
                            break
                            
        elif event_type == "input_audio_buffer.committed":
            # Audio buffer committed - speech is ready for processing
            # This happens after speech_stopped and before transcription
            print(f"[{get_timestamp()}] 📝 Audio committed, awaiting transcript...")
            
        elif event_type == "conversation.item.input_audio_transcription.completed":
            # FALLBACK: Use this event if transcript wasn't available in conversation.item.created
            # This is the reliable fallback for getting user transcripts
            transcript = event.get("transcript")
            if transcript and isinstance(transcript, str):
                transcript = transcript.strip()
                if transcript:
                    # Check if we already processed this transcript
                    if not (self.conversation_history and 
                           self.conversation_history[-1].get("role") == "user" and
                           self.conversation_history[-1].get("content") == transcript):
                        print(f"[{get_timestamp()}] 👤 User: {transcript}")
                        self.conversation_history.append({
                            "role": "user", 
                            "content": transcript,
                            "timestamp": get_timestamp()
                        })
                        
                        # Trigger LangGraph workflow
                        await self._run_langgraph_workflow(transcript)
            
        elif event_type == "response.content_part.done":
            # Ensure turn is unlocked if we missed transcript.done
            part = event.get("part", {})
            if part.get("type") == "audio":
                self._unlock_turn()
        
        elif event_type == "response.done":
            # Fallback unlock when response is fully done
            self._response_in_progress = False  # Reset response flag
            self._unlock_turn()
        
        elif event_type == "error":
            # Handle API errors
            self._response_in_progress = False  # Reset response flag on error
            error = event.get("error", {})
            error_message = error.get("message", "Unknown error")
            print(f"[{get_timestamp()}] ❌ API Error: {error_message}")
            
    async def _audio_input_loop(self):
        """Stream microphone audio to WebSocket."""
        async for audio_chunk in self.audio_processor.stream_microphone():
            if not self._is_running:
                break
            if voice_settings.ENABLE_AUDIO_INPUT and self._accept_audio_streaming:
                await self.ws_manager.send({
                    "type": "input_audio_buffer.append",
                    "audio": encode_audio(audio_chunk),
                })

    async def _text_input_loop(self):
        """Non-blocking loop to read typed text from stdin and send as a user message.
        Special commands:
        - /attach <path> [mime] : attach an image file to the next message
        - /help : show commands
        """
        import sys
        loop = asyncio.get_event_loop()
        print("⌨️  Text input enabled. Type a message and press Enter. Use /attach <path> to add an image.")
        while self._is_running and voice_settings.ENABLE_TEXT_INPUT:
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
            except Exception:
                break
            if line is None:
                break
            text = line.strip()
            if not text:
                continue
            if text.lower().startswith("/help"):
                print("Commands: /attach <path> [mime]")
                continue
            if text.lower().startswith("/attach "):
                parts = text.split(" ", 2)
                if len(parts) >= 2:
                    # parts[1] may include a path with spaces if quoted - keep simple for now
                    file_and_maybe_mime = parts[1:]
                    file_path = file_and_maybe_mime[0]
                    mime = None
                    if len(file_and_maybe_mime) > 1:
                        mime = file_and_maybe_mime[1]
                    ok, msg = await self.attach_image_from_path(file_path, mime)
                    print(("✅ " if ok else "❌ ") + msg)
                else:
                    print("Usage: /attach <path> [mime]")
                continue

            # If a turn is already locked by audio/text, ignore this entry
            if self._turn_locked:
                print("⏳ Busy processing the previous turn. Please wait...")
                continue

            # Lock turn for text and pause mic streaming
            self._lock_turn("text")

            # Build user message parts: include text and any attached images
            content_parts: List[Dict[str, Any]] = [{"type": "input_text", "text": text}]
            if self._attached_images:
                content_parts.extend(list(self._attached_images))

            # Send as conversation item
            await self.ws_manager.send({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": content_parts,
                },
            })

            # No need to call workflow here - conversation.item.created event will handle it
            
    async def _websocket_receive_loop(self):
        """Receive and handle WebSocket messages."""
        while self._is_running:
            try:
                event = await self.ws_manager.receive()
                await self._handle_websocket_event(event)
            except Exception as e:
                if self._is_running:
                    import traceback
                    print(f"⚠️ WebSocket error: {e}")
                    print(f"🐛 DEBUG: Full traceback:")
                    print(traceback.format_exc())
                    print(f"🐛 DEBUG: Last event type: {event.get('type', 'unknown') if 'event' in locals() else 'N/A'}")
                break
                
    async def _display_json_loop(self):
        """Periodically display claim JSON if enabled."""
        last_json = ""
        
        while self._is_running and self.display_json:
            current_json = json.dumps(self.current_claim_data, sort_keys=True)
            
            if current_json != last_json and current_json != "{}":
                print(f"\n[{get_timestamp()}] 📋 Current Claim Data:")
                print(json.dumps(self.current_claim_data, indent=2))
                last_json = current_json
                
            await asyncio.sleep(self.display_interval)
            
    async def start(self):
        """Start the voice agent."""
        print("🚀 Starting LangGraph Voice Agent...")
        
        # Select microphone
        if voice_settings.ENABLE_AUDIO_INPUT:
            if not self.audio_processor.select_microphone():
                return
            
        # Initialize WebSocket
        ws_url = self._build_ws_url()
        self.ws_manager = WebSocketManager(ws_url, voice_settings.AZURE_OPENAI_API_KEY)
        
        try:
            # Connect
            await self.ws_manager.connect()
            self._is_running = True
            
            # Start audio playback
            self.audio_playback.start()
            
            # Create tasks
            tasks = [
                asyncio.create_task(self._audio_input_loop()),
                asyncio.create_task(self._websocket_receive_loop()),
            ]
            if voice_settings.ENABLE_TEXT_INPUT:
                tasks.append(asyncio.create_task(self._text_input_loop()))
            
            if self.display_json:
                tasks.append(asyncio.create_task(self._display_json_loop()))
                
            # Wait for completion
            await asyncio.gather(*tasks)
            
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted by user")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            self._is_running = False
            self.audio_playback.stop()
            
            if self.ws_manager:
                await self.ws_manager.close()
                
            print("\n👋 Voice agent stopped")
            
            # Print final summary if we have data
            if self.current_claim_data:
                print("\n" + format_claim_summary(self.current_claim_data))


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LangGraph Voice Agent")
    parser.add_argument("--display-json", action="store_true", 
                       help="Display claim JSON updates in real-time")
    parser.add_argument("--display-interval", type=float, default=1.0,
                       help="Seconds between JSON display updates")
    
    args = parser.parse_args()
    
    # Validate settings
    validate_voice_settings()
    
    # Create and start agent
    agent = VoiceAgent(
        display_json=args.display_json,
        display_interval=args.display_interval
    )
    
    await agent.start()


if __name__ == "__main__":
    asyncio.run(main())
