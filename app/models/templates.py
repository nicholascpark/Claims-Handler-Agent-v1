"""
Industry Templates

Pre-built form configurations for common industries.
Users can start with a template and customize it for their needs.
"""

from typing import List, Dict, Optional
from app.models.form_config import (
    FormConfig, 
    FormField, 
    BusinessProfile, 
    AgentConfig,
    FieldType, 
    Industry, 
    AgentTone,
    TTSVoice
)


def _create_field(
    name: str,
    label: str,
    field_type: FieldType = FieldType.TEXT,
    required: bool = True,
    description: str = "",
    options: Optional[List[str]] = None,
    example: Optional[str] = None,
    order: int = 0
) -> FormField:
    """Helper to create a FormField."""
    return FormField(
        name=name,
        label=label,
        type=field_type,
        required=required,
        description=description,
        options=options,
        example=example,
        order=order
    )


# =============================================================================
# LEGAL SERVICES TEMPLATE
# =============================================================================

LEGAL_INTAKE_FIELDS: List[FormField] = [
    _create_field(
        name="full_name",
        label="Full Name",
        field_type=FieldType.NAME,
        description="Client's full legal name",
        example="John Michael Smith",
        order=1
    ),
    _create_field(
        name="phone",
        label="Phone Number",
        field_type=FieldType.PHONE,
        description="Best phone number to reach the client",
        example="555-123-4567",
        order=2
    ),
    _create_field(
        name="email",
        label="Email Address",
        field_type=FieldType.EMAIL,
        required=False,
        description="Client's email address",
        example="john.smith@email.com",
        order=3
    ),
    _create_field(
        name="case_type",
        label="Type of Case",
        field_type=FieldType.SELECT,
        description="What type of legal matter is this?",
        options=[
            "Personal Injury - Car Accident",
            "Personal Injury - Slip and Fall",
            "Personal Injury - Medical Malpractice",
            "Personal Injury - Workplace Injury",
            "Family Law - Divorce",
            "Family Law - Custody",
            "Criminal Defense",
            "Immigration",
            "Business/Corporate",
            "Estate Planning",
            "Real Estate",
            "Other"
        ],
        order=4
    ),
    _create_field(
        name="incident_date",
        label="Date of Incident",
        field_type=FieldType.DATE,
        description="When did the incident occur?",
        example="2024-01-15",
        order=5
    ),
    _create_field(
        name="incident_description",
        label="Brief Description",
        field_type=FieldType.TEXTAREA,
        description="Brief description of what happened",
        order=6
    ),
    _create_field(
        name="injuries",
        label="Injuries or Damages",
        field_type=FieldType.TEXTAREA,
        required=False,
        description="Description of any injuries or damages",
        order=7
    ),
    _create_field(
        name="has_attorney",
        label="Currently Have an Attorney?",
        field_type=FieldType.BOOLEAN,
        description="Do they currently have legal representation?",
        order=8
    ),
    _create_field(
        name="best_time_to_call",
        label="Best Time to Call",
        field_type=FieldType.TEXT,
        required=False,
        description="When is the best time to call back?",
        example="Afternoons after 2pm",
        order=9
    ),
    _create_field(
        name="how_heard_about_us",
        label="How Did You Hear About Us?",
        field_type=FieldType.SELECT,
        required=False,
        options=["Google Search", "Referral", "TV Ad", "Billboard", "Social Media", "Other"],
        order=10
    ),
]

LEGAL_TEMPLATE = FormConfig(
    id="template_legal",
    name="Legal Client Intake",
    business=BusinessProfile(
        name="Your Law Firm",
        industry=Industry.LEGAL,
        description="Legal services firm"
    ),
    agent=AgentConfig(
        name="Sarah",
        tone=AgentTone.PROFESSIONAL,
        voice=TTSVoice.NOVA,
        custom_greeting="Hello, thank you for calling. I'm Sarah, a virtual assistant. I'll gather some information to help our attorneys understand your situation. Everything you share is confidential. May I start by getting your name?"
    ),
    fields=LEGAL_INTAKE_FIELDS
)


# =============================================================================
# HEALTHCARE TEMPLATE
# =============================================================================

