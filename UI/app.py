import gradio as gr
import json
import uuid
import threading
import time
import sys
import os
import base64
from typing import Dict, Any, List, Generator, Tuple
import asyncio
from functools import lru_cache

# Add the parent directory to the path to import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.builder import create_graph
from src.schema import example_json, FNOLPayload
from langchain_core.messages import SystemMessage, HumanMessage

from src.state import ConvoState

class IntactBotUI:
    def __init__(self):
        self.graph = create_graph()
        self.thread_id = str(uuid.uuid4())
        self.config = {
            "configurable": {
                "thread_id": self.thread_id,
            }
        }
        self.conversation_history = []
        self.current_payload = FNOLPayload(claim=example_json)
        self.is_form_complete = False
        self.is_processing = False
        self._cached_payload_str = None  # Cache for formatted payload
        self._payload_hash = None  # Hash to detect payload changes
        
        # Initialize with empty state
        initial_human_message = HumanMessage(content=" ")
        self.initial_state: ConvoState = {
            "messages": [initial_human_message],
            "payload": self.current_payload,
            "is_form_complete": self.is_form_complete,
        }
        
        # Get initial AI message
        self.initial_chat_history = asyncio.run(self._get_initial_message())
    
    async def _get_initial_message(self) -> List[Dict[str, str]]:
        """Get the initial AI message by streaming the initial state with a whitespace message."""
        try:
            events = self.graph.astream(self.initial_state, self.config, stream_mode="values")
            
            async for event in events:
                if "messages" in event and event["messages"]:
                    last_message = event["messages"][-1]
                    if hasattr(last_message, 'content') and last_message.content.strip():
                        return [{"role": "assistant", "content": last_message.content}]
            
            return [{"role": "assistant", "content": "Hello! I'm here to help you process your First Notice of Loss claim. Please share the details of your claim."}]
        except Exception as e:
            print(f"Error getting initial message: {e}")
            return [{"role": "assistant", "content": "Hello! I'm here to help you process your First Notice of Loss claim. Please share the details of your claim."}]
    
    def _compute_payload_hash(self) -> str:
        """Compute a hash of the current payload for change detection."""
        if self.current_payload:
            payload_str = str(self.current_payload.model_dump()) if hasattr(self.current_payload, 'model_dump') else str(self.current_payload)
            return str(hash(payload_str))
        return "empty"
    
    async def process_message(self, message: str, history: List[List[str]]) -> Tuple[List[List[str]], str, bool]:
        """Process user message and return updated chat history, payload, and form completion status"""
        if not message.strip():
            return history, self.format_payload(), self.is_form_complete
        
        self.is_processing = True
        
        # Add user message to history
        if history is None:
            history = []
        history.append([message, None])
        
        try:
            # Update state with user input
            # self.initial_state["messages"].append(HumanMessage(content=message))
            
            # Stream events from the graph
            # events = self.graph.stream(self.initial_state, self.config, stream_mode="values")
            events = self.graph.astream({"messages": [HumanMessage(content=message)]}, self.config, stream_mode="values")
            
            agent_response = ""
            async for event in events:
                # Extract agent response from messages
                if "messages" in event and event["messages"]:
                    last_message = event["messages"][-1]
                    if hasattr(last_message, 'content') and last_message.content != message:
                        agent_response = last_message.content
                
                # Update payload if changed
                if "payload" in event and event["payload"]:
                    self.current_payload = event["payload"]
                    self.initial_state["payload"] = self.current_payload
                    # Invalidate cache when payload changes
                    self._cached_payload_str = None
                    self._payload_hash = None
                
                # Update form complete status
                if "is_form_complete" in event:
                    self.is_form_complete = event["is_form_complete"]
            
            # Update history with agent response
            if agent_response:
                history[-1][1] = agent_response
            else:
                history[-1][1] = "I'm processing your request..."
                
        except Exception as e:
            history[-1][1] = f"Error: {str(e)}"
        
        self.is_processing = False
        return history, self.format_payload(), self.is_form_complete
    
    def format_payload(self) -> str:
        """Format the current payload for display with caching for performance."""
        try:
            # Check if payload has changed using hash comparison
            current_hash = self._compute_payload_hash()
            if self._payload_hash == current_hash and self._cached_payload_str is not None:
                return self._cached_payload_str
            
            # Payload has changed, recompute formatted string
            if self.current_payload:
                payload_dict = self.current_payload.model_dump() if hasattr(self.current_payload, 'model_dump') else self.current_payload
                formatted_payload = json.dumps(payload_dict, indent=2, ensure_ascii=False)
            else:
                formatted_payload = "No payload data available"
            
            # Cache the result
            self._cached_payload_str = formatted_payload
            self._payload_hash = current_hash
            
            return formatted_payload
        except Exception as e:
            return f"Error formatting payload: {str(e)}"
    
    def reset_conversation(self) -> Tuple[List[Dict[str, str]], str, bool]:
        """Reset the conversation and payload"""
        self.thread_id = str(uuid.uuid4())
        self.config = {
            "configurable": {
                "thread_id": self.thread_id,
            }
        }
        self.conversation_history = []
        self.current_payload = FNOLPayload(claim=example_json)
        self.is_form_complete = False
        
        # Clear cache
        self._cached_payload_str = None
        self._payload_hash = None
        
        initial_human_message = HumanMessage(content=" ")
        self.initial_state: ConvoState = {
            "messages": [initial_human_message],
            "payload": self.current_payload,
            "is_form_complete": self.is_form_complete,
        }
        
        self.initial_chat_history = asyncio.run(self._get_initial_message())
        return self.initial_chat_history, self.format_payload(), self.is_form_complete

