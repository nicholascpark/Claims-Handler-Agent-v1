# Claims Handler Voice Agent - Integration Guide

This document explains the complete architecture and integration between the voice_langgraph agent, backend server, and frontend application.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  • UI Components (Chat, JSON Display, Status)                   │
│  • Audio Worklets (Capture & Playback)                          │
│  • WebSocket Client (useVoiceAgent hook)                        │
└────────────────────┬────────────────────────────────────────────┘
                     │ WebSocket (/ws/voice)
┌────────────────────┴────────────────────────────────────────────┐
│                    Backend (FastAPI)                             │
│  • WebSocket Server (main.py)                                   │
│  • Session Manager (session_manager.py)                         │
│  • Multi-user session handling                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │ Python Integration
┌────────────────────┴────────────────────────────────────────────┐
│                 voice_langgraph Module                           │
│  • LangGraph Workflow (graph_builder.py)                        │
│  • Nodes (supervisor, extraction, tools)                        │
│  • PropertyClaim Schema                                          │
└────────────────────┬────────────────────────────────────────────┘
                     │ WebSocket
┌────────────────────┴────────────────────────────────────────────┐
│              Azure OpenAI Realtime API                           │
│  • Voice Activity Detection (VAD)                                │
│  • Speech-to-Text (Transcription)                               │
│  • Text-to-Speech (Audio Generation)                            │
└─────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. Frontend (React)

**Location**: `./frontend/`

**Key Files**:
- `src/App.jsx` - Main application component
- `src/hooks/useVoiceAgent.js` - WebSocket and audio management
- `src/components/` - UI components

**Responsibilities**:
- Display UI (chat history, claim data, status)
- Capture microphone audio via Web Audio API
- Send audio to backend as base64-encoded PCM16
- Receive and play audio from backend
- Handle WebSocket connection lifecycle

**Audio Flow**:
```
Microphone → MediaStream → AudioWorklet → base64 PCM16 → WebSocket → Backend
Backend → WebSocket → base64 PCM16 → AudioWorklet → Speakers
```

### 2. Backend (FastAPI)

**Location**: `./backend/`

**Key Files**:
- `main.py` - FastAPI server with WebSocket endpoint
- `session_manager.py` - Session and VoiceSession classes

**Responsibilities**:
- Accept WebSocket connections from frontend
- Create isolated sessions for each user
- Forward audio to Azure Realtime API
- Run LangGraph workflow for each user message
- Broadcast state updates to frontend (claim data, messages)

**Session Lifecycle**:
1. Client connects → `create_session()` → unique session_id
2. Client sends `start_session` → Initialize Realtime API connection
3. Audio/text exchange → Process through LangGraph
4. Client sends `stop_session` or disconnects → Cleanup

### 3. voice_langgraph Module

**Location**: `./voice_langgraph/`

**Key Files**:
- `graph_builder.py` - Constructs LangGraph workflow
- `nodes.py` - Workflow nodes (supervisor, extraction, tools)
- `schema.py` - PropertyClaim Pydantic schema
- `state.py` - VoiceAgentState TypedDict
- `edges.py` - Routing logic between nodes
- `tools.py` - LangChain tools (submit_claim_payload, get_human_contact)
- `prompts.py` - System prompts
- `settings.py` - Configuration
- `utils.py` - Audio and WebSocket utilities

**LangGraph Workflow**:
```
voice_input → extraction_worker → supervisor → tools (optional) → END
                    ↓                  ↓
              error_handler       error_handler
```

**Node Responsibilities**:
- `voice_input`: Process incoming user message, set context
- `extraction_worker`: Use Trustcall to extract claim data
- `supervisor`: Generate natural language response, decide when to call tools
- `tools`: Execute tool calls (submit claim, get human contact)
- `error_handler`: Provide graceful error recovery

### 4. Azure OpenAI Realtime API

