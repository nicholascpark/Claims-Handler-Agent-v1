import { ChatResponse } from '../types';

const API_BASE = '/api';

export const api = {
  startChat: async (): Promise<ChatResponse> => {
    const response = await fetch(`${API_BASE}/chat/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('Failed to start chat');
    return response.json();
  },

  sendMessage: async (message: string, threadId: string): Promise<ChatResponse> => {
    const response = await fetch(`${API_BASE}/chat/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, thread_id: threadId }),
    });
    if (!response.ok) throw new Error('Failed to send message');
    return response.json();
  },

  sendVoice: async (audioBase64: string, threadId: string): Promise<ChatResponse> => {
    const response = await fetch(`${API_BASE}/chat/voice`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ audio_data: audioBase64, thread_id: threadId }),
    });
    if (!response.ok) throw new Error('Failed to send voice');
    return response.json();
  }
};
