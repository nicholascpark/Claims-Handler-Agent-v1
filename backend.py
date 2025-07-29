import asyncio
import uuid
import base64
import tempfile
import os
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from io import BytesIO

# Import existing components
from src.builder import create_graph
from src.schema import example_json, FNOLPayload
from langchain_core.messages import SystemMessage, HumanMessage
from src.state import ConvoState
from src.voice import transcribe_audio_stream, synthesize_speech_stream

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

class VoiceResponse(BaseModel):
    message: str
    chat_history: List[ChatMessage]
    payload: Dict[str, Any]
    is_form_complete: bool
    thread_id: str
    audio_data: Optional[str] = None  # base64 encoded response audio

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

# Global state management
class AgentSession:
    def __init__(self):
        self.graph = create_graph()
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    def get_or_create_session(self, thread_id: Optional[str] = None) -> tuple[str, Dict[str, Any]]:
        if not thread_id:
            thread_id = str(uuid.uuid4())
        
        if thread_id not in self.sessions:
            self.sessions[thread_id] = {
                "config": {"configurable": {"thread_id": thread_id}},
                "payload": FNOLPayload(claim=example_json),
                "is_form_complete": False,
                "process_complete": False,
                "api_retry_count": 0,
                "api_call_successful": False,
                "chat_history": []
            }
        
        return thread_id, self.sessions[thread_id]
    
    def format_payload(self, payload) -> Dict[str, Any]:
        try:
            if payload:
                return payload.model_dump() if hasattr(payload, 'model_dump') else payload
            return {}
        except Exception as e:
            return {"error": f"Error formatting payload: {str(e)}"}

# Initialize agent session
agent_session = AgentSession()