HEALTHCARE_INTAKE_FIELDS: List[FormField] = [
    _create_field(
        name="patient_name",
        label="Patient Name",
        field_type=FieldType.NAME,
        description="Patient's full name",
        order=1
    ),
    _create_field(
        name="date_of_birth",
        label="Date of Birth",
        field_type=FieldType.DATE,
        description="Patient's date of birth",
        order=2
    ),
    _create_field(
        name="phone",
        label="Phone Number",
        field_type=FieldType.PHONE,
        description="Contact phone number",
        order=3
    ),
    _create_field(
        name="reason_for_visit",
        label="Reason for Visit",
        field_type=FieldType.SELECT,
        description="Primary reason for scheduling",
        options=[
            "New Patient - General Checkup",
            "New Patient - Specific Concern",
            "Follow-up Appointment",
            "Prescription Refill",
            "Lab Results Review",
            "Urgent Care Needed",
            "Other"
        ],
        order=4
    ),
    _create_field(
        name="symptoms",
        label="Current Symptoms",
        field_type=FieldType.TEXTAREA,
        description="Describe current symptoms or concerns",
        order=5
    ),
    _create_field(
        name="symptom_duration",
        label="How Long Have You Had These Symptoms?",
        field_type=FieldType.TEXT,
        description="Duration of symptoms",
        example="About 3 days",
        order=6
    ),
    _create_field(
        name="current_medications",
        label="Current Medications",
        field_type=FieldType.TEXTAREA,
        required=False,
        description="List of current medications",
        order=7
    ),
    _create_field(
        name="allergies",
        label="Known Allergies",
        field_type=FieldType.TEXT,
        required=False,
        description="Any known allergies",
        example="Penicillin, Shellfish",
        order=8
    ),
    _create_field(
        name="insurance_provider",
        label="Insurance Provider",
        field_type=FieldType.TEXT,
        required=False,
        description="Health insurance company name",
        order=9
    ),
    _create_field(
        name="preferred_date",
        label="Preferred Appointment Date",
        field_type=FieldType.DATE,
        required=False,
        description="When would they like to come in?",
        order=10
    ),
    _create_field(
        name="urgency",
        label="Urgency Level",
        field_type=FieldType.SELECT,
        description="How urgent is this?",
        options=["Routine", "Soon (within a week)", "Urgent (within 24-48 hours)", "Emergency"],
        order=11
    ),
]

HEALTHCARE_TEMPLATE = FormConfig(
    id="template_healthcare",
    name="Patient Intake",
    business=BusinessProfile(
        name="Your Medical Practice",
        industry=Industry.HEALTHCARE,
        description="Healthcare provider"
    ),
    agent=AgentConfig(
        name="Alex",
        tone=AgentTone.EMPATHETIC,
        voice=TTSVoice.NOVA,
        custom_greeting="Hello, thank you for calling. I'm Alex, a virtual assistant here to help schedule your appointment. I'll ask a few questions to make sure we can best assist you. May I start with your name?"
    ),
    fields=HEALTHCARE_INTAKE_FIELDS
)


# =============================================================================
# REAL ESTATE TEMPLATE
# =============================================================================

REAL_ESTATE_FIELDS: List[FormField] = [
    _create_field(
        name="full_name",
        label="Full Name",
        field_type=FieldType.NAME,
        order=1
    ),
    _create_field(
        name="phone",
        label="Phone Number",
        field_type=FieldType.PHONE,
        order=2
    ),
    _create_field(
        name="email",
        label="Email Address",
        field_type=FieldType.EMAIL,
        required=False,
        order=3
    ),
    _create_field(
        name="inquiry_type",
        label="Are You Looking to Buy or Sell?",
        field_type=FieldType.SELECT,
        options=["Buying", "Selling", "Both", "Renting", "Just Browsing"],
        order=4
    ),
    _create_field(
        name="property_type",
        label="Property Type",
        field_type=FieldType.SELECT,
        options=["Single Family Home", "Condo/Townhouse", "Multi-Family", "Land", "Commercial", "Other"],
        order=5
    ),
    _create_field(
        name="location",
        label="Preferred Location/Area",
        field_type=FieldType.TEXT,
        description="City, neighborhood, or area of interest",
        order=6
    ),
    _create_field(
        name="budget",
        label="Budget Range",
        field_type=FieldType.SELECT,
        options=[
            "Under $200,000",
            "$200,000 - $400,000",
            "$400,000 - $600,000",
            "$600,000 - $800,000",
            "$800,000 - $1,000,000",
            "Over $1,000,000"
        ],
        order=7
    ),
    _create_field(
        name="bedrooms",
        label="Bedrooms Needed",
        field_type=FieldType.SELECT,
        required=False,
        options=["1", "2", "3", "4", "5+"],
        order=8
    ),
    _create_field(
        name="timeline",
        label="Purchase/Sell Timeline",
        field_type=FieldType.SELECT,
        options=["ASAP", "1-3 months", "3-6 months", "6-12 months", "Just exploring"],
        order=9
    ),
    _create_field(
        name="pre_approved",
        label="Pre-Approved for Mortgage?",
        field_type=FieldType.BOOLEAN,
        required=False,
        description="For buyers: are they pre-approved?",
        order=10
    ),
    _create_field(
        name="additional_requirements",
        label="Special Requirements",
        field_type=FieldType.TEXTAREA,
        required=False,
        description="Any must-haves or deal-breakers",
        order=11
    ),
]

