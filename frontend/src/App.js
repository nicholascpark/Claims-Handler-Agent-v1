import React, { useState, useEffect, useCallback, useMemo, memo } from 'react';
import styled from 'styled-components';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Audio testing utility for development
import './utils/audioTest';

import Header from './components/Header';
import ChatInterface from './components/ChatInterface';
import StartScreen from './components/StartScreen';
import LoadingSpinner from './components/LoadingSpinner';
import { chatApi } from './services/api';

const AppContainer = styled.div`
  min-height: 100vh;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  display: flex;
  flex-direction: column;
`;

const MainContent = styled.main`
  flex: 1;
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  width: 100%;
`;

const ErrorBanner = styled.div`
  background: #dc3545;
  color: white;
  padding: 12px 20px;
  text-align: center;
  font-weight: 500;
  
  button {
    background: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.3);
    color: white;
    padding: 4px 12px;
    border-radius: 4px;
    margin-left: 12px;
    font-size: 14px;
    
    &:hover {
      background: rgba(255, 255, 255, 0.3);
    }
  }
`;

// Memoized Toast configuration
const toastConfig = {
  position: "top-right",
  autoClose: 5000,
  hideProgressBar: false,
  newestOnTop: false,
  closeOnClick: true,
  rtl: false,
  pauseOnFocusLoss: true,
  draggable: true,
  pauseOnHover: true,
  theme: "light"
};

