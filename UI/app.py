import gradio as gr
import json
import uuid
import sys
import os
import base64
from typing import Dict, Any, List, Tuple
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
        self.config = {"configurable": {"thread_id": self.thread_id}}
        self.current_payload = FNOLPayload(claim=example_json)
        self.is_form_complete = False
        
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
        """Get the initial AI message"""
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
    
    async def process_message(self, message: str, history: List[List[str]]) -> Tuple[List[List[str]], str, bool]:
        """Process user message and return updated chat history, payload, and form completion status"""
        if not message.strip():
            return history, self.format_payload(), self.is_form_complete
        
        # Add user message to history
        if history is None:
            history = []
        history.append([message, None])
        
        try:
            # Stream events from the graph
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
        
        return history, self.format_payload(), self.is_form_complete
    
    def format_payload(self) -> str:
        """Format the current payload for display"""
        try:
            if self.current_payload:
                payload_dict = self.current_payload.model_dump() if hasattr(self.current_payload, 'model_dump') else self.current_payload
                return json.dumps(payload_dict, indent=2, ensure_ascii=False)
            else:
                return "No payload data available"
        except Exception as e:
            return f"Error formatting payload: {str(e)}"
    
    def reset_conversation(self) -> Tuple[List[Dict[str, str]], str, bool]:
        """Reset the conversation and payload"""
        self.thread_id = str(uuid.uuid4())
        self.config = {"configurable": {"thread_id": self.thread_id}}
        self.current_payload = FNOLPayload(claim=example_json)
        self.is_form_complete = False
        
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
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "intactbot_logo.png")
        
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode()
                return f"data:image/png;base64,{img_data}"
            return None
    except Exception as e:
        print(f"Error loading logo: {e}")
        return None

def create_ui():
    """Create and return the Gradio interface"""
    bot = IntactBotUI()
    logo_uri = get_logo_data_uri()
    
    # Clean CSS with Red/Black/Gray color scheme
    custom_css = """
    .main-container {
        max-width: 1400px;
        margin: 0 auto;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .logo-container {
        display: flex;
        align-items: center;
        padding: 8px 20px;
        background: #f8f9fa;
        border-radius: 8px;
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
        position: relative;
    }
    .logo-left {
        position: absolute;
        left: 20px;
    }
    .logo-text {
        text-align: center;
        width: 100%;
    }
    .logo-container h1 {
        font-weight: 600;
        font-size: 2.07rem;
        color: #2c3e50;
        margin: 0;
    }
    .logo-container p {
        color: #666;
        font-size: 1.15rem;
        margin: 0;
    }
    .chat-container {
        height: 500px;
        border: 1px solid #ddd;
        border-radius: 8px;
    }
    .payload-container {
        height: 500px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 12px;
        border: 1px solid #ddd;
        border-radius: 8px;
    }
    .processing-indicator {
        color: #666;
        font-style: italic;
        font-size: 14px;
    }
    /* Red button styling for Intact branding */
    .send-button {
        background: #dc3545 !important;
        border: 1px solid #dc3545 !important;
        color: white !important;
        font-weight: 500 !important;
    }
    .send-button:hover {
        background: #c82333 !important;
        border-color: #c82333 !important;
    }
    /* Clean section headers */
    .section-header {
        color: #333;
        font-weight: 600;
        margin-bottom: 10px;
        padding: 8px 0;
        border-bottom: 2px solid #dc3545;
    }
    /* Payload status styling */
    .payload-complete {
        color: #28a745;
        font-weight: 600;
    }
    .payload-incomplete {
        color: #666;
        font-weight: 500;
    }
    """
    
    with gr.Blocks(css=custom_css, title="IntactBot - First Notice of Loss Agent") as demo:
        # Helper functions for dynamic UI updates
        def create_payload_header(is_complete: bool) -> str:
            status_class = "payload-complete" if is_complete else "payload-incomplete"
            status_text = "✓ Complete" if is_complete else "In Progress"
            return f'<h3 class="section-header">Claim Payload <span class="{status_class}">({status_text})</span></h3>'

        def create_info_panel(is_complete: bool) -> str:
            bg_color = "#f8f9fa" if is_complete else "#f8f9fa"
            return f"""
            <div style="margin-top: 15px; padding: 12px; background: {bg_color}; border-radius: 6px; 
                        border-left: 4px solid #dc3545; font-size: 13px; color: #666;">
                <strong>Real-time Payload:</strong> This panel displays the current state of claim data 
                being processed by the agent. Updates automatically as the conversation progresses.
            </div>
            """

        # Create logo HTML with fallback
        if logo_uri:
            logo_html = f'<img src="{logo_uri}" alt="IntactBot Logo" style="max-height: 58px;">'
        else:
            logo_html = '<div style="font-size: 35px;">🤖</div>'
        
        gr.HTML(f"""
        <div class="logo-container">
            <div class="logo-left">
                {logo_html}
            </div>
            <div class="logo-text">
                <h1>IntactBot-FNOL-v0.1</h1>
                <p>First Notice of Loss Processing Agent</p>
            </div>
        </div>
        """)
        
        with gr.Row():
            # Left side - Chat interface
            with gr.Column(scale=1):
                gr.HTML('<h3 class="section-header">Chat Conversation</h3>')
                
                chatbot = gr.Chatbot(
                    value=bot.initial_chat_history,
                    elem_classes="chat-container",
                    show_label=False,
                    avatar_images=None,
                    type='messages'
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Describe your claim details...",
                        show_label=False,
                        scale=4,
                        container=False
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1, elem_classes="send-button")
                
                with gr.Row():
                    clear_btn = gr.Button("Clear Chat", variant="secondary")
                
                # Loading indicator
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
            """Process user message and update UI"""
            if not message.strip():
                yield history, "", bot.format_payload(), "", create_payload_header(bot.is_form_complete), create_info_panel(bot.is_form_complete)
                return

            # Show processing indicator
            history.append({"role": "user", "content": message})
            yield history, "", bot.format_payload(), "Processing your message...", create_payload_header(bot.is_form_complete), create_info_panel(bot.is_form_complete)

            # Convert to old format for processing
            old_format_history = []
            if history[:-1]:  # Exclude the last user message
                for msg in history[:-1]:
                    if msg.get('role') == 'user':
                        old_format_history.append([msg['content'], None])
                    elif msg.get('role') == 'assistant' and old_format_history:
                        if old_format_history:
                            old_format_history[-1][1] = msg['content']

            # Process the message
            updated_history_old, updated_payload, is_form_complete = await bot.process_message(message, old_format_history)
            
            # Convert back to new message format
            new_format_history = []
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

# Create the demo at module level for Gradio auto-reload
demo = create_ui()

def main():
    """Launch the Gradio app"""
    print("🚀 Starting IntactBot UI...")
    
    # Find an available port
    port = find_available_port()
    if port is None:
        print("❌ Could not find an available port. Please check if other Gradio apps are running.")
        return
    
    print(f"🔗 App will be available at: http://127.0.0.1:{port}")
    
    try:
        demo.launch(
            server_name="127.0.0.1",
            server_port=port,
            show_error=True,
            quiet=False,
            debug=True,
            inbrowser=True
        )
    except Exception as e:
        print(f"❌ Failed to launch app: {e}")

if __name__ == "__main__":
    main() 