"""State definitions for the LangGraph voice agent workflow.

This module contains TypedDict state classes for LangGraph workflow state management.
"""

from typing import TypedDict, List, Dict, Any, Optional


class ConversationMessage(TypedDict, total=False):
    """Single conversation message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str


class VoiceAgentState(TypedDict, total=False):
    """Complete state for the voice agent LangGraph workflow.
    
    This state is passed between nodes and tracks the full conversation context.
    """
    # Conversation tracking
    conversation_history: List[ConversationMessage]
    current_user_message: str
    last_assistant_message: str
    
    # Claim data (adheres to PropertyClaim schema)
    claim_data: Dict[str, Any]
    
    # Workflow control
    next_action: str  # "extract", "respond", "complete", "escalate"
    is_claim_complete: bool
    
    # Submission tracking
    submission_result: Optional[Dict[str, Any]]  # Result from submit_claim_payload tool
    
    # Session management
    session_id: str
    timestamp: str
    current_timezone: str  # User's timezone for time-related parsing
    
    # Error handling
    error: Optional[str]
    retry_count: int
