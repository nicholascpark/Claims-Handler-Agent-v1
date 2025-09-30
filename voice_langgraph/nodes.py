"""Node definitions for the LangGraph voice agent workflow.

Each node represents a specific agent or processing step in the workflow.
"""

import json
from typing import Dict, Any
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI
from trustcall import create_extractor

from .settings import voice_settings
from .state import VoiceAgentState
from .schema import PropertyClaim
from .prompts import Prompts
from .tools import submit_claim_payload
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
    """Process voice input and prepare for extraction.
    
    This node handles incoming voice transcriptions and prepares
    them for processing by other agents.
    """
    # Validate we have a user message to process
    if not state.get("current_user_message"):
        state["error"] = "No user message to process"
        state["next_action"] = "respond"
        return state
    
    # Reset error state
    state["error"] = None
    state["retry_count"] = 0
    
    # Add timestamp
    state["timestamp"] = datetime.now().isoformat()
    
    # Determine if we should extract data from this message
    user_msg = state["current_user_message"].lower()
    
    # Keywords that suggest claim data (from settings)
    extraction_keywords = voice_settings.EXTRACTION_KEYWORDS
    
    should_extract = any(keyword in user_msg for keyword in extraction_keywords)
    
    if should_extract:
        state["next_action"] = "extract"
    else:
        state["next_action"] = "respond"
    
    return state


