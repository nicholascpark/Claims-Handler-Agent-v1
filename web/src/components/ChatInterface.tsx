import { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { VoiceRecorder } from './VoiceRecorder';
import { TextInput } from './TextInput';
import { useChat } from '../hooks/useChat';
import { Loader2 } from 'lucide-react';
import { PayloadDisplay } from './PayloadDisplay';

export const ChatInterface = () => {
  const { 
    messages, 
    payload, 
    isLoading, 
    isComplete, 
    audioUrl,
    initChat, 
    sendMessage, 
    sendAudio 
  } = useChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Initial load
  useEffect(() => {
    initChat();
  }, []);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-play audio response
  useEffect(() => {
    if (audioUrl && audioRef.current) {
      audioRef.current.src = audioUrl;
      audioRef.current.play().catch(e => console.log("Auto-play blocked:", e));
    }
  }, [audioUrl]);

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-64px)] overflow-hidden bg-slate-50/50">
      {/* Audio Player (Hidden) */}
      <audio ref={audioRef} className="hidden" />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full relative">
        {/* Messages List */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-2">
          <div className="max-w-3xl mx-auto w-full pb-32">
            {messages.map((msg, idx) => (
              <MessageBubble key={idx} message={msg} />
            ))}
            
            {isLoading && (
              <div className="flex items-center gap-2 text-slate-400 ml-12 text-sm animate-pulse">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Notera is thinking...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area (Sticky Bottom) */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white to-transparent pt-12 pb-6 px-4">
          <div className="max-w-2xl mx-auto flex flex-col items-center">
            <VoiceRecorder onRecordComplete={sendAudio} isLoading={isLoading} />
            <TextInput onSend={sendMessage} isLoading={isLoading} />
          </div>
        </div>
      </div>

      {/* Side Panel (Payload) - Hidden on mobile, toggleable or stacked */}
      <div className="hidden lg:block w-96 h-full shadow-xl z-20">
        <PayloadDisplay payload={payload} isComplete={isComplete} />
      </div>
    </div>
  );
};
