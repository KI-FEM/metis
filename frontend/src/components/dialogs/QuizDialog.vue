<script setup lang="ts">
  import { ref, computed, onMounted, watch, onUnmounted } from 'vue';
  import { useQuizStore } from '@/stores/quiz.ts';
  import QuizQuestion from '@/components/quiz/QuizQuestion.vue';
  import QuizPagination from '@/components/quiz/QuizPagination.vue';
  import DialogCloseButton from '@/components/buttons/DialogCloseButton.vue';
  import type { components } from '@/types_api.ts';
  import type { QuestionState } from "@/types/Question";
  import type { QuizAnswer, QuizEvents } from '@/types';
  import { useI18n } from 'vue-i18n';

  const quizStore = useQuizStore();

  const showDialog = defineModel<boolean>({ default: false });
  //const questions = ref<components['schemas']['QuizModel']['questions']>([]);
  const questions = computed(() => quizStore.currentQuiz ? quizStore.currentQuiz.questions : []);
  const currentQuestionIndex = ref(0);
  //const answers = computed(() => questions.value[currentQuestionIndex.value].answer);
  const showHints = ref<Record<number, boolean>>({});
  const showSolutions = ref<Record<number, boolean>>({});
 
  /**
   * Computes the states of all questions for pagination. Currently only two states are possible. This function can be
   * expanded in the future to include more states (e.g., partially answered, flagged, etc.)
   */
  const questionStates = computed<QuestionState[]>(() => {
    return questions.value.map((q) => {
      if (q.answered) {
        return 1 as QuestionState;
      } else if (q.answer !== undefined) {
        return 0 as QuestionState;
      } else {
        return 0 as QuestionState;
      }
    });
  });
  const isLoading = ref(false);
  const isError = ref(false);
  const isSubmitting = ref(false);
  const loadingBulkCount = ref(0); // Number of questions still being loaded

  const currentQuestion = computed(() => questions.value[currentQuestionIndex.value] ?? null);

  /**
   * Util if the current question can be submitted
   */
  const canSubmitCurrentQuestion = computed(() => {
    if (!currentQuestion.value) return false;
    if (currentQuestion.value.answered) return false;
    if (isSubmitting.value) return false;

    return currentQuestion.value.answer !== undefined;
  });

  /**
   * Defines, if some of the footer tabs should be active. If null, no tab is visible
   */
  const footerTab = ref<string|null>(null);
  const hasClickedTab = ref<boolean>(false);

  watch(
    () => quizStore.currentQuiz,
    (newQuiz, oldQuiz) => {
      console.log('Current quiz changed:', newQuiz);
      if (!oldQuiz || (newQuiz && oldQuiz && newQuiz.id !== oldQuiz.id)) {
        currentQuestionIndex.value = 0;
      }
      if (!newQuiz || !newQuiz.questions || newQuiz.questions.length === 0) {
        //questions.value  = [];
        loadingBulkCount.value = 0;
        return;
      }

      isLoading.value = false;
      // if (!newQuiz.questions) {
      //   isError.value = true;
      //   isLoading.value = false;
      //   //questions.value  = [];
      //   loadingBulkCount.value = 0;
      //   return;
      // }
      isError.value = false;
      //questions.value = newQuiz.questions || [];

      //loadingBulkCount.value = (newQuiz as any).loadingBulk ? 4 : 0;

      // questions.value.map((q) => {
      //   showHints.value[q.id] = false;
      //   showSolutions.value[q.id] = !!q.feedback;
      // });
    }, { immediate: true });

  watch(() => quizStore.showQuiz, (newShow) => {
    showDialog.value = newShow;
  }, { immediate: true });

  watch(() => quizStore.isLoading, (newLoading) => {
    isLoading.value = newLoading;
    console.log('isLoading changed', newLoading);
  }, { immediate: true });

  watch(() => quizStore.isError, (newError) => {
    isError.value = newError;
  }, { immediate: true });

  watch(questions, (newQuestions) => {
    console.log('Questions updated:', newQuestions);
    questions.value.map((q) => {
      showHints.value[q.id] = false;
      showSolutions.value[q.id] = false;
    });
  }, { immediate: true });

  // watch(currentQuestion, (newQuestion) => {
  //   console.log('Current question changed:', newQuestion);
  //   if (newQuestion === null) {
  //     footerTab.value = null;
  //     hasClickedTab.value = false;
  //     return;
  //   }
  //   // Reset footer tab to force re-render
  //   const oldFooterTab = footerTab.value;
  //   footerTab.value = null;
  //   hasClickedTab.value = false;
  
  //   // If question has feedback (already answered), automatically show solution
  //   if (questionFeedback.value[newQuestion.id]) {
  //     showSolutions.value[newQuestion.id] = true;
  //     footerTab.value = 'solution';
  //     hasClickedTab.value = true;
  //   } else if (oldFooterTab === 'hint' && isHintVisible(newQuestion.id)) {
  //     footerTab.value = 'hint';
  //     hasClickedTab.value = true;
  //   } else if (oldFooterTab === 'solution' && isSolutionVisible(newQuestion.id)) {
  //     footerTab.value = 'solution';
  //     hasClickedTab.value = true;
  //   }
  // });

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex.value > 0) {
      currentQuestionIndex.value--;
    }
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex.value < questions.value.length - 1) {
      currentQuestionIndex.value++;
    }
  };

  const handleGoToQuestion = (index: number) => {
    currentQuestionIndex.value = index;
  };

  const handleAnswerChange = (questionId: number, answer: QuizAnswer) => {
    if(!questions.value || questions.value.length<questionId || !questions.value[questionId - 1]) return;
    const question = questions.value[questionId - 1];
    if (!question) return;
    question.answer = answer;
  };

  const handleSubmit = async () => {
    if (!canSubmitCurrentQuestion.value || !currentQuestion.value || !quizStore.currentQuiz) return;
    const submittedQuestion = currentQuestion.value; // Store reference to avoid issues with reactivity
    isSubmitting.value = true;
  
    try {
      const userAnswer = submittedQuestion.answer;
      const result = await quizStore.evaluateAnswer(
        quizStore.currentQuiz.id,
        submittedQuestion,
        userAnswer
      );
    
      if (result) {
        // Store feedback for this question
        submittedQuestion.score = [result.score, result.max_score];
        submittedQuestion.solution = result.solution;
        submittedQuestion.feedback = result.feedback;
        submittedQuestion.is_correct = result.score / result.max_score > 0.5;
      
        // Automatically open solution tab after submission
        toggleShowSolution();
        console.log('Question evaluated:', result);
      } else {
        console.error('Failed to evaluate question');
      }

    } catch (error) {
      console.error('Error submitting answer:', error);
    } finally {
      isSubmitting.value = false;
    }

    const quiz = quizStore.currentQuiz;
    const allAnswered = quiz.questions.every(q => q.answered);
    console.log('[quiz.evaluateAnswer] All answered?', allAnswered, 'Currently completed?', quiz.completed);
    if (allAnswered && !quiz.completed) {
      await quizStore.evaluateQuizCompletion(quiz);
    }
  };

  /**
   * Toggles Solution tab and closes Hint tab if open
   */
  const toggleShowSolution = () => {
    if (!currentQuestion.value) return;

    if (showSolutions.value[currentQuestion.value.id]) {
      showSolutions.value[currentQuestion.value.id] = false;
      footerTab.value = null;
      return;
    }

    showHints.value[currentQuestion.value.id] = false;
    footerTab.value = 'solution';
    showSolutions.value[currentQuestion.value.id] = true;
  }

  // const isHintVisible = (questionId: number) => {
  //   return showHints.value[questionId] || false;
  // };

  /**
 * Toggles Hint tab and closes Solution tab if open
 */
  const toggleShowHint = () => {
    if (!currentQuestion.value) return;

    if (showHints.value[currentQuestion.value.id]) {
      showHints.value[currentQuestion.value.id] = false;
      footerTab.value = null;
      return;
    }

    showSolutions.value[currentQuestion.value.id] = false;
    footerTab.value = 'hint';
    showHints.value[currentQuestion.value.id] = true;
  }

  function formatSolution(solution: components['schemas']['QuizQuestionEvaluationResponse']['solution']): string {
    if (currentQuestion.value && currentQuestion.value.type === 'multiple-choice' && Array.isArray(solution)) {
      return solution.map(index => {
        if (currentQuestion.value != undefined && currentQuestion.value.type == 'multiple-choice') {
          return currentQuestion.value.options[Number(index)] || index.toString();
        }
      }).join(', ');
    }
    if (Array.isArray(solution)) {
      return solution.join(', ');
    }
    return solution.toString();
  }

  onMounted(() => {
    footerTab.value = null;
    hasClickedTab.value = false;

    if (quizStore.currentQuiz && !quizStore.currentQuiz.questions && quizStore.currentQuiz.events.length > 0) {
      const lastEvent = quizStore.currentQuiz.events[quizStore.currentQuiz.events.length - 1]
      if (lastEvent) {
        setEventMessage(lastEvent);
      }
    }
  })

  // Message queue for staggered event display
  const {t} = useI18n()

  const messageQueue = ref<string[]>([])
  const isProcessingQueue = ref(false)
  const queueTimer = ref<number | null>(null)
  const MESSAGE_DISPLAY_DURATION = 1500 // 1.5 seconds
  const loadingMessage = ref(null as string | null)
  
  onUnmounted(() => {
    clearMessageQueue()
  })

  function clearMessageQueue() {
    messageQueue.value = []
    isProcessingQueue.value = false
    if (queueTimer.value) {
      clearTimeout(queueTimer.value)
      queueTimer.value = null
    }
  }

  function processMessageQueue() {
    if (isProcessingQueue.value || messageQueue.value.length === 0) {
      return
    }

    isProcessingQueue.value = true
    const nextMessage = messageQueue.value.shift()!
    loadingMessage.value = nextMessage

    queueTimer.value = setTimeout(() => {
      isProcessingQueue.value = false
      queueTimer.value = null

      // Process next message if any
      if (messageQueue.value.length > 0) {
        processMessageQueue()
      }
    }, MESSAGE_DISPLAY_DURATION)
  }

  function addToMessageQueue(message: string) {
    // If the same message is already at the end of the queue, don't add it again
    if (messageQueue.value[messageQueue.value.length - 1] === message) {
      return
    }

    messageQueue.value.push(message)
    processMessageQueue()
  }

  function setEventMessage(event: QuizEvents) {
    let eventMessage = ''

    if (event.event === 'quiz_verified') {
      eventMessage = t('quiz.eventVerified')
    } else if (event.event === 'quiz_generation_started') {
      eventMessage = t('quiz.eventGenerationStarted')
    } else if (event.event === 'quiz_generated') {
      // the agent is writing the final answer
      eventMessage = t('quiz.eventGenerated')
    } else if (event.event === 'question_answered') {
      // the agent is starting
      eventMessage = t('quiz.eventQuestionAnswered')
    } else if (event.event === 'quiz_completed') {
      eventMessage = t('quiz.eventCompleted')
    } else if (event.event === 'quiz_generation_delayed') {
      eventMessage = t('quiz.eventGenerationDelayed')
    }

    // Add to queue if we have a message
    if (eventMessage) {
      addToMessageQueue(eventMessage)
    }
  }

  // Process events staggeredly to show the progress
  watch(() => quizStore.currentQuiz?.events, (newEvents, oldEvents) => {
    console.log('Quiz events changed:', newEvents)
    if (!newEvents || quizStore.currentQuiz?.completed) return

    // get unprocessed events
    const unprocessedEvents = oldEvents
      ? newEvents.filter(e => !oldEvents.includes(e))
      : newEvents
    unprocessedEvents.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())

    // Process each unprocessed event
    for (const event of unprocessedEvents) {
      setEventMessage(event)
    }
  }, {immediate: true});
