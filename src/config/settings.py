"""Configuration settings for Claims Handler Agent v1"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Handle different pydantic versions
try:
    from pydantic import BaseSettings
except ImportError:
    from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_CHAT_API_VERSION: Optional[str] = None
    AZURE_OPENAI_CHAT_DEPLOYMENT_NAME: Optional[str] = None
    AZURE_OPENAI_REALTIME_API_VERSION: Optional[str] = None
    AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME: Optional[str] = None
    
    # Audio and Realtime API Settings
    AUDIO_FORMAT: str = "pcm16"
    SAMPLE_RATE: int = 24000
    AUDIO_CHANNELS: int = 1
    AUDIO_CHUNK_SIZE: int = 960  # ~40ms at 24kHz for smoother VAD

    # Transcription settings (use realtime-optimized model by default)
    TRANSCRIPTION_MODEL: str = "gpt-4o-mini-transcribe"
    TRANSCRIPTION_LANGUAGE: str = "en"
    TRANSCRIPTION_TEMPERATURE: float = 0.0

    # Voice Activity Detection (server-side VAD) defaults
    VAD_THRESHOLD: float = 0.55
    VAD_PREFIX_PADDING_MS: int = 400
    VAD_SILENCE_DURATION_MS: int = 1000

    # Local utterance gating thresholds (client-side guards)
    MIN_AVG_AMPLITUDE: int = 350  # mean |int16| amplitude threshold
    MIN_SPEECH_MS: int = 600      # minimum duration before commit
    
    # Agent Configuration
    JUNIOR_AGENT_VOICE: str = "sage"
    SUPERVISOR_TEMPERATURE: float = 0.7
    MAX_CONVERSATION_HISTORY: int = 50
    
    # Tool Configuration
    MAX_TOOL_RETRIES: int = 3
    TOOL_TIMEOUT: int = 30
    
    # Payload Processing
    PAYLOAD_PROCESSOR_ENDPOINT: Optional[str] = None
    MAX_PAYLOAD_SIZE: int = 10240  # 10KB
    
    # Conversation Flow (kept for compatibility; avoid any "checking" phrasing)
    FILLER_PHRASES: list = [
        "Thanks, I have that noted.",
        "Understood, thank you.",
        "Okay, got it.",
        "Thanks for confirming.",
        "I appreciate that."
    ]
    
    # Debug / Display
    DISPLAY_CLAIM_JSON: bool = False
    
    # LangSmith / Tracing
    LANGSMITH_PROJECT: Optional[str] = None
    LANGSMITH_ENDPOINT: Optional[str] = None
    LANGCHAIN_TRACING: Optional[str] = None
    LANGSMITH_API_KEY: Optional[str] = None

    # Company Information
    COMPANY_NAME: str = "Intact Specialty Insurance"
    COMPANY_GREETING: str = "Hi, you've reached Intact Specialty Insurance, how can I help you with your claim today?"
    
    # Timezone and temporal overrides
    TIMEZONE: str = "America/New_York"
    # Optional ISO string to fix "now" for demos/tests, e.g. "2025-09-25T15:00:00"
    FIXED_NOW_ISO: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from .env file


# Global settings instance
settings = Settings()


def validate_required_settings():
    """Validate that required settings are present"""
    required_settings = [
        ("AZURE_OPENAI_ENDPOINT", settings.AZURE_OPENAI_ENDPOINT),
        ("AZURE_OPENAI_API_KEY", settings.AZURE_OPENAI_API_KEY),
        ("AZURE_OPENAI_CHAT_API_VERSION", settings.AZURE_OPENAI_CHAT_API_VERSION),
        ("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME),
        ("AZURE_OPENAI_REALTIME_API_VERSION", settings.AZURE_OPENAI_REALTIME_API_VERSION),
        ("AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME", settings.AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME),
    ]
    
    missing_settings = [
        setting_name for setting_name, setting_value in required_settings
        if not setting_value
    ]
    
    if missing_settings:
        raise ValueError(f"Missing required settings: {', '.join(missing_settings)}")
    
    return True
