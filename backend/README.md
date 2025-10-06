# Claims Handler Voice Agent Backend

This backend server integrates the `voice_langgraph` agent with a WebSocket API for real-time voice communication with the frontend.

## Architecture

```
Frontend (React)
    ↓ WebSocket
Backend (FastAPI)
    ↓ Integration
voice_langgraph (LangGraph Agent)
    ↓ WebSocket
Azure OpenAI Realtime API
```

## Features

- **Real-time Voice Communication**: WebSocket-based bidirectional audio streaming
- **LangGraph Integration**: Full integration with voice_langgraph workflow
- **Session Management**: Multi-user session handling with isolated state
- **Claim Data Tracking**: Real-time claim data updates sent to frontend
- **Azure OpenAI Realtime API**: Native integration for low-latency voice

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your Azure OpenAI credentials:

```bash
cp .env.example .env
```

Required environment variables:
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI resource endpoint
- `AZURE_OPENAI_API_KEY`: Your API key
- `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME`: Deployment name for GPT-4 (e.g., "gpt-4o")
- `AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME`: Deployment name for Realtime API (e.g., "gpt-4o-realtime-preview")

### 3. Start the Server

**Important**: Always activate the virtual environment first!

**Option A - Use the startup script (Recommended)**:

```bash
# Linux/Mac
./start.sh

# Windows
start.bat
```

**Option B - Manual start**:

Linux/Mac:
```bash
# Activate venv first!
source venv/bin/activate

# Then start server
python main.py
```

Windows:
```bash
# Activate venv first!
venv\Scripts\activate.bat

# Then start server
python main.py
```

**Option C - Uvicorn directly**:
```bash
# After activating venv
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on `http://localhost:8000`.

> ⚠️ **Common Error**: If you see `ModuleNotFoundError: No module named 'fastapi'`, you forgot to activate the virtual environment. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for solutions.

## API Endpoints

### HTTP Endpoints

- `GET /`: Health check
- `GET /health`: Detailed health status with active session count

### WebSocket Endpoint

- `WS /ws/voice`: Main voice agent WebSocket connection

## WebSocket Protocol

### Client → Server Messages

1. **Start Session**
```json
{
  "type": "start_session"
}
```

2. **Stop Session**
```json
{
  "type": "stop_session"
}
```

3. **Audio Data** (PCM16, base64-encoded)
```json
{
  "type": "audio_data",
  "audio": "base64_encoded_pcm16_audio"
}
```

4. **Text Input** (optional, for testing)
```json
{
  "type": "text_input",
  "text": "My name is John Doe"
}
```

### Server → Client Messages

1. **Connected**
```json
{
  "type": "connected",
  "data": {
    "session_id": "uuid",
    "timestamp": "2025-10-03T12:00:00"
  }
}
```

2. **Chat Message**
```json
{
  "type": "chat_message",
  "data": {
    "role": "user" | "assistant",
    "content": "message text",
    "timestamp": "12:00:00"
  }
}
```

3. **Audio Delta** (PCM16, base64-encoded)
```json
{
  "type": "audio_delta",
  "data": {
    "audio": "base64_encoded_pcm16_audio"
  }
}
```

4. **Claim Data Update**
```json
{
  "type": "claim_data_update",
  "data": {
    "claim_data": { /* PropertyClaim object */ },
    "is_complete": false
  }
}
```

5. **User Speech Events**
```json
{
  "type": "user_speech_started" | "user_speech_stopped",
  "data": {}
}
```

6. **Agent Ready**
```json
{
  "type": "agent_ready",
  "data": {}
}
```

7. **Claim Complete**
```json
{
  "type": "claim_complete",
  "data": {
    "claim_data": { /* complete PropertyClaim */ },
    "submission_result": {
      "claim_id": "CLM-20251003-ABC123",
      "status": "submitted",
      "message": "Claim successfully submitted"
    }
  }
}
```

8. **Error**
```json
{
  "type": "error",
  "data": {
    "message": "Error description"
  }
}
```

## Integration with voice_langgraph

The backend uses the `voice_langgraph` module directly:

- **Graph**: Uses `default_graph` from `voice_langgraph.graph_builder`
- **Schema**: Uses `PropertyClaim` from `voice_langgraph.schema`
- **Settings**: Uses `voice_settings` from `voice_langgraph.settings`
- **Utils**: Uses audio utilities from `voice_langgraph.utils`

Each session maintains its own:
- Conversation history
- Claim data state
- LangGraph thread_id for conversation continuity

## Development

### Running in Development Mode

```bash
# With auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

Test the WebSocket connection:

```bash
# Using wscat
npm install -g wscat
wscat -c ws://localhost:8000/ws/voice
```

Then send:
```json
{"type": "start_session"}
```

## Production Deployment

For production deployment:

1. Set appropriate CORS origins in `main.py`
2. Use a production ASGI server (uvicorn with workers)
3. Configure SSL/TLS termination
4. Set up monitoring and logging
5. Configure environment variables securely

Example production start:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --log-config logging.conf
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure the parent directory (containing `voice_langgraph`) is accessible
2. **Azure API errors**: Verify your credentials and deployment names in `.env`
3. **WebSocket disconnects**: Check network stability and increase timeout settings
4. **Audio issues**: Verify PCM16 format (24kHz, mono, 16-bit) on both ends

### Logging

The backend uses Python's logging module. Adjust log level in `main.py`:

```python
logging.basicConfig(level=logging.DEBUG)  # For verbose logging
```

## License

Copyright © 2025 Intact Specialty Insurance. All rights reserved.

