import React, { useRef } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface TextInputProps {
  onSend: (text: string) => void;
  isLoading: boolean;
}

export const TextInput: React.FC<TextInputProps> = ({ onSend, isLoading }) => {
  const [text, setText] = React.useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim() && !isLoading) {
      onSend(text);
      setText('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 w-full max-w-2xl mx-auto mt-4 px-4">
      <input
        ref={inputRef}
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Or type your response..."
        disabled={isLoading}
        className="flex-1 bg-white border border-slate-200 rounded-full px-6 py-3 text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all shadow-sm"
      />
      <button
        type="submit"
        disabled={!text.trim() || isLoading}
        className="p-3 bg-white border border-slate-200 text-slate-700 rounded-full hover:bg-slate-50 hover:text-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
      >
        {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
      </button>
    </form>
  );
};
