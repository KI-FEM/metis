import type {components} from '@/types_api';

export type Locale = 'en' | 'de';
export type LocalizedString = Record<Locale, string>;

export type LearningType = components['schemas']['LearningTypeModel']

export type Module = components['schemas']['Module']

export type Topic = components['schemas']['TopicModel']

export type ActionButton = components['schemas']['Button']

export type ExtendedMetaInformation = components['schemas']['MetaInformation'] & {
  isInspiration?: boolean;
  sources: {
    [key: number]: components['schemas']['Source'];
  };
  trace_id?: string;
  [key: string]: unknown; // and any additional properties
}
export type ChatMessageMessage = components['schemas']['MessageResponse'] & {
  fragment: false;
  complete: boolean;
  timestamp: string;
  summary?: string;
  meta_information: ExtendedMetaInformation;
  events?: ChatMessageEvent[];
}

export type QuizState = 'loading' | 'ready' | 'complete' | 'error';

export type ChatMessageFragment = components['schemas']['MessageResponse']  & {
  fragment: true;
  meta_information: ExtendedMetaInformation;
  timestamp: string;
  quizId: string;
}

export type ChatMessage = ChatMessageMessage | ChatMessageFragment;
export type QuizAnswer = components['schemas']['QuizModel']['questions'][0]['answer'];
export type Quiz = components['schemas']['QuizModel'] & {
  questions: QuizQuestion[];
  events: QuizEvents[];
  state: QuizState;
  messages: ChatMessageMessage[];
};

export type QuizQuestion = components['schemas']['QuizModel']['questions'][0]

export type ChatMessageEvent = {
  timestamp: string;
  event: "tool_completed" 
        | "created_todo_list" 
        | "think" 
        | "retrieve_additional_information" 
        | "formulate_answer" 
        | "starting_agent" 
        | "initial_metadata" 
        | "update_conversation_strategy"
        | "updated_conversation_strategy"
        | "update_memory" 
        | "update_learner_model"
        | "get_relevant_learning_units";
  additional_info?: { [key: string]: unknown; };
}

export type QuizEvents = {
  timestamp: string;
  event: "quiz_generation_started" 
        | "quiz_generated"
        | "quiz_verified"
        | "question_answered" 
        | "quiz_completed";
  additional_info?: { [key: string]: unknown; };
}

export interface Chat {
  id: string;
  title: string;
  language: Locale;
  topic: Topic;
  messages: ChatMessage[];
  quiz?: Quiz[];
  storage: components['schemas']['RequestModel']['storage'];
}

export interface ChoiceDelta {
  content?: string;
  storage?: components['schemas']['RequestModel']['storage'];
  instructions?: string[];
  type?: string;
  thoughts?: string;
  buttons?: components['schemas']['Button'][];
  sources?: { [key: string]: components['schemas']['Source']; };
  llm_model?: string;
  citations?: number[];
  trace_id?: string;
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
