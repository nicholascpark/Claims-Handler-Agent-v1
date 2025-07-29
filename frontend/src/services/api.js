import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds timeout
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add any auth headers or other processing here
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle common errors
    if (error.response?.status === 500) {
      console.error('Server error:', error.response.data);
    }
    return Promise.reject(error);
  }
);

export const chatApi = {
  // Start a new conversation
  startConversation: async (threadId = null) => {
    try {
      const response = await api.post('/api/chat/start', { thread_id: threadId });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to start conversation: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Send a text message
  sendMessage: async (message, threadId) => {
    try {
      const response = await api.post('/api/chat/message', {
        message,
        thread_id: threadId,
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to send message: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Send a voice message
  sendVoiceMessage: async (audioData, threadId) => {
    try {
      const response = await api.post('/api/chat/voice', {
        audio_data: audioData,
        thread_id: threadId,
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to send voice message: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get audio response
  getAudioResponse: async (threadId, text) => {
    try {
      const response = await api.get(`/api/chat/audio/${threadId}`, {
        params: { text },
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get audio response: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Reset conversation
  resetConversation: async (threadId) => {
    try {
      const response = await api.delete(`/api/chat/${threadId}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to reset conversation: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get current payload
  getPayload: async (threadId) => {
    try {
      const response = await api.get(`/api/chat/${threadId}/payload`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get payload: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Health check
  healthCheck: async () => {
    try {
      const response = await api.get('/health');
      return response.data;
    } catch (error) {
      throw new Error(`Health check failed: ${error.response?.data?.detail || error.message}`);
    }
  },
};

export default api; 