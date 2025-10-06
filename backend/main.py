"""FastAPI Backend for Claims Handler Voice Agent

This backend integrates the voice_langgraph agent with a WebSocket interface
for real-time voice communication with the frontend.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global session manager
session_manager: Optional[SessionManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global session_manager
    
    # Startup
    logger.info("🚀 Starting Claims Handler Voice Agent Backend")
    session_manager = SessionManager()
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Claims Handler Voice Agent Backend")
    if session_manager:
        await session_manager.cleanup_all_sessions()


# Create FastAPI app
app = FastAPI(
    title="Claims Handler Voice Agent API",
    description="Real-time voice agent for insurance claim intake",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "Claims Handler Voice Agent",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "active_sessions": len(session_manager.active_sessions) if session_manager else 0,
        "timestamp": datetime.now().isoformat()
    }


@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for voice agent communication."""
    await websocket.accept()
    session_id = None
    
    try:
        # Create session
        session_id = await session_manager.create_session(websocket)
        logger.info(f"Session created: {session_id}")
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "data": {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
        })
        
        # Message loop
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_json()
                
                # Handle message
                await session_manager.handle_client_message(session_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {session_id}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from client: {e}")
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid message format"}
                })
            except Exception as e:
                logger.error(f"Error handling message: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": str(e)}
                })
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        # Cleanup session
        if session_id and session_manager:
            await session_manager.remove_session(session_id)
            logger.info(f"Session cleaned up: {session_id}")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


