<script setup lang="ts">
  import {ref, watch, computed, onMounted, onBeforeUnmount, nextTick, type ComputedRef} from 'vue'
  import {useRoute, useRouter} from 'vue-router'
  import {useDisplay, useTheme} from 'vuetify'
  import {useI18n} from 'vue-i18n'
  import VueMarkdown from 'vue-markdown-render'

  import {useTopicsStore} from '@/stores/topics'
  import {useChatStore} from '@/stores/chat'
  import {useQuizStore} from '@/stores/quiz.ts'
  import {useOnboardingStore} from '@/stores/onboarding'

  import ChatHistory from '@/components/ChatHistory.vue'
  import InspirationDialog from '@/components/dialogs/InspirationDialog.vue'
  import QuizDialog from '@/components/dialogs/QuizDialog.vue'
  import FeedbackDialog from '@/components/dialogs/FeedbackDialog.vue'
  import AiModelDialog from '@/components/dialogs/AiModelDialog.vue'
  import ReminderDialog from '@/components/dialogs/ReminderDialog.vue'
  import OnboardingStep from '@/components/OnboardingStep.vue'
  import ChatDashboard from '@/components/ChatDashboard.vue'
  import StartReflectionDialog from '@/components/dialogs/StartReflectionDialog.vue'
  import StorageInfoDialog from '@/components/dialogs/StorageInfoDialog.vue'

  import type {components} from '@/types_api.ts'
  import type {Chat, ChatMessageMessage} from '@/types.ts'

  const route = useRoute()
  const router = useRouter()
  const {thresholds, mdAndUp, xs} = useDisplay()
  const theme = useTheme()
  const {locale} = useI18n()
  const chatbotsStore = useTopicsStore()
  const chatStore = useChatStore()
  const onboardingStore = useOnboardingStore()

  const collapseCard = ref(false)
  const showInspiration = ref(false)
  const showFeedback = ref(false)
  const showAiModel = ref(false)
  const showReminder = ref(false)
  const showReflection = ref(false)
  const messageInput = ref('')
  const showStorageInfo = ref(false)
  const isManualCardCollapseToggle = ref(false)
  const maxCardHeight = ref<number | undefined>()

  const isDev = import.meta.env.DEV
  let scrollContainer: HTMLElement | null = null
  let lastScrollTop = 0

  onMounted(async () => {
    scrollContainer = document.querySelector('.v-main__scroller')
    scrollContainer?.addEventListener('scroll', handleScroll)
    setTimeout(() => {
      // TODO: fix positioning of card when loading existing chat
      maxCardHeight.value = scrollContainer ? scrollContainer.offsetHeight - 20 : undefined
    }, 1000)
  })

  onBeforeUnmount(() => {
    scrollContainer?.removeEventListener('scroll', handleScroll)
  })

  const selectedModule = computed(() => chatbotsStore.selectedTopic?.modules.find(module => module.code === route.params.chatId) as components['schemas']['Skill'])
  const selectedLevel = computed(() => selectedModule.value?.levels.find(level => level.id.toString() === chatbotsStore.storedModuleLevelId(selectedModule.value?.code)?.toString()))
  const lastAssistantMessage = computed(() => chatStore.currentChat?.messages.slice().reverse().find(m => m.type === 'assistant' && !m.fragment) as ChatMessageMessage | undefined)
  const isWipTopic = computed(() => chatbotsStore.selectedTopic?.features.includes('wip'))

  watch(
    [() => chatbotsStore.selectedTopic, () => chatStore.currentChat],
    async () => {
      if (chatbotsStore.selectedTopic && !route.params.chatId)
        await router.replace({
          params: {
            chatId: chatStore.getLastChatId(chatbotsStore.selectedTopic.endpoint)
          }
        })

      // TODO: forward if no matching topic AND/OR if modules but no one matches with id
      messageInput.value = ''
      if (chatbotsStore.selectedTopic && !chatStore.currentChat)
        await chatStore.createChat()

      if (chatbotsStore.selectedTopic?.type === 'coach') {
        // check when last time the user chatted was, and greet if longer than x hours
        const longerThanHours = 6
        const lastMessage = chatStore.currentChat?.messages.slice().reverse().find(m => m.type === 'assistant' || m.type === 'user')
        if (lastMessage) {
          const hoursSinceLastMessage = (Date.now() - new Date(lastMessage.timestamp).getTime()) / (1000 * 60 * 60)
          if (hoursSinceLastMessage > longerThanHours) {
            await chatStore.initChat()
          }
        }
      }
    }, {immediate: true}
  )

  watch(() => lastAssistantMessage.value?.complete, (newValue) => {
    if (newValue && !chatStore.isError) {
      messageInput.value = ''
    }
  })

  function getChatTitle(chat: Chat) {
    const title = chat.title || chatStore.getDefaultChatTitle()
    return title.length > 48 ? `${title.slice(0, 48)}...` : title // if longer than 48 chars, cut it off
  }

  function openStorageInfo() {
    showStorageInfo.value = true
  }

  function getImageUrl(imageURL: string) {
    if (!imageURL) return ''
    return import.meta.env.VITE_API_URL + imageURL.replace('{theme}', theme.current.value.dark ? 'dark' : 'light')
  }

  async function submitMessage() {
    await chatStore.sendUserMessage(messageInput.value)
  }

  function sendInspiration(message: string) {
    messageInput.value = message
    document.getElementById('message-input')?.focus()
  }

  function sendErrorMail() {
    const errorDetails = JSON.stringify(chatStore.errorObject, null, 2)
    const subject = encodeURIComponent(`Bug Report for Metis`)
    const body = encodeURIComponent(`Dear KI_FEM Team,\nI would like to report a bug in Metis.\n\nLocation: ${window.location.href}\nBug Details: ${errorDetails}`)
    window.open(`mailto:ki-fem@tu-dresden.de?subject=${subject}&body=${body}`)
  }

  async function handleScroll() {
    if (!scrollContainer || isManualCardCollapseToggle.value)
      return

    const scrollTop = scrollContainer.scrollTop
    const scrollDelta = scrollTop - lastScrollTop
    lastScrollTop = scrollTop

    if (scrollDelta > 0 && scrollTop > 16 && !collapseCard.value)
      collapseCard.value = true
  }

  async function toggleCardCollapse() {
    isManualCardCollapseToggle.value = true
    collapseCard.value = !collapseCard.value
    await nextTick()

    setTimeout(() => {
      isManualCardCollapseToggle.value = false
      if (scrollContainer)
        lastScrollTop = scrollContainer.scrollTop
    }, 300)
  }

  async function handleOpenQuiz() {
    showReflection.value = true
  }
