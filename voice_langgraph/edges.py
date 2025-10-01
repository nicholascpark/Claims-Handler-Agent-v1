"""Edge definitions and routing logic for the LangGraph voice agent workflow.

This module defines the conditional edges and routing decisions in the graph.
Uses PropertyClaim.is_complete() to trigger submission_node routing.
"""

from typing import Literal
from .state import VoiceAgentState
from .schema import PropertyClaim


def route_after_input(state: VoiceAgentState) -> Literal["extraction_worker", "supervisor", "error_handler"]:
    """Route after processing voice input.
    
    Determines whether to:
    - Extract data from the user message
    - Go directly to supervisor for response
    - Handle an error condition
    """
    if state.get("error"):
        return "error_handler"
    
    next_action = state.get("next_action", "respond")
    
    if next_action == "extract":
        return "extraction_worker"
    else:
        return "supervisor"


def route_after_extraction(state: VoiceAgentState) -> Literal["supervisor", "error_handler"]:
    """Route after extraction worker completes.
    
    Always go to supervisor unless there's an error.
    """
    if state.get("error"):
        return "error_handler"
    
    return "supervisor"


def route_after_supervisor(state: VoiceAgentState) -> Literal["submission", "get_human_representative", "end", "error_handler"]:
    """Route after supervisor makes decision.

    Determines whether to:
    - Submit claim (if complete)
    - Escalate to human representative (if requested)
    - End the workflow (continue conversation on next user input)
    - Handle an error
    """
    if state.get("error"):
        return "error_handler"

    next_action = state.get("next_action", "respond")

    if next_action == "submit":
        return "submission"
    elif next_action == "escalate":
        return "get_human_representative"
    else:
        # Supervisor has emitted message via add_messages; end this turn
        return "end"


def route_after_error(state: VoiceAgentState) -> Literal["end", "supervisor"]:
    """Route after error handling.
    
    Determines whether to:
    - End the workflow (for escalations)
    - Try again with supervisor
    """
    next_action = state.get("next_action", "respond")
    
    if next_action == "escalate":
        return "end"
    else:
        # Try to recover by going to supervisor
        return "supervisor"


def should_continue_conversation(state: VoiceAgentState) -> bool:
    """Determine if the conversation should continue.
    
    Returns False if:
    - Claim is complete (using PropertyClaim.is_complete())
    - Escalation is needed
    - Maximum retries exceeded
    """
    # Check completeness using PropertyClaim schema
    claim_data = state.get("claim_data", {})
    try:
        claim = PropertyClaim(**claim_data) if claim_data else None
        if claim and claim.is_complete():
            return False
    except Exception:
        pass  # Claim data not valid yet, continue conversation
    
    if state.get("next_action") == "escalate":
        return False
    
    if state.get("retry_count", 0) >= 3:
        return False
    
    return True


