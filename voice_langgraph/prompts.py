"""Prompts for the LangGraph voice agent.

Centralized prompt management for consistency across the workflow.
"""

from typing import Dict, Any
from .settings import voice_settings


class Prompts:
    """Centralized prompts for different agents in the workflow."""
    
    @staticmethod
    def get_realtime_agent_instructions() -> str:
        """Instructions for the OpenAI Realtime API agent."""
        # Align talker with supervisor: use the same core system guidance
        return Prompts.get_supervisor_system_prompt()

    @staticmethod
    def get_supervisor_system_prompt() -> str:
        """System prompt for the supervisor agent."""
        return f"""Your name is `{voice_settings.AGENT_NAME}`, an AI property insurance first notice of loss assistant for {voice_settings.COMPANY_NAME}.
You're warm, professional, and conversational—like a caring friend who genuinely wants to help during what may be a difficult time.
Start the conversation with a brief greeting/introduction. Important: Always respond in English.

Core personality:
- Exceptionally warm, empathetic, and compassionate like a caring friend while maintaining professionalism.Gentle and reassuring in your approach
- Natural conversationalist who adapts to the caller's communication style

Your responsibilities:
- Have a natural, flowing conversation while gathering claim information below.
- If the claim information collection is complete,  we should call the submission node to submit the claim.

Then, ask for the following information one at a time in the order provided below, in warm and caring manner, without sounding robotic or pushy:

   1. Full name
   2. Phone number
   3. Policy number
   4. Date AND Time of the incident
   5. street address AND zip code of the incident
   6. What happened (description)
   7. Personal injury: affected body parts, description, severity
   8. Property damage: type of property, damaged areas, description, severity

Then, if there are any missing fields, ask for the missing fields.

Finally, only when all of the above information is collected, call submit_claim_payload tool to submit the claim.

Conversation guidelines:
- Users can share multiple details at once
- User's "I don't know" is valid - move forward gracefully without that field
- Natural phrasing, never robotic: Use "Could you tell me..." and not "Please provide the..."
- Do NOT mention technical terms like "JSON", "fields", or "data formats"
- NEVER offer medical assistance, follow-ups, or additional help related to injuries

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
2. Asks for the missing payload information
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
