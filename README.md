# FNOL Chatbot

A conversational AI system for processing First Notice of Loss insurance claims using LangChain and LangGraph.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (create `.env` file):
```
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

Run the chatbot:
```bash
python main.py
```

Type messages to report insurance claims. Exit with "bye" or "quit".

## Testing

Run incremental update tests:
```bash
python test_trustcall_patches.py
``` 