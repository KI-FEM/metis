<script setup lang="ts">
  import {useChatStore} from '@/stores/chat.ts'
  import {useLearningTypesStore} from '@/stores/learningTypes.ts'
  import type {ChatMessage, ChatMessageMessage} from '@/types.ts'
  import type {paths} from '@/types_api.ts'
  import createClient from 'openapi-fetch'
  import {ref, watchEffect} from 'vue'
  import {useI18n} from 'vue-i18n'
  import {useTopicsStore} from '@/stores/topics.ts'
  import DialogCloseButton from '@/components/buttons/DialogCloseButton.vue'

  const topicsStore = useTopicsStore()
  const learningTypesStore = useLearningTypesStore()
  const chatStore = useChatStore()
  const client = createClient<paths>({baseUrl: import.meta.env.VITE_API_URL})

  const {locale, t} = useI18n()
  const tickLabels: { [key: number]: string } = {
    1: '😭',
    2: '😢',
    3: '☹️',
    4: '🙁',
    5: '😐',
    6: '🙂',
    7: '😊',
    8: '😁',
    9: '😄',
    10: '😍'
  }

  const showDialog = defineModel<boolean>({default: false})
  const learningTypeValue = ref(4)
  const feedbackValue = ref('')
  const showForm = ref(true)
  const feedbackAnswer = ref('')
  const recommendationsReady = ref(false)
  const isLoading = ref(false)

  watchEffect(() => {
    recommendationsReady.value = false
    isLoading.value = false
  })

  const submit = async () => {
    showForm.value = false
    isLoading.value = true
    if (!topicsStore.selectedTopic || !chatStore.currentChat) {
      console.error('[FeedbackOverlay.submit] Chat or topic not set')
      return
    }
    chatStore.currentChat?.messages.push({
      fragment: false,
      content: 'My learning type fits me like this: ' + tickLabels[learningTypeValue.value] + ' and my feedback is: ' + feedbackValue.value,
      type: 'user',
      buttons: [],
      meta_information: {} as ChatMessage['meta_information'],
      timestamp: new Date().toISOString(),
      complete: true
    })
    try {
      const {data, error} = await client.POST('/topic/{topic}/feedback', {
        params: {
          path: {
            topic: topicsStore.selectedTopic.endpoint
          }
        },
        body: {
          feedback: {
            learning_type_rating: learningTypeValue.value,
            comment: feedbackValue.value
          },
          id: chatStore.currentChat.id,
          language: locale.value,
          chat_history: chatStore.currentChat.messages,
          storage: chatStore.currentChat.storage,
          llm_purpose: chatStore.getSelectedLLMPurpose(),
          response_preferences: chatStore.responsePreferences,
          streaming: false
        }
      })
      if (error) {
        throw new Error(`Server error: ${error}`)
      }
      const message = data.messages.map(m => m.content).join('\n')
      feedbackAnswer.value = message
      chatStore.currentChat.messages.push(...data.messages.map(m => ({
        ...m,
        complete: true,
        timestamp: new Date().toISOString()
      } as ChatMessageMessage)))
      chatStore.currentChat.storage = {...chatStore.currentChat.storage, ...data.storage}
    } catch (e) {
      console.error('[FeedbackOverlay.submit] Error during API call: ', e)
      feedbackAnswer.value = t('feedbackError')
    } finally {
      isLoading.value = false
    }
  }
</script>

<template>
  <v-dialog v-model="showDialog"
            max-width="700"
            scrollable>
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          <v-icon icon="far fa-hand-point-up" start />
          <h1 class="text-headline-sm">
            {{ $t('feedbackTitle') }}
          </h1>
          <DialogCloseButton class="ms-auto" @click="showDialog = false" />
        </v-card-title>
      </v-card-item>
      <v-form v-if="showForm" class="pa-4" @submit.prevent="submit">
        <div>
          {{ $t('learningTypeFitMessage') }}
          <v-slider id="learning-type"
                    v-model="learningTypeValue"
                    class="my-2 text-h5"
                    color="primary"
                    :max="10"
                    :min="1"
                    show-ticks="always"
                    :step="1"
                    :ticks="tickLabels" />
        </div>
        <div>
          <v-textarea id="feedback" v-model="feedbackValue" :label="$t('feedbackMessage')" />
        </div>
        <v-btn block
               class="mt-2"
               color="primary"
               type="submit"
               variant="flat">
          {{ $t('submitButton') }}
        </v-btn>
      </v-form>
      <v-card-text v-else>
        <div>
          {{ feedbackAnswer }}
        </div>
        <div v-if="isLoading" class="d-flex flex-column align-center text-primary ga-3">
          <v-progress-circular color="primary" indeterminate />
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped lang="scss">

</style>
