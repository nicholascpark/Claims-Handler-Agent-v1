import React, { useState, useRef, useEffect, useCallback, useMemo, memo } from 'react';
import styled from 'styled-components';
import { FaTrash, FaEye, FaEyeSlash } from 'react-icons/fa';
import { toast } from 'react-toastify';

// Import optimized components
import PayloadDisplay from './PayloadDisplay';
import AudioControlsSection from './AudioControlsSection';
import MessagesList from './MessagesList';
import TextInputArea from './TextInputArea';
import useAudioRecording from '../hooks/useAudioRecording';
import { 
  playAudioImmediate, 
  stopAllAudio, 
  cacheAudio, 
  getCachedAudio,
  getAudioCacheStats 
} from '../utils/audioOptimization';
import { getLoadingSound } from '../utils/loadingSound';

const MainContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0;
  min-height: 70vh;
`;

const ChatContainer = styled.div`
  display: grid;
  grid-template-columns: ${props => props.$isChatVisible ? '1fr 560px' : '800px'};
  justify-content: center;
  gap: 24px;
  height: 60vh;
  min-height: 500px;
  transition: all 0.3s ease;
  
  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto;
    justify-content: normal;
  }
`;

const LeftPanel = styled.div`
  display: ${props => props.$isVisible ? 'flex' : 'none'};
  flex-direction: column;
  background: white;
  border-radius: 16px;
  border: 2px solid #e0e0e0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: all 0.3s ease;
  height: 100%;
  
  @media (max-width: 1200px) {
    display: ${props => props.$isVisible ? 'flex' : 'none'};
  }
`;

const ChatToggleContainer = styled.div`
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
`;

const ChatToggleButton = styled.button`
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 50%, #dee2e6 100%);
  color: #495057;
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 16px;
  padding: 14px 28px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 
    0 2px 8px rgba(0, 0, 0, 0.08),
    0 1px 2px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.6), transparent);
    transition: left 0.6s ease;
  }

  &:hover {
    background: linear-gradient(135deg, #ffffff 0%, #f1f3f4 50%, #e9ecef 100%);
    transform: translateY(-2px);
    box-shadow: 
      0 8px 25px rgba(0, 0, 0, 0.12),
      0 4px 8px rgba(0, 0, 0, 0.06),
      inset 0 1px 0 rgba(255, 255, 255, 0.95);
    border-color: rgba(255, 255, 255, 1);

    &::before {
      left: 100%;
    }
  }

  &:active {
    transform: translateY(-1px);
    box-shadow: 
      0 4px 12px rgba(0, 0, 0, 0.1),
      0 2px 4px rgba(0, 0, 0, 0.05),
      inset 0 1px 0 rgba(255, 255, 255, 0.9);
  }
`;

const PayloadWrapper = styled.div`
  width: ${props => props.$isChatVisible ? '560px' : '800px'};
  max-width: ${props => props.$isChatVisible ? '560px' : '800px'};
  transition: all 0.3s ease;
  
  @media (max-width: 1200px) {
    width: 100%;
    max-width: 100%;
  }
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
  min-height: 0;
  overflow: hidden;
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
  
  // Message queue state management
  const [messageQueue, setMessageQueue] = useState([]);
  const [isProcessingQueue, setIsProcessingQueue] = useState(false);
  const [processingQueueCount, setProcessingQueueCount] = useState(0);
  const [shouldInterruptProcessing, setShouldInterruptProcessing] = useState(false);
  const [currentAbortController, setCurrentAbortController] = useState(null);

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
    turnTimeoutRef,
    messageQueue,
    setMessageQueue,
    isProcessingQueue,
    setIsProcessingQueue,
    processingQueueCount,
    setProcessingQueueCount,
    shouldInterruptProcessing,
    setShouldInterruptProcessing,
    currentAbortController,
    setCurrentAbortController
  };
};

