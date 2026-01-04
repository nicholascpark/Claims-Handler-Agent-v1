import { Bot, Globe } from 'lucide-react';

export const Header = () => {
  return (
    <header className="flex items-center justify-between px-6 py-4 bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <div className="bg-primary-600 p-2 rounded-xl shadow-lg shadow-primary-500/20">
          <Bot className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="font-outfit font-bold text-xl text-slate-900 leading-tight">
            Notera Voice Agent
          </h1>
          <p className="text-xs font-medium text-slate-500 tracking-wide uppercase">
            Claims Intake v1.0
          </p>
        </div>
      </div>
      
      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-full text-sm font-medium text-slate-600">
          <Globe className="w-4 h-4" />
          <span>EN</span>
        </div>
      </div>
    </header>
  );
};