</script>

<template>
  <v-dialog v-model="showDialog"
            absolute
            max-width="750"
            scrollable
            @after-leave="quizStore.closeQuiz()">
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          <h2 class="text-headline-sm">
            {{ quizStore.currentQuiz?.title || $t('quiz.quiz') }}
          </h2>
          <DialogCloseButton class="ms-auto" @click="quizStore.closeQuiz()" />
        </v-card-title>
        <v-card-subtitle v-if="quizStore.currentQuiz?.description">
          {{ quizStore.currentQuiz?.description }}
        </v-card-subtitle>
      </v-card-item>
      <v-card-text>
        <QuizPagination :current-index="currentQuestionIndex"
                        :question-states="questionStates"
                        @go-to="handleGoToQuestion"
                        @next="handleNextQuestion"
                        @previous="handlePreviousQuestion" />
        <v-alert v-if="isError" :text="$t('quiz.error')" type="error" />
        <div v-if="quizStore.currentQuiz?.state == 'loading'" class="d-flex flex-column align-center">
          <v-progress-circular color="primary" indeterminate />
          {{ loadingMessage || $t('quiz.generating') }}
        </div>
        <div v-else-if="quizStore.currentQuiz?.state == 'error'" class="d-flex flex-column align-center">
          {{ $t('quiz.state.error') }}
        </div>
        <QuizQuestion v-else-if="currentQuestion"
                      :key="currentQuestion.id"
                      :question="currentQuestion"
                      :total-questions="questions.length"
                      @answer-change="handleAnswerChange" />
      </v-card-text>
      <v-card-item v-if="currentQuestion">
        <!-- <p class="quiz-dialog-footer--points">{{ $t('points') }}: {{ currentQuestion.maxPoints ?? 0 }}</p> -->
        <v-tabs v-model="footerTab"
                align-tabs="center"
                grow
                :mandatory="false"
                stacked>
          <v-tab :value="'hint'" @click="toggleShowHint">
            <v-icon icon="fas fa-lightbulb" size="small" />
            {{ $t('quiz.showHint') }}
          </v-tab>
          <v-tab :disabled="!(currentQuestion?.feedback)" :value="'solution'" @click="toggleShowSolution">
            <v-icon icon="fas fa-check-double" size="small" />
            {{ $t('quiz.showSolution') }}
          </v-tab>
        </v-tabs>
        <v-tabs-window v-model="footerTab">
          <v-tabs-window-item value="hint">
            <div v-if="currentQuestion?.hint" class="hint-content">
              {{ currentQuestion.hint }}
            </div>
            <div v-else class="hint-content">
              {{ $t('quiz.noHintAvailable') }}
            </div>
          </v-tabs-window-item>

          <v-tabs-window-item value="solution">
            <div v-if="currentQuestion?.feedback" class="solution-content">
              <div class="feedback-header" :class="currentQuestion?.is_correct ? 'correct' : 'incorrect'">
                <v-icon :icon="currentQuestion.is_correct ? 'fas fa-check-circle' : 'fas fa-times-circle'" />
                <span>{{ currentQuestion.is_correct ? $t('quiz.correct') : $t('quiz.incorrect') }}</span>
                <span class="score">{{ currentQuestion.score[0] }} / {{ currentQuestion.score[1] }} {{ $t('quiz.points') }}</span>
              </div>
              <div class="feedback-text">
                {{ currentQuestion.feedback }}
              </div>
              <div class="solution-text">
                <strong>{{ $t('quiz.solution') }}:</strong> {{ formatSolution(currentQuestion.solution) }}
              </div>
            </div>
            <div v-else class="solution-content"> 
              {{ $t('quiz.noSolutionAvailable') }}
            </div>
          </v-tabs-window-item>
        </v-tabs-window>
      </v-card-item>
      <v-card-actions class="d-flex flex-row align-center justify-center mt-n4">
        <v-btn v-if="currentQuestion && !quizStore.currentQuiz?.completed" 
               class=""
               :disabled="!canSubmitCurrentQuestion"
               :loading="isSubmitting"
               @click="handleSubmit">
          {{ currentQuestion?.answered ? $t('quiz.answered') : $t('quiz.submitAnswer') }}
        </v-btn>
        <v-btn v-if="quizStore.currentQuiz?.completed"
               class=""
               variant="outlined"
               @click="quizStore.closeQuiz()">
          {{ $t('quiz.quizCompleted') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped lang="scss">
.quiz-dialog {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  width: 750px;
  min-height: 650px;
  margin: 2rem auto;
  padding: 2rem 2.5rem;
  gap: 2rem;
  border-radius: 0.75rem;
  background-color: #F0F4F8;
  color: #181C1F;
}

.quiz-question {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
    .quiz-question--input {
    margin-left: 1rem;
    width: 95%;
  }
}


.hint-content,
.solution-content {
  padding: 1rem;
  border-radius: 8px;
  background: rgb(var(--v-theme-surface-container));
  color: rgb(var(--v-theme-on-surface));
  line-height: 1.6;
  font-size: 0.95rem;
}

.feedback-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding: 0.75rem;
  border-radius: 6px;
  font-weight: 600;

  &.correct {
    background: rgba(76, 175, 80, 0.1);
    color: #4caf50;
  }

  &.incorrect {
    background: rgba(244, 67, 54, 0.1);
    color: #f44336;
  }

  .score {
    margin-left: auto;
    font-weight: 500;
  }
}

.feedback-text {
  margin-bottom: 1rem;
  line-height: 1.6;
}

.solution-text {
  padding: 0.75rem;
  background: rgba(var(--v-theme-on-surface), 0.05);
  border-radius: 6px;
  line-height: 1.6;
}

.v-btn--stacked {
  padding-top: 1.5rem !important;
  padding-bottom: 1.7rem !important;
}
</style>
