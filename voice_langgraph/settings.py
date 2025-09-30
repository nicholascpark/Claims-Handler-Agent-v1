"""Configuration settings for the Voice LangGraph Agent.

This module loads environment variables and provides configuration
for the voice agent including company-specific settings.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Import main settings for Azure OpenAI configuration
from src.config.settings import settings as main_settings

# Load environment variables from .env file
load_dotenv()


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
        default="IntactBot",
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
        default=500,
        description="Silence duration to end speech in milliseconds"
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
    
    # Azure OpenAI Settings (inherited from main settings)
    @property
    def AZURE_OPENAI_ENDPOINT(self) -> Optional[str]:
        return main_settings.AZURE_OPENAI_ENDPOINT
    
    @property
    def AZURE_OPENAI_API_KEY(self) -> Optional[str]:
        return main_settings.AZURE_OPENAI_API_KEY
    
    @property
    def AZURE_OPENAI_CHAT_API_VERSION(self) -> Optional[str]:
        return main_settings.AZURE_OPENAI_CHAT_API_VERSION
    
    @property
    def AZURE_OPENAI_CHAT_DEPLOYMENT_NAME(self) -> Optional[str]:
        return main_settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
    
    @property
    def AZURE_OPENAI_REALTIME_API_VERSION(self) -> Optional[str]:
        return main_settings.AZURE_OPENAI_REALTIME_API_VERSION
    
    @property
    def AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME(self) -> Optional[str]:
        return main_settings.AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME
    
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
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Allow extra environment variables


# Create settings instance
voice_settings = VoiceAgentSettings()


def get_company_greeting() -> str:
    """Get the company greeting message."""
    return (
        f"Hello! This is {voice_settings.AGENT_NAME} from {voice_settings.COMPANY_NAME} "
        f"{voice_settings.COMPANY_DEPARTMENT}. I'm here to help you file your property damage claim. "
        f"First, could I get your full name, please?"
    )


def get_agent_instructions() -> str:
    """Get the full agent instructions with company branding."""
    return f"""You are {voice_settings.AGENT_NAME}, an AI property insurance claim assistant for {voice_settings.COMPANY_NAME}.
You're warm, professional, and conversational - like talking to a knowledgeable friend who happens to be great at insurance.

Core personality:
- Friendly and approachable while maintaining professionalism
- Patient and understanding, especially when callers are stressed
- Clear and concise without being robotic
- Empathetic to the caller's situation

Your primary goal is to collect claim information naturally through conversation.

IMPORTANT INSTRUCTIONS:
1. Start EVERY conversation by greeting: "{get_company_greeting()}"

2. Be conversational but efficient - acknowledge what they tell you and guide them to provide necessary information.

3. When the claim is complete, thank them and let them know their claim will be processed."""


def validate_voice_settings():
    """Validate that required voice agent settings are present."""
    # Use the main settings validation since we inherit from it
    from src.config.settings import validate_required_settings
    validate_required_settings()
