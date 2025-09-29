"""Enhanced Property Claims Schema for Claims Handler Agent

This schema supports double-nested structures for specialty property claims
including auto, home, condo, and commercial properties with comprehensive
damage tracking and points of impact analysis.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ClaimantInfo(BaseModel):
    """Nested claimant information structure"""
    insured_name: str = Field(description="Full name of the insured party")
    insured_phone: str = Field(description="Primary contact phone number")
    policy_number: Optional[str] = Field(default=None, description="Insurance policy number")


class IncidentDetails(BaseModel):
    """Nested incident information structure"""
    incident_date: str = Field(description="Date of incident (YYYY-MM-DD format)")
    incident_time: str = Field(description="Time of incident (HH:MM format)")
    incident_location: str = Field(description="Specific location where incident occurred")
    incident_description: str = Field(description="Detailed description of what happened")


class PropertyDamage(BaseModel):
    """Nested property damage assessment structure"""
    property_type: str = Field(description="Type of property (home, condo, auto, commercial, etc.)")
    points_of_impact: List[str] = Field(description="List of specific areas/points where damage occurred")
    damage_description: str = Field(description="Detailed description of the damage observed")
    estimated_damage_severity: str = Field(description="Estimated severity: minor, moderate, or severe")
    additional_details: Optional[str] = Field(default=None, description="Additional relevant details (witnesses, police reports, etc.)")


class PropertyClaim(BaseModel):
    """
    Enhanced property claim schema with double-nested structure.
    
    Supports specialty property claims with exactly 11 fields total across nested structures.
    Covers auto, home, condo, commercial, and other property types.
    Note: claim_id is generated during processing, not collected during intake.
    """
    
    # Nested structures (11 fields total across these 3 objects)
    claimant: ClaimantInfo = Field(description="Claimant contact and policy information")
    incident: IncidentDetails = Field(description="When, where, and how the incident occurred")
    property_damage: PropertyDamage = Field(description="Detailed property damage assessment")
    
    # System-generated identifier (not collected during intake)
    claim_id: Optional[str] = Field(default=None, description="System-generated unique claim identifier")

    def is_complete(self) -> bool:
        """Check if all essential intake fields are populated (claim_id not required for new claims)."""
        try:
            # Check claimant required fields
            if not (self.claimant.insured_name and 
                   str(self.claimant.insured_name).strip() and
                   self.claimant.insured_phone and 
                   str(self.claimant.insured_phone).strip()):
                return False
            
            # Check incident required fields
            if not (self.incident.incident_date and 
                   str(self.incident.incident_date).strip() and
                   self.incident.incident_time and 
                   str(self.incident.incident_time).strip() and
                   self.incident.incident_location and 
                   str(self.incident.incident_location).strip() and
                   self.incident.incident_description and 
                   str(self.incident.incident_description).strip()):
                return False
            
            # Check property damage required fields
            if not (self.property_damage.property_type and 
                   str(self.property_damage.property_type).strip() and
                   self.property_damage.points_of_impact and 
                   len(self.property_damage.points_of_impact) > 0 and
                   self.property_damage.damage_description and 
                   str(self.property_damage.damage_description).strip() and
                   self.property_damage.estimated_damage_severity and 
                   str(self.property_damage.estimated_damage_severity).strip()):
                return False
            
            return True
        except Exception:
            return False

    def get_missing_fields(self) -> List[str]:
        """Get list of missing required intake fields (claim_id not required for new claims)."""
        missing = []
        
        try:
            # Check claimant fields
            if not self.claimant.insured_name or not str(self.claimant.insured_name).strip():
                missing.append('claimant.insured_name')
            if not self.claimant.insured_phone or not str(self.claimant.insured_phone).strip():
                missing.append('claimant.insured_phone')
            
            # Check incident fields
            if not self.incident.incident_date or not str(self.incident.incident_date).strip():
                missing.append('incident.incident_date')
            if not self.incident.incident_time or not str(self.incident.incident_time).strip():
                missing.append('incident.incident_time')
            if not self.incident.incident_location or not str(self.incident.incident_location).strip():
                missing.append('incident.incident_location')
            if not self.incident.incident_description or not str(self.incident.incident_description).strip():
                missing.append('incident.incident_description')
            
            # Check property damage fields
            if not self.property_damage.property_type or not str(self.property_damage.property_type).strip():
                missing.append('property_damage.property_type')
            if not self.property_damage.points_of_impact or len(self.property_damage.points_of_impact) == 0:
                missing.append('property_damage.points_of_impact')
            if not self.property_damage.damage_description or not str(self.property_damage.damage_description).strip():
                missing.append('property_damage.damage_description')
            if not self.property_damage.estimated_damage_severity or not str(self.property_damage.estimated_damage_severity).strip():
                missing.append('property_damage.estimated_damage_severity')
            
        except Exception:
            missing.append('schema_validation_error')
        
        return missing

    @classmethod
    def get_field_collection_order(cls) -> List[tuple]:
        """Get the logical order for collecting fields with user-friendly descriptions (claim_id excluded - system generated)."""
        return [
            # Claimant identification first
            ('claimant.insured_name', "your full name"),
            ('claimant.insured_phone', "the best phone number to reach you"),
            ('claimant.policy_number', "your policy number (if available)"),
            
            # Incident details 
            ('incident.incident_date', "the date this happened"),
            ('incident.incident_time', "what time it occurred"),
            ('incident.incident_location', "where this took place"),
            ('incident.incident_description', "what exactly happened"),
            
            # Property damage assessment
            ('property_damage.property_type', "what type of property was affected"),
            ('property_damage.points_of_impact', "which specific areas were damaged"),
            ('property_damage.damage_description', "details about the damage you can see"),
            ('property_damage.estimated_damage_severity', "how severe the damage appears"),
            ('property_damage.additional_details', "any other important details")
        ]

# For backward compatibility, create an alias
SimplifiedClaim = PropertyClaim


# Example templates for testing different property types (claim_id will be generated)
EXAMPLE_HOME_CLAIM = PropertyClaim(
    claimant=ClaimantInfo(
        insured_name="Sarah Johnson",
        insured_phone="555-0123",
        policy_number="HOME-POL-12345"
    ),
    incident=IncidentDetails(
        incident_date="2025-09-22",
        incident_time="03:30",
        incident_location="123 Oak Street, Portland, OR",
        incident_description="Storm damage from high winds during severe weather event"
    ),
    property_damage=PropertyDamage(
        property_type="home",
        points_of_impact=["roof", "front porch", "living room window"],
        damage_description="Fallen tree branch punctured roof, damaged shingles, broke living room window",
        estimated_damage_severity="moderate",
        additional_details="Storm reported by National Weather Service, no injuries, neighbors witnessed event"
    )
)

EXAMPLE_AUTO_CLAIM = PropertyClaim(
    claimant=ClaimantInfo(
        insured_name="Mike Chen",
        insured_phone="555-0456",
        policy_number="AUTO-POL-67890"
    ),
    incident=IncidentDetails(
        incident_date="2025-09-21",
        incident_time="14:30",
        incident_location="Main St & 5th Ave intersection, Seattle, WA",
        incident_description="Rear-end collision while stopped at red light"
    ),
    property_damage=PropertyDamage(
        property_type="auto",
        points_of_impact=["rear bumper", "trunk", "rear lights"],
        damage_description="Significant rear-end damage, bumper detached, trunk won't close",
        estimated_damage_severity="moderate",
        additional_details="Police report filed, witness present, other driver admitted fault"
    )
)

EXAMPLE_COMMERCIAL_CLAIM = PropertyClaim(
    claimant=ClaimantInfo(
        insured_name="Lisa Rodriguez",
        insured_phone="555-0789",
        policy_number="COMM-POL-11111"
    ),
    incident=IncidentDetails(
        incident_date="2025-09-20",
        incident_time="09:15",
        incident_location="456 Business Plaza, Denver, CO",
        incident_description="Water pipe burst in ceiling causing flooding"
    ),
    property_damage=PropertyDamage(
        property_type="commercial", 
        points_of_impact=["office ceiling", "computer equipment", "carpet", "furniture"],
        damage_description="Water damage to electronics, soaked carpeting, ceiling tiles collapsed",
        estimated_damage_severity="severe",
        additional_details="Building maintenance notified, electricity shut off for safety, business operations halted"
    )
)

# Backward compatibility
EXAMPLE_SIMPLIFIED_CLAIM = EXAMPLE_AUTO_CLAIM
