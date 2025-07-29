import React, { useState, useEffect } from 'react';
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

  // Removed auto-start behavior to require user to press the Start button manually

  // Check backend health on startup
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        await chatApi.healthCheck();
        setIsBackendHealthy(true);
        setBackendError(null);
      } catch (error) {
        setIsBackendHealthy(false);
        setBackendError('Backend service is not available. Please ensure the backend server is running.');
        console.error('Backend health check failed:', error);
      }
    };

    checkBackendHealth();
    
    // Check health every 30 seconds
    const healthCheckInterval = setInterval(checkBackendHealth, 30000);
    
    return () => clearInterval(healthCheckInterval);
  }, []);

  const handleStartConversation = async () => {
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
  };

  const handleSendMessage = async (message) => {
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
  };

  const handleSendVoiceMessage = async (audioData) => {
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
  };

  const handleResetConversation = async () => {
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
      
      toast.success('Conversation reset successfully!');
    } catch (error) {
      console.error('Failed to reset conversation:', error);
      toast.error(`Failed to reset conversation: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const retryBackendConnection = async () => {
    try {
      await chatApi.healthCheck();
      setIsBackendHealthy(true);
      setBackendError(null);
      toast.success('Backend connection restored!');
    } catch (error) {
      setBackendError('Backend service is still not available. Please ensure the backend server is running.');
      toast.error('Failed to connect to backend service.');
    }
  };

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
          <StartScreen 
            onStart={handleStartConversation}
            isLoading={isLoading}
            isBackendHealthy={isBackendHealthy}
          />
        ) : (
          <ChatInterface
            chatHistory={chatHistory}
            payload={payload}
            isFormComplete={isFormComplete}
            onSendMessage={handleSendMessage}
            onSendVoiceMessage={handleSendVoiceMessage}
            onReset={handleResetConversation}
            isLoading={isLoading}
            initialAudio={initialAudio}
          />
        )}
      </MainContent>
      
      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />
    </AppContainer>
  );
}

export default App; 