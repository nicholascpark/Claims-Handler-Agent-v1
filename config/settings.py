import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4.1-mini-2025-04-14")
    
    # LangSmith Configuration - Disabled to avoid SSL issues
    LANGCHAIN_TRACING = os.getenv("LANGCHAIN_TRACING", "false")
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "fnol-extraction-agent")
    
    # Agent Configuration
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))

settings = Settings() 