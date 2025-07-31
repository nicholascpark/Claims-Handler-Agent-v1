import React, { memo, useMemo } from 'react';
import styled, { keyframes, css } from 'styled-components';
import { FaMicrophone } from 'react-icons/fa';
import SoundWaveVisualizer from './SoundWaveVisualizer';

const pulseAnimation = keyframes`
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 0 10px rgba(220, 53, 69, 0.0);
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
  padding: 16px;
`;

const StatusRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: ${props => props.$hasConversationIndicator ? '12px' : '0'};
  flex-wrap: wrap;
  
  @media (max-width: 768px) {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
`;

const StatusGroup = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
`;

const StatusIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  font-size: 14px;
  color: #333;
  min-width: 0;
  flex: 1;
`;

const StatusDot = styled.div`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: ${props => {
    if (props.$isRecording) return '#dc3545';
    if (props.$isPaused) return '#ffc107';
    return '#6c757d';
  }};
  transition: all 0.3s ease;
  flex-shrink: 0;
  
  ${props => props.$isRecording && css`
    animation: ${pulseAnimation} 1.5s infinite;
  `}
  
  ${props => props.$isPaused && css`
    animation: ${blinkAnimation} 2s infinite;
  `}
`;

const RecordingTimer = styled.div`
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 16px;
  font-weight: bold;
  color: ${props => props.$isRecording ? '#dc3545' : '#666'};
  background: ${props => props.$isRecording ? 'rgba(220, 53, 69, 0.1)' : '#f8f9fa'};
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid ${props => props.$isRecording ? 'rgba(220, 53, 69, 0.3)' : '#e0e0e0'};
  min-width: 70px;
  text-align: center;
  transition: all 0.3s ease;
  flex-shrink: 0;
  
  ${props => props.$isRecording && css`
    animation: ${blinkAnimation} 1s infinite;
  `}
`;

const ConversationIndicator = styled.div`
  background: ${props => {
    switch(props.$turn) {
      case 'ai_speaking': return 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)';
      case 'ai_complete': return 'linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%)';
      case 'user_turn': return 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)';
      case 'user_speaking': return 'linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%)';
      case 'processing': return 'linear-gradient(135deg, #fce4ec 0%, #f8bbd9 100%)';
      case 'no_audio': return 'linear-gradient(135deg, #fffde7 0%, #fff9c4 100%)';
      default: return 'linear-gradient(135deg, #f5f5f5 0%, #eeeeee 100%)';
    }
  }};
  border: 1px solid ${props => {
    switch(props.$turn) {
      case 'ai_speaking': return '#ff9800';
      case 'ai_complete': return '#4caf50';
      case 'user_turn': return '#2196f3';
      case 'user_speaking': return '#f44336';
      case 'processing': return '#e91e63';
      case 'no_audio': return '#ffc107';
      default: return '#757575';
    }
  }};
  border-radius: 8px;
  padding: 8px 12px;
  text-align: center;
  font-weight: 500;
  font-size: 13px;
  color: ${props => {
    switch(props.$turn) {
      case 'ai_speaking': return '#e65100';
      case 'ai_complete': return '#2e7d32';
      case 'user_turn': return '#1565c0';
      case 'user_speaking': return '#c62828';
      case 'processing': return '#ad1457';
      case 'no_audio': return '#ff8f00';
      default: return '#424242';
    }
  }};
  animation: ${props => 
    ['ai_speaking', 'user_speaking', 'no_audio'].includes(props.$turn) 
      ? css`${pulseAnimation} 2s infinite` 
      : 'slideIn 0.5s ease-out'
  };
  
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

const ControlsRow = styled.div`
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  
  @media (max-width: 768px) {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
`;

const MicrophoneInfo = styled.div`
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
  color: #666;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const DeviceSelect = styled.select`
  background: white;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 3px 6px;
  font-size: 11px;
  max-width: 150px;
`;

const VisualizerContainer = styled.div`
  flex: 1;
  min-width: 200px;
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  overflow: hidden;
  transition: all 0.3s ease;
  
  ${props => props.$show && css`
    border-color: ${props.$isRecording ? '#dc3545' : '#ffc107'};
    background: ${props.$isRecording ? 'rgba(220, 53, 69, 0.05)' : 'rgba(255, 193, 7, 0.05)'};
  `}
`;

const ErrorMessage = styled.div`
  background: #ffebee;
  border: 1px solid #f44336;
  border-radius: 6px;
  padding: 8px 12px;
  color: #c62828;
  margin-top: 8px;
  font-weight: 500;
  font-size: 13px;
