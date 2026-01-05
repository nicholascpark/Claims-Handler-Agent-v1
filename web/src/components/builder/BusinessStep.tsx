import React from 'react';
import { useFormBuilderStore } from '../../stores/formBuilderStore';
import { ArrowRight, Briefcase, Building, FileText } from 'lucide-react';
import { clsx } from 'clsx';

const INDUSTRIES = [
  'Legal Services',
  'Healthcare',
  'Real Estate',
  'Home Services',
  'Financial Services',
  'Recruiting',
  'Insurance',
  'Automotive',
  'Other'
];

export const BusinessStep = () => {
  const { config, updateBusiness, nextStep, loadTemplate } = useFormBuilderStore();
  const [errors, setErrors] = React.useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!config.businessName.trim()) newErrors.businessName = 'Business name is required';
    if (!config.industry) newErrors.industry = 'Industry is required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validate()) {
      nextStep();
    }
  };

  const handleIndustryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const industry = e.target.value;
    updateBusiness({ industry });
    if (industry && !config.fields.length) {
      // Auto-load template if fields are empty
      loadTemplate(industry);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900">Tell us about your business</h2>
        <p className="text-gray-500 mt-2">This helps the AI understand who it's working for.</p>
      </div>

      <div className="space-y-6 bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
        {/* Business Name */}
        <div className="space-y-2">
          <label className="block text-sm font-semibold text-gray-700">
            Business Name <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <Building className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input
              type="text"
              value={config.businessName}
              onChange={(e) => updateBusiness({ businessName: e.target.value })}
              className={clsx(
                "w-full pl-10 pr-4 py-3 rounded-xl border focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all outline-none",
                errors.businessName ? "border-red-300 bg-red-50" : "border-gray-200"
              )}
              placeholder="e.g. Smith Law Firm"
            />
          </div>
          {errors.businessName && <p className="text-red-500 text-xs mt-1">{errors.businessName}</p>}
        </div>

        {/* Industry */}
        <div className="space-y-2">
          <label className="block text-sm font-semibold text-gray-700">
            Industry <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <select
              value={config.industry}
              onChange={handleIndustryChange}
              className={clsx(
                "w-full pl-10 pr-4 py-3 rounded-xl border focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all outline-none appearance-none bg-white",
                errors.industry ? "border-red-300 bg-red-50" : "border-gray-200"
              )}
            >
              <option value="">Select your industry...</option>
              {INDUSTRIES.map(ind => (
                <option key={ind} value={ind}>{ind}</option>
              ))}
            </select>
            <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
              ▼
            </div>
          </div>
          {errors.industry && <p className="text-red-500 text-xs mt-1">{errors.industry}</p>}
        </div>

        {/* Description */}
        <div className="space-y-2">
          <label className="block text-sm font-semibold text-gray-700">
            Brief Description
            <span className="text-gray-400 font-normal ml-2">(Optional)</span>
          </label>
          <div className="relative">
            <FileText className="absolute left-3 top-4 text-gray-400" size={18} />
            <textarea
              value={config.description}
              onChange={(e) => updateBusiness({ description: e.target.value })}
              className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all outline-none min-h-[100px] resize-y"
              placeholder="e.g. We specialize in family law and estate planning..."
            />
          </div>
          <p className="text-xs text-gray-500">Helps the AI understand context and answer basic questions.</p>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleNext}
          className="group flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-6 py-3 rounded-xl font-medium transition-all shadow-md hover:shadow-lg active:scale-95"
        >
          Next: Agent Setup
          <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </div>
  );
};
