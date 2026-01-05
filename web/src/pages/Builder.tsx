import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { StepIndicator } from '../components/builder/StepIndicator';
import { BusinessStep } from '../components/builder/BusinessStep';
import { AgentStep } from '../components/builder/AgentStep';
import { FieldsStep } from '../components/builder/FieldsStep';
import { PreviewStep } from '../components/builder/PreviewStep';
import { useFormBuilderStore } from '../stores/formBuilderStore';

export const Builder = () => {
  const { currentStep, loadTemplate, resetForm } = useFormBuilderStore();
  const location = useLocation();

  useEffect(() => {
    // Reset form on mount
    resetForm();
    
    // Check for template in navigation state
    const state = location.state as { template?: string } | null;
    if (state?.template) {
      loadTemplate(state.template);
    }
  }, [location.state, resetForm, loadTemplate]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="font-bold text-lg text-gray-900">Notera Builder</div>
          <div className="text-sm text-gray-500">Draft Mode</div>
        </div>
      </header>

      <main className="flex-1 w-full max-w-4xl mx-auto px-4 py-8">
        <StepIndicator />
        
        <div className="mt-8">
          {currentStep === 1 && <BusinessStep />}
          {currentStep === 2 && <AgentStep />}
          {currentStep === 3 && <FieldsStep />}
          {currentStep === 4 && <PreviewStep />}
        </div>
      </main>
    </div>
  );
};
