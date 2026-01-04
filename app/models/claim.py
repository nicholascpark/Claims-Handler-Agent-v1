"""
Claim Data Models

Pydantic models for First Notice of Loss (FNOL) claim data.
These models define the structure for insurance claim information
collected through the voice agent conversation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Geo(BaseModel):
    """Geographic coordinates for incident location."""
    lat: Optional[float] = Field(default=None, description="Latitude of the incident location")
    lon: Optional[float] = Field(default=None, description="Longitude of the incident location")


class Contact(BaseModel):
    """Contact information for insured party."""
    phone: str = Field(default="", description="Primary contact phone number")
    email: str = Field(default="", description="Primary contact email address")


class Vehicle(BaseModel):
    """Vehicle information for claims involving vehicles."""
    role: str = Field(
        default="",
        description='Relationship of vehicle to claim (e.g., "insured_vehicle", "third_party_vehicle")'
    )
    vin: Optional[str] = Field(default=None, description="Vehicle VIN if known")
    make: Optional[str] = Field(default=None, description="Vehicle make")
    model: Optional[str] = Field(default=None, description="Vehicle model")
    year: Optional[str] = Field(default=None, description="Model year")
    license_plate: Optional[str] = Field(default=None, description="License plate number")
    damage_description: Optional[str] = Field(default=None, description="Description of damage")


class Injury(BaseModel):
    """Injury information for claims involving injuries."""
    person: Optional[str] = Field(default=None, description="Name or role of injured party")
    severity: Optional[str] = Field(default=None, description="Severity description (e.g., minor, serious)")
    description: Optional[str] = Field(default=None, description="Description of injuries")


class Witness(BaseModel):
    """Witness information."""
    full_name: str = Field(default="", description="Witness full name")
    phone: Optional[str] = Field(default=None, description="Witness phone number")
    statement: Optional[str] = Field(default=None, description="Witness statement")


class PoliceReport(BaseModel):
    """Police report information."""
    filed: bool = Field(default=False, description="Whether a police report was filed")
    agency: Optional[str] = Field(default=None, description="Police agency name")
    report_number: Optional[str] = Field(default=None, description="Police report number")
    officer_name: Optional[str] = Field(default=None, description="Responding officer name")
    contact_phone: Optional[str] = Field(default=None, description="Police contact phone")
    notes: Optional[List[str]] = Field(default=None, description="Additional notes")


class Location(BaseModel):
    """Incident location information."""
    address: Optional[str] = Field(default=None, description="Street address")
    highway: Optional[str] = Field(default=None, description="Highway name/number")
    direction: Optional[str] = Field(default=None, description="Direction of travel")
    exit: Optional[str] = Field(default=None, description="Exit number")
    city: str = Field(default="", description="City name")
    state: str = Field(default="", description="State/Province")
    country: str = Field(default="USA", description="Country")
    zip_code: Optional[str] = Field(default=None, description="ZIP/Postal code")
    geo: Geo = Field(default_factory=Geo, description="Geographic coordinates")


class Incident(BaseModel):
    """Incident details."""
    datetime: str = Field(default="", description="ISO-8601 timestamp of the incident")
    description: str = Field(default="", description="Description of what happened")
    location: Location = Field(default_factory=Location, description="Where it happened")
    vehicles_involved: List[Vehicle] = Field(default_factory=list, description="Vehicles involved")
    injuries: List[Injury] = Field(default_factory=list, description="Injuries reported")
    police_report: PoliceReport = Field(default_factory=PoliceReport, description="Police report info")
    witnesses: List[Witness] = Field(default_factory=list, description="Witness information")


class Policy(BaseModel):
    """Insurance policy information."""
    number: str = Field(default="", description="Policy number")
    type: str = Field(default="", description="Type of policy (auto, home, etc.)")


class Insured(BaseModel):
    """Insured party information."""
    full_name: str = Field(default="", description="Full legal name of insured")
    contact: Contact = Field(default_factory=Contact, description="Contact information")
    notes: Optional[List[str]] = Field(default=None, description="Additional notes")


class Claim(BaseModel):
    """Complete claim record."""
    claim_id: str = Field(default="", description="Unique claim identifier")
    date_reported: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO-8601 timestamp when claim was reported"
    )
    policy: Policy = Field(default_factory=Policy, description="Policy information")
    insured: Insured = Field(default_factory=Insured, description="Insured party information")
    incident: Incident = Field(default_factory=Incident, description="Incident details")


class FNOLPayload(BaseModel):
    """
    Root schema for First Notice of Loss extraction.
    This is the complete payload structure used by the trustcall extractor.
    """
    claim: Claim = Field(default_factory=Claim, description="The claim record")
    
    @classmethod
    def create_empty(cls) -> "FNOLPayload":
        """Create an empty FNOL payload with default values."""
        return cls(claim=Claim())
    
    def is_complete(self) -> bool:
        """
        Check if the payload has minimum required fields filled.
        Returns True if essential claim information is present.
        """
        claim = self.claim
        
        # Check required fields
        has_policy = bool(claim.policy.number)
        has_insured = bool(claim.insured.full_name)
        has_incident_date = bool(claim.incident.datetime)
        has_location = bool(claim.incident.location.city and claim.incident.location.state)
        has_description = bool(claim.incident.description)
        
        return all([has_policy, has_insured, has_incident_date, has_location, has_description])
    
    def get_missing_fields(self) -> List[str]:
        """Get list of missing required fields."""
        missing = []
        claim = self.claim
        
        if not claim.policy.number:
            missing.append("policy_number")
        if not claim.insured.full_name:
            missing.append("insured_name")
        if not claim.incident.datetime:
            missing.append("incident_date")
        if not claim.incident.location.city:
            missing.append("incident_city")
        if not claim.incident.location.state:
            missing.append("incident_state")
        if not claim.incident.description:
            missing.append("incident_description")
        
        return missing


# Default empty payload for new conversations
def create_default_payload() -> FNOLPayload:
    """Create a default FNOL payload for new conversations."""
    return FNOLPayload.create_empty()
