import React, { useState, useRef, useEffect, useCallback } from 'react';
import styled, { keyframes, css } from 'styled-components';
import { FaPaperPlane, FaTrash, FaMicrophone } from 'react-icons/fa';
import { toast } from 'react-toastify';

import PayloadDisplay from './PayloadDisplay';
import ChatMessage from './ChatMessage';
import AudioPlayer from './AudioPlayer';
import useAudioRecording from '../hooks/useAudioRecording';
import SoundWaveVisualizer from './SoundWaveVisualizer';

const ChatContainer = styled.div`
  display: grid;
  grid-template-columns: 1fr 560px;
  gap: 24px;
  min-height: 70vh;
  
  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto;
  }
`;

const LeftPanel = styled.div`
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 16px;
  border: 2px solid #e0e0e0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
`;

const ChatHeader = styled.div`
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  padding: 16px 20px;
  border-bottom: 2px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const ChatTitle = styled.h3`
  margin: 0;
  color: #2c3e50;
  font-size: 18px;
  font-weight: 600;
`;

const ResetButton = styled.button`
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;

  &:hover:not(:disabled) {
    background: #5a6268;
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

const ChatBody = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 500px;
`;

const MessagesContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
`;

const TextInputContainer = styled.div`
  padding: 16px 20px;
  border-top: 1px solid #e0e0e0;
  background: #f8f9fa;
`;

const TextInputRow = styled.div`
  display: flex;
  gap: 12px;
  align-items: center;
`;

const TextInput = styled.textarea`
  flex: 1;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  min-height: 50px;
  max-height: 120px;
  transition: border-color 0.3s ease;

  &:focus {
    outline: none;
    border-color: #007bff;
  }

  &::placeholder {
    color: #999;
  }
`;

const SendButton = styled.button`
  background: ${props => props.isRecording ? '#ffc107' : '#dc3545'};
  color: ${props => props.isRecording ? '#000' : 'white'};
  border: none;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 100px;
  justify-content: center;
  box-shadow: ${props => props.isRecording ? '0 0 0 2px rgba(255, 193, 7, 0.5)' : 'none'};

  &:hover:not(:disabled) {
    background: ${props => props.isRecording ? '#e0a800' : '#c82333'};
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

const NoMessagesPlaceholder = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
  text-align: center;
  gap: 16px;
`;

const PlaceholderIcon = styled.div`
  font-size: 48px;
  opacity: 0.5;
`;

const PlaceholderText = styled.p`
  font-size: 16px;
  margin: 0;
  line-height: 1.5;
`;

// Add from VoiceRecording
const VoiceControlsContainer = styled.div`
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border: 2px solid #e0e0e0;
  border-radius: 16px;
  padding: 20px;
  margin: 16px 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
  }
`;

const ControlsHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
`;

const StatusIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 500;
  color: #333;
`;

const StatusDot = styled.div`
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: ${props => {
    if (props.isRecording) return '#dc3545';
    if (props.isPaused) return '#ffc107';
    return '#6c757d';
  }};
  transition: all 0.3s ease;
  
  ${props => props.isRecording && css`
    animation: ${pulseAnimation} 1.5s infinite;
  `}
  
  ${props => props.isPaused && css`
    animation: ${blinkAnimation} 2s infinite;
  `}
`;

const RecordingTimer = styled.div`
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 18px;
  font-weight: bold;
  color: ${props => props.isRecording ? '#dc3545' : '#666'};
  background: ${props => props.isRecording ? 'rgba(220, 53, 69, 0.1)' : '#f8f9fa'};
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid ${props => props.isRecording ? 'rgba(220, 53, 69, 0.3)' : '#e0e0e0'};
  min-width: 80px;
  text-align: center;
  transition: all 0.3s ease;
  
  ${props => props.isRecording && css`
    animation: ${blinkAnimation} 1s infinite;
  `}
`;

const VisualizerContainer = styled.div`
  margin: 16px 0;
  min-height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  border-radius: 12px;
  border: 1px solid #e0e0e0;
  overflow: hidden;
  transition: all 0.3s ease;
  
  ${props => props.show && css`
    border-color: ${props.isRecording ? '#dc3545' : '#ffc107'};
    background: ${props.isRecording ? 'rgba(220, 53, 69, 0.05)' : 'rgba(255, 193, 7, 0.05)'};
  `}
`;

const ToggleButton = styled.button`
  background: ${props => props.isRecording ? '#ffc107' : '#28a745'};
  color: ${props => props.isRecording ? '#000' : 'white'};
  border: none;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 140px;
  justify-content: center;

  &:hover:not(:disabled) {
    background: ${props => props.isRecording ? '#e0a800' : '#218838'};
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

const ErrorMessage = styled.div`
  background: #ffebee;
  border: 1px solid #f44336;
  border-radius: 8px;
  padding: 12px;
  color: #c62828;
  margin: 8px 0;
  font-weight: 500;
`;

const pulseAnimation = keyframes`
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 0 10px rgba(220, 53, 69, 0);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0);
  }
