"""OpenAI Responses API equivalent for Claims Handler Agent

This module implements the /api/responses endpoint pattern from the OpenAI
realtime agents reference implementation, adapted for Python/FastAPI.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.agents.supervisor_agent import create_supervisor_agent
from src.config.settings import settings
from src.utils.time_utils import create_temporal_context_system_message


class ResponsesAPI:
    """
    Python implementation of the OpenAI /api/responses endpoint.
    
    Handles supervisor agent requests with iterative tool calling
    following the exact pattern from the TypeScript reference.
    """
    
    def __init__(self):
        # Use a shared singleton so state persists across calls
        global _shared_supervisor
        try:
            _shared_supervisor
        except NameError:
            _shared_supervisor = create_supervisor_agent()
        self.supervisor_agent = _shared_supervisor
    
    async def process_request(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request to the responses API.
        
        Args:
            request_body: Request with model, input, tools, etc.
            
        Returns:
            Response with output items and status
        """
        
        try:
            # Validate request body
            if not self._validate_request(request_body):
                return {"error": "Invalid request format"}
            
            # Extract conversation history and context
            conversation_history = self._extract_conversation_history(request_body)
            relevant_context = self._extract_relevant_context(request_body)
            
            # Get initial response from supervisor
            supervisor_response = await self.supervisor_agent.get_next_response(
                conversation_history, relevant_context
            )
            
            # Handle iterative tool calls if needed
            return await self._handle_tool_calls(request_body, supervisor_response)
            
        except Exception as e:
            return {"error": f"Processing failed: {str(e)}"}
    
    def _validate_request(self, request_body: Dict[str, Any]) -> bool:
        """Validate the request body format"""
        required_fields = ["model", "input"]
        return all(field in request_body for field in required_fields)
    
    def _extract_conversation_history(self, request_body: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract conversation history from request input"""
        input_items = request_body.get("input", [])
        
        conversation_history = []
        for item in input_items:
            if item.get("type") == "message":
                conversation_history.append({
                    "role": item.get("role", "user"),
                    "content": item.get("content", "")
                })
        
        return conversation_history
    
    def _extract_relevant_context(self, request_body: Dict[str, Any]) -> str:
        """Extract relevant context from the request"""
        input_items = request_body.get("input", [])
        
        # Prefer explicit marker regardless of role
        marker = "=== Relevant Context From Last User Message ==="
        for item in input_items:
            if item.get("type") == "message" and marker in item.get("content", ""):
                content = item["content"]
                parts = content.split(marker)
                if len(parts) > 1:
                    return parts[1].strip()
        
        # Fallback: get last user message content
        for item in reversed(input_items):
            if item.get("type") == "message" and item.get("role") == "user":
                return item.get("content", "")[:200]
        
        return ""
    
    async def _handle_tool_calls(self, original_request: Dict[str, Any], supervisor_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle tool calls iteratively following OpenAI pattern.
        
        This mirrors the handleToolCalls function from supervisorAgent.ts
        """
        
        # If supervisor didn't make tool calls, return direct response
        if not supervisor_response.get("tool_call_made"):
            return self._format_text_response(supervisor_response)
        
        # Handle iterative tool calling (similar to OpenAI implementation)
        current_request = original_request.copy()
        current_response = supervisor_response
        iteration_count = 0
        max_iterations = 10  # Prevent infinite loops
        
        while current_response.get("tool_call_made") and iteration_count < max_iterations:
            iteration_count += 1
            
            # Execute the tool call locally
            tool_call_result = await self._execute_tool_call(
                current_response["tool_call_made"], 
                current_response.get("tool_result", {})
            )
            
            # Add function call and result to request for next iteration
            current_request["input"].extend([
                {
                    "type": "function_call",
                    "call_id": self._generate_call_id(),
                    "name": current_response["tool_call_made"],
                    "arguments": json.dumps(current_response.get("tool_result", {}))
                },
                {
                    "type": "function_call_output", 
                    "call_id": self._generate_call_id(),
                    "output": json.dumps(tool_call_result)
                }
            ])
            
            # Get next response from supervisor
            conversation_history = self._extract_conversation_history(current_request)
            relevant_context = self._extract_relevant_context(current_request)
            
            current_response = await self.supervisor_agent.get_next_response(
                conversation_history, relevant_context
            )
        
        # Return final response
        return self._format_text_response(current_response)
    
    async def _execute_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool call locally and return result"""
        
        try:
            if tool_name == "validateClaimInfo":
                from src.tools.claim_validation import validate_claim_info
                return validate_claim_info(tool_args.get("claim_data", {}))
                
            elif tool_name == "lookupPolicyInfo":
                from src.tools.policy_lookup import lookup_policy_info
                return lookup_policy_info(tool_args.get("policy_number", ""))
                
            elif tool_name == "getLocationDetails":
                from src.tools.location_services import get_location_details
                return get_location_details(tool_args.get("location_string", ""))
                
            elif tool_name == "delegateToProcessor":
                from src.agents.payload_processor import create_payload_processor
                from src.schema.simplified_payload import SimplifiedClaim
                
                claim_data = tool_args.get("simplified_claim", {})
                simplified_claim = SimplifiedClaim(**claim_data)
                processor = create_payload_processor()
                return processor.process_claim_payload(simplified_claim, "supervisor")
            
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
    
    def _format_text_response(self, supervisor_response: Dict[str, Any]) -> Dict[str, Any]:
        """Format supervisor response for realtime API"""
        
        message_text = supervisor_response.get("message", "I'm here to help with your claim.")
        
        return {
            "output": [{
                "type": "message",
                "role": "assistant", 
                "content": [{"type": "output_text", "text": message_text}]
            }],
            "status": "completed"
        }
    
    def _generate_call_id(self) -> str:
        """Generate unique call ID"""
        import uuid
        return str(uuid.uuid4())[:16]


# Tool execution function matching OpenAI pattern
async def fetch_responses_message(request_body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function matching the fetchResponsesMessage from OpenAI implementation.
    
    Args:
        request_body: Request with model, input, tools, etc.
        
    Returns:
        Response dictionary
    """
    api = ResponsesAPI()
    return await api.process_request(request_body)


# Tool function for realtime agent (matches OpenAI pattern)
class GetNextResponseFromSupervisor:
    """
    Tool implementation matching the getNextResponseFromSupervisor from OpenAI.
    
    This is the tool that the junior realtime agent calls.
    """
    
    @staticmethod
    def get_definition() -> Dict[str, Any]:
        """Get tool definition for realtime API"""
        return {
            "type": "function",
            "name": "getNextResponseFromSupervisor", 
            "description": "Determines the next response whenever the agent faces a non-trivial decision, produced by a highly intelligent supervisor agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relevantContextFromLastUserMessage": {
                        "type": "string",
                        "description": "Key information from the user described in their most recent message. Critical to provide as supervisor needs full context."
                    }
                },
                "required": ["relevantContextFromLastUserMessage"],
                "additionalProperties": False
            }
        }
    
    @staticmethod
    async def execute(input_params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Execute the getNextResponseFromSupervisor tool.
        
        Args:
            input_params: Parameters including relevantContextFromLastUserMessage
            context: Optional context with conversation history
            
        Returns:
            Dictionary with nextResponse field
        """
        
        relevant_context = input_params.get("relevantContextFromLastUserMessage", "")
        
        # Extract conversation history from context
        conversation_history = []
        if context and "history" in context:
            history = context["history"]
            conversation_history = [
                {"role": item.get("role", "user"), "content": item.get("content", "")}
                for item in history
                if item.get("type") == "message"
            ]
        
        # Create request body; use Azure chat deployment name with structured history
        input_items: List[Dict[str, Any]] = [
            {
                "type": "message",
                "role": "system",
                "content": "You are processing a request from the junior claims agent."
            },
            {
                "type": "message",
                "role": "system",
                "content": create_temporal_context_system_message(),
            },
            {
                "type": "message",
                "role": "system",
                "content": f"=== Relevant Context From Last User Message ===\n{relevant_context}"
            },
        ]

        for msg in conversation_history:
            try:
                input_items.append({
                    "type": "message",
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            except Exception:
                continue

        request_body = {
            "model": settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
            "input": input_items,
            "tools": []
        }
        
        try:
            # Process through responses API
            response = await fetch_responses_message(request_body)
            
            if response.get("error"):
                return {"nextResponse": "I'm having trouble processing that. Let me connect you with a specialist."}
            
            # Extract text response from output
            output_items = response.get("output", [])
            message_items = [item for item in output_items if item.get("type") == "message"]
            
            if message_items:
                content_items = message_items[0].get("content", [])
                text_items = [item for item in content_items if item.get("type") == "output_text"]
                
                if text_items:
                    return {"nextResponse": text_items[0].get("text", "")}
            
            return {"nextResponse": "I'm here to help with your claim. How can I assist you?"}
            
        except Exception as e:
            return {"nextResponse": "I'm having trouble processing that. Let me connect you with a specialist."}


# Global API instance
_api_instance = None


def get_responses_api() -> ResponsesAPI:
    """Get or create responses API instance (singleton)"""
    global _api_instance
    if _api_instance is None:
        _api_instance = ResponsesAPI()
    return _api_instance

