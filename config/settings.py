import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # ========================================
    # PERFORMANCE CONFIGURATIONS
    # ========================================
    
    # LLM Performance Settings
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))  # Lower for faster, more deterministic responses
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1000")) if os.getenv("MAX_TOKENS") else None
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))  # Reduced for faster failure handling
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))
    
    # Connection and Timeout Settings
    HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
    HTTP_CONNECT_TIMEOUT = int(os.getenv("HTTP_CONNECT_TIMEOUT", "10"))
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "20"))
    
    # Caching and Performance
    ENABLE_LLM_CACHING = os.getenv("ENABLE_LLM_CACHING", "true").lower() == "true"
    ENABLE_PAYLOAD_CACHING = os.getenv("ENABLE_PAYLOAD_CACHING", "true").lower() == "true"
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    # ========================================
    # AZURE OPENAI CONFIGURATION
    # ========================================
    
    # Azure OpenAI Configuration (following official documentation)
    # These will be automatically picked up by AzureChatOpenAI from environment variables:
    # AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://maeaioai01.openai.azure.com/")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o-quick")
    
    # Optional: Model name for tracing and token counting (doesn't affect completion)
    MODEL = os.getenv("MODEL", "gpt-4")
    MODEL_VERSION = os.getenv("MODEL_VERSION", "0125")
    
    # ========================================
    # FALLBACK OPENAI CONFIGURATION
    # ========================================
    
    # Fallback to regular OpenAI if Azure not configured
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")  # Faster, cheaper model for testing
    
    # ========================================
    # OBSERVABILITY CONFIGURATION
    # ========================================
    
    # LangSmith Configuration - Disabled by default to avoid SSL issues and improve performance
    LANGCHAIN_TRACING = os.getenv("LANGCHAIN_TRACING", "false")
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "fnol-extraction-agent")
    
    # ========================================
    # VALIDATION AND HELPER METHODS
    # ========================================
    
    @classmethod
    def validate_configuration(cls):
        """Validate critical configuration settings."""
        errors = []
        
        if not cls.AZURE_OPENAI_API_KEY and not cls.OPENAI_API_KEY:
            errors.append("Either AZURE_OPENAI_API_KEY or OPENAI_API_KEY must be set")
        
        if cls.MAX_TOKENS and cls.MAX_TOKENS < 100:
            errors.append("MAX_TOKENS should be at least 100 for meaningful responses")
            
        if cls.TEMPERATURE < 0 or cls.TEMPERATURE > 2:
            errors.append("TEMPERATURE should be between 0 and 2")
            
        return errors
    
    @classmethod
    def get_performance_summary(cls):
        """Get a summary of performance-related settings."""
        return {
            "llm_caching_enabled": cls.ENABLE_LLM_CACHING,
            "payload_caching_enabled": cls.ENABLE_PAYLOAD_CACHING,
            "debug_mode": cls.DEBUG_MODE,
            "temperature": cls.TEMPERATURE,
            "max_tokens": cls.MAX_TOKENS,
            "max_retries": cls.MAX_RETRIES,
            "http_timeout": cls.HTTP_TIMEOUT,
            "api_timeout": cls.API_TIMEOUT,
        }

settings = Settings()

# Validate configuration on import
config_errors = settings.validate_configuration()
if config_errors:
    print("⚠️  Configuration warnings:")
    for error in config_errors:
        print(f"   - {error}") 