`;
const blinkAnimation = keyframes`
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0.3;
  }
`;

const RecordingIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  color: #dc3545;
  font-weight: 600;
  background: rgba(220, 53, 69, 0.1);
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(220, 53, 69, 0.3);
  animation: ${props => props.isRecording ? pulseAnimation : 'none'} 2s infinite;
`;

const AutoRecordingNotification = styled.div`
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border: 2px solid #2196f3;
  border-radius: 12px;
  padding: 12px 16px;
  margin: 12px 16px;
  text-align: center;
  font-weight: 500;
  color: #1565c0;
  animation: slideIn 0.5s ease-out;
  
  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
`;

const ConversationTurnIndicator = styled.div`
  background: ${props => {
    switch(props.turn) {
      case 'ai_speaking': return 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)';
      case 'ai_complete': return 'linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%)';
      case 'user_turn': return 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)';
      case 'user_speaking': return 'linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%)';
      case 'processing': return 'linear-gradient(135deg, #fce4ec 0%, #f8bbd9 100%)';
      case 'no_audio': return 'linear-gradient(135deg, #fffde7 0%, #fff9c4 100%)';
      default: return 'linear-gradient(135deg, #f5f5f5 0%, #eeeeee 100%)';
    }
  }};
  border: 2px solid ${props => {
    switch(props.turn) {
      case 'ai_speaking': return '#ff9800';
      case 'ai_complete': return '#4caf50';
      case 'user_turn': return '#2196f3';
      case 'user_speaking': return '#f44336';
      case 'processing': return '#e91e63';
      case 'no_audio': return '#ffc107';
      default: return '#757575';
    }
  }};
  border-radius: 12px;
  padding: 12px 16px;
  margin: 12px 16px;
  text-align: center;
  font-weight: 500;
  color: ${props => {
    switch(props.turn) {
      case 'ai_speaking': return '#e65100';
      case 'ai_complete': return '#2e7d32';
      case 'user_turn': return '#1565c0';
      case 'user_speaking': return '#c62828';
      case 'processing': return '#ad1457';
      case 'no_audio': return '#ff8f00';
      default: return '#424242';
    }
  }};
  animation: ${props => ['ai_speaking', 'user_speaking', 'no_audio'].includes(props.turn) ? css`${pulseAnimation} 2s infinite` : 'slideIn 0.5s ease-out'};
  
  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
`;

const MicrophoneSelector = styled.div`
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 8px 12px;
  margin: 8px 0;
  font-size: 12px;
  color: #666;
`;

const DeviceSelect = styled.select`
  background: white;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  margin-left: 8px;
  max-width: 200px;
`;

