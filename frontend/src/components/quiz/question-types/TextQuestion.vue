<script setup lang="ts">
  import type { components } from '@/types_api';
  import { ref, watch } from 'vue';

  interface Props {
    question: components['schemas']['TextQuestion'];
    modelValue?: string | undefined | null;
    disabled?: boolean;
    questionId?: string;
  }

  const props = defineProps<Props>();
  const emit = defineEmits<{
    'update:modelValue': [value: string];
  }>();

  const textValue = ref(props.modelValue || '');

  watch(() => props.modelValue, (newValue) => {
    textValue.value = newValue || '';
  });

  const handleTextChange = (value: string) => {
    if (props.disabled) return;
    textValue.value = value;
    emit('update:modelValue', value);
  };

  const maxLength = 2000;
  const inputId = props.questionId ? `${props.questionId}-input` : 'text-input';
</script>

<template>
  <div class="text-question">
    <div class="text-input-container">
      <label class="sr-only" :for="inputId">{{ question.placeholder || $t('quiz.defaultPlaceholder') }}</label>
      <textarea :id="inputId"
                :aria-describedby="`${inputId}-count`"
                class="text-input"
                :disabled="disabled"
                :maxlength="maxLength"
                :placeholder="question.placeholder || $t('quiz.defaultPlaceholder')"
                rows="4"
                :value="textValue"
                @input="(e) => handleTextChange((e.target as HTMLTextAreaElement).value)" />
    </div>
    <div :id="`${inputId}-count`" aria-live="polite" class="character-count">
      {{ textValue.length }} / {{ maxLength }} {{ $t('quiz.characters') }}
    </div>
  </div>
</template>

<style scoped lang="scss">
.text-question {
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.text-input-container {
  margin-bottom: 0.5rem;
}

.text-input {
  width: 95%;
  padding: 12px 16px;
  border: 2px solid currentColor;
  border-radius: 8px;
  background-color: transparent;
  color: inherit;
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
  min-height: 100px;
  min-width: 100px;
  
  &:focus {
    outline: 2px solid currentColor;
    outline-offset: 2px;
  }
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  
  &::placeholder {
    font-style: italic;
    opacity: 0.7;
  }
}

.character-count {
  text-align: right;
  font-size: 0.875rem;
  color: inherit;
  opacity: 0.7;
  margin-top: 0.5rem;
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