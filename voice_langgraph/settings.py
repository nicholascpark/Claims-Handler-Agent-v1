"""Configuration settings for the Voice LangGraph Agent.

This module loads environment variables and provides configuration
for the voice agent including company-specific settings.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load environment variables from .env file in project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))


class VoiceAgentSettings(BaseSettings):
    """Settings for the Voice LangGraph Agent."""
    
    # Company Information
    COMPANY_NAME: str = Field(
        default="Intact Specialty Insurance",
        description="Name of the insurance company"
    )
    
    COMPANY_DEPARTMENT: str = Field(
        default="Claims Department", 
        description="Department name for the agent"
    )
    
    AGENT_NAME: str = Field(
        default="Kismet AI",
        description="Name of the voice agent"
    )
    
    # Voice and Audio Settings
    JUNIOR_AGENT_VOICE: str = Field(
        default="shimmer",
        description="Voice model for the agent (alloy, echo, fable, onyx, nova, shimmer)"
    )
    
    SAMPLE_RATE: int = Field(
        default=24000,
        description="Audio sample rate in Hz"
    )
    
    AUDIO_CHANNELS: int = Field(
        default=1,
        description="Number of audio channels"
    )
    
    AUDIO_CHUNK_SIZE: int = Field(
        default=1024,
        description="Audio chunk size for processing"
    )
    
    # VAD (Voice Activity Detection) Settings
    VAD_THRESHOLD: float = Field(
        default=0.5,
        description="Voice activity detection threshold"
    )
    
    VAD_PREFIX_PADDING_MS: int = Field(
        default=300,
        description="Padding before speech in milliseconds"
    )
    
    VAD_SILENCE_DURATION_MS: int = Field(
        default=1500,
        description="Silence duration to end speech in milliseconds (1.5 second debounce to prevent cut-off sentences)"
    )
    
    # Transcription Settings
    TRANSCRIPTION_MODEL: str = Field(
        default="whisper-1",
        description="Transcription model to use"
    )
    
    TRANSCRIPTION_LANGUAGE: str = Field(
        default="en",
        description="Language for transcription"
    )
    
    # Azure OpenAI Settings (from environment variables)
    # These MUST be set in .env file - no defaults provided for security
    AZURE_OPENAI_ENDPOINT: Optional[str] = Field(
        default=None,
        description="Azure OpenAI endpoint URL",
        env="AZURE_OPENAI_ENDPOINT"
    )
    
    AZURE_OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="Azure OpenAI API key",
        env="AZURE_OPENAI_API_KEY"
    )
    
    AZURE_OPENAI_CHAT_API_VERSION: str = Field(
        default="2024-08-01-preview",
        description="Azure OpenAI Chat API version",
        env="AZURE_OPENAI_CHAT_API_VERSION"
    )
    
    AZURE_OPENAI_CHAT_DEPLOYMENT_NAME: Optional[str] = Field(
        default=None,
        description="Azure OpenAI Chat deployment name",
        env="AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
    )
    
    AZURE_OPENAI_REALTIME_API_VERSION: str = Field(
        default="2024-10-01-preview",
        description="Azure OpenAI Realtime API version",
        env="AZURE_OPENAI_REALTIME_API_VERSION"
    )
    
    AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME: Optional[str] = Field(
        default=None,
        description="Azure OpenAI Realtime deployment name",
        env="AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME"
    )
    
    # Conversation Settings
    MAX_CONVERSATION_HISTORY: int = Field(
        default=50,
        description="Maximum number of conversation messages to keep"
    )
    
    # Display Settings
    DISPLAY_CLAIM_JSON: bool = Field(
        default=False,
        description="Whether to display claim JSON by default"
    )
    
    # Speech Orchestration
    REALTIME_AS_TALKER: bool = Field(
        default=True,
        description="If true, let the Realtime model speak autonomously for lowest latency. The workflow will not send assistant speech."
    )
    
    # Workflow Settings
    EXTRACTION_KEYWORDS: list[str] = Field(
        default=[
            "name is", "my name", "i'm", "i am",
            "phone", "number", "call me", "contact",
            "email", "@",
            "address", "located at", "street", "avenue", "live at",
            "damage", "broke", "broken", "flooded", "fire", "storm", "leak",
            "happened", "occurred", "yesterday", "today", "last week", "when",
            "water", "burst", "wind", "hail", "tornado", "hurricane",
            "roof", "ceiling", "basement", "kitchen", "bathroom", "bedroom",
            "insurance", "claim", "policy", "coverage", "deductible"
        ],
        description="Keywords that trigger data extraction"
    )
    
    class Config:
        # Look for .env in project root (parent directory)
        env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
        env_file_encoding = "utf-8"
        case_sensitive = False  # Allow lowercase in .env (e.g., azure_openai_endpoint)
        extra = "allow"  # Allow extra environment variables


# Create settings instance
voice_settings = VoiceAgentSettings()


def validate_voice_settings():
    """Validate that required voice agent settings are present."""
    required_settings = [
        ("AZURE_OPENAI_ENDPOINT", voice_settings.AZURE_OPENAI_ENDPOINT),
        ("AZURE_OPENAI_API_KEY", voice_settings.AZURE_OPENAI_API_KEY),
        ("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", voice_settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME),
        ("AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME", voice_settings.AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME),
    ]
    
    missing = [name for name, value in required_settings if not value]
    
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Please set these in your .env file in the project root."
        )