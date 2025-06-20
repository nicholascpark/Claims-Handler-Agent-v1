# IntactBot UI

A Gradio-based user interface for the LangGraph First Notice of Loss (FNOL) agent.

## Features

- **Chat Interface**: Interactive conversation with the LangGraph agent
- **Real-time Payload Display**: Live updates of the claim data being processed
- **Loading Indicators**: Visual feedback when the agent is processing
- **Logo Integration**: IntactBot branding with logo display

## Quick Start

### Option 1: Direct Launch
```bash
cd UI
python app.py
```

### Option 2: Using Launch Script (Recommended)
```bash
cd UI
python launch.py
```

The launch script provides better error checking and startup feedback.

## Requirements

- Python 3.8+
- All dependencies from `../requirements.txt`
- Gradio (automatically installed)

## Interface Layout

The UI is split into two main sections:

### Left Side - Chat Conversation
- Input field for typing messages about claims
- Chat history display
- Send button and clear chat functionality
- Loading indicator during processing

### Right Side - Real-time Payload
- JSON display of the current claim data
- Automatically updates as the conversation progresses
- Properly formatted and indented for readability

## Usage

1. Launch the app using one of the methods above
2. Open your browser to `http://127.0.0.1:7860`
3. Start chatting with the IntactBot about your claim
4. Watch the payload update in real-time on the right side
5. Use "Clear Chat" to reset the conversation

## File Structure

- `app.py` - Main Gradio application
- `launch.py` - Launch script with error checking
- `README.md` - This documentation

The UI integrates seamlessly with the existing LangGraph components in the `../src/` directory without modifying any existing files. 