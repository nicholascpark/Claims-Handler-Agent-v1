"""Node definitions for the LangGraph voice agent workflow.

Each node represents a specific agent or processing step in the workflow.
"""

import json
import re
from typing import Dict, Any
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import AzureChatOpenAI
from trustcall import create_extractor

from .settings import voice_settings
from .state import VoiceAgentState
from .schema import PropertyClaim
from .prompts import Prompts
from .tools import submit_claim_payload, get_human_contact
from .utils import get_current_time_context, parse_relative_time


def _should_escalate_from_input(user_input: str, state: VoiceAgentState) -> bool:
    """Centralized escalation detection for user input.
    
    Checks for explicit escalation requests in user message.
    Returns True if escalation keywords detected.
    """
    escalation_keywords = [
        "human", "person", "representative", "agent", "operator", 
        "speak to someone", "talk to someone", "real person",
        "transfer me", "connect me"
    ]
    
    user_input_lower = user_input.lower()
    return any(keyword in user_input_lower for keyword in escalation_keywords)


# Initialize LLM for supervisor (not using Realtime API)
supervisor_llm = AzureChatOpenAI(
    azure_deployment=voice_settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
    azure_endpoint=voice_settings.AZURE_OPENAI_ENDPOINT,
    api_key=voice_settings.AZURE_OPENAI_API_KEY,
    api_version=voice_settings.AZURE_OPENAI_CHAT_API_VERSION,
    temperature=0.7
)

# Initialize trustcall extractor with PropertyClaim schema
# Trustcall handles extraction agentically without explicit extraction logic
# Note: We use single-schema mode (no enable_inserts) since we're updating ONE claim at a time
trustcall_extractor = create_extractor(
    supervisor_llm,
    tools=[PropertyClaim],
    tool_choice="PropertyClaim"
    # enable_inserts=True is for managing MULTIPLE instances (e.g., list of Person objects)
    # We're managing a SINGLE PropertyClaim, so we don't need it
)


async def voice_input_node(state: VoiceAgentState) -> VoiceAgentState:
    """Process the latest user message and prepare for routing.
    
    Sets up context but doesn't dictate routing - that's handled by edges.
    """
    # Find the latest human message
    msgs = state.get("messages", [])
    user_input = ""
    for m in reversed(msgs):
        if isinstance(m, HumanMessage):
            user_input = m.content or ""
            break

    if not user_input.strip():
        state["error"] = "No user message to process"
        return state

    # Reset error and set timestamp
    state["error"] = None
    state["retry_count"] = 0
    state["timestamp"] = datetime.now().isoformat()
    
    # Check for explicit escalation request using centralized detection
    if _should_escalate_from_input(user_input, state):
        state["escalation_requested"] = True
        print(f"[VOICE_INPUT] 🚨 Escalation detected in user message")
    
    # Note: Routing decision (extract vs skip) is made in edges.py
    # based on whether claim is already submitted
    return state


