# Quick Start Guide - Claims Handler Voice Agent

## 🚀 Get Running in 5 Minutes

### Step 1: Configure Azure Credentials (2 min)

```bash
# Copy environment template
cp .env.example .env
```

Edit `.env` and add your Azure OpenAI credentials:
```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME=gpt-4o-realtime-preview
```

### Step 2: Start Everything (1 min)

**Option A - Automatic (Recommended)**

Linux/Mac:
```bash
chmod +x start_fullstack.sh
./start_fullstack.sh
```

Windows:
```bash
start_fullstack.bat
```

**Option B - Manual**

Terminal 1 (Backend):
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate       # Linux/Mac
# OR
venv\Scripts\activate.bat      # Windows

# Install dependencies
pip install -r requirements.txt

# Start server
python main.py
```

Terminal 2 (Frontend):
```bash
cd frontend
npm install
npm run dev
```

### Step 3: Use the Application (2 min)

1. Open browser to: http://localhost:5173
2. Click "Allow" when prompted for microphone
3. Select your microphone from dropdown
4. Click "Start Call"
5. Wait for greeting: "Hi there, I'm Kismet AI..."
6. Start speaking!

## 🎤 Example Conversation

**Agent**: "Hi there, I'm Kismet AI with the Claims Department at Intact Specialty Insurance. I'm here to help with your property insurance claim. To get started, could you tell me your full name?"

**You**: "My name is John Smith"

**Agent**: "Thank you John. What's the best phone number to reach you?"

**You**: "555-123-4567"

**Agent**: "Got it. Do you have your policy number handy?"

**You**: "Yes, it's POL-123456"

... continue providing information as prompted ...

## 📋 What Information You'll Need

The agent will ask for:
1. ✅ Full name
2. ✅ Phone number  
3. ✅ Policy number (optional)
4. ✅ Date and time of incident
5. ✅ Address where incident occurred
6. ✅ Zip code
7. ✅ Description of what happened
8. ✅ Personal injuries (if any)
9. ✅ Property damage details

## 🔍 Monitoring Progress

**Watch the UI**:
- **Left panel**: Live chat transcript
- **Right panel**: JSON showing collected data
- **Top status**: Current agent state
- **Completion indicator**: Shows when ready to submit

**In the JSON panel**, you'll see fields populate:
```json
{
  "claimant": {
    "insured_name": "John Smith",
    "insured_phone": "555-123-4567",
    "policy_number": "POL-123456"
  },
  "incident": {
    "incident_date": "2025-10-01",
    "incident_time": "14:30",
    ...
  }
}
```

## 🎯 Tips for Best Experience

### Speaking with the Agent
- ✅ Speak naturally and conversationally
- ✅ You can provide multiple pieces of info at once
- ✅ It's okay to say "I don't know" for optional fields
- ❌ Don't speak while the agent is talking (wait for "Ready" status)

### Technical Tips
- ✅ Use Chrome or Edge (best Web Audio API support)
- ✅ Use a headset to avoid echo/feedback
- ✅ Check that your mic level is good (not too quiet/loud)
- ✅ Stable internet connection recommended

### If Something Goes Wrong
- 🔄 Refresh the page
- 🔄 Try a different microphone
- 🔄 Check browser console (F12) for errors
- 🔄 Restart backend/frontend

## 🛠️ Common Issues

### "ModuleNotFoundError: No module named 'fastapi'"
➡️ **Solution**: Virtual environment not activated

**Quick fix**:
```bash
cd backend
./start.sh       # Linux/Mac
start.bat        # Windows
```

**Or manually**:
```bash
cd backend
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate.bat      # Windows
python main.py
```

### "Could not connect to server"
➡️ **Solution**: Make sure backend is running on port 8000
```bash
curl http://localhost:8000/health
```

### "Microphone access denied"
➡️ **Solution**: Grant permission in browser settings
- Chrome: chrome://settings/content/microphone
- Firefox: about:preferences#privacy

### "No audio from agent"
➡️ **Solution**: Click anywhere on the page to resume audio
- Browsers require user interaction before playing audio

### "Fields not updating"
➡️ **Solution**: Check backend logs for extraction errors
```bash
# In backend terminal, look for:
[EXTRACTION] ✅ Trustcall completed extraction/merge
```

### "Agent not responding"
➡️ **Solution**: Check Azure OpenAI service status and credentials

## 📊 Endpoints for Testing

### Health Check
```bash
curl http://localhost:8000/health
```
Expected: `{"status": "healthy", "active_sessions": 0}`

### WebSocket Test
```bash
npm install -g wscat
wscat -c ws://localhost:8000/ws/voice
> {"type": "start_session"}
```

### API Documentation
Open: http://localhost:8000/docs

## 🎓 Learn More

- **[README.md](README.md)** - Full project overview
- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - Architecture deep-dive
- **[backend/README.md](backend/README.md)** - API specification
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - What was built

## 🆘 Still Having Issues?

1. Check all services are running:
   - Backend: http://localhost:8000
   - Frontend: http://localhost:5173

2. Verify `.env` file has correct credentials

3. Check browser console (F12) for JavaScript errors

4. Check backend terminal for Python errors

5. Try the standalone console agent:
   ```bash
   python run_voice_agent.py
   ```

6. Review logs with debug mode:
   ```python
   # In backend/main.py
   logging.basicConfig(level=logging.DEBUG)
   ```

## ✅ Success Checklist

When everything is working, you should see:

- [ ] Backend shows: "Running on http://localhost:8000"
- [ ] Frontend shows: "Local: http://localhost:5173"
- [ ] Browser loads the UI without errors
- [ ] Microphone dropdown shows your devices
- [ ] "Start Call" button is clickable
- [ ] Agent greets you after clicking start
- [ ] Chat messages appear as you speak
- [ ] JSON panel updates with your information
- [ ] You hear the agent's responses

If all checked ✅ - You're ready to go! 🎉

---

**Need Help?** Review the detailed guides or contact the development team.

