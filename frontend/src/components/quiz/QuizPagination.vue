<script setup lang="ts">
  import type { QuestionState } from '@/types/Question';
  import { computed } from 'vue';

  interface Props {
    /** The current question index */
    currentIndex: number;
    /** An array representing the state of each question (e.g., answered, unanswered) */
    questionStates: QuestionState[];
  }

  const props = defineProps<Props>();

  const emit = defineEmits<{
    previous: [];
    next: [];
    goTo: [index: number];
  }>();

  const canGoPrevious = computed(() => props.currentIndex > 0);
  const canGoNext = computed(() => props.currentIndex < props.questionStates.length - 1);

  const handlePrevious = () => {
    if (canGoPrevious.value) {
      emit('previous');
    }
  };

  const handleNext = () => {
    if (canGoNext.value) {
      emit('next');
    }
  };

  const handleDotClick = (index: number) => {
    emit('goTo', index);
  };

  const getIconState = (value: QuestionState) => {
    switch (value) {
      case 0:
        return 'fa-regular fa-circle';
      case 1:
        return 'fas fa-circle';
      default:
        return 'fa-regular fa-circle';
    }
  };

  const getStateLabel = (index: number, state: QuestionState) => {
    const stateText = state === 1 ? 'beantwortet' : 'nicht beantwortet';
    return `Frage ${index + 1} von ${props.questionStates.length} - ${stateText}`;
  };

  const progressText = computed(() => {
    const answered = props.questionStates.filter((s) => s === 1).length;
    return `${answered} von ${props.questionStates.length} Fragen beantwortet`;
  });
</script>

<template>
  <nav :aria-label="$t('quizNavigationLabel')" class="quiz-pagination">
    <div aria-live="polite" class="quiz-pagination--progress" role="status">
      <span class="sr-only">{{ progressText }}</span>
    </div>

    <button :aria-label="canGoPrevious ? 'Zur vorherigen Frage' : 'Vorherige Frage nicht verfügbar'"
            class="quiz-pagination--nav-btn"
            :disabled="!canGoPrevious"
            :title="canGoPrevious ? 'Zur vorherigen Frage (Vorherige)' : 'Vorherige Frage nicht verfügbar'"
            type="button"
            @click="handlePrevious">
      <v-icon aria-hidden="true" icon="fas fa-chevron-left" size="24" />
    </button>

    <div :aria-label="$t('questionNavigationLabel')" class="quiz-pagination--dots" role="group">
      <button v-for="(v, index) in questionStates"
              :key="index"
              :aria-current="index === currentIndex ? 'step' : undefined"
              :aria-describedby="`dot-desc-${index}`"
              :aria-label="getStateLabel(index, v)"
              class="quiz-pagination--dot"
              :class="{ 'quiz-pagination--dot-active': index === currentIndex }"
              type="button"
              @click="handleDotClick(index)"
              @keydown.left.prevent="index > 0 && handleDotClick(index - 1)"
              @keydown.right.prevent="index < questionStates.length - 1 && handleDotClick(index + 1)">
        <v-icon aria-hidden="true"
                :icon="getIconState(v)"
                :size="index === currentIndex ? 14 : 10" />
        <span :id="`dot-desc-${index}`" class="sr-only">
          {{ index === currentIndex ? '(aktuelle Frage)' : '' }}
        </span>
      </button>
    </div>

    <button :aria-label="canGoNext ? 'Zur nächsten Frage' : 'Nächste Frage nicht verfügbar'"
            class="quiz-pagination--nav-btn"
            :disabled="!canGoNext"
            :title="canGoNext ? 'Zur nächsten Frage (Nächste)' : 'Nächste Frage nicht verfügbar'"
            type="button"
            @click="handleNext">
      <v-icon aria-hidden="true" icon="fas fa-chevron-right" size="24" />
    </button>
  </nav>
</template>

<style scoped lang="scss">
.quiz-pagination {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 1rem;
}

.quiz-pagination--progress {
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

.quiz-pagination--nav-btn {
  background: transparent;
  border: 2px solid transparent;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 8px;
  transition: all 0.2s ease;
  color: inherit;
  min-height: 44px;
  min-width: 44px;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover:not(:disabled) {
    background-color: rgba(51, 69, 81, 0.1);
    border-color: currentColor;
  }

  &:focus-visible {
    outline: 2px solid currentColor;
    outline-offset: 2px;
    background-color: rgba(51, 69, 81, 0.1);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &:active:not(:disabled) {
    transform: scale(0.95);
  }
}

.quiz-pagination--dots {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.quiz-pagination--dot {
  background: transparent;
  border: 2px solid transparent;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 50%;
  transition: all 0.2s ease;
  min-height: 44px;
  min-width: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: inherit;

  &:hover {
    transform: scale(1.15);
    background-color: rgba(51, 69, 81, 0.05);
  }

  &:focus-visible {
    outline: 2px solid currentColor;
    outline-offset: 2px;
    border-color: currentColor;
  }

  &.quiz-pagination--dot-active {
    transform: scale(1.5);
    border-color: transparent;
    background-color: transparent;
  }

  &:active {
    transform: scale(1.1);
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