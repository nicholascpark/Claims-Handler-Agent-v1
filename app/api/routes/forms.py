"""
Form Configuration API endpoints.

CRUD operations for form configurations and templates.
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.models.form_config import (
    FormConfig, 
    FormField, 
    BusinessProfile, 
    AgentConfig,
    FieldType,
    Industry,
    AgentTone,
    TTSVoice,
)
from app.models.templates import TEMPLATES, get_template, list_templates
from app.agents.dynamic_agent import clear_agent_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/forms", tags=["Forms"])


# =============================================================================
# In-memory storage (replace with database in production)
# =============================================================================

_form_configs: dict[str, FormConfig] = {}


# =============================================================================
# Request/Response Models
# =============================================================================

class FieldCreate(BaseModel):
    """Request model for creating a field."""
    name: str = Field(..., description="Internal field name")
    label: str = Field(..., description="Display label")
    type: str = Field(default="text", description="Field type")
    description: str = Field(default="", description="Help text")
    required: bool = Field(default=True)
    options: Optional[List[str]] = Field(default=None)
    example: Optional[str] = Field(default=None)
    order: int = Field(default=0)


class BusinessProfileCreate(BaseModel):
    """Request model for business profile."""
    name: str = Field(..., description="Business name")
    industry: str = Field(default="other")
    description: Optional[str] = Field(default=None)


class AgentConfigCreate(BaseModel):
    """Request model for agent configuration."""
    name: str = Field(default="Alex")
    tone: str = Field(default="professional")
    voice: str = Field(default="nova")
    custom_greeting: Optional[str] = Field(default=None)
    custom_closing: Optional[str] = Field(default=None)


class FormConfigCreate(BaseModel):
    """Request model for creating a form configuration."""
    name: str = Field(..., description="Form name")
    business: BusinessProfileCreate
    agent: Optional[AgentConfigCreate] = Field(default=None)
    fields: List[FieldCreate] = Field(default_factory=list)


class FormConfigUpdate(BaseModel):
    """Request model for updating a form configuration."""
    name: Optional[str] = None
    business: Optional[BusinessProfileCreate] = None
    agent: Optional[AgentConfigCreate] = None
    fields: Optional[List[FieldCreate]] = None


class FormConfigResponse(BaseModel):
    """Response model for form configuration."""
    id: str
    name: str
    business: dict
    agent: dict
    fields: List[dict]
    created_at: str
    updated_at: str
    is_active: bool
    field_count: int
    required_field_count: int


class TemplateInfo(BaseModel):
    """Template summary information."""
    id: str
    name: str
    industry: str
    field_count: int
    description: Optional[str]


# =============================================================================
# Helper Functions
# =============================================================================

def _form_config_to_response(config: FormConfig) -> FormConfigResponse:
    """Convert FormConfig to response model."""
    return FormConfigResponse(
        id=config.id,
        name=config.name,
        business=config.business.model_dump(),
        agent=config.agent.model_dump(),
        fields=[f.model_dump() for f in config.fields],
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
        is_active=config.is_active,
        field_count=len(config.fields),
        required_field_count=len([f for f in config.fields if f.required]),
    )


def _create_form_config(data: FormConfigCreate) -> FormConfig:
    """Create FormConfig from request data."""
    # Convert business profile
    business = BusinessProfile(
        name=data.business.name,
        industry=Industry(data.business.industry) if data.business.industry in [e.value for e in Industry] else Industry.OTHER,
        description=data.business.description,
    )
    
    # Convert agent config
    agent_data = data.agent or AgentConfigCreate()
    agent = AgentConfig(
        name=agent_data.name,
        tone=AgentTone(agent_data.tone) if agent_data.tone in [e.value for e in AgentTone] else AgentTone.PROFESSIONAL,
        voice=TTSVoice(agent_data.voice) if agent_data.voice in [e.value for e in TTSVoice] else TTSVoice.NOVA,
        custom_greeting=agent_data.custom_greeting,
        custom_closing=agent_data.custom_closing,
    )
    
    # Convert fields
    fields = []
    for i, f in enumerate(data.fields):
        field_type = FieldType(f.type) if f.type in [e.value for e in FieldType] else FieldType.TEXT
        fields.append(FormField(
            name=f.name,
            label=f.label,
            type=field_type,
            description=f.description,
            required=f.required,
            options=f.options,
            example=f.example,
            order=f.order if f.order else i,
        ))
    
    return FormConfig(
        name=data.name,
        business=business,
        agent=agent,
        fields=fields,
    )


# =============================================================================
# Template Endpoints
# =============================================================================

@router.get("/templates", response_model=List[TemplateInfo])
async def get_templates():
    """Get list of available industry templates."""
    return [
        TemplateInfo(
            id=t["id"],
            name=t["name"],
            industry=t["industry"],
            field_count=t["field_count"],
            description=t["description"],
        )
        for t in list_templates()
    ]


@router.get("/templates/{industry}", response_model=FormConfigResponse)
async def get_template_by_industry(industry: str):
    """Get a specific industry template."""
    try:
        template = get_template(industry)
        return _form_config_to_response(template)
    except KeyError:
        raise HTTPException(
            status_code=404, 
            detail=f"Template not found for industry: {industry}. Available: {list(TEMPLATES.keys())}"
        )


@router.post("/from-template/{industry}", response_model=FormConfigResponse)
async def create_from_template(
    industry: str,
    business_name: str = Query(..., description="Your business name"),
):
    """Create a new form configuration from an industry template."""
    try:
        # Get template
        template = get_template(industry)
        
        # Customize with business name
        template.business.name = business_name
        template.id = None  # Will generate new ID
        template.created_at = datetime.now()
        template.updated_at = datetime.now()
        
        # Regenerate ID
        import uuid
        template.id = str(uuid.uuid4())
        
        # Store
        _form_configs[template.id] = template
        
        logger.info(f"Created form from template: {template.id} ({industry})")
        
        return _form_config_to_response(template)
        
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Template not found: {industry}"
        )


# =============================================================================
# Form CRUD Endpoints
# =============================================================================

@router.get("/", response_model=List[FormConfigResponse])
async def list_forms():
    """List all form configurations."""
    return [
        _form_config_to_response(config) 
        for config in _form_configs.values()
    ]


@router.post("/", response_model=FormConfigResponse)
async def create_form(data: FormConfigCreate):
    """Create a new form configuration."""
    config = _create_form_config(data)
    _form_configs[config.id] = config
    
    logger.info(f"Created form: {config.id} ({config.name})")
    
    return _form_config_to_response(config)


@router.get("/{form_id}", response_model=FormConfigResponse)
async def get_form(form_id: str):
    """Get a form configuration by ID."""
    if form_id not in _form_configs:
        raise HTTPException(status_code=404, detail="Form not found")
    
    return _form_config_to_response(_form_configs[form_id])


@router.put("/{form_id}", response_model=FormConfigResponse)
async def update_form(form_id: str, data: FormConfigUpdate):
    """Update a form configuration."""
    if form_id not in _form_configs:
        raise HTTPException(status_code=404, detail="Form not found")
    
    config = _form_configs[form_id]
    
    # Update fields
    if data.name is not None:
        config.name = data.name
    
    if data.business is not None:
        config.business = BusinessProfile(
            name=data.business.name,
            industry=Industry(data.business.industry) if data.business.industry in [e.value for e in Industry] else config.business.industry,
            description=data.business.description,
        )
    
    if data.agent is not None:
        config.agent = AgentConfig(
            name=data.agent.name,
            tone=AgentTone(data.agent.tone) if data.agent.tone in [e.value for e in AgentTone] else config.agent.tone,
            voice=TTSVoice(data.agent.voice) if data.agent.voice in [e.value for e in TTSVoice] else config.agent.voice,
            custom_greeting=data.agent.custom_greeting,
            custom_closing=data.agent.custom_closing,
        )
    
    if data.fields is not None:
        fields = []
        for i, f in enumerate(data.fields):
            field_type = FieldType(f.type) if f.type in [e.value for e in FieldType] else FieldType.TEXT
            fields.append(FormField(
                name=f.name,
                label=f.label,
                type=field_type,
                description=f.description,
                required=f.required,
                options=f.options,
                example=f.example,
                order=f.order if f.order else i,
            ))
        config.fields = fields
    
    config.updated_at = datetime.now()
    
    # Clear agent cache so it rebuilds with new config
    clear_agent_cache(form_id)
    
    logger.info(f"Updated form: {form_id}")
    
    return _form_config_to_response(config)


@router.delete("/{form_id}")
async def delete_form(form_id: str):
    """Delete a form configuration."""
    if form_id not in _form_configs:
        raise HTTPException(status_code=404, detail="Form not found")
    
    del _form_configs[form_id]
    clear_agent_cache(form_id)
    
    logger.info(f"Deleted form: {form_id}")
    
    return {"message": "Form deleted successfully"}


# =============================================================================
# Field Type Info
# =============================================================================

@router.get("/meta/field-types")
async def get_field_types():
    """Get available field types with descriptions."""
    return [
        {"value": "text", "label": "Short Text", "description": "Single line text input"},
        {"value": "textarea", "label": "Long Text", "description": "Multi-line text input"},
        {"value": "number", "label": "Number", "description": "Numeric value"},
        {"value": "date", "label": "Date", "description": "Date picker"},
        {"value": "time", "label": "Time", "description": "Time picker"},
        {"value": "datetime", "label": "Date & Time", "description": "Date and time picker"},
        {"value": "email", "label": "Email", "description": "Email address with validation"},
        {"value": "phone", "label": "Phone", "description": "Phone number"},
        {"value": "select", "label": "Dropdown", "description": "Single selection from options"},
        {"value": "multiselect", "label": "Multi-Select", "description": "Multiple selections from options"},
        {"value": "boolean", "label": "Yes/No", "description": "True or false question"},
        {"value": "address", "label": "Address", "description": "Full address input"},
        {"value": "name", "label": "Full Name", "description": "Person's full name"},
        {"value": "currency", "label": "Currency", "description": "Dollar amount"},
    ]


@router.get("/meta/industries")
async def get_industries():
    """Get available industries."""
    return [
        {"value": "legal", "label": "Legal Services"},
        {"value": "healthcare", "label": "Healthcare"},
        {"value": "real_estate", "label": "Real Estate"},
        {"value": "home_services", "label": "Home Services"},
        {"value": "recruiting", "label": "Recruiting"},
        {"value": "financial", "label": "Financial Services"},
        {"value": "insurance", "label": "Insurance"},
        {"value": "education", "label": "Education"},
        {"value": "hospitality", "label": "Hospitality"},
        {"value": "other", "label": "Other"},
    ]


@router.get("/meta/tones")
async def get_tones():
    """Get available agent tones."""
    return [
        {"value": "professional", "label": "Professional", "description": "Business-like and courteous"},
        {"value": "friendly", "label": "Friendly", "description": "Warm and approachable"},
        {"value": "empathetic", "label": "Empathetic", "description": "Understanding and supportive"},
        {"value": "formal", "label": "Formal", "description": "Precise and respectful"},
        {"value": "casual", "label": "Casual", "description": "Relaxed and conversational"},
    ]


@router.get("/meta/voices")
async def get_voices():
    """Get available TTS voices."""
    return [
        {"value": "alloy", "label": "Alloy", "description": "Neutral, balanced voice"},
        {"value": "echo", "label": "Echo", "description": "Male, warm voice"},
        {"value": "fable", "label": "Fable", "description": "British, expressive voice"},
        {"value": "onyx", "label": "Onyx", "description": "Male, deep voice"},
        {"value": "nova", "label": "Nova", "description": "Female, friendly voice"},
        {"value": "shimmer", "label": "Shimmer", "description": "Female, soft voice"},
    ]


# =============================================================================
# Internal function to get form config for chat
# =============================================================================

def get_form_config(form_id: str) -> Optional[FormConfig]:
    """Get form config by ID (for internal use)."""
    return _form_configs.get(form_id)


def get_or_create_demo_config() -> FormConfig:
    """Get or create a demo form config."""
    demo_id = "demo_config"
    
    if demo_id not in _form_configs:
        # Create from insurance template
        template = get_template("insurance")
        template.id = demo_id
        template.business.name = "Demo Insurance Co."
        _form_configs[demo_id] = template
    
    return _form_configs[demo_id]
