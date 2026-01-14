<script setup lang="ts">
  import type { components } from '@/types_api';
  import { ref, watch, computed } from 'vue';

  interface Props {
    question: components['schemas']['SliderQuestion'];
    modelValue?: number | undefined | null;
    disabled?: boolean;
    questionId?: string;
  }

  const props = defineProps<Props>();
  const emit = defineEmits<{
    'update:modelValue': [value: number];
  }>();

  const sliderValue = ref(props.modelValue || props.question.min);

  watch(() => props.modelValue, (newValue) => {
    sliderValue.value = newValue ?? props.question.min;
  });

  const handleSliderChange = (value: number) => {
    if (props.disabled) return;
    sliderValue.value = value;
    emit('update:modelValue', value);
  };

  const getCorrectValue = () => {
    if (!props.question.feedback) return null;
    try {
      return props.question.solution
    } catch {
      return null;
    }
  };

  const sliderId = props.questionId ? `${props.questionId}-slider` : 'slider-input';
  const descriptionId = props.questionId ? `${props.questionId}-desc` : 'slider-desc';

  const ariaLabel = computed(() => {
    return `Bewertung: ${sliderValue.value} von ${props.question.max}`;
  });
</script>

<template>
  <div class="slider-question">
    <label class="sr-only" :for="sliderId">{{ ariaLabel }}</label>
    <div class="slider-wrapper">
      <input :id="sliderId"
             :aria-describedby="descriptionId"
             :aria-label="ariaLabel"
             class="range-slider"
             :disabled="disabled || question.answered"
             :max="question.max"
             :min="question.min"
             :step="question.step || 1"
             type="range"
             :value="sliderValue"
             @input="(e) => handleSliderChange(Number((e.target as HTMLInputElement).value))">
    </div>
    <div class="slider-labels">
      <span aria-label="Minimum" class="slider-label">{{ question.min }}</span>
      <span :id="descriptionId" aria-live="polite" class="slider-value">
        {{ $t('quiz.sliderCurrentRating', { value: sliderValue }) }}
      </span>
      <span aria-label="Maximum" class="slider-label">{{ question.max }}</span>
    </div>
    <div v-if="question.feedback"
         aria-live="polite"
         class="slider-feedback"
         role="status">
      <div v-if="!question.is_correct" class="feedback-info">
        <p class="feedback-item incorrect">
          <strong>{{ $t('quiz.yourAnswer') }}:</strong> {{ modelValue }}
        </p>
        <p v-if="getCorrectValue() !== null" class="feedback-item correct">
          <strong>{{ $t('quiz.correctAnswer') }}:</strong> {{ getCorrectValue() }}
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.slider-question {
  width: 100%;
  padding: 1rem 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.slider-wrapper {
  margin: 1rem 0;
}

.range-slider {
  width: 100%;
  height: 8px;
  border-radius: 4px;
  background: linear-gradient(to right, #ddd 0%, #ddd 100%);
  outline: none;
  -webkit-appearance: none;
  appearance: none;

  &::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #1d9bf0;
    cursor: pointer;
    border: 2px solid white;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);

    &:focus-visible {
      outline: 2px solid #000;
      outline-offset: 2px;
    }
  }

  &::-moz-range-thumb {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #1d9bf0;
    cursor: pointer;
    border: 2px solid white;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);

    &:focus-visible {
      outline: 2px solid #000;
      outline-offset: 2px;
    }
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  &:focus-visible {
    outline: 2px solid #000;
    outline-offset: 2px;
  }
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1rem;
  font-size: 0.9rem;
  color: inherit;
  gap: 1rem;
}

.slider-label {
  font-weight: 500;
  flex: 0 0 auto;
}

.slider-value {
  font-weight: 600;
  color: inherit;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  flex: 1 1 auto;
  text-align: center;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.slider-feedback {
  margin-top: 1rem;
}

.feedback-info {
  background-color: rgba(255, 255, 255, 0.1);
  padding: 1rem;
  border-radius: 8px;
  border-left: 4px solid #1d9bf0;
}

.feedback-item {
  margin: 0.5rem 0;
  font-size: 0.95rem;

  &:first-child {
    margin-top: 0;
  }

  &:last-child {
    margin-bottom: 0;
  }

  &.correct {
    color: #4caf50;
    font-weight: 600;
  }

  &.incorrect {
    color: #f44336;
    font-weight: 600;
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