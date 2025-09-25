"""Claims Handler Agents - OpenAI Realtime Agents Pattern Implementation

This module provides agents following the supervisor pattern from OpenAI Realtime Agents:
- Junior realtime agent handles basic interactions  
- Supervisor agent handles complex decisions via tool calls
- Payload processor handles final claim submission
"""

from .realtime_agent import create_claims_realtime_agent, ClaimsRealtimeAgent
from .supervisor_agent import create_supervisor_agent, ClaimsSupervisorAgent  
from .payload_processor import create_payload_processor, PayloadProcessorAgent

__all__ = [
    'create_claims_realtime_agent',
    'ClaimsRealtimeAgent', 
    'create_supervisor_agent',
    'ClaimsSupervisorAgent',
    'create_payload_processor',
    'PayloadProcessorAgent'
]