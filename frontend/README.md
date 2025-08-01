# IntactBot FNOL Frontend (React.js)

A modern React.js frontend for the IntactBot First Notice of Loss (FNOL) processing agent with advanced voice recording capabilities and real-time backend integration.

## 🎯 Features

### Enhanced Voice Recording
- **Smart Auto-Start**: Automatically begins recording after AI completes speech
- **Visual Feedback**: Real-time sound wave visualization during recording
- **Button States**: Proper visual feedback for Resume/Pause and Stop & Send buttons
- **Recording Indicators**: Red blinking indicator during active recording
- **Pause & Review**: Ability to pause recording and review audio with visualization
- **Toggle Controls**: Resume/Pause button toggles between recording and pausing states

### Real-time Integration
- **FastAPI Backend**: Seamless communication with LangGraph agent
- **Live Updates**: Real-time payload updates as conversation progresses
- **Audio Responses**: Automatic playback of AI speech synthesis
- **Health Monitoring**: Backend connection status and retry mechanisms

### Modern UI/UX
- **Responsive Design**: Works on desktop and mobile devices
- **Accessibility**: ARIA labels and keyboard navigation support
- **Toast Notifications**: User-friendly feedback for all actions
- **Loading States**: Clear indicators during processing

## 🚀 Quick Start

### Prerequisites
- Node.js 16+ and npm/yarn
- Python 3.8+ (for backend)
- Backend server running (see backend setup below)

### Installation

1. **Install frontend dependencies:**
```bash
cd frontend
npm install
```

2. **Start the development server:**
```bash
npm start
```

The frontend will be available at `http://localhost:3000` and will proxy API requests to the backend at `http://localhost:8000`.

## 🔧 Backend Setup

The React frontend requires the FastAPI backend to be running. Follow these steps:

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up environment variables:**
Create a `.env` file in the project root with your Azure OpenAI credentials:
```env
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_STT_DEPLOYMENT_NAME=whisper
AZURE_TTS_DEPLOYMENT_NAME=tts
AZURE_TTS_API_VERSION=2024-02-15-preview
TTS_VOICE_MODEL=tts-1
```

3. **Start the FastAPI backend:**
```bash
python backend.py
```

The backend will be available at `http://localhost:8000`.

## 📁 Project Structure

```
frontend/
├── public/
│   └── index.html              # Main HTML template
├── src/
│   ├── components/
│   │   ├── AudioPlayer.js      # AI audio response player
│   │   ├── ChatInterface.js    # Main chat interface
│   │   ├── ChatMessage.js      # Individual message component
│   │   ├── Header.js           # Application header
│   │   ├── LoadingSpinner.js   # Loading indicator
│   │   ├── PayloadDisplay.js   # Real-time claim data display
│   │   ├── SoundWaveVisualizer.js # Audio visualization
│   │   ├── StartScreen.js      # Welcome/start screen
│   │   └── VoiceRecording.js   # Enhanced voice recording
│   ├── hooks/
│   │   └── useAudioRecording.js # Audio recording logic
│   ├── services/
│   │   └── api.js              # Backend API integration
│   ├── App.js                  # Main application component
│   ├── index.js                # React entry point
│   └── index.css               # Global styles
├── package.json                # Dependencies and scripts
└── README.md                   # This file
```

## 🎤 Voice Recording Features

### Smart Recording Controls
- **Resume/Pause Button**: Toggles between start/resume and pause states
- **Stop & Send Button**: Stops recording and sends to backend for processing
- **Visual States**: Different colors and animations for each state
- **Auto-Start**: Countdown timer before auto-recording begins

### Real-time Visualization
- **Sound Wave Bars**: 8-bar audio level visualization
- **Recording Animation**: Animated bars during active recording
- **Paused State**: Static bars showing last recorded levels for review
- **Color Coding**: Red for recording, yellow for paused, gray for idle

### Audio Processing
- **High Quality**: 44.1kHz sample rate with noise suppression
- **Web Standards**: Uses MediaRecorder API with opus codec
- **Base64 Encoding**: Seamless transfer to backend
- **Real-time Analysis**: Audio level detection for visualization

## 🔗 API Integration

The frontend communicates with the FastAPI backend through these endpoints:

- `POST /api/chat/start` - Initialize conversation
- `POST /api/chat/message` - Send text message
- `POST /api/chat/voice` - Send voice message
- `GET /api/chat/audio/{thread_id}` - Get audio response
- `DELETE /api/chat/{thread_id}` - Reset conversation
- `GET /health` - Backend health check

## 🎨 Styling & Theming

The application uses styled-components for:
- **Component Isolation**: Scoped styles for each component
- **Dynamic Styling**: Props-based style changes
- **Animations**: Keyframe animations for visual feedback
- **Responsive Design**: Mobile-first responsive layouts
- **Theme Consistency**: Intact Financial Corporation branding

## 🔒 Security Features

- **CORS Configuration**: Properly configured for frontend-backend communication
- **Input Validation**: Client-side validation before API calls
- **Error Handling**: Graceful error handling with user feedback
- **Audio Permissions**: Proper microphone permission handling

## 🛠️ Development

### Available Scripts

- `npm start` - Start development server
- `npm build` - Build for production
- `npm test` - Run test suite
- `npm run eject` - Eject from Create React App

### Environment Variables

Create `.env.local` in the frontend directory for development overrides:
```env
REACT_APP_API_URL=http://localhost:8000
```

## 📱 Browser Support

- Chrome 80+ (recommended for voice features)
- Firefox 80+
- Safari 14+
- Edge 80+

**Note**: Voice recording requires HTTPS in production or localhost in development.

## 🚀 Deployment

### Production Build
```bash
npm run build
```

### Docker Deployment
```dockerfile
FROM node:16-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 🐛 Troubleshooting

### Common Issues

1. **Microphone Permission Denied**
   - Ensure HTTPS or localhost
   - Check browser permissions
   - Reload page after granting permission

2. **Backend Connection Failed**
   - Verify backend is running on port 8000
   - Check CORS configuration
   - Ensure environment variables are set

3. **Audio Playback Issues**
   - Check browser audio permissions
   - Verify audio codec support
   - Test with different browsers

### Debug Mode
Set `REACT_APP_DEBUG=true` in `.env.local` for additional logging.

## 📄 License

This project is part of the IntactBot FNOL Agent system.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

For questions or support, please contact the development team. 