**Connection**: Backend connects via WebSocket (wss://)

**Features Used**:
- Server VAD (Voice Activity Detection)
- Input audio transcription (Whisper)
- Output audio synthesis (TTS)
- Conversation management

**Event Flow**:
```
Backend → input_audio_buffer.append → Realtime API
Realtime API → conversation.item.created (transcript) → Backend
Backend → conversation.item.create + response.create → Realtime API
Realtime API → response.audio.delta (audio chunks) → Backend
```

## Protocol Specification

### Frontend → Backend Messages

| Message Type | Payload | Description |
|-------------|---------|-------------|
| `start_session` | None | Initialize voice session |
| `stop_session` | None | End voice session |
| `audio_data` | `{audio: base64}` | PCM16 audio chunk (24kHz, mono) |
| `text_input` | `{text: string}` | Text message (optional) |

### Backend → Frontend Messages

| Message Type | Payload | Description |
|-------------|---------|-------------|
| `connected` | `{session_id, timestamp}` | Session established |
| `chat_message` | `{role, content, timestamp}` | User/assistant message |
| `claim_data_update` | `{claim_data, is_complete}` | Claim data state |
| `audio_delta` | `{audio: base64}` | PCM16 audio chunk from agent |
| `user_speech_started` | None | User began speaking |
| `user_speech_stopped` | None | User stopped speaking |
| `agent_ready` | None | Agent finished speaking |
| `claim_complete` | `{claim_data, submission_result}` | Claim submitted |
| `error` | `{message: string}` | Error occurred |

## Data Flow Example

### User says: "My name is John Doe"

1. **Frontend**: 
   - Captures audio → base64 PCM16
   - Sends `audio_data` message

2. **Backend**:
   - Receives audio → Forwards to Realtime API
   - Realtime API transcribes → "My name is John Doe"
   - Sends `chat_message` to frontend (user message)

3. **LangGraph**:
   - `voice_input` node receives transcript
   - `extraction_worker` node uses Trustcall:
     - Extracts: `claimant.insured_name = "John Doe"`
   - `supervisor` node generates response:
     - "Thank you John. What's your phone number?"
   - Backend sends `claim_data_update` to frontend

4. **Realtime API**:
   - Receives assistant text from backend
   - Generates audio (TTS)
   - Streams audio chunks to backend

5. **Backend**:
   - Receives audio chunks
   - Forwards as `audio_delta` to frontend
   - Sends `chat_message` (assistant transcript)

6. **Frontend**:
   - Receives `audio_delta` → Plays through speakers
   - Receives `chat_message` → Updates chat UI
   - Receives `claim_data_update` → Updates JSON display

## Configuration

### Environment Variables

Both backend and voice_langgraph share configuration via `.env`:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key

# Deployments
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME=gpt-4o-realtime-preview

# Server
PORT=8000
HOST=0.0.0.0

# Agent
AGENT_NAME=Kismet AI
COMPANY_NAME=Intact Specialty Insurance
```

### Frontend Configuration

Edit `frontend/src/hooks/useVoiceAgent.js`:

```javascript
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/voice'
```

Or set in `frontend/.env`:
```env
VITE_WS_URL=ws://localhost:8000/ws/voice
```

## Running the Complete Stack

### 1. Setup Environment

```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env with your Azure credentials
```

### 2. Start Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py
```

Backend runs on `http://localhost:8000`

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`

### 4. Test Connection

1. Open frontend in browser
2. Select microphone
3. Click "Start Call"
4. Wait for agent greeting
5. Speak naturally to provide claim information

## Development Tips

### Backend Debugging

Enable verbose logging in `backend/main.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Frontend Debugging

Check browser console for:
- WebSocket connection status
- Audio worklet messages
- Claim data updates

### LangGraph Visualization

Generate workflow diagram:
```bash
python see_graph.py
```

### Testing Without Frontend

Use the standalone voice agent:
```bash
python run_voice_agent.py
```

## Troubleshooting

### Audio Not Working

**Problem**: No audio playback or capture

**Solutions**:
1. Check browser permissions (microphone/audio)
2. Ensure audio context is resumed (click anywhere on page)
3. Verify PCM16 format (24kHz, mono, 16-bit)
4. Check audio worklet files in `frontend/public/`

### WebSocket Disconnects

**Problem**: Frequent disconnections

**Solutions**:
1. Check network stability
2. Increase heartbeat interval in `session_manager.py`
3. Verify Azure OpenAI service health
4. Check backend logs for errors

### Extraction Not Working

**Problem**: Claim data not updating

**Solutions**:
1. Verify Trustcall installation: `pip show trustcall`
2. Check extraction node logs in backend
3. Ensure PropertyClaim schema is correct
4. Review conversation history in logs

### Claim Not Submitting

**Problem**: Claim marked complete but not submitted

**Solutions**:
1. Check `is_complete()` method in `schema.py`
2. Verify all required fields are collected
3. Review supervisor node logic in `nodes.py`
4. Check tool execution in LangGraph

## Security Considerations

### Production Deployment

1. **CORS**: Configure allowed origins in `backend/main.py`
   ```python
   allow_origins=["https://your-domain.com"]
   ```

2. **API Keys**: Use secure secret management
   - Azure Key Vault
   - Environment variables (never commit)

3. **SSL/TLS**: Use HTTPS and WSS (not WS)
   ```javascript
   const WS_URL = 'wss://your-domain.com/ws/voice'
   ```

4. **Rate Limiting**: Add to FastAPI
   ```python
   from slowapi import Limiter
   ```

5. **Authentication**: Add JWT or session-based auth

## Performance Optimization

### Backend

- Use multiple uvicorn workers
- Enable connection pooling for Azure API
- Cache LangGraph compiled graph
- Use async/await throughout

### Frontend

- Lazy load components
- Optimize audio buffer sizes
- Use Web Workers for audio processing
- Implement message batching

## License

Copyright © 2025 Intact Specialty Insurance. All rights reserved.


