"""
Cost Tracking Service

Tracks OpenAI API usage and estimates costs for transparency.
Provides real-time cost information to users.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# OpenAI Pricing (as of 2024) - prices in USD per unit
# These should be updated periodically or made configurable
PRICING = {
    # GPT-4o pricing per 1K tokens
    "gpt-4o": {
        "input": 0.005,   # $0.005 per 1K input tokens
        "output": 0.015,  # $0.015 per 1K output tokens
    },
    "gpt-4o-mini": {
        "input": 0.00015,
        "output": 0.0006,
    },
    "gpt-4-turbo": {
        "input": 0.01,
        "output": 0.03,
    },
    "gpt-3.5-turbo": {
        "input": 0.0005,
        "output": 0.0015,
    },
    
    # Whisper STT pricing per minute
    "whisper-1": {
        "per_minute": 0.006,  # $0.006 per minute
    },
    
    # TTS pricing per 1K characters
    "tts-1": {
        "per_1k_chars": 0.015,  # $0.015 per 1K characters
    },
    "tts-1-hd": {
        "per_1k_chars": 0.030,  # $0.030 per 1K characters
    },
}


@dataclass
class UsageMetrics:
    """Tracks usage metrics for a session or aggregate."""
    
    # LLM usage
    input_tokens: int = 0
    output_tokens: int = 0
    llm_model: str = "gpt-4o"
    
    # Voice usage
    audio_seconds: float = 0.0
    stt_model: str = "whisper-1"
    
    # TTS usage
    tts_characters: int = 0
    tts_model: str = "tts-1"
    
    # Timestamps
    started_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def add_llm_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Add LLM token usage."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.last_updated = datetime.now()
    
    def add_audio_usage(self, seconds: float) -> None:
        """Add audio transcription usage."""
        self.audio_seconds += seconds
        self.last_updated = datetime.now()
    
    def add_tts_usage(self, characters: int) -> None:
        """Add TTS usage."""
        self.tts_characters += characters
        self.last_updated = datetime.now()
    
    def get_llm_cost(self) -> float:
        """Calculate LLM cost."""
        pricing = PRICING.get(self.llm_model, PRICING["gpt-4o"])
        input_cost = (self.input_tokens / 1000) * pricing["input"]
        output_cost = (self.output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost
    
    def get_stt_cost(self) -> float:
        """Calculate speech-to-text cost."""
        pricing = PRICING.get(self.stt_model, PRICING["whisper-1"])
        minutes = self.audio_seconds / 60
        return minutes * pricing["per_minute"]
    
    def get_tts_cost(self) -> float:
        """Calculate text-to-speech cost."""
        pricing = PRICING.get(self.tts_model, PRICING["tts-1"])
        return (self.tts_characters / 1000) * pricing["per_1k_chars"]
    
    def get_total_cost(self) -> float:
        """Calculate total cost."""
        return self.get_llm_cost() + self.get_stt_cost() + self.get_tts_cost()
    
    def get_breakdown(self) -> Dict[str, Any]:
        """Get detailed cost breakdown."""
        return {
            "llm": {
                "model": self.llm_model,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "cost": round(self.get_llm_cost(), 4),
            },
            "stt": {
                "model": self.stt_model,
                "audio_seconds": round(self.audio_seconds, 1),
                "audio_minutes": round(self.audio_seconds / 60, 2),
                "cost": round(self.get_stt_cost(), 4),
            },
            "tts": {
                "model": self.tts_model,
                "characters": self.tts_characters,
                "cost": round(self.get_tts_cost(), 4),
            },
            "total": {
                "cost": round(self.get_total_cost(), 4),
                "duration_seconds": (self.last_updated - self.started_at).total_seconds(),
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "audio_seconds": round(self.audio_seconds, 1),
            "tts_characters": self.tts_characters,
            "estimated_cost_usd": round(self.get_total_cost(), 4),
            "breakdown": self.get_breakdown(),
        }


class CostTracker:
    """
    Tracks costs across sessions.
    
    Provides both per-session and aggregate cost tracking.
    """
    
    def __init__(self):
        self._sessions: Dict[str, UsageMetrics] = {}
        self._aggregate = UsageMetrics()
    
    def get_or_create_session(
        self, 
        session_id: str,
        llm_model: str = "gpt-4o",
        stt_model: str = "whisper-1",
        tts_model: str = "tts-1",
    ) -> UsageMetrics:
        """Get or create a session tracker."""
        if session_id not in self._sessions:
            self._sessions[session_id] = UsageMetrics(
                llm_model=llm_model,
                stt_model=stt_model,
                tts_model=tts_model,
            )
        return self._sessions[session_id]
    
    def track_llm(
        self, 
        session_id: str, 
        input_tokens: int, 
        output_tokens: int
    ) -> None:
        """Track LLM usage for a session."""
        session = self.get_or_create_session(session_id)
        session.add_llm_usage(input_tokens, output_tokens)
        self._aggregate.add_llm_usage(input_tokens, output_tokens)
        
        logger.debug(
            f"Session {session_id}: +{input_tokens} input, +{output_tokens} output tokens"
        )
    
    def track_audio(self, session_id: str, seconds: float) -> None:
        """Track audio transcription for a session."""
        session = self.get_or_create_session(session_id)
        session.add_audio_usage(seconds)
        self._aggregate.add_audio_usage(seconds)
        
        logger.debug(f"Session {session_id}: +{seconds:.1f}s audio")
    
    def track_tts(self, session_id: str, characters: int) -> None:
        """Track TTS usage for a session."""
        session = self.get_or_create_session(session_id)
        session.add_tts_usage(characters)
        self._aggregate.add_tts_usage(characters)
        
        logger.debug(f"Session {session_id}: +{characters} TTS chars")
    
    def get_session_cost(self, session_id: str) -> Dict[str, Any]:
        """Get cost breakdown for a session."""
        if session_id not in self._sessions:
            return {"error": "Session not found", "total_cost": 0}
        
        return self._sessions[session_id].to_dict()
    
    def get_aggregate_cost(self) -> Dict[str, Any]:
        """Get aggregate cost across all sessions."""
        return {
            "session_count": len(self._sessions),
            "aggregate": self._aggregate.to_dict(),
        }
    
    def clear_session(self, session_id: str) -> None:
        """Clear a session's tracking data."""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def clear_all(self) -> None:
        """Clear all tracking data."""
        self._sessions.clear()
        self._aggregate = UsageMetrics()


