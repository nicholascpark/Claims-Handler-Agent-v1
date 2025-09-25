"""Claims Handler Realtime Agent - Based on OpenAI Realtime Agents pattern

This module implements the junior/supervisor pattern from the OpenAI Realtime Agents
reference implementation, adapted for claims processing.
"""

import json
import random
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from src.config.settings import settings


@dataclass
class RealtimeMessage:
    """Represents a message in the realtime conversation"""
    role: str  # 'user' or 'assistant' 
    content: str
    timestamp: Optional[str] = None


class ClaimsRealtimeAgent:
    """
    Junior realtime agent that handles basic interactions and defers to supervisor.
    
    Based on the OpenAI chat supervisor pattern:
    - Handles basic greetings and chitchat only
    - Uses filler phrases before calling supervisor
    - Cannot make decisions or call tools directly
    - Must use getNextResponseFromSupervisor for everything else
    """
    
    def __init__(self, name: str = "claimsAgent"):
        self.name = name
        self.voice = settings.JUNIOR_AGENT_VOICE
        self.conversation_history: List[RealtimeMessage] = []
        
        # Define instructions (similar to OpenAI pattern)
        self.instructions = self._get_agent_instructions()
        
        # Tools available (only the supervisor tool)
        self.tools = [self._get_supervisor_tool_definition()]
        
    def _get_agent_instructions(self) -> str:
        """Get agent instructions following OpenAI pattern"""
        return f"""You are a helpful junior claims handler agent for {settings.COMPANY_NAME}. Your top priority is to perform structured intake before escalating. Defer to the Supervisor Agent after you've collected as many intake details as possible.

# General Instructions
- You are very new and can only handle basic tasks, and will rely heavily on the Supervisor Agent via the getNextResponseFromSupervisor tool
- By default, you must always use the getNextResponseFromSupervisor tool to get your next response, except for very specific exceptions.
- Always greet the user with "{settings.COMPANY_GREETING}"
- If the user says "hi", "hello", or similar greetings in later messages, respond naturally and briefly instead of repeating the canned greeting.
- In general, don't say the same thing twice, always vary it to ensure the conversation feels natural.
- Do not use any information from examples as reference in conversation.

## Tone  
- Maintain a professional, empathetic, and helpful tone at all times.
- Be concise but warm, especially since users may be stressed from recent incidents.
- Use natural conversational flow.

# Tools
- You can ONLY call getNextResponseFromSupervisor
- Do not reference or request policy lookups; proceed with intake details only.

# Allow List of Permitted Actions
You can take the following actions directly, and don't need to use getNextResponse for these:

## Basic chitchat
- Handle greetings (e.g., "hello", "hi there").
- Engage in basic chitchat (e.g., "how are you?", "thank you").  
- Respond to requests to repeat or clarify information (e.g., "can you repeat that?").

## Collect information for Supervisor Agent tool calls
- Request user information needed for claim processing. Refer to the Supervisor Tools section below for full definitions.

### Supervisor Agent Tools
NEVER call these tools directly, these are only provided as a reference for collecting parameters for the supervisor to use.

validateClaimInfo:
  description: Validate completeness of claim information and identify missing fields.
  params:
    claim_data: object (required) - Current claim data object.

lookupPolicyInfo:
  description: Look up policy information and coverage details.
  params:
    policy_number: string (required) - User's policy number.

getLocationDetails:
  description: Get and validate location information for the incident.
  params:
    location_string: string (required) - Location description from user.

**You must NOT answer, resolve, or attempt to handle ANY other type of request, question, or issue yourself. For absolutely everything else, you MUST use the getNextResponseFromSupervisor tool to get your response.**

# Intake-First Flow (before calling getNextResponseFromSupervisor)
- Collect these items conversationally when relevant (one at a time):
  1) insured name
  2) contact phone/email
  3) incident type and brief description
  4) incident date/time
  5) incident location (city/street)
- Acknowledge what the user says and ask for the next missing item.
- Use natural phrasing; don't dump the whole checklist at once.

# getNextResponseFromSupervisor Usage
- For ALL requests that are not strictly and explicitly listed above, you MUST ALWAYS use the getNextResponseFromSupervisor tool.
- Do NOT attempt to answer, resolve, or speculate on any other requests, even if you think you know the answer.
- Before calling getNextResponseFromSupervisor, you MUST ALWAYS say something to the user (see 'Sample Filler Phrases' section). Never call it without first saying something.
  - Filler phrases must NOT indicate whether you can or cannot fulfill an action; they should be neutral.
  - After the filler phrase YOU MUST ALWAYS call the getNextResponseFromSupervisor tool.
- You will use this tool extensively.

## How getNextResponseFromSupervisor Works
- This asks the supervisor what to do next. The supervisor is more senior and intelligent with access to full conversation history and can call tools.
- You must provide key context from the most recent user message, as concise as possible.
- The supervisor analyzes the transcript, potentially calls functions, and provides a high-quality answer which you should read verbatim.

# Sample Filler Phrases
- "{random.choice(settings.FILLER_PHRASES)}"

# Example Flow
- User: "Hi"
- Assistant: "{settings.COMPANY_GREETING}"
- User: "I was in an accident yesterday and need to report a claim"  
- Assistant: "{random.choice(settings.FILLER_PHRASES)}" // Required filler phrase
- getNextResponseFromSupervisor(relevantContextFromLastUserMessage="User was in accident yesterday, wants to report claim")
  - Returns: "I'm sorry to hear about your accident. I'll help you report this claim right away. Let's start with your full name and a phone number to reach you."
- Assistant: "I'm sorry to hear about your accident. I'll help you report this claim right away. Let's start with your full name and a phone number to reach you."
"""

    def _get_supervisor_tool_definition(self) -> Dict[str, Any]:
        """Get the supervisor tool definition (equivalent to OpenAI pattern)"""
        return {
            "type": "function",
            "name": "getNextResponseFromSupervisor",
            "description": "Determines the next response whenever the agent faces a non-trivial decision, produced by a highly intelligent supervisor agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relevantContextFromLastUserMessage": {
                        "type": "string",
                        "description": "Key information from the user described in their most recent message. Critical to provide as the supervisor needs full context. Can be empty if user message didn't add new information."
                    }
                },
                "required": ["relevantContextFromLastUserMessage"],
                "additionalProperties": False
            }
        }

    def process_user_message(self, message: str) -> Dict[str, Any]:
        """
        Process user message and determine response strategy.
        
        Args:
            message: User's message
            
        Returns:
            Dictionary with response type and content
        """
        # Add to conversation history
        self.conversation_history.append(RealtimeMessage(
            role="user",
            content=message,
            timestamp=self._get_timestamp()
        ))
        
        message_lower = message.lower().strip()
        
        # Check if this is a basic interaction we can handle
        if self._is_basic_interaction(message_lower):
            response = self._handle_basic_interaction(message_lower)
            self._add_assistant_message(response)
            
            return {
                "type": "direct_response",
                "message": response,
                "needs_supervisor": False
            }
        
        # For everything else, defer to supervisor with filler phrase
        filler_phrase = self._get_filler_phrase()
        context = self._extract_context_from_message(message)
        
        # Add filler phrase to conversation history
        self._add_assistant_message(filler_phrase)
        
        return {
            "type": "supervisor_needed", 
            "filler_phrase": filler_phrase,
            "context_for_supervisor": context,
            "needs_supervisor": True,
            "conversation_history": self._get_conversation_history_for_supervisor()
        }

    def _is_basic_interaction(self, message: str) -> bool:
        """Check if this is a basic interaction we can handle directly"""
        basic_patterns = [
            # Greetings (only for first interaction or simple responses)
            "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
            # Thank you
            "thank you", "thanks", "appreciate it",
            # Basic politeness
            "how are you", "how's it going",
            # Clarification requests
            "can you repeat", "say that again", "what did you say", "pardon",
            "could you repeat", "excuse me"
        ]
        
        # Only handle as basic if it's purely one of these patterns
        return any(message.startswith(pattern) or message == pattern for pattern in basic_patterns)

    def _handle_basic_interaction(self, message: str) -> str:
        """Handle basic interactions directly without supervisor"""
        
        # Initial greetings
        if any(greeting in message for greeting in ["hi", "hello", "hey"]):
            if len(self.conversation_history) <= 1:  # First interaction
                return settings.COMPANY_GREETING
            else:
                return random.choice([
                    "Hello!",
                    "Hi there!",
                    "Yes, how can I help you?"
                ])
        
        # Thank you responses
        if any(thanks in message for thanks in ["thank you", "thanks"]):
            return random.choice([
                "You're welcome!",
                "Of course, happy to help.",
                "No problem at all."
            ])
        
        # How are you responses
        if "how are you" in message:
            return "I'm doing well, thank you for asking. How can I help you with your claim?"
        
        # Clarification requests  
        if any(clarify in message for clarify in ["repeat", "say that again", "pardon"]):
            return "Of course, let me repeat that information for you."
        
        # Default basic response
        return "I'm here to help you with your claim. What would you like to know?"

    def _get_filler_phrase(self) -> str:
        """Get a random filler phrase to use while calling supervisor"""
        return random.choice(settings.FILLER_PHRASES)

    def _extract_context_from_message(self, message: str) -> str:
        """Extract key context from the most recent user message for supervisor"""
        message_lower = message.lower().strip()
        
        # Look for key claim-related information
        context_indicators = {
            "accident": "user mentions accident",
            "collision": "user mentions collision",
            "crash": "user mentions crash", 
            "claim": "user wants to discuss claim",
            "report": "user wants to report incident",
            "policy": "user providing/asking about policy",
            "coverage": "user asking about coverage",
            "happened": "user describing what happened",
            "when": "user providing timing information",
            "where": "user providing location information",
            "phone": "user providing phone number",
            "name": "user providing name information"
        }
        
        # Extract relevant context
        relevant_context = []
        for keyword, context in context_indicators.items():
            if keyword in message_lower:
                relevant_context.append(context)
        
        # Include specific information if present
        if relevant_context:
            context_summary = "; ".join(relevant_context)
            return f"{context_summary}. Message: '{message[:200]}'"
        else:
            # Generic context with message preview
            return f"User message: '{message[:200]}'"

    def _get_conversation_history_for_supervisor(self) -> List[Dict[str, Any]]:
        """Get conversation history formatted for supervisor"""
        history = []
        for msg in self.conversation_history[-settings.MAX_CONVERSATION_HISTORY:]:
            history.append({
                "type": "message",
                "role": msg.role,
                "content": msg.content
            })
        return history

    def _add_assistant_message(self, message: str):
        """Add assistant message to conversation history"""
        self.conversation_history.append(RealtimeMessage(
            role="assistant",
            content=message,
            timestamp=self._get_timestamp()
        ))

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_session_config(self) -> Dict[str, Any]:
        """Get session configuration for realtime API"""
        return {
            "modalities": ["text", "audio"],
            "instructions": self.instructions,
            "voice": self.voice,
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16", 
            "input_audio_transcription": {
                "model": "whisper-1",
                "language": "en",
                "prompt": "You are transcribing an English insurance claim intake call. Common words: policy, claim, coverage, accident, incident, pipe, water, hail, storm, collision, location."
            },
            "turn_detection": {
                "type": "server_vad",
                # Make VAD more conservative and give user more time to speak
                "threshold": 0.9,
                "prefix_padding_ms": 800,
                "silence_duration_ms": 2000
            },
            "tools": self.tools,
            "tool_choice": "auto"
        }


def create_claims_realtime_agent(name: str = "claimsAgent") -> ClaimsRealtimeAgent:
    """Factory function to create a claims realtime agent"""
    return ClaimsRealtimeAgent(name=name)
