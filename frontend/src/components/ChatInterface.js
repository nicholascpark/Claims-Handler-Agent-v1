import React, { useState, useRef, useEffect, useCallback, useMemo, memo } from 'react';
import styled from 'styled-components';
import { FaTrash } from 'react-icons/fa';
import { toast } from 'react-toastify';

// Import optimized components
import PayloadDisplay from './PayloadDisplay';
import AudioControlsSection from './AudioControlsSection';
import MessagesList from './MessagesList';
import TextInputArea from './TextInputArea';
import useAudioRecording from '../hooks/useAudioRecording';
import { getLoadingSound } from '../utils/loadingSound';

const MainContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0;
  min-height: 70vh;
`;

const ChatContainer = styled.div`
  display: grid;
  grid-template-columns: 1fr 560px;
  gap: 24px;
  min-height: 60vh;
  
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

// Custom hook for conversation state management
const useConversationState = (initialAudio) => {
  const [conversationTurn, setConversationTurn] = useState('waiting');
  const [aiTextDisplayed, setAiTextDisplayed] = useState(false);
  const [aiAudioComplete, setAiAudioComplete] = useState(false);
  const [turnTransitionDelay, setTurnTransitionDelay] = useState(null);
  const [isAutoRecordingPending, setIsAutoRecordingPending] = useState(false);
  const [audioPlayStartTime, setAudioPlayStartTime] = useState(null);
  const [lastAIMessage, setLastAIMessage] = useState(null);
  const [currentAudioData, setCurrentAudioData] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPlayingLoadingSound, setIsPlayingLoadingSound] = useState(false);

  const turnTimeoutRef = useRef(null);

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

  return {
    conversationTurn,
    setConversationTurn,
    aiTextDisplayed,
    setAiTextDisplayed,
    aiAudioComplete,
    setAiAudioComplete,
    turnTransitionDelay,
    setTurnTransitionDelay,
    isAutoRecordingPending,
    setIsAutoRecordingPending,
    audioPlayStartTime,
    setAudioPlayStartTime,
    lastAIMessage,
    setLastAIMessage,
    currentAudioData,
    setCurrentAudioData,
    isProcessing,
    setIsProcessing,
    isPlayingLoadingSound,
    setIsPlayingLoadingSound,
    turnTimeoutRef
  };
};

