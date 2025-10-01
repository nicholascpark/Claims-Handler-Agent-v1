"""Graph builder for the LangGraph voice agent workflow.

Constructs the complete workflow graph with all nodes and edges.
"""

from typing import Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import VoiceAgentState
from .nodes import (
    voice_input_node,
    extraction_worker_node,
    supervisor_node,
    submission_node,
    get_human_representative,
    error_handling_node
)
from .edges import (
    route_after_input,
    route_after_extraction,
    route_after_supervisor,
    route_after_error
)


def build_voice_agent_graph(with_memory: bool = True) -> Any:
    """Build the complete voice agent workflow graph.
    
    This creates a LangGraph workflow with:
    - Voice input processing
    - Data extraction (when needed)
    - Supervisor orchestration
    - Response generation
    - Error handling
    
    The workflow avoids redundant operations by:
    - Only extracting data when necessary (based on keywords)
    - Using a single extraction pass per user message
    - Caching extraction results in state
    
    Args:
        with_memory: Whether to enable conversation memory/persistence
        
    Returns:
        Compiled LangGraph workflow
    """
    # Create the graph with our state schema
    graph = StateGraph(VoiceAgentState)
    
    # Add all nodes to the graph
    graph.add_node("voice_input", voice_input_node)
    graph.add_node("extraction_worker", extraction_worker_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("submission", submission_node)
    graph.add_node("get_human_representative", get_human_representative)
    graph.add_node("error_handler", error_handling_node)
    
    # Add edges from START
    graph.add_edge(START, "voice_input")
    
    # Add conditional edges with routing logic
    graph.add_conditional_edges(
        "voice_input",
        route_after_input,
        {
            "extraction_worker": "extraction_worker",
            "supervisor": "supervisor",
            "error_handler": "error_handler"
        }
    )
    
    graph.add_conditional_edges(
        "extraction_worker",
        route_after_extraction,
        {
            "supervisor": "supervisor",
            "error_handler": "error_handler"
        }
    )
    
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "submission": "submission",
            "get_human_representative": "get_human_representative",
            "end": END,
            "error_handler": "error_handler"
        }
    )
    
    # Submission and human representative nodes route to end
    graph.add_edge("submission", END)
    graph.add_edge("get_human_representative", END)
    
    graph.add_conditional_edges(
        "error_handler",
        route_after_error,
        {
            "end": END,
            "supervisor": "supervisor"
        }
    )
    
    # Compile with checkpointer for persistence
    if with_memory:
        checkpointer = MemorySaver()
        return graph.compile(checkpointer=checkpointer)
    else:
        return graph.compile()


def build_supervisor_only_graph() -> Any:
    """Build a simplified graph that only uses the supervisor.
    
    This is useful for testing or when extraction is handled externally.
    
    Returns:
        Compiled LangGraph workflow
    """
    graph = StateGraph(VoiceAgentState)
    
    # Simple flow: input -> supervisor -> end
    graph.add_node("voice_input", voice_input_node)
    graph.add_node("supervisor", supervisor_node)
    
    graph.add_edge(START, "voice_input")
    graph.add_edge("voice_input", "supervisor")
    graph.add_edge("supervisor", END)
    
    return graph.compile()


# Pre-built graph instances
default_graph = build_voice_agent_graph(with_memory=True)
supervisor_only_graph = build_supervisor_only_graph()
