# Notera - AI Conversational Form Builder

**Create AI voice agents that collect information through natural conversation. No code required.**

Build intake agents for **any industry** in minutes - legal, healthcare, real estate, recruiting, and more. Your users speak naturally; the AI extracts structured data in real-time.

## Why Notera?

| Traditional Forms | Notera Voice Agents |
|-------------------|---------------------|
| Users abandon long forms | Natural conversation feels effortless |
| Cold, impersonal experience | Warm, branded voice interactions |
| Manual data entry errors | AI extracts data accurately |
| Requires developers to modify | No-code builder, anyone can create |

### Cost Transparency

Notera uses OpenAI APIs with transparent per-conversation pricing:

| Component | Cost | Per Conversation (avg 3 min) |
|-----------|------|------------------------------|
| Speech-to-Text (Whisper) | $0.006/min | ~$0.018 |
| LLM (GPT-4o) | ~$0.01/1K tokens | ~$0.03 |
| Text-to-Speech | $0.015/1K chars | ~$0.03 |
| **Total** | | **~$0.08 - $0.15** |

*Compare to: $15-50 per human-handled intake call*

## Features

- **No-Code Builder**: 4-step wizard to create voice agents
- **7 Industry Templates**: Legal, Healthcare, Real Estate, Home Services, Recruiting, Financial, Insurance
- **Voice-First Design**: Natural speech with text fallback
- **Real-Time Extraction**: [trustcall](https://github.com/hinthornw/trustcall) with RFC-6902 JSON patches for efficient data extraction
- **Customizable Personality**: Agent name, tone, greeting, and voice
- **Drag-and-Drop Fields**: Define exactly what data to collect
- **Multi-Language**: English, Spanish, French support
- **Cost Tracking**: Real-time usage monitoring

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/nicholascpark/Claims-Handler-Agent-v1.git
cd Claims-Handler-Agent-v1

# Copy environment file and add your OpenAI key
cp .env.example .env
# Edit .env: OPENAI_API_KEY=sk-your-key

# Start with Docker Compose
docker-compose up --build
```

Open http://localhost:3000 and start building your first agent!

### Option 2: Local Development

**Prerequisites**: Python 3.10+, Node.js 18+, OpenAI API Key

```bash
# Clone and setup
git clone https://github.com/nicholascpark/Claims-Handler-Agent-v1.git
cd Claims-Handler-Agent-v1

# Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd web && npm install && cd ..

# Configure
cp .env.example .env
# Edit .env: OPENAI_API_KEY=sk-your-key

# Run backend (terminal 1)
python run.py

# Run frontend (terminal 2)
cd web && npm run dev
```

Backend: http://localhost:8000 | Frontend: http://localhost:5173

## How It Works

### 1. Choose a Template or Start Fresh
Select from 7 industry templates with pre-configured fields, or build from scratch.

### 2. Customize Your Agent
- **Business Profile**: Company name, industry, contact info
- **Agent Personality**: Name, tone (professional/friendly/empathetic), voice
- **Custom Fields**: Add, remove, reorder the data you want to collect

### 3. Test & Deploy
Preview your agent, test conversations, then deploy to your website or phone system.

## Architecture

```
                                    ┌─────────────────────────────────────┐
                                    │         Notera Platform             │
┌──────────────┐                    │  ┌─────────────────────────────┐   │
│   End User   │◀──── Voice ────────│──│      Voice Agent            │   │
│  (Customer)  │                    │  │  - Dynamic prompts          │   │
└──────────────┘                    │  │  - trustcall extraction     │   │
                                    │  │  - Real-time updates        │   │
┌──────────────┐                    │  └─────────────────────────────┘   │
│   Builder    │◀── No-Code UI ─────│──┌─────────────────────────────┐   │
│   (Admin)    │                    │  │      Form Builder           │   │
└──────────────┘                    │  │  - Template selection       │   │
                                    │  │  - Drag-drop fields         │   │
                                    │  │  - Agent customization      │   │
                                    │  └─────────────────────────────┘   │
                                    └─────────────────────────────────────┘
                                                     │
                                                     ▼
                                    ┌─────────────────────────────────────┐
                                    │           OpenAI APIs               │
                                    │  Whisper (STT) │ GPT-4o │ TTS      │
                                    └─────────────────────────────────────┘
```

## API Endpoints

### Form Configuration
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/forms` | GET | List all form configurations |
| `/api/forms` | POST | Create new form configuration |
| `/api/forms/{id}` | GET | Get form by ID |
| `/api/forms/{id}` | PUT | Update form configuration |
| `/api/forms/{id}` | DELETE | Delete form |
| `/api/forms/templates` | GET | Get industry templates |
| `/api/forms/meta/field-types` | GET | Available field types |
| `/api/forms/meta/industries` | GET | Supported industries |

### Settings & Cost
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/settings/api-key` | POST | Set OpenAI API key |
| `/api/settings/api-key/test` | POST | Test API key validity |
| `/api/settings/api-key/status` | GET | Check if key is configured |
| `/api/settings/cost-estimate` | POST | Estimate conversation cost |
| `/api/settings/pricing` | GET | Current pricing info |

### Conversation
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/start` | POST | Start new conversation |
| `/api/chat/message` | POST | Send text message |
| `/api/chat/voice` | POST | Send voice message |
| `/api/chat/{thread_id}/payload` | GET | Get extracted data |
| `/api/chat/{thread_id}/history` | GET | Get conversation history |

## Project Structure

```
Claims-Handler-Agent-v1/
├── app/                          # Backend (FastAPI)
│   ├── api/
│   │   ├── main.py              # App factory
│   │   └── routes/
│   │       ├── chat.py          # Conversation endpoints
│   │       ├── forms.py         # Form CRUD
│   │       ├── settings.py      # API key & cost
│   │       └── health.py        # Health checks
│   ├── agents/
│   │   ├── dynamic_agent.py     # Config-driven agent
│   │   ├── prompt_generator.py  # Dynamic prompt generation
│   │   └── schema_generator.py  # Dynamic Pydantic schemas
│   ├── models/
│   │   ├── form_config.py       # Form configuration models
│   │   └── templates.py         # Industry templates
│   └── services/
│       ├── cost_tracker.py      # Usage & cost tracking
│       ├── llm/                 # OpenAI LLM service
│       ├── voice/               # STT/TTS services
│       └── persistence/         # Database
├── web/                          # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Landing.tsx      # Homepage
│   │   │   ├── Builder.tsx      # 4-step wizard
│   │   │   └── Test.tsx         # Test conversations
│   │   ├── components/builder/  # Builder components
│   │   ├── stores/              # Zustand state
│   │   └── api/                 # API client
│   ├── Dockerfile               # Frontend container
│   └── nginx.conf               # Production nginx
├── docker-compose.yml           # One-command startup
├── Dockerfile                   # Backend container
├── requirements.txt             # Python deps
└── .env.example                 # Environment template
```

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, LangGraph, [trustcall](https://github.com/hinthornw/trustcall)
- **Frontend**: React 18, TypeScript, Tailwind CSS, Zustand, dnd-kit
- **AI**: OpenAI GPT-4o, Whisper, TTS
- **Infrastructure**: Docker, nginx

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-your-openai-api-key

# Optional
OPENAI_MODEL=gpt-4o              # LLM model
OPENAI_TEMPERATURE=0.7           # Response creativity
TTS_MODEL=tts-1                  # Text-to-speech model
TTS_VOICE=nova                   # Voice (alloy, echo, fable, onyx, nova, shimmer)
DEFAULT_LANGUAGE=en              # en, es, fr
HOST=0.0.0.0                     # Server host
PORT=8000                        # Server port
```

## Troubleshooting

**Docker issues?**
- Ensure Docker and Docker Compose are installed
- Check port availability (3000, 8000)
- Run `docker-compose logs` for error details

**API key errors?**
- Verify OPENAI_API_KEY is set correctly in .env
- Ensure key has access to gpt-4o, whisper-1, tts-1
- Check API credits/billing

**Microphone not working?**
- Allow browser microphone permissions
- Use HTTPS in production (required for mic access)
- Check browser console for errors

## License

MIT License

---

Built with [LangGraph](https://github.com/langchain-ai/langgraph), [trustcall](https://github.com/hinthornw/trustcall), [OpenAI](https://openai.com), and [FastAPI](https://fastapi.tiangolo.com).
