export type BaseQuestion = {
  id: number;
  title: string;
  text: string;
  maxPoints: number;
  hint?: string;
  solution?: string;
};

export type MultipleChoiceQuestion = BaseQuestion & {
  type: "multiple-choice";
  options: string[];
  correctAnswer: string;
};

export type SliderQuestion = BaseQuestion & {
  type: "slider";
  min: number;
  max: number;
  step: number;
  correctAnswer: number;
};

export type TextQuestion = BaseQuestion & {
  type: "text";
  placeholder: string;
};

export type FillInBlanksQuestion = BaseQuestion & {
  type: "fill-in-blanks";
  template: string;
  blanks: string[];
};

export type Question =
  | MultipleChoiceQuestion
  | SliderQuestion
  | TextQuestion
  | FillInBlanksQuestion;


/**
 * 0 = unanswered
 * 1 = answered
 */
export type QuestionState = 0 | 1

export type BaseAnswer = {
  questionId: number;
  /**
   * a value between 0 and 1 signifying correctness.
   * 0 = incorrect
   * 1 = correct
   * values in between signify partial correctness. (E.g. In freetext answers, the answer could miss some key facts.)
   */
  correctness: number;
};

export type MultipleChoiceAnswer = BaseAnswer & {
  answer: string;
};

export type SliderAnswer = BaseAnswer & {
  answer: number;
};

export type TextAnswer = BaseAnswer & {
  answer: string;
};

export type FillInBlanksAnswer = BaseAnswer & {
  answer: string[];
};

export type Answer = MultipleChoiceAnswer | SliderAnswer | TextAnswer | FillInBlanksAnswer;

export type Quiz = {
  id: number;
  title: string;
  questions: Question[];
  answers: Answer[]
  maxPoints: number; // sum of all question.maxPoints
  reachedPoints: number; // sum composed of question.maxPoints * answer.correctness
}