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


# Initialize LLM for supervisor (not using Realtime API)
supervisor_llm = AzureChatOpenAI(
    azure_deployment=voice_settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
    azure_endpoint=voice_settings.AZURE_OPENAI_ENDPOINT,
    api_key=voice_settings.AZURE_OPENAI_API_KEY,
    api_version=voice_settings.AZURE_OPENAI_CHAT_API_VERSION,
    temperature=0.7,
    model_name="gpt-4"
)

# Initialize trustcall extractor with PropertyClaim schema
# Trustcall handles extraction agentically without explicit extraction logic
trustcall_extractor = create_extractor(
    supervisor_llm,
    tools=[PropertyClaim],
    tool_choice="PropertyClaim"
)


async def voice_input_node(state: VoiceAgentState) -> VoiceAgentState:
    """Process the latest user message and route for extraction.
    
    Always extracts on new user input to keep the payload up to date.
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
        state["next_action"] = "respond"
        return state

    # Reset error and set timestamp
    state["error"] = None
    state["retry_count"] = 0
    state["timestamp"] = datetime.now().isoformat()

    # Always extract on any new user input
    state["next_action"] = "extract"
    return state


async def extraction_worker_node(state: VoiceAgentState) -> VoiceAgentState:
    """Extract structured claim data from user input using trustcall.
    
    Trustcall handles extraction agentically with the PropertyClaim schema,
    including automatic validation and patching.
    """
    try:
        # Latest user input from messages
        msgs = state.get("messages", [])
        user_input = ""
        for m in reversed(msgs):
            if isinstance(m, HumanMessage):
                user_input = m.content or ""
                break
        existing_data = state.get("claim_data", {})
        
        # Get timezone-aware time context
        timezone = state.get("current_timezone", "America/Toronto")
        time_context = get_current_time_context(timezone)
        
        # Check for relative time references
        relative_time = parse_relative_time(user_input, timezone)
        
        # Build conversation context with time awareness (last 5 messages)
        context_messages = [time_context["context_string"]]
        if relative_time:
            # Include both date and time if available
            time_info = f"Note: User mentioned '{relative_time.get('reference', '')}'"
            if relative_time.get('date'):
                time_info += f" which is {relative_time['date']}"
            if relative_time.get('time'):
                time_info += f" at {relative_time['time']}"
            if relative_time.get('time_reference'):
                time_info += f" (time reference: '{relative_time['time_reference']}')"
            context_messages.append(time_info)
        for mm in msgs[-5:]:
            if isinstance(mm, HumanMessage):
                context_messages.append(f"user: {mm.content}")
            else:
                try:
                    # AIMessage or others
                    if hasattr(mm, 'content') and mm.content:
                        context_messages.append(f"assistant: {mm.content}")
                except Exception:
                    pass
        conversation_context = "\n".join(context_messages)
        
        # Build messages for trustcall extractor
        messages = [
            {
                "role": "user",
                "content": f"""Extract property claim information from this conversation.

CRITICAL EXTRACTION RULES:
1. ONLY extract information explicitly stated by the user
2. Pay special attention to the Context section which contains parsed date/time information
3. If the context mentions a specific date from a relative reference (e.g., "yesterday"), use that date
4. If the context mentions a specific time from a relative reference (e.g., "around this time"), use that time
5. DO NOT create placeholder values like "unspecified" or "unknown" - leave empty instead
6. DO NOT fill in fields based on assumptions - only use actual user statements
7. For location, ONLY extract if user provides a specific place - never use placeholders

Context:
{conversation_context}

Current user message: {user_input}

Extract ONLY what the user explicitly mentioned into these structures:
- claimant: insured_name, insured_phone, policy_number
- incident: incident_date (YYYY-MM-DD, extract from context if mentioned), incident_time (HH:MM, extract from context if mentioned), incident_location (specific place only), incident_description
- property_damage: property_type, points_of_impact, damage_description, estimated_damage_severity, additional_details

If a field is not mentioned, leave it empty or null."""
            }
        ]
        
        # Use trustcall to extract and patch claim data
        # If we have existing data, pass it for patching
        invoke_params = {
            "messages": [("user", messages[0]["content"])],
            "existing": {"PropertyClaim": existing_data if existing_data else PropertyClaim.create_empty().model_dump()},
        }
        
        result = trustcall_extractor.invoke(invoke_params)
        
        # Get the extracted PropertyClaim
        if result.get("responses"):
            extracted_claim = result["responses"][0]
            state["claim_data"] = extracted_claim.model_dump() if hasattr(extracted_claim, 'model_dump') else extracted_claim
        else:
            state["error"] = "No data extracted"
            
    except Exception as e:
        state["error"] = f"Extraction failed: {str(e)}"
    
    # Always go to supervisor after extraction
    state["next_action"] = "respond"
    
    return state


async def supervisor_node(state: VoiceAgentState) -> VoiceAgentState:
    """Supervisor agent that orchestrates the conversation flow.
    
    Validates completeness, asks empathetically for the next missing field,
    and emits an AI message via messages aggregator.
    """
    try:
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
        
        # If claim is complete, route directly to submission without generating a response
        # The submission_node will generate the final message with claim ID
        if is_complete:
            state["next_action"] = "submit"
            return state
        
        # Get user-friendly field descriptions
        field_descriptions = dict(PropertyClaim.get_field_collection_order())
        # Focus conversation on the NEXT missing field in the defined order
        if missing_fields:
            ordered_fields = [f for f, _ in PropertyClaim.get_field_collection_order()]
            next_missing = next((f for f in ordered_fields if f in missing_fields), missing_fields[0])
            missing_friendly = [field_descriptions.get(next_missing, next_missing)]
        else:
            missing_friendly = []
        
        # Serialize recent conversation from messages
        msgs = state.get("messages", [])
        recent_serialized = []
        for m in msgs[-10:]:
            if isinstance(m, HumanMessage):
                recent_serialized.append({"role": "user", "content": m.content})
            elif hasattr(m, "content"):
                recent_serialized.append({"role": "assistant", "content": m.content})

        messages = [
            SystemMessage(content=Prompts.get_supervisor_system_prompt()),
            HumanMessage(content=f"""
