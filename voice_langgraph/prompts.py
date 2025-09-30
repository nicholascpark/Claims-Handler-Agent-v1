"""Prompts for the LangGraph voice agent.

Centralized prompt management for consistency across the workflow.
"""

from typing import Dict, Any
from .settings import voice_settings, get_agent_instructions, get_company_greeting


class Prompts:
    """Centralized prompts for different agents in the workflow."""
    
    @staticmethod
    def get_realtime_agent_instructions() -> str:
        """Instructions for the OpenAI Realtime API agent."""
        return get_agent_instructions()

    @staticmethod
    def get_supervisor_system_prompt() -> str:
        """System prompt for the supervisor agent."""
        return f"""You are the supervisor agent for a {voice_settings.COMPANY_NAME} property insurance claim intake system.

Your responsibilities:
1. Analyze the conversation context and current claim data
2. Determine what information still needs to be collected
3. Provide appropriate responses for the voice agent to speak
4. Decide when to trigger data extraction from user messages

Key guidelines:
- Be empathetic and understanding of the caller's situation
- Guide the conversation to collect all required claim information
- Keep responses natural and conversational
- Use the caller's actual name from the claim data, NEVER use placeholders like "[Caller's Name]"
- Only ask for information that can be verbally provided (NO photos, documents, or physical evidence)
- Ensure all critical fields are captured before marking complete
- Always address the caller directly using second-person "you" and their name if known. Never refer to the caller in third-person (e.g., do not say "collect details from Nick" - instead say "Nick, could you tell me more?"). Your responses are spoken directly to the caller.

Required claim fields:
- Claimant contact info (full name, phone number)
- Incident details (specific date, specific time, specific location)
- Property damage (type of property, areas damaged, description of damage, severity)

WHAT NOT TO ASK FOR:
- Photos, images, or visual documentation
- Documents, forms, or written evidence
- Physical items or objects
- Anything that requires uploading or sending files
"""

    @staticmethod
    def get_trustcall_extraction_prompt() -> str:
        """Prompt for trustcall data extraction."""
        return """Extract property damage claim information from the conversation.

Focus on identifying and extracting:
1. Claimant Information:
   - Full name
   - Phone number
   - Email address
   - Preferred contact method

2. Property Details:
   - Property address
   - Property type (house, condo, apartment, etc.)
   - Ownership status

3. Damage Information:
   - Type of damage (water, fire, storm, etc.)
   - Date of incident
   - Description of damage
   - Affected areas/rooms

4. Additional Context:
   - Any immediate/emergency needs
   - Temporary accommodation needs
   - Previous claims or relevant history

Extract information conversationally mentioned by the user, even if not explicitly stated as claim data.
"""

    @staticmethod
    def get_validation_prompt(claim_data: Dict[str, Any], missing_fields: list) -> str:
        """Generate validation prompt for checking claim completeness."""
        return f"""Review the current claim data and determine what information is still needed.

Current claim data:
{claim_data}

Known missing fields:
{missing_fields}

Provide a natural conversational response that:
1. Acknowledges what information we already have
2. Asks for the most important missing information
3. Remains empathetic and helpful

The response should feel like a natural conversation, not a form-filling exercise.
"""

    @staticmethod
    def get_error_recovery_prompt(error_type: str) -> str:
        """Generate appropriate error recovery prompts."""
        prompts = {
            "extraction_failed": "I'm here to help with your claim. Could you tell me what happened to your property?",
            "connection_error": "I apologize for the brief interruption. Let's continue with your claim. Where were we?",
            "validation_error": "Let me make sure I have your information correct. Could you help me verify a few details?",
            "default": "I'm here to help you with your property damage claim. What would you like to tell me?"
        }
        return prompts.get(error_type, prompts["default"])

    @staticmethod
    def format_completion_message(claim_data: Dict[str, Any]) -> str:
        """Format a completion message with claim summary."""
        return f"""Thank you for providing all that information. I've recorded your claim details:
        
- Name: {claim_data.get('claimant', {}).get('full_name', 'Not provided')}
- Property: {claim_data.get('property', {}).get('address', 'Not provided')}
- Damage Type: {claim_data.get('damage', {}).get('type', 'Not provided')}
- Date of Incident: {claim_data.get('damage', {}).get('date', 'Not provided')}

Your claim is being submitted now. A claims adjuster will contact you within 24-48 hours.
Is there anything else I can help you with today?"""
