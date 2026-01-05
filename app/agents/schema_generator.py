"""
Dynamic Schema Generator

Generates Pydantic models dynamically from form field definitions.
This allows trustcall to extract data into custom schemas based on user configuration.
"""

from typing import Any, Dict, List, Optional, Type, get_origin
from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo

from app.models.form_config import FormConfig, FormField, FieldType


# Mapping from FieldType to Python types
FIELD_TYPE_TO_PYTHON = {
    FieldType.TEXT: str,
    FieldType.TEXTAREA: str,
    FieldType.NUMBER: float,
    FieldType.DATE: str,  # ISO format string
    FieldType.TIME: str,
    FieldType.DATETIME: str,
    FieldType.EMAIL: str,
    FieldType.PHONE: str,
    FieldType.SELECT: str,
    FieldType.MULTISELECT: List[str],
    FieldType.BOOLEAN: bool,
    FieldType.ADDRESS: str,  # Could be dict, but string is simpler for extraction
    FieldType.NAME: str,
    FieldType.CURRENCY: float,
}


def _create_field_info(field: FormField) -> tuple:
    """
    Create a tuple of (type, FieldInfo) for dynamic model creation.
    
    Args:
        field: The form field definition
        
    Returns:
        Tuple of (python_type, Field(...))
    """
    python_type = FIELD_TYPE_TO_PYTHON.get(field.type, str)
    
    # Build description
    description_parts = [field.label]
    if field.description:
        description_parts.append(field.description)
    if field.options and field.type in [FieldType.SELECT, FieldType.MULTISELECT]:
        description_parts.append(f"Valid options: {', '.join(field.options)}")
    if field.example:
        description_parts.append(f"Example: {field.example}")
    
    description = ". ".join(description_parts)
    
    # Create field with appropriate default
    if field.required:
        # Required fields should have ... as default (no default)
        # But for extraction, we want Optional to allow partial extraction
        field_info = Field(
            default=None,
            description=description
        )
        # Wrap in Optional for graceful handling of missing data
        python_type = Optional[python_type]
    else:
        field_info = Field(
            default=None,
            description=description
        )
        python_type = Optional[python_type]
    
    return (python_type, field_info)


def generate_extraction_schema(config: FormConfig) -> Type[BaseModel]:
    """
    Generate a Pydantic model from a form configuration.
    
    This creates a dynamic model that trustcall can use for extraction.
    
    Args:
        config: The form configuration
        
    Returns:
        A Pydantic model class
    """
    # Build field definitions
    field_definitions: Dict[str, Any] = {}
    
    for field in config.fields:
        python_type, field_info = _create_field_info(field)
        field_definitions[field.name] = (python_type, field_info)
    
    # Create a unique model name based on config
    model_name = f"FormData_{config.id.replace('-', '_')[:8]}"
    
    # Create the dynamic model
    DynamicModel = create_model(
        model_name,
        __doc__=f"Extracted data for {config.name}",
        **field_definitions
    )
    
    # Add helper methods
    def is_complete(self) -> bool:
        """Check if all required fields are filled."""
        for field in config.fields:
            if field.required:
                value = getattr(self, field.name, None)
                if value is None or (isinstance(value, str) and not value.strip()):
                    return False
        return True
    
    def get_missing_fields(self) -> List[str]:
        """Get list of missing required field names."""
        missing = []
        for field in config.fields:
            if field.required:
                value = getattr(self, field.name, None)
                if value is None or (isinstance(value, str) and not value.strip()):
                    missing.append(field.name)
        return missing
    
    def get_filled_fields(self) -> Dict[str, Any]:
        """Get dictionary of filled fields only."""
        filled = {}
        for field in config.fields:
            value = getattr(self, field.name, None)
            if value is not None:
                if isinstance(value, str) and not value.strip():
                    continue
                filled[field.name] = value
        return filled
    
    def get_completion_percentage(self) -> float:
        """Get percentage of required fields completed."""
        required_fields = [f for f in config.fields if f.required]
        if not required_fields:
            return 100.0
        
        filled = 0
        for field in required_fields:
            value = getattr(self, field.name, None)
            if value is not None and (not isinstance(value, str) or value.strip()):
                filled += 1
        
        return (filled / len(required_fields)) * 100
    
    # Attach methods to the model
    DynamicModel.is_complete = is_complete
    DynamicModel.get_missing_fields = get_missing_fields
    DynamicModel.get_filled_fields = get_filled_fields
    DynamicModel.get_completion_percentage = get_completion_percentage
    
    # Store reference to config for later use
    DynamicModel._form_config = config
    
    return DynamicModel


def create_empty_payload(config: FormConfig) -> Dict[str, Any]:
    """
    Create an empty payload dictionary based on form config.
    
    Args:
        config: The form configuration
        
    Returns:
        Dictionary with all field names set to None
    """
    return {field.name: None for field in config.fields}


def validate_payload(config: FormConfig, payload: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate a payload against the form configuration.
    
    Args:
        config: The form configuration
        payload: The data to validate
        
    Returns:
        Dictionary with 'errors' and 'warnings' lists
    """
    errors = []
    warnings = []
    
    for field in config.fields:
        value = payload.get(field.name)
        
        # Check required fields
        if field.required and (value is None or (isinstance(value, str) and not value.strip())):
            errors.append(f"Missing required field: {field.label}")
            continue
        
        # Skip validation if no value
        if value is None:
            continue
        
        # Type-specific validation
        if field.type == FieldType.EMAIL and value:
            if "@" not in str(value) or "." not in str(value):
                warnings.append(f"Invalid email format for {field.label}")
        
        if field.type == FieldType.PHONE and value:
            digits = "".join(c for c in str(value) if c.isdigit())
            if len(digits) < 10:
                warnings.append(f"Phone number for {field.label} seems incomplete")
        
        if field.type == FieldType.SELECT and field.options:
            if str(value) not in field.options:
                warnings.append(f"Value '{value}' for {field.label} not in valid options")
    
    return {"errors": errors, "warnings": warnings}


def payload_to_display_format(config: FormConfig, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert a payload to a display-friendly format for the UI.
    
    Args:
        config: The form configuration
        payload: The extracted data
        
    Returns:
        List of field display objects with labels, values, and status
    """
    display = []
    
    for field in sorted(config.fields, key=lambda f: f.order):
        value = payload.get(field.name)
        
        display.append({
            "name": field.name,
            "label": field.label,
            "type": field.type,
            "value": value,
            "required": field.required,
            "filled": value is not None and (not isinstance(value, str) or bool(value.strip())),
            "options": field.options,
        })
    
    return display