function App() {
  const [isStarted, setIsStarted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [payload, setPayload] = useState({});
  const [isFormComplete, setIsFormComplete] = useState(false);
  const [backendError, setBackendError] = useState(null);
  const [isBackendHealthy, setIsBackendHealthy] = useState(null);
  const [initialAudio, setInitialAudio] = useState(null);

  // Memoized backend health check function with smart error handling
  const checkBackendHealth = useCallback(async () => {
    try {
      await chatApi.healthCheck();
      setIsBackendHealthy(true);
      setBackendError(null);
    } catch (error) {
      setIsBackendHealthy(false);
      console.error('Backend health check failed:', error);
      
      // Provide specific error messages based on error type
      if (error.message.includes('ERR_NETWORK') || error.message.includes('ECONNREFUSED')) {
        setBackendError('Backend service is sleeping (free tier). Click "Retry Connection" to wake it up.');
      } else if (error.message.includes('timeout')) {
        setBackendError('Backend service is slow to respond (possibly starting up). Please try "Retry Connection".');
      } else {
        setBackendError('Backend service is not available. Please ensure the backend server is running.');
      }
    }
  }, []);

  // Check backend health on startup
  useEffect(() => {
    checkBackendHealth();
    
    // Check health every 30 seconds
    const healthCheckInterval = setInterval(checkBackendHealth, 30000);
    
    return () => clearInterval(healthCheckInterval);
  }, [checkBackendHealth]);

  // Memoized handlers to prevent unnecessary re-renders
  const handleStartConversation = useCallback(async () => {
    if (!isBackendHealthy) {
      toast.error('Backend service is not available. Please try again later.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await chatApi.startConversation();
      
      setThreadId(response.thread_id);
      setChatHistory(response.chat_history);
      setPayload(response.payload);
      setIsFormComplete(response.is_form_complete);
      setInitialAudio(response.audio_data);
      setIsStarted(true);
      
      toast.success('Conversation started successfully!');
    } catch (error) {
      console.error('Failed to start conversation:', error);
      toast.error(`Failed to start conversation: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [isBackendHealthy]);

  const handleSendMessage = useCallback(async (messageOrMessages, abortSignal) => {
    if (!threadId) {
      toast.error('No active conversation. Please restart the application.');
      return;
    }

    // Handle both single messages and arrays of messages
    const isMultipleMessages = Array.isArray(messageOrMessages);
    
    // Only add optimistic updates for single messages
    // Multiple messages are handled optimistically by ChatInterface
    if (!isMultipleMessages) {
      const userMessage = {
        role: 'user',
        content: messageOrMessages,
        timestamp: new Date().toISOString()
      };
      setChatHistory(prev => [...prev, userMessage]);
    }

    try {
      const response = await chatApi.sendMessage(messageOrMessages, threadId, abortSignal);
      
      // Only update state if the request wasn't aborted
      if (!abortSignal?.aborted) {
        // For queued messages, we only add the AI response since user messages are already shown
        if (isMultipleMessages) {
          // Add only the AI response to the existing chat history
          setChatHistory(prev => [...prev, {
            role: 'assistant',
            content: response.message,
            timestamp: new Date().toISOString()
          }]);
        } else {
          // For single messages, update with complete chat history from server
          setChatHistory(response.chat_history);
        }
        setPayload(response.payload);
        setIsFormComplete(response.is_form_complete);
      }
      
      return response;
    } catch (error) {
      if (error.name === 'AbortError' || abortSignal?.aborted) {
        console.log('Message sending was aborted - cleaning up optimistic updates');
        // Remove optimistically added messages on abort
        // Only single messages have optimistic updates from App.js
        if (!isMultipleMessages) {
          setChatHistory(prev => prev.slice(0, -1));
        }
        throw error; // Re-throw abort error so calling code can handle it
      }
      
      console.error('Failed to send message:', error);
      
      // Remove the optimistically added user message(s) on error
      // Only single messages have optimistic updates from App.js
      if (!isMultipleMessages) {
        setChatHistory(prev => prev.slice(0, -1));
      }
      
      toast.error(`Failed to send message: ${error.message}`);
      throw error;
    }
  }, [threadId]);

  const handleSendVoiceMessage = useCallback(async (audioData) => {
    if (!threadId) {
      toast.error('No active conversation. Please restart the application.');
      return;
    }

    // Add user voice message to chat history immediately
    const userMessage = {
      role: 'user',
      content: 'Processing Voice',
      timestamp: new Date().toISOString(),
      isVoiceMessage: true,
      isProcessing: true
    };
    setChatHistory(prev => [...prev, userMessage]);

    try {
      const response = await chatApi.sendVoiceMessage(audioData, threadId);
      
      // Update with the complete chat history from the server
      // This will include the AI response and may have the transcribed text for the voice message
      setChatHistory(response.chat_history);
      setPayload(response.payload);
      setIsFormComplete(response.is_form_complete);
      
      return response;
    } catch (error) {
      console.error('Failed to send voice message:', error);
      
      // Remove the optimistically added user message on error
      setChatHistory(prev => prev.slice(0, -1));
      
      toast.error(`Failed to send voice message: ${error.message}`);
      throw error;
    }
  }, [threadId]);

  const handleResetConversation = useCallback(async () => {
    if (!threadId) return;

    setIsLoading(true);
    try {
      await chatApi.resetConversation(threadId);
      
      // Reset all state
      setIsStarted(false);
      setThreadId(null);
      setChatHistory([]);
      setPayload({});
      setIsFormComplete(false);
      setInitialAudio(null);
      
      toast.success('Conversation reset successfully!');
    } catch (error) {
      console.error('Failed to reset conversation:', error);
      toast.error(`Failed to reset conversation: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [threadId]);

  const retryBackendConnection = useCallback(async () => {
    try {
      setBackendError(null);
      setIsLoading(true);
      
      // Show helpful message about cold start
      toast.info('Waking up backend service... Render free tier can take 50+ seconds to spin up. Please be patient! ☕', {
        autoClose: false,
        toastId: 'waking-up'
      });
      
      await chatApi.healthCheck(true); // Pass true for retry mode (longer timeout)
      
      setIsBackendHealthy(true);
      setBackendError(null);
      toast.dismiss('waking-up');
      toast.success('Backend connection restored! 🚀');
    } catch (error) {
      toast.dismiss('waking-up');
      setBackendError(`Backend wake-up failed: ${error.message}`);
      toast.error('Failed to wake up backend service. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Memoized props for components to prevent unnecessary re-renders
  const startScreenProps = useMemo(() => ({
    onStart: handleStartConversation,
    isLoading,
    isBackendHealthy
  }), [handleStartConversation, isLoading, isBackendHealthy]);

  const chatInterfaceProps = useMemo(() => ({
    chatHistory,
    payload,
    isFormComplete,
    onSendMessage: handleSendMessage,
    onSendVoiceMessage: handleSendVoiceMessage,
    onReset: handleResetConversation,
    onUpdateChatHistory: setChatHistory,
    isLoading,
    initialAudio
  }), [
    chatHistory,
    payload,
    isFormComplete,
    handleSendMessage,
    handleSendVoiceMessage,
    handleResetConversation,
    setChatHistory,
    isLoading,
    initialAudio
  ]);

  return (
    <AppContainer>
      <Header />
      
      {backendError && (
        <ErrorBanner>
          ⚠️ {backendError}
          <div style={{ marginTop: '8px', fontSize: '0.9em', opacity: 0.8 }}>
            💡 <strong>Free Tier Note:</strong> Backend services sleep after 15 minutes of inactivity and take 50+ seconds to wake up (Render limitation).
          </div>
          <button onClick={retryBackendConnection} disabled={isLoading}>
            {isLoading ? 'Waking Up...' : 'Retry Connection'}
          </button>
        </ErrorBanner>
      )}
      
      <MainContent>
        {isLoading && <LoadingSpinner />}
        
        {!isStarted ? (
          <StartScreen {...startScreenProps} />
        ) : (
          <ChatInterface {...chatInterfaceProps} />
        )}
      </MainContent>
      
      <ToastContainer {...toastConfig} />
    </AppContainer>
  );
}

export default memo(App); 