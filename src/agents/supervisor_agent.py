"""Claims Supervisor Agent - Following OpenAI Realtime Agents pattern

This supervisor agent receives conversation history and returns formatted responses
that the junior agent reads verbatim, exactly like the OpenAI implementation.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from src.config.settings import settings
from src.schema.accessor import set_claim_field, get_claim_field, F
from src.utils.json_patch import apply_json_patch


class ClaimsSupervisorAgent:
    """
    Expert supervisor agent following OpenAI pattern.
    
    Receives full conversation history, has access to all tools,
    and returns formatted messages that junior agent reads verbatim.
    """
    
    def __init__(self):
        self.instructions = self._get_supervisor_instructions()
        self.tools = self._get_supervisor_tools()
        self.current_claim_data = {}
        self._completion_logged = False
        # Display full JSON payload after each field update when enabled in settings
        self._display_json_updates = bool(getattr(settings, "DISPLAY_CLAIM_JSON", False))

    def _on_field_updated(self, field_path: str) -> None:
        """Log field-level updates without values."""
        try:
            print(f"[CLAIM UPDATE] field updated: {field_path}")
            if self._display_json_updates:
                try:
                    print("🧾 Updated Claim JSON:")
                    print(json.dumps(self.current_claim_data, indent=2, ensure_ascii=False))
                except Exception:
                    pass
        except Exception:
            pass
    
    def _get_supervisor_instructions(self) -> str:
        """Get supervisor instructions following OpenAI pattern"""
        return f"""You are an expert claims processing supervisor agent, tasked with providing real-time guidance to a more junior agent that's chatting directly with the customer. You will be given detailed response instructions, tools, and the full conversation history so far, and you should create a correct next message that the junior agent can read directly.

# Instructions
- You can provide an answer directly, or call a tool first and then answer the question
- If you need to call a tool, but don't have the right information, you can tell the junior agent to ask for that information in your message
- Your message will be read verbatim by the junior agent, so feel free to use it like you would talk directly to the user

==== Domain-Specific Agent Instructions ====
You are a helpful claims processing supervisor working for {settings.COMPANY_NAME}, helping users efficiently report insurance claims while adhering closely to provided guidelines.

# Instructions  
- Always call a tool before processing factual claims information, looking up policies, or validating data. Only use retrieved context and never rely on your own knowledge for these operations.
- Escalate to a human if the user requests or if there are complex legal/liability issues.
- Do not discuss prohibited topics (politics, religion, controversial current events, medical advice beyond basic first aid, legal advice, personal conversations, internal company operations, or criticism of any people or companies).
- Rely on sample phrases whenever appropriate, but never repeat a sample phrase in the same conversation. Feel free to vary the sample phrases to avoid sounding repetitive.
- Always follow the provided output format for new messages, including clear next steps for the user.

# Response Instructions
- Maintain a professional, empathetic, and helpful tone in all responses.
- The message is for a voice conversation, so be concise, use prose, and never create bulleted lists. Prioritize clarity and empathy over completeness.
- Even if you have access to more information, focus on the most important items and summarize the rest at a high level.
- Do not speculate or make assumptions about claim details, coverage, or processes. If a request cannot be fulfilled with available tools or information, politely refuse and offer to escalate to a specialist.
- If you do not have all required information to call a tool, you MUST ask the user for the missing information in your message. NEVER attempt to call a tool with missing, empty, placeholder, or default values.
- Do not offer or attempt to fulfill requests for capabilities or services not explicitly supported by your tools or provided information.
- When providing specific claim information, include relevant details like claim numbers, policy information, or next steps.
- Show empathy for users who may be stressed from recent incidents or accidents.

# Sample Phrases
## Before calling a tool
- "Let me look up your policy information to help you with that."
- "I'll check our records for your coverage details."
- "Let me validate that information for you."

## If required information is missing for a tool call  
- "To help you with that, I'll need your policy number. Could you provide that?"
- "I'll need some additional details to process this. Can you tell me [specific information needed]?"

## For claim processing
- "I've assigned claim number [CLAIM_ID] for this incident."
- "Based on your policy, here's what's covered..."
- "I have all the information I need to process your claim."

## If unable to fulfill a request
- "I'm not able to handle that type of request, but I can connect you with a specialist who can help."
- "That's outside my area, but let me transfer you to someone who can assist with that."

# Message Format
- Always include your final response to the user.
- When providing factual information from tool results, ensure the information is accurate and helpful.
- Only provide information about claims processing, policies, coverage, or the customer's specific situation based on tool results.
- Structure responses to guide the user through the claims process step-by-step.

