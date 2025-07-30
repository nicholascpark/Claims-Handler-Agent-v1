import React, { memo, useMemo } from 'react';
import styled, { keyframes } from 'styled-components';
import { FaPaperPlane, FaMicrophone } from 'react-icons/fa';

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

const TextInputArea = memo(({
  textMessage,
  isRecording,
  isPaused,
  isLoading,
  isTextSending,
  isProcessing,
  conversationTurn,
  isAutoRecordingPending,
  onTextChange,
  onSendMessage,
  onKeyPress,
  onToggleRecording
}) => {
  // Memoize placeholder text calculation
  const placeholderText = useMemo(() => {
    if (isRecording || isPaused) {
      return "Recording in progress - press Send to submit recording...";
    }
    if (conversationTurn === 'ai_speaking' || conversationTurn === 'processing') {
      return "Please wait while AI responds...";
    }
    if (conversationTurn === 'user_turn' || conversationTurn === 'user_speaking') {
      return "💡 Your turn - Recording will start automatically or type here...";
    }
    return "💡 Type your message here to start the conversation...";
  }, [isRecording, isPaused, conversationTurn]);

  // Memoize send button text
  const sendButtonText = useMemo(() => {
    if (isRecording || isPaused) {
      return isProcessing ? 'Sending...' : 'Send Recording';
    }
    return isTextSending ? 'Sending...' : 'Send';
  }, [isRecording, isPaused, isProcessing, isTextSending]);

  // Memoize toggle button text
  const toggleButtonText = useMemo(() => {
    if (isRecording && !isPaused) return 'Pause';
    if (isPaused) return 'Resume';
    return 'Record';
  }, [isRecording, isPaused]);

  // Memoize input disabled state
  const isInputDisabled = useMemo(() => {
    return isLoading || isTextSending || isRecording || isPaused || 
           conversationTurn === 'ai_speaking' || conversationTurn === 'processing';
  }, [isLoading, isTextSending, isRecording, isPaused, conversationTurn]);

  // Memoize send button disabled state
  const isSendDisabled = useMemo(() => {
    return (!textMessage.trim() && !isRecording && !isPaused) || 
           isLoading || isTextSending || isProcessing || 
           (conversationTurn === 'ai_speaking' && !isRecording && !isPaused);
  }, [textMessage, isRecording, isPaused, isLoading, isTextSending, isProcessing, conversationTurn]);

  return (
    <TextInputContainer>
      {/* Recording indicator */}
      {(isRecording || isPaused) && (
        <RecordingIndicator $isRecording={isRecording && !isPaused}>
          <FaMicrophone />
          {isRecording && !isPaused 
            ? 'Recording... Press Send to submit' 
            : 'Recording paused - Press Send to submit'
          }
        </RecordingIndicator>
      )}
      
      <TextInputRow>
        <TextInput
          value={textMessage}
          onChange={onTextChange}
          onKeyPress={onKeyPress}
          placeholder={placeholderText}
          disabled={isInputDisabled}
        />
        
        <SendButton
          onClick={onSendMessage}
          disabled={isSendDisabled}
          $isRecording={isRecording || isPaused}
        >
          <FaPaperPlane />
          {sendButtonText}
        </SendButton>
        
        {/* Only show manual recording control if not auto-recording */}
        {!isAutoRecordingPending && (
          <ToggleButton
            onClick={onToggleRecording}
            disabled={isLoading || isProcessing}
            $isRecording={isRecording && !isPaused}
          >
            <FaMicrophone />
            {toggleButtonText}
          </ToggleButton>
        )}
      </TextInputRow>
    </TextInputContainer>
  );
});

TextInputArea.displayName = 'TextInputArea';

export default TextInputArea; 