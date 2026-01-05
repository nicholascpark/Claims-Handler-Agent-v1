import React, { useState } from 'react';
import { useFormBuilderStore } from '../../stores/formBuilderStore';
import { ArrowLeft, ArrowRight, Play, Pause, Bot, MessageSquare } from 'lucide-react';
import { clsx } from 'clsx';

const TONES = [
  { id: 'professional', label: 'Professional', desc: 'Formal and efficient' },
  { id: 'friendly', label: 'Friendly', desc: 'Warm and approachable' },
  { id: 'empathetic', label: 'Empathetic', desc: 'Caring and understanding' },
  { id: 'casual', label: 'Casual', desc: 'Relaxed and informal' },
];

const VOICES = [
  { id: 'nova', name: 'Nova', gender: 'Female', desc: 'Energetic' },
  { id: 'alloy', name: 'Alloy', gender: 'Neutral', desc: 'Versatile' },
  { id: 'echo', name: 'Echo', gender: 'Male', desc: 'Soft' },
  { id: 'onyx', name: 'Onyx', gender: 'Male', desc: 'Deep' },
  { id: 'shimmer', name: 'Shimmer', gender: 'Female', desc: 'Clear' },
];

export const AgentStep = () => {
  const { config, updateAgent, nextStep, prevStep } = useFormBuilderStore();
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);

  // Mock audio play function - in real app would use Audio API
  const toggleAudio = (voiceId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (playingVoice === voiceId) {
      setPlayingVoice(null);
      // Stop audio logic here
    } else {
      setPlayingVoice(voiceId);
      // Start audio logic here
      setTimeout(() => setPlayingVoice(null), 3000); // Mock stop after 3s
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900">Customize your AI agent</h2>
        <p className="text-gray-500 mt-2">Give your agent a personality and voice.</p>
      </div>

      <div className="space-y-8 bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
        
        {/* Agent Name */}
        <div className="space-y-3">
          <label className="block text-sm font-semibold text-gray-700">Agent Name</label>
          <div className="relative">
            <Bot className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input
              type="text"
              value={config.agentName}
              onChange={(e) => updateAgent({ agentName: e.target.value })}
              className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all outline-none"
              placeholder="e.g. Alex"
            />
          </div>
        </div>

        {/* Tone */}
        <div className="space-y-3">
          <label className="block text-sm font-semibold text-gray-700">Conversation Style</label>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {TONES.map((tone) => (
              <button
                key={tone.id}
                onClick={() => updateAgent({ agentTone: tone.id })}
                className={clsx(
                  "flex flex-col items-center justify-center p-3 rounded-xl border transition-all duration-200 text-center gap-1",
                  config.agentTone === tone.id
                    ? "border-primary-500 bg-primary-50 text-primary-700 shadow-sm ring-1 ring-primary-500"
                    : "border-gray-200 hover:border-primary-200 hover:bg-gray-50 text-gray-600"
                )}
              >
                <span className="font-medium text-sm">{tone.label}</span>
                <span className="text-[10px] opacity-70 leading-tight">{tone.desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Voice */}
        <div className="space-y-3">
          <label className="block text-sm font-semibold text-gray-700">Voice</label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {VOICES.map((voice) => (
              <div
                key={voice.id}
                onClick={() => updateAgent({ agentVoice: voice.id })}
                className={clsx(
                  "relative flex items-center p-3 rounded-xl border cursor-pointer transition-all duration-200 gap-3",
                  config.agentVoice === voice.id
                    ? "border-primary-500 bg-primary-50 ring-1 ring-primary-500"
                    : "border-gray-200 hover:border-primary-200 hover:bg-gray-50"
                )}
              >
                <button
                  onClick={(e) => toggleAudio(voice.id, e)}
                  className="w-8 h-8 flex items-center justify-center rounded-full bg-white border border-gray-200 shadow-sm text-primary-600 hover:scale-105 transition-transform"
                >
                  {playingVoice === voice.id ? <Pause size={14} fill="currentColor" /> : <Play size={14} fill="currentColor" />}
                </button>
                <div className="flex flex-col">
                  <span className={clsx("text-sm font-medium", config.agentVoice === voice.id ? "text-primary-900" : "text-gray-900")}>
                    {voice.name}
                  </span>
                  <span className="text-xs text-gray-500">{voice.gender}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Greeting */}
        <div className="space-y-3">
          <label className="block text-sm font-semibold text-gray-700">
            Custom Greeting 
            <span className="text-gray-400 font-normal ml-2">(Optional)</span>
          </label>
          <div className="relative">
            <MessageSquare className="absolute left-3 top-4 text-gray-400" size={18} />
            <textarea
              value={config.greeting || ''}
              onChange={(e) => updateAgent({ greeting: e.target.value })}
              className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all outline-none min-h-[80px] text-sm"
              placeholder="Hi, this is Alex from Smith Law Firm. How can I help you today?"
            />
          </div>
          <p className="text-xs text-gray-500">If left blank, AI will generate a greeting based on your settings.</p>
        </div>

      </div>

      <div className="flex justify-between">
        <button
          onClick={prevStep}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 px-4 py-3 font-medium transition-colors"
        >
          <ArrowLeft size={18} />
          Back
        </button>
        <button
          onClick={nextStep}
          className="group flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-6 py-3 rounded-xl font-medium transition-all shadow-md hover:shadow-lg active:scale-95"
        >
          Next: Fields
          <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </div>
  );
};
