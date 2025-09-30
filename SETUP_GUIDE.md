# FNOL Voice Agent - Setup Guide

Complete setup guide for the First Notice of Loss (FNOL) Voice Agent application with WebSocket-based conversational AI.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + Tailwind)               │
│  - Real-time chat display                                    │
│  - JSON payload visualization                                │
│  - Audio streaming via WebSocket                             │
└───────────────────────────┬─────────────────────────────────┘
                            │ WebSocket
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  - WebSocket handler                                         │
│  - Session management                                        │
│  - Integration with voice_langgraph                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 voice_langgraph Agent                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Voice Input → Extraction → Supervisor → Response   │   │
│  └─────────────────────────────────────────────────────┘   │
│  - LangGraph workflow orchestration                         │
│  - Trustcall JSON extraction                                │
│  - OpenAI Realtime API integration                          │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Required
- Python 3.11+
- Node.js 18+ and npm
- Azure OpenAI account with:
  - GPT-4 (chat) deployment
  - GPT-4o Realtime Preview deployment
- Microphone access (for voice input)

### Optional
- Docker (for containerized deployment)
- Git (for version control)

## Quick Start

### 1. Clone/Navigate to Repository

```bash
cd Claims-Handler-Agent-v1
```

### 2. Configure Azure OpenAI Credentials

Create a `.env` file in the **project root**:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_CHAT_API_VERSION=2024-08-01-preview
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_REALTIME_API_VERSION=2024-10-01-preview
AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME=gpt-4o-realtime-preview

# Company Branding
COMPANY_NAME=Intact Specialty Insurance
COMPANY_DEPARTMENT=Claims Department
AGENT_NAME=IntactBot

# Voice Settings
JUNIOR_AGENT_VOICE=shimmer
SAMPLE_RATE=24000
AUDIO_CHANNELS=1
VAD_THRESHOLD=0.5
VAD_PREFIX_PADDING_MS=300
VAD_SILENCE_DURATION_MS=500

# Transcription
TRANSCRIPTION_MODEL=whisper-1
TRANSCRIPTION_LANGUAGE=en
```

### 3. Start Backend (Terminal 1)

**Windows:**
```bash
cd backend
start.bat
```

**Linux/Mac:**
```bash
cd backend
chmod +x start.sh
./start.sh
```

**Manual:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

Backend will start on **http://localhost:8000**

### 4. Start Frontend (Terminal 2)

**Windows:**
```bash
cd frontend
start.bat
```

**Linux/Mac:**
```bash
cd frontend
chmod +x start.sh
./start.sh
```

**Manual:**
```bash
cd frontend
npm install
npm run dev
```

Frontend will start on **http://localhost:3000**

### 5. Open Application

Navigate to **http://localhost:3000** in your browser (Chrome recommended)

## Detailed Setup Instructions

### Backend Setup

#### 1. Install Dependencies

The backend requires Python packages including:
- FastAPI (web framework)
- LangGraph (agent orchestration)
- Trustcall (JSON extraction)
- WebSockets (real-time communication)
- Azure OpenAI SDK

```bash
cd backend
pip install -r requirements.txt
```

#### 2. Configure Environment

The backend reads configuration from the `.env` file in the **project root** (not in the backend directory).

Key settings:
- **AZURE_OPENAI_ENDPOINT**: Your Azure OpenAI resource URL
- **AZURE_OPENAI_API_KEY**: Authentication key
- **AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME**: Realtime model deployment
- **AZURE_OPENAI_CHAT_DEPLOYMENT_NAME**: Chat model for supervisor

#### 3. Test Backend

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-09-30T12:00:00",
  "services": {
    "langgraph": "available",
    "voice_settings": "configured"
  }
}
```

### Frontend Setup

#### 1. Install Dependencies

The frontend uses:
- React 18 (UI framework)
- Vite (build tool)
- Tailwind CSS (styling)
- WebSocket API (communication)
- Web Audio API (audio processing)

```bash
cd frontend
npm install
```

#### 2. Copy Logo

Ensure `intactbot_logo.png` is in `frontend/public/`:

```bash
cp ../frontend/intactbot_logo.png ./public/
# or
cp ../UI/intactbot_logo.png ./public/
```

#### 3. Configure WebSocket URL (Optional)

Create `frontend/.env`:

```bash
VITE_WS_URL=ws://localhost:8000/ws/voice
```

#### 4. Build for Production

```bash
npm run build
# Output in dist/ directory

# Preview production build
npm run preview
```

## Usage

### Starting a Voice Session

1. Open http://localhost:3000
2. Click **"Call Agent"** button
3. Allow microphone access when prompted
4. Speak with the agent
5. Watch chat history and JSON payload update in real-time

### UI Features

#### Chat History (Left Panel)
- Shows conversation transcript
- User messages in gray bubbles (right-aligned)
- Agent messages in dark bubbles (left-aligned)
- Auto-scrolls to latest message
- Timestamps for each message

#### JSON Payload (Right Panel)
- Live claim data object
- Syntax-highlighted JSON
- Progress bar showing completion percentage
- Green checkmark when claim is complete
- Collapsible for audio-focused interaction

#### Controls
- **Call Agent Button**: Start/stop voice session (red when inactive, gray when active)
- **Hide Chat Button**: Toggle chat visibility (audio is primary modality)
- **Status Indicator**: Connection and session status

