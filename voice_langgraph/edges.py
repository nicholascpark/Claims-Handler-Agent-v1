"""Edge definitions and routing logic for the LangGraph voice agent workflow.

This module defines the conditional edges and routing decisions in the graph.
Routes based on STATE CONDITIONS, not explicit next_action flags.
"""

from typing import Literal
from .state import VoiceAgentState
from .schema import PropertyClaim


def route_after_input(state: VoiceAgentState) -> Literal["extraction_worker", "supervisor", "error_handler"]:
    """Route after processing voice input.
    
    Routes based on state conditions:
    - error -> error_handler
    - escalation_requested -> supervisor (will handle escalation)
    - claim already submitted -> supervisor (skip extraction)
    - otherwise -> extraction_worker
    """
    if state.get("error"):
        print(f"[ROUTING] Error detected, routing to error_handler")
        return "error_handler"
    
    # If escalation requested, skip extraction and go straight to supervisor
    if state.get("escalation_requested"):
        print(f"[ROUTING] Escalation requested, skipping extraction")
        return "supervisor"
    
    # Check if claim is already submitted (has claim_id)
    claim_data = state.get("claim_data", {})
    if claim_data.get("claim_id"):
        print(f"[ROUTING] ⚠️ Claim already submitted (ID: {claim_data['claim_id']}), skipping extraction")
        return "supervisor"
    
    # Normal flow: extract from user message
    print(f"[ROUTING] Routing to extraction")
    return "extraction_worker"


def route_after_extraction(state: VoiceAgentState) -> Literal["supervisor", "error_handler"]:
    """Route after extraction worker completes.
    
    Always go to supervisor unless there's an error.
    """
    if state.get("error"):
        print(f"[ROUTING] Error after extraction, routing to error_handler")
        return "error_handler"
    
    print(f"[ROUTING] Extraction complete, routing to supervisor")
    return "supervisor"


def route_after_supervisor(state: VoiceAgentState) -> Literal["submission", "get_human_representative", "end", "error_handler"]:
    """Route after supervisor makes decision.

    Routes based on state conditions:
    - error -> error_handler
    - is_claim_complete=True -> submission
    - escalation_requested=True -> get_human_representative
    - otherwise -> end (wait for next user input)
    """
    if state.get("error"):
        print(f"[ROUTING] Error detected, routing to error_handler")
        return "error_handler"

    # Check if claim is complete and not already submitted this turn
    # Avoid repeated submissions if submission_result already exists
    if state.get("is_claim_complete") and not state.get("submission_result"):
        print(f"[ROUTING] ✅ Claim complete, routing to submission")
        return "submission"
    
    # Check if escalation was requested
    if state.get("escalation_requested"):
        print(f"[ROUTING] 🔄 Escalation requested, routing to get_human_representative")
        return "get_human_representative"
    
    # Normal flow: supervisor generated response, end this turn
    print(f"[ROUTING] 💬 Normal response, ending turn")
    return "end"


def route_after_error(state: VoiceAgentState) -> Literal["end", "supervisor", "get_human_representative"]:
    """Route after error handling.
    
    Routes based on state conditions:
    - escalation_requested -> get_human_representative
    - otherwise -> end (wait for next user input)
    """
    if state.get("escalation_requested"):
        print(f"[ROUTING] Error handler requested escalation")
        return "get_human_representative"
    
    # End turn, let user try again
    print(f"[ROUTING] Error handled, ending turn")
    return "end"