async def extraction_worker_node(state: VoiceAgentState) -> VoiceAgentState:
    """Extract structured claim data from user input using trustcall.
    
    Uses trustcall with extended conversation history to extract and merge claim data.
    Implements smart merging to preserve existing data.
    """
    try:
        # Get conversation messages
        msgs = state.get("messages", [])
        existing_data = state.get("claim_data", {})
        
        # Build conversation history for trustcall (EXPANDED to last 10 messages for better context)
        conversation_messages = []
        for mm in msgs[-20:]:
            if isinstance(mm, HumanMessage):
                conversation_messages.append(f"User: {mm.content}")
            elif isinstance(mm, AIMessage) and mm.content:
                conversation_messages.append(f"Assistant: {mm.content}")
        
        conversation_history = "\n".join(conversation_messages).strip()
        
        # Get timezone-aware time context
        timezone = state.get("current_timezone", "America/Toronto")
        time_context = get_current_time_context(timezone)
        
        # Check for relative time references in latest message
        latest_user_input = ""
        for m in reversed(msgs):
            if isinstance(m, HumanMessage):
                latest_user_input = m.content or ""
                break
        
        relative_time = parse_relative_time(latest_user_input, timezone)
        
        # Build extraction prompt with conversation context
        extraction_context = f"""Current time: {time_context["context_string"]}

Recent conversation:
{conversation_history}"""
        
        if relative_time:
            time_info = f"\nParsed time reference: '{relative_time.get('reference', '')}'"
            if relative_time.get('date'):
                time_info += f" = {relative_time['date']}"
            if relative_time.get('time'):
                time_info += f" at {relative_time['time']}"
            extraction_context += time_info
        
        extraction_prompt = f"""{extraction_context}

Extract claim information into the PropertyClaim schema with careful attention to field classification."""
        
        # Print trustcall input for debugging
        print("\n" + "="*80)
        print("TRUSTCALL INPUT:")
        print("="*80)
        print(extraction_prompt.strip())
        print("="*80 + "\n")
        
        # Use trustcall with existing data for intelligent patching
        invoke_params = {
            "messages": [("user", extraction_prompt)],
            "existing": {"PropertyClaim": existing_data if existing_data else PropertyClaim.create_empty().model_dump()},
        }
        
        result = trustcall_extractor.invoke(invoke_params)
        
        # Smart merge: only update if we got meaningful new data
        if result.get("responses"):
            extracted_claim = result["responses"][0]
            new_data = extracted_claim.model_dump() if hasattr(extracted_claim, 'model_dump') else extracted_claim
            
            # Check if extraction actually found new content
            # (trustcall may return mostly-empty structure when no new info is present)
            def has_real_content(data):
                """Check if data has actual meaningful content beyond empty strings/None."""
                if not data:
                    return False
                if isinstance(data, dict):
                    for v in data.values():
                        if has_real_content(v):
                            return True
                    return False
                elif isinstance(data, list):
                    return len(data) > 0 and any(has_real_content(item) for item in data)
                elif isinstance(data, str):
                    return bool(data.strip())
                else:
                    return data is not None
            
            # Always update claim_data (trustcall handles merging via "existing")
            state["claim_data"] = new_data
            print(f"[EXTRACTION] ✅ Trustcall completed extraction/merge")
        else:
            print(f"[EXTRACTION] ⚠️ No extraction result from trustcall")
            
    except Exception as e:
        print(f"[EXTRACTION] ❌ Error: {e}")
        state["error"] = f"Extraction failed: {str(e)}"
    
    return state


