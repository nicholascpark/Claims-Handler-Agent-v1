"""
Dynamic Prompt Generator

Generates system prompts from form configurations.
This allows the AI agent to adapt to any business type and data collection needs.
"""

from typing import Optional
from datetime import datetime

from app.models.form_config import FormConfig, FormField, FieldType, AgentTone


# Tone descriptions for the AI
TONE_DESCRIPTIONS = {
    AgentTone.PROFESSIONAL: "professional, courteous, and business-like",
    AgentTone.FRIENDLY: "warm, friendly, and conversational",
    AgentTone.EMPATHETIC: "empathetic, understanding, and supportive",
    AgentTone.FORMAL: "formal, respectful, and precise",
    AgentTone.CASUAL: "casual, relaxed, and approachable",
}

# Field type descriptions for AI understanding
FIELD_TYPE_HINTS = {
    FieldType.TEXT: "text response",
    FieldType.TEXTAREA: "detailed text response",
    FieldType.NUMBER: "numeric value",
    FieldType.DATE: "date (e.g., January 15, 2024 or 01/15/2024)",
    FieldType.TIME: "time (e.g., 3:30 PM)",
    FieldType.DATETIME: "date and time",
    FieldType.EMAIL: "email address",
    FieldType.PHONE: "phone number",
    FieldType.SELECT: "selection from options",
    FieldType.MULTISELECT: "one or more selections from options",
    FieldType.BOOLEAN: "yes or no",
    FieldType.ADDRESS: "full address including street, city, state, and zip",
    FieldType.NAME: "full name",
    FieldType.CURRENCY: "dollar amount",
}


def _format_field_for_prompt(field: FormField) -> str:
    """Format a single field for inclusion in the prompt."""
    
    # Base field description
    type_hint = FIELD_TYPE_HINTS.get(field.type, "text")
    required_marker = "(Required)" if field.required else "(Optional)"
    
    line = f"- **{field.label}** [{type_hint}] {required_marker}"
    
    # Add description if available
    if field.description:
        line += f"\n  *Purpose: {field.description}*"
    
    # Add options for select fields
    if field.options and field.type in [FieldType.SELECT, FieldType.MULTISELECT]:
        options_str = ", ".join(field.options)
        line += f"\n  *Options: {options_str}*"
    
    # Add example if available
    if field.example:
        line += f"\n  *Example: \"{field.example}\"*"
    
    return line


def generate_system_prompt(config: FormConfig) -> str:
    """
    Generate a complete system prompt from a form configuration.
    
    Args:
        config: The form configuration
        
    Returns:
        Complete system prompt string
    """
    
    # Get tone description
    tone_desc = TONE_DESCRIPTIONS.get(config.agent.tone, "professional")
    
    # Format all fields
    fields_section = "\n".join(
        _format_field_for_prompt(f) 
        for f in sorted(config.fields, key=lambda x: x.order)
    )
    
    # Count required vs optional
    required_count = len([f for f in config.fields if f.required])
    optional_count = len([f for f in config.fields if not f.required])
    
    # Build the prompt
    prompt = f"""You are {config.agent.name}, a {tone_desc} AI voice assistant for {config.business.name}.

## Your Role
You are conducting a voice-first conversation to collect information from callers. Your goal is to gather the required information naturally and efficiently while maintaining a {tone_desc} demeanor.

## Business Context
- **Business Name:** {config.business.name}
- **Industry:** {config.business.industry}
{f"- **Description:** {config.business.description}" if config.business.description else ""}

## Information to Collect
You need to gather the following information ({required_count} required, {optional_count} optional):

{fields_section}

## Conversation Guidelines

### Voice-First Principles
1. **Keep responses concise** - This is a voice conversation, not text. Aim for 1-3 sentences per turn.
2. **Ask one question at a time** - Don't overwhelm the caller with multiple questions.
3. **Be conversational** - Don't sound like a form. Make it feel like a natural dialogue.
4. **Acknowledge information** - Briefly confirm what you heard before moving on.

### Collection Strategy
1. Start with a warm greeting and explain your purpose.
2. Gather information in a logical order, but be flexible if the caller provides info out of sequence.
3. For required fields, gently persist until you have the information.
4. For optional fields, ask but don't push if they decline.
5. Confirm important details by repeating them back.

### Handling Responses
- If unclear: "I'm sorry, I didn't quite catch that. Could you repeat that for me?"
- If correcting: "No problem! Let me update that. [Confirm new information]"
- If refusing optional field: "That's completely fine. Let's move on."
- If caller is confused: Explain why you need the information briefly.

### Completion
Once you have all required information:
1. Briefly summarize what you've collected.
2. Ask if they have any questions or anything to add.
3. Thank them and explain next steps.

## Important Rules
- Never invent or assume information not provided by the caller.
- If something doesn't make sense, ask for clarification.
- Stay in character as {config.agent.name} throughout.
- Be patient and understanding - callers may be stressed or confused.
- Protect sensitive information - don't repeat full credit card numbers, SSNs, etc.

## Starting the Conversation
{config.agent.custom_greeting if config.agent.custom_greeting else f"Begin with a warm greeting, introduce yourself as {config.agent.name}, explain you're here to help gather some information, and ask your first question."}

Current date and time: {{time}}
"""
    
    return prompt


