<script setup lang="ts">
  import { ref, computed } from 'vue'
  import { useI18n } from 'vue-i18n'

  import { useLearningTypesStore } from '@/stores/learningTypes.ts'
  import { useTopicsStore } from '@/stores/topics.ts'
  import { useChatStore } from '@/stores/chat.ts'
  import createClient from 'openapi-fetch'
  import type { paths, components } from '@/types_api.ts'
  import DialogCloseButton from '@/components/buttons/DialogCloseButton.vue'
  import QuizQuestion from '../quiz/QuizQuestion.vue'

  interface Props {
    selectedModuleCode: string
    selectedLevelId: number
  }

  const props = defineProps<Props>()

  const { locale } = useI18n()
  const learningTypesStore = useLearningTypesStore()
  const topicsStore = useTopicsStore()
  const chatStore = useChatStore()
  const client = createClient<paths>({ baseUrl: import.meta.env.VITE_API_URL })

  const showDialog = defineModel<boolean>({ default: false })
  const isLoading = ref(true)
  const questions = ref<components['schemas']['InitialQuizModel']['questions']>([])
  const questionsAskedPerLevel = ref<components['schemas']['InitialQuizModel']['quiz_questions_asked_per_level']>([0,0,0])
  const selection = ref<Record<number, number[]>>({})
  const showSolution = ref(false)
  const isError = ref(false)
  const showFeedback = ref(false)
  const suggestedLevelChange = ref(0)
  const correctAnswers = ref(0)
  const totalQuestions = ref(0)
  const performance_below = ref(0)
  const performance_at_level = ref(0)
  const performance_above = ref(0)
  const selfEvaluation = ref('')

  // Computed property to get the recommended level information TODO maybe do different
  const recommendedLevel = computed(() => {
    if (!topicsStore.selectedTopic || suggestedLevelChange.value === 0) return null
    
    const selectedModule = topicsStore.selectedTopic.modules.find(module => 
      module.code === props.selectedModuleCode
    ) as components['schemas']['Skill'] | undefined
    
    if (!selectedModule || !selectedModule.levels) return null
    
    const currentLevel = props.selectedLevelId || 1
    const newLevelId = Number(currentLevel) + suggestedLevelChange.value
    
    const recommendedLevelData = selectedModule.levels.find(level => 
      level.id.toString() === newLevelId.toString()
    )
    
    return recommendedLevelData
  })

  async function loadQuiz() {
    if (!topicsStore.selectedTopic || !chatStore.currentChat) {
      console.error('[InitialQuizDialog.loadQuiz] No topic selected or chat not found...')
      return
    }
    try {
      selection.value = {}
      showSolution.value = false
      showDialog.value = true
      isLoading.value = true
      isError.value = false
      const { data, error: fetchError } = await client.POST('/topic/{topic}/initial_quiz', {
        params: {
          path: {
            topic: topicsStore.selectedTopic.endpoint
          }
        },
        body: {
          id: chatStore.currentChat.id,
          storage: {
            selected_competence: props.selectedModuleCode,
            skill_level: props.selectedLevelId || 1
          },
          language: locale.value,
          chat_history: [],
          llm_purpose: chatStore.getSelectedLLMPurpose(),
          response_preferences: chatStore.responsePreferences,
          streaming: false
        }
      })
      if (fetchError) {
        throw fetchError
      }
      if (!data) {
        throw new Error('No data received')
      }
      questions.value = data.questions
      questionsAskedPerLevel.value = data.quiz_questions_asked_per_level || [0, 0, 0]
    } catch (e) {
      isError.value = true
      console.error('[InitialQuizDialog.loadQuiz] Error during API call: ', e)
    } finally {
      isLoading.value = false
    }
  }

  async function submitQuiz() {
    if (!topicsStore.selectedTopic) {
      console.error('[InitialQuizDialog.submitQuiz] No topic selected...')
      return
    }
    showSolution.value = true

    try {
      // Calculate score before showing solutions
      // const correct = 0
      // const correctAnswerList: number[] = []
      // const total = questions.value.length
      
    //   questions.value.forEach(question => {
    //     const userAnswer = selection.value[question.id]
    //     const correctOptions = question.options.filter(option => option.correct).map(option => option.id)
        
    //     // Check if user's answer matches correct answer(s)
    //     if (typeof userAnswer === 'number') {
    //       if (correctOptions.includes(userAnswer)) {
    //         correct++
    //         correctAnswerList.push(question.learning_unit)
    //       }
    //     }
        
    //     // turn single-choice into multiple-choice for display
    //     if (typeof selection.value[question.id] === 'number')
    //       selection.value[question.id] = [selection.value[question.id] as number]
    //     if (typeof selection.value[question.id] === 'undefined')
    //       selection.value[question.id] = []
    //     // add correct answer to selections for display
    //     correctOptions.forEach(correctAnswer => {
    //       if (!(selection.value[question.id] as number[]).includes(correctAnswer))
    //         (selection.value[question.id] as number[]).push(correctAnswer)
    //     })
    //   })
      
    //   // Store results
    //   correctAnswers.value = correct
    //   totalQuestions.value = total

    //   const { data, error: fetchError } = await client.POST('/topic/{topic}/answer_initial_quiz', {
    //     params: {
    //       path: {
    //         topic: topicsStore.selectedTopic.endpoint
    //       }
    //     },
    //     body: {
    //       correct_question_ids: correctAnswerList,
    //       questions_asked_per_level: questionsAskedPerLevel.value,
    //       learning_type_id: learningTypesStore.selectedLearningTypeId,
    //       response_preferences: chatStore.responsePreferences,
    //       language: locale.value,
    //       chat_history: [],
    //       llm_purpose: chatStore.getSelectedLLMPurpose(),
    //       storage: {
    //         skill_level: props.selectedLevelId || 1
    //       },
    //       streaming: false
    //     }
    //   })
    //   if (fetchError) {
    //     throw fetchError
    //   }
    //   if (!data) {
    //     throw new Error('No data received')
    //   }
    //   performance_below.value = data.quiz_performance_below || 0
    //   performance_at_level.value = data.quiz_performance_at_level || 0
    //   performance_above.value = data.quiz_performance_above || 0
    //   suggestedLevelChange.value = data.quiz_recommended_change || 0

    //   if (selfEvaluation.value.trim()) {
    //     const timestamp = new Date().toISOString()
    //     const evaluationData = {
    //       topic: topicsStore.selectedTopic?.endpoint,
    //       module: props.selectedModuleCode,
    //       level: props.selectedLevelId,
    //       selfEvaluation: selfEvaluation.value.trim(),
    //       timestamp: timestamp,
    //       quizScore: {
    //         correct: correctAnswers.value,
    //         total: totalQuestions.value
    //       }
    //     }
        
    //     // Get existing self-evaluations from localStorage
    //     const existingEvaluations = JSON.parse(localStorage.getItem('selfEvaluations') || '[]')
    //     existingEvaluations.push(evaluationData)
    //     localStorage.setItem('selfEvaluations', JSON.stringify(existingEvaluations))
    //     console.log('[InitialQuizDialog] Self-evaluation stored in localStorage:', evaluationData)
    //   }

    //   showFeedback.value = true      
    } catch (e) {
      console.error('[InitialQuizDialog.submitQuiz] Error: ', e)
    }
  }

  function closeDialog() {
    showDialog.value = false
    setTimeout(() => {
      showSolution.value = false
      showFeedback.value = false
      isLoading.value = true
      questions.value = []
      questionsAskedPerLevel.value = [0, 0, 0]
      selection.value = {}
      correctAnswers.value = 0
      totalQuestions.value = 0
      performance_below.value = 0
      performance_at_level.value = 0
      performance_above.value = 0
      selfEvaluation.value = ''
    }, 300)
  }
