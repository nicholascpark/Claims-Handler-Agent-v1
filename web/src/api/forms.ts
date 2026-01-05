import { FormConfigCreate, FormConfigUpdate } from '../types/form';

const API_BASE = '/api';

export const formsApi = {
  // Templates
  getTemplates: () => fetch(`${API_BASE}/forms/templates`).then(r => r.json()),
  getTemplate: (industry: string) => fetch(`${API_BASE}/forms/templates/${industry}`).then(r => r.json()),
  createFromTemplate: (industry: string, businessName: string) => 
    fetch(`${API_BASE}/forms/from-template/${industry}?business_name=${encodeURIComponent(businessName)}`, 
      { method: 'POST' }).then(r => r.json()),
  
  // CRUD
  createForm: (data: FormConfigCreate) => 
    fetch(`${API_BASE}/forms/`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) }).then(r => r.json()),
  getForm: (id: string) => fetch(`${API_BASE}/forms/${id}`).then(r => r.json()),
  updateForm: (id: string, data: FormConfigUpdate) => 
    fetch(`${API_BASE}/forms/${id}`, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) }).then(r => r.json()),
  
  // Meta
  getFieldTypes: () => fetch(`${API_BASE}/forms/meta/field-types`).then(r => r.json()),
  getIndustries: () => fetch(`${API_BASE}/forms/meta/industries`).then(r => r.json()),
  getTones: () => fetch(`${API_BASE}/forms/meta/tones`).then(r => r.json()),
  getVoices: () => fetch(`${API_BASE}/forms/meta/voices`).then(r => r.json()),
};

export const settingsApi = {
  getApiKeyStatus: () => fetch(`${API_BASE}/settings/api-key/status`).then(r => r.json()),
  setApiKey: (apiKey: string) => 
    fetch(`${API_BASE}/settings/api-key`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ api_key: apiKey }) }).then(r => r.json()),
  testApiKey: (apiKey: string) => 
    fetch(`${API_BASE}/settings/api-key/test`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ api_key: apiKey }) }).then(r => r.json()),
  getCostEstimate: (turns?: number) => fetch(`${API_BASE}/settings/cost-estimate?turns=${turns || 5}`).then(r => r.json()),
  getPricing: () => fetch(`${API_BASE}/settings/pricing`).then(r => r.json()),
};