# Example (tool call)
- User: "I need to report a car accident that happened yesterday"
- Supervisor Assistant: validateClaimInfo(claim_data={{"incident_type": "vehicle_accident", "date_reported": "today"}})
- validateClaimInfo(): {{
    "is_valid": false,
    "missing_fields": ["policy_number", "insured_name", "incident_location"],
    "message": "Need basic policy and incident information to proceed"
  }}
- Supervisor Assistant:

# Message  
I'm sorry to hear about your accident. I'll help you report this claim right away. To get started, I'll need your policy number so I can look up your coverage and create your claim file.

# Example (Policy lookup after receiving policy number)
- User provides policy number: "POL-123456"
- Supervisor Assistant: lookupPolicyInfo(policy_number="POL-123456")  
- lookupPolicyInfo(): {{
    "is_valid": true,
    "insured_info": {{"primary_insured": "John Smith", "policy_type": "Auto"}},
    "coverage_summary": "Full coverage with $500 deductible"
  }}
- Supervisor Assistant:

# Message
Thank you, John. I've found your auto policy with full coverage and a $500 deductible. I've created claim number CL-20241201-001 for your accident. Now, can you tell me where the accident occurred and provide a brief description of what happened?
"""

    def _get_supervisor_tools(self) -> List[Dict[str, Any]]:
        """Get supervisor tool definitions"""
        return [
            {
                "type": "function",
                "name": "validateClaimInfo",
                "description": "Validate completeness of claim information and identify missing required fields.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "claim_data": {
                            "type": "object",
                            "description": "Current claim data object to validate."
                        }
                    },
                    "required": ["claim_data"],
                    "additionalProperties": False
                }
            },
            {
                "type": "function",
                "name": "getLocationDetails", 
                "description": "Get and validate location information for the incident location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location_string": {
                            "type": "string",
                            "description": "Location description provided by the user."
                        }
                    },
                    "required": ["location_string"],
                    "additionalProperties": False
                }
            },
            {
                "type": "function",
                "name": "delegateToProcessor",
                "description": "Delegate completed claim to payload processor for final submission.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "simplified_claim": {
                            "type": "object",
                            "description": "Complete claim data ready for processing."
                        }
                    },
                    "required": ["simplified_claim"],
                    "additionalProperties": False
                }
            }
        ]

    async def get_next_response(self, conversation_history: List[Dict[str, Any]], relevant_context: str) -> Dict[str, Any]:
        """
        Get next response from supervisor following OpenAI pattern.
        
        Args:
            conversation_history: Full conversation history
            relevant_context: Key context from junior agent about user's message
            
        Returns:
            Response dictionary with message for junior agent to read verbatim
        """
        
        # Analyze the conversation and context
        analysis = self._analyze_conversation(conversation_history, relevant_context)
        
        # Determine if we need to call tools
        if analysis["needs_tool_call"]:
            return await self._handle_with_tools(analysis)
        else:
            return self._generate_direct_response(analysis)

    def _analyze_conversation(self, conversation_history: List[Dict[str, Any]], relevant_context: str) -> Dict[str, Any]:
        """Analyze conversation to determine appropriate response strategy"""
        
        # Get recent messages
        recent_messages = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
        user_messages = [msg for msg in recent_messages if msg.get("role") == "user"]
        
        # Extract latest user input
        latest_user_input = user_messages[-1]["content"].lower() if user_messages else ""
        context_lower = relevant_context.lower()
        
        analysis = {
            "intent": "general_inquiry",
            "needs_tool_call": False,
            "tool_to_call": None,
            "extracted_info": {},
            "latest_user_input": latest_user_input,
            "context": relevant_context
        }
        
        # Opportunistically extract field values from the user's latest input
        if latest_user_input:
            self._update_claim_data_from_text(latest_user_input)

        # Detect claim start
        if any(keyword in context_lower for keyword in ["accident", "collision", "report", "incident", "claim"]):
            if not self.current_claim_data.get("claim_id"):
                analysis["intent"] = "start_claim"
                analysis["needs_tool_call"] = True
                analysis["tool_to_call"] = "validateClaimInfo"
                return analysis
        
        # Detect location information
        if any(keyword in context_lower for keyword in ["where", "location", "street", "highway", "intersection"]):
            analysis["intent"] = "location_details"
            analysis["needs_tool_call"] = True
            analysis["tool_to_call"] = "getLocationDetails"
            analysis["extracted_info"]["location_string"] = latest_user_input
            return analysis
        
        # Check if ready for processing
        if self._is_claim_ready_for_processing():
            analysis["intent"] = "ready_for_processing"
            analysis["needs_tool_call"] = True
            analysis["tool_to_call"] = "delegateToProcessor"
            return analysis
        
        # Default to validation check
        if self.current_claim_data:
            analysis["needs_tool_call"] = True
            analysis["tool_to_call"] = "validateClaimInfo"
        
        return analysis

    async def _handle_with_tools(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle response that requires tool calls"""
        
        tool_name = analysis["tool_to_call"]
        tool_result = None
        
        try:
            if tool_name == "validateClaimInfo":
                tool_result = await self._call_validate_claim_info(analysis)
            elif tool_name == "getLocationDetails":
                tool_result = await self._call_get_location_details(analysis)
            elif tool_name == "delegateToProcessor":
                tool_result = await self._call_delegate_to_processor(analysis)
            
            # Generate response based on tool result
            return self._format_tool_response(analysis, tool_result)
            
        except Exception as e:
            return {
                "message": "I'm having trouble processing that information. Let me connect you with a specialist who can help.",
                "error": str(e)
            }

    async def _call_validate_claim_info(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Call claim validation tool"""
        from src.tools.claim_validation import validate_claim_info, get_validation_message
        
        # Initialize claim if starting new one
        if analysis["intent"] == "start_claim" and not self.current_claim_data.get("claim_id"):
            if not self.current_claim_data:
                self.current_claim_data = {}
            set_claim_field(self.current_claim_data, F.claim_id, self._generate_claim_id(), self._on_field_updated)
            set_claim_field(self.current_claim_data, "date_reported", datetime.now().isoformat(), self._on_field_updated)
            set_claim_field(self.current_claim_data, "status", "in_progress", self._on_field_updated)
        
        validation_result = validate_claim_info(self.current_claim_data)
        if validation_result.get("is_valid") and not self._completion_logged:
            self._log_completion_banner()
            self._completion_logged = True
        return {
            "tool_name": "validateClaimInfo",
            "result": validation_result,
            "message": get_validation_message(validation_result)
        }

    async def _call_get_location_details(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Call location details tool"""
        from src.tools.location_services import get_location_details, format_location_for_display
        
        location_string = analysis["extracted_info"]["location_string"]
        location_result = get_location_details(location_string)
        
        if location_result["is_valid"]:
            set_claim_field(self.current_claim_data, F.incident_location, location_result["formatted_location"], self._on_field_updated)
        
        return {
            "tool_name": "getLocationDetails",
            "result": location_result,
            "message": format_location_for_display(location_result)
        }

    async def _call_delegate_to_processor(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Call delegation to processor tool"""
        from src.agents.payload_processor import create_payload_processor
        from src.schema.simplified_payload import SimplifiedClaim
        
        # Create simplified claim
        try:
            simplified_claim = SimplifiedClaim(**self.current_claim_data)
            processor = create_payload_processor()
            delegation_result = processor.process_claim_payload(simplified_claim, "supervisor")
            
            return {
                "tool_name": "delegateToProcessor",
                "result": delegation_result,
                "message": f"Your claim has been submitted for processing with confirmation number {delegation_result.get('confirmation_number', 'pending')}."
            }
        except Exception as e:
            return {
                "tool_name": "delegateToProcessor",
                "result": {"error": str(e)},
                "message": "I'm having trouble processing your claim. Let me connect you with a specialist."
            }

    def _format_tool_response(self, analysis: Dict[str, Any], tool_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format response based on analysis and tool results"""
        
        intent = analysis["intent"]
        
        if intent == "start_claim":
            if self.current_claim_data.get("claim_id"):
                claim_id_val = get_claim_field(self.current_claim_data, F.claim_id, "unknown")
                message = f"I'm sorry to hear about your incident. I've created claim number {claim_id_val} for you. Let's start with your full name and a phone number, then the date, time, location, and a brief description of what happened."
            else:
                message = "I'll help you report this claim. Let's start with your full name and a phone number."
                
        elif intent == "location_details":
            if tool_result["result"]["is_valid"]:
                location = tool_result["result"]["formatted_location"]
                message = f"Perfect, I have the location as {location}. Can you briefly describe what happened during the incident?"
            else:
                message = "I need to clarify the location. Can you provide more details about where this occurred, such as the street name or nearest intersection?"
                
        elif intent == "ready_for_processing":
            if tool_result["result"].get("status") == "completed":
                confirmation = tool_result["result"].get("confirmation_number", "pending")
                claim_id_val = get_claim_field(self.current_claim_data, F.claim_id, "unknown")
                message = f"Thank you for all the information. I have everything needed for claim {claim_id_val}. Your claim has been submitted and you should receive confirmation number {confirmation} shortly."
            else:
                message = "I'm having trouble processing your claim. Let me connect you with a specialist who can help."
        else:
            # Use tool result message or default
            message = tool_result.get("message", "I'm here to help with your claim. What would you like to know?")
        
        return {
            "message": message,
            "tool_call_made": tool_result.get("tool_name"),
            "tool_result": tool_result.get("result")
        }

    def _generate_direct_response(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate direct response without tool calls"""
        
        context_lower = analysis["context"].lower()
        
        # Handle common questions
        if "how long" in context_lower:
            message = "Claim processing typically takes 3-5 business days once we have all the required information."
        elif "what do you need" in context_lower or "what information" in context_lower:
            if self.current_claim_data:
                message = "I still need a few more details: your name, phone, the incident date and time, the city or street, and a short description of what happened."
            else:
                message = "To start your claim, I need your name and phone, then the date, time, location, and a brief description of what happened."
        elif "deductible" in context_lower:
            message = "I can help once your claim details are recorded. Let's capture your name, phone, date, time, location, and a brief description first."
        else:
            message = "I'm here to help with your claim. Could you tell me more about what you need assistance with?"
        
        return {
            "message": message,
            "tool_call_made": None
        }

    # Helper methods
    def _extract_policy_number(self, text: str) -> Optional[str]:
        """Extract policy number from text"""
        import re
        patterns = [
            r'(POL-\d+)',
            r'(INT-\d+)',
            r'(\d{6,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.upper())
            if match:
                return match.group(1)
        return None

    def _generate_claim_id(self) -> str:
        """Generate unique claim ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        return f"CL-{timestamp}"

    def _is_claim_ready_for_processing(self) -> bool:
        """Check if claim is ready for processing"""
        from src.tools.claim_validation import validate_claim_info
        
        if not self.current_claim_data:
            return False
            
        validation_result = validate_claim_info(self.current_claim_data)
        return validation_result["is_valid"]

    # Lightweight entity extraction from free text
    def _update_claim_data_from_text(self, text: str) -> None:
        """Best-effort extraction of fields from user's text to populate claim data."""
        import re
        from src.tools.claim_validation import validate_phone_format, validate_date_format, validate_time_format

        content = text.strip()
        lower = content.lower()

        # Phone number
        phone_candidates = re.findall(r"(\+?\d[\d\s().-]{9,}\d)", content)
        for cand in phone_candidates:
            if validate_phone_format(cand):
                set_claim_field(self.current_claim_data, F.insured_phone, cand, self._on_field_updated)
                break

        # Date (YYYY-MM-DD)
        date_match = re.search(r"(20\d{2}-\d{2}-\d{2})", content)
        if date_match and validate_date_format(date_match.group(1)):
            set_claim_field(self.current_claim_data, F.incident_date, date_match.group(1), self._on_field_updated)

        # Time (HH:MM 24h)
        time_match = re.search(r"\b(\d{1,2}:\d{2})\b", content)
        if time_match and validate_time_format(time_match.group(1)):
            # Normalize to HH:MM
            hh, mm = time_match.group(1).split(":")
            set_claim_field(self.current_claim_data, F.incident_time, f"{int(hh):02d}:{mm}", self._on_field_updated)

        # Name (simple pattern)
        name_match = re.search(r"(?:my name is|this is)\s+([A-Za-z ,.'-]{3,})", lower)
        if name_match:
            name_val = name_match.group(1).strip().title()
            # Stop at first punctuation suggesting end
            name_val = re.split(r"[.,]", name_val)[0].strip()
            set_claim_field(self.current_claim_data, F.insured_name, name_val, self._on_field_updated)

        # Injuries
        if "no injur" in lower or "nobody was hurt" in lower or "no one was hurt" in lower:
            set_claim_field(self.current_claim_data, F.injuries_reported, False, self._on_field_updated)
        elif "injur" in lower or "hurt" in lower:
            set_claim_field(self.current_claim_data, F.injuries_reported, True, self._on_field_updated)

        # Witness
        if "witness" in lower:
            if "no witness" in lower or "without witness" in lower:
                set_claim_field(self.current_claim_data, F.witness_present, False, self._on_field_updated)
            elif "with witness" in lower or "a witness" in lower:
                set_claim_field(self.current_claim_data, F.witness_present, True, self._on_field_updated)

        # Description: if long text and not set
        if ("accident" in lower or "incident" in lower or "collision" in lower or len(content) > 30):
            if not self.current_claim_data.get("incident_description"):
                set_claim_field(self.current_claim_data, F.incident_description, content[:300], self._on_field_updated)

    def _log_completion_banner(self) -> None:
        """Print a prominent banner indicating completion of required info."""
        try:
            line = "=" * 80
            msg = "ALL REQUIRED CLAIM INFORMATION HAS BEEN COLLECTED"
            print(line)
            print(f"{msg}")
            print(line)
        except Exception:
            pass

    def apply_claim_patches(self, patch_ops: List[Dict[str, Any]]) -> None:
        """Apply JSON patch operations to current_claim_data and log field updates."""
        apply_json_patch(self.current_claim_data, patch_ops, on_field_updated=self._on_field_updated)


def create_supervisor_agent() -> ClaimsSupervisorAgent:
    """Factory function to create supervisor agent"""
    return ClaimsSupervisorAgent()