`;

const VoiceControls = memo(({
  isRecording,
  isPaused,
  recordingTime,
  audioLevels,
  error,
  availableDevices,
  selectedDeviceId,
  audioURL,
  conversationTurn,
  turnTransitionDelay,
  isProcessing,
  isInitialized,
  isAutoRecordingPending,
  onDeviceChange
}) => {
  // Memoize device name calculation
  const currentDeviceName = useMemo(() => {
    if (!selectedDeviceId || availableDevices.length === 0) return 'Default microphone';
    const device = availableDevices.find(d => d.deviceId === selectedDeviceId);
    return device ? (device.label || 'Unknown device') : 'Default microphone';
  }, [selectedDeviceId, availableDevices]);

  // Memoize status text calculation
  const statusText = useMemo(() => {
    if (isProcessing) return 'Processing voice message...';
    if (conversationTurn === 'processing') return 'Processing your message...';
    if (conversationTurn === 'ai_speaking') return '🤖 AI is responding...';
    if (isRecording && !isPaused && conversationTurn === 'user_speaking') 
      return '🎤 Recording in progress - Press Send to submit';
    if (isPaused) return 'Recording paused - Press Send to submit or Resume/Pause to continue';
    if (isAutoRecordingPending || conversationTurn === 'user_turn') 
      return '🎤 Your turn - Recording will start automatically...';
    if (conversationTurn === 'user_speaking') return '🎤 Recording in progress - Press Send when done';
    if (conversationTurn === 'no_audio') return '⚠️ No audio recorded - please click Record to try again';
    if (!isInitialized) return 'Initializing microphone...';
    if (conversationTurn === 'waiting') return 'Ready to start conversation';
    return 'Ready to record or type a message';
  }, [isProcessing, conversationTurn, isRecording, isPaused, isAutoRecordingPending, isInitialized]);

  // Get conversation indicator text
  const getConversationIndicatorText = () => {
    switch (conversationTurn) {
      case 'ai_speaking':
        return '🤖 AI is speaking...';
      case 'ai_complete':
        return turnTransitionDelay 
          ? `✅ AI finished - Your turn in ${Math.ceil(turnTransitionDelay / 1000)}s`
          : '✅ AI finished - Your turn now';
      case 'user_turn':
        return '🎤 Your turn - Auto-recording starting...';
      case 'user_speaking':
        return '🎤 Listening... Press Send when finished';
      case 'processing':
        return '⏳ Processing your message...';
      case 'no_audio':
        return '⚠️ No audio recorded - please click Record to try again';
      default:
        return '';
    }
  };

  const showConversationIndicator = conversationTurn && conversationTurn !== 'waiting';

  return (
    <VoiceControlsContainer>
      <StatusRow $hasConversationIndicator={showConversationIndicator}>
        <StatusGroup>
          <StatusDot 
            $isRecording={isRecording && !isPaused} 
            $isPaused={isPaused}
          />
          <StatusIndicator>
            <span>{statusText}</span>
          </StatusIndicator>
        </StatusGroup>
        
        <RecordingTimer $isRecording={isRecording && !isPaused}>
          {recordingTime}
        </RecordingTimer>
      </StatusRow>

      {/* Conversation state indicator */}
      {showConversationIndicator && (
        <ConversationIndicator $turn={conversationTurn}>
          {getConversationIndicatorText()}
        </ConversationIndicator>
      )}

      {/* Controls row with microphone info and visualizer */}
      <ControlsRow>
        {/* Microphone device info */}
        <MicrophoneInfo>
          🎤 {currentDeviceName.length > 20 ? currentDeviceName.substring(0, 20) + '...' : currentDeviceName}
          {availableDevices.length > 1 && (
            <DeviceSelect value={selectedDeviceId || ''} onChange={onDeviceChange}>
              {availableDevices.map(device => (
                <option key={device.deviceId} value={device.deviceId}>
                  {device.label || `Microphone ${device.deviceId.slice(0, 8)}...`}
                </option>
              ))}
            </DeviceSelect>
          )}
        </MicrophoneInfo>

        {/* Sound wave visualizer */}
        <VisualizerContainer 
          $show={isRecording || isPaused} 
          $isRecording={isRecording && !isPaused}
        >
          <SoundWaveVisualizer
            audioLevels={audioLevels}
            isRecording={isRecording && !isPaused}
            isPaused={isPaused}
            show={isRecording || isPaused}
            audioURL={isPaused ? audioURL : null}
          />
        </VisualizerContainer>
      </ControlsRow>

      {error && (
        <ErrorMessage>
          ⚠️ {error}
        </ErrorMessage>
      )}
    </VoiceControlsContainer>
  );
});

VoiceControls.displayName = 'VoiceControls';

export default VoiceControls; 