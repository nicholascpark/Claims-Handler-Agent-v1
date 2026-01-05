import { useFormBuilderStore } from '../../stores/formBuilderStore';
import { Check } from 'lucide-react';
import { clsx } from 'clsx';

const steps = [
  { number: 1, title: 'Business' },
  { number: 2, title: 'Agent' },
  { number: 3, title: 'Fields' },
  { number: 4, title: 'Preview' },
];

export const StepIndicator = () => {
  const { currentStep } = useFormBuilderStore();

  return (
    <div className="w-full mb-8">
      <div className="relative flex items-center justify-between w-full max-w-2xl mx-auto">
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-gray-200 -z-10 rounded-full" />
        <div 
          className="absolute left-0 top-1/2 -translate-y-1/2 h-1 bg-primary-600 transition-all duration-500 ease-in-out -z-10 rounded-full" 
          style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }}
        />
        
        {steps.map((step) => {
          const isCompleted = step.number < currentStep;
          const isCurrent = step.number === currentStep;
          
          return (
            <div key={step.number} className="flex flex-col items-center gap-2 bg-white px-2">
              <div 
                className={clsx(
                  "w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-300",
                  isCompleted ? "bg-primary-600 border-primary-600 text-white" :
                  isCurrent ? "bg-white border-primary-600 text-primary-600" :
                  "bg-white border-gray-300 text-gray-400"
                )}
              >
                {isCompleted ? <Check size={20} /> : <span className="font-semibold">{step.number}</span>}
              </div>
              <span className={clsx(
                "text-sm font-medium transition-colors duration-300",
                isCurrent ? "text-primary-600" : "text-gray-500"
              )}>
                {step.title}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
