from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from src.state import ConvoState
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition
from src.tools import get_preliminary_estimate
from src.nodes import agent, extractor
from src.utils import create_tool_node_with_fallback

def create_graph():

    builder = StateGraph(ConvoState)
 
    builder.add_node("agent", agent)
    builder.add_node("extractor", extractor)
    builder.add_node("API-tool", create_tool_node_with_fallback([get_preliminary_estimate]))

    builder.set_entry_point("agent")
    
    builder.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "API-tool",
            "__end__": "extractor"
        }
    )
    builder.add_edge("API-tool", "agent")
    builder.add_edge("extractor", END)

    # conn_string = (
    #     "DRIVER={ODBC Driver 17 for SQL Server};"
    #     f"SERVER={os.getenv("SQL_SERVER")};"
    #     f"DATABASE={os.getenv("SQL_DATABASE")};"
    #     f"UID={os.getenv("SQL_USERNAME")};"
    #     f"PWD={os.getenv("SQL_PWD")};"
    # )
    # memory = MSSQLSaver(conn_string)
    memory = MemorySaver()

    return builder.compile(checkpointer=memory)#, interrupt_before=["tools"])
