import { useState } from 'react';
import { Eye, EyeOff, Check, AlertCircle } from 'lucide-react';
import { settingsApi } from '../../api/forms';
import { clsx } from 'clsx';

export const ApiKeyInput = () => {
  const [apiKey, setApiKey] = useState('');
  const [isVisible, setIsVisible] = useState(false);
  const [status, setStatus] = useState<'idle' | 'testing' | 'valid' | 'invalid'>('idle');

  const handleTest = async () => {
    if (!apiKey.trim()) return;
    setStatus('testing');
    try {
      const result = await settingsApi.testApiKey(apiKey);
      if (result.valid) {
        setStatus('valid');
        await settingsApi.setApiKey(apiKey);
      } else {
        setStatus('invalid');
      }
    } catch (e) {
      setStatus('invalid');
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm w-full">
      <div className="flex items-center justify-between mb-2">
        <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">OpenAI API Key</label>
        {status === 'valid' && <span className="text-xs text-green-600 flex items-center gap-1 font-medium"><Check size={12} /> Connected</span>}
      </div>
      
      <div className="relative">
        <input
          type={isVisible ? 'text' : 'password'}
          value={apiKey}
          onChange={(e) => {
            setApiKey(e.target.value);
            setStatus('idle');
          }}
          placeholder="sk-..."
          className={clsx(
            "w-full pl-3 pr-20 py-2 text-sm rounded-lg border focus:ring-2 focus:ring-primary-500 outline-none transition-all",
            status === 'invalid' ? "border-red-300 bg-red-50 text-red-900" : "border-gray-200"
          )}
        />
        <button
          onClick={() => setIsVisible(!isVisible)}
          className="absolute right-12 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 p-1"
        >
          {isVisible ? <EyeOff size={14} /> : <Eye size={14} />}
        </button>
        <button
          onClick={handleTest}
          disabled={!apiKey || status === 'testing'}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-medium bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded text-gray-700 transition-colors disabled:opacity-50"
        >
          {status === 'testing' ? '...' : 'Test'}
        </button>
      </div>

      {status === 'invalid' && (
        <p className="text-xs text-red-500 mt-2 flex items-center gap-1">
          <AlertCircle size={12} /> Invalid API Key
        </p>
      )}

      {status === 'idle' && !apiKey && (
        <div className="mt-3 text-xs text-gray-400 bg-gray-50 p-2 rounded border border-gray-100">
          <p className="font-medium text-gray-600 mb-1">Don't have a key?</p>
          <ol className="list-decimal list-inside space-y-0.5">
            <li>Go to platform.openai.com</li>
            <li>API Keys → Create new secret key</li>
          </ol>
        </div>
      )}
    </div>
  );
};
