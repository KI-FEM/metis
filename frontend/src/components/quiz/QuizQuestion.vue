<script setup lang="ts">
  import { computed } from 'vue';
  import MultipleChoiceQuestion from './question-types/MultipleChoiceQuestion.vue';
  import SliderQuestion from './question-types/SliderQuestion.vue';
  import TextQuestion from './question-types/TextQuestion.vue';
  import FillInBlanksQuestion from './question-types/FillInBlanksQuestion.vue';
  import type { QuizAnswer, QuizQuestion } from '@/types';


  interface Props {
    /** The quiz question object containing the question data */
    question: QuizQuestion;
    /** Optional current question number for display purposes */
    questionNumber?: number;
    /** Optional total number of questions in the quiz */
    totalQuestions?: number;
  }

  const props = defineProps<Props>();

  const emit = defineEmits<{
    answerChange: [questionId: number, answer: QuizAnswer];
  }>();

  const handleAnswerChange = (answer: QuizAnswer) => {
    emit('answerChange', props.question.id, answer);
  };


  const questionId = computed(() => `question-${props.question.id}`);
  const feedbackId = computed(() => `feedback-${props.question.id}`);

  const ariaLabel = computed(() => {
    if (props.questionNumber && props.totalQuestions) {
      return `Frage ${props.questionNumber} von ${props.totalQuestions}: ${props.question.title}`;
    }
    return props.question.title;
  });
</script>

<template>
  <section :id="questionId" :aria-labelledby="`${questionId}-title`" class="quiz-question--wrapper">
    <div class="quiz-question--response-wrapper quiz-message message-user">
      <h2 :id="`${questionId}-title`" class="quiz-question--question-headline">
        {{ question.title }}
      </h2>
      <p v-if="question.type != 'fill-in-the-blanks'" class="quiz-question--question-text">
        {{ question.text }}
      </p>
      <FillInBlanksQuestion v-if="question.type=='fill-in-the-blanks'"
                            :model-value="question.answer"
                            :question="question"
                            :question-id="questionId"
                            @update:model-value="handleAnswerChange" />
      <MultipleChoiceQuestion v-else-if="question.type=='multiple-choice'"
                              :model-value="question.answer"
                              :question="question"
                              :question-id="questionId"
                              @update:model-value="handleAnswerChange" />
      <SliderQuestion v-else-if="question.type=='slider'"
                      :model-value="question.answer"
                      :question="question"
                      :question-id="questionId"
                      @update:model-value="handleAnswerChange" />
      <TextQuestion v-else-if="question.type=='free-text'"
                    :model-value="question.answer"
                    :question="question"
                    :question-id="questionId"
                    @update:model-value="handleAnswerChange" />
      <div v-if="question.feedback"
           :id="feedbackId"
           aria-live="polite"
           class="sr-only"
           role="status">
        {{ question.feedback }}
      </div>
    </div>
  </section>
</template>

<style scoped lang="scss">
.quiz-question {
  flex: 1; 
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 2rem;
  background: #e9eef3;
  border-radius: 0.75rem;
  min-height: 250px;
}

.quiz-question--wrapper {
  & > * {
    text-align: left;

    .quiz-question--question-headline {
      margin-top: 0;
      margin-bottom: 1rem;
      font-weight: 700;
      font-size: 1.5rem;
      color: inherit;
    }

    .quiz-question--question-text {
      margin: 0 0 1rem 0;
    }
  }
}

.quiz-question--response-wrapper {
  margin-top: 1rem;    
  margin-left: 10rem; 
}

.quiz-question--response-wrapper textarea,
.quiz-question--response-wrapper input {
  width: 95%;
  min-height: 44px;
}

.quiz-message {
  max-width: 75%;
  border-radius: 20px !important;
  $sender-border-radius: 8px;
  padding: 1rem;

  &.message-bot {
    background: rgb(var(--v-theme-surface-container-high)) !important;
    color: rgb(var(--v-theme-on-surface)) !important;
    border-bottom-left-radius: $sender-border-radius !important;
    align-self: start;
  }

  &.message-user {
    background: rgb(var(--v-theme-secondary)) !important;
    color: rgb(var(--v-theme-on-secondary)) !important;
    border-bottom-right-radius: $sender-border-radius !important;
    align-self: end;
  }
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
</style>