import React, { memo, useRef, useEffect } from 'react';
import styled from 'styled-components';
import ChatMessage from './ChatMessage';

const MessagesContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  max-height: 100%;
  scroll-behavior: smooth;
  
  /* Custom scrollbar styling for better UX */
  &::-webkit-scrollbar {
    width: 8px;
  }
  
  &::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 4px;
    transition: background 0.3s ease;
  }
  
  &::-webkit-scrollbar-thumb:hover {
    background: #a8a8a8;
  }
`;

const NoMessagesPlaceholder = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
  text-align: center;
  gap: 16px;
`;

const PlaceholderIcon = styled.div`
  font-size: 48px;
  opacity: 0.5;
`;

const PlaceholderText = styled.p`
  font-size: 16px;
  margin: 0;
  line-height: 1.5;
`;

const MessagesList = memo(({ chatHistory = [], conversationTurn = 'waiting' }) => {
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive, but only if user is near bottom
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container || !messagesEndRef.current) return;

    // Check if user is near the bottom (within 100px)
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
    
    // Only auto-scroll if user is near bottom or if it's the first message
    if (isNearBottom || chatHistory.length <= 1) {
      messagesEndRef.current?.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end'
      });
    }
  }, [chatHistory]);

  return (
    <MessagesContainer ref={messagesContainerRef}>
      {chatHistory.length === 0 ? (
        <NoMessagesPlaceholder>
          <PlaceholderIcon>💬</PlaceholderIcon>
          <PlaceholderText>
            {conversationTurn === 'waiting' ? (
              <>
                Welcome to IntactBot FNOL System!<br />
                Start by typing a message below or wait for the AI to begin.
              </>
            ) : (
              <>
                Conversation in progress...<br />
                Messages will appear here as you chat with the AI.
              </>
            )}
          </PlaceholderText>
        </NoMessagesPlaceholder>
      ) : (
        <>
          {chatHistory.map((message, index) => (
            <ChatMessage
              key={index}
              message={message}
              isLatest={index === chatHistory.length - 1}
            />
          ))}
          <div ref={messagesEndRef} />
        </>
      )}
    </MessagesContainer>
  );
});

MessagesList.displayName = 'MessagesList';

export default MessagesList; 