const ChatInterface = memo(({
  chatHistory = [],
  payload = {},
  isFormComplete = false,
  onSendMessage,
  onSendVoiceMessage,
  onReset,
  onUpdateChatHistory,
  isLoading = false,
  initialAudio
}) => {
  const [textMessage, setTextMessage] = useState('');
  const [isChatVisible, setIsChatVisible] = useState(false); // Default to hidden as requested

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
    turnTimeoutRef,
    messageQueue,
    setMessageQueue,
    isProcessingQueue,
    setIsProcessingQueue,
    processingQueueCount,
    setProcessingQueueCount,
    shouldInterruptProcessing,
    setShouldInterruptProcessing,
    currentAbortController,
    setCurrentAbortController
  } = conversationState;

  // Audio recording hook
  const {
    isRecording,
    isPaused,
    recordingTime,
    audioLevels,
    error: recordingError,
    toggleRecording,
    startRecording,
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

  // Manage conversation turn transitions with reduced delays
  useEffect(() => {
    if (conversationTurn === 'ai_speaking' && aiTextDisplayed && aiAudioComplete) {
      console.log('AI turn complete, transitioning to user turn');
      setConversationTurn('ai_complete');
      
      // Reduced delay for faster transitions
      const delay = Math.max(300, Math.min(800, (audioPlayStartTime ? Date.now() - audioPlayStartTime : 500) * 0.1));
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
      // Reduced safety timeout for more responsive system
      safetyTimeout = setTimeout(() => {
        console.log('Safety timeout: Forcing AI audio completion');
        setAiAudioComplete(true);
        setCurrentAudioData(null);
      }, 15000); // Reduced from 30 to 15 seconds
    }
    
    return () => {
      if (safetyTimeout) {
        clearTimeout(safetyTimeout);
      }
    };
  }, [conversationTurn, aiTextDisplayed, currentAudioData, setAiAudioComplete, setCurrentAudioData]);

  // Helper function to start loading sound
  const startLoadingSound = useCallback(async () => {
    try {
      console.log('Starting AI thinking sound');
      const loadingAudioData = await getLoadingSound();
      setCurrentAudioData(loadingAudioData);
      setIsPlayingLoadingSound(true);
      setAiAudioComplete(false);
    } catch (error) {
      console.error('Failed to load AI thinking sound:', error);
      // Fallback - just clear current audio
      setCurrentAudioData(null);
      setAiAudioComplete(true);
    }
  }, [setCurrentAudioData, setIsPlayingLoadingSound, setAiAudioComplete]);

  // Helper function to stop loading sound immediately
  const stopLoadingSound = useCallback((immediate = true) => {
    if (isPlayingLoadingSound || immediate) {
      console.log('Stopping AI thinking sound immediately');
      setIsPlayingLoadingSound(false);
      setCurrentAudioData(null);
      // Force stop any currently playing audio if immediate termination is requested
      if (immediate) {
        stopAllAudio(); // Use optimized audio stopping function
      }
    }
  }, [isPlayingLoadingSound, setIsPlayingLoadingSound, setCurrentAudioData]);

  // Audio handlers for playback control
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
      // AI thinking sound completed - restart for continuous feedback
      setTimeout(() => {
        // Use current state to check if still processing
        setConversationTurn(currentTurn => {
          console.log('Checking if still processing, current turn:', currentTurn);
          
          // Only restart thinking sound if we're still processing
          if (currentTurn === 'processing') {
            startLoadingSound();
          }
          return currentTurn; // Return unchanged
        });
      }, 10); // Minimal delay for immediate restart
    }
  }, [setAiAudioComplete, setCurrentAudioData, setConversationTurn, isPlayingLoadingSound, startLoadingSound, conversationTurn]);

  // Interrupt current processing with proper cleanup and immediate queue processing
  const interruptProcessing = useCallback(async () => {
    if (currentAbortController) {
      console.log('Interrupting current message processing for batching');
      setShouldInterruptProcessing(true);
      currentAbortController.abort();
      stopLoadingSound(true);
      
      // Wait a brief moment for cleanup to complete
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Reset processing states
      setIsProcessing(false);
      setIsProcessingQueue(false);
      setProcessingQueueCount(0);
      setConversationTurn('user_turn');
      
      console.log('Interruption complete - ready for immediate queue processing');
    }
  }, [currentAbortController, setShouldInterruptProcessing, stopLoadingSound, setIsProcessing, setIsProcessingQueue, setProcessingQueueCount, setConversationTurn]);

  // Message queue processing logic with proper gating
  const processMessageQueue = useCallback(async () => {
    // Enhanced gating to prevent concurrent processing
    if (isProcessingQueue || isProcessing || messageQueue.length === 0) {
      console.log('Skipping queue processing - already processing or no messages:', {
        isProcessingQueue,
        isProcessing,
        queueLength: messageQueue.length
      });
      return;
    }

    console.log('Starting queue processing for', messageQueue.length, 'messages');
    setIsProcessingQueue(true);
    setIsProcessing(true);
    setShouldInterruptProcessing(false);
    
    try {
      // Get all queued messages and track count for UI
      const messages = [...messageQueue];
      setProcessingQueueCount(messages.length); // Store count for UI display
      setMessageQueue([]); // Clear queue
      
      console.log(`Processing ${messages.length} queued messages:`, messages);
      
      setConversationTurn('processing');
      setIsAutoRecordingPending(false);

      // Start loading sound immediately and track processing start time
      const loadingStartTime = Date.now();
      window.processingStartTime = loadingStartTime;
      await startLoadingSound();

      // Create abort controller for interruption
      const abortController = new AbortController();
      setCurrentAbortController(abortController);

      try {
        // Send queued messages to backend for processing
        const response = await onSendMessage(messages, abortController.signal);
        
        // Check if processing was interrupted
        if (shouldInterruptProcessing || abortController.signal.aborted) {
          console.log('Message processing was interrupted');
          stopLoadingSound(true);
          return;
        }
        
        // Calculate if processing completed early - be more aggressive about early completion
        const loadingDuration = Date.now() - loadingStartTime;
        const completedEarly = response.completedEarly || 
                             (response.processing_time && (response.processing_time * 1000) < loadingDuration) || // Any completion faster than loading time
                             (loadingDuration < 2000); // Always consider completion under 2 seconds as early
        
        console.log(`Queue processing - Early completion: ${completedEarly}, Server time: ${response.processing_time}s, Loading time: ${(loadingDuration/1000).toFixed(2)}s, Cached: ${response.cached}`);
        
        // Stop loading sound immediately for any completion
        stopLoadingSound(true);
        
        if (response.audio_data) {
          // Cache the audio response for potential future use
          if (response.message) {
            cacheAudio(response.message, response.audio_data);
          }
          
          // Always use immediate playback for zero delay
          console.log('Using immediate audio playback for seamless transition');
          setConversationTurn('ai_speaking');
          setAiAudioComplete(false);
          
          // Play audio immediately without delay
          playAudioImmediate(
            response.audio_data,
            () => handleAudioPlay(),
            () => handleAudioEnd()
          ).catch(error => {
            console.error('Immediate audio playback failed:', error);
            // Fallback to regular audio handling
            setCurrentAudioData(response.audio_data);
          });
        } else {
          setCurrentAudioData(null);
          setAiAudioComplete(true);
        }
        
        // Show performance-aware success message
        const successMessage = response.cached 
          ? '⚡ Messages processed (cached response)!' 
          : completedEarly 
            ? `🚀 ${messages.length} messages processed (fast response)!` 
            : `${messages.length} messages processed successfully!`;
        toast.success(successMessage);
        
      } catch (error) {
        if (error.name === 'AbortError' || shouldInterruptProcessing || abortController.signal.aborted) {
          console.log('Message processing was interrupted by user - cleaning up gracefully');
          stopLoadingSound(true);
          setConversationTurn('user_turn');
          setCurrentAudioData(null);
          setAiAudioComplete(true);
          return; // Don't show error toast for intentional interruptions
        }
        
        console.error('Error processing message queue:', error);
        
        // Stop loading sound on error with immediate termination
        stopLoadingSound(true);
        setConversationTurn('user_turn');
        setCurrentAudioData(null);
        setAiAudioComplete(true);
        toast.error(`Failed to process messages: ${error.message}`);
      }
    } finally {
      setIsProcessingQueue(false);
      setIsProcessing(false);
      setProcessingQueueCount(0); // Clear processing count
      setCurrentAbortController(null);
      setShouldInterruptProcessing(false);
      console.log('Queue processing completed and states cleaned up');
    }
  }, [
    isProcessingQueue,
    isProcessing,
    messageQueue, 
    setMessageQueue, 
    onSendMessage, 
    setConversationTurn, 
    setIsAutoRecordingPending, 
    setCurrentAudioData, 
    setAiAudioComplete, 
    startLoadingSound, 
    stopLoadingSound, 
    shouldInterruptProcessing, 
    setIsProcessingQueue,
    setIsProcessing,
    setProcessingQueueCount,
    setShouldInterruptProcessing, 
    setCurrentAbortController,
    handleAudioPlay,
    handleAudioEnd
  ]);

  // Voice message handler
  const handleSendVoiceMessageLocal = useCallback(async (audioData) => {
    // Clear any pending message queue and interrupt processing for voice message
    if (messageQueue.length > 0) {
      console.log('Clearing message queue for voice message');
      setMessageQueue([]);
    }
    
    if (isProcessingQueue || isProcessing) {
      console.log('Interrupting current processing for voice message');
      await interruptProcessing();
    }
    
    setConversationTurn('processing');
    setIsAutoRecordingPending(false);
    
    // Start loading sound immediately and track processing start time
    const loadingStartTime = Date.now();
    window.processingStartTime = loadingStartTime; // Global tracking for audio handler
    await startLoadingSound();
    
    try {
      const response = await onSendVoiceMessage(audioData);
      
      // Calculate if processing completed early - be more aggressive about early completion
      const loadingDuration = Date.now() - loadingStartTime;
      const completedEarly = response.completedEarly || 
                           (response.processing_time && (response.processing_time * 1000) < loadingDuration) || // Any completion faster than loading time
                           (loadingDuration < 2000); // Always consider completion under 2 seconds as early
      
      console.log(`Voice processing - Early completion: ${completedEarly}, Server time: ${response.processing_time}s, Loading time: ${(loadingDuration/1000).toFixed(2)}s, Cached: ${response.cached}`);
      
      // Stop loading sound immediately for any completion
      stopLoadingSound(true);
      
      if (response.audio_data) {
        // Cache the audio response for potential future use
        if (response.message) {
          cacheAudio(response.message, response.audio_data);
        }
        
        // Always use immediate playback for zero delay
        console.log('Using immediate audio playback for seamless voice transition');
        setConversationTurn('ai_speaking');
        setAiAudioComplete(false);
        
        // Play audio immediately without delay
        playAudioImmediate(
          response.audio_data,
          () => handleAudioPlay(),
          () => handleAudioEnd()
        ).catch(error => {
          console.error('Immediate audio playback failed:', error);
          // Fallback to regular audio handling
          setCurrentAudioData(response.audio_data);
        });
      }
      
      return response;
    } catch (error) {
      console.error('Error sending voice message:', error);
      toast.error(`Failed to send voice message: ${error.message}`);
      
      // Stop loading sound on error with immediate termination
      stopLoadingSound(true);
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
  }, [onSendVoiceMessage, setConversationTurn, setIsAutoRecordingPending, setCurrentAudioData, setAiAudioComplete, setIsProcessing, startLoadingSound, stopLoadingSound, isProcessingQueue, isProcessing, interruptProcessing, handleAudioPlay, handleAudioEnd, messageQueue.length, setMessageQueue]);

  // Process message queue with immediate processing for responsive UI
  useEffect(() => {
    if (messageQueue.length > 0 && !isProcessingQueue && !isProcessing) {
      console.log(`Queue updated: ${messageQueue.length} messages - processing immediately for responsiveness`);
      
      // Reduced batching window for more immediate processing
      // Still allows batching for rapid successive inputs but reduces delay
      const batchTimeout = setTimeout(() => {
        if (messageQueue.length > 0 && !isProcessingQueue && !isProcessing) {
          console.log(`Processing batch of ${messageQueue.length} messages`);
          processMessageQueue();
        }
      }, 200); // Reduced from 750ms to 200ms for faster response
      
      return () => clearTimeout(batchTimeout);
    }
  }, [messageQueue.length, isProcessingQueue, isProcessing, processMessageQueue]);

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

  // Stop and send recording handler
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

  // Enhanced sendMessage handler with immediate UI feedback
  const handleSendMessage = useCallback(async (messageText = null) => {
    const message = messageText || textMessage.trim();
    
    // If we're currently recording, stop and send the voice message
    if (!message && (isRecording || isPaused)) {
      return await handleStopAndSend();
    }
    
    if (!message) return;
    
    setTextMessage('');

    // Immediately add user message to chat history for instant UI feedback
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
      isOptimistic: true // Flag to identify optimistic updates
    };
    
    // Update chat history immediately
    onUpdateChatHistory(prev => [...prev, userMessage]);

    // Add to queue for batch processing
    setMessageQueue(prev => {
      const newQueue = [...prev, message];
      console.log(`Added message to queue: ${newQueue.length} total messages:`, newQueue);
      return newQueue;
    });
    
    // If currently processing, interrupt to batch all messages
    if (isProcessingQueue || isProcessing) {
      console.log('Currently processing - interrupting to batch all messages');
      await interruptProcessing();
    }
    
  }, [textMessage, isRecording, isPaused, handleStopAndSend, setMessageQueue, isProcessingQueue, isProcessing, interruptProcessing, onUpdateChatHistory]);



  const handleToggleRecording = useCallback(async () => {
    try {
      // If AI is currently speaking, stop the audio output (works for both currentAudioData and playAudioImmediate)
      if (conversationTurn === 'ai_speaking') {
        console.log('Recording button clicked while AI is speaking - terminating AI audio');
        stopAllAudio(); // Stop all audio playback immediately
        setCurrentAudioData(null); // Clear current audio data
        setAiAudioComplete(true); // Mark AI audio as complete
        setConversationTurn('user_turn'); // Transition to user turn
        toast.info('🤐 AI audio stopped - your turn to speak!');
      }
      
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
  }, [isRecording, isPaused, textMessage, currentAudioData, conversationTurn, toggleRecording, setCurrentAudioData, setAiAudioComplete, setConversationTurn]);

  // Restart recording from scratch
  const handleStartOver = useCallback(async () => {
    try {
      // Stop any ongoing recording (if any)
      if (isRecording || isPaused) {
        await stopRecording();
      }
      // Start a fresh recording
      await startRecording();
    } catch (error) {
      toast.error(`Failed to restart recording: ${error.message}`);
    }
  }, [isRecording, isPaused, stopRecording, startRecording]);

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
    
    // If user starts typing while queue is processing, allow interruption
    if ((isProcessingQueue || isProcessing) && newValue.length > oldLength && newValue.trim()) {
      console.log('User typing while processing queue - preparing for interruption');
    }
  }, [textMessage.length, isRecording, isPaused, isProcessingQueue, isProcessing, setConversationTurn, setIsAutoRecordingPending]);

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
      setMessageQueue([]);
      setIsProcessingQueue(false);
      setProcessingQueueCount(0);
      setIsProcessing(false);
      await onReset();
    }
  }, [onReset, setConversationTurn, setAiTextDisplayed, setAiAudioComplete, setTurnTransitionDelay, setIsAutoRecordingPending, setCurrentAudioData, setLastAIMessage, setIsPlayingLoadingSound, setMessageQueue, setIsProcessingQueue, setProcessingQueueCount, setIsProcessing]);

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

  // Cleanup function - no longer needed for Tone.js
  useEffect(() => {
    return () => {
      console.log('Cleaning up chat interface');
    };
  }, []);

  // Performance monitoring (optional debug display)
  const [showPerformanceStats, setShowPerformanceStats] = useState(false);
  const [performanceStats, setPerformanceStats] = useState({});
  
  useEffect(() => {
    if (showPerformanceStats) {
      const interval = setInterval(() => {
        const audioStats = getAudioCacheStats();
        setPerformanceStats(audioStats);
      }, 1000);
      
      return () => clearInterval(interval);
    }
  }, [showPerformanceStats]);

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
    onManualRecordingTest: handleManualRecordingTest,
    // Audio control button handlers
    onSendRecording: handleStopAndSend,
    onToggleRecording: handleToggleRecording,
    onStartOver: handleStartOver
  }), [isRecording, isPaused, recordingTime, audioLevels, recordingError, availableDevices, selectedDeviceId, audioURL, conversationTurn, isProcessing, isInitialized, isAutoRecordingPending, handleDeviceChange, handleManualRecordingTest, handleStopAndSend, handleToggleRecording, handleStartOver]);

  // Memoized text input props
  const textInputProps = useMemo(() => ({
    textMessage,
    isRecording,
    isPaused,
    isLoading,
    isProcessingQueue,
    isProcessing,
    conversationTurn,
    isAutoRecordingPending,
    messageQueueLength: isProcessingQueue ? processingQueueCount : messageQueue.length,
    onTextChange: handleTextChange,
    onSendMessage: () => handleSendMessage(),
    onKeyPress: handleKeyPress,
    onToggleRecording: handleToggleRecording,
    onStartOver: handleStartOver,
    onStopRecording: handleStopRecording
  }), [textMessage, isRecording, isPaused, isLoading, isProcessingQueue, isProcessing, conversationTurn, isAutoRecordingPending, messageQueue.length, processingQueueCount, handleTextChange, handleSendMessage, handleKeyPress, handleToggleRecording, handleStartOver, handleStopRecording]);

  // Toggle chat visibility
  const toggleChatVisibility = useCallback(() => {
    setIsChatVisible(prev => !prev);
  }, []);

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

      {/* Chat Toggle Button - Always visible */}
      <ChatToggleContainer>
        <ChatToggleButton onClick={toggleChatVisibility}>
          {isChatVisible ? <FaEyeSlash /> : <FaEye />}
          {isChatVisible ? 'Hide Conversation History' : 'Show Conversation History'}
        </ChatToggleButton>
      </ChatToggleContainer>

      {/* Dual-pane layout */}
      <ChatContainer $isChatVisible={isChatVisible}>
        <LeftPanel $isVisible={isChatVisible}>
          <ChatHeader>
            <ChatTitle>💬 Conversation History</ChatTitle>
            <div style={{ display: 'flex', gap: '8px' }}>
              <ResetButton onClick={handleReset} disabled={isLoading}>
                <FaTrash />
                Clear Chat
              </ResetButton>
              <ResetButton 
                onClick={() => setShowPerformanceStats(!showPerformanceStats)}
                style={{ fontSize: '12px', padding: '4px 8px' }}
                title="Toggle performance statistics"
              >
                📊
              </ResetButton>
            </div>
          </ChatHeader>

          <ChatBody>
            <MessagesList 
              chatHistory={chatHistory} 
              conversationTurn={conversationTurn} 
            />
            {showPerformanceStats && (
              <div style={{
                padding: '8px',
                background: '#f8f9fa',
                border: '1px solid #dee2e6',
                borderRadius: '4px',
                margin: '8px',
                fontSize: '12px',
                fontFamily: 'monospace'
              }}>
                <strong>🚀 Performance Stats:</strong><br/>
                Audio Cache: {performanceStats.cacheSize || 0}/{performanceStats.maxCacheSize || 0} |
                Audio Pool: {performanceStats.poolSize || 0} |
                Active: {performanceStats.activeAudio || 0}
              </div>
            )}
          </ChatBody>
          <TextInputArea {...textInputProps} />
        </LeftPanel>

        <PayloadWrapper $isChatVisible={isChatVisible}>
          <PayloadDisplay
            payload={payload}
            isFormComplete={isFormComplete}
          />
        </PayloadWrapper>
      </ChatContainer>
    </MainContainer>
  );
});

ChatInterface.displayName = 'ChatInterface';

export default ChatInterface; 