</script>

<template>
  <v-dialog v-model="showDialog"
            max-width="700"
            scrollable
            @after-enter="loadQuiz">
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          <v-icon icon="fas fa-clipboard-check" start />
          <h1 class="text-headline-sm">
            {{ $t('initialQuiz') }}
          </h1>
          <DialogCloseButton class="ms-auto" @click="closeDialog" />
        </v-card-title>
      </v-card-item>
      <v-card-text>
        <div class="mb-4">
          <p>{{ $t('initialQuizIntro1') }}</p>
          <p>{{ $t('initialQuizIntro2') }}</p>
          <p>{{ $t('initialQuizIntro3') }}</p>
        </div>
        
        <v-alert v-if="isError" :text="$t('quizError')" type="error" />
        <div v-if="isLoading" class="d-flex flex-column align-center text-primary ga-3">
          <v-progress-circular color="primary" indeterminate />
          {{ $t('generatingInitialQuiz') }}
        </div>
        <v-form v-else :disabled="false" @submit.prevent="submitQuiz">
          <QuizQuestion v-for="(question, index) in questions"
                        :key="question.id"
                        v-model="selection[question.id]"
                        class="mb-6"
                        :feedback="undefined"
                        :question="question"
                        :question-id="`initial-quiz-question-${index}`"
                        :question-number="index + 1"
                        :total-questions="questions.length" />

          <div class="mt-6">
            <v-textarea v-model="selfEvaluation"
                        class="mb-4"
                        :disabled="showSolution"
                        :label="$t('selfEvaluationLabel')"
                        rows="4"
                        variant="outlined" />
          </div>
          
          <div v-if="!showSolution && !isError" class="text-center">
            <v-btn color="primary" :text="$t('solveInitialQuiz')" type="submit" />
          </div>
        </v-form>
        
        <div v-if="showFeedback" class="pt-4">
          <v-divider class="mb-4" />
          
          <div class="text-center mb-6">
            <h3 class="text-h6 mb-4">
              {{ $t('initialQuizFeedback') }}
            </h3>
            
            <v-chip class="mb-4"
                    :color="suggestedLevelChange === 1 ? 'success' : suggestedLevelChange === -1 ? 'error' : 'primary'"
                    size="large">
              {{ correctAnswers }} / {{ totalQuestions }} {{ $t('correct') }}
              ({{ Math.round((correctAnswers / totalQuestions) * 100) }}%)
            </v-chip>
          </div>

          <div class="mb-6">
            <template v-if="suggestedLevelChange !== 0 && recommendedLevel">
              <v-card class="recommendation-card pa-4 text-center" 
                      :class="suggestedLevelChange === 1 ? 'bg-success-container' : 'bg-warning-container'"
                      variant="tonal">
                <div class="d-flex flex-column align-center ga-3">
                  <div class="d-flex align-center ga-2">
                    <v-icon :color="suggestedLevelChange === 1 ? 'success' : 'warning'" 
                            :icon="suggestedLevelChange === 1 ? 'fas fa-arrow-up' : 'fas fa-arrow-down'" 
                            size="20" />
                    <h4 class="text-title-sm font-weight-bold">
                      {{ $t('recommendation') }}
                    </h4>
                  </div>
                  
                  <div class="text-body-2 mb-2">
                    {{ suggestedLevelChange === 1 ? $t('suggestLevelIncrease') : $t('suggestLevelDecrease') }}
                  </div>
                  
                  <v-chip :color="suggestedLevelChange === 1 ? 'success' : 'warning'" 
                          size="large">
                    <v-icon :icon="'fas fa-flag-checkered'" start />
                    {{ recommendedLevel.title[locale] }}
                  </v-chip>
                </div>
              </v-card>
            </template>
            <template v-else>
              <v-card class="recommendation-card pa-4 text-center bg-success-container" variant="tonal">
                <div class="d-flex flex-column align-center ga-2">
                  <div class="d-flex align-center ga-2">
                    <v-icon color="success" icon="fas fa-check" size="20" />
                    <h4 class="text-title-sm font-weight-bold">
                      {{ $t('recommendation') }}
                    </h4>
                  </div>
                  <div class="text-body-2">
                    {{ $t('suggestLevelStay') }}
                  </div>
                </div>
              </v-card>
            </template>
          </div>

          <v-expansion-panels v-if="questionsAskedPerLevel.some(count => count > 0)" class="performance-details" variant="accordion">
            <v-expansion-panel>
              <v-expansion-panel-title>
                <div class="d-flex align-center ga-2">
                  <v-icon icon="fas fa-chart-bar" size="16" />
                  <span class="text-body-2">{{ $t('detailedResults') }}</span>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-row class="text-center justify-center">
                  <v-col v-if="questionsAskedPerLevel[0] > 0" 
                         cols="12" 
                         :sm="questionsAskedPerLevel.filter(count => count > 0).length === 2 ? '6' : '4'">
                    <v-card class="pa-3" variant="outlined">
                      <div class="text-caption text-medium-emphasis mb-1">
                        {{ $t('belowLevel') }}
                      </div>
                      <div class="text-h6" :class="performance_below / questionsAskedPerLevel[0] > 0.7 ? 'text-success' : performance_below / questionsAskedPerLevel[0] < 0.3 ? 'text-error' : 'text-warning'">
                        {{ Math.round(performance_below / questionsAskedPerLevel[0] * 100) }}%
                      </div>
                    </v-card>
                  </v-col>
                  <v-col v-if="questionsAskedPerLevel[1] > 0" 
                         cols="12" 
                         :sm="questionsAskedPerLevel.filter(count => count > 0).length === 2 ? '6' : '4'">
                    <v-card class="pa-3" variant="outlined">
                      <div class="text-caption text-medium-emphasis mb-1">
                        {{ $t('atLevel') }}
                      </div>
                      <div class="text-h6" :class="performance_at_level / questionsAskedPerLevel[1] > 0.7 ? 'text-success' : performance_at_level / questionsAskedPerLevel[1] < 0.3 ? 'text-error' : 'text-warning'">
                        {{ Math.round(performance_at_level / questionsAskedPerLevel[1] * 100) }}%
                      </div>
                    </v-card>
                  </v-col>
                  <v-col v-if="questionsAskedPerLevel[2] > 0" 
                         cols="12" 
                         :sm="questionsAskedPerLevel.filter(count => count > 0).length === 2 ? '6' : '4'">
                    <v-card class="pa-3" variant="outlined">
                      <div class="text-caption text-medium-emphasis mb-1">
                        {{ $t('aboveLevel') }}
                      </div>
                      <div class="text-h6" :class="performance_above / questionsAskedPerLevel[2] > 0.7 ? 'text-success' : performance_above / questionsAskedPerLevel[2] < 0.3 ? 'text-error' : 'text-warning'">
                        {{ Math.round(performance_above / questionsAskedPerLevel[2] * 100) }}%
                      </div>
                    </v-card>
                  </v-col>
                </v-row>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>
      </v-card-text>
      
      <v-card-actions>
        <template v-if="showFeedback">
          <v-spacer />
          <v-btn color="primary"
                 :text="$t('closeQuiz')"
                 variant="flat"
                 @click="closeDialog" />
        </template>
        <template v-else>
          <v-btn :text="$t('closeQuiz')"
                 @click="closeDialog" />
        </template>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped lang="scss">
.v-selection-control--disabled {
  --v-disabled-opacity: 0.75;
}

.recommendation-card {
  border-radius: 12px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
  
  &.bg-success-container {
    border-color: rgb(var(--v-theme-success));
  }
  
  &.bg-warning-container {
    border-color: rgb(var(--v-theme-warning));
  }
}
</style>