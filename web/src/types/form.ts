export type FieldType = 'text' | 'number' | 'email' | 'phone' | 'date' | 'select' | 'boolean';

export interface FieldOption {
  label: string;
  value: string;
}

export interface FormField {
  id: string;
  label: string;
  type: FieldType;
  description: string; // The "help text" or question AI asks
  required: boolean;
  options?: FieldOption[]; // For select type
}

export interface FormConfig {
  id?: string;
  businessName: string;
  industry: string;
  description: string;
  agentName: string;
  agentTone: string;
  agentVoice: string;
  greeting?: string;
  fields: FormField[];
  createdAt?: string;
  updatedAt?: string;
}

export interface FormTemplate {
  id: string;
  name: string;
  description: string;
  industry: string;
  config: Partial<FormConfig>;
}

export interface FormConfigCreate extends Omit<FormConfig, 'id' | 'createdAt' | 'updatedAt'> {}
export interface FormConfigUpdate extends Partial<FormConfigCreate> {}
