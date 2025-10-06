# Claims Handler Voice Agent v1

A production-ready, real-time voice agent for insurance claim intake built with LangGraph, Azure OpenAI Realtime API, FastAPI, and React.

## 🎯 Overview

This application provides an intelligent, conversational voice interface for First Notice of Loss (FNOL) claims processing. It combines:

- **Voice LangGraph Agent**: Intelligent conversation orchestration with structured data extraction
- **Azure OpenAI Realtime API**: Low-latency voice interaction with server VAD
- **FastAPI Backend**: WebSocket server with session management
- **React Frontend**: Modern, responsive web interface with real-time updates

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                       │
│  • Real-time chat display                                       │
│  • Live claim data JSON visualization                           │
│  • Audio capture & playback (Web Audio API)                     │
└────────────────────┬────────────────────────────────────────────┘
                     │ WebSocket (/ws/voice)
┌────────────────────┴────────────────────────────────────────────┐
│                    Backend (FastAPI)                             │
│  • WebSocket server with session management                     │
│  • Multi-user support with isolated sessions                    │
│  • Integration with voice_langgraph                             │
└────────────────────┬────────────────────────────────────────────┘
                     │ Python Integration
┌────────────────────┴────────────────────────────────────────────┐
│                 voice_langgraph Module                           │
│  • LangGraph workflow with checkpointing                        │
│  • Trustcall extraction                                          │
│  • PropertyClaim schema (nested structure)                      │
│  • Tools: submit_claim_payload, get_human_contact              │
└────────────────────┬────────────────────────────────────────────┘
                     │ WebSocket (wss://)
┌────────────────────┴────────────────────────────────────────────┐
│              Azure OpenAI Realtime API                           │
│  • Voice Activity Detection (VAD)                                │
│  • Speech-to-Text (Whisper)                                     │
│  • Text-to-Speech (TTS)                                         │
└─────────────────────────────────────────────────────────────────┘
```

## ✨ Features

### Voice Agent Capabilities
- **Natural Conversation**: Warm, empathetic interactions using GPT-4 Realtime
- **Structured Extraction**: Trustcall-powered extraction into PropertyClaim schema
- **Smart Routing**: LangGraph workflow with conditional edges
- **Multimodal Input**: 🎤 Voice + 💬 Text + 🖼️ Images (NEW!)
  - Voice: Natural conversation with auto-transcription
  - Text: Type precise information (policy numbers, addresses)
  - Images: Upload damage photos, documents (up to 10MB)
- **Tool Calling**: Automatic claim submission and human escalation

### Technical Features
- **Real-time Audio**: Bidirectional audio streaming (PCM16, 24kHz)
- **Multi-user Sessions**: Isolated state per user with thread IDs
- **Conversation Memory**: LangGraph checkpointer for context retention
- **Error Recovery**: Graceful error handling with retry logic
- **Live Updates**: Real-time claim data updates to frontend

### User Experience
- **Visual Feedback**: Live transcription and status indicators
- **Claim Visualization**: JSON display with syntax highlighting
- **Multimodal Input**: Voice, text, and image upload in one interface (NEW!)
- **Microphone Selection**: Choose audio input device
- **Progress Tracking**: See collected vs. missing fields
- **Message Type Indicators**: 🎤 Voice, 💬 Text, 🖼️ Images
- **Responsive Design**: Works on desktop and mobile

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Azure OpenAI account with:
  - GPT-4 deployment (e.g., `gpt-4o`)
  - Realtime API deployment (e.g., `gpt-4o-realtime-preview`)

### 1. Clone and Configure

```bash
git clone <repository-url>
cd Claims-Handler-Agent-v1

# Copy and edit environment variables
cp .env.example .env
# Edit .env with your Azure OpenAI credentials
```

### 2. Start Full Stack (Easiest)

**Linux/Mac:**
```bash
chmod +x start_fullstack.sh
./start_fullstack.sh
```

**Windows:**
```bash
start_fullstack.bat
```

This script will:
1. Start the backend server on `http://localhost:8000`
2. Start the frontend dev server on `http://localhost:5173`
3. Open your browser automatically

### 3. Manual Startup (Alternative)

**Terminal 1 - Backend:**
```bash
cd backend

# Create virtual environment
python -m venv venv

# ⚠️ IMPORTANT: Activate it!
source venv/bin/activate       # Linux/Mac
# OR
venv\Scripts\activate.bat      # Windows

# Install dependencies
pip install -r requirements.txt

# Start server
python main.py
```

> 🔴 **Common Error**: `ModuleNotFoundError: No module named 'fastapi'`  
> **Fix**: You forgot to activate the virtual environment! See [IMMEDIATE_FIX.md](IMMEDIATE_FIX.md)

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### 4. Use the Application

1. Open `http://localhost:5173` in your browser
2. Grant microphone permissions when prompted
3. Select your microphone from the dropdown
4. Click "Start Call" to begin
5. Wait for the agent's greeting
6. Speak naturally to provide claim information

## 📁 Project Structure

```
Claims-Handler-Agent-v1/
├── backend/                      # FastAPI backend server
│   ├── main.py                   # FastAPI app with WebSocket endpoint
│   ├── session_manager.py        # Session and voice agent management
│   ├── requirements.txt          # Python dependencies
│   ├── start.sh / start.bat      # Backend startup scripts
│   └── README.md                 # Backend documentation
│
├── frontend/                     # React frontend application
│   ├── src/
│   │   ├── App.jsx               # Main application component
│   │   ├── hooks/
│   │   │   └── useVoiceAgent.js  # WebSocket & audio management
│   │   └── components/           # UI components
│   ├── public/
│   │   ├── audio-processor-worklet.js   # Microphone capture
│   │   └── audio-playback-worklet.js    # Audio playback
│   ├── package.json              # npm dependencies
│   └── README.md                 # Frontend documentation
│
├── voice_langgraph/              # LangGraph agent module
│   ├── voice_agent.py            # Standalone voice agent (console)
│   ├── graph_builder.py          # LangGraph workflow construction
│   ├── nodes.py                  # Workflow nodes
│   ├── edges.py                  # Routing logic
│   ├── state.py                  # VoiceAgentState definition
│   ├── schema.py                 # PropertyClaim Pydantic schema
│   ├── tools.py                  # LangChain tools
│   ├── prompts.py                # System prompts
│   ├── settings.py               # Configuration
│   └── utils.py                  # Audio/WebSocket utilities
│
├── start_fullstack.sh / .bat     # Unified startup scripts
├── INTEGRATION_GUIDE.md          # Complete integration guide
├── .env.example                  # Environment template
└── README.md                     # This file
```

## 🔧 Configuration

### Environment Variables

Edit `.env` with your settings:

```env
# Azure OpenAI (Required)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key

# Chat API (for supervisor and extraction)
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_CHAT_API_VERSION=2024-08-01-preview

# Realtime API (for voice)
AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME=gpt-4o-realtime-preview
AZURE_OPENAI_REALTIME_API_VERSION=2024-10-01-preview

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Agent Configuration
AGENT_NAME=Kismet AI
COMPANY_NAME=Intact Specialty Insurance
COMPANY_DEPARTMENT=Claims Department
JUNIOR_AGENT_VOICE=shimmer  # alloy, echo, fable, onyx, nova, shimmer
```

### Advanced Settings (voice_langgraph/settings.py)

- `VAD_THRESHOLD`: Voice activity detection sensitivity (0.0-1.0)
- `VAD_SILENCE_DURATION_MS`: Silence duration before ending speech (ms)
- `ENABLE_AUDIO_INPUT`: Enable/disable microphone input
- `ENABLE_TEXT_INPUT`: Enable/disable text input (console mode)
- `REALTIME_AS_TALKER`: Let Realtime API speak (recommended: true)

## 📚 Documentation

- **[QUICK_START.md](QUICK_START.md)**: Get running in 5 minutes
- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)**: Complete architecture and integration details
- **[TEXT_AND_IMAGE_INPUT_GUIDE.md](TEXT_AND_IMAGE_INPUT_GUIDE.md)**: Multimodal input guide (NEW!)
- **[MULTIMODAL_QUICK_REFERENCE.md](MULTIMODAL_QUICK_REFERENCE.md)**: Quick reference for users (NEW!)
- **[backend/README.md](backend/README.md)**: Backend API specification
- **[backend/TROUBLESHOOTING.md](backend/TROUBLESHOOTING.md)**: Backend troubleshooting guide
- **[frontend/README.md](frontend/README.md)**: Frontend development guide
- **[IMMEDIATE_FIX.md](IMMEDIATE_FIX.md)**: Common startup issues
- **[voice_langgraph/](voice_langgraph/)**: Module contains extensive docstrings

