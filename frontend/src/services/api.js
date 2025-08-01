import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000, // Reduced to 15 seconds for faster error detection
  // Connection optimization
  maxRedirects: 3,
  validateStatus: function (status) {
    return status >= 200 && status < 300; // default
  },
  // Enable compression for better performance
  decompress: true,
  maxContentLength: 50000000, // 50MB max response size
  maxBodyLength: 50000000, // 50MB max request size
  // Remove adapter specification to use browser default (xhr)
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add timestamp for request timing
    config.metadata = { startTime: new Date() };
    console.log('Making API request to:', config.baseURL + config.url);
    return config;
  },
  (error) => {
    console.error('Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor with performance monitoring
api.interceptors.response.use(
  (response) => {
    // Calculate client-side request time
    const requestTime = new Date() - response.config.metadata.startTime;
    
    // Log performance metrics if available
    if (response.data?.processing_time) {
      console.log(`Request completed - Server: ${response.data.processing_time.toFixed(2)}s, Client: ${(requestTime/1000).toFixed(2)}s, Cached: ${response.data.cached || false}`);
    }
    
    return response;
  },
  (error) => {
    // Enhanced error logging for debugging
    console.error('API Error Details:', {
      message: error.message,
      code: error.code,
      status: error.response?.status,
      data: error.response?.data,
      url: error.config?.url,
      baseURL: error.config?.baseURL,
      timeout: error.config?.timeout
    });
    
    // Handle common errors
    if (error.response?.status === 500) {
      console.error('Server error:', error.response.data);
    } else if (error.code === 'ECONNREFUSED' || error.code === 'ERR_NETWORK') {
      console.error('Network connection error - backend may be unavailable');
    }
    
    return Promise.reject(error);
  }
);

// Debug function to test backend connectivity
window.testBackendConnection = async () => {
  console.log('Testing backend connection...');
  try {
    const response = await fetch('http://localhost:8000/health');
    const data = await response.json();
    console.log('✅ Backend connection successful:', data);
    return data;
  } catch (error) {
    console.error('❌ Backend connection failed:', error);
    throw error;
  }
};

export const chatApi = {
  // Start a new conversation
  startConversation: async (threadId = null) => {
    try {
      const response = await api.post('/api/chat/start', { thread_id: threadId });
      return {
        ...response.data,
        // Add client timing information
        clientRequestTime: new Date() - response.config.metadata.startTime
      };
    } catch (error) {
      throw new Error(`Failed to start conversation: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Send a text message with early completion detection (supports both single messages and arrays)
  sendMessage: async (messageOrMessages, threadId, abortSignal, options = {}) => {
    try {
      const startTime = Date.now();
      
      let response;
      
      // Check if we're sending multiple messages (array) or single message
      if (Array.isArray(messageOrMessages)) {
        // Use the queue endpoint for multiple messages
        response = await api.post('/api/chat/queue', {
          messages: messageOrMessages,
          thread_id: threadId,
          stream: options.enableStreaming || false,
        }, {
          signal: abortSignal
        });
      } else {
        // Use the standard endpoint for single messages
        response = await api.post('/api/chat/message', {
          message: messageOrMessages,
          thread_id: threadId,
          stream: options.enableStreaming || false,
        }, {
          signal: abortSignal
        });
      }
      
      const totalTime = Date.now() - startTime;
      
      return {
        ...response.data,
        clientRequestTime: totalTime,
        // Flag for early completion handling
        completedEarly: response.data.processing_time && (response.data.processing_time * 1000) < (totalTime * 0.8)
      };
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error; // Re-throw abort errors as-is
      }
      throw new Error(`Failed to send message: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Send a voice message with early completion detection
  sendVoiceMessage: async (audioData, threadId, options = {}) => {
    try {
      const startTime = Date.now();
      
      const response = await api.post('/api/chat/voice', {
        audio_data: audioData,
        thread_id: threadId,
        stream: options.enableStreaming || false,
      });
      
      const totalTime = Date.now() - startTime;
      
      return {
        ...response.data,
        clientRequestTime: totalTime,
        // Flag for early completion handling
        completedEarly: response.data.processing_time && (response.data.processing_time * 1000) < (totalTime * 0.8)
      };
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

  // Health check with performance stats and cold start handling
  healthCheck: async (isRetry = false) => {
    try {
      console.log('Attempting health check to:', API_BASE_URL + '/health');
      
      // Longer timeout for cold starts on Render free tier
      const timeout = isRetry ? 90000 : 15000; // 90s for retry, 15s for normal
      
      const response = await api.get('/health', { timeout });
      console.log('Health check successful:', response.data);
      return response.data;
    } catch (error) {
      console.error('Health check error details:', {
        message: error.message,
        code: error.code,
        response: error.response?.data,
        status: error.response?.status,
        url: error.config?.url,
        isRetry
      });
      
      // Provide helpful error messages for different scenarios
      if (error.code === 'ECONNABORTED' && isRetry) {
        throw new Error('Backend is starting up (this can take up to 90 seconds on free tier). Please wait...');
      } else if (error.code === 'ERR_NETWORK' || error.code === 'ECONNREFUSED') {
        throw new Error('Backend service is sleeping. Click "Retry Connection" to wake it up.');
      }
      
      throw new Error(`Health check failed: ${error.response?.data?.detail || error.message}`);
    }
  },

  // New: Get performance statistics
  getPerformanceStats: async () => {
    try {
      const response = await api.get('/api/performance/stats');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get performance stats: ${error.response?.data?.detail || error.message}`);
    }
  },

  // New: Clear caches for testing
  clearCache: async () => {
    try {
      const response = await api.post('/api/performance/clear-cache');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to clear cache: ${error.response?.data?.detail || error.message}`);
    }
  }
};

export default api; 