export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ClaimPayload {
  incident_date?: string;
  incident_time?: string;
  incident_location?: string;
  vehicle_info?: string;
  damage_description?: string;
  injury_info?: string;
  police_report?: string;
  other_party_info?: string;
  [key: string]: any;
}

export interface ChatResponse {
  message: string;
  chat_history: ChatMessage[];
  payload: ClaimPayload;
  is_form_complete: boolean;
  thread_id: string;
  audio_data?: string; // base64 encoded MP3
  language: string;
  processing_time?: number;
}