## 🎮 Usage Modes

### 1. Web Interface (Recommended)
Full-featured web interface with visual feedback and claim visualization.

```bash
./start_fullstack.sh
# Open http://localhost:5173
```

### 2. Console Mode (Testing)
Standalone voice agent for console-based testing.

```bash
python run_voice_agent.py
```

### 3. API Only
Run backend for integration with custom frontends.

```bash
cd backend
python main.py
# WebSocket endpoint: ws://localhost:8000/ws/voice
```

## 🧪 Testing

### Test Backend Health
```bash
curl http://localhost:8000/health
```

### Test WebSocket
```bash
npm install -g wscat
wscat -c ws://localhost:8000/ws/voice
> {"type": "start_session"}
```

### Visualize LangGraph Workflow
```bash
python see_graph.py
# Generates graph.png
```

## 🔍 Troubleshooting

### Backend Issues

#### ❌ ModuleNotFoundError: No module named 'fastapi'
**Most Common Issue!**

**Quick Fix**:
```bash
cd backend
./start.sh       # Linux/Mac
start.bat        # Windows
```

See **[IMMEDIATE_FIX.md](IMMEDIATE_FIX.md)** for detailed instructions.

**Why**: Backend must run in an activated virtual environment with dependencies installed.

#### Other Backend Issues
- **Port already in use**: Kill process on port 8000 or use different port
- **Azure API errors**: Verify `.env` credentials and deployment names
- **Import errors**: Check `voice_langgraph` directory exists in project root

