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

  // Memoized backend health check function
  const checkBackendHealth = useCallback(async () => {
    try {
      await chatApi.healthCheck();
      setIsBackendHealthy(true);
      setBackendError(null);
    } catch (error) {
      setIsBackendHealthy(false);
      setBackendError('Backend service is not available. Please ensure the backend server is running.');
      console.error('Backend health check failed:', error);
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

  const handleSendMessage = useCallback(async (message) => {
    if (!threadId) {
      toast.error('No active conversation. Please restart the application.');
      return;
    }

    try {
      const response = await chatApi.sendMessage(message, threadId);
      
      setChatHistory(response.chat_history);
      setPayload(response.payload);
      setIsFormComplete(response.is_form_complete);
      
      return response;
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error(`Failed to send message: ${error.message}`);
      throw error;
    }
  }, [threadId]);

  const handleSendVoiceMessage = useCallback(async (audioData) => {
    if (!threadId) {
      toast.error('No active conversation. Please restart the application.');
      return;
    }

    try {
      const response = await chatApi.sendVoiceMessage(audioData, threadId);
      
      setChatHistory(response.chat_history);
      setPayload(response.payload);
      setIsFormComplete(response.is_form_complete);
      
      return response;
    } catch (error) {
      console.error('Failed to send voice message:', error);
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
      await chatApi.healthCheck();
      setIsBackendHealthy(true);
      setBackendError(null);
      toast.success('Backend connection restored!');
    } catch (error) {
      setBackendError('Backend service is still not available. Please ensure the backend server is running.');
      toast.error('Failed to connect to backend service.');
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
    isLoading,
    initialAudio
  }), [
    chatHistory,
    payload,
    isFormComplete,
    handleSendMessage,
    handleSendVoiceMessage,
    handleResetConversation,
    isLoading,
    initialAudio
  ]);

  return (
    <AppContainer>
      <Header />
      
      {backendError && (
        <ErrorBanner>
          ⚠️ {backendError}
          <button onClick={retryBackendConnection}>
            Retry Connection
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