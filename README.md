# FNOL Chatbot

A conversational AI system for processing First Notice of Loss (FNOL) insurance claims using LangChain, LangGraph, and OpenAI. The system extracts structured claim data from natural language conversations and supports incremental updates.
Check TrustCall for more details: https://github.com/hinthornw/trustcall/tree/main/trustcall

## Features

- **Conversational Interface**: Natural language claim reporting
- **Structured Data Extraction**: Uses trustcall to extract claim details into structured format
- **Incremental Updates**: Supports adding information across multiple conversation turns
- **Graph-based Architecture**: Agent → Extractor → Tools workflow using LangGraph
- **Web UI**: Streamlit-based interface available in `/UI` directory

## Architecture

The system uses a graph-based conversation flow:
- **Agent Node**: Handles conversation and determines next actions
- **Extractor Node**: Extracts structured FNOL data using trustcall
- **Tools Node**: Provides additional capabilities when needed

## Data Structure

Extracts comprehensive claim information including:
- Policy and insured details
- Incident location, time, and description  
- Vehicle information and damage
- Injuries and witnesses
- Police report details

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file with required variables:
```
OPENAI_API_KEY=your_openai_api_key_here
LANGSMITH_API_KEY=your_langsmith_key_here  # optional
```

## Usage

### Command Line Interface
```bash
python main.py
```

### Web Interface
```bash
cd UI
streamlit run app.py
```

Type messages to report insurance claims. Exit CLI with "bye" or "quit".

## Testing

Run incremental update tests:
```bash
python test_trustcall_patches.py
```

## Corporate Network

The system includes SSL workarounds for corporate networks. Uncomment the SSL configuration in `main.py` if needed. 
