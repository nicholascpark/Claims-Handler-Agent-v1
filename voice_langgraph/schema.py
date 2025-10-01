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
    policy_number: Optional[str] = Field(default=None, description="Insurance policy number (POL-XXXXXX format)")


class IncidentLocation(BaseModel):
    """Nested incident location structure with detailed address information"""
    incident_street_address: str = Field(description="Street address where incident occurred")
    incident_zip_code: str = Field(description="Zip code or postal code of incident location")


class IncidentDetails(BaseModel):
    """Nested incident information structure"""
    incident_date: str = Field(description="Date of incident (YYYY-MM-DD format)")
    incident_time: str = Field(description="Time of incident (HH:MM format)")
    incident_location: IncidentLocation = Field(description="Detailed location where incident occurred")
    incident_description: str = Field(description="Detailed description of what happened")


class PersonalInjury(BaseModel):
    """Nested personal injury assessment structure"""
    points_of_impact: List[str] = Field(description="List of specific body parts or areas affected by injury")
    injury_description: str = Field(description="Detailed description of the injuries sustained")
    severity: str = Field(description="Injury severity: minor, moderate, or severe")


class PropertyDamage(BaseModel):
    """Nested property damage assessment structure"""
    property_type: str = Field(description="Type of property (home, condo, auto, commercial, etc.)")
    points_of_impact: List[str] = Field(description="List of specific areas/points where damage occurred")
    damage_description: str = Field(description="Detailed description of the damage observed")
    estimated_damage_severity: str = Field(description="Estimated severity: minor, moderate, or severe")


