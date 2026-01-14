<script setup lang="ts">
  import {computed, onMounted, onUnmounted, ref, watch, watchEffect} from 'vue'
  import {useTheme} from 'vuetify'
  import {useI18n} from 'vue-i18n'
  import {useClipboard} from '@vueuse/core'
  import VueMarkdown from 'vue-markdown-render'
  import type MarkdownIt from 'markdown-it'

  import type {ActionButton, ChatMessage, ChatMessageEvent, ChatMessageMessage} from '@/types'

  import {useChatStore} from '@/stores/chat'
  import {useTopicsStore} from '@/stores/topics.ts'

  import gradientTextRevealLight from '@/assets/gradient-text-reveal-light.png'
  import gradientTextRevealDark from '@/assets/gradient-text-reveal-dark.png'
  import type {components} from '@/types_api'
  import SourceList from './SourceList.vue'
  import { useMemoryStore } from '@/stores/memory'
  import CommentMessageDialog from './dialogs/CommentMessageDialog.vue'

  const {message} = defineProps<{
    /**
     * The chat message to display.
     */
    message: ChatMessageMessage;
    /**
     * Indicates whether the button is disabled.
     */
    disabled?: boolean;
    /**
     * Indicates whether all actions except bookmarking are disabled.
     */
    bookmarked?: boolean;
  }>()

  const emit = defineEmits<{ retry: [], bookmark: [] }>()

  const topicsStore = useTopicsStore()

  defineOptions({
    inheritAttrs: false // needed to apply attributes from parent to nested card
  })

  // STORES & COMPOSABLES

  const theme = useTheme()
  const {t} = useI18n()
  const {
    copy: copyToClipboard,
    copied: copiedToClipboard,
    isSupported: isClipboardSupported
  } = useClipboard({copiedDuring: 1800})
  const chatStore = useChatStore()
  const memoryStore = useMemoryStore()


  // CONSTANTS & REACTIVE DATA

  const enableRetry = ref(true)
  const MESSAGE_DISPLAY_DURATION = 1500 // 1.5 seconds
  const citationList = ref([] as components['schemas']['Source'][])
  const renderedMessage = ref('')
  const loadingMessage = ref(null as string | null)
  const messageQueue = ref<string[]>([])
  const isProcessingQueue = ref(false)
  const queueTimer = ref<number | null>(null)
  const showCommentDialog = ref(false)


  // COMPUTED

  const messageText = computed(() => {
    if (message.content) {
      return renderedMessage.value.length > 0 ? renderedMessage.value : message.content
    }
    console.log("No message content found for message:", message);
    return ''
  })

  const messageInfo = computed(() => {
    if (
      !message.meta_information ||
      !message.complete ||
      message.type != 'assistant'
    )
      return
    return `${t('senderLabel')}: ${message.type}, ${t('LLMLabel')}: ${message.meta_information.llm_model
    }, ${t('sourcesLabel')}: ${message.meta_information.sources}, Citations: ${message.meta_information.citations
    }`
  })


  // CITATIONS & SOURCES

  onMounted(() => {
    // Convert citation placeholders to links and build list of only the sources that are actually used in the message
    if (message.meta_information.sources && message.complete) renderCitations()
  })

  watchEffect(() => {
    if (message.complete) {
      renderCitations()
      clearMessageQueue()
      loadingMessage.value = null
    }
  })

  function renderCitations() {
    renderedMessage.value = messageText.value.replace(/\[source_id:\s*(\d+)\]/g, (match, p1) => {
      const source = message.meta_information.sources[p1]
      if (source && citationList.value.includes(source)) {
        // If the source is already in the list, return the existing citation link
        const existingIndex = citationList.value.indexOf(source)
        return `[[${existingIndex}]](#source-${new Date(message.timestamp).getTime()}-${existingIndex})`
      }
      const newCit = citationList.value.push(message.meta_information.sources[p1]!)
      return `[[${newCit}]](#source-${new Date(message.timestamp).getTime()}-${newCit})`
    })
  }

  function getNumberOfSources() {
    return message.meta_information.sources
      ? Object.keys(message.meta_information.sources).length
      : 0
  }


  // MESSAGE EVENT PROCESSING

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

  // Process events staggeredly to show the progress
  watch(() => message.events, (newEvents, oldEvents) => {
    if (!newEvents || message.complete) return

    // get unprocessed events
    const unprocessedEvents = oldEvents
      ? newEvents.filter(e => !oldEvents.includes(e))
      : newEvents
    unprocessedEvents.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())

    // Process each unprocessed event
    for (const event of unprocessedEvents) {
      let eventMessage = ''

      if (event.event === 'think') {
        // the agent is thinking
        if (event.additional_info?.thought_summary) {
          eventMessage = event.additional_info.thought_summary as string
        } else {
          eventMessage = t('thinkingMessage')
        }
      } else if (event.event === 'retrieve_additional_information') {
        // the agent is retrieving documents
        if (event.additional_info?.query) {
          eventMessage = t('retrievingMessage', {query: event.additional_info?.query})
        } else {
          eventMessage = t('sourcesMessage', {num: getNumberOfSources()})
        }
      } else if (event.event === 'formulate_answer') {
        // the agent is writing the final answer
        eventMessage = t('modelMessage', {model: message.meta_information.llm_model || event.additional_info?.llm || 'LLM'})
      } else if (event.event === 'starting_agent') {
        // the agent is starting
        eventMessage = t('processingMessage')
      } else if (event.event === 'initial_metadata') {
        // a normal streaming message with initial metadata is starting
        if (message.meta_information.sources && getNumberOfSources() > 0) {
          eventMessage = t('sourcesMessage', {num: getNumberOfSources()})
        } else if (message.meta_information.llm_model) {
          eventMessage = t('modelMessage', {model: message.meta_information.llm_model})
        } else {
          eventMessage = t('processingMessage')
        }
      }
      // else if (event.event === "tool_completed") {
      //   // a tool has completed execution
      //   const toolName = event.additional_info?.name as string || "Unknown";
      //   eventMessage = t("toolCompletedMessage", { name: toolName });
      // }

      // Add to queue if we have a message
      if (eventMessage) {
        addToMessageQueue(eventMessage)
        // console.log("Queued event message: ", event.event, "message:", eventMessage);
      }
    }
  }, {immediate: true})

  const gradientTextReveal = computed(() => {
    return theme.current.value.dark
      ? gradientTextRevealLight
      : gradientTextRevealDark
  })

  function getMessageEvents(message: ChatMessage) {
    if (message.fragment || !message.events?.length) return []
    const excludedEvents = ['tool_completed', 'starting_agent', 'initial_metadata']
    const eventsWithoutTools = message.events.filter(event => !excludedEvents.includes(event.event)) || []
    return eventsWithoutTools.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
  }

  const eventSummaryText = computed(() => {
    if (message.fragment || !message.events?.length) return null

    if (message.complete && message.events) {
      const stepCount = getMessageEvents(message).length
      return t('generatedInSteps', {count: stepCount})
    }

    return loadingMessage.value
  })

  const hasEvents = computed(() => {
    return !message.fragment && message.events && getMessageEvents(message).length > 1 // more than just initial event
  })

  function getThoughts() {
    return message.thoughts ?? ''
  }

  function getEventDisplayText(event: ChatMessageEvent) {
    if (event.event === 'think') {
      if (event.additional_info?.thought_summary) {
        return event.additional_info.thought_summary as string
      } else {
        return t('thinkingMessage')
      }
    } else if (event.event === 'retrieve_additional_information') {
      if (event.additional_info?.query) {
        return t('retrievingMessage', {query: event.additional_info?.query})
      } else {
        return t('sourcesMessage', {num: getNumberOfSources()})
      }
    } else if (event.event === 'formulate_answer') {
      return t('modelMessage', {model: message.meta_information.llm_model || event.additional_info?.llm || 'LLM'})
    } else if (event.event === 'initial_metadata') {
      if (message.meta_information.sources && getNumberOfSources() > 0) {
        return t('sourcesMessage', {num: getNumberOfSources()})
      } else if (message.meta_information.llm_model) {
        return t('modelMessage', {model: message.meta_information.llm_model})
      } else {
        return t('processingMessage')
      }
    } else if (event.event === 'update_learner_model') {
      return t('updatingLearnerModelMessage')
    } else if (event.event === 'update_conversation_strategy') {
      return t('updatingStrategyMessage')
    } else if (event.event === 'updated_conversation_strategy') {
      return t('updatedStrategyMessage')
    } else if (event.event === 'update_memory') {
      return t('updatingMemoryMessage')
    } else if (event.event === 'get_relevant_learning_units') {
      return t('gettingLUsMessage')
    }
    return event.event
  }

  const hasPotentialMemory = computed(() => {
    return memoryStore.hasPotentialMemory(message.timestamp)
  })

  function acceptMemory() {
    memoryStore.acceptPotentialMemory(message, chatStore)
  }

  // ACTIONS

  function selectAction(button: ActionButton) {
    chatStore.sendButtonAction(button)
  }

  function resendMessage() {
    renderedMessage.value = ''
    citationList.value = []
    emit('retry')
  }

  async function voteMessage(rating: 'up' | 'down') {
    await chatStore.voteMessage(message.timestamp, rating)
  }

  function commentMessage() {
    showCommentDialog.value = true
  }

  // function editMessage() {
  //   console.log('edit') // TODO
  // }

  const wrapTableOpen = () => '<div class="table"><table>'
  const wrapTableClose = () => '</table></div>'

  // TODO: make inspiration bubble clickable via keyboard and move focus to inspo dialog if opened