Current claim data:
{json.dumps(claim_data, indent=2)}

Complete: {is_complete}
Missing fields (next): {', '.join(missing_friendly) if missing_friendly else 'None'}

Recent conversation:
{json.dumps(recent_serialized, indent=2)}

IMPORTANT GUIDELINES FOR YOUR RESPONSE:
1. Begin with a warm, empathetic acknowledgement (use the caller's name if present).
2. Ask for only the single next missing field shown above.
3. Do not claim we have info unless it appears in the JSON.
4. Do not ask for documents or anything non-verbal.

Based on this information, provide:
1. A natural, conversational response for the voice agent to speak
2. Whether we need to escalate to a human agent

Format your response as JSON:
{{
    "next_message": "Your response here",
    "should_escalate": false,
    "confidence": 0.95,
    "reasoning": "Brief explanation"
}}
""")
        ]
        
        # Get supervisor decision
        response = await supervisor_llm.ainvoke(messages)
        
        # Parse response
        try:
            decision = json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            decision = {
                "next_message": str(response.content),
                "should_escalate": False,
                "confidence": 0.5,
                "reasoning": "Failed to parse supervisor response"
            }
        
        # Emit assistant message via messages aggregator
        state["messages"] = [AIMessage(content=decision["next_message"])]
        
        if decision.get("should_escalate", False):
            state["next_action"] = "escalate"
        else:
            state["next_action"] = "respond"
            
    except Exception as e:
        # Fallback response on error
        state["error"] = f"Supervisor error: {str(e)}"
        state["messages"] = [AIMessage(content=Prompts.get_error_recovery_prompt("default"))]
        state["next_action"] = "respond"
        
    return state


async def get_human_representative(state: VoiceAgentState) -> VoiceAgentState:
    """Invoke human contact tool and generate a handoff message.

    This replaces ad-hoc response generation for human escalation.
    """
    contact = get_human_contact.invoke({})
    phone = contact.get("phone_number", "877-624-7775")
    hours = contact.get("hours", "24/7")
    state["messages"] = [AIMessage(content=(
        f"I understand you'd like to speak with a human representative. "
        f"You can reach our Claims team at {phone} ({hours}). "
        f"I'll also note your request to escalate this call."
    ))]
    state["next_action"] = "complete"
    return state


async def submission_node(state: VoiceAgentState) -> VoiceAgentState:
    """Submit the completed claim payload.
    
    This node is triggered when PropertyClaim.is_complete() returns True.
    It calls the submit_claim_payload tool to finalize the claim and generates
    a warm summary using the supervisor LLM.
    """
    try:
        claim_data = state.get("claim_data", {})
        
        # Submit the completed claim payload
        submission_result = submit_claim_payload.invoke({"claim_payload": claim_data})
        
        # Update state with submission results
        state["claim_data"]["claim_id"] = submission_result.get("claim_id")
        state["submission_result"] = submission_result
        state["next_action"] = "complete"
        
        # Generate a warm, personalized summary using supervisor LLM
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
        except Exception as e:
            # Fallback message if LLM fails
            completion_message = (
                f"Thank you for providing all the details about your claim. "
                f"I've successfully submitted everything with claim number {submission_result.get('claim_id')}, "
                f"and {submission_result.get('next_steps', 'a claims adjuster will contact you within 24-48 hours')}"
            )
        
        state["messages"] = [AIMessage(content=completion_message)]
        
    except Exception as e:
        state["error"] = f"Failed to submit claim: {str(e)}"
        state["messages"] = [AIMessage(content=(
            "I've collected your information, but there was an issue submitting it. "
            "Let me transfer you to a specialist who can help."
        ))]
        state["next_action"] = "escalate"
    
    return state


async def error_handling_node(state: VoiceAgentState) -> VoiceAgentState:
    """Handle errors and provide recovery responses.
    
    This node ensures the conversation can continue even after errors.
    """
    error = state.get("error", "Unknown error")
    retry_count = state.get("retry_count", 0)
    
    # Increment retry count
    state["retry_count"] = retry_count + 1
    
    # Provide appropriate error recovery message
    if retry_count >= 3:
        state["messages"] = [AIMessage(content=(
            "I apologize for the technical difficulties. "
            "Let me transfer you to a specialist who can help you better. "
            "Please hold for a moment."
        ))]
        state["next_action"] = "escalate"
    else:
        error_type = "default"
        if "extraction" in str(error).lower():
            error_type = "extraction_failed"
        elif "connection" in str(error).lower():
            error_type = "connection_error"
            
        state["messages"] = [AIMessage(content=Prompts.get_error_recovery_prompt(error_type))]
        state["next_action"] = "respond"
    
    # Clear error for next iteration
    state["error"] = None
    
    return state