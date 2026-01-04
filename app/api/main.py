"""
FastAPI Application

Main entry point for the Kismet Voice Agent API.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import chat_router, health_router
from app.services.persistence import init_database

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Initialize database
    if settings.persistence_enabled:
        init_database()
        logger.info("Database initialized")
    
    # Validate configuration
    errors = settings.validate_config()
    if errors:
        for error in errors:
            logger.warning(f"Config warning: {error}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Multi-modal Voice AI Agent for Claims Intake",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )
    
    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    application.include_router(health_router)
    application.include_router(chat_router)
    
    logger.info(f"CORS origins: {settings.cors_origins_list}")
    
    return application


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=not settings.is_production,
        log_level="debug" if settings.debug else "info"
    )
