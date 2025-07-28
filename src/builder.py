from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import tools_condition
from src.state import ConvoState
from src.tools import get_preliminary_estimate
from src.nodes import agent, extractor
from src.utils import create_tool_node_with_fallback

def create_graph():
    """
    Create and compile the LangGraph workflow for Claims Handler Agent.
    
    Performance optimizations:
    - Uses MemorySaver for fast in-memory state management
    - Efficient node routing with conditional edges
    - Fallback tools for error handling
    """
    builder = StateGraph(ConvoState)
 
    # Add nodes to the graph
    builder.add_node("agent", agent)
    builder.add_node("extractor", extractor)
    builder.add_node("API-tool", create_tool_node_with_fallback([get_preliminary_estimate]))

    # Set entry point
    builder.set_entry_point("agent")
    
    # Define workflow routing
    builder.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "API-tool",
            "__end__": "extractor"
        }
    )
    builder.add_edge("API-tool", "extractor")
    builder.add_edge("extractor", END)

    # Use in-memory storage for better performance
    # For production, consider using SQL storage:
    # conn_string = (
    #     "DRIVER={ODBC Driver 17 for SQL Server};"
    #     f"SERVER={os.getenv("SQL_SERVER")};"
    #     f"DATABASE={os.getenv("SQL_DATABASE")};"
    #     f"UID={os.getenv("SQL_USERNAME")};"
    #     f"PWD={os.getenv("SQL_PWD")};"
    # )
    # memory = MSSQLSaver(conn_string)
    memory = MemorySaver()

    return builder.compile(checkpointer=memory)
