"""
Settings API endpoints.

API key management and application settings.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.cost_tracker import estimate_conversation_cost, get_cost_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["Settings"])


# =============================================================================
# In-memory settings (for demo - in production use secure storage)
# =============================================================================

_runtime_settings = {
    "openai_api_key": None,  # Will be set via API
    "openai_api_key_valid": False,
}


# =============================================================================
# Request/Response Models
# =============================================================================

class APIKeyRequest(BaseModel):
    """Request to set API key."""
    api_key: str = Field(..., description="OpenAI API key", min_length=10)


class APIKeyStatus(BaseModel):
    """API key status response."""
    is_set: bool
    is_valid: bool
    masked_key: Optional[str] = None
    source: str  # "environment" or "runtime"


class CostEstimate(BaseModel):
    """Cost estimate response."""
    per_conversation: dict
    pricing_info: dict


# =============================================================================
# API Key Endpoints
# =============================================================================

@router.get("/api-key/status", response_model=APIKeyStatus)
async def get_api_key_status():
    """Check if API key is configured and valid."""
    
    # Check environment first
    env_key = os.environ.get("OPENAI_API_KEY") or settings.openai_api_key
    runtime_key = _runtime_settings.get("openai_api_key")
    
    if runtime_key:
        return APIKeyStatus(
            is_set=True,
            is_valid=_runtime_settings.get("openai_api_key_valid", False),
            masked_key=f"sk-...{runtime_key[-4:]}" if len(runtime_key) > 4 else "sk-...",
            source="runtime"
        )
    elif env_key:
        return APIKeyStatus(
            is_set=True,
            is_valid=True,  # Assume valid if set in env
            masked_key=f"sk-...{env_key[-4:]}" if len(env_key) > 4 else "sk-...",
            source="environment"
        )
    else:
        return APIKeyStatus(
            is_set=False,
            is_valid=False,
            masked_key=None,
            source="none"
        )


@router.post("/api-key")
async def set_api_key(request: APIKeyRequest):
    """Set the OpenAI API key at runtime."""
    
    # Basic validation
    if not request.api_key.startswith("sk-"):
        raise HTTPException(
            status_code=400, 
            detail="Invalid API key format. Key should start with 'sk-'"
        )
    
    # Test the key
    is_valid = await _test_api_key(request.api_key)
    
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="API key validation failed. Please check your key."
        )
    
    # Store in runtime settings
    _runtime_settings["openai_api_key"] = request.api_key
    _runtime_settings["openai_api_key_valid"] = True
    
    # Also set in environment for the current process
    os.environ["OPENAI_API_KEY"] = request.api_key
    
    logger.info("API key updated via runtime settings")
    
    return {
        "message": "API key set successfully",
        "masked_key": f"sk-...{request.api_key[-4:]}"
    }


@router.post("/api-key/test")
async def test_api_key(request: APIKeyRequest):
    """Test an API key without saving it."""
    
    if not request.api_key.startswith("sk-"):
        return {"valid": False, "error": "Invalid format"}
    
    is_valid = await _test_api_key(request.api_key)
    
    return {
        "valid": is_valid,
        "error": None if is_valid else "API key validation failed"
    }


@router.delete("/api-key")
async def clear_api_key():
    """Clear the runtime API key."""
    _runtime_settings["openai_api_key"] = None
    _runtime_settings["openai_api_key_valid"] = False
    
    return {"message": "Runtime API key cleared"}


# =============================================================================
# Cost Estimation Endpoints
# =============================================================================

@router.get("/cost-estimate")
async def get_cost_estimate(
    turns: int = 5,
    voice_enabled: bool = True,
):
    """
    Get estimated cost per conversation.
    
    Args:
        turns: Expected number of conversation turns
        voice_enabled: Whether voice (STT/TTS) is enabled
    """
    estimate = estimate_conversation_cost(
        turns=turns,
        avg_user_message_tokens=50 if not voice_enabled else 30,
        avg_assistant_tokens=100,
        audio_seconds_per_turn=10 if voice_enabled else 0,
        tts_chars_per_turn=200 if voice_enabled else 0,
    )
    
    return {
        "estimate": estimate,
        "disclaimer": "Actual costs may vary based on conversation length and complexity."
    }


@router.get("/cost-tracking")
async def get_cost_tracking():
    """Get current session cost tracking data."""
    tracker = get_cost_tracker()
    return tracker.get_aggregate_cost()


@router.get("/cost-tracking/{session_id}")
async def get_session_cost(session_id: str):
    """Get cost tracking for a specific session."""
    tracker = get_cost_tracker()
    return tracker.get_session_cost(session_id)


# =============================================================================
# Pricing Information
# =============================================================================

@router.get("/pricing")
async def get_pricing_info():
    """Get current OpenAI pricing information."""
    return {
        "last_updated": "2024-01-01",
        "disclaimer": "Prices are estimates and may change. Check OpenAI's pricing page for current rates.",
        "models": {
            "gpt-4o": {
                "input_per_1k_tokens": 0.005,
                "output_per_1k_tokens": 0.015,
                "description": "Most capable model, best for complex conversations"
            },
            "gpt-4o-mini": {
                "input_per_1k_tokens": 0.00015,
                "output_per_1k_tokens": 0.0006,
                "description": "Faster and cheaper, good for simpler tasks"
            },
        },
        "voice": {
            "whisper-1": {
                "per_minute": 0.006,
                "description": "Speech-to-text transcription"
            },
            "tts-1": {
                "per_1k_characters": 0.015,
                "description": "Standard text-to-speech"
            },
            "tts-1-hd": {
                "per_1k_characters": 0.030,
                "description": "High-definition text-to-speech"
            },
        },
        "typical_conversation": {
            "turns": 5,
            "estimated_cost_range": "$0.05 - $0.15",
            "note": "Voice-enabled conversations cost more due to STT/TTS"
        }
    }


# =============================================================================
# Helper Functions
# =============================================================================

async def _test_api_key(api_key: str) -> bool:
    """Test if an API key is valid by making a simple API call."""
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=api_key)
        
        # Make a minimal API call to test
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        
        return True
        
    except Exception as e:
        logger.warning(f"API key validation failed: {e}")
        return False


def get_active_api_key() -> Optional[str]:
    """Get the currently active API key."""
    runtime_key = _runtime_settings.get("openai_api_key")
    if runtime_key:
        return runtime_key
    
    return os.environ.get("OPENAI_API_KEY") or settings.openai_api_key