async def supervisor_node(state: VoiceAgentState) -> VoiceAgentState:
    """Supervisor agent that orchestrates the conversation flow.
    
    Generates natural conversational responses while tracking claim completeness.
    CRITICAL: Only adds actual conversation to messages, never JSON dumps.
    """
    try:
        # First: process outputs from tool nodes (submission/handoff) and generate user-facing messages
        # This ensures tool outputs are converted to messages centrally in the supervisor
        if state.get("submission_result") and not state.get("submission_announced"):
            # Prefer the tool-provided summary for determinism; fallback to LLM if missing
            submission_result = state.get("submission_result", {})
            completion_message = submission_result.get("summary_two_sentences")
            if not completion_message:
                claim_data = state.get("claim_data", {})
                summary_messages = [
                    SystemMessage(content=f"""You are {voice_settings.AGENT_NAME}, providing a final summary after successfully submitting a claim.
Your tone should be:
- Warm, reassuring, and professional
- Brief but comprehensive (exactly 2 sentences)
- Include the claim number and next steps

The caller has just completed their claim intake process and you need to provide closure with confidence that they're in good hands."""),
                    HumanMessage(content=f"""Generate a final summary message for the completed claim submission.

Claim data submitted:
{json.dumps(claim_data, indent=2)}

Submission result:
- Claim ID: {submission_result.get('claim_id')}
- Status: {submission_result.get('status')}
- Next steps: {submission_result.get('next_steps', 'A claims adjuster will contact you within 24-48 hours.')}

Provide a warm, reassuring 2-sentence summary that:
1. First sentence: Acknowledges the completion and mentions the claim number
2. Second sentence: Provides next steps and reassurance

Use the caller's name if available in the claim data.""")
                ]
                try:
                    summary_response = await supervisor_llm.ainvoke(summary_messages)
                    completion_message = summary_response.content.strip()
                except Exception:
                    completion_message = (
                        f"Thank you for providing all the details. I've submitted your claim as {submission_result.get('claim_id')}. "
                        f"A claims adjuster will contact you within 24-48 hours."
                    )

            state["messages"] = [AIMessage(content=completion_message)]
            state["submission_announced"] = True
            return state

        if state.get("handoff_info") and not state.get("handoff_acknowledged"):
            # Build a clear, personalized handoff message using stored tool output
            handoff = state.get("handoff_info", {})
            phone = handoff.get("phone_number", "877-624-7775")
            hours = handoff.get("hours", "24/7")
            notes = handoff.get("notes", "")
            claim_data = state.get("claim_data", {})
            caller_name = claim_data.get("claimant", {}).get("insured_name", "")
            name_part = f"{caller_name}, " if caller_name else ""

            message = (
                f"I understand, {name_part}you'd like to speak with a human representative. "
                f"You can reach our Claims team directly at {phone} (available {hours}). "
            )
            if notes:
                message += notes

            state["messages"] = [AIMessage(content=message)]
            state["handoff_acknowledged"] = True
            return state

        # Get current claim data
        claim_data = state.get("claim_data", {})
        
        # Validate completeness using PropertyClaim schema
        try:
            claim = PropertyClaim(**claim_data) if claim_data else None
            is_complete = claim.is_complete() if claim else False
            missing_fields = claim.get_missing_fields() if claim else []
        except Exception:
            # If data doesn't validate to PropertyClaim yet, it's definitely not complete
            is_complete = False
            missing_fields = PropertyClaim.get_field_collection_order()
        
        state["is_claim_complete"] = is_complete
        
        # If claim is complete, routing will handle submission
        # Just log it here; actual summary message will be generated after submission tool runs
        if is_complete and not state.get("submission_result"):
            print(f"[SUPERVISOR] ✅ Claim is complete. Routing will go to submission.")
            return state
        
        # Get conversation history (actual messages only, last 10)
        msgs = state.get("messages", [])
        conversation_summary = []
        for m in msgs[-20:]:
            if isinstance(m, HumanMessage):
                conversation_summary.append(f"User: {m.content}")
            elif isinstance(m, AIMessage) and m.content:
                conversation_summary.append(f"Assistant: {m.content}")
        
        conversation_text = "\n".join(conversation_summary)
        
        # If escalation was already requested in voice_input, supervisor will still run
        # but routing will handle sending to get_human_representative node
        # No need to generate message here - let the handoff node handle it
        if state.get("escalation_requested"):
            print(f"[SUPERVISOR] 🔔 Escalation already flagged, will route to handoff")
            return state
        
        # Get friendly field names for missing fields
        field_descriptions = dict(PropertyClaim.get_field_collection_order())
        missing_friendly = [field_descriptions.get(f, f) for f in missing_fields]
        
        # Identify the NEXT field to collect (first in the missing list)
        next_field_to_collect = missing_friendly[0] if missing_friendly else None
        
        # Build explicit missing fields guidance
        if missing_friendly:
            missing_fields_guidance = f"""
MISSING FIELDS TO COLLECT (in priority order):
1. **NEXT FIELD TO ASK FOR**: {next_field_to_collect}
2. Then collect: {', '.join(missing_friendly[1:4])}
{f"   ... and {len(missing_friendly) - 4} more fields" if len(missing_friendly) > 4 else ""}

INSTRUCTION: Focus your next question on collecting the NEXT FIELD ({next_field_to_collect}) in a natural, conversational way.
"""
        else:
            missing_fields_guidance = "All required fields are collected! The claim should be complete."
        
        # Build supervisor prompt (this is INTERNAL, not added to conversation messages)
        supervisor_prompt = f"""Recent conversation:
{conversation_text}

Current claim data summary:
{json.dumps(claim_data, indent=2)}

{missing_fields_guidance}

CRITICAL VALIDATION:
- Review the conversation history above
- ONLY acknowledge information that was ACTUALLY mentioned in the conversation
- If a field has data in JSON but wasn't mentioned in the conversation, the user hasn't provided it yet
- Example: If JSON shows phone="555-1234" but conversation doesn't mention a phone number, DON'T say "thank you for providing your phone"
- FOCUS ON COLLECTING THE NEXT MISSING FIELD IF NOT N/A: {next_field_to_collect if next_field_to_collect else 'N/A'}

Generate your response as JSON:
{{
    "next_message": "Your natural, conversational response that asks for the next missing field",
    "should_escalate": false,
    "reasoning": "Why you chose this response and which field you're asking for"
}}"""
        
        # Call LLM with system prompt + analysis prompt (INTERNAL - not added to state messages)
        internal_messages = [
            SystemMessage(content=Prompts.get_supervisor_system_prompt()),
            HumanMessage(content=supervisor_prompt)
        ]
        
        response = await supervisor_llm.ainvoke(internal_messages)
        
        # Parse response
        try:
            decision = json.loads(response.content)
        except json.JSONDecodeError:
            print(f"[SUPERVISOR] ⚠️ Failed to parse JSON from LLM response")
            decision = {
                "next_message": "I'm here to help with your claim. Could you tell me what happened?",
                "should_escalate": False,
                "reasoning": "JSON parse failure - using fallback"
            }
        
        print(f"[SUPERVISOR] Decision - escalate: {decision.get('should_escalate', False)}")
        print(f"[SUPERVISOR] Reasoning: {decision.get('reasoning', 'No reasoning')[:100]}")
        
        # Handle escalation from LLM decision
        if decision.get("should_escalate", False):
            state["escalation_requested"] = True
            print(f"[SUPERVISOR] 🔔 LLM detected escalation request")
        
        # Add ONLY the conversation message to state (this goes into the conversation history)
        state["messages"] = [AIMessage(content=decision["next_message"])]
            
    except Exception as e:
        # Fallback response on error
        print(f"[SUPERVISOR] ❌ Error: {e}")
        state["error"] = f"Supervisor error: {str(e)}"
        state["messages"] = [AIMessage(content=Prompts.get_error_recovery_prompt("default"))]
        
    return state


