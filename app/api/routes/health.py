"""Health check endpoints."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"{settings.app_name} API is running",
        "version": settings.app_version
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }


@router.get("/config")
async def get_config():
    """Get public configuration (non-sensitive)."""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "supported_languages": settings.supported_languages_list,
        "default_language": settings.default_language,
        "tts_voice": settings.tts_voice,
        "has_api_key": bool(settings.openai_api_key)
    }