REAL_ESTATE_TEMPLATE = FormConfig(
    id="template_real_estate",
    name="Real Estate Lead Intake",
    business=BusinessProfile(
        name="Your Real Estate Agency",
        industry=Industry.REAL_ESTATE,
        description="Real estate services"
    ),
    agent=AgentConfig(
        name="Jordan",
        tone=AgentTone.FRIENDLY,
        voice=TTSVoice.ALLOY,
        custom_greeting="Hi there! Thanks for reaching out. I'm Jordan, your virtual assistant. I'd love to learn more about what you're looking for so one of our agents can help you find the perfect property. Let's start with your name?"
    ),
    fields=REAL_ESTATE_FIELDS
)


# =============================================================================
# HOME SERVICES TEMPLATE
# =============================================================================

HOME_SERVICES_FIELDS: List[FormField] = [
    _create_field(
        name="full_name",
        label="Full Name",
        field_type=FieldType.NAME,
        order=1
    ),
    _create_field(
        name="phone",
        label="Phone Number",
        field_type=FieldType.PHONE,
        order=2
    ),
    _create_field(
        name="address",
        label="Service Address",
        field_type=FieldType.ADDRESS,
        description="Where is the service needed?",
        order=3
    ),
    _create_field(
        name="service_type",
        label="Type of Service Needed",
        field_type=FieldType.SELECT,
        options=[
            "Plumbing",
            "Electrical",
            "HVAC/Heating/Cooling",
            "Roofing",
            "Painting",
            "Flooring",
            "General Handyman",
            "Landscaping",
            "Cleaning",
            "Other"
        ],
        order=4
    ),
    _create_field(
        name="problem_description",
        label="Describe the Problem",
        field_type=FieldType.TEXTAREA,
        description="What needs to be fixed or done?",
        order=5
    ),
    _create_field(
        name="urgency",
        label="How Urgent Is This?",
        field_type=FieldType.SELECT,
        options=["Emergency (ASAP)", "Urgent (within 24 hours)", "Soon (this week)", "Flexible"],
        order=6
    ),
    _create_field(
        name="property_type",
        label="Property Type",
        field_type=FieldType.SELECT,
        options=["House", "Apartment/Condo", "Townhouse", "Commercial", "Other"],
        order=7
    ),
    _create_field(
        name="availability",
        label="When Are You Available?",
        field_type=FieldType.TEXT,
        description="Best days/times for service",
        example="Weekday mornings",
        order=8
    ),
    _create_field(
        name="homeowner",
        label="Are You the Homeowner?",
        field_type=FieldType.BOOLEAN,
        order=9
    ),
]

HOME_SERVICES_TEMPLATE = FormConfig(
    id="template_home_services",
    name="Service Request Intake",
    business=BusinessProfile(
        name="Your Home Services Company",
        industry=Industry.HOME_SERVICES,
        description="Home repair and maintenance services"
    ),
    agent=AgentConfig(
        name="Mike",
        tone=AgentTone.FRIENDLY,
        voice=TTSVoice.ONYX,
        custom_greeting="Hi! Thanks for calling. I'm Mike, your virtual assistant. I'll get some details about what you need help with so we can get someone out to you. First, can I get your name?"
    ),
    fields=HOME_SERVICES_FIELDS
)


# =============================================================================
# RECRUITING TEMPLATE
# =============================================================================

