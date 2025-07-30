import React, { memo, useMemo } from 'react';
import styled from 'styled-components';
import { FaUser, FaRobot, FaMicrophone } from 'react-icons/fa';

const MessageContainer = styled.div`
  display: flex;
  gap: 12px;
  align-items: flex-start;
  opacity: ${props => props.$isLatest ? 1 : 0.95};
  transition: opacity 0.3s ease;
`;

const MessageAvatar = styled.div`
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: ${props => props.$isUser ? '#007bff' : '#dc3545'};
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 16px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
`;

const MessageBubble = styled.div`
  background: ${props => props.$isUser ? '#e3f2fd' : '#f8f9fa'};
  border: 1px solid ${props => props.$isUser ? '#2196f3' : '#e0e0e0'};
  border-radius: 16px;
  padding: 12px 16px;
  max-width: 80%;
  position: relative;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;

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
      ? 'transparent transparent transparent #2196f3' 
      : 'transparent #e0e0e0 transparent transparent'};
  }
`;

const MessageContent = styled.div`
  font-size: 14px;
  line-height: 1.5;
  color: #333;
  white-space: pre-wrap;
  word-wrap: break-word;
`;

const MessageMeta = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #666;
  font-weight: 500;
`;

const VoiceIndicator = styled.span`
  color: #dc3545;
  font-size: 11px;
`;

const MessageTime = styled.span`
  font-size: 11px;
  color: #999;
  margin-top: 4px;
  display: block;
`;

// Optimize time formatting by memoizing it
const formatTime = () => {
  return new Date().toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  });
};

const ChatMessage = memo(({ message, isLatest = false }) => {
  const isUser = message.role === 'user';
  
  // Memoize voice message detection and content processing
  const { isVoiceMessage, displayContent } = useMemo(() => {
    const isVoice = message.content.includes('🎤');
    const content = isVoice 
      ? message.content.replace(/🎤\s*\*?(.+?)\*?/g, '$1')
      : message.content;
    
    return {
      isVoiceMessage: isVoice,
      displayContent: content
    };
  }, [message.content]);

  // Memoize current time for message
  const messageTime = useMemo(() => formatTime(), []);

  // Memoize avatar icon
  const avatarIcon = useMemo(() => {
    return isUser ? <FaUser /> : <FaRobot />;
  }, [isUser]);

  // Memoize user name
  const userName = useMemo(() => {
    return isUser ? 'You' : 'IntactBot';
  }, [isUser]);

  return (
    <MessageContainer $isLatest={isLatest}>
      <MessageAvatar $isUser={isUser}>
        {avatarIcon}
      </MessageAvatar>
      
      <div style={{ flex: 1 }}>
        <MessageBubble $isUser={isUser}>
          <MessageMeta>
            <span>{userName}</span>
            {isVoiceMessage && (
              <VoiceIndicator>
                <FaMicrophone /> Voice Message
              </VoiceIndicator>
            )}
          </MessageMeta>
          
          <MessageContent>
            {displayContent}
          </MessageContent>
          
          <MessageTime>
            {messageTime}
          </MessageTime>
        </MessageBubble>
      </div>
    </MessageContainer>
  );
});

ChatMessage.displayName = 'ChatMessage';

export default ChatMessage; 