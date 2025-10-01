"""Tools for the LangGraph voice agent.

Defines LangChain tools used by LangGraph nodes.
"""

import uuid
from typing import Dict, Any
from datetime import datetime

from langchain_core.tools import tool


@tool
def submit_claim_payload(claim_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Submit the completed claim payload to the claims processing system.
    
    This tool is called when the claim data collection is complete and validated.
    It simulates a POST API request to submit the claim for processing.
    
    Args:
        claim_payload: Complete PropertyClaim payload as a dictionary
        
    Returns:
        API response with claim_id, status, and confirmation message
    """
    # Simulate POST API response
    # In production, this would make an actual API call to the claims system
    
    # Generate a unique claim ID
    claim_id = f"CLM-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    # Add claim_id to the payload
    claim_payload["claim_id"] = claim_id
    
    # Simulate successful API response
    response = {
        "success": True,
        "claim_id": claim_id,
        "status": "submitted",
        "message": f"Claim {claim_id} has been successfully submitted for processing.",
        "submitted_at": datetime.now().isoformat(),
        "next_steps": "A claims adjuster will contact you within 24-48 hours.",
        "reference_number": claim_id,
        "payload": claim_payload
    }
    
    return response


@tool
def get_human_agent_phone_number() -> Dict[str, str]:
    """Return the phone number for a human claims agent."""
    return {"phone_number": "877-624-7775"}


@tool
def get_human_contact() -> Dict[str, Any]:
    """Return contact info for a human claims representative.
    
    Provides phone number and basic hours/instructions.
    """
    return {
        "phone_number": "877-624-7775",
        "hours": "24/7",
        "notes": "Ask for Claims Intake; provide your policy number if available."
    }
