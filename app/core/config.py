"""
Application Configuration

Centralized configuration management with environment variable support.
Designed for easy customization without code changes.
"""

import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    All settings can be overridden via environment variables.
    Example: APP_NAME -> app_name, OPENAI_API_KEY -> openai_api_key
    """
    
    # ===========================================
    # Application Settings
    # ===========================================
    app_name: str = Field(default="Notera Voice Agent", description="Application name")
    app_version: str = Field(default="2.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # ===========================================
    # API Configuration
    # ===========================================
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # ===========================================
    # OpenAI Configuration (Primary Provider)
    # ===========================================
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model for chat")
    openai_temperature: float = Field(default=0.1, description="Model temperature (0-2)")
    openai_max_tokens: Optional[int] = Field(default=1000, description="Max tokens for response")
    
    # ===========================================
    # Voice Configuration (OpenAI)
    # ===========================================
    whisper_model: str = Field(default="whisper-1", description="Whisper model for STT")
    tts_model: str = Field(default="tts-1", description="TTS model")
    tts_voice: str = Field(default="alloy", description="TTS voice: alloy, echo, fable, onyx, nova, shimmer")
    tts_speed: float = Field(default=1.0, description="TTS speed (0.25-4.0)")
    
    # ===========================================
    # Multi-language Support
    # ===========================================
    default_language: str = Field(default="en", description="Default language code")
    supported_languages: str = Field(
        default="en,es,fr,de,it,pt,zh,ja,ko",
        description="Comma-separated list of supported language codes"
    )
    
    # ===========================================
    # Session & Persistence
    # ===========================================
    session_timeout_minutes: int = Field(default=30, description="Session timeout in minutes")
    persistence_enabled: bool = Field(default=True, description="Enable conversation persistence")
    database_url: Optional[str] = Field(default=None, description="Database URL for persistence (SQLite by default)")
    
    # ===========================================
    # Performance Settings
    # ===========================================
    max_retries: int = Field(default=3, description="Max retries for API calls")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    enable_caching: bool = Field(default=True, description="Enable response caching")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    
    # ===========================================
    # Observability
    # ===========================================
    langsmith_api_key: Optional[str] = Field(default=None, description="LangSmith API key for tracing")
    langsmith_project: str = Field(default="notera-voice-agent", description="LangSmith project name")
    enable_tracing: bool = Field(default=False, description="Enable LangSmith tracing")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    @property
    def supported_languages_list(self) -> List[str]:
        """Parse supported languages string into list."""
        return [lang.strip() for lang in self.supported_languages.split(",") if lang.strip()]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
    
    @property
    def database_path(self) -> str:
        """Get database path for SQLite (default persistence)."""
        if self.database_url:
            return self.database_url
        return "sqlite:///./data/conversations.db"
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        
        if self.openai_temperature < 0 or self.openai_temperature > 2:
            errors.append("OPENAI_TEMPERATURE must be between 0 and 2")
        
        if self.tts_speed < 0.25 or self.tts_speed > 4.0:
            errors.append("TTS_SPEED must be between 0.25 and 4.0")
        
        return errors


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
