# FNOL Voice Agent Frontend

React + Tailwind CSS frontend for the First Notice of Loss (FNOL) voice agent application.

## Features

- **Real-time Voice Communication**: WebSocket-based audio streaming
- **Live Chat History**: See conversation transcript as it happens
- **Dynamic JSON Payload**: Watch claim data build in real-time
- **Minimalistic Design**: Clean white/gray/black/red color scheme
- **Responsive Layout**: Works on desktop and mobile devices
- **Audio-First Interface**: Chat display is optional, audio is primary
- **Progress Tracking**: Visual indicators for claim completion

## Design

### Color Scheme
- Primary: White (#FFFFFF)
- Secondary: Gray shades (#F5F5F5, #9CA3AF, #18181B)
- Accent: Intact Red (#E31937, #B01429)
- Text: Black (#18181B)

### Layout
- **Header**: IntactBot logo (top-left), company branding (top-right)
- **Main Area**: 
  - Left: Chat History (collapsible)
  - Right: JSON Payload Display
- **Controls**: Call Agent button (prominent, centered)
- **Footer**: Company information

## Installation

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Create a `.env` file (optional):

```bash
VITE_WS_URL=ws://localhost:8000/ws/voice
```

### 3. Run Development Server

```bash
npm run dev
```

Frontend will start on `http://localhost:3000`

## Build for Production

```bash
npm run build
```

Built files will be in the `dist` directory.

## Project Structure

```
frontend/
├── public/
│   ├── intactbot_logo.png
│   ├── audio-processor-worklet.js
│   └── audio-playback-worklet.js
├── src/
│   ├── components/
│   │   ├── Header.jsx
│   │   ├── CallAgentButton.jsx
│   │   ├── ChatHistory.jsx
│   │   ├── JsonPayloadDisplay.jsx
│   │   └── StatusIndicator.jsx
│   ├── hooks/
│   │   └── useVoiceAgent.js
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── index.html
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── package.json
```

## Components

### Header
- Displays IntactBot logo and company branding
- Responsive design with mobile optimization

### CallAgentButton
- Prominent button to start/stop voice session
- Visual feedback for session state
- Smooth transitions and hover effects

### ChatHistory
- Real-time conversation transcript
- Auto-scrolls to newest messages
- User/Assistant message differentiation
- Timestamps for each message

### JsonPayloadDisplay
- Live JSON object display
- Syntax-highlighted JSON
- Completion progress bar
- Collapsible for focus on audio interaction

### StatusIndicator
- Connection status (connected/disconnected)
- Session status (active/inactive)
- Visual indicators with color-coded dots

## WebSocket Integration

The frontend connects to the backend via WebSocket and handles:

1. **Audio Streaming**: Bidirectional PCM16 audio at 24kHz
2. **Chat Updates**: Real-time message transcription
3. **Claim Data Updates**: Live JSON payload updates
4. **Error Handling**: Connection errors and recovery

### Audio Worklets

- **audio-processor-worklet.js**: Processes microphone input to PCM16
- **audio-playback-worklet.js**: Plays received audio from agent

## Browser Compatibility

- Chrome 90+ (recommended)
- Edge 90+
- Safari 14+
- Firefox 88+

**Note**: WebSocket and Web Audio API support required.

## Development

### Hot Reload

Vite provides instant hot module replacement during development.

### Linting

```bash
npm run lint
```

### Preview Production Build

```bash
npm run preview
```

## Troubleshooting

### Microphone Not Working
1. Check browser permissions
2. Ensure HTTPS (or localhost)
3. Verify audio worklets loaded correctly

### WebSocket Connection Failed
1. Ensure backend is running on port 8000
2. Check VITE_WS_URL environment variable
3. Verify CORS settings on backend

### Audio Not Playing
1. Check browser audio permissions
2. Ensure AudioContext is resumed (user interaction required)
3. Verify audio format (PCM16, 24kHz)

## License

Same as parent project