RECRUITING_FIELDS: List[FormField] = [
    _create_field(
        name="full_name",
        label="Full Name",
        field_type=FieldType.NAME,
        order=1
    ),
    _create_field(
        name="phone",
        label="Phone Number",
        field_type=FieldType.PHONE,
        order=2
    ),
    _create_field(
        name="email",
        label="Email Address",
        field_type=FieldType.EMAIL,
        order=3
    ),
    _create_field(
        name="position_interest",
        label="Position Interested In",
        field_type=FieldType.TEXT,
        description="What role are they applying for?",
        order=4
    ),
    _create_field(
        name="years_experience",
        label="Years of Experience",
        field_type=FieldType.SELECT,
        options=["0-1 years", "1-3 years", "3-5 years", "5-10 years", "10+ years"],
        order=5
    ),
    _create_field(
        name="current_role",
        label="Current/Most Recent Job Title",
        field_type=FieldType.TEXT,
        order=6
    ),
    _create_field(
        name="key_skills",
        label="Key Skills",
        field_type=FieldType.TEXTAREA,
        description="Main skills and qualifications",
        order=7
    ),
    _create_field(
        name="availability",
        label="When Can You Start?",
        field_type=FieldType.SELECT,
        options=["Immediately", "2 weeks notice", "1 month", "Other"],
        order=8
    ),
    _create_field(
        name="salary_expectation",
        label="Salary Expectations",
        field_type=FieldType.TEXT,
        required=False,
        description="Expected salary range",
        order=9
    ),
    _create_field(
        name="work_authorization",
        label="Authorized to Work in the US?",
        field_type=FieldType.BOOLEAN,
        order=10
    ),
    _create_field(
        name="willing_to_relocate",
        label="Willing to Relocate?",
        field_type=FieldType.BOOLEAN,
        required=False,
        order=11
    ),
]

RECRUITING_TEMPLATE = FormConfig(
    id="template_recruiting",
    name="Candidate Screening",
    business=BusinessProfile(
        name="Your Company",
        industry=Industry.RECRUITING,
        description="Talent acquisition"
    ),
    agent=AgentConfig(
        name="Taylor",
        tone=AgentTone.PROFESSIONAL,
        voice=TTSVoice.SHIMMER,
        custom_greeting="Hello! Thank you for your interest in joining our team. I'm Taylor, a virtual recruiter. I'll ask you a few questions to learn more about your background. Let's start with your name?"
    ),
    fields=RECRUITING_FIELDS
)


# =============================================================================
# FINANCIAL SERVICES TEMPLATE
# =============================================================================

FINANCIAL_FIELDS: List[FormField] = [
    _create_field(
        name="full_name",
        label="Full Name",
        field_type=FieldType.NAME,
        order=1
    ),
    _create_field(
        name="phone",
        label="Phone Number",
        field_type=FieldType.PHONE,
        order=2
    ),
    _create_field(
        name="email",
        label="Email Address",
        field_type=FieldType.EMAIL,
        order=3
    ),
    _create_field(
        name="service_interest",
        label="What Service Are You Interested In?",
        field_type=FieldType.SELECT,
        options=[
            "Personal Loan",
            "Mortgage/Home Loan",
            "Auto Loan",
            "Business Loan",
            "Debt Consolidation",
            "Investment Advisory",
            "Insurance",
            "Tax Services",
            "Other"
        ],
        order=4
    ),
    _create_field(
        name="loan_amount",
        label="Estimated Amount Needed",
        field_type=FieldType.CURRENCY,
        required=False,
        description="Approximate loan amount",
        order=5
    ),
    _create_field(
        name="employment_status",
        label="Employment Status",
        field_type=FieldType.SELECT,
        options=["Employed Full-Time", "Employed Part-Time", "Self-Employed", "Retired", "Unemployed", "Other"],
        order=6
    ),
    _create_field(
        name="annual_income",
        label="Approximate Annual Income",
        field_type=FieldType.SELECT,
        required=False,
        options=[
            "Under $30,000",
            "$30,000 - $50,000",
            "$50,000 - $75,000",
            "$75,000 - $100,000",
            "$100,000 - $150,000",
            "Over $150,000"
        ],
        order=7
    ),
    _create_field(
        name="credit_score_range",
        label="Credit Score Range",
        field_type=FieldType.SELECT,
        required=False,
        options=["Excellent (750+)", "Good (700-749)", "Fair (650-699)", "Below 650", "Not Sure"],
        order=8
    ),
    _create_field(
        name="timeline",
        label="When Do You Need This?",
        field_type=FieldType.SELECT,
        options=["ASAP", "Within 1 month", "1-3 months", "Just exploring"],
        order=9
    ),
    _create_field(
        name="best_time_to_call",
        label="Best Time to Call",
        field_type=FieldType.TEXT,
        required=False,
        order=10
    ),
]