const ChatInterface = ({
  chatHistory = [],
  payload = {},
  isFormComplete = false,
  onSendMessage,
  onSendVoiceMessage,
  onReset,
  isLoading = false,
  initialAudio
}) => {
  const [textMessage, setTextMessage] = useState('');
  const [isTextSending, setIsTextSending] = useState(false);
  const [lastAIMessage, setLastAIMessage] = useState(null);
  const [shouldAutoStartRecording, setShouldAutoStartRecording] = useState(false);
  const [currentAudioData, setCurrentAudioData] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isAutoRecordingPending, setIsAutoRecordingPending] = useState(false);
  const [audioPlayStartTime, setAudioPlayStartTime] = useState(null);
  
  // Add conversation turn state management
  const [conversationTurn, setConversationTurn] = useState('waiting'); // 'ai_speaking', 'ai_complete', 'user_turn', 'user_speaking', 'processing', 'waiting'
  const [aiTextDisplayed, setAiTextDisplayed] = useState(false);
  const [aiAudioComplete, setAiAudioComplete] = useState(false);
  const [turnTransitionDelay, setTurnTransitionDelay] = useState(null);
  
  const messagesEndRef = useRef(null);
  const textInputRef = useRef(null);
  const turnTimeoutRef = useRef(null);

  // Add recording hook
  const {
    isRecording,
    isPaused,
    recordingTime,
    audioLevels,
    error: recordingError,
    toggleRecording,
    stopRecording,
    getBase64Audio,
    isInitialized,
    audioURL,
    availableDevices,
    selectedDeviceId,
    changeDevice
  } = useAudioRecording();

  // Set initial audio and start AI turn if present
  useEffect(() => {
    if (initialAudio) {
      setCurrentAudioData(initialAudio);
      setConversationTurn('ai_speaking');
      setAiTextDisplayed(true);
      setAiAudioComplete(false);
    }
  }, [initialAudio]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (turnTimeoutRef.current) {
        clearTimeout(turnTimeoutRef.current);
      }
    };
  }, []);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  // Detect new AI messages and start AI turn
  useEffect(() => {
    if (chatHistory.length > 0) {
      const lastMessage = chatHistory[chatHistory.length - 1];
      if (lastMessage.role === 'assistant' && lastMessage !== lastAIMessage) {
        console.log('New AI message detected, starting AI turn');
        setLastAIMessage(lastMessage);
        setConversationTurn('ai_speaking');
        setAiTextDisplayed(true); // Text is immediately displayed
        setAiAudioComplete(false);
        setTurnTransitionDelay(null);
      }
    }
  }, [chatHistory, lastAIMessage]);

  // Manage conversation turn transitions based on AI text display and audio completion
  useEffect(() => {
    console.log('=== Conversation Turn Management ===');
    console.log('conversationTurn:', conversationTurn);
    console.log('aiTextDisplayed:', aiTextDisplayed);
    console.log('aiAudioComplete:', aiAudioComplete);
    console.log('audioPlayStartTime:', audioPlayStartTime);
    console.log('isInitialized:', isInitialized);
    console.log('isRecording:', isRecording);
    console.log('isPaused:', isPaused);
    console.log('isProcessing:', isProcessing);
    
    if (conversationTurn === 'ai_speaking' && aiTextDisplayed && aiAudioComplete) {
      console.log('AI turn complete (text + audio), transitioning to user turn');
      setConversationTurn('ai_complete');
      
      // Add a brief delay before starting user turn for better UX
      const delay = Math.max(800, Math.min(1500, (audioPlayStartTime ? Date.now() - audioPlayStartTime : 1000) * 0.15));
      console.log('Turn transition delay calculated:', delay + 'ms');
      setTurnTransitionDelay(delay);
      
      turnTimeoutRef.current = setTimeout(() => {
        console.log('Starting user turn with auto-recording');
        setConversationTurn('user_turn');
        setIsAutoRecordingPending(true);
        
        // Start auto-recording if conditions are met
        if (isInitialized && !isRecording && !isPaused && !isProcessing) {
          console.log('Conditions met for auto-recording, starting...');
          startAutoRecording();
        } else {
          console.log('Auto-recording conditions not met:', {
            isInitialized,
            isRecording,
            isPaused,
            isProcessing
          });
        }
      }, delay);
    }
  }, [conversationTurn, aiTextDisplayed, aiAudioComplete, audioPlayStartTime, isInitialized, isRecording, isPaused, isProcessing]);

  // Auto-start recording helper function
  const startAutoRecording = async () => {
    try {
      console.log('=== Auto-starting recording ===');
      console.log('Current states before auto-recording:', {
        isInitialized,
        isRecording,
        isPaused,
        isProcessing,
        conversationTurn
      });
      
      await toggleRecording();
      setConversationTurn('user_speaking');
      setIsAutoRecordingPending(false);
      toast.success('🎤 Your turn - speak now!');
      
      console.log('Auto-recording started successfully');
    } catch (error) {
      console.error('Auto-recording failed:', error);
      toast.error(`Auto-recording failed: ${error.message}`);
      setConversationTurn('user_turn');
      setIsAutoRecordingPending(false);
    }
  };

  // Handle user turn when conditions change (e.g., if auto-recording wasn't ready initially)
  useEffect(() => {
    if (conversationTurn === 'user_turn' && isInitialized && !isRecording && !isPaused && !isProcessing && !isAutoRecordingPending) {
      startAutoRecording();
    }
  }, [conversationTurn, isInitialized, isRecording, isPaused, isProcessing, isAutoRecordingPending]);

  const handleSendMessage = async (messageText = null) => {
    const message = messageText || textMessage.trim();
    if (!message && !isRecording && !isPaused) return;

    // If we're currently recording, stop and send the voice message
    if (isRecording || isPaused) {
      return await handleStopAndSend();
    }

    // Otherwise, send text message
    if (!message) return;
    
    setTextMessage('');
    setIsTextSending(true);
    setConversationTurn('processing');
    setIsAutoRecordingPending(false);

    try {
      const response = await onSendMessage(message);
      
      // Handle audio response
      if (response.audio_data) {
        setCurrentAudioData(response.audio_data);
        setAiAudioComplete(false); // Reset audio completion flag
        // Note: aiTextDisplayed will be set to true by the effect that detects new AI messages
      } else {
        // No audio response from AI, mark audio as complete immediately
        setCurrentAudioData(null);
        setAiAudioComplete(true);
      }
      
      toast.success('Message sent successfully!');
    } catch (error) {
      console.error('Error sending text message:', error);
      setConversationTurn('user_turn'); // Reset to user turn on error
      // Clear any audio data on error
      setCurrentAudioData(null);
      setAiAudioComplete(true);
      // Error is already handled in parent component
    } finally {
      setIsTextSending(false);
    }
  };

  const handleSendVoiceMessageLocal = useCallback(async (audioData) => {
    setConversationTurn('processing');
    setIsAutoRecordingPending(false);
    
    try {
      const response = await onSendVoiceMessage(audioData);
      
      if (response.audio_data) {
        setCurrentAudioData(response.audio_data);
        setAiAudioComplete(false); // Reset audio completion flag
      }
      
      return response;
    } catch (error) {
      console.error('Error sending voice message:', error);
      toast.error(`Failed to send voice message: ${error.message}`);
      
      // Clear any previous audio data to prevent replaying
      setCurrentAudioData(null);
      setAiAudioComplete(true);
      
      if (error.message && error.message.toLowerCase().includes('no audio')) {
        setConversationTurn('no_audio');
      } else {
        setConversationTurn('user_turn');
      }
    } finally {
      setIsProcessing(false);
    }
  }, [onSendVoiceMessage]);

  const handleStopAndSend = useCallback(async () => {
    if (!isRecording && !isPaused) {
      toast.warning('No recording to send.');
      return;
    }

    setIsProcessing(true);
    try {
      // Stop the current recording session first
      await stopRecording();

      /*
       * Wait until the MediaRecorder has fully finished flushing the audio
       * data to the blob.  In some browsers the `onstop` event that creates
       * the final blob fires a short time **after** `mediaRecorder.stop()`
       * resolves.  Converting immediately can therefore lead to an empty
       * or undefined blob and the dreaded "No audio detected" error.  We
       * poll `getBase64Audio()` until it succeeds, or we hit a reasonable
       * timeout.
       */
      const MAX_WAIT_MS = 2000; // 2 seconds should be plenty for short clips
      const INTERVAL_MS = 100;
      const start = Date.now();
      let audioData = null;

      // eslint-disable-next-line no-constant-condition
      while (true) {
        try {
          audioData = await getBase64Audio();
          break; // Success!
        } catch (err) {
          if (Date.now() - start > MAX_WAIT_MS) {
            throw err; // Give up – propagate original error
          }
          await new Promise(res => setTimeout(res, INTERVAL_MS));
        }
      }

      await handleSendVoiceMessageLocal(audioData);
      toast.success('🎤 Voice message sent successfully!');
    } catch (error) {
      console.error('Error sending voice message:', error);
      toast.error(`Failed to send voice message: ${error.message}`);
      
      // Clear any previous audio data to prevent replaying
      setCurrentAudioData(null);
      setAiAudioComplete(true);
      
      if (error.message && error.message.toLowerCase().includes('no audio')) {
        setConversationTurn('no_audio');
      } else {
        setConversationTurn('user_turn');
      }
    } finally {
      setIsProcessing(false);
    }
  }, [isRecording, isPaused, setIsProcessing, stopRecording, getBase64Audio, handleSendVoiceMessageLocal]);

  const handleToggleRecording = async () => {
    try {
      // If we are about to START recording (not pause/resume), stop any ongoing AI audio playback
      if (!isRecording && !isPaused && currentAudioData) {
        setCurrentAudioData(null); // This unmounts AudioPlayer and stops playback
        setAiAudioComplete(true);  // Ensure turn state reflects that AI audio is done
      }
      await toggleRecording();
    } catch (error) {
      toast.error(`Recording error: ${error.message}`);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleReset = async () => {
    if (window.confirm('Are you sure you want to reset the conversation? This will clear all chat history and payload data.')) {
      // Clear turn timeout
      if (turnTimeoutRef.current) {
        clearTimeout(turnTimeoutRef.current);
        turnTimeoutRef.current = null;
      }
      
      // Reset all conversation turn states
      setConversationTurn('waiting');
      setAiTextDisplayed(false);
      setAiAudioComplete(false);
      setTurnTransitionDelay(null);
      setIsAutoRecordingPending(false);
      setCurrentAudioData(null);
      setLastAIMessage(null);
      await onReset();
    }
  };

  const handleAudioPlay = () => {
    // Audio started playing
    console.log('AI audio started playing');
    setAudioPlayStartTime(Date.now());
  };

  const handleAudioEnd = () => {
    // Audio finished playing - mark audio as complete for turn management
    console.log('AI audio finished playing');
    const playDuration = audioPlayStartTime ? Date.now() - audioPlayStartTime : 0;
    console.log('Audio played for:', playDuration, 'ms');
    
    setAiAudioComplete(true);
  };

  const handleDeviceChange = async (e) => {
    const deviceId = e.target.value;
    try {
      await changeDevice(deviceId);
      toast.success('Microphone changed successfully!');
    } catch (error) {
      toast.error(`Failed to change microphone: ${error.message}`);
    }
  };

  const getStatusText = () => {
    if (isProcessing) return 'Processing voice message...';
    if (conversationTurn === 'processing') return 'Processing your message...';
    if (conversationTurn === 'ai_speaking') return '🤖 AI is responding...';
    if (conversationTurn === 'ai_complete' && turnTransitionDelay) return `🤖 AI response complete - Your turn in ${Math.ceil(turnTransitionDelay / 1000)}s...`;
    if (isRecording && !isPaused && conversationTurn === 'user_speaking') return '🎤 Recording in progress - Press Send to submit';
    if (isPaused) return 'Recording paused - Press Send to submit or Resume/Pause to continue';
    if (isAutoRecordingPending || conversationTurn === 'user_turn') return '🎤 Your turn - Recording will start automatically...';
    if (conversationTurn === 'user_speaking') return '🎤 Recording in progress - Press Send when done';
    if (conversationTurn === 'no_audio') return '⚠️ No audio recorded - please click Record to try again';
    if (!isInitialized) return 'Initializing microphone...';
    if (conversationTurn === 'waiting') return 'Ready to start conversation';
    return 'Ready to record or type a message';
  };

  const getSendButtonText = () => {
    if (isRecording || isPaused) {
      return isProcessing ? 'Sending...' : 'Send Recording';
    }
    return isTextSending ? 'Sending...' : 'Send';
  };

  const getCurrentDeviceName = () => {
    if (!selectedDeviceId || availableDevices.length === 0) return 'Default microphone';
    const device = availableDevices.find(d => d.deviceId === selectedDeviceId);
    return device ? (device.label || 'Unknown device') : 'Default microphone';
  };

  return (
    <ChatContainer>
      <LeftPanel>
        <ChatHeader>
          <ChatTitle>🗣️ Voice & Text Conversation</ChatTitle>
          <ResetButton onClick={handleReset} disabled={isLoading}>
            <FaTrash />
            Clear Chat
          </ResetButton>
        </ChatHeader>

        {/* Conversation turn indicator */}
        {conversationTurn !== 'waiting' && (
          <ConversationTurnIndicator turn={conversationTurn}>
            {conversationTurn === 'ai_speaking' && '🤖 AI is speaking...'}
            {conversationTurn === 'ai_complete' && turnTransitionDelay && `✅ AI finished - Your turn in ${Math.ceil(turnTransitionDelay / 1000)}s`}
            {conversationTurn === 'user_turn' && '🎤 Your turn - Auto-recording starting...'}
            {conversationTurn === 'user_speaking' && '🎤 Listening... Press Send when finished'}
            {conversationTurn === 'processing' && '⏳ Processing your message...'}
            {conversationTurn === 'no_audio' && '⚠️ No audio recorded - please click Record to try again'}
          </ConversationTurnIndicator>
        )}

        {/* Auto-recording notification - only show if no turn indicator */}
        {isAutoRecordingPending && conversationTurn === 'waiting' && (
          <AutoRecordingNotification>
            🤖 Recording will start automatically in a moment...
          </AutoRecordingNotification>
        )}

        {/* Voice controls section - simplified */}
        <VoiceControlsContainer>
          <ControlsHeader>
            <StatusIndicator>
              <StatusDot 
                isRecording={isRecording && !isPaused} 
                isPaused={isPaused}
              />
              <span>{getStatusText()}</span>
            </StatusIndicator>
            
            <RecordingTimer isRecording={isRecording && !isPaused}>
              {recordingTime}
            </RecordingTimer>
          </ControlsHeader>

          {/* Microphone device selector */}
          {availableDevices.length > 1 && (
            <MicrophoneSelector>
              🎤 Current microphone: <strong>{getCurrentDeviceName()}</strong>
              <DeviceSelect value={selectedDeviceId || ''} onChange={handleDeviceChange}>
                {availableDevices.map(device => (
                  <option key={device.deviceId} value={device.deviceId}>
                    {device.label || `Microphone ${device.deviceId.slice(0, 8)}...`}
                  </option>
                ))}
              </DeviceSelect>
            </MicrophoneSelector>
          )}

          {recordingError && (
            <ErrorMessage>
              ⚠️ {recordingError}
            </ErrorMessage>
          )}

          <VisualizerContainer 
            show={isRecording || isPaused} 
            isRecording={isRecording && !isPaused}
          >
            <SoundWaveVisualizer
              audioLevels={audioLevels}
              isRecording={isRecording && !isPaused}
              isPaused={isPaused}
              show={isRecording || isPaused}
              audioURL={isPaused ? audioURL : null}
            />
          </VisualizerContainer>
        </VoiceControlsContainer>

        {/* Hidden AI Audio Player - no UI, just background audio */}
        {currentAudioData && (
          <AudioPlayer
            audioData={currentAudioData}
            onPlay={handleAudioPlay}
            onEnd={handleAudioEnd}
            autoPlay={true}
          />
        )}

        <ChatBody>
          <MessagesContainer>
            {chatHistory.length === 0 ? (
              <NoMessagesPlaceholder>
                <PlaceholderIcon>💬</PlaceholderIcon>
                <PlaceholderText>
                  {conversationTurn === 'waiting' ? (
                    <>
                      Welcome to IntactBot FNOL System!<br />
                      Start by typing a message below or wait for the AI to begin.
                    </>
                  ) : (
                    <>
                      Conversation in progress...<br />
                      Messages will appear here as you chat with the AI.
                    </>
                  )}
                </PlaceholderText>
              </NoMessagesPlaceholder>
            ) : (
              <>
                {chatHistory.map((message, index) => (
                  <ChatMessage
                    key={index}
                    message={message}
                    isLatest={index === chatHistory.length - 1}
                  />
                ))}
                <div ref={messagesEndRef} />
              </>
            )}
          </MessagesContainer>

          <TextInputContainer>
            {/* Recording indicator */}
            {(isRecording || isPaused) && (
              <RecordingIndicator isRecording={isRecording && !isPaused}>
                <FaMicrophone />
                {isRecording && !isPaused ? 'Recording... Press Send to submit' : 'Recording paused - Press Send to submit'}
              </RecordingIndicator>
            )}
            
            <TextInputRow>
              <TextInput
                ref={textInputRef}
                value={textMessage}
                onChange={(e) => setTextMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={
                  isRecording || isPaused 
                    ? "Recording in progress - press Send to submit recording..."
                    : conversationTurn === 'ai_speaking' || conversationTurn === 'processing'
                    ? "Please wait while AI responds..."
                    : conversationTurn === 'user_turn' || conversationTurn === 'user_speaking'
                    ? "💡 Your turn - Recording will start automatically or type here..."
                    : "💡 Type your message here to start the conversation..."
                }
                disabled={isLoading || isTextSending || isRecording || isPaused || conversationTurn === 'ai_speaking' || conversationTurn === 'processing'}
              />
              <SendButton
                onClick={() => handleSendMessage()}
                disabled={(!textMessage.trim() && !isRecording && !isPaused) || isLoading || isTextSending || isProcessing || (conversationTurn === 'ai_speaking' && !isRecording && !isPaused)}
                isRecording={isRecording || isPaused}
              >
                <FaPaperPlane />
                {getSendButtonText()}
              </SendButton>
              {/* Only show manual recording control if not auto-recording */}
              {!isAutoRecordingPending && (
                <ToggleButton
                  onClick={handleToggleRecording}
                  disabled={isLoading || isProcessing}
                  isRecording={isRecording && !isPaused}
                >
                  <FaMicrophone />
                  {isRecording && !isPaused ? 'Pause' : isPaused ? 'Resume' : 'Record'}
                </ToggleButton>
              )}
            </TextInputRow>
          </TextInputContainer>
        </ChatBody>
      </LeftPanel>

      <PayloadDisplay
        payload={payload}
        isFormComplete={isFormComplete}
      />
    </ChatContainer>
  );
};

export default ChatInterface; 