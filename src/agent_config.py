"""Agent Configuration - Claims Handler Agent Set

This module defines the agent configuration following the OpenAI Realtime Agents pattern.
It corresponds to the agentConfigs structure in the TypeScript implementation.
"""

from typing import List, Dict, Any
from src.agents.realtime_agent import create_claims_realtime_agent
from src.config.settings import settings


def get_claims_handler_scenario() -> List[Dict[str, Any]]:
    """
    Get the claims handler agent scenario configuration.
    
    This follows the pattern from OpenAI agentConfigs where each scenario
    is defined as a list of agent configurations.
    
    Returns:
        List of agent configurations for the claims scenario
    """
    
    # Create the junior realtime agent
    junior_agent = create_claims_realtime_agent("claimsHandlerAgent")
    
    # Convert to configuration format
    agent_config = {
        "name": junior_agent.name,
        "voice": junior_agent.voice,
        "instructions": junior_agent.instructions,
        "tools": junior_agent.tools,
        "session_config": junior_agent.get_session_config()
    }
    
    return [agent_config]


def get_all_scenarios() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get all available agent scenarios.
    
    This corresponds to the allAgentSets export in the TypeScript implementation.
    
    Returns:
        Dictionary mapping scenario names to agent configurations
    """
    
    return {
        "claimsHandler": get_claims_handler_scenario()
    }


def get_default_scenario() -> str:
    """Get the default scenario key"""
    return "claimsHandler"


def get_company_name() -> str:
    """Get company name for this agent set"""
    return settings.COMPANY_NAME


# For backward compatibility and easy imports
claims_handler_scenario = get_claims_handler_scenario()
all_agent_sets = get_all_scenarios()
default_agent_set_key = get_default_scenario()
company_name = get_company_name()

