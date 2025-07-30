import React, { memo } from 'react';
import styled, { keyframes, css } from 'styled-components';

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

const ConversationTurnIndicator = styled.div`
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
  border: 2px solid ${props => {
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
  border-radius: 12px;
  padding: 12px 16px;
  margin: 12px 16px;
  text-align: center;
  font-weight: 500;
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

const ConversationIndicator = memo(({ conversationTurn, turnTransitionDelay }) => {
  if (conversationTurn === 'waiting') return null;

  const getIndicatorText = () => {
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

  return (
    <ConversationTurnIndicator $turn={conversationTurn}>
      {getIndicatorText()}
    </ConversationTurnIndicator>
  );
});

ConversationIndicator.displayName = 'ConversationIndicator';

export default ConversationIndicator; 