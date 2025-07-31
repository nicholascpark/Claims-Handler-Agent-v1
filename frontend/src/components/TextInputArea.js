import React, { memo, useMemo, useCallback } from 'react';
import styled, { keyframes } from 'styled-components';
import { FaPaperPlane, FaMicrophone, FaRedo } from 'react-icons/fa';

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
  animation: ${props => props.$isRecording ? 'pulse 2s infinite' : 'none'};
  
  @keyframes pulse {
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
  }
`;

const TextInputContainer = styled.div`
  padding: 16px 20px;
  border-top: 1px solid #e0e0e0;
  background: #f8f9fa;
`;

const QueueIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  color: #007bff;
  font-weight: 600;
  background: rgba(0, 123, 255, 0.1);
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(0, 123, 255, 0.3);
  margin-bottom: 12px;
  animation: pulse 2s infinite;
  
  @keyframes pulse {
    0% {
      transform: scale(1);
      box-shadow: 0 0 0 0 rgba(0, 123, 255, 0.7);
    }
    50% {
      transform: scale(1.02);
      box-shadow: 0 0 0 10px rgba(0, 123, 255, 0);
    }
    100% {
      transform: scale(1);
      box-shadow: 0 0 0 0 rgba(0, 123, 255, 0);
    }
  }
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
  background: ${props => props.$isRecording ? '#ffc107' : '#dc3545'};
  color: ${props => props.$isRecording ? '#000' : 'white'};
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
  box-shadow: ${props => props.$isRecording ? '0 0 0 2px rgba(255, 193, 7, 0.5)' : 'none'};

  &:hover:not(:disabled) {
    background: ${props => props.$isRecording ? '#e0a800' : '#c82333'};
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

const ToggleButton = styled.button`
  background: ${props => props.$isRecording ? '#ffc107' : '#28a745'};
  color: ${props => props.$isRecording ? '#000' : 'white'};
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
    background: ${props => props.$isRecording ? '#e0a800' : '#218838'};
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

// Start Over button shares styles with ToggleButton but uses a neutral color scheme
const StartOverButton = styled.button`
  background: #6c757d;
  color: white;
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
    background: #5a6268;
    transform: translateY(-1px);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

const TextInputArea = memo(({
  textMessage,
  isRecording,
  isPaused,
  isLoading,
  isProcessingQueue,
  isProcessing,
  conversationTurn,
  isAutoRecordingPending,
  messageQueueLength = 0,
  onTextChange,
  onSendMessage,
  onKeyPress,
  onToggleRecording,
  onStartOver,
  onStopRecording
}) => {
  // Memoize placeholder text calculation
  const placeholderText = useMemo(() => {
    if (isProcessingQueue && messageQueueLength > 0) {
      return `🔄 Processing ${messageQueueLength} queued message(s)...`;
    }
    if (messageQueueLength > 0) {
      return `📝 ${messageQueueLength} message(s) queued - processing together...`;
    }
    if (conversationTurn === 'ai_speaking' || conversationTurn === 'processing') {
      return "⚡ Type your message while AI is responding (will interrupt and batch)...";
    }
    if (isRecording && !isPaused && !textMessage.trim()) {
      return "🎤 Recording in progress - start typing...";
    }
    if (isPaused && !textMessage.trim()) {
      return "⏸️ Recording paused - start typing to switch to text mode...";
    }
    if (conversationTurn === 'user_turn' || conversationTurn === 'user_speaking') {
      return "💡 Your turn - Type here or use Record button to start voice recording...";
    }
    return "💡 Type your message here to start the conversation...";
  }, [isRecording, isPaused, textMessage, conversationTurn, messageQueueLength, isProcessingQueue]);

  // Input is now always enabled to allow continuous typing
  const isInputDisabled = useMemo(() => {
    return false; // Keep input always enabled
  }, []);

  // Handle text change and stop recording if user starts typing
  const handleTextChange = useCallback((e) => {
    const newValue = e.target.value;
    onTextChange(e);
    
    // If user starts typing while recording, stop the recording completely
    if ((isRecording || isPaused) && newValue.length > textMessage.length) {
      // Only trigger when text is being added, not deleted
      onStopRecording();
    }
  }, [onTextChange, isRecording, isPaused, textMessage.length, onStopRecording]);

  // Allow sending messages at any time when there's content
  const isSendDisabled = useMemo(() => {
    return (!textMessage.trim() && !isRecording && !isPaused);
  }, [textMessage, isRecording, isPaused]);

  // Determine if we should show recording-specific UI or normal text input UI
  const showRecordingUI = useMemo(() => {
    return (isRecording || isPaused) && !textMessage.trim();
  }, [isRecording, isPaused, textMessage]);

  // Memoize send button text - updated for queue support
  const sendButtonText = useMemo(() => {
    if (showRecordingUI) {
      return isProcessing ? 'Sending...' : 'Send Recording';
    }
    if (isProcessingQueue) {
      return messageQueueLength > 0 ? 'Adding to Queue...' : 'Processing...';
    }
    return messageQueueLength > 0 ? `Send (${messageQueueLength + 1})` : 'Send';
  }, [showRecordingUI, isProcessing, isProcessingQueue, messageQueueLength]);

  // Memoize toggle button text
  const toggleButtonText = useMemo(() => {
    if (isRecording && !isPaused) return 'Pause';
    if (isPaused) return 'Resume';
    return 'Record';
  }, [isRecording, isPaused]);

  return (
    <TextInputContainer>
      {/* Recording indicator - only show when recording and no typed text */}
      {showRecordingUI && (
        <RecordingIndicator $isRecording={isRecording && !isPaused}>
          <FaMicrophone />
          {isRecording && !isPaused 
            ? 'Recording... Press Send to submit or start typing to switch modes' 
            : 'Recording paused - Press Send to submit or Resume to continue'
          }
        </RecordingIndicator>
      )}
      
      {/* Queue indicator - only show when messages are being queued or processed */}
      {(isProcessingQueue || messageQueueLength > 0) && (
        <QueueIndicator>
          <FaMicrophone />
          {isProcessingQueue 
            ? `🔄 Processing ${messageQueueLength} queued message(s)...` 
            : `📝 ${messageQueueLength} message(s) queued - processing together...`
          }
        </QueueIndicator>
      )}

      <TextInputRow>
        <TextInput
          value={textMessage}
          onChange={handleTextChange}
          onKeyPress={onKeyPress}
          placeholder={placeholderText}
          disabled={isInputDisabled}
        />
        
        <SendButton
          onClick={onSendMessage}
          disabled={isSendDisabled}
          $isRecording={showRecordingUI}
        >
          <FaPaperPlane />
          {sendButtonText}
        </SendButton>
        
        {/* Manual recording controls - always show when not auto-recording */}
        {!isAutoRecordingPending && (
          <>
            <ToggleButton
              onClick={onToggleRecording}
              disabled={isLoading || isProcessing}
              $isRecording={isRecording && !isPaused}
            >
              <FaMicrophone />
              {toggleButtonText}
            </ToggleButton>

            {/* Start Over appears only while recording or paused and no text typed */}
            {showRecordingUI && (
              <StartOverButton
                onClick={onStartOver}
                disabled={isLoading || isProcessing}
              >
                <FaRedo />
                Start Over
              </StartOverButton>
            )}
          </>
        )}
      </TextInputRow>
    </TextInputContainer>
  );
});

TextInputArea.displayName = 'TextInputArea';

export default TextInputArea; 