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
    builder.add_node("tools", create_tool_node_with_fallback([get_preliminary_estimate]))

    builder.set_entry_point("agent")
    
    builder.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            "__end__": "extractor"
        }
    )
    builder.add_edge("tools", "agent")
    builder.add_conditional_edges(
        "extractor",
        lambda x: "agent" if x["is_form_complete"] else "__end__",
        {
            "agent": "agent",
            "__end__": END
        }
    )

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

# from langgraph.graph import StateGraph
# from langgraph.checkpoint.memory import MemorySaver
# from src.state import ConvoState
# from langgraph.graph import END, START, StateGraph
# from src.tools import get_preliminary_estimate
# from src.nodes import agent, extractor
# from src.utils import create_tool_node_with_fallback

# def create_graph():

#     builder = StateGraph(ConvoState)
 
#     builder.add_node("agent", agent)
#     builder.add_node("extractor", extractor)
#     builder.add_node("API", create_tool_node_with_fallback([get_preliminary_estimate]))

#     builder.set_entry_point("agent")
#     builder.add_edge("agent", "extractor")
#     builder.add_conditional_edges(
#         "extractor",
#         lambda x: "json_complete" if x["is_form_complete"] else "json_incomplete",
#         {
#             "json_incomplete": END,
#             "json_complete": "API"
#         }
#     )
#     builder.add_edge("API", "agent")
#     builder.add_conditional_edges(
#         "agent",
#         lambda x: "process_complete" if x["process_complete"] else "process_incomplete",
#         {
#             "process_complete": END,
#             "process_incomplete": "extractor"
#         }
#     )
#     builder.add_edge("API", END)

#     # conn_string = (
#     #     "DRIVER={ODBC Driver 17 for SQL Server};"
#     #     f"SERVER={os.getenv("SQL_SERVER")};"
#     #     f"DATABASE={os.getenv("SQL_DATABASE")};"
#     #     f"UID={os.getenv("SQL_USERNAME")};"
#     #     f"PWD={os.getenv("SQL_PWD")};"
#     # )
#     # memory = MSSQLSaver(conn_string)
#     memory = MemorySaver()

#     return builder.compile(checkpointer=memory)#, interrupt_before=["API"])

