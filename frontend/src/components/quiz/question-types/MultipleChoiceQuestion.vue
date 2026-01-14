<script setup lang="ts">
  import type { components } from '@/types_api';

  interface Props {
    /** The multiple choice question data containing options and other question details */
    question: components['schemas']['MultipleChoiceQuestion'];
    /** The current answer to the question */
    modelValue: number[] | null | undefined;
    /** Unique identifier for the question */
    questionId?: string;
    /** Optional: disables question */
    disabled?: boolean;
  }
  
  const props = defineProps<Props>();
  const emit = defineEmits<{
    'update:model-value': [value: number[]];
  }>();

  const handleSelectionChange = (value: number) => {
    if (props.disabled) return;
    emit('update:model-value', [value]);
  };

  const getOptionClass = (option: string, index: number) => {
    if (!props.question.feedback) return '';
  
    const correctAnswer = props.question.solution;
    const userAnswer = props.modelValue;
  
    if (correctAnswer.includes(index)) {
      return 'option-correct';
    }
    if (userAnswer?.includes(index) && !props.question.is_correct) {
      return 'option-incorrect';
    }
    return '';
  };

  const getOptionAriaLabel = (index: number, option: string) => {
    return `Option ${index + 1}: ${option}`;
  };

  const fieldsetId = props.questionId ? `${props.questionId}-options` : 'options';
</script>

<template>
  <fieldset :id="fieldsetId" class="multiple-choice-question">
    <legend class="sr-only">
      {{ $t('quiz.selectAnswer') || 'Wählen Sie eine Antwort' }}
    </legend>
    <div class="options-group" role="group">
      <div v-for="(option, index) in question.options"
           :key="index"
           class="option-wrapper">
        <input :id="`${fieldsetId}-option-${index}`"
               :aria-label="getOptionAriaLabel(index, option)"
               :checked="question.answer?.includes(index)"
               :class="['option-input', getOptionClass(option, index)]"
               :disabled="disabled"
               :name="fieldsetId"
               type="radio"
               :value="index"
               @change="handleSelectionChange(index)">
        <label class="option-label"
               :class="getOptionClass(option, index)"
               :for="`${fieldsetId}-option-${index}`">
          {{ option }}
        </label>
      </div>
    </div>
  </fieldset>
</template>

<style scoped lang="scss">
.multiple-choice-question {
  width: 100%;
  border: none;
  padding: 0;
  margin: 0;
}

.options-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.option-wrapper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.option-input {
  width: 24px;
  height: 24px;
  min-width: 24px;
  min-height: 24px;
  cursor: pointer;
  accent-color: #1d9bf0;

  &:focus-visible {
    outline: 2px solid #000;
    outline-offset: 2px;
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  &.option-correct {
    accent-color: #059669;
  }

  &.option-incorrect {
    accent-color: #dc2626;
  }
}

.option-label {
  flex: 1;
  cursor: pointer;
  padding: 0.75rem;
  border-radius: 6px;
  transition: background-color 0.2s ease;
  user-select: none;
  font-weight: 500;

  .option-input:disabled ~ & {
    opacity: 0.6;
    cursor: not-allowed;
  }

  &.option-correct {
    background-color: #d1fae5;
    color: #065f46;
    border: 1px solid #6ee7b7;
  }

  &.option-incorrect {
    background-color: #fee2e2;
    color: #7f1d1d;
    border: 1px solid #fca5a5;
  }
}

.option-input:hover:not(:disabled) ~ .option-label {
  background-color: rgba(0, 0, 0, 0.05);
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