</script>

<template>
  <v-container :max-width="thresholds.md">
    <v-card class="mb-4 d-flex flex-column"
            :max-height="maxCardHeight"
            style="position: sticky; top: 0; z-index: 1;"
            tag="header">
      <v-card-item>
        <v-card-title class="d-flex align-center ga-3 text-headline-sm text-sm-headline-md text-md-headline-lg">
          <v-icon icon="mdi mdi-book-open-variant" :style="{color: chatbotsStore.selectedTopic?.color}" />
          <v-skeleton-loader :loading="chatbotsStore.isFetching" type="heading" :width="xs ? '80%' : '60%'">
            <h2 class="d-flex flex-row align-center ga-2" style="font-size: inherit; font-weight: inherit;">
              <span>
                {{ chatbotsStore.selectedTopic?.title[locale] }}
              </span>
              <v-chip v-if="chatbotsStore.selectedTopic?.tag"
                      density="comfortable"
                      label
                      variant="outlined">
                {{ chatbotsStore.selectedTopic?.tag }}
              </v-chip>
            </h2>
          </v-skeleton-loader>
          <v-btn v-tooltip="collapseCard ? $t('topicCardMaximize') : $t('topicCardMinimize')"
                 class="ms-auto"
                 :icon="collapseCard ? 'fas fa-chevron-down' : 'fas fa-chevron-up'"
                 variant="text"
                 @click="toggleCardCollapse" />
        </v-card-title>
      </v-card-item>
      <v-expand-transition>
        <v-card-text v-if="!collapseCard" class="d-flex pb-0 overflow-y-auto" style="overscroll-behavior: contain;">
          <v-skeleton-loader :loading="chatbotsStore.isFetching" type="sentences">
            <VueMarkdown class="markdown" :source="chatbotsStore.selectedTopic?.long_description[locale] || ''" />
          </v-skeleton-loader>
          <div class="flex-shrink-0">
            <img v-if="chatbotsStore.selectedTopic?.avatar"
                 alt=""
                 :height="xs ? 100 : 200"
                 :src="getImageUrl(chatbotsStore.selectedTopic?.avatar)"
                 style="object-fit: contain">
          </div>
        </v-card-text>
      </v-expand-transition>
      <v-expand-transition>
        <v-card-actions v-if="!collapseCard">
          <v-skeleton-loader class="w-100 align-end ga-2" :loading="chatbotsStore.isFetching" type="button@2">
            <template v-if="selectedModule">
              <OnboardingStep storage-key="switchModuleLevel" :text="$t('onboardingSwitchModuleLevel')" />
              <v-chip class="bg-secondary"
                      prepend-icon="fas fa-graduation-cap"
                      :to="{name: 'modules'}">
                <span class="d-sr-only">{{ $t('actionModule') + ': ' }}</span>
                {{ selectedModule?.title[locale] }}
              </v-chip>
              <v-chip class="bg-tertiary"
                      prepend-icon="fas fa-flag-checkered"
                      :to="{name: 'modules'}">
                <span class="d-sr-only">{{ $t('actionLevel') + ': ' }}</span>
                {{ selectedLevel?.title[locale] }}
              </v-chip>
            </template>
            <template v-else-if="chatbotsStore.selectedTopic?.type === 'basic'">
              <OnboardingStep storage-key="switchChats" :text="$t('onboardingSwitchChats')" />
              <v-chip class="bg-secondary"
                      prepend-icon="fas fa-clock-rotate-left">
                {{ $t('actionChatHistory') }}
                <v-menu activator="parent" open-on-click>
                  <v-list>
                    <v-list-item v-for="chat in chatStore.topicChats"
                                 :key="chat.id"
                                 :subtitle="chat.id"
                                 :title="getChatTitle(chat)"
                                 :to="{name: 'chat', params: {chatId: chat.id}}" />
                  </v-list>
                </v-menu>
              </v-chip>
              <v-chip class="bg-tertiary"
                      prepend-icon="far fa-comment"
                      :text="$t('actionNewChat')"
                      :to="{name: 'chat', params: {chatId: 'new'}}" />
            </template>
            <v-spacer />
            <v-chip v-if="isDev"
                    class="bg-tertiary"
                    prepend-icon="fas fa-database"
                    text="Debug Storage"
                    @click="openStorageInfo" />
            <StorageInfoDialog v-model="showStorageInfo" />
            <v-btn v-if="chatbotsStore.selectedTopic?.optional"
                   v-tooltip="$t('topicUnsubscribe')"
                   icon="mdi mdi-minus-circle-outline"
                   @click="chatbotsStore.unsubscribeTopic(chatbotsStore.selectedTopic?.endpoint)" />
          </v-skeleton-loader>
        </v-card-actions>
      </v-expand-transition>
    </v-card>

    <ChatHistory />
    <ChatDashboard v-if="chatbotsStore.selectedTopic?.features.includes('dashboard')" />

    <InspirationDialog v-model="showInspiration" @send-inspo="(message : string) => sendInspiration(message)" />
    <QuizDialog />
    <FeedbackDialog v-model="showFeedback" />
    <AiModelDialog v-model="showAiModel" />
    <ReminderDialog v-model="showReminder" />
    <StartReflectionDialog v-model="showReflection" />

    <v-footer app
              :aria-label="$t('messageActionsLabel')"
              style="color: inherit !important; background: inherit !important;"
              tag="section">
      <v-container class="d-flex flex-column ga-3" :max-width="thresholds.md">
        <OnboardingStep v-if="onboardingStore.isRead('switchChats') || onboardingStore.isRead('switchModuleLevel')"
                        storage-key="chatActions"
                        :text="$t('onboardingChatActions')" />
        <v-alert v-model="chatStore.isError"
                 closable
                 close-label="closeMessageError"
                 color="error-container"
                 type="error">
          <template #text>
            <div class="w-100 d-flex flex-row  justify-space-between  align-center">
              {{ $t('messageError') }}
              <v-btn :aria-label="$t('reportBugLabel')"
                     class="bug-button"
                     :color="'secondary'"
                     prepend-icon="fas fa-bug"
                     :text="$t('reportBugLabel')"
                     @click="sendErrorMail()" />
            </div>
          </template>
        </v-alert>
        <ul class="d-flex justify-end align-center flex-wrap ga-2">
          <v-chip v-if="chatbotsStore.selectedTopic?.features.includes('inspirations')"
                  id="inspirations"
                  prepend-icon="far fa-lightbulb"
                  tag="li"
                  :text="$t('actionInspiration')"
                  variant="outlined"
                  @click="showInspiration = !showInspiration" />
          <v-chip v-if="chatbotsStore.selectedTopic?.features.includes('quiz')"
                  prepend-icon="fas fa-list-check"
                  tag="li"
                  :text="$t('actionQuiz')"
                  variant="outlined"
                  @click="handleOpenQuiz()" />
          <v-chip v-if="chatbotsStore.selectedTopic?.features.includes('feedback')"
                  prepend-icon="far fa-hand-point-up"
                  tag="li"
                  :text="$t('actionFeedback')"
                  variant="outlined"
                  @click="showFeedback = true" />
          <v-chip v-if="chatbotsStore.selectedTopic?.features.includes('aimodel')"
                  prepend-icon="mdi mdi-creation-outline"
                  tag="li"
                  :text="$t('actionAiModel')"
                  variant="outlined"
                  @click="showAiModel = true" />
          <v-chip v-if="chatbotsStore.selectedTopic?.features.includes('plan')"
                  prepend-icon="far fa-bell"
                  tag="li"
                  :text="$t('actionReminder')"
                  variant="outlined"
                  @click="showReminder = true" />
          <v-btn v-if="chatbotsStore.selectedTopic?.features.includes('dashboard')"
                 v-tooltip="chatStore.showDashboard ? $t('dashboardClose') : $t('dashboardOpen')"
                 icon="mdi mdi-view-dashboard"
                 variant="text"
                 @click="chatStore.showDashboard = !chatStore.showDashboard" />
        </ul>
        <v-form id="chat" class="d-flex ga-2" @submit.prevent="submitMessage">
          <v-textarea id="message-input"
                      v-model="messageInput"
                      auto-grow
                      :disabled="chatStore.isLoading || chatbotsStore.isFetching || isWipTopic"
                      hide-details
                      max-rows="6"
                      no-resize
                      :placeholder="isWipTopic ? $t('messagePlaceholderWIP') : $t('messagePlaceholder')"
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
  </v-container>
</template>

<style scoped lang="scss">
  .submit-button {
    .v-icon {
      color: rgb(var(--v-theme-primary)) !important;
    }

    &.v-btn--disabled .v-icon {
      color: rgb(var(--v-theme-primary)) !important;
      opacity: .38 !important;
    }
  }

  .bug-button {
    color: rgb(var(--v-theme-error)) !important;
    background-color: rgba(var(--v-theme-on-error)) !important;
  }
</style>
