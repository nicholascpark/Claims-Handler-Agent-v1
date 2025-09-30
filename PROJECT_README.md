# FNOL Voice Agent - Complete Application

A production-ready First Notice of Loss (FNOL) application with real-time voice interaction, powered by Azure OpenAI Realtime API and LangGraph.

## 🎯 Overview

This application provides an intelligent voice agent for insurance claim intake with:

- **Real-time Voice Conversation**: Full-duplex audio communication via OpenAI Realtime API
- **Live Chat Transcript**: See what you and the agent are saying in real-time
- **Dynamic JSON Payload**: Watch claim data build as the conversation progresses
- **Intelligent Extraction**: LangGraph + Trustcall for accurate data extraction
- **Professional UI**: Clean, minimalistic design in Intact brand colors

## 🏗️ Architecture

### Technology Stack

**Backend:**
- Python 3.11+ with FastAPI
- LangGraph for agent workflow orchestration
- Trustcall for JSON extraction
- WebSocket for real-time communication
- Azure OpenAI (Chat + Realtime API)

**Frontend:**
- React 18 with Hooks
- Vite (build tool)
- Tailwind CSS (styling)
- Web Audio API (audio processing)
- WebSocket client

### Directory Structure

```
Claims-Handler-Agent-v1/
├── backend/                    # FastAPI WebSocket server
│   ├── server.py              # Main server application
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile             # Backend container
│   ├── start.sh / start.bat   # Startup scripts
│   └── README.md              # Backend documentation
│
├── frontend/                   # React application
│   ├── src/
│   │   ├── components/        # UI components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── App.jsx            # Main application
│   │   └── main.jsx           # Entry point
│   ├── public/                # Static assets
│   │   ├── intactbot_logo.png
│   │   └── audio-*.js         # Audio worklets
│   ├── package.json           # Node dependencies
│   ├── Dockerfile             # Frontend container
│   ├── start.sh / start.bat   # Startup scripts
│   └── README.md              # Frontend documentation
│
├── voice_langgraph/           # Core agent logic (existing)
│   ├── voice_agent.py         # Voice agent implementation
│   ├── graph_builder.py       # LangGraph workflow
│   ├── nodes.py               # Agent nodes
│   ├── schema.py              # Data schemas
│   ├── tools.py               # Agent tools
│   └── ...                    # Other modules
│
├── docker-compose.yml         # Docker orchestration
├── SETUP_GUIDE.md             # Detailed setup instructions
└── README.md                  # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Azure OpenAI account with Realtime API access
- Microphone-enabled device

### 1. Configure Azure OpenAI

Create `.env` in project root:

```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME=gpt-4o-realtime-preview
AZURE_OPENAI_CHAT_API_VERSION=2024-08-01-preview
AZURE_OPENAI_REALTIME_API_VERSION=2024-10-01-preview
```

### 2. Start Backend (Terminal 1)

```bash
cd backend
./start.sh         # Linux/Mac
# or
start.bat          # Windows
```

Backend runs on **http://localhost:8000**

### 3. Start Frontend (Terminal 2)

```bash
cd frontend
./start.sh         # Linux/Mac
# or  
start.bat          # Windows
```

Frontend runs on **http://localhost:3000**

### 4. Use the Application

1. Open http://localhost:3000
2. Click **"Call Agent"**
3. Allow microphone access
4. Start speaking with the agent
5. Watch chat history and claim data update in real-time

## 📋 Features

### Voice Interaction
- Full-duplex audio (speak and listen simultaneously)
- Server-side VAD (Voice Activity Detection)
- Natural conversation flow
- Low latency response

### Chat History
- Real-time transcription
- User and agent messages clearly differentiated
- Timestamps for each message
- Auto-scroll to latest message
- Collapsible for audio-focused mode

### JSON Payload Display
- Live updates as conversation progresses
- Structured claim data visualization
- Progress bar showing completion percentage
- Expandable/collapsible view
- Syntax-highlighted JSON

### Agent Intelligence
- **Voice Input Node**: Processes transcriptions
- **Extraction Worker**: Uses Trustcall for data extraction
- **Supervisor Node**: Orchestrates conversation flow
- **Response Generator**: Creates natural responses
- **Error Handler**: Graceful error recovery

## 🎨 UI Design

### Color Palette
- **Primary**: White (#FFFFFF) - Clean, professional background
- **Text**: Black (#18181B) - High contrast, readable
- **Secondary**: Gray (#F5F5F5, #9CA3AF) - Subtle borders and backgrounds
- **Accent**: Intact Red (#E31937) - Call-to-action and branding

### Layout Philosophy
- **Minimalistic**: No clutter, focus on essential information
- **Functional**: Every element serves a purpose
- **Responsive**: Works on desktop, tablet, and mobile
- **Accessible**: High contrast, clear typography

## 🔧 Configuration

### Backend Configuration

All settings via `.env` file:

```bash
# Required
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME=...
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=...

