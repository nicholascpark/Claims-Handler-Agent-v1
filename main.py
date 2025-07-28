from src.builder import create_graph
from src.utils import _print_event
from langchain_core.messages import SystemMessage, HumanMessage
import uuid
from typing import Dict, Any, List
from src.state import initialize_convo_state
from src.utils import get_mermaid_code
import asyncio
import sys
import time

async def main():
    start_time = time.time()
    print("🚀 Starting Claims Handler Agent...")

    # Create graph once and reuse
    part_1_graph = create_graph()
    
    # Only generate mermaid in debug mode
    if "--debug" in sys.argv:
        get_mermaid_code(part_1_graph)

    thread_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    initial_state = initialize_convo_state()
    _printed = set()

    print(f"✅ Initialization completed in {time.time() - start_time:.2f}s")
    print("="*50)

    # Trigger initial message
    initial_input = {"messages": [HumanMessage(content=" ")]}
    
    try:
        events = part_1_graph.astream(initial_input, config, stream_mode="values")
        async for event in events:
            _print_event(event, _printed)
    except Exception as e:
        print(f"Error during initialization: {e}")
        return

    print("\n💬 Type 'bye', 'quit', or 'bye intactbot' to exit")
    print("="*50)

    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["bye intactbot", "bye", "quit", "exit"]:
                print("✅ You have successfully quit the chat. Refresh the page to start a new conversation.")
                break
            
            if not user_input.strip():
                continue
            
            # Process user input
            events = part_1_graph.astream(
                {"messages": [HumanMessage(content=user_input)]}, 
                config, 
                stream_mode="values"
            )
            
            async for event in events:
                _print_event(event, _printed)
                # Uncomment for debugging payload:
                # print('\nPayload: ', event.get("payload"), '\n')
                
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            print("💡 Please try again or type 'quit' to exit.")
            continue

# User Input → Graph.stream() → Loads from MemorySaver → Agent Node → Extractor Node → Updates State → Saves to MemorySaver

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)
