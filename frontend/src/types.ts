import type { components } from '@/types_api'

export type Locale = 'en' | 'de';

export type LearningType = components['schemas']['LearningTypeModel']

export type Module = components['schemas']['Module']

export type Topic = components['schemas']['TopicModel']

export type ActionButton = components["schemas"]["Button"]

export type ExtendedMetaInformation = components['schemas']['MetaInformation'] & {
  isInspiration?: boolean;
  [key: string]: unknown; // and any additional properties
}

export type ChatMessage = components['schemas']['MessageResponse'] & {
  complete: boolean;
  timestamp: string;
  summary?: string;
  meta_information: ExtendedMetaInformation;
}

export interface Chat {
  id: string;
  title: string;
  language: Locale;
  topic: Topic;
  messages: ChatMessage[];
  storage: Record<string, string>;
}

export interface ChoiceDelta {
  content?: string;
  storage?: Record<string, string>;
  instructions?: string[];
  sender?: string;
  thoughts?: string;
  buttons?: components['schemas']['Button'][];
  sources?: { [key: string]: components["schemas"]["Source"]; };
  llm_model?: string;
  citations?: number[];
}

export interface Choice {
  delta: ChoiceDelta;
  finish_reason: string;
}

export interface ChatCompletionsChunk {
  id: string;
  choices: Choice[];
  created: string;
}
