# FNOL Voice Agent - Quick Start

Get up and running in 5 minutes!

## ⚡ Fast Setup

### Step 1: Configure Azure OpenAI (2 min)

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
# Required: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY
nano .env  # or use any text editor
```

**Minimum required in .env:**
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME=gpt-4o-realtime-preview
```

### Step 2: Start Application (2 min)

**Option A: One Command (Recommended)**

```bash
# Windows
start_all.bat

# Linux/Mac
chmod +x start_all.sh
./start_all.sh
```

This opens two terminal windows - one for backend, one for frontend.

**Option B: Manual (Two Terminals)**

Terminal 1 - Backend:
```bash
cd backend
./start.sh        # Linux/Mac
# or
start.bat         # Windows
```

Terminal 2 - Frontend:
```bash
cd frontend
./start.sh        # Linux/Mac
# or
start.bat         # Windows
```

### Step 3: Use the Application (1 min)

1. Open **http://localhost:3000** in Chrome
2. Click **"Call Agent"** button (big red button)
3. Allow microphone access when prompted
4. Start speaking!

## 🎯 First Test Conversation

Try this simple conversation:

**You:** "Hello"

**Agent:** *Greets you and asks for your name*

**You:** "My name is [Your Name]"

**Agent:** *Acknowledges and asks what happened*

**You:** "I had a car accident yesterday at 2 PM on Main Street. My rear bumper was hit."

**Agent:** *Asks for more details*

Watch as:
- 💬 Chat history populates with transcription
- 📋 JSON payload fills with extracted data
- 📊 Progress bar increases

## 🎨 UI Overview

```
┌─────────────────────────────────────────────────────────┐
│  [Logo] FNOL Voice Agent        Intact Specialty Ins.   │ ← Header
├─────────────────────────────────────────────────────────┤
│  ● Connected - Ready          [Hide Chat]               │ ← Status
│                                                          │
│              [🎙️ Call Agent]                            │ ← Big Red Button
│                                                          │
├──────────────────────┬──────────────────────────────────┤
│  Chat History        │  Claim Data Payload             │
│  ┌────────────────┐ │  ┌────────────────────────────┐ │
│  │ 👤 User: Hi    │ │  │ {                          │ │
│  │ 🤖 Agent: Hello│ │  │   "claimant": {            │ │
│  │ 👤 User: John  │ │  │     "insured_name": "John" │ │
│  │                │ │  │   },                       │ │
│  │                │ │  │   "incident": {},          │ │
│  │                │ │  │   "property_damage": {}    │ │
│  │                │ │  │ }                          │ │
│  └────────────────┘ │  └────────────────────────────┘ │
│                      │  Progress: ████░░░░ 40%         │
└──────────────────────┴──────────────────────────────────┘
│  © 2025 Intact Specialty Insurance                     │ ← Footer
└─────────────────────────────────────────────────────────┘
```

## 🎤 Voice Interaction Tips

### Do's ✅
- Speak clearly and at normal pace
- Wait for agent to finish before responding
- Provide specific details (dates, times, locations)
- Answer questions directly

### Don'ts ❌
- Don't interrupt the agent mid-sentence
- Don't speak too quietly or too loudly
- Don't provide vague information ("somewhere", "sometime")
- Don't try to upload photos (voice only!)

## 🔧 Troubleshooting

### Problem: Can't hear the agent

**Solution:**
1. Check system volume
2. Check browser audio permissions
3. Click anywhere on page (activates AudioContext)
4. Try refreshing the page

### Problem: Agent can't hear me

**Solution:**
1. Check microphone permissions in browser
2. Select correct microphone in system settings
3. Check if microphone is muted
4. Try different browser (Chrome recommended)

### Problem: WebSocket won't connect

**Solution:**
1. Verify backend is running (`http://localhost:8000/health`)
2. Check browser console for errors (F12)
3. Restart both backend and frontend
4. Check firewall settings

### Problem: JSON not updating

**Solution:**
1. Check backend logs for errors
2. Verify Azure OpenAI credentials in .env
3. Ensure conversation includes extraction keywords
4. Check browser console for WebSocket messages

## 📚 Next Steps

Once you have it working:

1. **Review Documentation**
   - `SETUP_GUIDE.md` - Detailed setup
   - `TESTING_GUIDE.md` - Test scenarios
   - `backend/README.md` - Backend details
   - `frontend/README.md` - Frontend details

2. **Explore Features**
   - Try different claim types (auto, home, commercial)
   - Test error recovery (disconnect during call)
   - Hide chat interface (audio-only mode)
   - Watch JSON payload build

3. **Customize**
   - Adjust company branding in .env
   - Modify UI colors in `tailwind.config.js`
   - Tune VAD settings for your environment
   - Add custom extraction keywords

4. **Production Deployment**
   - Review `DEPLOYMENT_PRODUCTION.md`
   - Set up monitoring
   - Configure SSL/HTTPS
   - Enable rate limiting

## 🆘 Getting Help

If you encounter issues:

1. Check error messages in:
   - Browser console (F12)
   - Backend terminal
   - Frontend terminal

2. Review documentation:
   - This guide
   - SETUP_GUIDE.md
   - Component README files

3. Check configuration:
   - .env file exists and has correct values
   - Ports 8000 and 3000 are available
   - Azure OpenAI deployments are accessible

4. Verify prerequisites:
   - Python 3.11+
   - Node.js 18+
   - Microphone enabled
   - Chrome browser (or compatible)

## 🎉 Success Indicators

You'll know it's working when:

- ✅ Backend shows "Starting server on http://localhost:8000"
- ✅ Frontend shows "Local: http://localhost:3000"
- ✅ Browser shows IntactBot logo
- ✅ Status indicator is green "Connected - Ready"
- ✅ Clicking "Call Agent" prompts for microphone
- ✅ Speaking shows transcription in chat
- ✅ JSON payload updates with your information
- ✅ Agent responds with natural voice

## 🚀 Advanced Usage

### Docker Deployment

```bash
# One command to rule them all
docker-compose up -d

# Access application
open http://localhost:3000
```

### Custom Configuration

```bash
# Backend: Edit voice_langgraph/settings.py
# Frontend: Edit tailwind.config.js for colors
# Environment: Edit .env for behavior
```

### Development Mode

```bash
# Backend with auto-reload
cd backend
uvicorn server:app --reload

# Frontend with hot reload (already default)
cd frontend
npm run dev
```

---

**Need Help?** See SETUP_GUIDE.md for detailed troubleshooting.

**Ready for Production?** See DEPLOYMENT_PRODUCTION.md for deployment guide.

---

*Happy claim processing! 🎉*
