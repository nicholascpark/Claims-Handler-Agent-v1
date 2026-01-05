import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChatInterface } from '../components/ChatInterface';
import { CostMeter } from '../components/settings/CostMeter';
import { useFormBuilderStore } from '../stores/formBuilderStore';
import { ArrowLeft } from 'lucide-react';

export const Test = () => {
  const { formId } = useParams();
  const navigate = useNavigate();
  const { config } = useFormBuilderStore(); // In real app, load from API by ID
  const [duration, setDuration] = useState(0);

  // Simple timer for cost estimation demo
  useEffect(() => {
    const timer = setInterval(() => {
      setDuration(d => d + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="h-screen bg-gray-100 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
        <button 
          onClick={() => navigate('/builder')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 font-medium text-sm"
        >
          <ArrowLeft size={16} /> Back to Builder
        </button>
        <div className="font-semibold text-gray-900">Test Mode: {config.businessName}</div>
        <div className="w-24"></div> {/* Spacer */}
      </header>

      <div className="flex-1 relative overflow-hidden flex">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col h-full max-w-3xl mx-auto bg-white shadow-2xl my-4 rounded-2xl overflow-hidden border border-gray-200">
           <ChatInterface formId={formId} className="flex flex-col h-full relative bg-white" />
        </div>

        {/* Floating Cost Meter */}
        <div className="absolute top-6 right-6">
          <CostMeter durationSeconds={duration} />
        </div>
      </div>
    </div>
  );
};
