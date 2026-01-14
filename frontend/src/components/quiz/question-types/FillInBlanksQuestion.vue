<script setup lang="ts">
  import type { components } from '@/types_api';
  import { ref, computed, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  const props = defineProps<Props>();

  const emit = defineEmits<{
    'update:modelValue': [value: string[]];
  }>();

  const { t } = useI18n();

  interface Props {
    /**
     * The fill-in-the-blanks question object containing the question data
     */
    question: components['schemas']['FillInTheBlanksQuestion'];
    /**
     * The user's current answers for the blanks
     */
    modelValue?: string[] | null | undefined;
    /**
     * Optional flag to disable interaction with the question
     */
    disabled?: boolean;
    /**
     * Optional question ID for generating unique element IDs
     */
    questionId?: string;
  }

  const blankAnswers = ref<string[]>(props.modelValue || new Array(props.question.solution?.length || 0).fill(''));

  watch(() => props.modelValue, (newValue) => {
    blankAnswers.value = newValue || new Array(props.question.solution?.length || 0).fill('');
  });

  const templateParts = computed(() => {
    if (!props.question.template) {
      return [props.question.text || ''];
    }
    const parts = props.question.template.split('{}');
    return parts;
  });

  const handleBlankChange = (index: number, value: string) => {
    if (props.disabled) return;
    blankAnswers.value[index] = value;
    emit('update:modelValue', [...blankAnswers.value]);
  };

  const getBlankLabel = (index: number) => {
    return t('quiz.fillInBlanksPlaceholder', { number: index + 1 });
  };

  const getBlankId = (index: number) => {
    return props.questionId ? `${props.questionId}-blank-${index}` : `blank-${index}`;
  };
</script>

<template>
  <div class="fill-in-blanks-question">
    <div class="template-container">
      <div class="template-text-block">
        <template v-for="(part, index) in templateParts" :key="index">
          <span class="text-part">{{ part }}</span>
          <template v-if="index < templateParts.length - 1">
            <label class="sr-only" :for="getBlankId(index)">{{ getBlankLabel(index) }}</label>
            <input :id="getBlankId(index)"
                   :aria-label="getBlankLabel(index)"
                   class="blank-input"
                   :disabled="disabled"
                   type="text"
                   :value="blankAnswers[index]"
                   @input="(e) => handleBlankChange(index, (e.target as HTMLInputElement).value)">
          </template>
        </template>
      </div>
    </div>
    
    <div v-if="question.solution && question.solution.length > 0" class="blanks-info">
      <p class="blanks-hint">
        {{ $t('quiz.fillInBlanksHint', { count: question.solution.length }) }}
      </p>
    </div>
  </div>
</template>

<style scoped lang="scss">
.fill-in-blanks-question {
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.template-container {
  background: transparent;
  border-radius: 12px;
  padding: 0;
  margin-bottom: 1rem;
  color: inherit;
  line-height: 1.8;
}

.template-text-block {
  font-size: 1rem;
  line-height: 1.8;
  word-break: break-word;
}

.text-part {
  color: inherit;
  font-size: 1rem;
  line-height: 1.8;
}

.blank-input {
  display: inline-block;
  border-radius: 4px;
  border: 2px solid currentColor;
  padding: 8px 12px;
  margin: 4px 2px;
  color: inherit;
  font-size: 1rem;
  width: 140px;
  max-width: 180px;
  font-family: inherit;
  vertical-align: middle;
  min-height: 44px;
  
  &:focus {
    outline: 2px solid currentColor;
    outline-offset: 2px;
  }
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  
  &::placeholder {
    color: inherit;
    opacity: 0.5;
    font-style: italic;
  }
}

.blanks-info {
  margin-top: 1rem;
}

.blanks-hint {
  font-size: 0.875rem;
  color: inherit;
  font-style: italic;
  margin: 0;
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