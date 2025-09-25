"""Policy lookup tools for the Claims Handler Agent"""

from typing import Dict, Optional, List
import re


def lookup_policy_info(policy_number: str) -> Dict[str, any]:
    """
    Retrieve policy details and coverage information.
    
    Note: This is a mock implementation for demonstration.
    In production, this would connect to actual policy systems.
    
    Args:
        policy_number: Insurance policy number
        
    Returns:
        Dictionary with policy information
    """
    # Clean and validate policy number format
    cleaned_policy = policy_number.strip().upper()
    
    result = {
        "policy_number": cleaned_policy,
        "is_valid": False,
        "status": "unknown",
        "coverage_details": {},
        "insured_info": {},
        "error_message": None
    }
    
    # Validate policy number format (example: POL-12345 or similar)
    if not validate_policy_format(cleaned_policy):
        result["error_message"] = "Invalid policy number format. Expected format like 'POL-12345'"
        return result
    
    # Mock policy lookup based on pattern
    mock_policy = get_mock_policy_data(cleaned_policy)
    
    if mock_policy:
        result.update(mock_policy)
        result["is_valid"] = True
    else:
        result["error_message"] = "Policy not found in our records"
    
    return result


def validate_policy_format(policy_number: str) -> bool:
    """
    Validate policy number format.
    
    Args:
        policy_number: Policy number to validate
        
    Returns:
        True if format is valid, False otherwise
    """
    # Example patterns: POL-12345, INT-67890, 123456789
    patterns = [
        r'^[A-Z]{3}-\d{5,}$',  # POL-12345
        r'^[A-Z]{3}\d{6,}$',   # POL123456
        r'^\d{6,12}$'          # 123456789
    ]
    
    return any(re.match(pattern, policy_number) for pattern in patterns)


def get_mock_policy_data(policy_number: str) -> Optional[Dict[str, any]]:
    """
    Get mock policy data based on policy number.
    
    Args:
        policy_number: Clean policy number
        
    Returns:
        Mock policy data if policy exists, None otherwise
    """
    # Mock policy database - in production, this would be real data
    mock_policies = {
        "POL-12345": {
            "status": "active",
            "policy_type": "Auto Insurance",
            "effective_date": "2024-01-01",
            "expiry_date": "2024-12-31",
            "coverage_details": {
                "liability": {
                    "bodily_injury": "$100,000/$300,000",
                    "property_damage": "$50,000"
                },
                "collision": {
                    "deductible": "$500",
                    "coverage": "Full Coverage"
                },
                "comprehensive": {
                    "deductible": "$250",
                    "coverage": "Full Coverage"
                }
            },
            "insured_info": {
                "primary_insured": "John Smith",
                "address": "123 Main St, Seattle, WA 98101",
                "vehicles": [
                    {
                        "year": "2020",
                        "make": "Toyota",
                        "model": "Camry",
                        "vin": "1HGBH41JXMN109186"
                    }
                ]
            },
            "premium": "$1,200/year"
        },
        "INT-67890": {
            "status": "active",
            "policy_type": "Auto Insurance",
            "effective_date": "2024-06-01",
            "expiry_date": "2025-05-31",
            "coverage_details": {
                "liability": {
                    "bodily_injury": "$250,000/$500,000",
                    "property_damage": "$100,000"
                },
                "collision": {
                    "deductible": "$1000",
                    "coverage": "Full Coverage"
                },
                "comprehensive": {
                    "deductible": "$500",
                    "coverage": "Full Coverage"
                }
            },
            "insured_info": {
                "primary_insured": "Sarah Johnson",
                "address": "456 Oak Ave, Portland, OR 97201",
                "vehicles": [
                    {
                        "year": "2019",
                        "make": "Honda",
                        "model": "Civic",
                        "vin": "2HGFC2F59KH542315"
                    }
                ]
            },
            "premium": "$1,450/year"
        }
    }
    
    return mock_policies.get(policy_number)


def format_policy_info_for_agent(policy_info: Dict[str, any]) -> str:
    """
    Format policy information for agent use in conversation.
    
    Args:
        policy_info: Result from lookup_policy_info
        
    Returns:
        Human-readable policy information
    """
    if not policy_info["is_valid"]:
        return f"I'm unable to find that policy number. {policy_info.get('error_message', '')}"
    
    # Build response based on available information
    response_parts = []
    
    # Basic policy info
    response_parts.append(f"I found your {policy_info['policy_type']} policy")
    
    # Status
    if policy_info["status"] == "active":
        response_parts.append("and it's currently active")
    else:
        response_parts.append(f"but it shows as {policy_info['status']}")
    
    # Coverage highlights
    if policy_info.get("coverage_details"):
        coverage = policy_info["coverage_details"]
        if coverage.get("collision"):
            deductible = coverage["collision"].get("deductible", "")
            if deductible:
                response_parts.append(f"Your collision deductible is {deductible}")
    
    # Join with natural language connectors
    if len(response_parts) == 1:
        return response_parts[0] + "."
    elif len(response_parts) == 2:
        return f"{response_parts[0]} {response_parts[1]}."
    else:
        return f"{', '.join(response_parts[:-1])}, and {response_parts[-1]}."


def get_coverage_summary(policy_info: Dict[str, any]) -> Dict[str, str]:
    """
    Get a simplified coverage summary for display.
    
    Args:
        policy_info: Result from lookup_policy_info
        
    Returns:
        Dictionary with simplified coverage information
    """
    if not policy_info["is_valid"]:
        return {}
    
    summary = {}
    coverage = policy_info.get("coverage_details", {})
    
    if coverage.get("collision"):
        summary["collision_deductible"] = coverage["collision"].get("deductible", "Unknown")
    
    if coverage.get("comprehensive"):
        summary["comprehensive_deductible"] = coverage["comprehensive"].get("deductible", "Unknown")
    
    if coverage.get("liability"):
        liability = coverage["liability"]
        summary["liability_limits"] = f"{liability.get('bodily_injury', 'Unknown')} bodily injury, {liability.get('property_damage', 'Unknown')} property damage"
    
    return summary