</script>

<template>
  <v-hover v-slot="{ isHovering, props }">
    <article class="d-flex align-end ga-2"
             :class="{ 'justify-end align-center': message.type !== 'assistant' && message.type !== 'system' }"
             v-bind="props">
      <v-card :class="{
                'message-bot': message.type === 'assistant' || message.type === 'system',
                'message-user': message.type === 'user',
                'message-inspiration': message.meta_information.isInspiration,
              }"
              :loading="loadingMessage == null && !message.complete"
              variant="tonal"
              v-bind="$attrs">
        <v-card-text v-if="loadingMessage == null && !message.complete"
                     class="mb-2 d-flex flex-row justify-space-between align-center ga-4"
                     style="min-width: 6rem" />
        <v-card-text v-else>
          <!-- Event Timeline Toggle -->
          <v-expansion-panels v-if="hasEvents && (loadingMessage !== null || message.complete || message.type === 'system')"
                              class="mb-3">
            <v-expansion-panel class="rounded-lg border"
                               :class="{
                                 'border-white': !theme.current.value.dark,
                                 'border-black': theme.current.value.dark,
                               }"
                               elevation="0">
              <v-expansion-panel-title :class="{
                'border-white': !theme.current.value.dark,
                'border-black': theme.current.value.dark,
              }">
                <template #default="{ expanded }">
                  <div class="d-flex align-center ga-2" :class="{ 'border-bottom': expanded }">
                    <v-icon icon="fas fa-clock" size="x-small" />
                    <span v-if="message.complete" class="text-animation-off">
                      {{ eventSummaryText }}
                    </span>
                    <span v-else
                          class="text-animation"
                          :style="{ 'background-image': `url(${gradientTextReveal})` }">
                      {{ eventSummaryText }}
                    </span>
                  </div>
                </template>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div class="timeline-container">
                  <div v-for="(event, index) in getMessageEvents(message)"
                       :key="`${event.timestamp}-${index}`"
                       class="timeline-item">
                    <div class="timeline-dot"
                         :class="{ 'active': index === (getMessageEvents(message).length ?? 0) - 1 && !message.complete }" />
                    <div class="timeline-content">
                      <div class="timeline-text">
                        {{ getEventDisplayText(event) }}
                      </div>
                    </div>
                  </div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <!-- Loading Animation (when no events or fallback) -->
          <div v-else-if="!message.complete"
               class="mb-4 text-body-sm text-animation"
               :style="{ 'background-image': `url(${gradientTextReveal})` }">
            <span v-if="loadingMessage !== null">{{ loadingMessage }}</span>
          </div>
          <span class="d-sr-only">
            {{
              message.type === 'assistant'
                ? $t('messageSenderBot')
                : $t('messageSenderYou')
            }}:
          </span>
          <v-expansion-panels v-if="getThoughts()" class="mb-3">
            <v-expansion-panel class="rounded-lg border"
                               :class="{
                                 'border-white': !theme.current.value.dark,
                                 'border-black': theme.current.value.dark,
                               }"
                               elevation="0">
              <v-expansion-panel-title :class="{
                'border-white': !theme.current.value.dark,
                'border-black': theme.current.value.dark,
              }">
                <template #default="{ expanded }">
                  <div :class="{ 'border-bottom': expanded }">
                    {{ $t('thoughtsLabel') }}
                  </div>
                </template>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <VueMarkdown class="text-start chat-message text-body-sm" :source="getThoughts()" />
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
          <VueMarkdown class="markdown"
                       :plugins="[(md: MarkdownIt) => {md.renderer.rules.table_open = wrapTableOpen; md.renderer.rules.table_close = wrapTableClose}]"
                       :source="messageText" />
          <SourceList v-if="citationList.length > 0" :citations="citationList" :timestamp="message.timestamp" />
        </v-card-text>
        <v-card-actions v-if="message.buttons?.length" class="flex-wrap justify-end" role="group">
          <v-chip v-for="(button, index) in message.buttons"
                  :key="index"
                  :text="button.label"
                  variant="outlined"
                  @click="selectAction(button)" />
        </v-card-actions>
        <template #loader="{ isActive }">
          <v-progress-linear v-if="isActive" indeterminate />
        </template>
      </v-card>
      <ul v-show="isHovering || message.meta_information.isInspiration"
          :class="{ 'order-first text-end': message.type === 'user' }">
        <v-btn v-if="message.type === 'assistant' && !bookmarked"
               :aria-label="$t('message.action.voteUp')"
               icon
               variant="text"
               @click="voteMessage('up')">
          <v-icon icon="far fa-thumbs-up" size="small" />
          <v-tooltip activator="parent" :text="$t('message.action.voteUp')" />
        </v-btn>
        <v-btn v-if="message.type === 'assistant' && !bookmarked"
               :aria-label="$t('message.action.voteDown')"
               icon
               variant="text"
               @click="voteMessage('down')">
          <v-icon icon="far fa-thumbs-down" size="small" />
          <v-tooltip activator="parent" :text="$t('message.action.voteDown')" />
        </v-btn>
        <v-btn v-if="message.type === 'assistant' && !bookmarked"
               :aria-label="$t('message.action.comment')"
               icon
               variant="text"
               @click="commentMessage">
          <v-icon icon="far fa-comment" size="small" />
          <v-tooltip activator="parent" :text="$t('message.action.comment')" />
        </v-btn>
        <CommentMessageDialog v-model="showCommentDialog"
                              :message-id="message.timestamp" />
       
        <v-btn v-if="messageInfo"
               :aria-label="messageInfo"
               icon
               variant="text">
          <v-icon icon="fas fa-circle-info" size="small" />
          <v-tooltip activator="parent">
            <span>{{ $t('senderLabel') }}: {{ message.type }}</span><br>
            <span v-if="message.meta_information.llm_model">{{ $t('LLMLabel') }}: {{
              message.meta_information.llm_model
            }}</span>
          </v-tooltip>
        </v-btn>
        <v-btn v-if="isClipboardSupported && !message.meta_information.isInspiration"
               :aria-label="$t('message.action.copy')"
               icon
               variant="text"
               @click="copyToClipboard(message.content)">
          <v-icon icon="far fa-copy" size="small" />
          <v-tooltip activator="parent"
                     :text="copiedToClipboard
                       ? $t('message.action.copied')
                       : $t('message.action.copy')
                     " />
        </v-btn>
        <v-btn v-if="message.type === 'assistant' && !message.meta_information.isInspiration && topicsStore.selectedTopic?.features.includes('dashboard')"
               :aria-label="bookmarked ? $t('message.action.bookmarkRemove') : $t('message.action.bookmark')"
               icon
               variant="text"
               @click="$emit('bookmark')">
          <v-icon :icon="bookmarked ? 'fas fa-thumbtack-slash' : 'fas fa-thumbtack'" size="small" />
          <v-tooltip activator="parent"
                     :text="bookmarked ? $t('message.action.bookmarkRemove') : $t('message.action.bookmark')" />
        </v-btn>
        <v-btn v-if="message.type === 'assistant' && enableRetry && !bookmarked"
               :aria-label="$t('message.action.resend')"
               icon
               variant="text"
               @click="resendMessage">
          <v-icon icon="fas fa-arrow-rotate-right" size="small" />
          <v-tooltip activator="parent" :text="$t('message.action.resend')" />
        </v-btn>
        <!--        <v-btn v-if="message.sender === 'user' && !bookmarked" -->
        <!--               :aria-label="$t('messageActionEdit')" -->
        <!--               icon -->
        <!--               variant="text" -->
        <!--               @click="editMessage"> -->
        <!--          <v-icon icon="fas fa-pencil" size="small" /> -->
        <!--          <v-tooltip activator="parent" :text="$t('messageActionEdit')" /> -->
        <!--        </v-btn> -->
      </ul>
    </article>
  </v-hover>
  <span v-if="message.meta_information['user_memory']"
        class="d-flex align-end ga-2 mt-1 text-secondary"
        :class="{ 'justify-end align-center': message.type !== 'assistant' && message.type !== 'system' }">
    <VueMarkdown class="markdown text-body-sm" :source=" $t('memoryUpdatedMessage')" />
  </span>
  <div v-if="hasPotentialMemory">
    <v-alert class="mt-2 memory-update-message" type="info" variant="outlined">
      <div class="d-flex flex-column ga-2">
        <div>
          {{ $t('memory.potentialMemoryMessage') }}
        </div>
        <div>
          <strong>{{ memoryStore.getPotentialMemory(message.timestamp) }}</strong>
        </div>
        <div class="d-flex ga-2 w-100">
          <v-btn variant="tonal" @click="acceptMemory">
            {{ $t('acceptButton') }}
          </v-btn>
          <v-btn variant="tonal" @click="memoryStore.rejectPotentialMemory(message.timestamp)">
            {{ $t('rejectButton') }}
          </v-btn>
        </div>
      </div>
    </v-alert>
  </div>
