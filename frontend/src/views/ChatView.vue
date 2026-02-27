<script setup lang="ts">
  import {ref, watch} from 'vue'
  import {useRoute, useRouter} from 'vue-router'
  import {useDisplay} from 'vuetify'
  
  import {useTopicsStore} from '@/stores/topics'
  import {useChatStore} from '@/stores/chat'

  import TopicCard from '@/components/TopicCard.vue'
  import ChatHistory from '@/components/ChatHistory.vue'
  import InspirationDialog from '@/components/dialogs/InspirationDialog.vue'
  import QuizDialog from '@/components/dialogs/QuizDialog.vue'
  import FeedbackDialog from '@/components/dialogs/FeedbackDialog.vue'
  import AiModelDialog from '@/components/dialogs/AiModelDialog.vue'
  import ReminderDialog from '@/components/dialogs/ReminderDialog.vue'

  const route = useRoute()
  const router = useRouter()
  const {thresholds, mdAndUp} = useDisplay()
  const topicsStore = useTopicsStore()
  const chatStore = useChatStore()

  const showInspiration = ref(false)
  const showQuiz = ref(false)
  const showFeedback = ref(false)
  const showAiModel = ref(false)
  const showReminder = ref(false)
  const messageInput = ref('')

  // watch([() => topicsStore.isFetching, () => topicsStore.selectedTopic, () => chatStore.currentChat], async () => {
  //   // exit if topic is not available anymore, otherwise init new chat if chatId is missing or unknown
  //   if (!topicsStore.isFetching && !topicsStore.selectedTopic)
  //     await router.push({name: 'topics'})
  //   messageInput.value = ''
  //   if (!topicsStore.isFetching && topicsStore.selectedTopic && !chatStore.currentChat)
  //     await chatStore.initChat()
  // }, {immediate: true})
  watch([() => topicsStore.selectedTopic, () => chatStore.currentChat], async () => {
    if (topicsStore.selectedTopic && !route.params.chatId)
      await router.replace({params: {chatId: chatStore.getLastChatId(topicsStore.selectedTopic.endpoint)}})

    // TODO: forward if no matching topic AND/OR if modules but no one matches with id
    messageInput.value = ''
    if (topicsStore.selectedTopic && !chatStore.currentChat)
      await chatStore.createChat()
  }, {immediate: true})

  async function submitMessage() {
    await chatStore.sendUserMessage(messageInput.value)
    if (!chatStore.isError)
      messageInput.value = ''
  }

  const feedbackHighlight = ref(false);

  function sendInspiration(message: string) {
    messageInput.value = message
    document.getElementById('message-input')?.focus()
  }

  watch(() => chatStore.currentChat?.messages.length, () => {
    const conversationalTurns = chatStore.currentChat?.messages.filter(m => m.sender === 'user').length || 0;
    if (conversationalTurns % 2 === 0 && conversationalTurns > 0) {
      feedbackHighlight.value = true;
    } else {
      feedbackHighlight.value = false;
    }
  });
</script>