async def extraction_worker_node(state: VoiceAgentState) -> VoiceAgentState:
    """Extract structured claim data from user input using trustcall.
    
    Trustcall handles extraction agentically with the PropertyClaim schema,
    including automatic validation and patching.
    """
    try:
        user_input = state.get("current_user_message", "")
        existing_data = state.get("claim_data", {})
        
        # Get timezone-aware time context
        timezone = state.get("current_timezone", "America/Toronto")
        time_context = get_current_time_context(timezone)
        
        # Check for relative time references
        relative_time = parse_relative_time(user_input, timezone)
        
        # Build conversation context with time awareness
        history = state.get("conversation_history", [])
        context_messages = [time_context["context_string"]]
        
        if relative_time:
            context_messages.append(f"Note: User mentioned '{relative_time['reference']}' which is {relative_time['date']}")
        
        for msg in history[-5:]:  # Last 5 messages for context
            if msg.get("role") in ["user", "assistant"]:
                context_messages.append(f"{msg['role']}: {msg['content']}")
        
        conversation_context = "\n".join(context_messages)
        
        # Build messages for trustcall extractor
        messages = [
            {
                "role": "user",
                "content": f"""Extract property claim information from this conversation.

CRITICAL EXTRACTION RULES:
1. ONLY extract information explicitly stated by the user
2. DO NOT infer dates/times from the current session time - leave empty if not mentioned
3. DO NOT create placeholder values like "unspecified" or "unknown" - leave empty instead
4. DO NOT fill in fields based on assumptions - only use actual user statements
5. For location, ONLY extract if user provides a specific place - never use placeholders

Context:
{conversation_context}

Current user message: {user_input}

Extract ONLY what the user explicitly mentioned into these structures:
- claimant: insured_name, insured_phone, policy_number
- incident: incident_date (YYYY-MM-DD, only if stated), incident_time (HH:MM, only if stated), incident_location (specific place only), incident_description
- property_damage: property_type, points_of_impact, damage_description, estimated_damage_severity, additional_details

If a field is not mentioned, leave it empty or null."""
            }
        ]
        
        # Use trustcall to extract and patch claim data
        # If we have existing data, pass it for patching
        invoke_params = {"messages": messages}
        if existing_data:
            invoke_params["existing"] = {"PropertyClaim": existing_data}
        
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
    
    This node:
    1. Validates claim completeness using PropertyClaim.is_complete()
    2. Decides next conversation steps
    3. Generates appropriate responses
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
        
        # Build conversation context for LLM
        conversation_history = state.get("conversation_history", [])
        recent_history = conversation_history[-10:]  # Last 10 messages
        
        # Get user-friendly field descriptions
        field_descriptions = dict(PropertyClaim.get_field_collection_order())
        missing_friendly = [field_descriptions.get(f, f) for f in missing_fields[:3]]  # Top 3
        
        messages = [
            SystemMessage(content=Prompts.get_supervisor_system_prompt()),
            HumanMessage(content=f"""
Current claim data:
{json.dumps(claim_data, indent=2)}

Validation result:
- Complete: {is_complete}
- Missing fields: {', '.join(missing_friendly) if missing_friendly else 'None'}

Recent conversation:
{json.dumps(recent_history, indent=2)}

User's last message: {state.get('current_user_message', '')}

IMPORTANT GUIDELINES FOR YOUR RESPONSE:
1. If the user just described an incident but didn't provide date/time/location, ask for these specifics
2. If location has placeholder values or is vague, ask for the specific location
3. If date/time are missing, ask when exactly the incident occurred
4. DO NOT ask about photos, documents, or anything that can't be verbally provided
5. Use the caller's actual name if available, never use "[Caller's Name]" or similar placeholders
6. Keep responses natural and empathetic

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
        
        # Update state with decision
        state["last_assistant_message"] = decision["next_message"]
        
        if is_complete:
            # Route to submission node
            state["next_action"] = "submit"
        elif decision.get("should_escalate", False):
            state["next_action"] = "escalate"
        else:
            state["next_action"] = "respond"
            
    except Exception as e:
        # Fallback response on error
        state["error"] = f"Supervisor error: {str(e)}"
        state["last_assistant_message"] = Prompts.get_error_recovery_prompt("default")
        state["next_action"] = "respond"
        
    return state


async def response_generation_node(state: VoiceAgentState) -> VoiceAgentState:
    """Generate final response when supervisor is not needed.
    
    This node handles simple responses that don't require supervisor logic.
    """
    # If we already have a message from supervisor, use it
    if state.get("last_assistant_message"):
        return state
    
    # Generate a simple response based on context
    user_msg = state.get("current_user_message", "").lower()
    
    # Simple response logic
    if any(greeting in user_msg for greeting in ["hello", "hi", "hey"]):
        state["last_assistant_message"] = (
            "Hello! This is Samantha from ACME Insurance. "
            "I'm here to help you file your property damage claim. "
            "First, could I get your full name please?"
        )
    elif any(word in user_msg for word in ["thank", "bye", "goodbye"]):
        state["last_assistant_message"] = (
            "Thank you for calling ACME Insurance. "
            "Have a great day!"
        )
    else:
        # Default to asking for more information
        state["last_assistant_message"] = (
            "I'm here to help with your property damage claim. "
            "Could you tell me what happened?"
        )
    
    return state


async def submission_node(state: VoiceAgentState) -> VoiceAgentState:
    """Submit the completed claim payload.
    
    This node is triggered when PropertyClaim.is_complete() returns True.
    It calls the submit_claim_payload tool to finalize the claim.
    """
    try:
        claim_data = state.get("claim_data", {})
        
        # Submit the completed claim payload
        submission_result = submit_claim_payload.invoke({"claim_payload": claim_data})
        
        # Update state with submission results
        state["claim_data"]["claim_id"] = submission_result.get("claim_id")
        state["submission_result"] = submission_result
        state["next_action"] = "complete"
        
        # Format completion message with claim ID
        state["last_assistant_message"] = (
            f"Thank you! Your claim has been successfully submitted. "
            f"Your claim reference number is {submission_result.get('claim_id')}. "
            f"{submission_result.get('next_steps', 'A claims adjuster will contact you soon.')}"
        )
        
    except Exception as e:
        state["error"] = f"Failed to submit claim: {str(e)}"
        state["last_assistant_message"] = (
            "I've collected all your information, but there was an issue submitting it. "
            "Let me transfer you to a specialist who can help."
        )
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
        state["last_assistant_message"] = (
            "I apologize for the technical difficulties. "
            "Let me transfer you to a specialist who can help you better. "
            "Please hold for a moment."
        )
        state["next_action"] = "escalate"
    else:
        error_type = "default"
        if "extraction" in str(error).lower():
            error_type = "extraction_failed"
        elif "connection" in str(error).lower():
            error_type = "connection_error"
            
        state["last_assistant_message"] = Prompts.get_error_recovery_prompt(error_type)
        state["next_action"] = "respond"
    
    # Clear error for next iteration
    state["error"] = None
    
    return state
