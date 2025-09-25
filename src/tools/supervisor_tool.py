"""Supervisor Tool Handler - Integrates with OpenAI Realtime API

This module implements the getNextResponseFromSupervisor tool for the realtime API,
matching the OpenAI pattern exactly.
"""

import json
import asyncio
from typing import Dict, Any, Optional, List

from src.api.responses_api import GetNextResponseFromSupervisor
from src.config.settings import settings


class SupervisorToolHandler:
    """
    Handles getNextResponseFromSupervisor tool calls from the realtime API.
    
    This class bridges the OpenAI realtime API tool calls with our supervisor
    implementation, following the exact pattern from the reference.
    """
    
    def __init__(self):
        self.supervisor_tool = GetNextResponseFromSupervisor()
    
    async def handle_tool_call(self, tool_call: Dict[str, Any], conversation_context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Handle getNextResponseFromSupervisor tool call.
        
        Args:
            tool_call: Tool call event from realtime API
            conversation_context: Optional conversation context
            
        Returns:
            Tool response dictionary
        """
        
        try:
            # Extract function name and arguments
            function_name = tool_call.get("name", "")
            arguments_str = tool_call.get("arguments", "{}")
            
            if function_name != "getNextResponseFromSupervisor":
                return {
                    "error": f"Unknown tool function: {function_name}"
                }
            
            # Parse arguments
            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                return {
                    "error": "Invalid arguments format"
                }
            
            # Extract parameters
            relevant_context = arguments.get("relevantContextFromLastUserMessage", "")
            
            # Execute supervisor tool
            result = await self.supervisor_tool.execute(
                input_params={"relevantContextFromLastUserMessage": relevant_context},
                context=conversation_context
            )
            
            return result
            
        except Exception as e:
            return {
                "error": f"Tool execution failed: {str(e)}"
            }
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Get tool definition for realtime API"""
        return self.supervisor_tool.get_definition()


# Global tool handler instance
_tool_handler = None


def get_supervisor_tool_handler() -> SupervisorToolHandler:
    """Get or create supervisor tool handler (singleton)"""
    global _tool_handler
    if _tool_handler is None:
        _tool_handler = SupervisorToolHandler()
    return _tool_handler


def create_realtime_tool_response(tool_call_id: str, result: Dict[str, str]) -> Dict[str, Any]:
    """
    Create a realtime API tool response event.
    
    Args:
        tool_call_id: ID of the tool call
        result: Result from supervisor tool
        
    Returns:
        Tool response event for realtime API
    """
    
    # Extract the nextResponse or use error message
    if "nextResponse" in result:
        output = result["nextResponse"]
    elif "error" in result:
        output = result["error"]
    else:
        output = "I'm here to help with your claim. How can I assist you?"
    
    return {
        "type": "conversation.item.create",
        "item": {
            "type": "function_call_output",
            "call_id": tool_call_id,
            "output": output
        }
    }

