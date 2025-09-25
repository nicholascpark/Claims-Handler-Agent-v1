"""Claim validation tools for the Claims Handler Agent"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from src.schema.simplified_payload import SimplifiedClaim
from src.schema.accessor import accessor


def validate_claim_info(claim_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate essential claim information completeness and format.
    
    Args:
        claim_data: Dictionary containing claim information
        
    Returns:
        Dictionary with validation status and details
    """
    validation_result = {
        "is_valid": True,
        "missing_fields": [],
        "format_errors": [],
        "warnings": []
    }
    
    # Check required fields derived from schema (no hard-coded keys)
    required_fields = accessor.required_fields() if accessor else [
        "claim_id", "insured_name", "insured_phone",
        "incident_date", "incident_time", "incident_location", "incident_description"
    ]
    
    for field in required_fields:
        if not claim_data.get(field) or not str(claim_data[field]).strip():
            validation_result["missing_fields"].append(field)
            validation_result["is_valid"] = False
    
    # Validate formats if fields are present
    if claim_data.get("insured_phone"):
        if not validate_phone_format(claim_data["insured_phone"]):
            validation_result["format_errors"].append("insured_phone: Invalid phone format")
            validation_result["is_valid"] = False
    
    if claim_data.get("incident_date"):
        if not validate_date_format(claim_data["incident_date"]):
            validation_result["format_errors"].append("incident_date: Expected YYYY-MM-DD format")
            validation_result["is_valid"] = False
    
    if claim_data.get("incident_time"):
        if not validate_time_format(claim_data["incident_time"]):
            validation_result["format_errors"].append("incident_time: Expected HH:MM format")
            validation_result["is_valid"] = False
    
    if claim_data.get("incident_location"):
        if not validate_location_format(claim_data["incident_location"]):
            validation_result["warnings"].append("incident_location: Consider 'City, State' format")
    
    # Check for completeness percentage
    total_possible_fields = len(required_fields) + 5  # Optional fields including policy_number
    filled_fields = sum(
        1
        for field in required_fields
        + [
            "policy_number",
            "vehicles_involved",
            "injuries_reported",
            "police_report_number",
            "witness_present",
        ]
        if claim_data.get(field) is not None
    )
    
    validation_result["completeness_percentage"] = (filled_fields / total_possible_fields) * 100
    
    return validation_result


def validate_phone_format(phone: str) -> bool:
    """Validate phone number format"""
    # Allow various common formats: (555) 123-4567, 555-123-4567, 5551234567
    phone_pattern = r'^(\(?\d{3}\)?)[-.\s]?\d{3}[-.\s]?\d{4}$'
    return bool(re.match(phone_pattern, phone.strip()))


def validate_date_format(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)"""
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_time_format(time_str: str) -> bool:
    """Validate time format (HH:MM)"""
    try:
        datetime.strptime(time_str.strip(), "%H:%M")
        return True
    except ValueError:
        return False


def validate_location_format(location: str) -> bool:
    """Validate location format (City, State)"""
    # Look for City, State pattern
    location_pattern = r'^[A-Za-z\s]+,\s*[A-Za-z]{2}$'
    return bool(re.match(location_pattern, location.strip()))


def get_validation_message(validation_result: Dict[str, Any]) -> str:
    """
    Generate a human-readable validation message for the agent to use.
    
    Args:
        validation_result: Result from validate_claim_info
        
    Returns:
        Human-readable message about validation status
    """
    if validation_result["is_valid"]:
        return "All required information has been collected successfully."
    
    messages = []
    
    if validation_result["missing_fields"]:
        field_names = {
            "claim_id": "claim ID",
            "insured_name": "your full name",
            "insured_phone": "your phone number",
            "incident_date": "the date of the incident",
            "incident_time": "the time of the incident",
            "incident_location": "where the incident occurred",
            "incident_description": "a description of what happened"
        }
        
        missing_readable = [field_names.get(field, field) for field in validation_result["missing_fields"]]
        
        if len(missing_readable) == 1:
            messages.append(f"I still need {missing_readable[0]}.")
        elif len(missing_readable) == 2:
            messages.append(f"I still need {missing_readable[0]} and {missing_readable[1]}.")
        else:
            messages.append(f"I still need {', '.join(missing_readable[:-1])}, and {missing_readable[-1]}.")
    
    if validation_result["format_errors"]:
        messages.append("Some information needs to be corrected:")
        for error in validation_result["format_errors"]:
            if "phone" in error:
                messages.append("Please provide your phone number in a standard format like (555) 123-4567.")
            elif "date" in error:
                messages.append("Please provide the incident date in YYYY-MM-DD format.")
            elif "time" in error:
                messages.append("Please provide the incident time in HH:MM format (24-hour).")
    
    return " ".join(messages)


def create_simplified_claim(claim_data: Dict[str, Any]) -> Optional[SimplifiedClaim]:
    """
    Create a SimplifiedClaim object from validated claim data.
    
    Args:
        claim_data: Dictionary containing claim information
        
    Returns:
        SimplifiedClaim object if data is complete, None otherwise
    """
    validation_result = validate_claim_info(claim_data)
    
    if not validation_result["is_valid"]:
        return None
    
    try:
        return SimplifiedClaim(**claim_data)
    except Exception:
        return None
