"""State definitions for the LangGraph voice agent workflow.

This module defines the minimal state for the LangGraph workflow using
the standard messages aggregator pattern following LangGraph best practices.
"""

from typing import TypedDict, Dict, Any, Optional, Annotated
from langgraph.graph import add_messages
from langchain_core.messages import AnyMessage


class VoiceAgentState(TypedDict, total=False):
    """Complete state for the voice agent LangGraph workflow.
    
    Following LangGraph best practices:
    - messages: ONLY actual conversation messages (user/assistant speech)
    - claim_data: tracked JSON payload (PropertyClaim dict)
    - Routing is determined by state conditions, not explicit next_action
    
    State channels:
    - messages: conversation history using add_messages reducer
    - claim_data: tracked JSON payload (PropertyClaim dict)
    - is_claim_complete: computed from claim validation
    - submission_result: result from submit_claim_payload
    - timestamp/current_timezone: time context
    - error/retry_count: error tracking
    - escalation_requested: flag for human handoff
    """
    # Conversation tracking (LangGraph-native, ONLY actual conversation)
    messages: Annotated[list[AnyMessage], add_messages]

    # Claim data payload (adheres to PropertyClaim schema)
    claim_data: Dict[str, Any]

    # Workflow state flags (derived from claim_data, not set manually)
    is_claim_complete: bool
    escalation_requested: bool

    # Submission tracking
    submission_result: Optional[Dict[str, Any]]
    submission_announced: bool

    # Time context
    timestamp: str
    current_timezone: str  # User's timezone for time-related parsing
    
    # Error handling
    error: Optional[str]
    retry_count: int

    # Human handoff tracking
    handoff_info: Optional[Dict[str, Any]]
    handoff_acknowledged: bool
