import React, { useState, useEffect, useRef } from 'react';
import styled, { keyframes, css } from 'styled-components';
import { FaMicrophone, FaPause, FaPlay, FaStop } from 'react-icons/fa';
import { toast } from 'react-toastify';

import useAudioRecording from '../hooks/useAudioRecording';
import SoundWaveVisualizer from './SoundWaveVisualizer';

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

const ButtonsContainer = styled.div`
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: center;
  margin-top: 16px;
`;

const ControlButton = styled.button`
  background: ${props => {
    if (props.variant === 'record' && !props.disabled) {
      if (props.isPaused) return '#ffc107';
      return '#28a745';
    }
    if (props.variant === 'stop' && props.active) return '#dc3545';
    if (props.variant === 'stop') return '#6c757d';
    return '#dc3545';
  }};
  color: ${props => (props.variant === 'record' && props.isPaused) ? '#000' : 'white'};
  border: 2px solid ${props => {
    if (props.variant === 'record' && !props.disabled) {
      if (props.isPaused) return '#ffc107';
      return '#28a745';
    }
    if (props.variant === 'stop' && props.active) return '#dc3545';
    if (props.variant === 'stop') return '#6c757d';
    return '#dc3545';
  }};
  border-radius: 12px;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: ${props => props.disabled ? 'not-allowed' : 'pointer'};
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 140px;
  justify-content: center;
  position: relative;
  overflow: hidden;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
    
    ${props => {
      if (props.variant === 'record' && !props.disabled) {
        if (props.isPaused) return 'background: #e0a800; border-color: #e0a800;';
        return 'background: #218838; border-color: #218838;';
      }
      if (props.variant === 'stop' && props.active) return 'background: #c82333; border-color: #c82333;';
      if (props.variant === 'stop') return 'background: #5a6268; border-color: #5a6268;';
      return 'background: #c82333; border-color: #c82333;';
    }}
  }

  &:active:not(:disabled) {
    transform: translateY(0);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  }

  &:disabled {
    opacity: 0.6;
    transform: none !important;
    box-shadow: none !important;
  }

  ${props => props.isRecording && css`
    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: -100%;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
      animation: shimmer 2s infinite;
    }
  `}
`;

const AutoRecordingNotification = styled.div`
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border: 2px solid #2196f3;
  border-radius: 12px;
  padding: 12px 16px;
  margin: 12px 0;
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

const ErrorMessage = styled.div`
  background: #ffebee;
  border: 1px solid #f44336;
  border-radius: 8px;
  padding: 12px;
  color: #c62828;
  margin: 8px 0;
  font-weight: 500;
