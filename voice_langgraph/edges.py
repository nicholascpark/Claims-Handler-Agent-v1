"""Edge definitions and routing logic for the LangGraph voice agent workflow.

This module defines the conditional edges and routing decisions in the graph.
Routes based on STATE CONDITIONS, not explicit next_action flags.
"""

from typing import Literal
from langchain_core.messages import AIMessage
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


def route_after_supervisor(state: VoiceAgentState) -> Literal["tools", "end", "error_handler"]:
    """Route after supervisor makes decision.

    Routes based on state conditions:
    - error -> error_handler
    - supervisor emitted tool_calls -> tools
    - otherwise -> end (wait for next user input)
    """
    if state.get("error"):
        print(f"[ROUTING] Error detected, routing to error_handler")
        return "error_handler"

    # Detect if the last AIMessage includes tool calls
    messages = state.get("messages", [])
    claim_data = state.get("claim_data", {}) or {}
    already_submitted = bool(state.get("submission_result") or claim_data.get("claim_id"))

    for m in reversed(messages):
        if isinstance(m, AIMessage):
            tool_calls = getattr(m, "tool_calls", None) or []
            if tool_calls:
                # Post-submission safety: ignore submit_claim_payload tool calls
                allowed_tool_calls = []
                for tc in tool_calls:
                    try:
                        name = (tc.get("name") or tc.get("tool", {}).get("name") or "").strip()
                    except Exception:
                        name = ""
                    if already_submitted and name == "submit_claim_payload":
                        print("[ROUTING] 🛠️ Ignoring submit_claim_payload after submission; ending turn")
                        # Do not route to tools for submit after submission
                        continue
                    allowed_tool_calls.append(tc)

                if allowed_tool_calls:
                    print(f"[ROUTING] 🛠️ Tool calls detected from supervisor, routing to tools")
                    return "tools"
                # No allowed tool calls remain
                return "end"
            break
    
    # Normal flow: supervisor generated response, end this turn
    print(f"[ROUTING] 💬 Normal response, ending turn")
    return "end"


def route_after_error(state: VoiceAgentState) -> Literal["end", "supervisor"]:
    """Route after error handling.
    
    Routes based on state conditions:
    - otherwise -> end (wait for next user input)
    """
    # End turn, let user try again
    print(f"[ROUTING] Error handled, ending turn")
    return "end"


