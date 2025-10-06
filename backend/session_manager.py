"""Session Manager for Voice Agent

Manages individual user sessions, integrating the voice_langgraph agent
with WebSocket communication to the frontend.
"""

import asyncio
import base64
import json
import logging
from typing import Dict, Optional
from datetime import datetime
from uuid import uuid4

from fastapi import WebSocket
import sys
import os

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
from langchain_core.messages import HumanMessage, AIMessage

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
        
        # Control flags
        self._greeting_sent = False
        self._response_in_progress = False
        self._accept_audio_streaming = True
        
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
    
    async def handle_audio_data(self, audio_base64: str):
        """Handle incoming audio data from client."""
        if not self.is_active or not self.realtime_ws or not self._accept_audio_streaming:
            return
        
        try:
            # Forward audio to Realtime API
            await self.realtime_ws.send({
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            })
        except Exception as e:
            logger.error(f"[{self.session_id}] Error forwarding audio: {e}")
    
    async def handle_text_input(self, text: str):
        """Handle text input from client."""
        if not self.is_active or not self.realtime_ws:
            return
        
        try:
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
    
    async def handle_image_input(self, image_data: str, mime_type: str, name: str = None):
        """Handle image input from client."""
        if not self.is_active or not self.realtime_ws:
            return
        
        try:
            # Prepare image content for Realtime API
            # The Realtime API accepts images as base64 in the content array
            image_content = {
                "type": "input_image",
                "image": image_data,
                "mime_type": mime_type
            }
            
            # Send as conversation item with image
            await self.realtime_ws.send({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [image_content]
                }
            })
            
            logger.info(f"[{self.session_id}] Sent image: {name} ({mime_type})")
            
            # Add to conversation history
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
        except Exception as e:
            logger.error(f"[{self.session_id}] Error sending image: {e}")
    
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
                # Send greeting
                if not self._greeting_sent:
                    await self._send_greeting()
                    self._greeting_sent = True
            
            elif event_type == "response.audio.delta":
                # Forward audio to client
                audio_b64 = event.get("delta", "") or event.get("audio", "")
                if audio_b64:
                    await self.websocket.send_json({
                        "type": "audio_delta",
                        "data": {"audio": audio_b64}
                    })
            
            elif event_type == "response.audio_transcript.done":
                # Capture assistant transcript
                self._response_in_progress = False
                transcript = event.get("transcript", "")
                if transcript and isinstance(transcript, str):
                    transcript = transcript.strip()
                    if transcript:
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
            
            elif event_type == "input_audio_buffer.speech_started":
                # User started speaking
                await self.websocket.send_json({
                    "type": "user_speech_started",
                    "data": {}
                })
                
                # Cancel any ongoing response
                self._accept_audio_streaming = True
                await self.realtime_ws.send({"type": "response.cancel"})
            
            elif event_type == "input_audio_buffer.speech_stopped":
                # User stopped speaking
                await self.websocket.send_json({
                    "type": "user_speech_stopped",
                    "data": {}
                })
                self._accept_audio_streaming = False
            
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
                                    await self._process_user_message(transcript, source="voice", echo_user_to_frontend=True)
                                    break
                        elif content_part.get("type") in ["input_text", "text"]:
                            text = content_part.get("text")
                            if text and isinstance(text, str):
                                text = text.strip()
                                if text:
                                    # For typed input, process but do not echo back the user message
                                    await self._process_user_message(text, source="text", echo_user_to_frontend=False)
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
                            await self._process_user_message(transcript)
            
            elif event_type == "response.done":
                self._response_in_progress = False
                self._accept_audio_streaming = True
                
                # Notify frontend
                await self.websocket.send_json({
                    "type": "agent_ready",
                    "data": {}
                })
            
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
    
    async def _send_greeting(self):
        """Send initial greeting."""
        if self._response_in_progress:
            return
        
        self._response_in_progress = True
        # Pause mic streaming during TTS to prevent barge-in cancellation
        self._accept_audio_streaming = False
        # Let the model generate the greeting per system prompt; do not pre-create an assistant item
        await self.realtime_ws.send({
            "type": "response.create",
            "response": {"tool_choice": "none"}
        })
    
    async def _process_user_message(self, transcript: str, source: str = "voice", echo_user_to_frontend: bool = True):
        """Process user message through LangGraph workflow.
        
        source: 'voice' | 'text' determines how we record the user message.
        echo_user_to_frontend controls whether to send the user message back to the UI.
        """
        logger.info(f"[{self.session_id}] User ({source}): {transcript}")
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": transcript,
            "type": source,
            "timestamp": get_timestamp()
        })
        
        # Optionally echo to frontend (disabled for typed input to avoid duplicates)
        if echo_user_to_frontend:
            await self.websocket.send_json({
                "type": "chat_message",
                "data": {
                    "role": "user",
                    "content": transcript,
                    "type": source,
                    "timestamp": get_timestamp()
                }
            })
        
        # Run LangGraph workflow
        try:
            state: VoiceAgentState = {
                "messages": [HumanMessage(content=transcript)],
                "claim_data": self.current_claim_data,
                "timestamp": datetime.now().isoformat(),
                "current_timezone": self.current_timezone,
                "is_claim_complete": False,
                "escalation_requested": False,
                "retry_count": 0
            }
            
            config = {"configurable": {"thread_id": self.session_id}}
            
            result = await default_graph.ainvoke(state, config)
            
            # Update claim data
            if result.get("claim_data") != self.current_claim_data:
                self.current_claim_data = result["claim_data"]
                self.is_claim_complete = result.get("is_claim_complete", False)
                
                # Send claim data update to frontend
                await self.websocket.send_json({
                    "type": "claim_data_update",
                    "data": {
                        "claim_data": self.current_claim_data,
                        "is_complete": self.is_claim_complete
                    }
                })
            
            # Handle response
            response_message = None
            for m in reversed(result.get("messages", [])):
                if isinstance(m, AIMessage):
                    response_message = m.content
                    break
            
            if response_message and not self._response_in_progress:
                self._response_in_progress = True
                # Pause mic streaming while assistant speaks to avoid cancellation
                self._accept_audio_streaming = False
                
                # Send to Realtime API for speech
                await self.realtime_ws.send({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "text", "text": response_message}]
                    }
                })
                await self.realtime_ws.send({
                    "type": "response.create",
                    "response": {"tool_choice": "none"}
                })
            
            # Check if claim is complete
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
            
            # Send fallback response
            fallback = "I'm here to help with your claim. Could you please tell me what happened?"
            
            if not self._response_in_progress:
                self._response_in_progress = True
                await self.realtime_ws.send({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "text", "text": fallback}]
                    }
                })
                await self.realtime_ws.send({"type": "response.create"})


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


