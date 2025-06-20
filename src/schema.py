from typing import List, Optional
from pydantic import BaseModel, Field

# ──────────────────────────────
# 1.  Leaf-level helper objects
# ──────────────────────────────

class Geo(BaseModel):
    lat: Optional[float] = Field(
        default=None, description="Latitude of the incident location"
    )
    lon: Optional[float] = Field(
        default=None, description="Longitude of the incident location"
    )

class Contact(BaseModel):
    phone: str = Field(description="Primary contact phone number")
    email: str = Field(description="Primary contact email address")

class Vehicle(BaseModel):
    role: str = Field(
        description='Relationship of vehicle to claim (e.g. "insured_vehicle", "third_party_vehicle")'
    )
    vin: Optional[str] = Field(default=None, description="Vehicle VIN if known")
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[str] = Field(
        default=None, description="Model year (string to allow unknown / partial)"
    )
    license_plate: Optional[str] = None
    damage_description: Optional[str] = None

class Injury(BaseModel):
    person: Optional[str] = Field(
        default=None, description="Name or role of injured party"
    )
    severity: Optional[str] = Field(
        default=None, description="Severity description (e.g. minor, serious)"
    )

class Witness(BaseModel):
    full_name: str
    phone: Optional[str] = None
    statement: Optional[str] = None

class PoliceReport(BaseModel):
    agency: Optional[str] = None
    report_number: Optional[str] = None
    officer_name: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[List[str]] = None

# ─────────────────────────
# 2.  Mid-level composites
# ─────────────────────────

class Location(BaseModel):
    highway: Optional[str] = None
    direction: Optional[str] = None
    exit: Optional[str] = None
    city: str
    state: str
    country: str
    geo: Geo

class Incident(BaseModel):
    datetime: str = Field(
        description="ISO-8601 timestamp of the incident (local time if available)"
    )
    location: Location
    description: str
    vehicles_involved: List[Vehicle]
    injuries: List[Injury]
    police_report: PoliceReport
    witnesses: List[Witness]

class Policy(BaseModel):
    number: str
    type: str

class Insured(BaseModel):
    full_name: str
    contact: Contact
    notes: Optional[List[str]] = None

# ──────────────────────────
# 3.  Top-level claim object
# ──────────────────────────

class Claim(BaseModel):
    claim_id: str
    date_reported: str = Field(
        description="ISO-8601 timestamp the claim was reported/created"
    )
    policy: Policy
    insured: Insured
    incident: Incident

class FNOLPayload(BaseModel):
    """Root schema expected by trustcall for First-Notice-of-Loss extraction."""
    claim: Claim


example_json = {
    "claim_id": "xxxxx",
    "date_reported": "YYYY-MM-DD HH:MM:SS",
    "policy": {"number": "POLXXXXXX", "type": "Type of Policy"},
    "insured": {"full_name": "John Doe", "contact": {"phone": "123-456-7890", "email": "john.doe@example.com"}},
    "incident": {
        "description": "Accident",
        "datetime": "YYYY-MM-DD HH:MM:SS",
        "location": {"address": "Accident Location", "city": "City", "state": "State", "country": "Country", "geo": {"lat": 0.0, "lon": 0.0}},
        "vehicles_involved": [{"make": "Car Make", "model": "Car Model", "year": "xxxx", "role": "Driver"}],
        "injuries": [{"type": "Injury Type", "severity": "Injury Severity"}],
        "police_report": {"report_number": "123456", "officer_name": "Officer Name", "contact_phone": "123-456-7890"},
        "witnesses": [{"full_name": "Witness Name", "contact": {"phone": "xxx-xxx-xxxx", "email": "witness@example.com"}}]
    }
}