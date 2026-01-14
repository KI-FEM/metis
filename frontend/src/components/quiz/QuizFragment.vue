<script setup lang="ts">
  import { useQuizStore } from '@/stores/quiz.ts';
  import { computed } from 'vue';

  const props = defineProps<{
    /** The ID of the quiz */
    id: string,
  }>();

  const quizStore = useQuizStore();

  const quiz = computed(() => {
    const q = quizStore.getQuiz(props.id);
    console.log('[QuizFragment] Quiz computed:', props.id, q?.completed, q);
    return q;
  });

  const stateClass = computed(() => {
    switch (quiz.value?.state) {
      case 'loading':
        return 'quiz-fragment__loading';
      case 'ready':
        return 'quiz-fragment__unsolved';
      case 'complete':
        return 'quiz-fragment__solved';
      case 'error':
        return 'quiz-fragment__error';
      default:
        return 'quiz-fragment__unknown';
    }
  });

  const stateMessage = computed(() => {
    switch (quiz.value?.state) {
      case 'loading':
        return 'quiz.state.loading';
      case 'ready':
        return 'quiz.state.unsolved';
      case 'complete':
        return 'quiz.state.solved';
      case 'error':
        return 'quiz.state.error';
      default:
        return 'quiz.state.unknown';
    }
  });

  const handleClick = () => {
    console.log('Opening quiz with id:', props.id);
    quizStore.openQuiz(props.id);
  };
</script>

<template>
  <button v-if="quiz"
          class="quiz-fragment"
          :class="stateClass"
          type="button"
          @click="handleClick">
    <div class="quiz-fragment--content d-flex flex-row align-center justify-space-between">
      <div class="d-flex flex-row align-center justify-start">
        <v-icon class="quiz-fragment--icon" icon="fas fa-clipboard-question" size="32" />
        <span>{{ $t(`quiz.fragments.title`) }} <v-icon icon="fas fa-up-right-from-square" size="12" /></span>
      </div>
      <div v-if="quiz.state == 'complete' || quiz.state == 'ready'" class="quiz-fragment--status">
        <div class="d-flex flex-row align-center">
          <v-icon class="quiz-fragment--status-icon" 
                  icon="fas fa-circle"
                  size="12" />
          <span>
            {{ $t(stateMessage) }}
          </span>
        </div>
        <span>{{ quiz.score[0] }} / {{ quiz.score[1] }} {{ $t('quiz.points') }}</span>
      </div>
      <div v-else-if="quiz.state == 'loading'" class="quiz-fragment--status d-flex flex-row align-center">
        <div class="my-2">
          <v-progress-circular class="mr-4"
                               color="primary"
                               indeterminate />
          <span>
            {{ $t(stateMessage) }}
          </span>
        </div>
      </div>
      <div v-else-if="quiz.state == 'error'" class="quiz-fragment--status d-flex flex-row align-center">
        <v-icon class="quiz-fragment--status-icon" 
                icon="fas fa-xmark" />
        <span>
          {{ $t(stateMessage) }}
        </span>
      </div>
      <div v-else class="quiz-fragment--status d-flex flex-row align-center">
        <v-icon class="quiz-fragment--status-icon" 
                icon="fas fa-question" />
        <span>
          {{ $t('quiz.state.unknown') }}
        </span>
      </div>
    </div>
  </button>
  <span v-else>
    {{ $t('quiz.state.error') }}
  </span>
  <span v-if="quiz && quiz.messages && quiz.messages.length > 0" class="d-flex align-end ga-2 mt-1 text-secondary ms-4">
    <span v-for="(message, index) in quiz.messages" :key="index">
      {{ message.content }}
    </span>
  </span>
</template>

<style scoped lang="scss">
.quiz-fragment {
  width: 75%;
  margin-top: 12px;
  padding: 20px;
  border-radius: 20px 20px 20px 8px !important;
  background: rgb(var(--v-theme-surface-container-high)) !important;
  color: rgb(var(--v-theme-on-surface)) !important;
  text-decoration: none;

  &.quiz-fragment__solved {
    & .quiz-fragment--status-icon {
      color: green;
    }
  }
  &.quiz-fragment__error {
    & .quiz-fragment--status-icon {
      color: rgb(var(--v-theme-error)) !important;
      &:after {
        background-color: rgba(var(--v-theme-error), 0) !important;
      }
    }
  }
  &.quiz-fragment__unknown {
    & .quiz-fragment--status-icon {
      &:after {
        background-color: rgba(var(--v-theme-error), 0) !important;
      }
    }
  }
}

.quiz-fragment--content {
  width: 100%;

  & .quiz-fragment--status-icon {
    position: relative;
    color: #FFB200;
    margin-right: 8px;

    &:after {
      content: '';
      position: absolute;
      top: -3px;
      left: -3px;
      right: -3px;
      bottom: -3px;
      border-radius: 50%;
      background-color: rgba(255, 178, 0, 0.2);
    }
  }
}
</style>
