import React, { memo, useMemo } from 'react';
import styled, { keyframes } from 'styled-components';
import { FaUser, FaRobot, FaMicrophone } from 'react-icons/fa';

// Pulsing animation for thought bubble
const pulseGlow = keyframes`
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(200, 84, 80, 0.7);
  }
  50% {
    transform: scale(1.02);
    box-shadow: 0 0 0 8px rgba(200, 84, 80, 0.0);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(200, 84, 80, 0);
  }
`;

const MessageContainer = styled.div`
  display: flex;
  gap: 12px;
  align-items: flex-start;
  opacity: ${props => props.$isLatest ? 1 : 0.95};
  transition: opacity 0.3s ease;
  flex-direction: ${props => props.$isUser ? 'row-reverse' : 'row'};
  justify-content: ${props => props.$isUser ? 'flex-end' : 'flex-start'};
  margin-bottom: 16px;
`;

const MessageAvatar = styled.div`
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: ${props => props.$isUser ? '#c85450' : '#495057'};
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 16px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
`;

// Regular speech bubble
const MessageBubble = styled.div`
  background: ${props => props.$isUser ? '#c85450' : '#f8f9fa'};
  border: 1px solid ${props => props.$isUser ? '#c85450' : '#e0e0e0'};
  border-radius: 16px;
  padding: 12px 16px;
  max-width: 70%;
  position: relative;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  color: ${props => props.$isUser ? 'white' : '#333'};

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &::before {
    content: '';
    position: absolute;
    top: 12px;
    ${props => props.$isUser ? 'right: -8px;' : 'left: -8px;'}
    width: 0;
    height: 0;
    border-style: solid;
    border-width: ${props => props.$isUser ? '8px 0 8px 8px' : '8px 8px 8px 0'};
    border-color: ${props => props.$isUser 
      ? 'transparent transparent transparent #c85450' 
      : 'transparent #e0e0e0 transparent transparent'};
  }
`;

// Thought bubble for processing voice messages
const ThoughtBubble = styled.div`
  background: ${props => props.$isUser ? '#c85450' : '#f8f9fa'};
  border: 1px solid ${props => props.$isUser ? '#c85450' : '#e0e0e0'};
  border-radius: 20px;
  padding: 12px 16px;
  max-width: 70%;
  position: relative;
  color: ${props => props.$isUser ? 'white' : '#333'};
  animation: ${pulseGlow} 2s infinite;
  
  /* Main thought bubble pointer */
  &::before {
    content: '';
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    ${props => props.$isUser ? 'right: -12px;' : 'left: -12px;'}
    width: 16px;
    height: 20px;
    background: ${props => props.$isUser ? '#c85450' : '#f8f9fa'};
    border: 1px solid ${props => props.$isUser ? '#c85450' : '#e0e0e0'};
    border-radius: 50%;
    ${props => props.$isUser ? 'border-left: none;' : 'border-right: none;'}
  }
  
  /* Small thought bubbles */
  &::after {
    content: '';
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    ${props => props.$isUser ? 'right: -28px;' : 'left: -28px;'}
    width: 8px;
    height: 8px;
    background: ${props => props.$isUser ? '#c85450' : '#f8f9fa'};
    border: 1px solid ${props => props.$isUser ? '#c85450' : '#e0e0e0'};
    border-radius: 50%;
    box-shadow: 
      ${props => props.$isUser ? 
        '8px -4px 0 -2px #c85450, 8px -4px 0 -1px #c85450, 12px 4px 0 -4px #c85450, 12px 4px 0 -3px #c85450' : 
        '-8px -4px 0 -2px #f8f9fa, -8px -4px 0 -1px #e0e0e0, -12px 4px 0 -4px #f8f9fa, -12px 4px 0 -3px #e0e0e0'};
  }
`;

const MessageContent = styled.div`
  font-size: 14px;
  line-height: 1.5;
  color: inherit;
  white-space: pre-wrap;
  word-wrap: break-word;
`;

const MessageMeta = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 12px;
  color: ${props => props.$isUser ? 'rgba(255, 255, 255, 0.9)' : '#666'};
  font-weight: 500;
  justify-content: ${props => props.$isUser ? 'flex-end' : 'flex-start'};
`;

const VoiceIndicator = styled.span`
  color: ${props => props.$isUser ? 'rgba(255, 255, 255, 0.8)' : '#dc3545'};
  font-size: 11px;
`;

const MessageTime = styled.span`
  font-size: 11px;
  color: ${props => props.$isUser ? 'rgba(255, 255, 255, 0.7)' : '#999'};
  margin-top: 4px;
  display: block;
  text-align: ${props => props.$isUser ? 'right' : 'left'};
`;

const MessageWrapper = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: ${props => props.$isUser ? 'flex-end' : 'flex-start'};
`;

// Optimize time formatting by memoizing it
const formatTime = (timestamp) => {
  if (timestamp) {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }
  return new Date().toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  });
};

const ChatMessage = memo(({ message, isLatest = false }) => {
  const isUser = message.role === 'user';
  
  // Memoize voice message detection and content processing
  const { isVoiceMessage, displayContent, isProcessing } = useMemo(() => {
    // Check if isVoiceMessage property is set (for immediate display)
    // or detect from content pattern (for server responses)
    const isVoice = message.isVoiceMessage || message.content.includes('🎤');
    const isProc = message.isProcessing || false;
    const content = isVoice && message.content.includes('🎤')
      ? message.content.replace(/🎤\s*\*?(.+?)\*?/g, '$1')
      : message.content;
    
    return {
      isVoiceMessage: isVoice,
      displayContent: content,
      isProcessing: isProc
    };
  }, [message.content, message.isVoiceMessage, message.isProcessing]);

  // Memoize message time using actual timestamp if available
  const messageTime = useMemo(() => formatTime(message.timestamp), [message.timestamp]);

  // Memoize avatar icon
  const avatarIcon = useMemo(() => {
    return isUser ? <FaUser /> : <FaRobot />;
  }, [isUser]);

  // Memoize user name
  const userName = useMemo(() => {
    return isUser ? 'You' : 'IntactBot';
  }, [isUser]);

  // Choose bubble component based on processing state
  const BubbleComponent = isVoiceMessage && isProcessing ? ThoughtBubble : MessageBubble;

  return (
    <MessageContainer $isLatest={isLatest} $isUser={isUser}>
      <MessageAvatar $isUser={isUser}>
        {avatarIcon}
      </MessageAvatar>
      
      <MessageWrapper $isUser={isUser}>
        <BubbleComponent $isUser={isUser}>
          <MessageMeta $isUser={isUser}>
            <span>{userName}</span>
            {isVoiceMessage && (
              <VoiceIndicator $isUser={isUser}>
                <FaMicrophone /> {isProcessing ? 'Processing...' : 'Voice Message'}
              </VoiceIndicator>
            )}
          </MessageMeta>
          
          <MessageContent>
            {displayContent}
          </MessageContent>
          
          <MessageTime $isUser={isUser}>
            {messageTime}
          </MessageTime>
        </BubbleComponent>
      </MessageWrapper>
    </MessageContainer>
  );
});

ChatMessage.displayName = 'ChatMessage';

export default ChatMessage; 