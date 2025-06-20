from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode as BaseToolNode
import pgeocode
import pandas as pd
from src.schema import example_json

def create_tool_node_with_fallback(tools: list) -> dict:
    return BaseToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )

def handle_tool_error(state) -> dict:
    error = state.get("error")
    retry_count = state.get("api_retry_count", 0)
    
    if retry_count >= 2:
        return {
            "messages": [
                ToolMessage(
                    content="API call failed multiple times. Concluding the conversation.",
                    tool_call_id=state["messages"][-1].tool_calls[0]["id"],
                )
            ],
            "process_complete": True    
        }
    
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ],
        "api_retry_count": retry_count + 1
    }

def _print_event(event: dict, _printed: set, max_length=1500):
    current_state = event.get("dialog_state")
    if current_state:
        print("Currently in: ", current_state[-1])
    message = event.get("messages")
    if message:
        if isinstance(message, list):
            message = message[-1]
        if message.id not in _printed:
            msg_repr = message.pretty_repr(html=True)
            if len(msg_repr) > max_length:
                msg_repr = msg_repr[:max_length] + " ... (truncated)"
            print(msg_repr)
            _printed.add(message.id)
            
def get_mermaid_code(graph):

    mermaid_code = graph.get_graph(xray=True).draw_mermaid()
    
    print("=== MERMAID GRAPH CODE ===")
    print(mermaid_code)
    print("=========================")
    
    # Save to file for easy copying
    with open("graph.mmd", "w") as f:
        f.write(mermaid_code)
    
    print(f"Mermaid code also saved to: graph.mmd")
    print("You can copy this code and paste it into:")
    print("- https://mermaid.live/")
    print("- https://mermaid-js.github.io/mermaid-live-editor/")

def get_city_state(zip_code):
    nomi = pgeocode.Nominatim('us')  # Use 'us' for United States, change as needed
    location = nomi.query_postal_code(zip_code)
    
    if pd.notnull(location.place_name) and pd.notnull(location.state_code):
        return location.place_name, location.state_code
    else:
        return None, None

def check_payload_completeness(state) -> bool:
    """Check if payload has been updated from example values for required fields."""
    
    if not state.get("payload") or not state["payload"].claim:
        return False
    
    claim = state["payload"].claim.model_dump()

    print("Checking payload completeness...")
    
    # Required fields that should differ from example
    required_checks = [
        # claim["claim_id"] != example_json["claim_id"],
        claim["policy"]["number"] != example_json["policy"]["number"],
        claim["insured"]["full_name"] != example_json["insured"]["full_name"],
        claim["incident"]["datetime"] != example_json["incident"]["datetime"],
        claim["incident"]["location"]["city"] != example_json["incident"]["location"]["city"],
        claim["incident"]["location"]["state"] != example_json["incident"]["location"]["state"],
        claim["incident"]["vehicles_involved"] != example_json["incident"]["vehicles_involved"]
    ]
    
    return all(required_checks)