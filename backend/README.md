# FNOL Voice Agent Backend

FastAPI backend server that integrates the voice_langgraph agent for First Notice of Loss (FNOL) claim intake.

## Features

- **Real-time Voice Communication**: WebSocket integration with OpenAI Realtime API
- **Live Chat History**: Streams conversation messages to frontend in real-time
- **Dynamic JSON Payload**: Updates claim data as conversation progresses
- **LangGraph Integration**: Uses the modular voice_langgraph workflow
- **Error Handling**: Comprehensive error recovery and logging

## Architecture

```
Frontend (React) 
    ↓ WebSocket (/ws/voice)
Backend FastAPI Server
    ↓ WebSocket (Azure OpenAI Realtime API)
OpenAI Realtime API
    ↓ Transcription
LangGraph Workflow
    ├── Voice Input Node
    ├── Extraction Worker (Trustcall)
    ├── Supervisor Node
    └── Response Generation
```

## Installation

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Azure OpenAI credentials
```

### 3. Run Server

```bash
python server.py
```

Server will start on `http://localhost:8000`

## API Endpoints

### WebSocket

- `ws://localhost:8000/ws/voice` - Main voice agent WebSocket

### HTTP

- `GET /` - Health check
- `GET /health` - Detailed health status
- `GET /api/session/{session_id}` - Session data (debugging)

## WebSocket Protocol

### Client → Server Messages

```json
{
  "type": "start_session"
}
```

```json
{
  "type": "audio_data",
  "audio": "base64_encoded_pcm16_audio"
}
```

```json
{
  "type": "stop_session"
}
```

### Server → Client Messages

```json
{
  "type": "connected",
  "data": {
    "session_id": "20250930_123456_789",
    "message": "Connected to FNOL Voice Agent"
  }
}
```

```json
{
  "type": "chat_message",
  "data": {
    "role": "user | assistant",
    "content": "Message text",
    "timestamp": "12:34:56"
  }
}
```

```json
{
  "type": "claim_data_update",
  "data": {
    "claim_data": { /* PropertyClaim object */ },
    "is_complete": false
  }
}
```

```json
{
  "type": "audio_delta",
  "data": {
    "audio": "base64_encoded_pcm16_audio"
  }
}
```

```json
{
  "type": "agent_ready",
  "data": {
    "message": "Agent is listening"
  }
}
```

```json
{
  "type": "claim_complete",
  "data": {
    "claim_data": { /* Complete PropertyClaim */ },
    "submission_result": {
      "claim_id": "CLM-20250930-ABC123",
      "status": "submitted",
      "next_steps": "A claims adjuster will contact you within 24-48 hours."
    }
  }
}
```

```json
{
  "type": "error",
  "data": {
    "message": "Error description"
  }
}
```

## Configuration

All configuration is managed through environment variables (`.env` file).

### Required Settings

- `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI resource endpoint
- `AZURE_OPENAI_API_KEY` - API key for authentication
- `AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME` - Realtime model deployment name
- `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` - Chat model deployment name

### Optional Settings

- `COMPANY_NAME` - Company name for branding (default: "Intact Specialty Insurance")
- `AGENT_NAME` - Agent name (default: "IntactBot")
- `JUNIOR_AGENT_VOICE` - Voice selection (default: "shimmer")

## Development

### Running in Development Mode

```bash
# With auto-reload
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Test WebSocket connection
python -m websockets ws://localhost:8000/ws/voice
```

## Production Deployment

### Using Gunicorn

```bash
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker

```bash
docker build -t fnol-backend .
docker run -p 8000:8000 --env-file .env fnol-backend
```

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Verify Azure OpenAI endpoint and API key
   - Check firewall/network settings
   - Ensure deployment names are correct

2. **Audio Not Working**
   - Check audio format is PCM16 at 24kHz
   - Verify base64 encoding/decoding

3. **Claim Data Not Updating**
   - Check LangGraph workflow execution logs
   - Verify Trustcall extraction is working
   - Review conversation history

### Debug Logging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## License

Same as parent project
