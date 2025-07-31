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
import json
import time
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

# Import existing components
from src.builder import create_graph
from src.schema import example_json, FNOLPayload
from langchain_core.messages import SystemMessage, HumanMessage
from src.state import ConvoState
from src.voice import transcribe_audio_stream, synthesize_speech_stream

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thread pool for parallel processing
THREAD_POOL = ThreadPoolExecutor(max_workers=4)

# Response cache for common queries (simple in-memory cache)
RESPONSE_CACHE = {}
CACHE_MAX_SIZE = 100
CACHE_TTL = 3600  # 1 hour

# Pydantic models for API
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    stream: Optional[bool] = False  # Enable streaming support

class QueuedChatRequest(BaseModel):
    messages: List[str]  # Array of messages for queue processing
    thread_id: Optional[str] = None
    stream: Optional[bool] = False

class VoiceRequest(BaseModel):
    audio_data: str  # base64 encoded audio
    thread_id: Optional[str] = None
    stream: Optional[bool] = False  # Enable streaming support

class ChatResponse(BaseModel):
    message: str
    chat_history: List[ChatMessage]
    payload: Dict[str, Any]
    is_form_complete: bool
    thread_id: str
    audio_data: Optional[str] = None  # base64 encoded response audio
    processing_time: Optional[float] = None  # Processing time in seconds
    cached: Optional[bool] = False  # Whether response was cached

class StreamingChatResponse(BaseModel):
    type: str  # 'partial', 'complete', 'audio', 'error'
    content: Optional[str] = None
    audio_data: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    is_form_complete: Optional[bool] = None
    processing_time: Optional[float] = None
    thread_id: Optional[str] = None

# Session cleanup configuration
SESSION_TIMEOUT_MINUTES = 30
CLEANUP_INTERVAL_MINUTES = 10

# FastAPI app
app = FastAPI(title="IntactBot FNOL Agent API", version="1.0.0")

# Enable CORS for React frontend
allowed_origins = [
    "http://localhost:3000", 
    "http://127.0.0.1:3000"
]

# Add production origins if environment variables are set
if os.getenv("FRONTEND_URL"):
    allowed_origins.append(os.getenv("FRONTEND_URL"))
if os.getenv("RENDER_EXTERNAL_URL"):
    allowed_origins.append(os.getenv("RENDER_EXTERNAL_URL"))

# Allow all origins for Render deployments (you can restrict this later)
if os.getenv("ENVIRONMENT") == "production":
    allowed_origins.append("https://*.onrender.com")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
        # Add caching for session-specific responses
        self.response_cache = {}
    
    def update_access_time(self):
        """Update last accessed timestamp"""
        self.last_accessed = asyncio.get_event_loop().time()

    def get_cache_key(self, message: str) -> str:
        """Generate cache key for message responses"""
        return f"{self.thread_id}:{hash(message + str(self.payload))}"

    def get_cached_response(self, message: str) -> Optional[Tuple[str, Dict[str, Any], bool]]:
        """Get cached response if available and not expired"""
        cache_key = self.get_cache_key(message)
        if cache_key in self.response_cache:
            response, timestamp = self.response_cache[cache_key]
            if time.time() - timestamp < CACHE_TTL:
                return response
            else:
                # Remove expired cache entry
                del self.response_cache[cache_key]
        return None

    def cache_response(self, message: str, response: Tuple[str, Dict[str, Any], bool]):
        """Cache response for future use"""
        cache_key = self.get_cache_key(message)
        self.response_cache[cache_key] = (response, time.time())
        
        # Simple LRU: remove oldest entries if cache is full
        if len(self.response_cache) > CACHE_MAX_SIZE:
            oldest_key = min(self.response_cache.keys(), 
                           key=lambda k: self.response_cache[k][1])
            del self.response_cache[oldest_key]

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

async def process_queued_messages_optimized(
    messages: List[str], 
    session: SessionData
) -> Tuple[str, Dict[str, Any], bool, bool]:
    """
    Process multiple queued messages and generate a single contextual response.
    Returns (agent_response, updated_payload, is_form_complete, was_cached)
    """
    start_time = time.time()
    
    if not messages:
        raise ValueError("No messages provided for processing")
    
    # Create cache key for the entire message sequence
    combined_message = " | ".join(messages)
    cache_key = f"queue:{session.get_cache_key(combined_message)}"
    
    # Check cache for the entire sequence
    cached_response = session.get_cached_response(combined_message)
    if cached_response:
        logger.info(f"Cache hit for queued messages: {len(messages)} messages")
        return cached_response[0], cached_response[1], cached_response[2], True
    
    try:
        # Create a contextual message that combines all queued messages
        if len(messages) == 1:
            contextual_message = messages[0]
        else:
            contextual_message = f"I have {len(messages)} messages to address:\n"
            for i, msg in enumerate(messages, 1):
                contextual_message += f"{i}. {msg}\n"
            contextual_message += "\nPlease provide a comprehensive response that addresses all of these points."
        
        # Process through the standard agent pipeline
        initial_message = HumanMessage(content=contextual_message)
        
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
        
        # Fallback for empty responses
        if not agent_response:
            agent_response = f"I've reviewed all {len(messages)} of your messages and I'm processing your requests..."
        
        response_tuple = (agent_response, session.payload, session.is_form_complete)
        
        # Cache response for future use
        session.cache_response(combined_message, response_tuple)
        
        processing_time = time.time() - start_time
        logger.info(f"Queued messages processed in {processing_time:.2f}s")
        
        return agent_response, session.payload, session.is_form_complete, False
        
    except Exception as e:
        logger.error(f"Error processing queued messages: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing messages: {str(e)}")

