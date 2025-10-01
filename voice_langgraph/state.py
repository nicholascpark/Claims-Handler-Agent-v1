"""State definitions for the LangGraph voice agent workflow.

This module defines the minimal state for the LangGraph workflow using
the standard messages aggregator pattern.
"""

from typing import TypedDict, Dict, Any, Optional, Annotated
from langgraph.graph import add_messages
from langchain_core.messages import AnyMessage


class VoiceAgentState(TypedDict, total=False):
    """Complete state for the voice agent LangGraph workflow.
    
    Minimal state:
    - messages: conversation history using LangGraph's add_messages
    - claim_data: tracked JSON payload (PropertyClaim dict)
    - next_action: routing control
    - is_claim_complete: supervisor completeness flag
    - submission_result: result from submit_claim_payload
    - timestamp/current_timezone: time context
    - error/retry_count: error tracking
    """
    # Conversation tracking (LangGraph-native)
    messages: Annotated[list[AnyMessage], add_messages]

    # Claim data payload (adheres to PropertyClaim schema)
    claim_data: Dict[str, Any]

    # Workflow control
    next_action: str  # "extract", "respond", "submit", "complete", "escalate"
    is_claim_complete: bool

    # Submission tracking
    submission_result: Optional[Dict[str, Any]]

    # Time context
    timestamp: str
    current_timezone: str  # User's timezone for time-related parsing
    
    # Error handling
    error: Optional[str]
    retry_count: int