`;

const VoiceRecording = ({ 
  onVoiceMessage, 
  isDisabled = false, 
  autoStartAfterAI = false,
  onRecordingStateChange 
}) => {
  const {
    isRecording,
    isPaused,
    recordingTime,
    audioLevels,
    error: recordingError,
    toggleRecording,
    stopRecording,
    getBase64Audio,
    cleanup,
    isInitialized,
    audioURL
  } = useAudioRecording();

  const [isProcessing, setIsProcessing] = useState(false);
  const [showAutoRecordingNotification, setShowAutoRecordingNotification] = useState(false);
  const [autoRecordingCountdown, setAutoRecordingCountdown] = useState(0);
  const [hasAutoStarted, setHasAutoStarted] = useState(false);
  const autoStartTimeoutRef = useRef(null);
  const countdownIntervalRef = useRef(null);

  // Notify parent of recording state changes
  useEffect(() => {
    if (onRecordingStateChange) {
      onRecordingStateChange({
        isRecording,
        isPaused,
        isProcessing,
        recordingTime
      });
    }
  }, [isRecording, isPaused, isProcessing, recordingTime, onRecordingStateChange]);

  // Auto-start recording on component mount
  useEffect(() => {
    if (!hasAutoStarted && !isDisabled && !isProcessing && isInitialized) {
      setHasAutoStarted(true);

      autoStartTimeoutRef.current = setTimeout(async () => {
        if (!isRecording && !isPaused && !isDisabled) {
          try {
            await toggleRecording();
            toast.success('🎤 Recording started automatically!');
          } catch (error) {
            toast.error(`Recording error: ${error.message}`);
          }
        }
      }, 500);
    }

    return () => {
      if (autoStartTimeoutRef.current) {
        clearTimeout(autoStartTimeoutRef.current);
      }
    };
  }, [hasAutoStarted, isDisabled, isProcessing, isInitialized, isRecording, isPaused, toggleRecording]);

  // Auto-start recording after AI response (existing functionality)
  useEffect(() => {
    if (autoStartAfterAI && !isRecording && !isPaused && !isProcessing && hasAutoStarted) {
      autoStartTimeoutRef.current = setTimeout(async () => {
        if (!isRecording && !isPaused) {
          try {
            await toggleRecording();
            toast.success('🎤 Auto-recording resumed!');
          } catch (error) {
            toast.error(`Recording error: ${error.message}`);
          }
        }
      }, 500);
    }

    return () => {
      if (autoStartTimeoutRef.current) {
        clearTimeout(autoStartTimeoutRef.current);
      }
    };
  }, [autoStartAfterAI, isRecording, isPaused, isProcessing, toggleRecording, hasAutoStarted]);

  const handleToggleRecording = async () => {
    try {
      await toggleRecording();
    } catch (error) {
      toast.error(`Recording error: ${error.message}`);
    }
  };

  const handleStopAndSend = async () => {
    if (!isRecording && !isPaused) {
      toast.warning('No recording to send.');
      return;
    }

    setIsProcessing(true);
    try {
      await stopRecording();
      
      // Small delay to ensure recording is stopped
      setTimeout(async () => {
        try {
          const audioData = await getBase64Audio();
          await onVoiceMessage(audioData);
          toast.success('🎤 Voice message sent successfully!');
        } catch (error) {
          console.error('Error sending voice message:', error);
          
          // Provide specific error messages based on the error type
          if (error.message.includes('No audio recorded') || error.message.includes('Audio blob is empty')) {
            toast.error('No audio detected. Please check your microphone permissions and try speaking closer to the microphone.');
          } else if (error.message.includes('Audio conversion failed')) {
            toast.error('Audio processing failed. Please try recording again.');
          } else if (error.message.includes('Base64 conversion failed')) {
            toast.error('Audio encoding failed. Please try recording again.');
          } else {
            toast.error(`Failed to send voice message: ${error.message}`);
          }
        } finally {
          setIsProcessing(false);
        }
      }, 100);
    } catch (error) {
      setIsProcessing(false);
      console.error('Error processing recording:', error);
      
      if (error.message.includes('No audio')) {
        toast.error('Recording failed - no audio detected. Please check your microphone and try again.');
      } else {
        toast.error(`Error processing recording: ${error.message}`);
      }
    }
  };

  const getRecordButtonText = () => {
    if (isProcessing) return 'Processing...';
    if (!isRecording && !isPaused) return '▶️ Resume Recording';
    if (isPaused) return '▶️ Resume';
    return '⏸️ Pause';
  };

  const getStopButtonText = () => {
    if (isProcessing) return 'Sending...';
    return '⏹️ Stop & Send';
  };

  const getStatusText = () => {
    if (isProcessing) return 'Processing voice message...';
    if (isRecording && !isPaused) return 'Recording in progress';
    if (isPaused) return 'Recording paused - Press Resume to continue';
    if (!isInitialized) return 'Initializing microphone...';
    if (!hasAutoStarted) return 'Preparing to start recording...';
    return 'Ready to record';
  };

  const handleStartRecording = async () => {
    try {
      await toggleRecording();
    } catch (error) {
      toast.error(`Recording error: ${error.message}`);
    }
  };

  return (
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

      {showAutoRecordingNotification && (
        <AutoRecordingNotification>
          🤖 Recording will start in {autoRecordingCountdown} seconds...
        </AutoRecordingNotification>
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

      <ButtonsContainer>
        {/* Always show record/pause/resume button when initialized or recording */}
        {(isInitialized || isRecording || isPaused) && (
          <ControlButton
            variant="record"
            onClick={isRecording || isPaused ? handleToggleRecording : handleStartRecording}
            disabled={isDisabled || isProcessing}
            isPaused={isPaused}
            isRecording={isRecording && !isPaused}
          >
            {!isRecording && !isPaused ? (
              <FaMicrophone />
            ) : isPaused ? (
              <FaPlay />
            ) : (
              <FaPause />
            )}
            {getRecordButtonText()}
          </ControlButton>
        )}

        <ControlButton
          variant="stop"
          onClick={handleStopAndSend}
          disabled={(!isRecording && !isPaused) || isProcessing}
          active={isRecording || isPaused}
        >
          <FaStop />
          {getStopButtonText()}
        </ControlButton>
      </ButtonsContainer>
    </VoiceControlsContainer>
  );
};

export default VoiceRecording; 