<template>
  <TopicCard />
  <ChatHistory class="mt-4" />

  <InspirationDialog v-model="showInspiration" @send-inspo="(message : string) => sendInspiration(message)" />
  <QuizDialog v-model="showQuiz" />
  <FeedbackDialog v-model="showFeedback" />
  <AiModelDialog v-model="showAiModel" />
  <ReminderDialog v-model="showReminder" />

  <v-footer app
            :aria-label="$t('messageActionsLabel')"
            style="color: inherit !important; background: inherit !important;"
            tag="section">
    <v-container class="d-flex flex-column ga-3" :max-width="thresholds.md">
      <v-alert v-model="chatStore.isError"
               closable
               close-label="closeMessageError"
               color="error-container"
               :text="$t('messageError')"
               type="error" />
      <ul class="d-flex justify-end flex-wrap ga-2">
        <v-chip v-if="topicsStore.selectedTopic?.features.includes('inspirations')"
                id="inspirations"
                prepend-icon="far fa-lightbulb"
                tag="li"
                :text="$t('actionInspiration')"
                variant="outlined"
                @click="showInspiration = !showInspiration" />
        <v-chip v-if="topicsStore.selectedTopic?.features.includes('quiz')"
                prepend-icon="fas fa-list-check"
                tag="li"
                :text="$t('actionQuiz')"
                variant="outlined"
                @click="showQuiz = true" />
        <v-chip v-if="topicsStore.selectedTopic?.features.includes('feedback')"
                id="feedback"
                :class="{ 'highlight-feedback': feedbackHighlight, 'glow-feedback': feedbackHighlight }"
                prepend-icon="far fa-hand-point-up"
                tag="li"
                :text="feedbackHighlight ? $t('actionFeedbackHighlighted') : $t('actionFeedback')"
                variant="outlined"
                @click="() => { showFeedback = true; feedbackHighlight = false; }" />
        <!-- TODO: add feature flag for "models" -->
        <v-chip prepend-icon="mdi mdi-creation-outline"
                tag="li"
                :text="$t('actionAiModel')"
                variant="outlined"
                @click="showAiModel = true" />
        <v-chip v-if="topicsStore.selectedTopic?.features.includes('plan')"
                prepend-icon="far fa-bell"
                tag="li"
                :text="$t('actionReminder')"
                variant="outlined"
                @click="showReminder = true" />
      </ul>
      <v-form id="chat" class="d-flex ga-2" @submit.prevent="submitMessage">
        <v-textarea id="message-input"
                    v-model="messageInput"
                    auto-grow
                    :disabled="chatStore.isLoading || topicsStore.isFetching"
                    hide-details
                    max-rows="6"
                    no-resize
                    :placeholder="$t('messagePlaceholder')"
                    required
                    :rows="mdAndUp ? 4 : 2"
                    variant="solo-filled"
                    @keydown.enter.exact.prevent.stop="submitMessage">
          <template #append-inner>
            <v-btn :aria-label="$t('sendMessage')"
                   class="submit-button"
                   :disabled="!messageInput"
                   icon
                   :loading="chatStore.isLoading"
                   type="submit"
                   variant="text"
                   @click="submitMessage">
              <v-icon icon="fas fa-paper-plane" type="submit" />
            </v-btn>
          </template>
        </v-textarea>
      </v-form>
    </v-container>
  </v-footer>
</template>

<style lang="scss" scoped>
  .submit-button {
    .v-icon {
      color: rgb(var(--v-theme-primary)) !important;
    }

    &.v-btn--disabled .v-icon {
      color: rgb(var(--v-theme-primary)) !important;
      opacity: .38 !important;
    }
  }

  .to-front.white-shadow {
    box-shadow: 0 0 10px 5px rgba(var(--v-theme-accent), 0.4), 0 0 20px 10px rgba(var(--v-theme-accent), 0.4);
  }

  section:has(#chat.to-front) {
    z-index: 2000 !important;
    //box-shadow: inset 0 0 0 9999px rgba(0, 0, 0, .3);

    & .to-front {
      border-radius: 1.5rem;
      box-shadow: 0 0 10px 5px rgba(var(--v-theme-accent), 0.4), 0 0 20px 10px rgba(var(--v-theme-accent), 0.3);
    }

    & .v-chip {
      border-color: #8b8f94 !important;
    }
  }

  section:has(#feedback.to-front) {
    z-index: 2000 !important;
    //box-shadow: inset 0 0 0 9999px rgba(0, 0, 0, .3);

    & #chat {
      border-radius: 1.5rem;
      //box-shadow: 0 0 10px 5px rgba(255, 255, 255, 0.2), 0 0 20px 10px rgba(255, 255, 255, 0.19);
    }

    & .to-front {
      box-shadow: 0 0 10px 5px rgba(var(--v-theme-accent), 0.4), 0 0 20px 10px rgba(var(--v-theme-accent), 0.3);
      //border: 1px solid rgba(var(--v-theme-tertiary));
      background-color: white !important;
      //color: white !important;
    }
  }

  .highlight-feedback {
    background-color: rgba(var(--v-theme-primary), 0.2) !important;
    border-color: rgba(var(--v-theme-primary), 0.8) !important;
    color: rgb(var(--v-theme-primary)) !important;
  }

  .glow-feedback {
    animation: glow-pulse 1s ease-in-out;
  }

  @keyframes glow-pulse {
    0% {
      box-shadow: 0 0 10px 5px rgba(var(--v-theme-primary), 0.6), 0 0 20px 10px rgba(var(--v-theme-primary), 0.4);
    }
    100% {
      box-shadow: none;
    }
  }
</style>