async def get_human_representative(state: VoiceAgentState) -> VoiceAgentState:
    """Invoke human contact tool and store handoff info for supervisor to render.

    This node is a pure tool node. The supervisor will generate the user-facing message.
    """
    print(f"[ESCALATION] 🔄 Initiating human representative handoff")
    contact = get_human_contact.invoke({})
    state["handoff_info"] = contact
    # Clear escalation flag to avoid loops; supervisor will acknowledge handoff
    state["escalation_requested"] = False
    print(f"[ESCALATION] 📞 Contact info retrieved: {contact}")
    return state


async def submission_node(state: VoiceAgentState) -> VoiceAgentState:
    """Submit the completed claim payload.
    
    Pure tool node: call the submission tool, store results, and defer messaging to the supervisor.
    """
    try:
        claim_data = state.get("claim_data", {})
        print(f"[SUBMISSION] 📝 Submitting completed claim for: {claim_data.get('claimant', {}).get('insured_name', 'Unknown')}")
        submission_result = submit_claim_payload.invoke({"claim_payload": claim_data})
        print(f"[SUBMISSION] ✅ Claim submitted successfully. Claim ID: {submission_result.get('claim_id')}")
        state["claim_data"]["claim_id"] = submission_result.get("claim_id")
        state["submission_result"] = submission_result
        state["submission_announced"] = False
    except Exception as e:
        print(f"[SUBMISSION] ❌ Error: {e}")
        state["error"] = f"Failed to submit claim: {str(e)}"
        state["escalation_requested"] = True
    return state


async def error_handling_node(state: VoiceAgentState) -> VoiceAgentState:
    """Handle errors and provide recovery responses.
    
    This node ensures the conversation can continue even after errors.
    """
    error = state.get("error", "Unknown error")
    retry_count = state.get("retry_count", 0)
    
    print(f"[ERROR_HANDLER] Handling error (retry {retry_count}): {error}")
    
    # Increment retry count
    state["retry_count"] = retry_count + 1
    
    # Provide appropriate error recovery message
    if retry_count >= 3:
        print(f"[ERROR_HANDLER] Max retries reached, escalating")
        state["messages"] = [AIMessage(content=(
            "I apologize for the technical difficulties. "
            "Let me transfer you to a specialist who can help you better. "
            "Please hold for a moment."
        ))]
        state["escalation_requested"] = True
    else:
        error_type = "default"
        if "extraction" in str(error).lower():
            error_type = "extraction_failed"
        elif "connection" in str(error).lower():
            error_type = "connection_error"
            
        state["messages"] = [AIMessage(content=Prompts.get_error_recovery_prompt(error_type))]
    
    # Clear error for next iteration
    state["error"] = None
    
    return state