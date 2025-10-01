"""Voice LangGraph Agent Package.

A modular voice agent implementation using:
- LangGraph for workflow orchestration
- OpenAI Realtime API for voice interaction
- Trustcall for structured data extraction

Key components:
- schema.py: PropertyClaim Pydantic model with validation
- state.py: LangGraph state definitions
- prompts.py: Centralized prompt management
- tools.py: Realtime API tool definitions
- nodes.py: LangGraph nodes (supervisor, extraction, etc.)
- edges.py: Routing logic between nodes
- graph_builder.py: Workflow construction
- utils.py: Audio and utility functions including timezone support
- voice_agent.py: Main agent implementation
"""

from .voice_agent import VoiceAgent, main
from .graph_builder import build_voice_agent_graph, build_supervisor_only_graph
from .state import VoiceAgentState
from .schema import PropertyClaim
from .tools import submit_claim_payload

__all__ = [
    "VoiceAgent",
    "main",
    "build_voice_agent_graph", 
    "build_supervisor_only_graph",
    "VoiceAgentState",
    "PropertyClaim",
    "submit_claim_payload",
]

__version__ = "1.0.0"
