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
from fastapi.staticfiles import StaticFiles
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


@app.get("/api/status")
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


@app.get("/api/health")
async def health_api():
    """Detailed health check (API namespace)."""
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

"""Static frontend mount and resilient fallback.

We avoid raising 500s when the static directory doesn't exist. Instead,
we always mount StaticFiles with check_dir=False (which defers directory
checks) and provide a GET "/" route that either serves index.html when
present or returns a minimal HTML fallback.
"""

static_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

# Serve built asset files when present (Vite outputs to dist/assets)
assets_dir = os.path.join(static_dir, "assets")
app.mount("/assets", StaticFiles(directory=assets_dir, html=False, check_dir=False), name="assets")

# Serve root-level built files (copied from Vite public/) such as logo and worklets
app.mount("/static", StaticFiles(directory=static_dir, html=False, check_dir=False), name="static_root")

# Backwards-compatibility: serve logo at root path for favicon/header usage
from fastapi.responses import FileResponse, Response

@app.get("/intactbot_logo.png")
async def serve_logo():
    logo_path = os.path.join(static_dir, "intactbot_logo.png")
    if os.path.isfile(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    # Return 404 without stack traces
    return Response(status_code=404)

@app.get("/")
async def root_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        # Serve built frontend when available
        from fastapi.responses import FileResponse
        return FileResponse(index_path, media_type="text/html")
    # Minimal in-browser fallback to indicate service is up
    from fastapi.responses import HTMLResponse
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>Claims Handler Voice Agent</title>
          <style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:2rem;line-height:1.5}code{background:#f6f8fa;padding:.2rem .4rem;border-radius:4px}</style>
        </head>
        <body>
          <h1>Claims Handler Voice Agent</h1>
          <p>Status: <strong>online</strong></p>
          <p>Frontend build not found. Please deploy <code>frontend/dist</code> or enable build on startup.</p>
        </body>
        </html>
        """,
        status_code=200,
    )


