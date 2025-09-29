"""Claims Handler Realtime Agent - Based on OpenAI Realtime Agents pattern

This module implements the junior/supervisor pattern from the OpenAI Realtime Agents
reference implementation, adapted for claims processing.
"""

import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from src.config.settings import settings
from src.prompts import AgentPrompts


@dataclass
class RealtimeMessage:
    """Represents a message in the realtime conversation"""
    role: str  # 'user' or 'assistant' 
    content: str
    timestamp: Optional[str] = None


class ClaimsRealtimeAgent:
    """
    Junior realtime agent that handles basic interactions and defers to supervisor.
    
    Based on the OpenAI chat supervisor pattern:
    - Does not hardcode turn logic or canned responses
    - Maintains conversation history only
    - Delegates content generation entirely to the supervisor tool
    - Always routes non-trivial responses through getNextResponseFromSupervisor
    """
    
    def __init__(self, name: str = "claimsAgent"):
        self.name = name
        self.voice = settings.JUNIOR_AGENT_VOICE
        self.conversation_history: List[RealtimeMessage] = []
        
        # Define instructions (similar to OpenAI pattern)
        self.instructions = self._get_agent_instructions()
        
        # Tools available (only the supervisor tool)
        self.tools = [self._get_supervisor_tool_definition()]
        
    def _get_agent_instructions(self) -> str:
        """Get agent instructions from centralized prompts"""
        return AgentPrompts.get_realtime_agent_instructions()

    def _get_supervisor_tool_definition(self) -> Dict[str, Any]:
        """Get the supervisor tool definition (equivalent to OpenAI pattern)"""
        return {
            "type": "function",
            "name": "getNextResponseFromSupervisor",
            "description": "Determines the next response whenever the agent faces a non-trivial decision, produced by a highly intelligent supervisor agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relevantContextFromLastUserMessage": {
                        "type": "string",
                        "description": "Key information from the user described in their most recent message. Critical to provide as the supervisor needs full context. Can be empty if user message didn't add new information."
                    }
                },
                "required": ["relevantContextFromLastUserMessage"],
                "additionalProperties": False
            }
        }

    def process_user_message(self, message: str) -> Dict[str, Any]:
        """Record the user message and request supervisor guidance every time."""
        # Add to conversation history
        self.conversation_history.append(RealtimeMessage(
            role="user",
            content=message,
            timestamp=self._get_timestamp()
        ))

        context = self._extract_context_from_message(message)
        return {
            "type": "supervisor_needed",
            "context_for_supervisor": context,
            "needs_supervisor": True,
            "conversation_history": self._get_conversation_history_for_supervisor()
        }

    def add_assistant_message(self, message: str) -> None:
        """Public helper to record assistant messages in history."""
        self._add_assistant_message(message)

    # Filler phrases are intentionally not used in intake; avoid "checking" language

    def _extract_context_from_message(self, message: str) -> str:
        """Extract key context from the most recent user message for supervisor"""
        message_lower = message.lower().strip()
        
        # Look for key claim-related information
        context_indicators = {
            "accident": "user mentions accident",
            "collision": "user mentions collision",
            "crash": "user mentions crash", 
            "claim": "user wants to discuss claim",
            "report": "user wants to report incident",
            "policy": "user providing/asking about policy",
            "coverage": "user asking about coverage",
            "happened": "user describing what happened",
            "when": "user providing timing information",
            "where": "user providing location information",
            "phone": "user providing phone number",
            "name": "user providing name information"
        }
        
        # Extract relevant context
        relevant_context = []
        for keyword, context in context_indicators.items():
            if keyword in message_lower:
                relevant_context.append(context)
        
        # Include specific information if present
        if relevant_context:
            context_summary = "; ".join(relevant_context)
            return f"{context_summary}. Message: '{message[:200]}'"
        else:
            # Generic context with message preview
            return f"User message: '{message[:200]}'"

    def _get_conversation_history_for_supervisor(self) -> List[Dict[str, Any]]:
        """Get conversation history formatted for supervisor"""
        history = []
        for msg in self.conversation_history[-settings.MAX_CONVERSATION_HISTORY:]:
            history.append({
                "type": "message",
                "role": msg.role,
                "content": msg.content
            })
        return history

    # Public alias for external callers to avoid using a private method name
    def get_conversation_history_for_supervisor(self) -> List[Dict[str, Any]]:
        return self._get_conversation_history_for_supervisor()

    def _add_assistant_message(self, message: str):
        """Add assistant message to conversation history"""
        self.conversation_history.append(RealtimeMessage(
            role="assistant",
            content=message,
            timestamp=self._get_timestamp()
        ))

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_session_config(self) -> Dict[str, Any]:
        """Get session configuration for realtime API"""
        return {
            "modalities": ["text", "audio"],
            "instructions": self.instructions,
            "voice": self.voice,
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16", 
            "input_audio_transcription": {
                "model": settings.TRANSCRIPTION_MODEL,
                "language": settings.TRANSCRIPTION_LANGUAGE,
                "prompt": "You are transcribing an English insurance claim intake call. Common words: policy, claim, coverage, accident, incident, pipe, water, hail, storm, collision, location."
            },
            "turn_detection": {
                "type": "server_vad",
                # Make VAD more conservative and give user more time to speak
                "threshold": settings.VAD_THRESHOLD,
                "prefix_padding_ms": settings.VAD_PREFIX_PADDING_MS,
                "silence_duration_ms": settings.VAD_SILENCE_DURATION_MS
            },
            "tools": self.tools,
            # Allow tools; per-turn calls explicitly specify the function to avoid duplicates
            "tool_choice": "auto"
        }


def create_claims_realtime_agent(name: str = "claimsAgent") -> ClaimsRealtimeAgent:
    """Factory function to create a claims realtime agent"""
    return ClaimsRealtimeAgent(name=name)
