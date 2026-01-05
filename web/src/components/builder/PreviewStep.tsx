import { useEffect, useState } from 'react';
import { useFormBuilderStore } from '../../stores/formBuilderStore';
import { ArrowLeft, Save, Play } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const PreviewStep = () => {
  const { config, prevStep, saveForm, isLoading } = useFormBuilderStore();
  const navigate = useNavigate();
  const [costEstimate, setCostEstimate] = useState<{min: number, max: number}>({ min: 0.08, max: 0.12 });

  useEffect(() => {
    // Simple cost estimation logic based on field count
    const baseCost = 0.05;
    const costPerField = 0.015;
    const totalFields = config.fields.length;
    const min = baseCost + (totalFields * costPerField * 0.8);
    const max = baseCost + (totalFields * costPerField * 1.2);
    setCostEstimate({ min: Number(min.toFixed(2)), max: Number(max.toFixed(2)) });
  }, [config.fields.length]);

  const handleSave = async () => {
    try {
      await saveForm();
      // Only navigate if save is successful
      navigate('/'); 
    } catch (error) {
      console.error(error);
    }
  };

  const handleTest = async () => {
    try {
      const id = await saveForm();
      navigate(`/test/${id}`);
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Ready to launch?</h2>
        <p className="text-gray-500 mt-2">Review your configuration and test the agent.</p>
      </div>

      <div className="grid gap-6">
        {/* Summary Card */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
            <span className="text-xl">📋</span> Configuration Summary
          </h3>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between py-2 border-b border-gray-50">
              <span className="text-gray-500">Business</span>
              <span className="font-medium text-gray-900">{config.businessName}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-50">
              <span className="text-gray-500">Industry</span>
              <span className="font-medium text-gray-900">{config.industry}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-50">
              <span className="text-gray-500">Agent</span>
              <span className="font-medium text-gray-900">
                {config.agentName} <span className="text-gray-400">({config.agentTone})</span>
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-50">
              <span className="text-gray-500">Fields to Collect</span>
              <span className="font-medium text-gray-900">
                {config.fields.filter(f => f.required).length} Required, {config.fields.filter(f => !f.required).length} Optional
              </span>
            </div>
            <div className="pt-2 text-xs text-gray-400">
              ID: {config.id || 'Not saved yet'}
            </div>
          </div>
        </div>

        {/* Test Card */}
        <div className="bg-gradient-to-br from-primary-900 to-primary-800 p-6 rounded-2xl shadow-lg text-white relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white opacity-5 rounded-full -translate-y-1/2 translate-x-1/3 blur-3xl group-hover:opacity-10 transition-opacity"></div>
          
          <div className="relative z-10 text-center space-y-6 py-4">
            <div>
              <h3 className="text-2xl font-bold mb-2">Test Your Agent</h3>
              <p className="text-primary-100 opacity-90">Have a real conversation to see how it performs.</p>
            </div>

            <button
              onClick={handleTest}
              className="inline-flex items-center gap-2 bg-white text-primary-900 px-8 py-4 rounded-full font-bold shadow-lg hover:scale-105 active:scale-95 transition-all"
            >
              <Play size={20} fill="currentColor" />
              Start Test Call
            </button>
            
            <p className="text-xs text-primary-200">
              No real data will be saved during test mode.
            </p>
          </div>
        </div>

        {/* Cost Estimate */}
        <div className="text-center text-sm text-gray-500 bg-gray-50 py-3 rounded-xl border border-gray-100">
          💰 Estimated cost per conversation: <span className="font-semibold text-gray-900">${costEstimate.min} - ${costEstimate.max}</span>
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <button
          onClick={prevStep}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 px-4 py-3 font-medium transition-colors"
        >
          <ArrowLeft size={18} />
          Back
        </button>
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="group flex items-center gap-2 bg-gray-900 hover:bg-black text-white px-8 py-3 rounded-xl font-medium transition-all shadow-md hover:shadow-lg active:scale-95 disabled:opacity-70"
        >
          {isLoading ? (
            <span className="animate-pulse">Saving...</span>
          ) : (
            <>
              <Save size={18} />
              Save Configuration
            </>
          )}
        </button>
      </div>
    </div>
  );
};