@app.get("/")
async def root():
    return {"message": "IntactBot FNOL Agent API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "intactbot-fnol-agent"}

@app.post("/api/chat/start", response_model=ChatResponse)
async def start_conversation(thread_id: Optional[str] = None):
    """Start a new conversation and get the initial AI message"""
    thread_id, session = agent_session.get_or_create_session(thread_id)
    
    try:
        # Initialize with a proper trigger message to get the system prompt greeting
        # Use a message that clearly indicates this is the conversation start
        initial_human_message = HumanMessage(content="[CONVERSATION_START]")
        initial_state: ConvoState = {
            "messages": [initial_human_message],
            "payload": session["payload"],
            "is_form_complete": session["is_form_complete"],
            "process_complete": session.get("process_complete", False),
            "api_retry_count": session.get("api_retry_count", 0),
            "api_call_successful": session.get("api_call_successful", False),
        }
        
        events = agent_session.graph.astream(initial_state, session["config"], stream_mode="values")
        
        agent_response = ""
        final_event = None
        async for event in events:
            final_event = event
            if "messages" in event and event["messages"]:
                last_message = event["messages"][-1]
                if hasattr(last_message, 'content') and last_message.content.strip():
                    agent_response = last_message.content
        
        # Update session with final state from LangGraph
        if final_event:
            if "payload" in final_event and final_event["payload"]:
                session["payload"] = final_event["payload"]
            
            if "is_form_complete" in final_event:
                session["is_form_complete"] = final_event["is_form_complete"]
                
            if "process_complete" in final_event:
                session["process_complete"] = final_event["process_complete"]
                
            if "api_call_successful" in final_event:
                session["api_call_successful"] = final_event["api_call_successful"]
        
        # Ensure we have the proper greeting as specified in SYS_PROMPT
        if not agent_response or agent_response == "[CONVERSATION_START]":
            agent_response = "Welcome to the automated First Notice of Loss system. I'm here to help you report your loss. To begin, please tell me what happened."
        
        # Update chat history
        session["chat_history"] = [{"role": "assistant", "content": agent_response}]
        
        # Generate speech for response
        try:
            audio_response = await synthesize_speech_stream(agent_response)
            audio_data_b64 = base64.b64encode(audio_response).decode() if audio_response else None
        except Exception as e:
            print(f"Warning: Failed to generate speech response: {e}")
            audio_data_b64 = None
        
        return ChatResponse(
            message=agent_response,
            chat_history=session["chat_history"],
            payload=agent_session.format_payload(session["payload"]),
            is_form_complete=session["is_form_complete"],
            thread_id=thread_id,
            audio_data=audio_data_b64
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting conversation: {str(e)}")

@app.post("/api/chat/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a text message to the agent"""
    thread_id, session = agent_session.get_or_create_session(request.thread_id)
    
    try:
        # Add user message to history
        session["chat_history"].append({"role": "user", "content": request.message})
        
        # Create the state with current payload for TrustCall continuity
        initial_state = {
            "messages": [HumanMessage(content=request.message)],
            "payload": session["payload"],
            "is_form_complete": session["is_form_complete"],
            "process_complete": session.get("process_complete", False),
            "api_retry_count": session.get("api_retry_count", 0),
            "api_call_successful": session.get("api_call_successful", False),
        }
        
        # Process message through graph
        events = agent_session.graph.astream(
            initial_state, 
            session["config"], 
            stream_mode="values"
        )
        
        agent_response = ""
        final_event = None
        async for event in events:
            final_event = event
            if "messages" in event and event["messages"]:
                last_message = event["messages"][-1]
                if hasattr(last_message, 'content') and last_message.content != request.message:
                    agent_response = last_message.content
        
        # Update session with final state from LangGraph
        if final_event:
            if "payload" in final_event and final_event["payload"]:
                session["payload"] = final_event["payload"]
            
            if "is_form_complete" in final_event:
                session["is_form_complete"] = final_event["is_form_complete"]
        
        if not agent_response:
            agent_response = "I'm processing your request..."
        
        # Add agent response to history
        session["chat_history"].append({"role": "assistant", "content": agent_response})
        
        # Generate speech for response
        try:
            audio_response = await synthesize_speech_stream(agent_response)
            audio_data_b64 = base64.b64encode(audio_response).decode() if audio_response else None
        except Exception as e:
            print(f"Warning: Failed to generate speech response: {e}")
            audio_data_b64 = None
        
        return ChatResponse(
            message=agent_response,
            chat_history=session["chat_history"],
            payload=agent_session.format_payload(session["payload"]),
            is_form_complete=session["is_form_complete"],
            thread_id=thread_id,
            audio_data=audio_data_b64
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.post("/api/chat/voice", response_model=VoiceResponse)
async def send_voice_message(request: VoiceRequest):
    """Send a voice message to the agent"""
    thread_id, session = agent_session.get_or_create_session(request.thread_id)
    
    try:
        # Decode base64 audio data
        try:
            audio_bytes = base64.b64decode(request.audio_data)
            print(f"Decoded audio data: {len(audio_bytes)} bytes")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid audio data format: {str(e)}")
        
        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="No audio data received")
        
        # Transcribe audio with better error handling
        try:
            print(f"Attempting to transcribe audio ({len(audio_bytes)} bytes)...")
            user_input = await transcribe_audio_stream(audio_bytes)
            print(f"Transcription successful: '{user_input}'")
        except ValueError as e:
            # Handle specific audio validation errors
            print(f"Audio validation error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Audio validation failed: {str(e)}")
        except Exception as e:
            # Handle other transcription errors
            print(f"Transcription error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Audio transcription failed: {str(e)}")
        
        # Add user message to history (with voice indicator)
        session["chat_history"].append({"role": "user", "content": f"🎤 *{user_input}*"})
        
        # Create the state with current payload for TrustCall continuity
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "payload": session["payload"],
            "is_form_complete": session["is_form_complete"],
            "process_complete": session.get("process_complete", False),
            "api_retry_count": session.get("api_retry_count", 0),
            "api_call_successful": session.get("api_call_successful", False),
        }
        
        # Process message through graph
        events = agent_session.graph.astream(
            initial_state, 
            session["config"], 
            stream_mode="values"
        )
        
        agent_response = ""
        final_event = None
        async for event in events:
            final_event = event
            if "messages" in event and event["messages"]:
                last_message = event["messages"][-1]
                if hasattr(last_message, 'content') and last_message.content != user_input:
                    agent_response = last_message.content
        
        # Update session with final state from LangGraph
        if final_event:
            if "payload" in final_event and final_event["payload"]:
                session["payload"] = final_event["payload"]
            
            if "is_form_complete" in final_event:
                session["is_form_complete"] = final_event["is_form_complete"]
        
        if not agent_response:
            agent_response = "I'm processing your request..."
        
        # Add agent response to history
        session["chat_history"].append({"role": "assistant", "content": agent_response})
        
        # Generate speech for response
        try:
            audio_response = await synthesize_speech_stream(agent_response)
            audio_data_b64 = base64.b64encode(audio_response).decode() if audio_response else None
        except Exception as e:
            print(f"Warning: Failed to generate speech response: {e}")
            audio_data_b64 = None
        
        return VoiceResponse(
            message=agent_response,
            chat_history=session["chat_history"],
            payload=agent_session.format_payload(session["payload"]),
            is_form_complete=session["is_form_complete"],
            thread_id=thread_id,
            audio_data=audio_data_b64
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
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
        raise HTTPException(status_code=500, detail=f"Error generating audio: {str(e)}")

@app.delete("/api/chat/{thread_id}")
async def reset_conversation(thread_id: str):
    """Reset/clear a conversation"""
    try:
        if thread_id in agent_session.sessions:
            del agent_session.sessions[thread_id]
        return {"message": "Conversation reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting conversation: {str(e)}")

@app.get("/api/chat/{thread_id}/payload")
async def get_payload(thread_id: str):
    """Get current payload for a thread"""
    try:
        _, session = agent_session.get_or_create_session(thread_id)
        return {
            "payload": agent_session.format_payload(session["payload"]),
            "is_form_complete": session["is_form_complete"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting payload: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting IntactBot FNOL Agent Backend...")
    uvicorn.run(
        "backend:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    ) 