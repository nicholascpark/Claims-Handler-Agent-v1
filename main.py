# import ssl
# import urllib3
# import os

# # Temporary SSL workaround for corporate networks
# ssl._create_default_https_context = ssl._create_unverified_context
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# # Alternative: Set environment variables to disable SSL verification
# os.environ["PYTHONHTTPSVERIFY"] = "0"
# os.environ["CURL_CA_BUNDLE"] = ""

from src.builder import create_graph
from src.utils import _print_event
from langchain_core.messages import SystemMessage, HumanMessage
import uuid
from typing import Dict, Any, List
from src.state import initialize_convo_state
from src.utils import get_mermaid_code

def main():

    part_1_graph = create_graph()
    get_mermaid_code(part_1_graph)

    thread_id = str(uuid.uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    initial_state = initialize_convo_state()

    def user_input_generator():
        yield ""
        while True:
            user_input = input("User: ")
            if user_input.lower() in ["bye intactbot", "bye", "quit"]:
                print("You have successfully quit the chat. Refresh the page to start a new conversation.")
                break
            yield user_input

    _printed = set()

    for user_input in user_input_generator():
        initial_state["user_input"] = user_input
        initial_state["messages"].append(HumanMessage(content=user_input))
        
        events = part_1_graph.stream(initial_state, config, stream_mode="values")
    
        for event in events:
            _print_event(event, _printed)
            # print('\nPayload: ', event["payload"], '\n')

# User Input → Graph.stream() → Loads from MemorySaver → Agent Node → Extractor Node → Updates State → Saves to MemorySaver

if __name__ == "__main__":
    main()
