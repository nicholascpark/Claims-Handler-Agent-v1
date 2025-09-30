"""
FastAPI Backend Server for FNOL Voice Agent

This server provides WebSocket endpoints for:
1. Real-time voice conversation with OpenAI Realtime API
2. Live chat history updates
3. Dynamic JSON payload updates

The backend integrates the voice_langgraph agent and exposes it via WebSocket
for the frontend React application.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import base64

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import voice_langgraph components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from voice_langgraph.graph_builder import default_graph
from voice_langgraph.state import VoiceAgentState, ConversationMessage
from voice_langgraph.schema import PropertyClaim
from voice_langgraph.settings import voice_settings, validate_voice_settings
from voice_langgraph.prompts import Prompts
from voice_langgraph.utils import get_timestamp, WebSocketManager, encode_audio, decode_audio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="FNOL Voice Agent API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections
active_connections: Set[WebSocket] = set()


class VoiceSessionManager:
    """Manages a single voice agent session with WebSocket communication"""
    
    def __init__(self, client_ws: WebSocket):
        self.client_ws = client_ws
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.conversation_history: List[ConversationMessage] = []
        self.current_claim_data: Dict[str, Any] = {}
        self.current_timezone: str = "America/Toronto"
        self.is_active = False
        self.realtime_ws: Optional[WebSocketManager] = None
        self._greeting_sent = False
        
    def _build_ws_url(self) -> str:
        """Build WebSocket URL for Azure OpenAI Realtime API"""
        endpoint = voice_settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        api_version = voice_settings.AZURE_OPENAI_REALTIME_API_VERSION
        deployment = voice_settings.AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME
        
        https_url = f"{endpoint}/openai/realtime?api-version={api_version}&deployment={deployment}"
        return https_url.replace("https://", "wss://").replace("http://", "ws://")
    
    def _get_session_config(self) -> Dict[str, Any]:
        """Get Realtime API session configuration"""
        return {
            "modalities": ["text", "audio"],
            "instructions": Prompts.get_realtime_agent_instructions(),
            "voice": voice_settings.JUNIOR_AGENT_VOICE,
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
    
    async def send_to_client(self, event_type: str, data: Any):
        """Send event to frontend client"""
        try:
            await self.client_ws.send_json({
                "type": event_type,
                "data": data,
                "timestamp": get_timestamp()
            })
        except Exception as e:
            logger.error(f"Failed to send to client: {e}")
    
    async def run_langgraph_workflow(self, user_message: str):
        """Run LangGraph workflow with user's message"""
        state: VoiceAgentState = {
            "conversation_history": self.conversation_history,
            "current_user_message": user_message,
            "claim_data": self.current_claim_data,
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "current_timezone": self.current_timezone,
        }
        
        config = {"configurable": {"thread_id": self.session_id}}
        
        try:
            result = await default_graph.ainvoke(state, config)
            
            # Update claim data if changed
            if result.get("claim_data") != self.current_claim_data:
                self.current_claim_data = result["claim_data"]
                
                # Send updated JSON payload to client
                await self.send_to_client("claim_data_update", {
                    "claim_data": self.current_claim_data,
                    "is_complete": result.get("is_claim_complete", False)
                })
            
            # Get response message
            response_message = result.get("last_assistant_message", "I'm here to help with your claim.")
            
            # Send response to Realtime API if configured
            if not voice_settings.REALTIME_AS_TALKER and self.realtime_ws:
                await self.realtime_ws.send({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "input_text", "text": response_message}]
                    },
                })
                await self.realtime_ws.send({
                    "type": "response.create",
                    "response": {"tool_choice": "none"}
                })
            
            # Check if claim is complete
            if result.get("is_claim_complete"):
                submission_result = result.get("submission_result")
                await self.send_to_client("claim_complete", {
                    "claim_data": self.current_claim_data,
                    "submission_result": submission_result
                })
                
        except Exception as e:
            logger.error(f"Workflow error: {e}")
            # Send error to client
            await self.send_to_client("error", {"message": str(e)})
    
    async def handle_realtime_event(self, event: Dict[str, Any]):
        """Handle events from OpenAI Realtime API"""
        event_type = event.get("type", "")
        
        if event_type == "session.created":
            await self.realtime_ws.send({
                "type": "session.update",
                "session": self._get_session_config(),
            })
            
        elif event_type == "session.updated":
            if not self._greeting_sent:
                if voice_settings.REALTIME_AS_TALKER:
                    await self.realtime_ws.send({
                        "type": "response.create",
                        "response": {
                            "instructions": Prompts.get_realtime_agent_instructions() + "\n\nStart with the greeting immediately.",
                            "tool_choice": "none"
                        },
                    })
                self._greeting_sent = True
                await self.send_to_client("agent_ready", {"message": "Agent is listening"})
                
        elif event_type == "response.audio.delta":
            # Forward audio to client
            audio_b64 = event.get("delta", "") or event.get("audio", "")
            if audio_b64:
                await self.send_to_client("audio_delta", {"audio": audio_b64})
                
        elif event_type == "response.content_part.done":
            # Capture assistant transcript
            part = event.get("part", {})
            if part.get("type") == "audio" and part.get("transcript"):
                transcript = part["transcript"].strip()
                if transcript:
                    message = {
                        "role": "assistant",
                        "content": transcript,
                        "timestamp": get_timestamp()
                    }
                    self.conversation_history.append(message)
                    await self.send_to_client("chat_message", message)
                    
        elif event_type == "conversation.item.input_audio_transcription.completed":
            # Capture user transcript
            transcript = event.get("transcript", "").strip()
            if transcript:
                message = {
                    "role": "user",
                    "content": transcript,
                    "timestamp": get_timestamp()
                }
                self.conversation_history.append(message)
                await self.send_to_client("chat_message", message)
                
                # Trigger LangGraph workflow
                await self.run_langgraph_workflow(transcript)
    
    async def start_realtime_connection(self):
        """Start connection to OpenAI Realtime API"""
        ws_url = self._build_ws_url()
        self.realtime_ws = WebSocketManager(ws_url, voice_settings.AZURE_OPENAI_API_KEY)
        
        try:
            await self.realtime_ws.connect()
            self.is_active = True
            
            # Start receiving from Realtime API
            while self.is_active:
                try:
                    event = await self.realtime_ws.receive()
                    await self.handle_realtime_event(event)
                except Exception as e:
                    if self.is_active:
                        logger.error(f"Realtime API error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Failed to connect to Realtime API: {e}")
            await self.send_to_client("error", {"message": f"Connection failed: {e}"})
        finally:
            self.is_active = False
            if self.realtime_ws:
                await self.realtime_ws.close()
    
    async def handle_client_message(self, message: Dict[str, Any]):
        """Handle messages from frontend client"""
        msg_type = message.get("type", "")
        
        if msg_type == "audio_data":
            # Forward audio to Realtime API
            if self.realtime_ws:
                audio_b64 = message.get("audio", "")
                await self.realtime_ws.send({
                    "type": "input_audio_buffer.append",
                    "audio": audio_b64,
                })
        
        elif msg_type == "start_session":
            # Start Realtime API connection
            await self.start_realtime_connection()
        
        elif msg_type == "stop_session":
            # Stop session
            self.is_active = False


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "FNOL Voice Agent API"}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        validate_voice_settings()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "langgraph": "available",
                "voice_settings": "configured"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for voice agent communication"""
    await websocket.accept()
    active_connections.add(websocket)
    
    session = VoiceSessionManager(websocket)
    
    try:
        logger.info(f"New voice session started: {session.session_id}")
        
        # Send initial connection acknowledgment
        await session.send_to_client("connected", {
            "session_id": session.session_id,
            "message": "Connected to FNOL Voice Agent"
        })
        
        # Create tasks for bidirectional communication
        async def receive_from_client():
            """Receive messages from frontend"""
            try:
                while True:
                    data = await websocket.receive_json()
                    await session.handle_client_message(data)
            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {session.session_id}")
            except Exception as e:
                logger.error(f"Client receive error: {e}")
        
        # Run both tasks concurrently
        await receive_from_client()
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session.session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        session.is_active = False
        active_connections.discard(websocket)


@app.get("/api/session/{session_id}")
async def get_session_data(session_id: str):
    """Get session data (for debugging/monitoring)"""
    # In production, you'd retrieve this from a database or cache
    return {
        "session_id": session_id,
        "status": "active",
        "message": "Session data endpoint (implement with persistent storage)"
    }


if __name__ == "__main__":
    # Validate settings before starting
    try:
        validate_voice_settings()
        logger.info("✅ Voice settings validated")
    except Exception as e:
        logger.error(f"❌ Settings validation failed: {e}")
        exit(1)
    
    # Start server
    logger.info("🚀 Starting FNOL Voice Agent Backend Server")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