### Hiding Chat Interface

Click **"Hide Chat"** to focus on audio interaction only. The JSON payload will expand to full width.

## Troubleshooting

### Backend Issues

#### "Module not found" errors
```bash
# Ensure you're in the backend directory
cd backend

# Ensure voice_langgraph is accessible
cd ..
ls voice_langgraph/  # Should show .py files

# Check Python path
python -c "import sys; print(sys.path)"
```

#### "Settings validation failed"
```bash
# Check .env file exists in project root
ls ../.env

# Verify required environment variables
python -c "from voice_langgraph.settings import voice_settings; print(voice_settings.AZURE_OPENAI_ENDPOINT)"
```

#### WebSocket connection refused
```bash
# Verify backend is running
curl http://localhost:8000/

# Check firewall settings
# Ensure port 8000 is not blocked
```

### Frontend Issues

#### "Failed to fetch audio worklets"
```bash
# Ensure worklet files exist
ls public/audio-*.js

# Should show:
# audio-playback-worklet.js
# audio-processor-worklet.js
```

#### WebSocket connection failed
- Ensure backend is running on port 8000
- Check browser console for errors
- Verify CORS settings in backend

#### Microphone not working
- Check browser permissions (chrome://settings/content/microphone)
- Ensure HTTPS or localhost (microphone requires secure context)
- Try different browser (Chrome recommended)

#### Audio not playing
- Check system audio output settings
- Ensure browser has audio permissions
- Click page to resume AudioContext (user interaction required)

### Common Issues

#### Port already in use
```bash
# Backend (port 8000)
# Windows: netstat -ano | findstr :8000
# Linux/Mac: lsof -i :8000

# Frontend (port 3000)  
# Windows: netstat -ano | findstr :3000
# Linux/Mac: lsof -i :3000
```

#### SSL/Certificate errors
Some corporate networks may have SSL interception. This is handled in the backend WebSocket connection.

## Development

### Backend Development

#### Run with auto-reload
```bash
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

#### Enable debug logging
```python
# In server.py, change:
logging.basicConfig(level=logging.DEBUG)
```

#### Test WebSocket manually
```bash
pip install websockets
python -m websockets ws://localhost:8000/ws/voice
```

### Frontend Development

#### Component development
Components are in `src/components/`:
- `Header.jsx` - Top navigation bar
- `CallAgentButton.jsx` - Main action button
- `ChatHistory.jsx` - Conversation display
- `JsonPayloadDisplay.jsx` - Claim data viewer
- `StatusIndicator.jsx` - Connection status

#### Styling with Tailwind
```bash
# Tailwind config in tailwind.config.js
# Custom colors:
# - intact-red: #E31937
# - intact-dark-red: #B01429
```

#### Hot reload
Vite provides instant hot module replacement. Changes to React components will update immediately.

## Docker Deployment

### Build Images

```bash
# Backend
cd backend
docker build -t fnol-backend .

# Frontend (create Dockerfile)
cd frontend
docker build -t fnol-frontend .
```

### Run with Docker Compose

Create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
    env_file:
      - .env

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      - VITE_WS_URL=ws://localhost:8000/ws/voice
```

```bash
docker-compose up
```

## Production Deployment

### Backend Production

```bash
cd backend

# Using Gunicorn with Uvicorn workers
pip install gunicorn
gunicorn server:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Frontend Production

```bash
cd frontend

# Build optimized production bundle
npm run build

# Serve with any static file server
npx serve -s dist -p 3000

# Or use nginx, Apache, etc.
```

### Environment Variables for Production

- Set proper CORS origins in backend
- Use environment-specific `.env` files
- Enable HTTPS for production
- Configure proper WebSocket URL

## Testing

### Backend Testing

```bash
cd backend

# Test health endpoint
curl http://localhost:8000/health

# Test WebSocket (requires websockets package)
python -c "
import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://localhost:8000/ws/voice') as ws:
        msg = await ws.recv()
        print(json.loads(msg))

asyncio.run(test())
"
```

### Frontend Testing

```bash
cd frontend

# Run linter
npm run lint

# Build test
npm run build

# Preview build
npm run preview
```

## Performance Optimization

### Backend
- Use multiple Gunicorn workers for production
- Enable WebSocket compression
- Implement connection pooling
- Add Redis for session persistence (optional)

### Frontend
- Lazy load components
- Optimize bundle size with code splitting
- Use production build for deployment
- Enable gzip compression on server

## Security Considerations

### Backend
- Validate all WebSocket messages
- Implement rate limiting
- Use proper CORS configuration
- Secure API keys in environment variables
- Enable HTTPS in production

### Frontend
- Sanitize user inputs
- Use secure WebSocket (wss://) in production
- Implement CSP headers
- Validate audio data

## Monitoring and Logging

### Backend Logs
- WebSocket connection events
- LangGraph workflow execution
- Claim data updates
- Errors and exceptions

### Frontend Logs
- Browser console for debugging
- WebSocket connection status
- Audio stream errors
- React component errors

## Support

For issues or questions:
1. Check this setup guide
2. Review README files in backend/ and frontend/
3. Check voice_langgraph/ documentation
4. Review browser console and backend logs

## License

Same as parent project (Intact Financial Corporation)

---

**Last Updated**: September 30, 2025  
**Version**: 1.0.0
