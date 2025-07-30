import React, { memo, useRef, useEffect } from 'react';
import styled from 'styled-components';
import ChatMessage from './ChatMessage';

const MessagesContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
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

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  return (
    <MessagesContainer>
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