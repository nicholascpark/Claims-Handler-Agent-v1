"""
Form Configuration Models

Data models for dynamic form configuration.
These models allow users to define what information they want to collect
through the conversational AI agent.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


class FieldType(str, Enum):
    """Supported field types for data collection."""
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    EMAIL = "email"
    PHONE = "phone"
    SELECT = "select"
    MULTISELECT = "multiselect"
    BOOLEAN = "boolean"
    ADDRESS = "address"
    NAME = "name"
    CURRENCY = "currency"


class Industry(str, Enum):
    """Supported industry types with pre-built templates."""
    LEGAL = "legal"
    HEALTHCARE = "healthcare"
    REAL_ESTATE = "real_estate"
    HOME_SERVICES = "home_services"
    RECRUITING = "recruiting"
    FINANCIAL = "financial"
    INSURANCE = "insurance"
    EDUCATION = "education"
    HOSPITALITY = "hospitality"
    OTHER = "other"


class AgentTone(str, Enum):
    """Agent conversation style/tone."""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    EMPATHETIC = "empathetic"
    FORMAL = "formal"
    CASUAL = "casual"


class TTSVoice(str, Enum):
    """OpenAI TTS voice options."""
    ALLOY = "alloy"
    ECHO = "echo"
    FABLE = "fable"
    ONYX = "onyx"
    NOVA = "nova"
    SHIMMER = "shimmer"


class FormField(BaseModel):
    """
    A single field to collect in the conversation.
    
    The AI will ask for this information during the conversation
    and extract it into the structured payload.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = Field(..., description="Internal field name (e.g., 'incident_date')")
    label: str = Field(..., description="Human-readable label (e.g., 'Date of Incident')")
    type: FieldType = Field(default=FieldType.TEXT, description="Field data type")
    description: str = Field(
        default="", 
        description="Help text for the AI to understand what to collect"
    )
    required: bool = Field(default=True, description="Whether this field is required")
    options: Optional[List[str]] = Field(
        default=None, 
        description="Options for select/multiselect fields"
    )
    validation: Optional[str] = Field(
        default=None,
        description="Validation hint (e.g., 'Must be a valid email')"
    )
    example: Optional[str] = Field(
        default=None,
        description="Example value to help AI understand format"
    )
    order: int = Field(default=0, description="Display/collection order")
    
    class Config:
        use_enum_values = True


class BusinessProfile(BaseModel):
    """
    Business information for context.
    
    This helps the AI understand the business context
    and tailor the conversation appropriately.
    """
    name: str = Field(..., description="Business name")
    industry: Industry = Field(default=Industry.OTHER, description="Business industry")
    description: Optional[str] = Field(
        default=None, 
        description="Brief description of the business"
    )
    website: Optional[str] = Field(default=None, description="Business website")
    
    class Config:
        use_enum_values = True


class AgentConfig(BaseModel):
    """
    AI agent personality and voice configuration.
    """
    name: str = Field(default="Alex", description="Agent's name")
    tone: AgentTone = Field(
        default=AgentTone.PROFESSIONAL, 
        description="Conversation style"
    )
    voice: TTSVoice = Field(default=TTSVoice.NOVA, description="TTS voice")
    custom_greeting: Optional[str] = Field(
        default=None,
        description="Custom greeting message (auto-generated if not provided)"
    )
    custom_closing: Optional[str] = Field(
        default=None,
        description="Custom closing message after form completion"
    )
    
    class Config:
        use_enum_values = True


class FormConfig(BaseModel):
    """
    Complete form configuration.
    
    This is the main configuration object that defines:
    - What business is using the agent
    - How the agent should behave
    - What information to collect
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Form name (e.g., 'Client Intake Form')")
    business: BusinessProfile = Field(..., description="Business information")
    agent: AgentConfig = Field(
        default_factory=AgentConfig, 
        description="Agent configuration"
    )
    fields: List[FormField] = Field(
        default_factory=list, 
        description="Fields to collect"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)
    
    # Usage tracking
    total_conversations: int = Field(default=0)
    total_completions: int = Field(default=0)
    
    def get_required_fields(self) -> List[FormField]:
        """Get all required fields."""
        return [f for f in self.fields if f.required]
    
    def get_optional_fields(self) -> List[FormField]:
        """Get all optional fields."""
        return [f for f in self.fields if not f.required]
    
    def get_fields_by_type(self, field_type: FieldType) -> List[FormField]:
        """Get fields of a specific type."""
        return [f for f in self.fields if f.type == field_type]
    
    def to_schema_dict(self) -> Dict[str, Any]:
        """
        Convert fields to a dictionary representation
        suitable for dynamic Pydantic model generation.
        """
        schema = {}
        for field in self.fields:
            field_info = {
                "type": field.type,
                "description": field.description or field.label,
                "required": field.required,
            }
            if field.options:
                field_info["options"] = field.options
            if field.example:
                field_info["example"] = field.example
            schema[field.name] = field_info
        return schema


class ConversationSession(BaseModel):
    """
    Active conversation session.
    
    Tracks the state of an ongoing conversation.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    form_config_id: str = Field(..., description="Associated form configuration")
    thread_id: str = Field(..., description="LangGraph thread ID")
    
    # Session state
    started_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    is_complete: bool = Field(default=False)
    
    # Collected data
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    # Cost tracking
    total_input_tokens: int = Field(default=0)
    total_output_tokens: int = Field(default=0)
    total_audio_seconds: float = Field(default=0.0)
    total_tts_characters: int = Field(default=0)
    estimated_cost_usd: float = Field(default=0.0)


class FormSubmission(BaseModel):
    """
    Completed form submission.
    
    Stored after a conversation successfully collects all required data.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    form_config_id: str = Field(..., description="Associated form configuration")
    session_id: str = Field(..., description="Conversation session that created this")
    
    # Submission data
    data: Dict[str, Any] = Field(..., description="Collected form data")
    submitted_at: datetime = Field(default_factory=datetime.now)
    
    # Metadata
    duration_seconds: float = Field(default=0.0)
    total_messages: int = Field(default=0)
    estimated_cost_usd: float = Field(default=0.0)
