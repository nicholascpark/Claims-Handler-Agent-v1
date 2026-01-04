import React from 'react';
import { ChatMessage } from '../types';
import clsx from 'clsx';
import { Bot, User } from 'lucide-react';

interface MessageBubbleProps {
  message: ChatMessage;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';
  
  return (
    <div className={clsx(
      "flex w-full mb-6",
      isUser ? "justify-end" : "justify-start"
    )}>
      <div className={clsx(
        "flex max-w-[85%] md:max-w-[75%] gap-3",
        isUser ? "flex-row-reverse" : "flex-row"
      )}>
        {/* Avatar */}
        <div className={clsx(
          "w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-sm",
          isUser ? "bg-primary-100 text-primary-600" : "bg-white text-slate-600 border border-slate-200"
        )}>
          {isUser ? <User size={16} /> : <Bot size={16} />}
        </div>

        {/* Bubble */}
        <div className={clsx(
          "p-4 rounded-2xl shadow-sm text-[15px] leading-relaxed",
          isUser 
            ? "bg-primary-600 text-white rounded-tr-sm" 
            : "bg-white border border-slate-100 text-slate-700 rounded-tl-sm"
        )}>
          {message.content}
        </div>
      </div>
    </div>
  );
};