const ChatInterface = memo(({
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

  // Use custom hook for conversation state
  const conversationState = useConversationState(initialAudio);
  const {
    conversationTurn,
    setConversationTurn,
    aiTextDisplayed,
    setAiTextDisplayed,
    aiAudioComplete,
    setAiAudioComplete,
    turnTransitionDelay,
    setTurnTransitionDelay,
    isAutoRecordingPending,
    setIsAutoRecordingPending,
    audioPlayStartTime,
    setAudioPlayStartTime,
    lastAIMessage,
    setLastAIMessage,
    currentAudioData,
    setCurrentAudioData,
    isProcessing,
    setIsProcessing,
    isPlayingLoadingSound,
    setIsPlayingLoadingSound,
    turnTimeoutRef
  } = conversationState;

  // Audio recording hook
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

  // Detect new AI messages and start AI turn
  useEffect(() => {
    if (chatHistory.length > 0) {
      const lastMessage = chatHistory[chatHistory.length - 1];
      if (lastMessage.role === 'assistant' && lastMessage !== lastAIMessage) {
        console.log('New AI message detected, starting AI turn');
        setLastAIMessage(lastMessage);
        setConversationTurn('ai_speaking');
        setAiTextDisplayed(true);
        setAiAudioComplete(false);
        setTurnTransitionDelay(null);
      }
    }
  }, [chatHistory, lastAIMessage, setLastAIMessage, setConversationTurn, setAiTextDisplayed, setAiAudioComplete, setTurnTransitionDelay]);

  // Auto-start recording helper function
  const startAutoRecording = useCallback(async () => {
    try {
      console.log('=== Auto-starting recording ===');
      console.log('Current states:', {
        isInitialized,
        isRecording,
        isPaused,
        isProcessing,
        conversationTurn,
        isAutoRecordingPending
      });
      
      // Double-check initialization before attempting to record
      if (!isInitialized) {
        console.log('Audio recording not initialized, attempting to initialize...');
        toast.info('Initializing microphone...');
        // The toggleRecording function will handle initialization
      }
      
      console.log('About to call toggleRecording...');
      const result = await toggleRecording();
      console.log('toggleRecording result:', result);
      
      setConversationTurn('user_speaking');
      setIsAutoRecordingPending(false);
      toast.success('🎤 Your turn - speak now!');
      console.log('Auto-recording started successfully');
    } catch (error) {
      console.error('Auto-recording failed:', error);
      console.error('Error details:', {
        message: error.message,
        stack: error.stack,
        isInitialized,
        isRecording,
        isPaused
      });
      toast.error(`Auto-recording failed: ${error.message}`);
      setConversationTurn('user_turn');
      setIsAutoRecordingPending(false);
    }
  }, [toggleRecording, setConversationTurn, setIsAutoRecordingPending, isInitialized, isRecording, isPaused, isProcessing, conversationTurn, isAutoRecordingPending]);

  // Manage conversation turn transitions
  useEffect(() => {
    if (conversationTurn === 'ai_speaking' && aiTextDisplayed && aiAudioComplete) {
      console.log('AI turn complete, transitioning to user turn');
      setConversationTurn('ai_complete');
      
      const delay = Math.max(800, Math.min(1500, (audioPlayStartTime ? Date.now() - audioPlayStartTime : 1000) * 0.15));
      setTurnTransitionDelay(delay);
      
      turnTimeoutRef.current = setTimeout(() => {
        console.log('Timeout: Setting conversation turn to user_turn and isAutoRecordingPending to true');
        setConversationTurn('user_turn');
        setIsAutoRecordingPending(true);
        
        // Let the useEffect handle auto-recording after state updates
      }, delay);
    }
  }, [conversationTurn, aiTextDisplayed, aiAudioComplete, audioPlayStartTime, isInitialized, isRecording, isPaused, isProcessing, startAutoRecording, setConversationTurn, setTurnTransitionDelay, setIsAutoRecordingPending]);

  // Safety timeout to handle cases where audio events might not fire properly
  useEffect(() => {
    let safetyTimeout;
    
    if (conversationTurn === 'ai_speaking' && aiTextDisplayed && currentAudioData) {
      // Set a safety timeout of 30 seconds to force transition if audio doesn't complete
      safetyTimeout = setTimeout(() => {
        console.log('Safety timeout: Forcing AI audio completion');
        setAiAudioComplete(true);
        setCurrentAudioData(null);
      }, 30000); // 30 second safety timeout
    }
    
    return () => {
      if (safetyTimeout) {
        clearTimeout(safetyTimeout);
      }
    };
  }, [conversationTurn, aiTextDisplayed, currentAudioData, setAiAudioComplete, setCurrentAudioData]);

  // Handle user turn when conditions change
  useEffect(() => {
    console.log('Auto-recording effect triggered:', {
      conversationTurn,
      isInitialized,
      isRecording,
      isPaused,
      isProcessing,
      isAutoRecordingPending
    });
    
    if (conversationTurn === 'user_turn' && isInitialized && !isRecording && !isPaused && !isProcessing && isAutoRecordingPending) {
      console.log('Conditions met - starting auto-recording');
      startAutoRecording();
    }
  }, [conversationTurn, isInitialized, isRecording, isPaused, isProcessing, isAutoRecordingPending, startAutoRecording]);

  // Helper function to start loading sound
  const startLoadingSound = useCallback(async () => {
    try {
      const loadingAudioData = await getLoadingSound();
      setCurrentAudioData(loadingAudioData);
      setIsPlayingLoadingSound(true);
      setAiAudioComplete(false);
    } catch (error) {
      console.error('Failed to load loading sound:', error);
      // Fallback - just clear current audio
      setCurrentAudioData(null);
      setAiAudioComplete(true);
    }
  }, [setCurrentAudioData, setIsPlayingLoadingSound, setAiAudioComplete]);

  // Helper function to stop loading sound
  const stopLoadingSound = useCallback(() => {
    if (isPlayingLoadingSound) {
      console.log('Stopping loading sound');
      setIsPlayingLoadingSound(false);
      setCurrentAudioData(null);
      // Don't set aiAudioComplete here - let the actual AI response audio handle this
    }
  }, [isPlayingLoadingSound, setIsPlayingLoadingSound, setCurrentAudioData]);

  // Memoized handlers to prevent unnecessary re-renders
  const handleSendMessage = useCallback(async (messageText = null) => {
    const message = messageText || textMessage.trim();
    if (!message && !isRecording && !isPaused) return;

    // If we're currently recording, stop and send the voice message
    if (isRecording || isPaused) {
      return await handleStopAndSend();
    }

    if (!message) return;
    
    setTextMessage('');
    setIsTextSending(true);
    setConversationTurn('processing');
    setIsAutoRecordingPending(false);

    // Start loading sound immediately
    await startLoadingSound();

    try {
      const response = await onSendMessage(message);
      
      // Stop loading sound and play AI response
      stopLoadingSound();
      
      if (response.audio_data) {
        setCurrentAudioData(response.audio_data);
        setAiAudioComplete(false);
        setConversationTurn('ai_speaking');
      } else {
        setCurrentAudioData(null);
        setAiAudioComplete(true);
      }
      
      toast.success('Message sent successfully!');
    } catch (error) {
      console.error('Error sending text message:', error);
      
      // Stop loading sound on error
      stopLoadingSound();
      setConversationTurn('user_turn');
      setCurrentAudioData(null);
      setAiAudioComplete(true);
    } finally {
      setIsTextSending(false);
    }
  }, [textMessage, isRecording, isPaused, onSendMessage, setConversationTurn, setIsAutoRecordingPending, setCurrentAudioData, setAiAudioComplete, startLoadingSound, stopLoadingSound]);

  const handleSendVoiceMessageLocal = useCallback(async (audioData) => {
    setConversationTurn('processing');
    setIsAutoRecordingPending(false);
    
    // Start loading sound immediately
    await startLoadingSound();
    
    try {
      const response = await onSendVoiceMessage(audioData);
      
      // Stop loading sound and play AI response
      stopLoadingSound();
      
      if (response.audio_data) {
        setCurrentAudioData(response.audio_data);
        setAiAudioComplete(false);
        setConversationTurn('ai_speaking');
      }
      
      return response;
    } catch (error) {
      console.error('Error sending voice message:', error);
      toast.error(`Failed to send voice message: ${error.message}`);
      
      // Stop loading sound on error
      stopLoadingSound();
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
  }, [onSendVoiceMessage, setConversationTurn, setIsAutoRecordingPending, setCurrentAudioData, setAiAudioComplete, setIsProcessing, startLoadingSound, stopLoadingSound]);

  const handleStopAndSend = useCallback(async () => {
    if (!isRecording && !isPaused) {
      toast.warning('No recording to send.');
      return;
    }

    setIsProcessing(true);
    try {
      console.log('🎤 Stopping recording and waiting for blob...');
      const audioBlob = await stopRecording();
      
      if (!audioBlob) {
        throw new Error('No audio blob returned from stopRecording');
      }
      
      const audioData = await getBase64Audio(audioBlob);
      await handleSendVoiceMessageLocal(audioData);
      toast.success('🎤 Voice message sent successfully!');
    } catch (error) {
      console.error('Error sending voice message:', error);
      toast.error(`Failed to send voice message: ${error.message}`);
      
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
  }, [isRecording, isPaused, stopRecording, getBase64Audio, handleSendVoiceMessageLocal, setIsProcessing, setCurrentAudioData, setAiAudioComplete, setConversationTurn]);

  const handleToggleRecording = useCallback(async () => {
    try {
      // If we have text content and are starting recording, clear the text
      if (!isRecording && !isPaused && textMessage.trim()) {
        setTextMessage('');
      }
      
      if (!isRecording && !isPaused && currentAudioData) {
        setCurrentAudioData(null);
        setAiAudioComplete(true);
      }
      await toggleRecording();
    } catch (error) {
      toast.error(`Recording error: ${error.message}`);
    }
  }, [isRecording, isPaused, textMessage, currentAudioData, toggleRecording, setCurrentAudioData, setAiAudioComplete]);

  // Restart recording from scratch
  const handleStartOver = useCallback(async () => {
    try {
      // Stop any ongoing recording (if any)
      if (isRecording || isPaused) {
        await stopRecording();
      }
      // Start a fresh recording
      await toggleRecording();
    } catch (error) {
      toast.error(`Failed to restart recording: ${error.message}`);
    }
  }, [isRecording, isPaused, stopRecording, toggleRecording]);

  // Stop recording without restarting (for typing override)
  const handleStopRecording = useCallback(async () => {
    try {
      if (isRecording || isPaused) {
        await stopRecording();
        setConversationTurn('user_turn');
        setIsAutoRecordingPending(false);
      }
    } catch (error) {
      console.error('Failed to stop recording:', error);
    }
  }, [isRecording, isPaused, stopRecording, setConversationTurn, setIsAutoRecordingPending]);

  const handleTextChange = useCallback((e) => {
    const newValue = e.target.value;
    const oldLength = textMessage.length;
    
    setTextMessage(newValue);
    
    // If user starts typing while recording or paused, update conversation state
    if ((isRecording || isPaused) && newValue.length > oldLength && newValue.trim()) {
      // User is typing over recording - transition to normal text input mode
      setConversationTurn('user_turn');
      setIsAutoRecordingPending(false);
    }
  }, [textMessage.length, isRecording, isPaused, setConversationTurn, setIsAutoRecordingPending]);

  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  const handleReset = useCallback(async () => {
    if (window.confirm('Are you sure you want to reset the conversation? This will clear all chat history and payload data.')) {
      if (turnTimeoutRef.current) {
        clearTimeout(turnTimeoutRef.current);
        turnTimeoutRef.current = null;
      }
      
      setConversationTurn('waiting');
      setAiTextDisplayed(false);
      setAiAudioComplete(false);
      setTurnTransitionDelay(null);
      setIsAutoRecordingPending(false);
      setCurrentAudioData(null);
      setLastAIMessage(null);
      setIsPlayingLoadingSound(false);
      await onReset();
    }
  }, [onReset, setConversationTurn, setAiTextDisplayed, setAiAudioComplete, setTurnTransitionDelay, setIsAutoRecordingPending, setCurrentAudioData, setLastAIMessage, setIsPlayingLoadingSound]);

  const handleAudioPlay = useCallback(() => {
    console.log('AI audio started playing');
    setAudioPlayStartTime(Date.now());
  }, [setAudioPlayStartTime]);

  const handleAudioEnd = useCallback(() => {
    console.log('AI audio finished playing');
    console.log('isPlayingLoadingSound:', isPlayingLoadingSound);
    console.log('conversationTurn:', conversationTurn);
    
    // If we're in ai_speaking state, this should be the AI response audio finishing
    if (conversationTurn === 'ai_speaking' || !isPlayingLoadingSound) {
      // AI response audio completed - clear it and mark as complete
      console.log('Marking AI audio as complete');
      setAiAudioComplete(true);
      setCurrentAudioData(null);
    } else if (isPlayingLoadingSound && conversationTurn === 'processing') {
      // Loading sound completed - restart it if still processing
      setTimeout(() => {
        // Use current state to check if still processing
        setConversationTurn(currentTurn => {
          console.log('Checking if still processing, current turn:', currentTurn);
          if (currentTurn === 'processing') {
            startLoadingSound();
          }
          return currentTurn; // Return unchanged
        });
      }, 100); // 100ms delay between loading sound repetitions for seamless continuity
    }
  }, [setAiAudioComplete, setCurrentAudioData, setConversationTurn, isPlayingLoadingSound, startLoadingSound, conversationTurn]);

  const handleDeviceChange = useCallback(async (e) => {
    const deviceId = e.target.value;
    try {
      await changeDevice(deviceId);
      toast.success('Microphone changed successfully!');
    } catch (error) {
      toast.error(`Failed to change microphone: ${error.message}`);
    }
  }, [changeDevice]);

  const handleManualRecordingTest = useCallback(async () => {
    try {
      console.log('=== Manual Recording Test ===');
      console.log('Current states before test:', {
        isInitialized,
        isRecording,
        isPaused,
        conversationTurn
      });
      
      toast.info('Testing microphone access...');
      await toggleRecording();
      
      if (!isRecording) {
        toast.success('Manual recording test successful! Microphone is working.');
      }
    } catch (error) {
      console.error('Manual recording test failed:', error);
      toast.error(`Manual test failed: ${error.message}`);
    }
  }, [toggleRecording, isInitialized, isRecording, isPaused, conversationTurn]);

  const runDiagnostics = useCallback(async () => {
    console.log('=== AUDIO DIAGNOSTICS ===');
    
    // Check browser capabilities
    console.log('Browser capabilities:', {
      hasGetUserMedia: !!navigator.mediaDevices?.getUserMedia,
      hasMediaRecorder: !!window.MediaRecorder,
      hasAudioContext: !!(window.AudioContext || window.webkitAudioContext)
    });
    
    // Check current permissions
    try {
      const permissionStatus = await navigator.permissions.query({ name: 'microphone' });
      console.log('Microphone permission:', permissionStatus.state);
    } catch (e) {
      console.log('Permission query not supported');
    }
    
    // Check available devices
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = devices.filter(d => d.kind === 'audioinput');
      console.log('Available audio input devices:', audioInputs.length);
      audioInputs.forEach((device, index) => {
        console.log(`  Device ${index}:`, device.label || 'Unknown', device.deviceId);
      });
    } catch (e) {
      console.error('Failed to enumerate devices:', e);
    }
    
    // Check hook states
    console.log('Recording hook states:', {
      isInitialized,
      isRecording,
      isPaused,
      recordingError,
      availableDevices: availableDevices.length,
      selectedDeviceId
    });
    
    // Check conversation states
    console.log('Conversation states:', {
      conversationTurn,
      isAutoRecordingPending,
      isProcessing,
      aiTextDisplayed,
      aiAudioComplete
    });
    
    console.log('=== END DIAGNOSTICS ===');
  }, [isInitialized, isRecording, isPaused, recordingError, availableDevices, selectedDeviceId, conversationTurn, isAutoRecordingPending, isProcessing, aiTextDisplayed, aiAudioComplete]);

  // Run diagnostics on mount and when key states change
  useEffect(() => {
    runDiagnostics();
  }, [conversationTurn, isAutoRecordingPending]);

  // Memoized voice controls props
  const voiceControlsProps = useMemo(() => ({
    isRecording,
    isPaused,
    recordingTime,
    audioLevels,
    error: recordingError,
    availableDevices,
    selectedDeviceId,
    audioURL,
    conversationTurn,
    isProcessing,
    isInitialized,
    isAutoRecordingPending,
    onDeviceChange: handleDeviceChange,
    onManualRecordingTest: handleManualRecordingTest
  }), [isRecording, isPaused, recordingTime, audioLevels, recordingError, availableDevices, selectedDeviceId, audioURL, conversationTurn, isProcessing, isInitialized, isAutoRecordingPending, handleDeviceChange, handleManualRecordingTest]);

  // Memoized text input props
  const textInputProps = useMemo(() => ({
    textMessage,
    isRecording,
    isPaused,
    isLoading,
    isTextSending,
    isProcessing,
    conversationTurn,
    isAutoRecordingPending,
    onTextChange: handleTextChange,
    onSendMessage: () => handleSendMessage(),
    onKeyPress: handleKeyPress,
    onToggleRecording: handleToggleRecording,
    onStartOver: handleStartOver,
    onStopRecording: handleStopRecording
  }), [textMessage, isRecording, isPaused, isLoading, isTextSending, isProcessing, conversationTurn, isAutoRecordingPending, handleTextChange, handleSendMessage, handleKeyPress, handleToggleRecording, handleStartOver, handleStopRecording]);

  return (
    <MainContainer>
      {/* Audio Controls Section - Above the dual-pane layout */}
      <AudioControlsSection 
        conversationTurn={conversationTurn}
        turnTransitionDelay={turnTransitionDelay}
        isAutoRecordingPending={isAutoRecordingPending}
        currentAudioData={currentAudioData}
        onAudioPlay={handleAudioPlay}
        onAudioEnd={handleAudioEnd}
        voiceControlsProps={voiceControlsProps}
      />

      {/* Dual-pane layout */}
      <ChatContainer>
        <LeftPanel>
          <ChatHeader>
            <ChatTitle>💬 Conversation History</ChatTitle>
            <ResetButton onClick={handleReset} disabled={isLoading}>
              <FaTrash />
              Clear Chat
            </ResetButton>
          </ChatHeader>

          <ChatBody>
            <MessagesList 
              chatHistory={chatHistory} 
              conversationTurn={conversationTurn} 
            />
            <TextInputArea {...textInputProps} />
          </ChatBody>
        </LeftPanel>

        <PayloadDisplay
          payload={payload}
          isFormComplete={isFormComplete}
        />
      </ChatContainer>
    </MainContainer>
  );
});

ChatInterface.displayName = 'ChatInterface';

export default ChatInterface; 