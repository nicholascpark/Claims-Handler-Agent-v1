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
    if (props.$isRecording) return '#dc3545';
    if (props.$isPaused) return '#ffc107';
    return '#6c757d';
  }};
  transition: all 0.3s ease;
  
  ${props => props.$isRecording && css`
    animation: ${pulseAnimation} 1.5s infinite;
  `}
  
  ${props => props.$isPaused && css`
    animation: ${blinkAnimation} 2s infinite;
  `}
`;

const RecordingTimer = styled.div`
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 18px;
  font-weight: bold;
  color: ${props => props.$isRecording ? '#dc3545' : '#666'};
  background: ${props => props.$isRecording ? 'rgba(220, 53, 69, 0.1)' : '#f8f9fa'};
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid ${props => props.$isRecording ? 'rgba(220, 53, 69, 0.3)' : '#e0e0e0'};
  min-width: 80px;
  text-align: center;
  transition: all 0.3s ease;
  
  ${props => props.$isRecording && css`
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
  
  ${props => props.$show && css`
    border-color: ${props.$isRecording ? '#dc3545' : '#ffc107'};
    background: ${props.$isRecording ? 'rgba(220, 53, 69, 0.05)' : 'rgba(255, 193, 7, 0.05)'};
  `}
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

const ErrorMessage = styled.div`
  background: #ffebee;
  border: 1px solid #f44336;
  border-radius: 8px;
  padding: 12px;
  color: #c62828;
  margin: 8px 0;
  font-weight: 500;
`;

const TestButton = styled.button`
  background: #007bff;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  margin: 8px 0;

  &:hover:not(:disabled) {
    background: #0056b3;
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
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
  isProcessing,
  isInitialized,
  isAutoRecordingPending,
  onDeviceChange,
  onManualRecordingTest // Add this new prop
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

  return (
    <VoiceControlsContainer>
      <ControlsHeader>
        <StatusIndicator>
          <StatusDot 
            $isRecording={isRecording && !isPaused} 
            $isPaused={isPaused}
          />
          <span>{statusText}</span>
        </StatusIndicator>
        
        <RecordingTimer $isRecording={isRecording && !isPaused}>
          {recordingTime}
        </RecordingTimer>
      </ControlsHeader>

      {/* Microphone device selector */}
      {availableDevices.length > 1 && (
        <MicrophoneSelector>
          🎤 Current microphone: <strong>{currentDeviceName}</strong>
          <DeviceSelect value={selectedDeviceId || ''} onChange={onDeviceChange}>
            {availableDevices.map(device => (
              <option key={device.deviceId} value={device.deviceId}>
                {device.label || `Microphone ${device.deviceId.slice(0, 8)}...`}
              </option>
            ))}
          </DeviceSelect>
        </MicrophoneSelector>
      )}

      {error && (
        <ErrorMessage>
          ⚠️ {error}
        </ErrorMessage>
      )}

      {/* Manual test button for debugging */}
      <TestButton 
        onClick={onManualRecordingTest}
        disabled={isProcessing}
      >
        🔧 Test Recording Manually
      </TestButton>

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
    </VoiceControlsContainer>
  );
});

VoiceControls.displayName = 'VoiceControls';

export default VoiceControls; 