<script setup lang="ts">
  import {useChatStore} from '@/stores/chat.ts'
  import {useLearningTypesStore} from '@/stores/learningTypes.ts'
  import type {ChatMessage} from '@/types.ts'
  import type {paths} from '@/types_api.ts'
  import createClient from 'openapi-fetch'
  import {ref, watchEffect, type Ref} from 'vue'
  import {useI18n} from 'vue-i18n'
  import {useTopicsStore} from '@/stores/topics.ts'
  import DialogCloseButton from '@/components/buttons/DialogCloseButton.vue'

  const showDialog = defineModel<boolean>({default: false})

  const topicsStore = useTopicsStore()
  const learningTypesStore = useLearningTypesStore()
  const chatStore = useChatStore()
  const client = createClient<paths>({baseUrl: import.meta.env.VITE_API_URL})

  const {locale, t} = useI18n()
  const showSuccess = ref(false)
  const recommendedDate = ref(new Date())
  const recommendedTopics: Ref<string[]> = ref([])
  const topicSelection = ref('')
  const plannedDate = ref(new Date())
  const recommendationsReady = ref(false)
  const isLoading = ref(false)

  watchEffect(() => {
    recommendationsReady.value = false
    isLoading.value = false
  })

  const getRecommendations = async () => {
    if (!topicsStore.selectedTopic || !chatStore.currentChat) {
      console.error('[FeedbackOverlay.getRecommendations] Topic/Chat not set')
      return
    }
    try {
      const {data, error: fetchError} = await client.POST('/topic/{topic}/plan-session', {
        params: {
          path: {
            topic: topicsStore.selectedTopic.endpoint
          }
        },
        body: {
          learning_type_id: learningTypesStore.selectedLearningTypeId,
          storage: chatStore.currentChat.storage,
          language: locale.value,
          chat_history: chatStore.currentChat.messages,
          llm_purpose: chatStore.getSelectedLLMPurpose(),
          streaming: false
        }
      })
      if (fetchError) {
        throw new Error(`Server error: ${fetchError}`)
      }
      if (!data) {
        throw new Error('Invalid response from server')
      }
      recommendedDate.value = new Date(data.recommended_date)
      plannedDate.value = new Date(data.recommended_date)
      recommendedTopics.value = data.recommended_topics
      topicSelection.value = data.recommended_topics[0]
    } catch (e) {
      console.error('[FeedbackOverlay.getRecommendations] Error during API call: ', e)
    }
  }

  const planDate = async () => {
    showSuccess.value = true
    const message = t('plannedDateUserMessage', {
      date: plannedDate.value.toLocaleDateString(),
      topic: topicSelection.value
    })
    chatStore.currentChat?.messages.push({
      message: message,
      sender: 'user',
      buttons: [],
      meta_information: {} as ChatMessage['meta_information'],
      timestamp: new Date().toISOString(),
      complete: true
    })
  }

  const loadRecommendations = async () => {
    if (!recommendationsReady.value) {
      await getRecommendations().then(() => {
        recommendationsReady.value = true
      })
    }
  }

  const closeDialog = () => {
    showDialog.value = false
    showSuccess.value = false
  }
</script>

<template>
  <v-dialog v-model="showDialog" max-width="700" @after-enter="loadRecommendations">
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          <v-icon icon="far fa-bell" start />
          <h1 class="text-headline-sm">
            {{ $t('dateTitle') }}
          </h1>
          <DialogCloseButton class="ms-auto" @click="showDialog = false" />
        </v-card-title>
      </v-card-item>
      <div v-if="!recommendationsReady">
        <v-skeleton-loader type="paragraph@3" />
      </div>
      <v-form v-if="recommendationsReady && !showSuccess" class="pa-4" @submit.prevent="planDate">
        <div class="d-flex flex-column ga-10">
          <div class="d-flex flex-column justify-center ga-2">
            <span class="d-flex flex-column align-center justify-center text-h6">{{ $t('planDateMessage') }}</span>
            <div class="justify-center align-center d-flex flex-column">
              <v-date-picker v-model="plannedDate"
                             color="primary"
                             elevation="4"
                             :header="$t('planDateMessage')"
                             :min="new Date().toISOString()" />
            </div>
          </div>
          <div class="d-flex flex-column justify-center ga-2 align-center">
            <span class="d-flex flex-column align-center justify-center text-h6">{{
              $t('topicSelectionMessage')
            }}</span>
            <v-select v-model="topicSelection"
                      class="w-lg-75 w-100"
                      :items="recommendedTopics" />
          </div>
        </div>
        <v-btn block
               class="mt-2"
               color="primary"
               type="submit">
          {{ $t('submitButton') }}
        </v-btn>
      </v-form>
      <v-card-text v-if="showSuccess">
        {{ $t('plannedDateMessage', {date: plannedDate.toLocaleDateString(), topic: topicSelection}) }}
      </v-card-text>
      <v-card-actions v-if="showSuccess">
        <v-btn block
               class="mt-2"
               color="primary"
               @click="closeDialog">
          {{ $t('closeButton') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped lang="scss">

</style>
