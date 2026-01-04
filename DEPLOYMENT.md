# Deployment Guide

## Local Development

### Prerequisites
- Python 3.10+
- Node.js 18+
- OpenAI API Key

### Quick Start

```bash
# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
python run.py

# Frontend (new terminal)
cd web
npm install
npm run dev
```

## Production Deployment

### Option 1: Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Node.js for frontend build
RUN apt-get update && apt-get install -y nodejs npm

# Backend dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend build
COPY web/package*.json ./web/
RUN cd web && npm ci

COPY web/ ./web/
RUN cd web && npm run build

# Backend code
COPY app/ ./app/
COPY run.py .

# Serve frontend from FastAPI
ENV STATIC_FILES_DIR=/app/web/dist

EXPOSE 8000

CMD ["python", "run.py"]
```

### Option 2: Render

Create `render.yaml`:

```yaml
services:
  - type: web
    name: kismet-voice-agent
    env: python
    buildCommand: |
      pip install -r requirements.txt
      cd web && npm ci && npm run build
    startCommand: python run.py
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: PORT
        value: 8000
```

### Option 3: Railway

```bash
# railway.json
{
  "build": {
    "builder": "nixpacks"
  },
  "deploy": {
    "startCommand": "python run.py"
  }
}
```

Set environment variables in Railway dashboard:
- `OPENAI_API_KEY`
- `PORT=8000`

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o` | LLM model |
| `OPENAI_TEMPERATURE` | No | `0.7` | Response creativity |
| `STT_MODEL` | No | `whisper-1` | Speech-to-text model |
| `TTS_MODEL` | No | `tts-1` | Text-to-speech model |
| `TTS_VOICE` | No | `nova` | TTS voice |
| `DEFAULT_LANGUAGE` | No | `en` | Default language |
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8000` | Server port |

## Health Checks

```bash
# Check API health
curl http://localhost:8000/api/health

# Response
{"status": "healthy", "version": "1.0.0"}
```

## Scaling Considerations

1. **Session Storage**: Current implementation uses in-memory storage. For production, configure Redis or PostgreSQL.

2. **Rate Limiting**: Add rate limiting middleware for production.

3. **CORS**: Configure `CORS_ORIGINS` for your domains.

4. **SSL**: Use a reverse proxy (nginx, Caddy) for HTTPS.

## Monitoring

Recommended monitoring setup:
- Application logs via stdout
- OpenAI API usage via OpenAI dashboard
- Error tracking via Sentry (optional)
