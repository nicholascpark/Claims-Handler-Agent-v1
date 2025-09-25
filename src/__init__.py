"""Claims Handler Agent v1 - OpenAI Realtime Agents Pattern

A Python implementation of the claims processing agent following the supervisor pattern
from the OpenAI Realtime Agents reference implementation.

Key features:
- Junior realtime agent for basic voice interactions
- Supervisor agent for complex decision making
- Tool-based claim processing workflow  
- Voice interface with real-time audio
- Integration with external claim processing systems

Usage:
    python run_voice_agent.py
"""

from .agents import (
    create_claims_realtime_agent,
    create_supervisor_agent,
    create_payload_processor
)

from .api import (
    ResponsesAPI,
    GetNextResponseFromSupervisor,
    fetch_responses_message
)

from .voice_agent import create_voice_agent
from .agent_config import get_claims_handler_scenario, get_all_scenarios
from .config.settings import settings

__version__ = "1.0.0"
__title__ = "Claims Handler Agent v1"
__description__ = "OpenAI Realtime Agents pattern implementation for insurance claims processing"

__all__ = [
    'create_claims_realtime_agent',
    'create_supervisor_agent', 
    'create_payload_processor',
    'create_voice_agent',
    'ResponsesAPI',
    'GetNextResponseFromSupervisor',
    'fetch_responses_message',
    'get_claims_handler_scenario',
    'get_all_scenarios',
    'settings'
]