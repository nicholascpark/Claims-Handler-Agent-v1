import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { ChatMessage, ClaimPayload } from '../types';

export const useChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [payload, setPayload] = useState<ClaimPayload>({});
  const [isLoading, setIsLoading] = useState(false);
  const [threadId, setThreadId] = useState<string>('');
  const [isComplete, setIsComplete] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const initChat = async () => {
    setIsLoading(true);
    try {
      const data = await api.startChat();
      setThreadId(data.thread_id);
      setMessages(data.chat_history);
      setPayload(data.payload);
      handleAudioResponse(data.audio_data);
    } catch (error) {
      console.error('Failed to init chat', error);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;
    
    // Optimistic update
    const tempMsg: ChatMessage = { 
      role: 'user', 
      content: text, 
      timestamp: new Date().toISOString() 
    };
    setMessages(prev => [...prev, tempMsg]);
    setIsLoading(true);

    try {
      const data = await api.sendMessage(text, threadId);
      updateStateFromResponse(data);
    } catch (error) {
      console.error('Failed to send message', error);
      // Remove failed optimistic message or show error
    } finally {
      setIsLoading(false);
    }
  };

  const sendAudio = async (base64Audio: string) => {
    setIsLoading(true);
    try {
      const data = await api.sendVoice(base64Audio, threadId);
      updateStateFromResponse(data);
    } catch (error) {
      console.error('Failed to send voice', error);
    } finally {
      setIsLoading(false);
    }
  };

  const updateStateFromResponse = (data: any) => {
    setMessages(data.chat_history);
    setPayload(data.payload);
    setIsComplete(data.is_form_complete);
    handleAudioResponse(data.audio_data);
  };

  const handleAudioResponse = (base64Audio?: string) => {
    if (base64Audio) {
      // Convert base64 to blob url
      const byteCharacters = atob(base64Audio);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: 'audio/mp3' });
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
    }
  };

  // Cleanup audio URL
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  return {
    messages,
    payload,
    isLoading,
    isComplete,
    audioUrl,
    initChat,
    sendMessage,
    sendAudio
  };
};