FINANCIAL_TEMPLATE = FormConfig(
    id="template_financial",
    name="Financial Services Inquiry",
    business=BusinessProfile(
        name="Your Financial Services",
        industry=Industry.FINANCIAL,
        description="Financial services provider"
    ),
    agent=AgentConfig(
        name="Morgan",
        tone=AgentTone.PROFESSIONAL,
        voice=TTSVoice.NOVA,
        custom_greeting="Hello, thank you for calling. I'm Morgan, a virtual assistant. I'll gather some information to connect you with the right financial advisor. All information is confidential. May I start with your name?"
    ),
    fields=FINANCIAL_FIELDS
)


# =============================================================================
# INSURANCE TEMPLATE (Original FNOL-style)
# =============================================================================

INSURANCE_FIELDS: List[FormField] = [
    _create_field(
        name="policy_number",
        label="Policy Number",
        field_type=FieldType.TEXT,
        description="Insurance policy number",
        example="POL-12345678",
        order=1
    ),
    _create_field(
        name="insured_name",
        label="Policyholder Name",
        field_type=FieldType.NAME,
        description="Name as it appears on the policy",
        order=2
    ),
    _create_field(
        name="phone",
        label="Contact Phone",
        field_type=FieldType.PHONE,
        order=3
    ),
    _create_field(
        name="incident_date",
        label="Date of Incident",
        field_type=FieldType.DATE,
        order=4
    ),
    _create_field(
        name="incident_time",
        label="Time of Incident",
        field_type=FieldType.TIME,
        required=False,
        order=5
    ),
    _create_field(
        name="incident_location",
        label="Location of Incident",
        field_type=FieldType.ADDRESS,
        description="Where did this happen?",
        order=6
    ),
    _create_field(
        name="incident_description",
        label="What Happened?",
        field_type=FieldType.TEXTAREA,
        description="Description of the incident",
        order=7
    ),
    _create_field(
        name="damage_description",
        label="Describe the Damage",
        field_type=FieldType.TEXTAREA,
        order=8
    ),
    _create_field(
        name="injuries",
        label="Were There Any Injuries?",
        field_type=FieldType.TEXTAREA,
        required=False,
        order=9
    ),
    _create_field(
        name="police_report_filed",
        label="Was a Police Report Filed?",
        field_type=FieldType.BOOLEAN,
        order=10
    ),
    _create_field(
        name="police_report_number",
        label="Police Report Number",
        field_type=FieldType.TEXT,
        required=False,
        order=11
    ),
    _create_field(
        name="other_party_info",
        label="Other Party Information",
        field_type=FieldType.TEXTAREA,
        required=False,
        description="Information about other parties involved",
        order=12
    ),
]

INSURANCE_TEMPLATE = FormConfig(
    id="template_insurance",
    name="Insurance Claim Intake",
    business=BusinessProfile(
        name="Your Insurance Company",
        industry=Industry.INSURANCE,
        description="Insurance claims processing"
    ),
    agent=AgentConfig(
        name="Alex",
        tone=AgentTone.EMPATHETIC,
        voice=TTSVoice.NOVA,
        custom_greeting="Hello, I'm sorry to hear you need to file a claim. I'm Alex, a virtual assistant here to help gather the details. This call may be recorded for quality purposes. To begin, may I have your policy number?"
    ),
    fields=INSURANCE_FIELDS
)


# =============================================================================
# TEMPLATE REGISTRY
# =============================================================================

TEMPLATES: Dict[str, FormConfig] = {
    "legal": LEGAL_TEMPLATE,
    "healthcare": HEALTHCARE_TEMPLATE,
    "real_estate": REAL_ESTATE_TEMPLATE,
    "home_services": HOME_SERVICES_TEMPLATE,
    "recruiting": RECRUITING_TEMPLATE,
    "financial": FINANCIAL_TEMPLATE,
    "insurance": INSURANCE_TEMPLATE,
}


def get_template(industry: str) -> FormConfig:
    """
    Get a template by industry name.
    
    Args:
        industry: Industry identifier (e.g., 'legal', 'healthcare')
        
    Returns:
        FormConfig template for the industry
        
    Raises:
        KeyError: If industry template doesn't exist
    """
    if industry not in TEMPLATES:
        raise KeyError(f"No template for industry: {industry}. Available: {list(TEMPLATES.keys())}")
    return TEMPLATES[industry].model_copy(deep=True)


def list_templates() -> List[Dict]:
    """
    List all available templates with summary info.
    
    Returns:
        List of template summaries
    """
    return [
        {
            "id": template.id,
            "name": template.name,
            "industry": template.business.industry,
            "field_count": len(template.fields),
            "description": template.business.description
        }
        for template in TEMPLATES.values()
    ]
