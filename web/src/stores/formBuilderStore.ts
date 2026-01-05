import { create } from 'zustand';
import { FormConfig, FormField } from '../types/form';
import { formsApi } from '../api/forms';

interface FormBuilderState {
  currentStep: number;
  config: FormConfig;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setStep: (step: number) => void;
  nextStep: () => void;
  prevStep: () => void;
  
  updateBusiness: (data: Partial<Pick<FormConfig, 'businessName' | 'industry' | 'description'>>) => void;
  updateAgent: (data: Partial<Pick<FormConfig, 'agentName' | 'agentTone' | 'agentVoice' | 'greeting'>>) => void;
  
  addField: (field: FormField) => void;
  updateField: (id: string, field: Partial<FormField>) => void;
  removeField: (id: string) => void;
  setFields: (fields: FormField[]) => void;
  reorderFields: (fields: FormField[]) => void;
  
  resetForm: () => void;
  loadTemplate: (industry: string) => Promise<void>;
  saveForm: () => Promise<string>; // Returns form ID
}

const INITIAL_CONFIG: FormConfig = {
  businessName: '',
  industry: '',
  description: '',
  agentName: 'Assistant',
  agentTone: 'professional',
  agentVoice: 'alloy',
  greeting: '',
  fields: []
};

export const useFormBuilderStore = create<FormBuilderState>((set, get) => ({
  currentStep: 1,
  config: INITIAL_CONFIG,
  isLoading: false,
  error: null,

  setStep: (step) => set({ currentStep: step }),
  
  nextStep: () => set((state) => ({ currentStep: Math.min(state.currentStep + 1, 4) })),
  
  prevStep: () => set((state) => ({ currentStep: Math.max(state.currentStep - 1, 1) })),

  updateBusiness: (data) => set((state) => ({
    config: { ...state.config, ...data }
  })),

  updateAgent: (data) => set((state) => ({
    config: { ...state.config, ...data }
  })),

  addField: (field) => set((state) => ({
    config: { ...state.config, fields: [...state.config.fields, field] }
  })),

  updateField: (id, fieldData) => set((state) => ({
    config: {
      ...state.config,
      fields: state.config.fields.map((f) => 
        f.id === id ? { ...f, ...fieldData } : f
      )
    }
  })),

  removeField: (id) => set((state) => ({
    config: {
      ...state.config,
      fields: state.config.fields.filter((f) => f.id !== id)
    }
  })),

  setFields: (fields) => set((state) => ({
    config: { ...state.config, fields }
  })),

  reorderFields: (fields) => set((state) => ({
    config: { ...state.config, fields }
  })),

  resetForm: () => set({ 
    currentStep: 1, 
    config: INITIAL_CONFIG, 
    error: null 
  }),

  loadTemplate: async (industry) => {
    set({ isLoading: true, error: null });
    try {
      // In a real app, we'd fetch from API. For now we simulate or use the API if ready
      // const template = await formsApi.getTemplate(industry);
      // For the UI demo, we'll just set some defaults based on industry
      // But let's try to use the API structure if possible, or fallback
      
      const newConfig = { ...INITIAL_CONFIG, industry };
      
      // Basic local templates if API fails or for speed in this demo
      if (industry.toLowerCase().includes('health')) {
         newConfig.fields = [
           { id: '1', label: 'Patient Name', type: 'text', description: 'What is your full name?', required: true },
           { id: '2', label: 'Date of Birth', type: 'date', description: 'What is your date of birth?', required: true },
           { id: '3', label: 'Reason for Visit', type: 'text', description: 'What is the main reason for your visit today?', required: true }
         ];
         newConfig.agentTone = 'empathetic';
         newConfig.agentName = 'Sarah';
      } else if (industry.toLowerCase().includes('legal')) {
         newConfig.fields = [
           { id: '1', label: 'Client Name', type: 'text', description: 'What is your full name?', required: true },
           { id: '2', label: 'Case Type', type: 'select', description: 'What type of legal assistance do you need?', required: true, options: [{label: 'Family Law', value: 'family'}, {label: 'Criminal Defense', value: 'criminal'}, {label: 'Personal Injury', value: 'injury'}] },
           { id: '3', label: 'Incident Date', type: 'date', description: 'When did the incident occur?', required: false }
         ];
         newConfig.agentTone = 'professional';
         newConfig.agentName = 'James';
      }

      set({ config: newConfig });
    } catch (err) {
      set({ error: 'Failed to load template' });
    } finally {
      set({ isLoading: false });
    }
  },

  saveForm: async () => {
    set({ isLoading: true, error: null });
    try {
      const config = get().config;
      // If we have an ID, update, else create
      let result;
      if (config.id) {
        result = await formsApi.updateForm(config.id, config);
      } else {
        result = await formsApi.createForm(config);
      }
      return result.id;
    } catch (err) {
      set({ error: 'Failed to save form' });
      throw err;
    } finally {
      set({ isLoading: false });
    }
  }
}));