See **[backend/TROUBLESHOOTING.md](backend/TROUBLESHOOTING.md)** for complete solutions.

### Frontend Issues

#### Audio Issues
- **No audio playback**: Click anywhere on page to resume AudioContext
- **No microphone**: Check browser permissions (chrome://settings/content/microphone)
- **Choppy audio**: Reduce network latency or use faster deployment

#### Connection Issues
- **WebSocket disconnects**: Check Azure OpenAI service health and network
- **Frontend 404**: Ensure backend is running on port 8000
- **Connection refused**: Verify backend started successfully (check terminal)

### Data Issues

#### Extraction Issues
- **Data not updating**: Check Trustcall installation: `pip show trustcall`
- **Wrong fields**: Review conversation history and disambiguation rules in `nodes.py`

See **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** for detailed troubleshooting.

## 🚢 Production Deployment

### Backend
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend
```bash
cd frontend
npm run build
# Serve dist/ with nginx or similar
```

### Security Checklist
- [ ] Configure CORS to specific origins
- [ ] Use HTTPS/WSS in production
- [ ] Secure `.env` with Azure Key Vault or similar
- [ ] Add rate limiting to WebSocket endpoint
- [ ] Implement authentication (JWT/session)
- [ ] Enable logging and monitoring

## 📊 Performance

- **Latency**: ~100-300ms end-to-end (voice to response)
- **Throughput**: Supports multiple concurrent users
- **Audio**: 24kHz PCM16 for optimal quality/latency balance
- **LangGraph**: Checkpointer for conversation continuity

## 🤝 Contributing

This is an internal Intact Specialty Insurance project. For questions or issues, contact the development team.

## 📄 License

Copyright © 2025 Intact Specialty Insurance. All rights reserved.

## 🙏 Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - AI workflow orchestration
- [LangChain](https://github.com/langchain-ai/langchain) - LLM framework
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) - Voice and chat models
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [React](https://react.dev/) - Frontend framework
- [Trustcall](https://github.com/parlance-labs/trustcall) - Structured extraction

## 📞 Support

For issues or questions:
1. Check **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** for detailed documentation
2. Review logs in backend terminal
3. Check browser console for frontend errors
4. Contact the development team

---

**Version**: 1.0.0  
**Last Updated**: October 2025