# Optional
COMPANY_NAME=Intact Specialty Insurance
AGENT_NAME=IntactBot
JUNIOR_AGENT_VOICE=shimmer
VAD_THRESHOLD=0.5
```

### Frontend Configuration

Optional `.env` in frontend directory:

```bash
VITE_WS_URL=ws://localhost:8000/ws/voice
```

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Start both services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Individual Containers

```bash
# Backend
cd backend
docker build -t fnol-backend .
docker run -p 8000:8000 --env-file ../.env fnol-backend

# Frontend
cd frontend
docker build -t fnol-frontend .
docker run -p 3000:80 fnol-frontend
```

## 📊 Data Flow

```
User speaks → Microphone
    ↓
Frontend captures audio (Web Audio API)
    ↓
WebSocket sends PCM16 audio to backend
    ↓
Backend forwards to Azure OpenAI Realtime API
    ↓
Realtime API transcribes speech
    ↓
Backend triggers LangGraph workflow
    ├── Voice Input Node (keyword detection)
    ├── Extraction Worker (Trustcall extraction)
    ├── Supervisor Node (orchestration)
    └── Response Generation
    ↓
Backend sends updates to frontend:
    ├── Chat message (transcript)
    ├── Claim data update (JSON)
    └── Audio response (agent speech)
    ↓
Frontend updates UI:
    ├── Chat History (new message)
    ├── JSON Payload (updated claim)
    └── Audio Playback (agent voice)
```

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Health check
curl http://localhost:8000/health

# WebSocket test
python -m websockets ws://localhost:8000/ws/voice
```

### Frontend Tests

```bash
cd frontend

# Lint
npm run lint

# Build
npm run build

# Preview
npm run preview
```

### End-to-End Test

1. Start both backend and frontend
2. Click "Call Agent" 
3. Say: "Hello, my name is John Smith"
4. Verify:
   - Chat shows transcription
   - JSON payload shows `claimant.insured_name: "John Smith"`
   - Agent responds appropriately

## 🔍 Monitoring

### Backend Logs
- Connection events
- Message flow
- LangGraph execution
- Error tracking

### Frontend Console
- WebSocket connection status
- Audio stream status
- Component render cycles
- Error messages

## 📈 Performance

### Backend
- Async/await for concurrent operations
- WebSocket for low-latency communication
- Efficient LangGraph workflow
- Minimal API calls via keyword detection

### Frontend
- React 18 with concurrent features
- Vite for fast builds and HMR
- Tailwind CSS (purged in production)
- Audio worklets for efficient processing

## 🔒 Security

### Backend
- Environment-based secrets
- CORS configuration
- Input validation
- Error sanitization

### Frontend
- Secure WebSocket (wss:// in production)
- Content Security Policy
- XSS protection
- Microphone permission handling

## 🚀 Production Checklist

- [ ] Configure production .env file
- [ ] Set proper CORS origins in backend
- [ ] Use HTTPS/WSS in production
- [ ] Enable frontend build optimization
- [ ] Set up monitoring/logging
- [ ] Configure firewall rules
- [ ] Test with production Azure OpenAI deployment
- [ ] Enable rate limiting
- [ ] Set up backup/disaster recovery
- [ ] Document API keys and secrets management

## 📚 Documentation

- **SETUP_GUIDE.md**: Detailed setup and troubleshooting
- **backend/README.md**: Backend API documentation
- **frontend/README.md**: Frontend component guide
- **voice_langgraph/README.md**: Agent workflow documentation

## 🤝 Contributing

This is an enterprise application for Intact Financial Corporation.

## 📄 License

Intact Financial Corporation - Internal Use Only

## 🆘 Support

For issues or questions:
1. Review SETUP_GUIDE.md for common issues
2. Check component-specific README files
3. Review logs (backend and browser console)
4. Contact development team

---

**Version**: 1.0.0  
**Last Updated**: September 30, 2025  
**Maintained by**: Intact Financial Corporation
