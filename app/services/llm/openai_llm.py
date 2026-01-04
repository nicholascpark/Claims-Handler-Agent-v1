"""
OpenAI LLM Service

Provides LLM capabilities using OpenAI's Chat Completions API.
Designed for use with LangGraph and LangChain.
"""

import logging
from typing import Optional, List, Any
from functools import lru_cache

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache for LLM instances
_llm_cache: dict = {}


class OpenAILLM:
    """
    OpenAI LLM wrapper with configuration management.
    
    Provides a unified interface for creating and managing
    OpenAI language model instances.
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize OpenAI LLM.
        
        Args:
            model: Model name (default: from settings)
            temperature: Temperature for sampling (default: from settings)
            max_tokens: Max tokens for response (default: from settings)
            api_key: OpenAI API key (default: from settings)
        """
        self.model = model or settings.openai_model
        self.temperature = temperature if temperature is not None else settings.openai_temperature
        self.max_tokens = max_tokens or settings.openai_max_tokens
        self.api_key = api_key or settings.openai_api_key
        
        self._llm: Optional[ChatOpenAI] = None
    
    def get_llm(self) -> ChatOpenAI:
        """
        Get or create the LLM instance.
        
        Returns:
            ChatOpenAI instance configured with current settings.
        """
        if self._llm is None:
            if not self.api_key:
                raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
            
            logger.info(f"Creating OpenAI LLM: model={self.model}, temp={self.temperature}")
            
            self._llm = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=self.api_key,
                max_retries=settings.max_retries,
                request_timeout=settings.request_timeout,
            )
        
        return self._llm
    
    def bind_tools(self, tools: List[Any]) -> BaseChatModel:
        """
        Bind tools to the LLM for function calling.
        
        Args:
            tools: List of LangChain tools to bind.
            
        Returns:
            LLM with tools bound.
        """
        return self.get_llm().bind_tools(tools)


def create_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    use_cache: bool = True,
) -> ChatOpenAI:
    """
    Factory function to create an LLM instance.
    
    Uses caching to avoid creating multiple instances with the same configuration.
    
    Args:
        model: Model name (optional)
        temperature: Temperature setting (optional)
        use_cache: Whether to use cached instances (default: True)
        
    Returns:
        Configured ChatOpenAI instance.
    """
    # Create cache key
    cache_key = f"{model or 'default'}_{temperature or 'default'}"
    
    # Check cache
    if use_cache and cache_key in _llm_cache:
        logger.debug(f"Using cached LLM: {cache_key}")
        return _llm_cache[cache_key]
    
    # Create new instance
    wrapper = OpenAILLM(model=model, temperature=temperature)
    llm = wrapper.get_llm()
    
    # Cache if enabled
    if use_cache:
        _llm_cache[cache_key] = llm
        logger.debug(f"Cached LLM: {cache_key}")
    
    return llm


def clear_llm_cache() -> None:
    """Clear the LLM instance cache."""
    global _llm_cache
    _llm_cache.clear()
    logger.info("LLM cache cleared")
