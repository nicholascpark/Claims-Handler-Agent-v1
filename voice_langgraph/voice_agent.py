"""Main entry point for the LangGraph voice agent.

This module provides the VoiceAgent class that integrates:
- OpenAI Realtime API for voice interaction
- LangGraph workflow for conversation orchestration
- Trustcall for data extraction (without redundancy)
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
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
        self.current_timezone: str = "America/Toronto"  # Default timezone
        self._greeting_sent = False
        self._is_running = False
        
    def _build_ws_url(self) -> str:
        """Build WebSocket URL for Azure OpenAI Realtime API."""
        endpoint = voice_settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        api_version = voice_settings.AZURE_OPENAI_REALTIME_API_VERSION
        deployment = voice_settings.AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME
        
        https_url = f"{endpoint}/openai/realtime?api-version={api_version}&deployment={deployment}"
        return https_url.replace("https://", "wss://").replace("http://", "ws://")
        
    def _get_session_config(self) -> Dict[str, Any]:
        """Get Realtime API session configuration."""
        return {
            "modalities": ["text", "audio"],
            "instructions": self.instructions,
            "voice": self.voice,
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": voice_settings.TRANSCRIPTION_MODEL,
                "language": voice_settings.TRANSCRIPTION_LANGUAGE,
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": voice_settings.VAD_THRESHOLD,
                "prefix_padding_ms": voice_settings.VAD_PREFIX_PADDING_MS,
                "silence_duration_ms": voice_settings.VAD_SILENCE_DURATION_MS,
            },
        }
        
    async def _run_langgraph_workflow(self, user_message: str):
        """Run the LangGraph workflow with the user's message.
        
        Triggered by transcription completion events from Realtime API.
        """
        # Create state for LangGraph workflow
        state: VoiceAgentState = {
            "messages": [HumanMessage(content=user_message)],
            "claim_data": self.current_claim_data,
            "timestamp": datetime.now().isoformat(),
            "current_timezone": self.current_timezone,
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
                # Create a conversation item with the LangGraph-generated response
                await self.ws_manager.send({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "text", "text": response_message}]
                    },
                })
                
                # Trigger response generation for Realtime to speak it
                await self.ws_manager.send({
                    "type": "response.create",
                    "response": {
                        "tool_choice": "none"
                    }
                })
            
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
            await self.ws_manager.send({"type": "response.create"})
            
    async def _handle_websocket_event(self, event: Dict[str, Any]):
        """Handle incoming WebSocket events."""
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
            # Handle audio playback
            audio_b64 = event.get("delta", "") or event.get("audio", "")
            if audio_b64:
                audio_data = decode_audio(audio_b64)
                await self.audio_playback.add_audio(audio_data)
                
        elif event_type == "response.content_part.done":
            # Capture assistant transcript
            part = event.get("part", {})
            if part.get("type") == "audio" and part.get("transcript"):
                transcript = part["transcript"].strip()
                if transcript:
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
            await self.ws_manager.send({"type": "response.cancel"})
                    
        elif event_type == "conversation.item.input_audio_transcription.completed":
            # Capture user transcript and trigger LangGraph workflow
            transcript = event.get("transcript", "").strip()
            if transcript:
                print(f"[{get_timestamp()}] 👤 User: {transcript}")
                self.conversation_history.append({
                    "role": "user", 
                    "content": transcript,
                    "timestamp": get_timestamp()
                })
                
                # Trigger LangGraph workflow directly
                await self._run_langgraph_workflow(transcript)
            
    async def _audio_input_loop(self):
        """Stream microphone audio to WebSocket."""
        async for audio_chunk in self.audio_processor.stream_microphone():
            if not self._is_running:
                break
                
            await self.ws_manager.send({
                "type": "input_audio_buffer.append",
                "audio": encode_audio(audio_chunk),
            })
            
    async def _websocket_receive_loop(self):
        """Receive and handle WebSocket messages."""
        while self._is_running:
            try:
                event = await self.ws_manager.receive()
                await self._handle_websocket_event(event)
            except Exception as e:
                if self._is_running:
                    print(f"⚠️ WebSocket error: {e}")
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
