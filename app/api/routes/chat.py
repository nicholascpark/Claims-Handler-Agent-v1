"""Chat API endpoints."""

import uuid
import base64
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.agents import create_agent
from app.services.voice import transcribe_audio, synthesize_speech
from app.services.persistence import save_conversation, load_conversation, delete_conversation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ===========================================
# Request/Response Models
# ===========================================

class ChatMessage(BaseModel):
    """Single chat message."""
    role: str
    content: str
    timestamp: Optional[str] = None
    is_voice: bool = False


class StartRequest(BaseModel):
    """Request to start a conversation."""
    thread_id: Optional[str] = None
    language: Optional[str] = Field(default="en", description="Language code")


class MessageRequest(BaseModel):
    """Request to send a text message."""
    message: str
    thread_id: str
    language: Optional[str] = None


class VoiceRequest(BaseModel):
    """Request to send a voice message."""
    audio_data: str  # base64 encoded
    thread_id: str
    language: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from chat endpoints."""
    message: str
    chat_history: List[ChatMessage]
    payload: Dict[str, Any]
    is_form_complete: bool
    thread_id: str
    audio_data: Optional[str] = None  # base64 encoded TTS response
    language: str = "en"
    processing_time: Optional[float] = None


# ===========================================
# Session Management
# ===========================================

# In-memory session storage (for production, use Redis or database)
_sessions: Dict[str, Dict[str, Any]] = {}


def get_or_create_session(thread_id: Optional[str] = None, language: str = "en") -> tuple[str, Dict[str, Any]]:
    """Get existing session or create new one."""
    if not thread_id:
        thread_id = str(uuid.uuid4())
    
    if thread_id not in _sessions:
        _sessions[thread_id] = {
            "thread_id": thread_id,
            "created_at": datetime.now().isoformat(),
            "chat_history": [],
            "payload": {},
            "is_form_complete": False,
            "language": language
        }
        logger.info(f"Created new session: {thread_id}")
    
    return thread_id, _sessions[thread_id]


def update_session(thread_id: str, updates: Dict[str, Any]) -> None:
    """Update session data."""
    if thread_id in _sessions:
        _sessions[thread_id].update(updates)
        _sessions[thread_id]["updated_at"] = datetime.now().isoformat()


# ===========================================
# Endpoints
# ===========================================

@router.post("/start", response_model=ChatResponse)
async def start_conversation(request: StartRequest = None):
    """Start a new conversation and get initial AI message."""
    import time
    start_time = time.time()
    
    if request is None:
        request = StartRequest()
    
    language = request.language or settings.default_language
    thread_id, session = get_or_create_session(request.thread_id, language)
    
    try:
        # Get agent
        agent = create_agent(language=language)
        
        # Process initial greeting
        result = await agent.process_message(
            message="",
            thread_id=thread_id,
            is_conversation_start=True
        )
        
        # Get response text
        response_text = result.get("response", "Hello! I'm here to help you file your insurance claim.")
        
        # Generate TTS audio
        audio_data = None
        try:
            audio_bytes = await synthesize_speech(response_text)
            audio_data = base64.b64encode(audio_bytes).decode()
        except Exception as e:
            logger.warning(f"TTS failed: {e}")
        
        # Update session
        assistant_message = ChatMessage(
            role="assistant",
            content=response_text,
            timestamp=datetime.now().isoformat()
        )
        session["chat_history"].append(assistant_message.model_dump())
        session["payload"] = result.get("payload", {})
        if hasattr(session["payload"], "model_dump"):
            session["payload"] = session["payload"].model_dump()
        session["is_form_complete"] = result.get("is_form_complete", False)
        
        processing_time = time.time() - start_time
        
        return ChatResponse(
            message=response_text,
            chat_history=session["chat_history"],
            payload=session["payload"],
            is_form_complete=session["is_form_complete"],
            thread_id=thread_id,
            audio_data=audio_data,
            language=language,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Failed to start conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=ChatResponse)
async def send_message(request: MessageRequest):
    """Send a text message and get AI response."""
    import time
    start_time = time.time()
    
    thread_id, session = get_or_create_session(request.thread_id)
    language = request.language or session.get("language", "en")
    
    try:
        # Add user message to history
        user_message = ChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.now().isoformat()
        )
        session["chat_history"].append(user_message.model_dump())
        
        # Get agent response
        agent = create_agent(language=language)
        result = await agent.process_message(
            message=request.message,
            thread_id=thread_id,
            is_conversation_start=False
        )
        
        response_text = result.get("response", "")
        
        # Generate TTS audio
        audio_data = None
        if response_text:
            try:
                audio_bytes = await synthesize_speech(response_text)
                audio_data = base64.b64encode(audio_bytes).decode()
            except Exception as e:
                logger.warning(f"TTS failed: {e}")
        
        # Add assistant message to history
        assistant_message = ChatMessage(
            role="assistant",
            content=response_text,
            timestamp=datetime.now().isoformat()
        )
        session["chat_history"].append(assistant_message.model_dump())
        
        # Update session
        payload = result.get("payload", session.get("payload", {}))
        if hasattr(payload, "model_dump"):
            payload = payload.model_dump()
        session["payload"] = payload
        session["is_form_complete"] = result.get("is_form_complete", False)
        
        processing_time = time.time() - start_time
        
        return ChatResponse(
            message=response_text,
            chat_history=session["chat_history"],
            payload=session["payload"],
            is_form_complete=session["is_form_complete"],
            thread_id=thread_id,
            audio_data=audio_data,
            language=language,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Failed to process message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice", response_model=ChatResponse)
async def send_voice_message(request: VoiceRequest):
    """Send a voice message and get AI response with audio."""
    import time
    start_time = time.time()
    
    thread_id, session = get_or_create_session(request.thread_id)
    language = request.language or session.get("language", "en")
    
    try:
        # Decode audio
        audio_bytes = base64.b64decode(request.audio_data)
        logger.info(f"Received audio: {len(audio_bytes)} bytes")
        
        # Transcribe audio
        transcribed_text = await transcribe_audio(audio_bytes, language=language)
        logger.info(f"Transcribed: {transcribed_text}")
        
        if not transcribed_text:
            raise HTTPException(status_code=400, detail="No speech detected in audio")
        
        # Add user message to history (with voice indicator)
        user_message = ChatMessage(
            role="user",
            content=transcribed_text,
            timestamp=datetime.now().isoformat(),
            is_voice=True
        )
        session["chat_history"].append(user_message.model_dump())
        
        # Get agent response
        agent = create_agent(language=language)
        result = await agent.process_message(
            message=transcribed_text,
            thread_id=thread_id,
            is_conversation_start=False
        )
        
        response_text = result.get("response", "")
        
        # Generate TTS audio
        audio_data = None
        if response_text:
            try:
                audio_bytes = await synthesize_speech(response_text)
                audio_data = base64.b64encode(audio_bytes).decode()
            except Exception as e:
                logger.warning(f"TTS failed: {e}")
        
        # Add assistant message to history
        assistant_message = ChatMessage(
            role="assistant",
            content=response_text,
            timestamp=datetime.now().isoformat()
        )
        session["chat_history"].append(assistant_message.model_dump())
        
        # Update session
        payload = result.get("payload", session.get("payload", {}))
        if hasattr(payload, "model_dump"):
            payload = payload.model_dump()
        session["payload"] = payload
        session["is_form_complete"] = result.get("is_form_complete", False)
        
        processing_time = time.time() - start_time
        
        return ChatResponse(
            message=response_text,
            chat_history=session["chat_history"],
            payload=session["payload"],
            is_form_complete=session["is_form_complete"],
            thread_id=thread_id,
            audio_data=audio_data,
            language=language,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process voice message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{thread_id}/payload")
async def get_payload(thread_id: str):
    """Get current payload for a thread."""
    if thread_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[thread_id]
    return {
        "payload": session.get("payload", {}),
        "is_form_complete": session.get("is_form_complete", False)
    }


@router.get("/{thread_id}/history")
async def get_history(thread_id: str):
    """Get conversation history for a thread."""
    if thread_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[thread_id]
    return {
        "thread_id": thread_id,
        "chat_history": session.get("chat_history", []),
        "language": session.get("language", "en")
    }


@router.delete("/{thread_id}")
async def reset_conversation(thread_id: str):
    """Reset/delete a conversation."""
    if thread_id in _sessions:
        del _sessions[thread_id]
        logger.info(f"Deleted session: {thread_id}")
    
    return {"message": "Conversation reset successfully"}


@router.get("/sessions/list")
async def list_sessions():
    """List all active sessions (for debugging)."""
    return {
        "count": len(_sessions),
        "sessions": [
            {
                "thread_id": tid,
                "created_at": s.get("created_at"),
                "message_count": len(s.get("chat_history", [])),
                "is_complete": s.get("is_form_complete", False)
            }
            for tid, s in _sessions.items()
        ]
    }