class PropertyClaim(BaseModel):
    """
    Enhanced property claim schema with double-nested structure.
    
    Supports specialty property claims with nested structures for location, injuries, and property damage.
    Covers auto, home, condo, commercial, and other property types.
    Note: claim_id is generated during processing, not collected during intake.
    """
    
    # Nested structures
    claimant: ClaimantInfo = Field(description="Claimant contact and policy information")
    incident: IncidentDetails = Field(description="When, where, and how the incident occurred")
    personal_injury: Optional[PersonalInjury] = Field(default=None, description="Personal injury details if applicable")
    property_damage: Optional[PropertyDamage] = Field(default=None, description="Property damage assessment if applicable")
    
    # System-generated identifier (not collected during intake)
    claim_id: Optional[str] = Field(default=None, description="System-generated unique claim identifier")

    def is_complete(self) -> bool:
        """Check if all essential intake fields are populated (claim_id not required for new claims)."""
        try:
            # Helper to check if value is valid (not empty and not a placeholder)
            def is_valid_value(value: str) -> bool:
                if not value or not str(value).strip():
                    return False
                value_lower = str(value).lower().strip()
                # Reject placeholder values
                placeholders = ['unspecified', 'unknown', 'not provided', 'n/a', 'none', 'tbd', 'to be determined']
                return not any(placeholder in value_lower for placeholder in placeholders)
            
            # Check claimant required fields
            if not (is_valid_value(self.claimant.insured_name) and
                   is_valid_value(self.claimant.insured_phone)):
                return False
            
            # Check incident required fields
            if not (is_valid_value(self.incident.incident_date) and
                   is_valid_value(self.incident.incident_time) and
                   is_valid_value(self.incident.incident_location.incident_street_address) and
                   is_valid_value(self.incident.incident_location.incident_zip_code) and
                   is_valid_value(self.incident.incident_description)):
                return False
            
            # At least one of personal_injury or property_damage must be present and complete
            has_injury = False
            has_damage = False
            
            if self.personal_injury:
                if (self.personal_injury.points_of_impact and 
                    len(self.personal_injury.points_of_impact) > 0 and
                    is_valid_value(self.personal_injury.injury_description) and
                    is_valid_value(self.personal_injury.severity)):
                    has_injury = True
            
            if self.property_damage:
                if (is_valid_value(self.property_damage.property_type) and
                    self.property_damage.points_of_impact and 
                    len(self.property_damage.points_of_impact) > 0 and
                    is_valid_value(self.property_damage.damage_description) and
                    is_valid_value(self.property_damage.estimated_damage_severity)):
                    has_damage = True
            
            # At least one type of damage (injury or property) must be complete
            return has_injury or has_damage
            
        except Exception:
            return False

    def get_missing_fields(self) -> List[str]:
        """Get list of missing required intake fields (claim_id not required for new claims)."""
        missing = []
        
        # Helper to check if value is valid (not empty and not a placeholder)
        def is_valid_value(value: str) -> bool:
            if not value or not str(value).strip():
                return False
            value_lower = str(value).lower().strip()
            # Reject placeholder values
            placeholders = ['unspecified', 'unknown', 'not provided', 'n/a', 'none', 'tbd', 'to be determined']
            return not any(placeholder in value_lower for placeholder in placeholders)
        
        try:
            # Check claimant fields
            if not is_valid_value(self.claimant.insured_name):
                missing.append('claimant.insured_name')
            if not is_valid_value(self.claimant.insured_phone):
                missing.append('claimant.insured_phone')
            
            # Check incident fields
            if not is_valid_value(self.incident.incident_date):
                missing.append('incident.incident_date')
            if not is_valid_value(self.incident.incident_time):
                missing.append('incident.incident_time')
            if not is_valid_value(self.incident.incident_location.incident_street_address):
                missing.append('incident.incident_location.incident_street_address')
            if not is_valid_value(self.incident.incident_location.incident_zip_code):
                missing.append('incident.incident_location.incident_zip_code')
            if not is_valid_value(self.incident.incident_description):
                missing.append('incident.incident_description')
            
            # Check if at least one of personal_injury or property_damage is present
            has_injury_data = self.personal_injury is not None
            has_damage_data = self.property_damage is not None
            
            # Check personal injury fields if present
            if has_injury_data:
                if not self.personal_injury.points_of_impact or len(self.personal_injury.points_of_impact) == 0:
                    missing.append('personal_injury.points_of_impact')
                if not is_valid_value(self.personal_injury.injury_description):
                    missing.append('personal_injury.injury_description')
                if not is_valid_value(self.personal_injury.severity):
                    missing.append('personal_injury.severity')
            
            # Check property damage fields if present
            if has_damage_data:
                if not is_valid_value(self.property_damage.property_type):
                    missing.append('property_damage.property_type')
                if not self.property_damage.points_of_impact or len(self.property_damage.points_of_impact) == 0:
                    missing.append('property_damage.points_of_impact')
                if not is_valid_value(self.property_damage.damage_description):
                    missing.append('property_damage.damage_description')
                if not is_valid_value(self.property_damage.estimated_damage_severity):
                    missing.append('property_damage.estimated_damage_severity')
            
            # If neither injury nor damage is specified, we need to know which one applies
            if not has_injury_data and not has_damage_data:
                missing.append('damage_type_unknown')
            
        except Exception:
            missing.append('schema_validation_error')
        
        return missing

    @classmethod
    def get_field_collection_order(cls) -> List[tuple[str, str]]:
        """Return ordered (field_path, friendly_name) pairs for intake.

        The order reflects the desired conversational collection sequence.
        """
        return [
            # Claimant first
            ("claimant.insured_name", "full name"),
            ("claimant.insured_phone", "phone number"),
            ("claimant.policy_number", "policy number"),
            # Incident details
            ("incident.incident_date", "date of incident"),
            ("incident.incident_time", "time of incident"),
            ("incident.incident_location.incident_street_address", "incident address"),
            ("incident.incident_location.incident_zip_code", "incident zip/postal code"),
            ("incident.incident_description", "what happened"),
            # Damage details (either personal injury or property damage)
            ("personal_injury.points_of_impact", "injury points of impact"),
            ("personal_injury.injury_description", "injury description"),
            ("personal_injury.severity", "injury severity"),
            ("property_damage.property_type", "property type"),
            ("property_damage.points_of_impact", "damaged areas"),
            ("property_damage.damage_description", "damage description"),
            ("property_damage.estimated_damage_severity", "damage severity"),
        ]


    @classmethod
    def create_empty(cls) -> "PropertyClaim":
        """Factory method to create an empty PropertyClaim with all fields as empty strings.
        
        This ensures all required fields exist in the structure from the beginning,
        making it easier for trustcall to patch values incrementally.
        """
        return cls(
            claimant=ClaimantInfo(
                insured_name="",
                insured_phone="",
                policy_number=None  # Optional field
            ),
            incident=IncidentDetails(
                incident_date="",
                incident_time="",
                incident_location=IncidentLocation(
                    incident_street_address="",
                    incident_zip_code=""
                ),
                incident_description=""
            ),
            personal_injury=None,  # Optional - only if personal injury involved
            property_damage=None,  # Optional - only if property damage involved
            claim_id=None  # System-generated
        )

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
        incident_location=IncidentLocation(
            incident_street_address="123 Oak Street, Portland, OR",
            incident_zip_code="97201"
        ),
        incident_description="Storm damage from high winds during severe weather event"
    ),
    property_damage=PropertyDamage(
        property_type="home",
        points_of_impact=["roof", "front porch", "living room window"],
        damage_description="Fallen tree branch punctured roof, damaged shingles, broke living room window",
        estimated_damage_severity="moderate"
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
        incident_location=IncidentLocation(
            incident_street_address="Main St & 5th Ave intersection, Seattle, WA",
            incident_zip_code="98101"
        ),
        incident_description="Rear-end collision while stopped at red light"
    ),
    personal_injury=PersonalInjury(
        points_of_impact=["neck", "lower back"],
        injury_description="Whiplash from sudden impact, lower back pain",
        severity="minor"
    ),
    property_damage=PropertyDamage(
        property_type="auto",
        points_of_impact=["rear bumper", "trunk", "rear lights"],
        damage_description="Significant rear-end damage, bumper detached, trunk won't close",
        estimated_damage_severity="moderate"
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
        incident_location=IncidentLocation(
            incident_street_address="456 Business Plaza, Denver, CO",
            incident_zip_code="80202"
        ),
        incident_description="Water pipe burst in ceiling causing flooding"
    ),
    property_damage=PropertyDamage(
        property_type="commercial", 
        points_of_impact=["office ceiling", "computer equipment", "carpet", "furniture"],
        damage_description="Water damage to electronics, soaked carpeting, ceiling tiles collapsed",
        estimated_damage_severity="severe"
    )
)

# Backward compatibility
EXAMPLE_SIMPLIFIED_CLAIM = EXAMPLE_AUTO_CLAIM