def generate_greeting(config: FormConfig) -> str:
    """
    Generate or return the greeting message.
    
    Args:
        config: The form configuration
        
    Returns:
        Greeting message string
    """
    if config.agent.custom_greeting:
        return config.agent.custom_greeting
    
    tone_greetings = {
        AgentTone.PROFESSIONAL: f"Hello, thank you for calling {config.business.name}. I'm {config.agent.name}, a virtual assistant. I'll be gathering some information to assist you. May I start by getting your name?",
        AgentTone.FRIENDLY: f"Hi there! Thanks for reaching out to {config.business.name}. I'm {config.agent.name}, your virtual helper today. Let's get some quick details so we can best assist you. What's your name?",
        AgentTone.EMPATHETIC: f"Hello, and thank you for contacting {config.business.name}. I'm {config.agent.name}, and I'm here to help. I understand reaching out can sometimes be difficult, so I'll make this as easy as possible. Could you start by telling me your name?",
        AgentTone.FORMAL: f"Good day. You have reached {config.business.name}. I am {config.agent.name}, an automated assistant. I will be collecting some preliminary information. May I have your full name, please?",
        AgentTone.CASUAL: f"Hey! You've reached {config.business.name}. I'm {config.agent.name}. Just need to grab a few details from you, cool? What's your name?",
    }
    
    return tone_greetings.get(config.agent.tone, tone_greetings[AgentTone.PROFESSIONAL])


def generate_closing(config: FormConfig, form_completed: bool = True) -> str:
    """
    Generate or return the closing message.
    
    Args:
        config: The form configuration
        form_completed: Whether all required fields were collected
        
    Returns:
        Closing message string
    """
    if config.agent.custom_closing:
        return config.agent.custom_closing
    
    if form_completed:
        return f"Great, I have all the information I need. Thank you for your time today. Someone from {config.business.name} will be in touch with you soon. Is there anything else I can help you with before we finish?"
    else:
        return f"I understand we weren't able to complete everything today. No problem at all. Someone from {config.business.name} will follow up with you to gather any remaining details. Thank you for calling!"


def generate_extraction_instructions(config: FormConfig) -> str:
    """
    Generate instructions for the trustcall extractor.
    
    Args:
        config: The form configuration
        
    Returns:
        Extraction instruction prompt
    """
    
    field_descriptions = []
    for field in config.fields:
        desc = f"- {field.name}: {field.label}"
        if field.description:
            desc += f" ({field.description})"
        if field.type == FieldType.SELECT and field.options:
            desc += f" - Valid options: {', '.join(field.options)}"
        field_descriptions.append(desc)
    
    fields_text = "\n".join(field_descriptions)
    
    return f"""Extract the following information from the conversation:

{fields_text}

Rules:
- Only extract information explicitly stated by the user.
- Use null/None for fields not mentioned.
- For date fields, convert to ISO format (YYYY-MM-DD).
- For phone fields, normalize to digits only or standard format.
- For boolean fields, interpret yes/no, true/false, affirmative/negative responses.
- For select fields, match to the closest valid option.
"""
