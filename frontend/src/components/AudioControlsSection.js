import React, { memo } from 'react';
import styled from 'styled-components';
import ConversationIndicator from './ConversationTurnIndicator';
import VoiceControls from './VoiceControls';
import AudioPlayer from './AudioPlayer';

const AudioControlsContainer = styled.div`
  background: white;
  border-radius: 16px;
  border: 2px solid #e0e0e0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
  overflow: hidden;
`;

const AudioHeader = styled.div`
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  padding: 16px 20px;
  border-bottom: 2px solid #e0e0e0;
  text-align: center;
`;

const AudioTitle = styled.h3`
  margin: 0;
  color: #2c3e50;
  font-size: 18px;
  font-weight: 600;
`;

const AudioBody = styled.div`
  padding: 0;
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
      <AudioHeader>
        <AudioTitle>🎤 Audio Controls & Status</AudioTitle>
      </AudioHeader>
      
      <AudioBody>
        {/* Conversation turn indicator */}
        <ConversationIndicator 
          conversationTurn={conversationTurn}
          turnTransitionDelay={turnTransitionDelay}
        />

        {/* Auto-recording notification */}
        {isAutoRecordingPending && conversationTurn === 'waiting' && (
          <AutoRecordingNotification>
            🤖 Recording will start automatically in a moment...
          </AutoRecordingNotification>
        )}

        {/* Voice controls with sound wave visualizer */}
        <VoiceControls {...voiceControlsProps} />

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
      </AudioBody>
    </AudioControlsContainer>
  );
});

AudioControlsSection.displayName = 'AudioControlsSection';

export default AudioControlsSection; 