# Global cost tracker instance
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker


def estimate_conversation_cost(
    turns: int = 5,
    avg_user_message_tokens: int = 50,
    avg_assistant_tokens: int = 100,
    audio_seconds_per_turn: float = 10,
    tts_chars_per_turn: int = 200,
    llm_model: str = "gpt-4o",
) -> Dict[str, Any]:
    """
    Estimate cost for a typical conversation.
    
    Args:
        turns: Number of conversation turns
        avg_user_message_tokens: Average tokens per user message
        avg_assistant_tokens: Average tokens per assistant response
        audio_seconds_per_turn: Average audio per turn (for voice)
        tts_chars_per_turn: Average TTS characters per turn
        llm_model: LLM model to use for pricing
        
    Returns:
        Cost estimate breakdown
    """
    llm_pricing = PRICING.get(llm_model, PRICING["gpt-4o"])
    stt_pricing = PRICING["whisper-1"]
    tts_pricing = PRICING["tts-1"]
    
    # Calculate totals
    total_input_tokens = turns * avg_user_message_tokens
    total_output_tokens = turns * avg_assistant_tokens
    total_audio_minutes = (turns * audio_seconds_per_turn) / 60
    total_tts_chars = turns * tts_chars_per_turn
    
    # Calculate costs
    llm_cost = (
        (total_input_tokens / 1000) * llm_pricing["input"] +
        (total_output_tokens / 1000) * llm_pricing["output"]
    )
    stt_cost = total_audio_minutes * stt_pricing["per_minute"]
    tts_cost = (total_tts_chars / 1000) * tts_pricing["per_1k_chars"]
    
    total_cost = llm_cost + stt_cost + tts_cost
    
    return {
        "assumptions": {
            "turns": turns,
            "avg_user_tokens": avg_user_message_tokens,
            "avg_assistant_tokens": avg_assistant_tokens,
            "audio_seconds_per_turn": audio_seconds_per_turn,
            "tts_chars_per_turn": tts_chars_per_turn,
        },
        "breakdown": {
            "llm": {
                "model": llm_model,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cost": round(llm_cost, 4),
            },
            "stt": {
                "model": "whisper-1",
                "audio_minutes": round(total_audio_minutes, 2),
                "cost": round(stt_cost, 4),
            },
            "tts": {
                "model": "tts-1",
                "characters": total_tts_chars,
                "cost": round(tts_cost, 4),
            },
        },
        "total_estimated_cost": round(total_cost, 4),
        "cost_range": {
            "low": round(total_cost * 0.7, 4),
            "high": round(total_cost * 1.5, 4),
        }
    }