</template>

<style scoped lang="scss">
  article {
    .v-card {
      max-width: 75%;
      border-radius: 20px !important;
      $sender-border-radius: 8px;

      &.message-bot {
        background: rgb(var(--v-theme-surface-container-high)) !important;
        color: rgb(var(--v-theme-on-surface)) !important;
        border-bottom-left-radius: $sender-border-radius !important;

        :deep(pre), :deep(blockquote), :deep(.table) {
          padding: 16px !important;
          background: rgb(var(--v-theme-surface-dim)) !important;
          color: rgb(var(--v-theme-on-surface)) !important;
          border-radius: $sender-border-radius !important;
          border-inline-start: 8px solid rgb(var(--v-theme-tertiary-fixed-dim));
          overflow-x: auto;
          scrollbar-color: rgb(var(--v-theme-on-surface)) transparent;
        }

        :deep(code) { // inline code
          background: rgb(var(--v-theme-surface-dim)) !important;
          color: rgb(var(--v-theme-on-surface)) !important;
          border-radius: calc($sender-border-radius / 2) !important;
          padding: 0 .25rem !important;
        }
      }

      &.message-user {
        background: rgb(var(--v-theme-secondary)) !important;
        color: rgb(var(--v-theme-on-secondary)) !important;
        border-bottom-right-radius: $sender-border-radius !important;
      }

      &.message-inspiration {
        background: rgb(var(--v-theme-secondary-container)) !important;
        border-bottom-right-radius: $sender-border-radius !important;
        color: rgb(var(--v-theme-on-secondary-container)) !important;
      }

      :deep(.v-card__loader) {
        padding: 0 16px;
        top: auto;
        bottom: 0;
      }
    }

    .v-icon {
      opacity: 0.85;
    }
  }

  .memory-update-message {
    max-width: 75%;
    border-radius: 20px !important;
  }

  .text-animation {
    max-width: fit-content;
    -webkit-background-clip: text !important;
    background-clip: text !important;
    color: transparent !important;
    background: url("@/assets/gradient-text-reveal-dark.png");
    background-size: 200% 100%;
    background-position: 150% 0%;
    background-repeat: repeat-x;
    animation: reveal 2s ease-in-out infinite reverse;
  }

  .text-animation-off {
    max-width: fit-content;
  }


  .timeline-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding-bottom: 8px;
    position: relative;

    &:last-child {
      padding-bottom: 0;
    }
  }

  .timeline-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: rgba(var(--v-border-color), 0.3);
    border: 2px solid rgba(var(--v-border-color), 0.5);
    flex-shrink: 0;
    margin-top: 2px;

    &.active {
      background: rgb(var(--v-theme-primary));
      border-color: rgb(var(--v-theme-primary));
      animation: pulse 2s ease-in-out infinite;
    }
  }

  .timeline-content {
    flex-grow: 1;
    min-width: 0;
  }

  .timeline-text {
    font-size: 0.875rem;
    line-height: 1.4;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .timeline-duration {
    opacity: 0.7;
    font-size: 0.75rem;
    color: rgb(var(--v-theme-on-surface-variant));
    white-space: nowrap;
  }

  @keyframes reveal {
    0% {
      background-position: 150% 0%;
    }

    100% {
      background-position: 350% 0%;
    }
  }

  @keyframes pulse {
    0%, 100% {
      transform: scale(1);
      opacity: 1;
    }
    50% {
      transform: scale(1.1);
      opacity: 0.8;
    }
  }
</style>
