import gradio as gr
import json
import uuid
import sys
import os
import base64
from typing import Dict, Any, List, Tuple
import asyncio
from functools import lru_cache
import numpy as np
import soundfile as sf
from io import BytesIO

# Add the parent directory to the path to import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.builder import create_graph
from src.schema import example_json, FNOLPayload
from langchain_core.messages import SystemMessage, HumanMessage
from src.state import ConvoState
from src.voice import transcribe_audio_stream, synthesize_speech_stream

class IntactBotUI:
    def __init__(self):
        self.graph = create_graph()
        self.thread_id = str(uuid.uuid4())
        self.config = {"configurable": {"thread_id": self.thread_id}}
        self.current_payload = FNOLPayload(claim=example_json)
        self.is_form_complete = False
        
        # Initialize with empty state
        initial_human_message = HumanMessage(content=" ")
        self.initial_state: ConvoState = {
            "messages": [initial_human_message],
            "payload": self.current_payload,
            "is_form_complete": self.is_form_complete,
        }
        
        self.initial_chat_history = []
    
    async def start_fnol_process(self):
        """Get the initial AI message and TTS audio."""
        try:
            events = self.graph.astream(self.initial_state, self.config, stream_mode="values")
            
            async for event in events:
                if "messages" in event and event["messages"]:
                    last_message = event["messages"][-1]
                    if hasattr(last_message, 'content') and last_message.content.strip():
                        text_response = last_message.content
                        audio_bytes = await synthesize_speech_stream(text_response)
                        return [{"role": "assistant", "content": text_response}], audio_bytes
            
            # Fallback
            text_response = "Hello! I'm here to help you process your First Notice of Loss claim. Please share the details of your claim."
            audio_bytes = await synthesize_speech_stream(text_response)
            return [{"role": "assistant", "content": text_response}], audio_bytes
        except Exception as e:
            print(f"Error getting initial message: {e}")
            text_response = "Hello! I'm here to help you process your First Notice of Loss claim. Please share the details of your claim."
            audio_bytes = await synthesize_speech_stream(text_response)
            return [{"role": "assistant", "content": text_response}], audio_bytes
    
    async def process_voice_message(self, audio_data: bytes, history: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], str, bool, bytes]:
        """Process voice audio data and return updated chat history, payload, and form completion status"""
        if not audio_data:
            return history, self.format_payload(), self.is_form_complete, b""
        
        # Transcribe the audio
        user_input = await transcribe_audio_stream(audio_data)
        
        if not user_input.strip():
            return history, self.format_payload(), self.is_form_complete, b""
        
        # Add user message to history
        if history is None:
            history = []
        
        history.append({"role": "user", "content": f"🎤 *{user_input}*"})
        
        try:
            # Stream events from the graph
            events = self.graph.astream({"messages": [HumanMessage(content=user_input)]}, self.config, stream_mode="values")
            
            agent_response = ""
            async for event in events:
                # Extract agent response from messages
                if "messages" in event and event["messages"]:
                    last_message = event["messages"][-1]
                    if hasattr(last_message, 'content') and last_message.content != user_input:
                        agent_response = last_message.content
                
                # Update payload if changed
                if "payload" in event and event["payload"]:
                    self.current_payload = event["payload"]
                    self.initial_state["payload"] = self.current_payload
                
                # Update form complete status
                if "is_form_complete" in event:
                    self.is_form_complete = event["is_form_complete"]
            
            # Update history with agent response
            if agent_response:
                history.append({"role": "assistant", "content": agent_response})
                audio_response = await synthesize_speech_stream(agent_response)
            else:
                agent_response = "I'm processing your request..."
                history.append({"role": "assistant", "content": agent_response})
                audio_response = await synthesize_speech_stream(agent_response)
                
        except Exception as e:
            error_message = f"Error: {str(e)}"
            history.append({"role": "assistant", "content": error_message})
            audio_response = await synthesize_speech_stream(error_message)
        
        return history, self.format_payload(), self.is_form_complete, audio_response

    async def process_message(self, message: Dict, history: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], str, bool, bytes]:
        """Process user message (text or audio) and return updated chat history, payload, and form completion status"""
        user_input = ""
        is_audio = False

        if message["text"]:
            user_input = message["text"]
        elif message["files"]:
            audio_path = message["files"][0]
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            user_input = await transcribe_audio_stream(audio_data)
            is_audio = True

        if not user_input.strip():
            # Return empty audio if there's no input
            return history, self.format_payload(), self.is_form_complete, b""
        
        # Add user message to history
        if history is None:
            history = []
        
        if is_audio:
            history.append({"role": "user", "content": f"🎤 *{user_input}*"})
        else:
            history.append({"role": "user", "content": user_input})
        
        try:
            # Stream events from the graph
            events = self.graph.astream({"messages": [HumanMessage(content=user_input)]}, self.config, stream_mode="values")
            
            agent_response = ""
            async for event in events:
                # Extract agent response from messages
                if "messages" in event and event["messages"]:
                    last_message = event["messages"][-1]
                    if hasattr(last_message, 'content') and last_message.content != user_input:
                        agent_response = last_message.content
                
                # Update payload if changed
                if "payload" in event and event["payload"]:
                    self.current_payload = event["payload"]
                    self.initial_state["payload"] = self.current_payload
                
                # Update form complete status
                if "is_form_complete" in event:
                    self.is_form_complete = event["is_form_complete"]
            
            # Update history with agent response
            if agent_response:
                history.append({"role": "assistant", "content": agent_response})
                audio_response = await synthesize_speech_stream(agent_response)
            else:
                agent_response = "I'm processing your request..."
                history.append({"role": "assistant", "content": agent_response})
                audio_response = await synthesize_speech_stream(agent_response)
                
        except Exception as e:
            error_message = f"Error: {str(e)}"
            history.append({"role": "assistant", "content": error_message})
            audio_response = await synthesize_speech_stream(error_message)
        
        return history, self.format_payload(), self.is_form_complete, audio_response
    
    def format_payload(self) -> str:
        """Format the current payload for display"""
        try:
            if self.current_payload:
                payload_dict = self.current_payload.model_dump() if hasattr(self.current_payload, 'model_dump') else self.current_payload
                return json.dumps(payload_dict, indent=2, ensure_ascii=False)
            else:
                return "No payload data available"
        except Exception as e:
            return f"Error formatting payload: {str(e)}"
    
    def reset_conversation(self) -> Tuple[List[Dict[str, str]], str, bool, bytes]:
        """Reset the conversation and payload"""
        self.thread_id = str(uuid.uuid4())
        self.config = {"configurable": {"thread_id": self.thread_id}}
        self.current_payload = FNOLPayload(claim=example_json)
        self.is_form_complete = False
        
        initial_human_message = HumanMessage(content=" ")
        self.initial_state: ConvoState = {
            "messages": [initial_human_message],
            "payload": self.current_payload,
            "is_form_complete": self.is_form_complete,
        }
        
        return [], self.format_payload(), self.is_form_complete, b""

