import React, { memo } from 'react';
import styled from 'styled-components';
import VoiceControls from './VoiceControls';
import AudioPlayer from './AudioPlayer';

const AudioControlsContainer = styled.div`
  background: white;
  border-radius: 12px;
  border: 1px solid #e0e0e0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 20px;
  overflow: hidden;
  width: 60%;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
  
  @media (max-width: 768px) {
    width: 90%;
  }
`;

const AutoRecordingNotification = styled.div`
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border-bottom: 1px solid #2196f3;
  padding: 8px 16px;
  text-align: center;
  font-weight: 500;
  font-size: 14px;
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

const AudioControlsSection = memo(({
  // Conversation state props
  conversationTurn,
  turnTransitionDelay,
  isAutoRecordingPending,
  
  // Audio player props
  currentAudioData,
  onAudioPlay,
  onAudioEnd,
  
  // Voice controls props
  voiceControlsProps
}) => {
  return (
    <AudioControlsContainer>
      {/* Auto-recording notification */}
      {isAutoRecordingPending && conversationTurn === 'waiting' && (
        <AutoRecordingNotification>
          🤖 Recording will start automatically in a moment...
        </AutoRecordingNotification>
      )}

      {/* Integrated voice controls with conversation indicator */}
      <VoiceControls 
        {...voiceControlsProps}
        conversationTurn={conversationTurn}
        turnTransitionDelay={turnTransitionDelay}
      />

      {/* Hidden AI Audio Player */}
      {currentAudioData && (
        <AudioPlayer
          audioData={currentAudioData}
          onPlay={onAudioPlay}
          onEnd={onAudioEnd}
          autoPlay={true}
          loop={false}
        />
      )}
    </AudioControlsContainer>
  );
});

AudioControlsSection.displayName = 'AudioControlsSection';

export default AudioControlsSection; 