async def process_agent_message_optimized(
    message: str, 
    session: SessionData, 
    is_conversation_start: bool = False
) -> Tuple[str, Dict[str, Any], bool, bool]:
    """
    Optimized message processing with caching and parallel execution.
    Returns (agent_response, updated_payload, is_form_complete, was_cached)
    """
    start_time = time.time()
    
    # Check cache first for non-conversation-start messages
    if not is_conversation_start:
        cached_response = session.get_cached_response(message)
        if cached_response:
            logger.info(f"Cache hit for message: {message[:50]}...")
            return cached_response[0], cached_response[1], cached_response[2], True
    
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
        
        response_tuple = (agent_response, session.payload, session.is_form_complete)
        
        # Cache response for future use (but not conversation start)
        if not is_conversation_start:
            session.cache_response(message, response_tuple)
        
        processing_time = time.time() - start_time
        logger.info(f"Message processed in {processing_time:.2f}s")
        
        return agent_response, session.payload, session.is_form_complete, False
        
    except Exception as e:
        logger.error(f"Error processing agent message: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

async def generate_audio_response_parallel(text: str) -> Optional[str]:
    """
    Generate audio response with parallel execution and caching.
    Returns base64 encoded audio or None if generation fails.
    """
    try:
        # Check global cache first
        audio_cache_key = f"audio:{hash(text)}"
        if audio_cache_key in RESPONSE_CACHE:
            cache_entry, timestamp = RESPONSE_CACHE[audio_cache_key]
            if time.time() - timestamp < CACHE_TTL:
                logger.info("Audio cache hit")
                return cache_entry
        
        # Run audio synthesis in thread pool for better performance
        loop = asyncio.get_event_loop()
        audio_response = await loop.run_in_executor(
            THREAD_POOL, 
            lambda: asyncio.run(synthesize_speech_stream(text))
        )
        
        if audio_response:
            encoded_audio = base64.b64encode(audio_response).decode()
            
            # Cache the result
            RESPONSE_CACHE[audio_cache_key] = (encoded_audio, time.time())
            
            # Simple cache cleanup
            if len(RESPONSE_CACHE) > CACHE_MAX_SIZE:
                oldest_key = min(RESPONSE_CACHE.keys(), 
                               key=lambda k: RESPONSE_CACHE[k][1])
                del RESPONSE_CACHE[oldest_key]
            
            return encoded_audio
        return None
    except Exception as e:
        logger.warning(f"Failed to generate speech response: {e}")
        return None

def create_chat_response_optimized(
    agent_response: str,
    session: SessionData,
    thread_id: str,
    audio_data: Optional[str] = None,
    user_message: Optional[str] = None,
    user_messages: Optional[List[str]] = None,
    processing_time: Optional[float] = None,
    cached: bool = False
) -> ChatResponse:
    """Create standardized chat response with performance metrics"""
    # Update chat history with user message(s)
    if user_messages:
        # Add multiple user messages as separate entries
        for message in user_messages:
            session.chat_history.append({"role": "user", "content": message})
    elif user_message:
        # Add single user message
        session.chat_history.append({"role": "user", "content": user_message})
    
    # Add agent response to history
    session.chat_history.append({"role": "assistant", "content": agent_response})
    
    return ChatResponse(
        message=agent_response,
        chat_history=session.chat_history,
        payload=agent_session.format_payload(session.payload),
        is_form_complete=session.is_form_complete,
        thread_id=thread_id,
        audio_data=audio_data,
        processing_time=processing_time,
        cached=cached
    )

@app.get("/")
async def root():
    return {"message": "IntactBot FNOL Agent API is running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "intactbot-fnol-agent",
        "active_sessions": len(agent_session.sessions),
        "cache_size": len(RESPONSE_CACHE)
    }

@app.post("/api/chat/start", response_model=ChatResponse)
async def start_conversation(thread_id: Optional[str] = None):
    """Start a new conversation and get the initial AI message"""
    start_time = time.time()
    thread_id, session = agent_session.get_or_create_session(thread_id)
    
    try:
        # Process initial conversation start with parallel audio generation
        agent_response, updated_payload, is_form_complete, was_cached = await process_agent_message_optimized(
            "", session, is_conversation_start=True
        )
        
        # Start audio generation in parallel (don't await immediately)
        audio_task = asyncio.create_task(generate_audio_response_parallel(agent_response))
        
        # Create response immediately with processing time
        processing_time = time.time() - start_time
        
        # Now await audio generation
        audio_data = await audio_task
        
        # Create and return response
        return create_chat_response_optimized(
            agent_response, session, thread_id, audio_data, 
            processing_time=processing_time, cached=was_cached
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting conversation: {str(e)}")

@app.post("/api/chat/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a text message to the agent with optimized processing"""
    start_time = time.time()
    thread_id, session = agent_session.get_or_create_session(request.thread_id)
    
    try:
        # Process message with optimizations
        agent_response, updated_payload, is_form_complete, was_cached = await process_agent_message_optimized(
            request.message, session
        )
        
        # Start audio generation in parallel
        audio_task = asyncio.create_task(generate_audio_response_parallel(agent_response))
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Await audio generation
        audio_data = await audio_task
        
        # Create and return response
        return create_chat_response_optimized(
            agent_response, session, thread_id, audio_data, request.message,
            processing_time=processing_time, cached=was_cached
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.post("/api/chat/queue", response_model=ChatResponse)
async def send_queued_messages(request: QueuedChatRequest):
    """Process multiple queued messages and generate a single contextual response"""
    start_time = time.time()
    thread_id, session = agent_session.get_or_create_session(request.thread_id)
    
    try:
        logger.info(f"Processing {len(request.messages)} queued messages for thread {thread_id}")
        
        # Process queued messages with optimizations
        agent_response, updated_payload, is_form_complete, was_cached = await process_queued_messages_optimized(
            request.messages, session
        )
        
        # Start audio generation in parallel
        audio_task = asyncio.create_task(generate_audio_response_parallel(agent_response))
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Await audio generation
        audio_data = await audio_task
        
        # Create and return response with individual user messages
        return create_chat_response_optimized(
            agent_response, session, thread_id, audio_data, 
            user_messages=request.messages,
            processing_time=processing_time, cached=was_cached
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing queued messages: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing queued messages: {str(e)}")

@app.post("/api/chat/voice", response_model=ChatResponse)
async def send_voice_message(request: VoiceRequest):
    """Send a voice message to the agent with parallel processing"""
    start_time = time.time()
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
        
        # Transcribe audio with parallel processing
        try:
            logger.info(f"Transcribing audio ({len(audio_bytes)} bytes)...")
            
            # Run transcription in thread pool for better performance
            loop = asyncio.get_event_loop()
            user_input = await loop.run_in_executor(
                THREAD_POOL,
                lambda: asyncio.run(transcribe_audio_stream(audio_bytes))
            )
            logger.info(f"Transcription successful: '{user_input}'")
        except ValueError as e:
            logger.error(f"Audio validation error: {e}")
            raise HTTPException(status_code=400, detail=f"Audio validation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise HTTPException(status_code=500, detail=f"Audio transcription failed: {str(e)}")
        
        # Process transcribed message with optimizations
        agent_response, updated_payload, is_form_complete, was_cached = await process_agent_message_optimized(
            user_input, session
        )
        
        # Start audio generation in parallel
        audio_task = asyncio.create_task(generate_audio_response_parallel(agent_response))
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Await audio generation
        audio_data = await audio_task
        
        # Create response with voice indicator in user message
        user_message_with_indicator = f"🎤 *{user_input}*"
        
        return create_chat_response_optimized(
            agent_response, session, thread_id, audio_data, user_message_with_indicator,
            processing_time=processing_time, cached=was_cached
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing voice message: {str(e)}")

@app.get("/api/chat/audio/{thread_id}")
async def get_audio_response(thread_id: str, text: str):
    """Generate audio response for given text with caching"""
    try:
        # Use the parallel audio generation with caching
        audio_data = await generate_audio_response_parallel(text)
        if audio_data:
            audio_bytes = base64.b64decode(audio_data)
            return StreamingResponse(
                BytesIO(audio_bytes),
                media_type="audio/wav",
                headers={"Content-Disposition": "attachment; filename=response.wav"}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate audio")
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

# New endpoints for performance monitoring
@app.get("/api/performance/stats")
async def get_performance_stats():
    """Get performance statistics"""
    return {
        "active_sessions": len(agent_session.sessions),
        "global_cache_size": len(RESPONSE_CACHE),
        "thread_pool_active": THREAD_POOL._threads,
        "cache_ttl": CACHE_TTL
    }

@app.post("/api/performance/clear-cache")
async def clear_cache():
    """Clear all caches for testing/debugging"""
    global RESPONSE_CACHE
    RESPONSE_CACHE.clear()
    
    # Clear session caches
    for session in agent_session.sessions.values():
        session.response_cache.clear()
    
    return {"message": "All caches cleared successfully"}

# Graceful shutdown handler
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    logger.info("Shutting down, cleaning up resources...")
    agent_session.cleanup()
    THREAD_POOL.shutdown(wait=True)

if __name__ == "__main__":
    logger.info("🚀 Starting IntactBot FNOL Agent Backend...")
    
    # Get host and port from environment variables for production
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Disable reload in production
    reload = environment == "development"
    
    uvicorn.run(
        "backend:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    ) 