@lru_cache(maxsize=1)
def get_logo_data_uri():
    """Convert logo to base64 data URI with caching"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "intactbot_logo.png")
        
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode()
                return f"data:image/png;base64,{img_data}"
            return None
    except Exception as e:
        print(f"Error loading logo: {e}")
        return None

def create_ui():
    """Create and return the Gradio interface"""
    bot = IntactBotUI()
    logo_uri = get_logo_data_uri()
    
    # Enhanced CSS with voice recording controls
    custom_css = """
    .main-container {
        max-width: 1400px;
        margin: 0 auto;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .logo-container {
        display: flex;
        align-items: center;
        padding: 8px 20px;
        background: #f8f9fa;
        border-radius: 8px;
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
        position: relative;
    }
    .logo-left {
        position: absolute;
        left: 20px;
    }
    .logo-text {
        text-align: center;
        width: 100%;
    }
    .logo-container h1 {
        font-weight: 600;
        font-size: 2.07rem;
        color: #2c3e50;
        margin: 0;
    }
    .logo-container p {
        color: #666;
        font-size: 1.15rem;
        margin: 0;
    }
    .chat-container {
        height: 500px;
        border: 1px solid #ddd;
        border-radius: 8px;
    }
    .payload-container {
        height: 500px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 12px;
        border: 1px solid #ddd;
        border-radius: 8px;
    }
    .processing-indicator {
        color: #666;
        font-style: italic;
        font-size: 14px;
    }
    /* Red button styling for Intact branding */
    .send-button {
        background: #dc3545 !important;
        border: 1px solid #dc3545 !important;
        color: white !important;
        font-weight: 500 !important;
    }
    .send-button:hover {
        background: #c82333 !important;
        border-color: #c82333 !important;
    }
    /* Clean section headers */
    .section-header {
        color: #333;
        font-weight: 600;
        margin-bottom: 10px;
        padding: 8px 0;
        border-bottom: 2px solid #dc3545;
    }
    /* Payload status styling */
    .payload-complete {
        color: #28a745;
        font-weight: 600;
    }
    .payload-incomplete {
        color: #666;
        font-weight: 500;
    }
    /* Audio indicators */
    .audio-status {
        background: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 8px 12px;
        margin: 8px 0;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .audio-playing {
        color: #007bff;
        background: #e3f2fd;
        border-color: #007bff;
    }
    .audio-recording {
        color: #dc3545;
        background: #ffebee;
        border-color: #dc3545;
        animation: pulse 1.5s infinite;
    }
    .audio-paused {
        color: #ffc107;
        background: #fff8e1;
        border-color: #ffc107;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.3; }
    }
    .start-fnol-container {
        text-align: center;
        padding: 40px 20px;
        background: #f8f9fa;
        border-radius: 12px;
        margin: 20px 0;
        border: 2px solid #e0e0e0;
    }
    .start-fnol-container h2 {
        color: #2c3e50;
        margin-bottom: 16px;
        font-size: 1.8rem;
    }
    .start-fnol-container p {
        color: #666;
        margin-bottom: 24px;
        font-size: 1.1rem;
    }
    
    /* Enhanced Voice Recording Controls */
    .voice-controls {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 16px;
        margin: 12px 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* Voice Control Buttons - Enhanced styling */
    .voice-control-button {
        background: #dc3545;
        color: white;
        border: 2px solid #dc3545;
        border-radius: 8px;
        padding: 10px 18px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
        transition: all 0.3s ease;
        min-width: 100px;
        position: relative;
        overflow: hidden;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .voice-control-button:hover:not(:disabled) {
        background: #c82333;
        border-color: #c82333;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
    }
    
    .voice-control-button:active:not(:disabled) {
        transform: translateY(0);
        box-shadow: 0 2px 6px rgba(220, 53, 69, 0.2);
    }
    
    .voice-control-button:disabled {
        background: #6c757d !important;
        border-color: #6c757d !important;
        cursor: not-allowed;
        opacity: 0.6;
        transform: none !important;
        box-shadow: none !important;
    }
    
    /* Resume/Pause Button - Dual state styling */
    .voice-control-button.resume-pause {
        background: #28a745;
        border-color: #28a745;
        min-width: 120px;
    }
    
    .voice-control-button.resume-pause:hover:not(:disabled) {
        background: #218838;
        border-color: #218838;
        box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
    }
    
    .voice-control-button.resume-pause.paused {
        background: #ffc107;
        border-color: #ffc107;
        color: #000;
    }
    
    .voice-control-button.resume-pause.paused:hover:not(:disabled) {
        background: #e0a800;
        border-color: #e0a800;
        box-shadow: 0 4px 12px rgba(255, 193, 7, 0.3);
    }
    
    /* Stop Button */
    .voice-control-button.stop {
        background: #6c757d;
        border-color: #6c757d;
    }
    
    .voice-control-button.stop:hover:not(:disabled) {
        background: #5a6268;
        border-color: #5a6268;
        box-shadow: 0 4px 12px rgba(108, 117, 125, 0.3);
    }
    
    .voice-control-button.stop.active {
        background: #dc3545;
        border-color: #dc3545;
    }
    
    .voice-control-button.stop.active:hover:not(:disabled) {
        background: #c82333;
        border-color: #c82333;
        box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
    }
    
    /* Recording Timer */
    .recording-timer {
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 18px;
        font-weight: bold;
        color: #dc3545;
        background: rgba(220, 53, 69, 0.1);
        padding: 8px 12px;
        border-radius: 6px;
        border: 1px solid rgba(220, 53, 69, 0.3);
        min-width: 80px;
        text-align: center;
    }
    
    .recording-timer.recording {
        animation: blink 1s infinite;
    }
    
    /* Voice Status with Enhanced Indicators */
    .voice-status {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 14px;
        color: #666;
        font-weight: 500;
    }
    
    /* Status Dots - Enhanced with better animations */
    .status-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #6c757d;
        transition: all 0.3s ease;
        border: 2px solid transparent;
    }
    
    .status-dot.recording {
        background: #dc3545;
        animation: pulse-strong 0.8s infinite;
        border-color: rgba(220, 53, 69, 0.3);
        box-shadow: 0 0 12px rgba(220, 53, 69, 0.5);
    }
    
    .status-dot.paused {
        background: #ffc107;
        border-color: rgba(255, 193, 7, 0.3);
        animation: pulse-slow 2s infinite;
    }
    
    .status-dot.ready {
        background: #28a745;
        border-color: rgba(40, 167, 69, 0.3);
    }
    
    @keyframes pulse-strong {
        0% { 
            transform: scale(1); 
            opacity: 1; 
        }
        50% { 
            transform: scale(1.3); 
            opacity: 0.7; 
        }
        100% { 
            transform: scale(1); 
            opacity: 1; 
        }
    }
    
    @keyframes pulse-slow {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* Sound Wave Visualization */
    .sound-wave {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 2px;
        height: 30px;
        padding: 0 10px;
    }
    
    .sound-wave-bar {
        width: 3px;
        background: #dc3545;
        border-radius: 2px;
        transition: height 0.1s ease;
    }
    
    .sound-wave-bar.recording {
        animation: wave-bounce 0.5s infinite alternate;
    }
    
    .sound-wave-bar:nth-child(1) { animation-delay: 0s; }
    .sound-wave-bar:nth-child(2) { animation-delay: 0.1s; }
    .sound-wave-bar:nth-child(3) { animation-delay: 0.2s; }
    .sound-wave-bar:nth-child(4) { animation-delay: 0.3s; }
    .sound-wave-bar:nth-child(5) { animation-delay: 0.4s; }
    .sound-wave-bar:nth-child(6) { animation-delay: 0.3s; }
    .sound-wave-bar:nth-child(7) { animation-delay: 0.2s; }
    .sound-wave-bar:nth-child(8) { animation-delay: 0.1s; }
    
    @keyframes wave-bounce {
        0% { height: 5px; }
        100% { height: 25px; }
    }
    
    .sound-wave.paused .sound-wave-bar {
        height: 15px;
        background: #ffc107;
        animation: none;
    }
    """
    
    # JavaScript for voice recording functionality
    voice_recording_js = """
    <script>
    let mediaRecorder = null;
    let recordedChunks = [];
    let recordingTimer = null;
    let recordingStartTime = 0;
    let recordingState = 'idle'; // 'idle', 'recording', 'paused'
    let isAutoRecordingEnabled = false;
    let soundWaveInterval = null;
    
    function updateRecordingUI(state, time = '00:00') {
        const statusDot = document.querySelector('.status-dot');
        const timer = document.querySelector('.recording-timer');
        const resumePauseBtn = document.getElementById('resume-pause-recording');
        const stopBtn = document.getElementById('stop-recording');
        const soundWave = document.getElementById('sound-wave');
        
        if (statusDot) {
            statusDot.className = 'status-dot ' + state;
        }
        
        if (timer) {
            timer.textContent = time;
            timer.className = state === 'recording' ? 'recording-timer recording' : 'recording-timer';
        }
        
        if (resumePauseBtn && stopBtn) {
            switch(state) {
                case 'recording':
                    resumePauseBtn.disabled = false;
                    resumePauseBtn.textContent = '⏸️ Pause';
                    resumePauseBtn.className = 'voice-control-button resume-pause paused';
                    stopBtn.disabled = false;
                    stopBtn.className = 'voice-control-button stop active';
                    if (soundWave) {
                        soundWave.style.display = 'flex';
                        soundWave.className = 'sound-wave';
                        const bars = soundWave.querySelectorAll('.sound-wave-bar');
                        bars.forEach(bar => bar.className = 'sound-wave-bar recording');
                    }
                    startSoundWaveAnimation();
                    break;
                case 'paused':
                    resumePauseBtn.disabled = false;
                    resumePauseBtn.textContent = '▶️ Resume';
                    resumePauseBtn.className = 'voice-control-button resume-pause';
                    stopBtn.disabled = false;
                    stopBtn.className = 'voice-control-button stop active';
                    if (soundWave) {
                        soundWave.style.display = 'flex';
                        soundWave.className = 'sound-wave paused';
                        const bars = soundWave.querySelectorAll('.sound-wave-bar');
                        bars.forEach(bar => bar.className = 'sound-wave-bar');
                    }
                    stopSoundWaveAnimation();
                    break;
                case 'idle':
                default:
                    resumePauseBtn.disabled = false;
                    resumePauseBtn.textContent = '🎤 Resume/Pause';
                    resumePauseBtn.className = 'voice-control-button resume-pause';
                    stopBtn.disabled = true;
                    stopBtn.className = 'voice-control-button stop';
                    if (soundWave) {
                        soundWave.style.display = 'none';
                    }
                    stopSoundWaveAnimation();
                    break;
            }
        }
    }
    
    function startSoundWaveAnimation() {
        if (soundWaveInterval) clearInterval(soundWaveInterval);
        
        soundWaveInterval = setInterval(() => {
            if (recordingState === 'recording') {
                const bars = document.querySelectorAll('.sound-wave-bar.recording');
                bars.forEach(bar => {
                    const height = Math.random() * 20 + 5; // Random height between 5-25px
                    bar.style.height = height + 'px';
                });
            }
        }, 100);
    }
    
    function stopSoundWaveAnimation() {
        if (soundWaveInterval) {
            clearInterval(soundWaveInterval);
            soundWaveInterval = null;
        }
    }
    
    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return mins + ':' + (secs < 10 ? '0' : '') + secs;
    }
    
    function startRecordingTimer() {
        recordingStartTime = Date.now();
        recordingTimer = setInterval(() => {
            if (recordingState === 'recording') {
                const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
                updateRecordingUI('recording', formatTime(elapsed));
            }
        }, 1000);
    }
    
    function stopRecordingTimer() {
        if (recordingTimer) {
            clearInterval(recordingTimer);
            recordingTimer = null;
        }
    }
    
    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            recordedChunks = [];
            
            mediaRecorder = new MediaRecorder(stream);
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    recordedChunks.push(event.data);
                }
            };
            
            mediaRecorder.onstop = () => {
                stream.getTracks().forEach(track => track.stop());
                const audioBlob = new Blob(recordedChunks, { type: 'audio/wav' });
                
                // Convert blob to base64 and trigger processing
                const reader = new FileReader();
                reader.onloadend = () => {
                    const base64Audio = reader.result.split(',')[1];
                    processVoiceRecording(base64Audio);
                };
                reader.readAsDataURL(audioBlob);
            };
            
            mediaRecorder.start(1000); // Collect data every second
            recordingState = 'recording';
            startRecordingTimer();
            updateRecordingUI('recording');
            
        } catch (err) {
            console.error('Error starting recording:', err);
            alert('Error accessing microphone. Please check permissions.');
        }
    }
    
    function toggleRecording() {
        if (recordingState === 'idle') {
            startRecording();
        } else if (recordingState === 'recording') {
            pauseRecording();
        } else if (recordingState === 'paused') {
            resumeRecording();
        }
    }
    
    function pauseRecording() {
        if (mediaRecorder && recordingState === 'recording') {
            mediaRecorder.pause();
            recordingState = 'paused';
            updateRecordingUI('paused');
        }
    }
    
    function resumeRecording() {
        if (mediaRecorder && recordingState === 'paused') {
            mediaRecorder.resume();
            recordingState = 'recording';
            updateRecordingUI('recording');
        }
    }
    
    function stopRecording() {
        if (mediaRecorder && recordingState !== 'idle') {
            mediaRecorder.stop();
            recordingState = 'idle';
            stopRecordingTimer();
            updateRecordingUI('idle', '');
        }
    }
    
         function processVoiceRecording(base64Audio) {
         // Send the recorded audio to Python backend via hidden input
         console.log('Processing voice recording...', base64Audio.substring(0, 50) + '...');
         const audioInput = document.getElementById('recorded-audio-input');
         if (audioInput) {
             // Set the value and trigger multiple events to ensure it's detected
             audioInput.value = base64Audio;
             
             // Try multiple event types to ensure detection
             const events = ['input', 'change', 'blur'];
             events.forEach(eventType => {
                 const event = new Event(eventType, { bubbles: true });
                 audioInput.dispatchEvent(event);
             });
             
             console.log('Audio data sent to backend');
         } else {
             console.error('Audio input element not found!');
         }
     }
    
    // Auto-start recording after AI response
    function enableAutoRecording() {
        isAutoRecordingEnabled = true;
        
        // Show countdown before auto-recording starts
        let countdown = 3;
        const countdownInterval = setInterval(() => {
            if (!isAutoRecordingEnabled) {
                clearInterval(countdownInterval);
                return;
            }
            
            const timer = document.querySelector('.recording-timer');
            if (timer && countdown > 0) {
                timer.textContent = `Auto-start in ${countdown}s`;
                timer.className = 'recording-timer';
            }
            
            countdown--;
            
            if (countdown < 0) {
                clearInterval(countdownInterval);
                if (isAutoRecordingEnabled && recordingState === 'idle') {
                    // Show brief "Recording started" feedback
                    if (timer) {
                        timer.textContent = 'Recording started!';
                        timer.className = 'recording-timer recording';
                    }
                    
                    setTimeout(() => {
                        if (recordingState === 'idle') {
                            startRecording();
                        }
                    }, 500);
                } else {
                    if (timer) {
                        timer.textContent = '00:00';
                        timer.className = 'recording-timer';
                    }
                }
            }
        }, 1000);
    }
    
    function disableAutoRecording() {
        isAutoRecordingEnabled = false;
    }
    
    // Initialize when DOM loads
    document.addEventListener('DOMContentLoaded', function() {
        updateRecordingUI('idle');
    });
    </script>
    """
    
    with gr.Blocks(css=custom_css, title="IntactBot - First Notice of Loss Agent", head=voice_recording_js) as demo:
        # Helper functions for dynamic UI updates
        def create_payload_header(is_complete: bool) -> str:
            status_class = "payload-complete" if is_complete else "payload-incomplete"
            status_text = "✓ Complete" if is_complete else "In Progress"
            return f'<h3 class="section-header">Claim Payload <span class="{status_class}">({status_text})</span></h3>'

        def create_info_panel(is_complete: bool) -> str:
            bg_color = "#f8f9fa" if is_complete else "#f8f9fa"
            return f"""
            <div style="margin-top: 15px; padding: 12px; background: {bg_color}; border-radius: 6px; 
                        border-left: 4px solid #dc3545; font-size: 13px; color: #666;">
                <strong>Real-time Payload:</strong> This panel displays the current state of claim data 
                being processed by the agent. Updates automatically as the conversation progresses.
            </div>
            """

        # Create logo HTML with fallback
        if logo_uri:
            logo_html = f'<img src="{logo_uri}" alt="IntactBot Logo" style="max-height: 58px;">'
        else:
            logo_html = '<div style="font-size: 35px;">🤖</div>'
        
        gr.HTML(f"""
        <div class="logo-container">
            <div class="logo-left">
                {logo_html}
            </div>
            <div class="logo-text">
                <h1>IntactBot-FNOL-v0.1</h1>
                <p>First Notice of Loss Processing Agent</p>
            </div>
        </div>
        """)
        
        with gr.Blocks() as fnol_interface:
            with gr.Column(elem_classes="start-fnol-container"):
                gr.HTML("<h2>🎤 Voice-First FNOL Processing</h2>")
                gr.HTML("<p>Click the button below to start reporting your loss. The system will automatically begin recording your voice after each response.</p>")
                start_button = gr.Button("Start FNOL Process", variant="primary", size="lg")
                
                # Audio status indicator (initially hidden)
                audio_status = gr.HTML(
                    value="",
                    visible=False,
                    elem_classes="audio-status"
                )

        with gr.Row(visible=False) as chat_interface:
            # Left side - Chat interface
            with gr.Column(scale=1):
                gr.HTML('<h3 class="section-header">🗣️ Voice & Text Conversation</h3>')
                
                # Voice Recording Controls
                with gr.Row(elem_classes="voice-controls"):
                    with gr.Column(scale=2):
                        gr.HTML('<div class="voice-status"><span class="status-dot" id="status-dot"></span><span>Voice Recording</span></div>')
                        gr.HTML('''
                        <div class="sound-wave" id="sound-wave" style="display: none;">
                            <div class="sound-wave-bar"></div>
                            <div class="sound-wave-bar"></div>
                            <div class="sound-wave-bar"></div>
                            <div class="sound-wave-bar"></div>
                            <div class="sound-wave-bar"></div>
                            <div class="sound-wave-bar"></div>
                            <div class="sound-wave-bar"></div>
                            <div class="sound-wave-bar"></div>
                        </div>
                        ''')
                    with gr.Column(scale=1):
                        gr.HTML('<div class="recording-timer" id="recording-timer">00:00</div>')
                    with gr.Column(scale=3):
                        with gr.Row():
                            resume_pause_btn = gr.Button("🎤 Resume/Pause", elem_id="resume-pause-recording", elem_classes="voice-control-button resume-pause")
                            stop_record_btn = gr.Button("⏹️ Stop & Send", elem_id="stop-recording", elem_classes="voice-control-button stop")
                
                # Audio output component (always present but initially hidden)
                audio_output = gr.Audio(
                    autoplay=True, 
                    visible=False,
                    show_label=False,
                    interactive=False,
                    show_download_button=False,
                    show_share_button=False
                )
                
                chatbot = gr.Chatbot(
                    value=bot.initial_chat_history,
                    elem_classes="chat-container",
                    show_label=False,
                    avatar_images=None,
                    type='messages',
                    visible=False
                )
                
                with gr.Row():
                    msg_input = gr.MultimodalTextbox(
                        placeholder="💡 Use voice recording controls above, or type your response here...",
                        show_label=False,
                        scale=4,
                        container=False,
                        interactive=True,
                        file_types=["audio"]
                    )
                
                with gr.Row():
                    clear_btn = gr.Button("Clear Chat", variant="secondary")

                # Loading and audio status indicators
                loading_indicator = gr.HTML(
                    value="",
                    visible=True,
                    elem_classes="processing-indicator"
                )
                
                # Recording status indicator
                recording_status = gr.HTML(
                    value="",
                    visible=True,
                    elem_classes="audio-status"
                )
                
                # Hidden component to store recorded audio data
                recorded_audio_data = gr.State(value=None)
                recorded_audio_input = gr.Textbox(value="", visible=False, elem_id="recorded-audio-input")
            
            # Right side - Payload display
            with gr.Column(scale=1):
                payload_header = gr.HTML(create_payload_header(bot.is_form_complete))
                
                payload_display = gr.Code(
                    value=bot.format_payload(),
                    language="json",
                    show_label=False,
                    elem_classes="payload-container",
                    interactive=False
                )
                
                info_panel = gr.HTML(create_info_panel(bot.is_form_complete))
        
        # Hidden component for JavaScript communication
        js_trigger = gr.HTML(value="", visible=False)
        
        async def start_process():
            initial_history, audio_bytes = await bot.start_fnol_process()
            
            # Show audio playing indicator
            audio_status_html = '<div class="audio-status audio-playing">🔊 Playing initial message...</div>'
            
            # Save audio to temporary file for playback
            audio_file = None
            if audio_bytes:
                audio_file = "temp_audio_init.wav"
                with open(audio_file, "wb") as f:
                    f.write(audio_bytes)
            
            # Always make audio component visible when we have audio to play
            audio_visible = audio_file is not None
            
            return {
                chat_interface: gr.update(visible=True),
                chatbot: gr.update(value=initial_history, visible=True),
                start_button: gr.update(visible=False),
                audio_output: gr.update(value=audio_file, visible=audio_visible),
                audio_status: gr.update(value=audio_status_html, visible=True),
                recording_status: gr.update(value="🎤 <strong>Auto-recording will start after AI finishes speaking</strong>", visible=True)
            }

        async def process_voice_recording(audio_data_b64):
            """Process base64 encoded audio data from JavaScript"""
            if not audio_data_b64:
                return [], bot.format_payload(), "", create_payload_header(bot.is_form_complete), create_info_panel(bot.is_form_complete), None, "", ""
            
            try:
                # Decode base64 audio data
                import base64
                audio_bytes = base64.b64decode(audio_data_b64)
                
                # Get current chat history
                current_history = []  # This would need to be tracked in state
                
                # Process the voice message
                updated_history, updated_payload, is_form_complete, audio_response = await bot.process_voice_message(audio_bytes, current_history)
                
                # Prepare audio response
                audio_filepath = None
                audio_status_html = ""
                if audio_response:
                    audio_filepath = "temp_audio_response.wav"
                    with open(audio_filepath, "wb") as f:
                        f.write(audio_response)
                    audio_status_html = '<div class="audio-status audio-playing">🔊 Playing response...</div>'
                
                # Set up for next recording cycle
                recording_html = '<div class="audio-status">🎤 <strong>Auto-recording will start after AI finishes speaking</strong></div>'
                
                return (
                    updated_history,
                    updated_payload,
                    "",
                    create_payload_header(is_form_complete),
                    create_info_panel(is_form_complete),
                    gr.update(value=audio_filepath, visible=True) if audio_filepath else gr.update(visible=False),
                    audio_status_html,
                    recording_html
                )
                
            except Exception as e:
                print(f"Error processing voice recording: {e}")
                return [], bot.format_payload(), f"Error: {str(e)}", create_payload_header(bot.is_form_complete), create_info_panel(bot.is_form_complete), None, "", ""

        async def handle_user_input(message, history):
            """Process user message and update UI"""
            if not message["text"].strip() and not message["files"]:
                yield history, message, bot.format_payload(), "", create_payload_header(bot.is_form_complete), create_info_panel(bot.is_form_complete), None, "", ""
                return

            # Show recording/processing indicators
            if message["files"]:
                history.append({"role": "user", "content": "🎤 *Processing voice input...*"})
                recording_html = '<div class="audio-status audio-recording">🎤 Processing your voice message...</div>'
            else:
                history.append({"role": "user", "content": message["text"]})
                recording_html = '<div class="audio-status">⌨️ Processing your text message...</div>'

            yield (
                history, 
                gr.update(value={"text": "", "files": []}), 
                bot.format_payload(), 
                "Processing your message...", 
                create_payload_header(bot.is_form_complete), 
                create_info_panel(bot.is_form_complete), 
                None,
                "",
                recording_html
            )

            # Process the message
            updated_history, updated_payload, is_form_complete, audio_response = await bot.process_message(message, history[:-1])

            # Prepare audio response
            audio_filepath = None
            audio_status_html = ""
            if audio_response:
                audio_filepath = "temp_audio_response.wav"
                with open(audio_filepath, "wb") as f:
                    f.write(audio_response)
                audio_status_html = '<div class="audio-status audio-playing">🔊 Playing response...</div>'
            
            # Set up for next recording cycle
            recording_html = '<div class="audio-status">🎤 <strong>Auto-recording will start after AI finishes speaking</strong></div>'
            
            yield (
                updated_history, 
                gr.update(value={"text": "", "files": []}), 
                updated_payload, 
                "", 
                create_payload_header(is_form_complete), 
                create_info_panel(is_form_complete), 
                gr.update(value=audio_filepath, visible=True) if audio_filepath else gr.update(visible=False),
                audio_status_html,
                recording_html
            )
        
        def clear_chat():
            cleared_history, cleared_payload, is_form_complete, audio_bytes = bot.reset_conversation()
            return (
                cleared_history, 
                cleared_payload, 
                "", 
                create_payload_header(is_form_complete), 
                create_info_panel(is_form_complete), 
                gr.update(visible=False),
                "",
                "",
                gr.update(visible=True), 
                gr.update(visible=False)
            )
        
        def clear_audio_status():
            """Clear audio status indicators"""
            return gr.update(value="", visible=False)
        
        def update_ready_status():
            """Update status to show ready for input"""
            return gr.update(value='<div class="audio-status">✅ Ready for your response</div>', visible=True)
        
        # Add audio finish callback - trigger auto-recording when audio finishes
        def handle_audio_finish():
            """Handle when AI audio finishes playing"""
            return (
                gr.update(value="", visible=False),  # Clear audio status
                gr.update(value="""
                    <script>
                    setTimeout(() => {
                        if (typeof enableAutoRecording === 'function') {
                            enableAutoRecording();
                        }
                    }, 1000);  // Start auto-recording 1 second after audio finishes
                    </script>
                """)  # Trigger auto-recording
            )
        
        audio_output.change(
            fn=handle_audio_finish,
            outputs=[audio_status, js_trigger]
        )
        
        # JavaScript functions that can be called from Python
        def trigger_auto_recording():
            """Trigger auto-recording via JavaScript"""
            return gr.update(value="""
                <script>
                setTimeout(() => {
                    if (typeof enableAutoRecording === 'function') {
                        enableAutoRecording();
                    }
                }, 500);  // Short delay to ensure audio is playing
                </script>
            """)
        
        def stop_auto_recording():
            """Stop auto-recording via JavaScript"""
            return gr.update(value="""
                <script>
                if (typeof disableAutoRecording === 'function') {
                    disableAutoRecording();
                }
                </script>
            """)
        
        # State to track chat history for voice processing
        chat_history_state = gr.State(value=[])
        
        async def enhanced_start_process():
            """Enhanced start process with auto-recording trigger"""
            initial_results = await start_process()
            # Convert to list to modify, add JavaScript trigger
            results_list = list(initial_results.values())
            results_list.append(trigger_auto_recording())
            
            # Return properly mapped results
            return (
                initial_results[chat_interface],
                initial_results[chatbot], 
                initial_results[start_button],
                initial_results[audio_output],
                initial_results[audio_status],
                initial_results[recording_status],
                results_list[-1]  # js_trigger
            )
        
        async def enhanced_handle_user_input(message, history, history_state):
            """Enhanced message handler with auto-recording management"""
            # Stop any current auto-recording when user starts typing/recording manually
            stop_recording_js = stop_auto_recording()
            
            async for result in handle_user_input(message, history):
                # Add JavaScript trigger to stop auto-recording during processing
                result_list = list(result)
                result_list.append(stop_recording_js)
                result_list.append(result[0])  # Update history state
                yield tuple(result_list)
            
            # Get the final result and trigger auto-recording
            final_result = list(result)
            final_result.append(trigger_auto_recording())
            final_result.append(final_result[0])  # Update history state
            yield tuple(final_result)
        
        async def process_recorded_audio(audio_b64_data, current_history):
            """Process audio data from JavaScript recording"""
            if not audio_b64_data or audio_b64_data.strip() == "":
                return current_history, "", bot.format_payload(), "", create_payload_header(bot.is_form_complete), None, "", "", current_history
            
            try:
                import base64
                # Decode the base64 audio data
                audio_bytes = base64.b64decode(audio_b64_data)
                
                # Process the voice message
                updated_history, updated_payload, is_form_complete, audio_response = await bot.process_voice_message(audio_bytes, current_history)
                
                # Prepare audio file for playback
                audio_filepath = None
                if audio_response:
                    audio_filepath = "temp_audio_response.wav"
                    with open(audio_filepath, "wb") as f:
                        f.write(audio_response)
                
                return (
                    updated_history,
                    gr.update(value=""),  # Clear the audio input
                    updated_payload,
                    "",
                    create_payload_header(is_form_complete),
                    gr.update(value=audio_filepath, visible=True) if audio_filepath else gr.update(visible=False),
                    '<div class="audio-status audio-playing">🔊 Playing response...</div>' if audio_response else "",
                    trigger_auto_recording(),  # Trigger next recording cycle
                    updated_history  # Update chat history state
                )
            except Exception as e:
                print(f"Error processing recorded audio: {e}")
                return current_history, "", bot.format_payload(), f"Error: {str(e)}", create_payload_header(bot.is_form_complete), None, "", "", current_history
        
        # Voice recording button handlers
        def handle_resume_pause_recording():
            """Handle consolidated resume/pause recording button"""
            return gr.update(value="""
                <script>
                setTimeout(() => {
                    if (typeof toggleRecording === 'function') {
                        toggleRecording();
                    }
                }, 10);
                </script>
            """)
        
        def handle_stop_recording():
            """Handle stop and send recording button"""
            return gr.update(value="""
                <script>
                setTimeout(() => {
                    if (typeof stopRecording === 'function') {
                        stopRecording();
                    }
                }, 10);
                </script>
            """)
        
        # Enhanced clear function to reset history state
        def enhanced_clear_chat():
            result = clear_chat()
            return result + ([], "")  # Reset history state and js trigger
        
        # Event handlers
        start_button.click(
            enhanced_start_process,
            outputs=[chat_interface, chatbot, start_button, audio_output, audio_status, recording_status, js_trigger]
        )

        msg_input.submit(
            enhanced_handle_user_input,
            inputs=[msg_input, chatbot, chat_history_state],
            outputs=[chatbot, msg_input, payload_display, loading_indicator, payload_header, info_panel, audio_output, audio_status, recording_status, js_trigger, chat_history_state]
        )
        
        clear_btn.click(
            enhanced_clear_chat,
            outputs=[chatbot, payload_display, loading_indicator, payload_header, info_panel, audio_output, audio_status, recording_status, start_button, chat_interface, chat_history_state, js_trigger]
        )
        
        # Voice recording button event handlers
        resume_pause_btn.click(
            handle_resume_pause_recording,
            outputs=[js_trigger]
        )
        
        stop_record_btn.click(
            handle_stop_recording,
            outputs=[js_trigger]
        )
        
        # Handle recorded audio from JavaScript
        recorded_audio_input.change(
            process_recorded_audio,
            inputs=[recorded_audio_input, chat_history_state],
            outputs=[chatbot, recorded_audio_input, payload_display, loading_indicator, payload_header, audio_output, audio_status, js_trigger, chat_history_state]
        )
    
    return demo

def find_available_port(start_port=7860, max_attempts=10):
    """Find an available port starting from start_port"""
    import socket
    
    for i in range(max_attempts):
        port = start_port + i
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return None

# Create the demo at module level for Gradio auto-reload
demo = create_ui()

def main():
    """Launch the Gradio app"""
    print("🚀 Starting IntactBot UI...")
    
    # Find an available port
    port = find_available_port()
    if port is None:
        print("❌ Could not find an available port. Please check if other Gradio apps are running.")
        return
    
    print(f"🔗 App will be available at: http://127.0.0.1:{port}")
    
    try:
        demo.launch(
            server_name="127.0.0.1",
            server_port=port,
            show_error=True,
            quiet=False,
            debug=True,
            inbrowser=True
        )
    except Exception as e:
        print(f"❌ Failed to launch app: {e}")

if __name__ == "__main__":
    main() 