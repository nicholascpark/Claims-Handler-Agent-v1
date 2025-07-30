import asyncio
import uuid
import base64
import tempfile
import os
from typing import Dict, Any, List, Optional, Tuple
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from io import BytesIO
from threading import Timer
import logging

# Import existing components
from src.builder import create_graph
from src.schema import example_json, FNOLPayload
from langchain_core.messages import SystemMessage, HumanMessage
from src.state import ConvoState
from src.voice import transcribe_audio_stream, synthesize_speech_stream

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

class VoiceRequest(BaseModel):
    audio_data: str  # base64 encoded audio
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    chat_history: List[ChatMessage]
    payload: Dict[str, Any]
    is_form_complete: bool
    thread_id: str
    audio_data: Optional[str] = None  # base64 encoded response audio

# Session cleanup configuration
SESSION_TIMEOUT_MINUTES = 30
CLEANUP_INTERVAL_MINUTES = 10

# FastAPI app
app = FastAPI(title="IntactBot FNOL Agent API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SessionData:
    """Enhanced session data with timestamp for cleanup"""
    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self.config = {"configurable": {"thread_id": thread_id}}
        self.payload = FNOLPayload(claim=example_json)
        self.is_form_complete = False
        self.process_complete = False
        self.api_retry_count = 0
        self.api_call_successful = False
        self.chat_history = []
        self.last_accessed = asyncio.get_event_loop().time()
    
    def update_access_time(self):
        """Update last accessed timestamp"""
        self.last_accessed = asyncio.get_event_loop().time()

class AgentSession:
    """Optimized session management with automatic cleanup"""
    def __init__(self):
        self.graph = create_graph()
        self.sessions: Dict[str, SessionData] = {}
        self.cleanup_timer = None
        self._start_cleanup_timer()
    
    def _start_cleanup_timer(self):
        """Start periodic session cleanup"""
        if self.cleanup_timer:
            self.cleanup_timer.cancel()
        
        def cleanup_sessions():
            self._cleanup_expired_sessions()
            self._start_cleanup_timer()  # Schedule next cleanup
        
        # Schedule cleanup every CLEANUP_INTERVAL_MINUTES
        self.cleanup_timer = Timer(CLEANUP_INTERVAL_MINUTES * 60, cleanup_sessions)
        self.cleanup_timer.start()
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions to prevent memory leaks"""
        current_time = asyncio.get_event_loop().time()
        timeout_seconds = SESSION_TIMEOUT_MINUTES * 60
        
        expired_sessions = [
            thread_id for thread_id, session in self.sessions.items()
            if current_time - session.last_accessed > timeout_seconds
        ]
        
        for thread_id in expired_sessions:
            del self.sessions[thread_id]
            logger.info(f"Cleaned up expired session: {thread_id}")
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_or_create_session(self, thread_id: Optional[str] = None) -> Tuple[str, SessionData]:
        """Get existing session or create new one with optimized structure"""
        if not thread_id:
            thread_id = str(uuid.uuid4())
        
        if thread_id not in self.sessions:
            self.sessions[thread_id] = SessionData(thread_id)
            logger.info(f"Created new session: {thread_id}")
        else:
            self.sessions[thread_id].update_access_time()
        
        return thread_id, self.sessions[thread_id]
    
    def format_payload(self, payload) -> Dict[str, Any]:
        """Optimized payload formatting with caching"""
        try:
            if payload:
                if hasattr(payload, 'model_dump'):
                    return payload.model_dump()
                elif isinstance(payload, dict):
                    return payload
                else:
                    return {"data": str(payload)}
            return {}
        except Exception as e:
            logger.error(f"Error formatting payload: {e}")
            return {"error": f"Error formatting payload: {str(e)}"}
    
    def cleanup(self):
        """Cleanup resources on shutdown"""
        if self.cleanup_timer:
            self.cleanup_timer.cancel()
        self.sessions.clear()

# Initialize agent session
agent_session = AgentSession()

async def process_agent_message(
    message: str, 
    session: SessionData, 
    is_conversation_start: bool = False
) -> Tuple[str, Dict[str, Any], bool]:
    """
    Unified message processing function to eliminate code duplication.
    Returns (agent_response, updated_payload, is_form_complete)
    """
    try:
        # Create appropriate message based on context
        if is_conversation_start:
            initial_message = HumanMessage(content="[CONVERSATION_START]")
        else:
            initial_message = HumanMessage(content=message)
        
        # Create state for processing
        initial_state: ConvoState = {
            "messages": [initial_message],
            "payload": session.payload,
            "is_form_complete": session.is_form_complete,
            "process_complete": session.process_complete,
            "api_retry_count": session.api_retry_count,
            "api_call_successful": session.api_call_successful,
        }
        
        # Process through graph
        events = agent_session.graph.astream(
            initial_state, 
            session.config, 
            stream_mode="values"
        )
        
        agent_response = ""
        final_event = None
        
        async for event in events:
            final_event = event
            if "messages" in event and event["messages"]:
                last_message = event["messages"][-1]
                if hasattr(last_message, 'content') and last_message.content.strip():
                    # For conversation start, ensure we don't return the trigger message
                    if not is_conversation_start or last_message.content != "[CONVERSATION_START]":
                        agent_response = last_message.content
        
        # Update session with final state
        if final_event:
            if "payload" in final_event and final_event["payload"]:
                session.payload = final_event["payload"]
            
            if "is_form_complete" in final_event:
                session.is_form_complete = final_event["is_form_complete"]
            
            if "process_complete" in final_event:
                session.process_complete = final_event["process_complete"]
            
            if "api_call_successful" in final_event:
                session.api_call_successful = final_event["api_call_successful"]
        
        # Handle conversation start fallback
        if is_conversation_start and (not agent_response or agent_response == "[CONVERSATION_START]"):
            agent_response = "Welcome to the automated First Notice of Loss system. I'm here to help you report your loss. To begin, please tell me what happened."
        
        # Fallback for empty responses
        if not agent_response:
            agent_response = "I'm processing your request..."
        
        return agent_response, session.payload, session.is_form_complete
        
    except Exception as e:
        logger.error(f"Error processing agent message: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

async def generate_audio_response(text: str) -> Optional[str]:
    """
    Generate audio response with error handling and optimization.
    Returns base64 encoded audio or None if generation fails.
    """
    try:
        audio_response = await synthesize_speech_stream(text)
        if audio_response:
            return base64.b64encode(audio_response).decode()
        return None
    except Exception as e:
        logger.warning(f"Failed to generate speech response: {e}")
        return None

def create_chat_response(
    agent_response: str,
    session: SessionData,
    thread_id: str,
    audio_data: Optional[str] = None,
    user_message: Optional[str] = None
) -> ChatResponse:
    """Create standardized chat response"""
    # Update chat history if user message provided
    if user_message:
        session.chat_history.append({"role": "user", "content": user_message})
    
    # Add agent response to history
    session.chat_history.append({"role": "assistant", "content": agent_response})
    
    return ChatResponse(
        message=agent_response,
        chat_history=session.chat_history,
        payload=agent_session.format_payload(session.payload),
        is_form_complete=session.is_form_complete,
        thread_id=thread_id,
        audio_data=audio_data
    )

@app.get("/")
async def root():
    return {"message": "IntactBot FNOL Agent API is running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "intactbot-fnol-agent",
        "active_sessions": len(agent_session.sessions)
    }

@app.post("/api/chat/start", response_model=ChatResponse)
async def start_conversation(thread_id: Optional[str] = None):
    """Start a new conversation and get the initial AI message"""
    thread_id, session = agent_session.get_or_create_session(thread_id)
    
    try:
        # Process initial conversation start
        agent_response, updated_payload, is_form_complete = await process_agent_message(
            "", session, is_conversation_start=True
        )
        
        # Generate audio response
        audio_data = await generate_audio_response(agent_response)
        
        # Create and return response
        return create_chat_response(agent_response, session, thread_id, audio_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting conversation: {str(e)}")

@app.post("/api/chat/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a text message to the agent"""
    thread_id, session = agent_session.get_or_create_session(request.thread_id)
    
    try:
        # Process message
        agent_response, updated_payload, is_form_complete = await process_agent_message(
            request.message, session
        )
        
        # Generate audio response
        audio_data = await generate_audio_response(agent_response)
        
        # Create and return response
        return create_chat_response(
            agent_response, session, thread_id, audio_data, request.message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.post("/api/chat/voice", response_model=ChatResponse)
async def send_voice_message(request: VoiceRequest):
    """Send a voice message to the agent"""
    thread_id, session = agent_session.get_or_create_session(request.thread_id)
    
    try:
        # Decode and validate audio data
        try:
            audio_bytes = base64.b64decode(request.audio_data)
            logger.info(f"Decoded audio data: {len(audio_bytes)} bytes")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid audio data format: {str(e)}")
        
        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="No audio data received")
        
        # Transcribe audio
        try:
            logger.info(f"Transcribing audio ({len(audio_bytes)} bytes)...")
            user_input = await transcribe_audio_stream(audio_bytes)
            logger.info(f"Transcription successful: '{user_input}'")
        except ValueError as e:
            logger.error(f"Audio validation error: {e}")
            raise HTTPException(status_code=400, detail=f"Audio validation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise HTTPException(status_code=500, detail=f"Audio transcription failed: {str(e)}")
        
        # Process transcribed message
        agent_response, updated_payload, is_form_complete = await process_agent_message(
            user_input, session
        )
        
        # Generate audio response
        audio_data = await generate_audio_response(agent_response)
        
        # Create response with voice indicator in user message
        user_message_with_indicator = f"🎤 *{user_input}*"
        
        return create_chat_response(
            agent_response, session, thread_id, audio_data, user_message_with_indicator
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing voice message: {str(e)}")

@app.get("/api/chat/audio/{thread_id}")
async def get_audio_response(thread_id: str, text: str):
    """Generate audio response for given text"""
    try:
        audio_bytes = await synthesize_speech_stream(text)
        return StreamingResponse(
            BytesIO(audio_bytes),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=response.wav"}
        )
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating audio: {str(e)}")

@app.delete("/api/chat/{thread_id}")
async def reset_conversation(thread_id: str):
    """Reset/clear a conversation"""
    try:
        if thread_id in agent_session.sessions:
            del agent_session.sessions[thread_id]
            logger.info(f"Reset conversation for thread: {thread_id}")
        return {"message": "Conversation reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Error resetting conversation: {str(e)}")

@app.get("/api/chat/{thread_id}/payload")
async def get_payload(thread_id: str):
    """Get current payload for a thread"""
    try:
        _, session = agent_session.get_or_create_session(thread_id)
        return {
            "payload": agent_session.format_payload(session.payload),
            "is_form_complete": session.is_form_complete
        }
    except Exception as e:
        logger.error(f"Error getting payload: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting payload: {str(e)}")

# Graceful shutdown handler
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    logger.info("Shutting down, cleaning up resources...")
    agent_session.cleanup()

if __name__ == "__main__":
    logger.info("🚀 Starting IntactBot FNOL Agent Backend...")
    uvicorn.run(
        "backend:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    ) 