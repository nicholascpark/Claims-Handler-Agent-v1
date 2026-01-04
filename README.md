# Notera Voice Agent

A multi-modal Voice AI Claims Intake Agent built with LangGraph, OpenAI, and modern async Python. Supports voice-first interactions for First Notice of Loss (FNOL) claims processing.

## Features

- **Voice-First Design**: Primary interaction via voice with text fallback
- **Multi-Language Support**: English, Spanish, and French
- **Real-Time Transcription**: OpenAI Whisper STT
- **Natural TTS Responses**: OpenAI Text-to-Speech
- **Intelligent Extraction**: LangGraph-powered claim data extraction
- **Modern Web UI**: React + TypeScript + Tailwind CSS frontend
- **Conversation Persistence**: SQLite-based session storage

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web Frontend  │────▶│   FastAPI API   │────▶│  LangGraph Agent│
│  (React + TS)   │◀────│   (Python)      │◀────│  (GPT-4o)       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  Voice Recording│     │  OpenAI Services│
│  (MediaRecorder)│     │  (Whisper + TTS)│
└─────────────────┘     └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API Key

### 1. Clone and Setup

```bash
git clone https://github.com/nicholascpark/Claims-Handler-Agent-v1.git
cd Claims-Handler-Agent-v1

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd web && npm install && cd ..
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

Required environment variables:

```bash
OPENAI_API_KEY=sk-your-openai-api-key
```

Optional configuration:

```bash
# Model Settings
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=1000

# Voice Settings
STT_MODEL=whisper-1
TTS_MODEL=tts-1
TTS_VOICE=nova

# Language
DEFAULT_LANGUAGE=en  # en, es, fr

# Server
HOST=0.0.0.0
PORT=8000
```

### 3. Run the Application

**Start the Backend:**

```bash
python run.py
# Server runs at http://localhost:8000
```

**Start the Frontend (separate terminal):**

```bash
cd web
npm run dev
# Frontend runs at http://localhost:5173
```

### 4. Use the Application

1. Open http://localhost:5173 in your browser
2. Allow microphone access when prompted
3. Click the microphone button to start speaking
4. Describe your insurance claim naturally
5. Watch as the AI extracts claim details in real-time

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/start` | POST | Start new conversation, get greeting |
| `/api/chat/message` | POST | Send text message |
| `/api/chat/voice` | POST | Send voice message (base64 audio) |
| `/api/chat/{thread_id}/payload` | GET | Get extracted claim data |
| `/api/chat/{thread_id}/history` | GET | Get conversation history |
| `/api/chat/{thread_id}` | DELETE | Reset conversation |
| `/api/health` | GET | Health check |

## Project Structure

```
Claims-Handler-Agent-v1/
├── app/                      # Backend application
│   ├── api/
│   │   ├── main.py          # FastAPI app factory
│   │   └── routes/
│   │       ├── chat.py      # Chat endpoints
│   │       └── health.py    # Health endpoints
│   ├── agents/
│   │   ├── fnol_agent.py    # LangGraph FNOL agent
│   │   ├── prompts.py       # Multi-language prompts
│   │   └── tools.py         # Agent tools
│   ├── core/
│   │   └── config.py        # Settings management
│   ├── models/
│   │   ├── claim.py         # FNOL data models
│   │   └── conversation.py  # Conversation models
│   └── services/
│       ├── llm/             # OpenAI LLM service
│       ├── voice/           # STT/TTS services
│       └── persistence/     # Database service
├── web/                      # Frontend application
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom hooks
│   │   ├── services/        # API client
│   │   └── types/           # TypeScript types
│   └── public/              # Static assets
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
├── run.py                   # Server startup script
└── README.md
```

## Claim Data Extracted

The agent extracts the following FNOL information:

- **Incident Date & Time**: When the incident occurred
- **Incident Location**: Where it happened (address, city, state)
- **Vehicle Information**: Make, model, year, license plate
- **Damage Description**: Details of damage sustained
- **Injury Information**: Any injuries reported
- **Police Report**: Whether police were involved, report number
- **Other Party Info**: Information about other parties involved

## Development

### Backend Development

```bash
# Run with hot reload
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd web
npm run dev
```

### Build for Production

```bash
# Build frontend
cd web && npm run build

# The backend can serve the built frontend from web/dist
```

## Supported Languages

| Code | Language |
|------|----------|
| `en` | English |
| `es` | Spanish (Espa-ol) |
| `fr` | French (Francais) |

## Troubleshooting

**Microphone not working?**
- Ensure browser has microphone permissions
- Check if another application is using the microphone
- Try refreshing the page

**API errors?**
- Verify `OPENAI_API_KEY` is set correctly
- Check API key has access to required models (gpt-4o, whisper-1, tts-1)
- Ensure sufficient API credits

**Audio playback issues?**
- Check browser audio permissions
- Some browsers block auto-play - click to interact first

## License

MIT License

---

Built with LangGraph, OpenAI, FastAPI, and React.
