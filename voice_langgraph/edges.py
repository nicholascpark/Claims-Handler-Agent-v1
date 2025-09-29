"""Edge definitions and routing logic for the LangGraph voice agent workflow.

This module defines the conditional edges and routing decisions in the graph.
Uses PropertyClaim.is_complete() to trigger submission_node routing.
"""

from typing import Literal
from langgraph.graph import END
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


def route_after_supervisor(state: VoiceAgentState) -> Literal["submission", "response_generator", "end", "error_handler"]:
    """Route after supervisor makes decision.
    
    Determines whether to:
    - Submit claim (if complete)
    - Generate a response (if not already provided)
    - Complete the workflow
    - Handle an error
    """
    if state.get("error"):
        return "error_handler"
    
    next_action = state.get("next_action", "respond")
    
    if next_action == "submit":
        return "submission"
    elif next_action == "complete":
        return "end"
    elif next_action == "escalate":
        return "end"  # End workflow for escalation
    else:
        # Check if supervisor already provided a message
        if state.get("last_assistant_message"):
            return "end"
        else:
            return "response_generator"


def route_after_response(state: VoiceAgentState) -> Literal["end"]:
    """Route after response generation.
    
    Always end the workflow after generating response.
    """
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


def format_state_for_response(state: VoiceAgentState) -> dict:
    """Format the final state for response to the voice handler.
    
    Extracts only the necessary fields for the WebSocket response.
    """
    return {
        "message": state.get("last_assistant_message", ""),
        "is_complete": state.get("is_claim_complete", False),
        "claim_data": state.get("claim_data", {}),
        "should_escalate": state.get("next_action") == "escalate",
        "error": state.get("error")
    }
