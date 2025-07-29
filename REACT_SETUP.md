# IntactBot FNOL Agent - React.js Setup Guide

This guide will help you set up and run the new React.js frontend with the FastAPI backend for the IntactBot FNOL Agent.

## 🎯 What's New

The voice recording feature has been completely rewritten in React.js with the following enhancements:

### ✅ Fixed Issues
- **Button Visual Feedback**: Resume/Pause and Stop & Send buttons now show proper active/clickable states
- **Recording Indicators**: Red blinking indicator during recording with visual animations
- **Auto-Start Recording**: Automatic recording after AI completes speech with countdown
- **Sound Wave Visualization**: Real-time visualization during recording and static view when paused
- **Toggle Functionality**: Resume/Pause button properly toggles between states
- **Backend Integration**: Seamless connection with LangGraph agent via FastAPI

### 🆕 Enhanced Features
- **Modern UI**: Responsive design with styled-components
- **Real-time Updates**: Live payload updates as conversation progresses
- **Audio Playback**: Automatic AI response playback with controls
- **Error Handling**: Comprehensive error handling with user feedback
- **Health Monitoring**: Backend connection status and retry mechanisms

## 🚀 Quick Setup

### Step 1: Install Dependencies

First, install the backend dependencies:
```bash
# In the project root
pip install -r requirements.txt
```

Then, install the frontend dependencies:
```bash
# Navigate to frontend directory
cd frontend
npm install
```

### Step 2: Configure Environment

Create a `.env` file in the project root with your Azure OpenAI credentials:
```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_STT_DEPLOYMENT_NAME=whisper
AZURE_TTS_DEPLOYMENT_NAME=tts
AZURE_TTS_API_VERSION=2024-02-15-preview
TTS_VOICE_MODEL=tts-1

# Optional: Database configuration
DATABASE_URL=sqlite:///./fnol_agent.db
```

### Step 3: Start the Backend

In the project root, start the FastAPI backend:
```bash
python backend.py
```

The backend will start on `http://localhost:8000` and you should see:
```
🚀 Starting IntactBot FNOL Agent Backend...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 4: Start the Frontend

In a new terminal, navigate to the frontend directory and start the React app:
```bash
cd frontend
npm start
```

The frontend will start on `http://localhost:3000` and automatically open in your browser.

## 🎤 Voice Recording Features

### Smart Controls
1. **Resume/Pause Button**: 
   - Green when ready to start/resume
   - Yellow when paused
   - Proper hover effects and animations

2. **Stop & Send Button**:
   - Gray when disabled
   - Red when active (recording or paused)
   - Shows "Sending..." state during processing

### Visual Feedback
1. **Status Dot**: 
   - Gray: Idle
   - Red with pulse animation: Recording
   - Yellow with slow blink: Paused

2. **Sound Wave Visualization**:
   - Real-time bars during recording
   - Static bars when paused (for review)
   - Smooth animations and color transitions

3. **Auto-Start Notification**:
   - Countdown timer before auto-recording begins
   - Can be cancelled by manual interaction

### Recording Flow
1. AI completes speech and audio finishes playing
2. 3-second countdown appears
3. Recording automatically starts (red blinking indicator)
4. User can pause to review (yellow indicator with static wave)
5. User can resume or stop & send
6. Audio is transcribed and processed by LangGraph agent

## 🔧 Advanced Configuration

### Frontend Environment Variables
Create `frontend/.env.local` for frontend-specific overrides:
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_DEBUG=true
```

### Backend Configuration
The FastAPI backend supports these additional environment variables:
```env
# Server Configuration
HOST=127.0.0.1
PORT=8000
RELOAD=true

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]

# Logging
LOG_LEVEL=info
```

## 📱 Browser Requirements

For optimal voice recording functionality:
- **Chrome 80+** (recommended)
- **Firefox 80+**
- **Safari 14+**
- **Edge 80+**

**Important**: Voice recording requires:
- HTTPS in production OR localhost in development
- Microphone permissions granted
- Modern browser with MediaRecorder API support

## 🐛 Troubleshooting

### Backend Issues

**"Backend service is not available"**
```bash
# Check if backend is running
curl http://localhost:8000/health

# If not running, start backend
python backend.py
```

**"Import errors"**
```bash
# Install missing dependencies
pip install -r requirements.txt

# Check Python version (requires 3.8+)
python --version
```

### Frontend Issues

**"npm install fails"**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**"Proxy errors to backend"**
```bash
# Verify backend is running on port 8000
# Check frontend/package.json proxy setting
```

### Voice Recording Issues

**"Microphone permission denied"**
1. Ensure you're on localhost or HTTPS
2. Check browser permissions (camera/microphone)
3. Reload the page after granting permissions

**"No audio visualization"**
1. Check browser console for errors
2. Verify microphone is working in other apps
3. Try a different browser

**"Recording not starting automatically"**
1. Ensure audio is playing and finishes
2. Check for JavaScript errors in console
3. Verify microphone permissions are granted

## 🔄 Migration from Gradio

If you were using the previous Gradio UI:

1. **Stop the old UI**: Close any running Gradio instances
2. **Backup data**: Export any important conversation data
3. **Follow setup**: Use this guide to set up the new React interface
4. **Test functionality**: Verify all features work in the new interface

The new React interface provides all the functionality of the Gradio version with significant improvements in user experience and voice recording capabilities.

## 📊 API Endpoints

The FastAPI backend provides these endpoints:

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /api/chat/start` - Start conversation
- `POST /api/chat/message` - Send text message  
- `POST /api/chat/voice` - Send voice message
- `GET /api/chat/audio/{thread_id}` - Get audio response
- `DELETE /api/chat/{thread_id}` - Reset conversation
- `GET /api/chat/{thread_id}/payload` - Get current payload

You can view the interactive API documentation at `http://localhost:8000/docs` when the backend is running.

## 🎉 Success!

If everything is set up correctly, you should see:

1. **Backend**: Running on port 8000 with health check passing
2. **Frontend**: React app on port 3000 with IntactBot interface
3. **Voice Recording**: Working with proper visual feedback
4. **Integration**: Seamless communication between frontend and backend

You now have a modern, fast, and feature-rich React.js interface for the IntactBot FNOL Agent with enhanced voice recording capabilities!

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review browser console for errors
3. Verify all dependencies are installed
4. Ensure environment variables are configured correctly

The new React interface provides a significant improvement in performance, user experience, and voice recording functionality compared to the previous Gradio implementation. 