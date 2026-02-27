<script setup lang="ts">
  import {ref} from 'vue'

  import {useLearningTypesStore} from '@/stores/learningTypes.ts'
  import {useTopicsStore} from '@/stores/topics.ts'
  import {useChatStore} from '@/stores/chat.ts'
  import createClient from 'openapi-fetch'
  import type {paths, components} from '@/types_api.ts'
  import DialogCloseButton from '@/components/buttons/DialogCloseButton.vue'

  const learningTypesStore = useLearningTypesStore()
  const topicsStore = useTopicsStore()
  const chatStore = useChatStore()
  const client = createClient<paths>({baseUrl: import.meta.env.VITE_API_URL})

  const showDialog = defineModel<boolean>({default: false})
  const isLoading = ref(true)
  const questions = ref<components['schemas']['QuizModel']['questions']>([])
  const selection = ref<Record<number, number | number[]>>({})
  const showSolution = ref(false)
  const isError = ref(false)

  async function loadQuiz() {
    if (!topicsStore.selectedTopic || !chatStore.currentChat) {
      console.error('[QuizOverlay.loadQuiz] No topic or chat selected...')
      return
    }
    try {
      selection.value = {}
      showSolution.value = false
      showDialog.value = true
      isLoading.value = true
      isError.value = false
      const {data, error: fetchError} = await client.POST('/topic/{topic}/quiz', {
        params: {
          path: {
            topic: topicsStore.selectedTopic.endpoint
          }
        },
        body: {
          learning_type_id: learningTypesStore.selectedLearningTypeId,
          storage: chatStore.currentChat.storage,
          language: chatStore.currentChat.language,
          chat_history: chatStore.currentChat.messages,
          llm_purpose: chatStore.getSelectedLLMPurpose(),
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
      chatStore.currentChat.storage = {...chatStore.currentChat?.storage, ...data.storage}
    } catch (e) {
      isError.value = true
      console.error('[QuizOverlay.loadQuiz] Error during API call: ', e)
    } finally {
      isLoading.value = false
    }
  }

  async function submitQuiz() {
    if (!topicsStore.selectedTopic || !chatStore.currentChat) {
      console.error('[QuizOverlay.submitQuiz] No topic or chat selected...')
      return
    }
    showSolution.value = true
    try {
      chatStore.isLoading = true
      const {data, error: fetchError} = await client.PUT('/topic/{topic}/quiz', {
        params: {
          path: {
            topic: topicsStore.selectedTopic.endpoint
          }
        },
        body: {
          learning_type_id: learningTypesStore.selectedLearningTypeId,
          language: chatStore.currentChat?.language,
          chat_history: chatStore.currentChat?.messages,
          storage: chatStore.currentChat?.storage,
          questions: questions.value,
          answers: Object.entries(selection.value).map(([questionId, answer]) => ({
            question_id: parseInt(questionId),
            selected_options_ids: Array.isArray(answer) ? answer : [answer]
          })),
          llm_purpose: chatStore.getSelectedLLMPurpose(),
          streaming: false
        }
      })
      if (fetchError) {
        throw fetchError
      }
      if (!data) {
        throw new Error('No data received')
      }

      chatStore.currentChat.messages.push(...data.messages.map(m => ({
        ...m,
        complete: true,
        timestamp: new Date().toISOString()
      })))
      chatStore.currentChat.storage = {...chatStore.currentChat?.storage, ...data.storage}
      //const instructions = data.instructions // TODO: handle instructions

      questions.value.forEach(question => {
        // turn single-choice into multiple-choice
        if (typeof selection.value[question.id] === 'number')
          selection.value[question.id] = [selection.value[question.id] as number]
        if (typeof selection.value[question.id] === 'undefined')
          selection.value[question.id] = []
        // add correct answer to selections
        const correctAnswers = question.options.filter(option => option.correct)
        correctAnswers.forEach(correctAnswer => {
          if (!(selection.value[question.id] as number[]).includes(correctAnswer.id))
            (selection.value[question.id] as number[]).push(correctAnswer.id)
        })
      })
    } catch (e) {
      console.error('[QuizOverlay.submitQuiz] Error during API call: ', e)
    } finally {
      chatStore.isLoading = false
    }
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
          <v-icon icon="fas fa-list-check" start />
          <h1 class="text-headline-sm">
            {{ $t('quiz') }}
          </h1>
          <DialogCloseButton class="ms-auto" @click="showDialog = false" />
        </v-card-title>
      </v-card-item>
      <v-card-text>
        <v-alert v-if="isError" :text="$t('quizError')" type="error" />
        <div v-if="isLoading" class="d-flex flex-column align-center text-primary ga-3">
          <v-progress-circular color="primary" indeterminate />
          {{ $t('generatingQuiz') }}
        </div>
        <v-form v-else :disabled="false" @submit.prevent="submitQuiz">
          <template v-for="question in questions" :key="question.id">
            <v-radio-group v-model="selection[question.id]"
                           :class="{'v-selection-control--disabled':showSolution}"
                           :multiple="showSolution">
              <template #label>
                <h2 class="mt-3 text-h6 text-wrap">
                  {{ question.question }}
                </h2>
              </template>
              <v-radio v-for="option in question.options"
                       :key="option.id"
                       :color="showSolution ? (option.correct ? 'success' : 'error') : undefined"
                       :label="option.label"
                       :true-icon="showSolution ? (option.correct ? 'fas fa-check': 'fas fa-xmark') : undefined"
                       :value="option.id" />
            </v-radio-group>
          </template>
          <div v-if="!showSolution && !isError" class="text-center">
            <v-btn color="primary"
                   :text="$t('solveQuiz')"
                   type="submit" />
          </div>
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-btn :text="$t('closeQuiz')"
               @click="showDialog = false" />
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped lang="scss">
  .v-selection-control--disabled {
    --v-disabled-opacity: 0.75;
  }
</style>
