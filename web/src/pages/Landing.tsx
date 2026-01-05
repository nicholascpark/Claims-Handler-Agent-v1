import { useNavigate } from 'react-router-dom';
import { ArrowRight, Mic, Shield, Stethoscope, Home, Briefcase, Landmark, Store } from 'lucide-react';
import { ApiKeyInput } from '../components/settings/ApiKeyInput';

const TEMPLATES = [
  { id: 'legal', icon: Shield, label: 'Legal', desc: 'Case intake & screening' },
  { id: 'health', icon: Stethoscope, label: 'Healthcare', desc: 'Patient triage & scheduling' },
  { id: 'home', icon: Home, label: 'Home Services', desc: 'Quotes & appointments' },
  { id: 'recruiting', icon: Briefcase, label: 'Recruiting', desc: 'Candidate screening' },
  { id: 'finance', icon: Landmark, label: 'Financial', desc: 'Loan applications' },
  { id: 'retail', icon: Store, label: 'Retail', desc: 'Order tracking & support' },
];

export const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex flex-col">
      
      {/* Header */}
      <header className="px-6 py-4 flex items-center justify-between max-w-7xl mx-auto w-full">
        <div className="flex items-center gap-2 font-bold text-xl text-gray-900">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center text-white">
            <Mic size={18} />
          </div>
          NOTERA
        </div>
        <div className="w-64">
           <ApiKeyInput />
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-16 text-center max-w-4xl mx-auto w-full animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-50 text-primary-700 text-sm font-medium mb-6 border border-primary-100">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-500"></span>
          </span>
          No coding required
        </div>
        
        <h1 className="text-5xl md:text-6xl font-extrabold text-gray-900 tracking-tight mb-6">
          AI Conversational <br className="hidden md:block"/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-indigo-600">Form Builder</span>
        </h1>
        
        <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto leading-relaxed">
          Create voice-first agents that collect information through natural conversation. 
          Replace boring forms with intelligent interviews.
        </p>

        <button
          onClick={() => navigate('/builder')}
          className="group relative inline-flex items-center gap-3 bg-gray-900 text-white px-8 py-4 rounded-full font-bold text-lg shadow-xl hover:bg-black hover:scale-105 transition-all duration-300 active:scale-95"
        >
          Get Started - It's Free
          <ArrowRight className="group-hover:translate-x-1 transition-transform" />
          <div className="absolute inset-0 rounded-full ring-4 ring-white/20 group-hover:ring-white/40 transition-all" />
        </button>

        {/* Templates */}
        <div className="mt-20 w-full">
          <div className="flex items-center gap-4 mb-8">
            <div className="h-px bg-gray-200 flex-1"></div>
            <span className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Or start with a template</span>
            <div className="h-px bg-gray-200 flex-1"></div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {TEMPLATES.map((t) => (
              <button
                key={t.id}
                onClick={() => navigate('/builder', { state: { template: t.id } })}
                className="group p-4 bg-white rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-md text-left transition-all"
              >
                <div className="w-10 h-10 bg-gray-50 rounded-lg flex items-center justify-center text-gray-500 group-hover:bg-primary-50 group-hover:text-primary-600 mb-3 transition-colors">
                  <t.icon size={20} />
                </div>
                <h3 className="font-bold text-gray-900 group-hover:text-primary-700 transition-colors">{t.label}</h3>
                <p className="text-sm text-gray-500">{t.desc}</p>
              </button>
            ))}
          </div>
        </div>

        <p className="mt-12 text-sm text-gray-400">
          💰 Typical cost: ~$0.08-0.15 per conversation
        </p>
      </main>
    </div>
  );
};
