"""Simplified payload schema for Claims Handler Agent v1

This schema reduces complexity by 80% compared to the previous version,
focusing only on essential claim information for efficient processing.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class SimplifiedClaim(BaseModel):
    """
    Simplified claim schema with essential fields only.
    
    Reduced from 15+ nested classes to 1 class with 12 core fields.
    """
    
    # Core identifiers
    claim_id: str = Field(description="Unique claim identifier")
    policy_number: Optional[str] = Field(default=None, description="Insurance policy number (optional in v1)")
    
    # Essential parties
    insured_name: str = Field(description="Full name of insured party")
    insured_phone: str = Field(description="Primary contact phone number")
    
    # Incident essentials
    incident_date: str = Field(description="Date of incident (YYYY-MM-DD format)")
    incident_time: str = Field(description="Time of incident (HH:MM format)")
    incident_location: str = Field(description="Location in 'City, State' format")
    incident_description: str = Field(description="Brief description of what happened")
    
    # Vehicle basics (if applicable)
    vehicles_involved: Optional[List[str]] = Field(
        default=None, 
        description="List of vehicles in 'make model year' format"
    )
    
    # Injury indicator
    injuries_reported: bool = Field(
        default=False,
        description="Whether any injuries were reported"
    )
    
    # Optional enhancements
    police_report_number: Optional[str] = Field(
        default=None,
        description="Police report number if available"
    )
    witness_present: bool = Field(
        default=False,
        description="Whether witnesses were present"
    )

    def is_complete(self) -> bool:
        """Check if all essential fields are populated."""
        required_fields = [
            self.claim_id,
            self.insured_name,
            self.insured_phone,
            self.incident_date,
            self.incident_time,
            self.incident_location,
            self.incident_description
        ]
        return all(field and str(field).strip() for field in required_fields)

    def get_missing_fields(self) -> List[str]:
        """Get list of missing required fields."""
        missing = []
        field_checks = {
            'claim_id': self.claim_id,
            'insured_name': self.insured_name,
            'insured_phone': self.insured_phone,
            'incident_date': self.incident_date,
            'incident_time': self.incident_time,
            'incident_location': self.incident_location,
            'incident_description': self.incident_description
        }
        
        for field_name, field_value in field_checks.items():
            if not field_value or not str(field_value).strip():
                missing.append(field_name)
        
        return missing


# Example template for testing
EXAMPLE_SIMPLIFIED_CLAIM = SimplifiedClaim(
    claim_id="CL-2025-001",
    policy_number="POL-12345",
    insured_name="John Smith",
    insured_phone="555-0123",
    incident_date="2025-09-22",
    incident_time="14:30",
    incident_location="Seattle, WA",
    incident_description="Rear-end collision at intersection",
    vehicles_involved=["Toyota Camry 2020", "Ford F-150 2019"],
    injuries_reported=False,
    police_report_number="SPD-2025-0922-001",
    witness_present=True
)