@lru_cache(maxsize=1)
def get_logo_data_uri():
    """Convert logo to base64 data URI with caching"""
    try:
        # Get the current directory of this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "intactbot_logo.png")
        
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode()
                return f"data:image/png;base64,{img_data}"
        else:
            return None
    except Exception as e:
        print(f"Error loading logo: {e}")
        return None

def create_ui():
    """Create and return the Gradio interface"""
    bot = IntactBotUI()
    logo_uri = get_logo_data_uri()
    
    # Custom CSS for styling
    custom_css = """
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    .main-container {
        max-width: 1400px;
        margin: 0 auto;
    }
    .logo-container {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .logo-container h1 {
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        font-size: 2.5rem;
        background: linear-gradient(135deg, #1f2937 0%, #374151 50%, #111827 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 15px 0 10px 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        letter-spacing: -0.5px;
    }
    .logo-container p {
        font-family: 'Poppins', sans-serif;
        font-weight: 400;
        color: #6b7280;
        font-size: 1.1rem;
        margin: 0;
    }
    .chat-container {
        height: 500px;
    }
    .payload-container {
        height: 500px;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 12px;
    }
    .processing-indicator {
        color: #007bff;
        font-style: italic;
    }
    /* Custom red styling for Send button */
    .send-button {
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 8px rgba(220, 38, 38, 0.3) !important;
    }
    .send-button:hover {
        background: linear-gradient(135deg, #b91c1c 0%, #991b1b 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4) !important;
    }
    .send-button:active {
        transform: translateY(0) !important;
    }
    """
    
    with gr.Blocks(css=custom_css, title="IntactBot - First Notice of Loss Agent") as demo:
        # Helper functions for dynamic UI updates
        def create_payload_header(is_complete: bool) -> str:
            if is_complete:
                return "<h3>📋 Real-time Payload ✅ (Form is Complete)</h3>"
            else:
                return "<h3>📋 Real-time Payload</h3>"

        def create_info_panel(is_complete: bool) -> str:
            background_color = "#e6ffed" if is_complete else "#f0f7ff"
            return f"""
            <div style="margin-top: 10px; padding: 10px; background: {background_color}; border-radius: 5px; font-size: 12px;">
                <strong>ℹ️ Payload Information:</strong><br>
                This panel shows the real-time state of the claim data being processed by the LangGraph agent.
                The payload updates automatically as the conversation progresses.
            </div>
            """

        # Create logo HTML with fallback
        if logo_uri:
            logo_html = f'<img src="{logo_uri}" alt="IntactBot Logo" style="max-height: 80px;">'
        else:
            logo_html = '<div style="font-size: 48px; margin: 10px;">🤖</div>'
        
        gr.HTML(f"""
        <div class="logo-container">
            {logo_html}
            <h1>IntactBot - First Notice of Loss Agent</h1>
            <p>Chat with the AI agent to process First Notice of Loss (FNOL) claims</p>
        </div>
        """)
        
        with gr.Row():
            # Left side - Chat interface
            with gr.Column(scale=1):
                gr.HTML("<h3>💬 Chat Conversation</h3>")
                
                chatbot = gr.Chatbot(
                    value=bot.initial_chat_history,
                    elem_classes="chat-container",
                    show_label=False,
                    avatar_images=None,
                    type='messages'
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Type your message about the claim...",
                        show_label=False,
                        scale=4,
                        container=False
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1, elem_classes="send-button")
                
                with gr.Row():
                    clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")
                
                # Loading indicator (hidden by default)
                loading_indicator = gr.HTML(
                    value="",
                    visible=True,
                    elem_classes="processing-indicator"
                )
            
            # Right side - Payload display
            with gr.Column(scale=1):
                payload_header = gr.HTML(create_payload_header(bot.is_form_complete))
                
                payload_display = gr.Code(
                    value=bot.format_payload(),
                    language="json",
                    show_label=False,
                    elem_classes="payload-container",
                    interactive=False
                )
                
                info_panel = gr.HTML(create_info_panel(bot.is_form_complete))
        
        async def send_message(message, history):
            """Process user message and stream updates to the UI."""
            if not message.strip():
                yield history, "", bot.format_payload(), "", create_payload_header(bot.is_form_complete), create_info_panel(bot.is_form_complete)
                return

            # Append user message to history for immediate display
            history.append({"role": "user", "content": message})
            yield history, "", bot.format_payload(), "🤖 Processing...", create_payload_header(bot.is_form_complete), create_info_panel(bot.is_form_complete)

            # Convert history to the old format for processing
            # We need to use the history *before* adding the new user message
            # because process_message adds it internally.
            old_format_history = []
            if history[:-1]:  # Exclude the last user message
                for msg in history[:-1]:
                    if msg.get('role') == 'user':
                        old_format_history.append([msg['content'], None])
                    elif msg.get('role') == 'assistant' and old_format_history:
                        # Ensure we don't append to a non-existent list
                        if old_format_history:
                            old_format_history[-1][1] = msg['content']

            # Process the message
            updated_history_old, updated_payload, is_form_complete = await bot.process_message(message, old_format_history)
            
            # Convert back to new message format
            new_format_history = []
            # Preserve initial AI message if it exists
            if history and history[0].get('role') == 'assistant':
                new_format_history.append(history[0])
            
            for user_msg, assistant_msg in updated_history_old:
                new_format_history.append({"role": "user", "content": user_msg})
                if assistant_msg:
                    new_format_history.append({"role": "assistant", "content": assistant_msg})
            
            yield new_format_history, "", updated_payload, "", create_payload_header(is_form_complete), create_info_panel(is_form_complete)
        
        def clear_chat():
            cleared_history, cleared_payload, is_form_complete = bot.reset_conversation()
            return cleared_history, cleared_payload, "", create_payload_header(is_form_complete), create_info_panel(is_form_complete)
        
        # Event handlers
        send_btn.click(
            send_message,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input, payload_display, loading_indicator, payload_header, info_panel]
        )
        
        msg_input.submit(
            send_message,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input, payload_display, loading_indicator, payload_header, info_panel]
        )
        
        clear_btn.click(
            clear_chat,
            outputs=[chatbot, payload_display, loading_indicator, payload_header, info_panel]
        )
    
    return demo

def find_available_port(start_port=7860, max_attempts=10):
    """Find an available port starting from start_port"""
    import socket
    
    for i in range(max_attempts):
        port = start_port + i
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return None

def main():
    """Launch the Gradio app"""
    print("🚀 Starting IntactBot UI...")
    
    # Find an available port
    port = find_available_port()
    if port is None:
        print("❌ Could not find an available port. Please check if other Gradio apps are running.")
        print("💡 Try closing other applications or restart your terminal.")
        return
    
    print(f"🔗 App will be available at: http://127.0.0.1:{port}")
    
    # Create the UI
    demo = create_ui()
    
    # Launch the app
    try:
        demo.launch(
            server_name="127.0.0.1",
            server_port=port,
            show_error=True,
            quiet=False,
            debug=False,
            inbrowser=True  # Automatically open browser
        )
    except Exception as e:
        print(f"❌ Failed to launch app: {e}")
        print("💡 Try running: pkill -f gradio")
        print("💡 Or restart your terminal and try again.")

if __name__ == "__main__":
    main() 