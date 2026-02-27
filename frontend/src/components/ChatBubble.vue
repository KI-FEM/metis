<script setup lang="ts">
  import { computed, onMounted, ref, watchEffect } from "vue";
  import { useTheme } from "vuetify";
  import { useI18n } from "vue-i18n";
  import { useClipboard } from "@vueuse/core";
  import VueMarkdown from "vue-markdown-render";
  import type MarkdownIt from 'markdown-it'

  import type { ActionButton, ChatMessage } from "@/types";

  import { useChatStore } from "@/stores/chat";
  import gradientTextRevealLight from "@/assets/gradient-text-reveal-light.png";
  import gradientTextRevealDark from "@/assets/gradient-text-reveal-dark.png";
  import type { components } from "@/types_api";
  import SourceList from "./SourceList.vue";

  const { message } = defineProps<{
    /**
     * The chat message to display.
     */
    message: ChatMessage;
    /**
     * Indicates whether the button is disabled.
     */
    disabled?: boolean;
  }>();

  const emit = defineEmits<{ retry: [] }>();

  defineOptions({
    inheritAttrs: false, // needed to apply attributes from parent to nested card
  });

  const theme = useTheme();
  const { t } = useI18n();
  const {
    copy: copyToClipboard,
    copied: copiedToClipboard,
    isSupported: isClipboardSupported,
  } = useClipboard({ copiedDuring: 1800 });

  const chatStore = useChatStore();


  export type LoadingState =
    | "thinking"
    | "sources_done"
    | "model_done"
    | "done"
    | "model_and_sources_done"
    | "waiting";
  const enableRetry = ref(true);

  const messageInfo = computed(() => {
    if (
      !message.meta_information ||
      !message.complete ||
      message.sender != "assistant"
    )
      return;
    return `${t("senderLabel")}: ${message.sender}, ${t("LLMLabel")}: ${message.meta_information.llm_model
    }, ${t("sourcesLabel")}: ${message.meta_information.sources}, Citations: ${message.meta_information.citations
    }`;
  });

  const citationList = ref([] as components["schemas"]["Source"][]);
  const renderedMessage = ref("");

  const messageText = computed(() => {
    return renderedMessage.value.length > 0 ? renderedMessage.value : message.message;
  });

  function renderCitations() {
    renderedMessage.value = messageText.value.replace(/\[source_id:\s*(\d+)\]/g, (match, p1) => {
      const newCit = citationList.value.push(message.meta_information.sources[Number(p1)]);
      return `[[${newCit}]](#source-${new Date(message.timestamp).getTime()}-${newCit})`;
    });
  }

  onMounted(() => {
    // Convert citation placeholders to links and build list of only the sources that are actually used in the message
    if (message.meta_information.sources && (loadingState.value == "done" || message.complete)) renderCitations();
  });

  function getNumberOfSources() {
    return message.meta_information.sources
      ? Object.keys(message.meta_information.sources).length
      : 0;
  }

  const isLoading = computed(() => {
    return !message.message || message.message === "";
  });

  const loadingState = computed((): LoadingState => {
    if (!message) return "waiting"; // waiting for server/backend mit indicator (andere zustände mit schimmerndem Text)
    if (
      (!message.message || message.message.length == 0) &&
      message.meta_information.sources &&
      Object.keys(message.meta_information.sources).length > 0
    )
      return "sources_done"; // nur Quellen, kein LLM
    if (
      message.meta_information.llm_model &&
      message.meta_information.sources &&
      Object.keys(message.meta_information.sources).length > 0
    )
      return "model_and_sources_done"; // mit RAG
    if (message.thoughts && message.thoughts.length > 0) return "thinking"; // bei thinking models mit thoughts (nicht bei lama)
    if (message.meta_information.llm_model) return "model_done"; // ohne RAG
    if (!isLoading.value) return "done"; // alles fertig (letzter token reingekommen)
    return "waiting";
  });

  watchEffect(() => {
    if (!loadingState.value) return;
    if (loadingState.value === "done" || message.complete) renderCitations();
  });

  const gradientTextReveal = computed(() => {
    return theme.current.value.dark
      ? gradientTextRevealLight
      : gradientTextRevealDark;
  });

  function selectAction(button: ActionButton) {
    chatStore.sendButtonAction(button);
  }

  // function voteMessage(rating: 'up' | 'down') {
  //   console.log('vote', rating) // TODO
  // }

  function resendMessage() {
    console.log("resend"); // TODO
    renderedMessage.value = "";
    emit("retry");
  }

  // function editMessage() {
  //   console.log('edit') // TODO
  // }

  function getThoughts() {
    return message.thoughts ?? "";
  }

  const wrapTableOpen = () => '<div class="table"><table>'
  const wrapTableClose = () => '</table></div>'

  // TODO: make inspiration bubble clickable via keyboard and move focus to inspo dialog if opened
</script>

<template>
  <v-hover v-slot="{ isHovering, props }">
    <article class="d-flex align-end ga-2"
             :class="{ 'justify-end align-center': message.sender !== 'assistant' }"
             v-bind="props">
      <v-card :class="{
                'message-bot': message.sender === 'assistant',
                'message-user': message.sender === 'user',
                'message-inspiration': message.meta_information.isInspiration,
              }"
              :loading="loadingState === 'waiting'"
              variant="tonal"
              v-bind="$attrs">
        <v-card-text v-if="loadingState === 'waiting'"
                     class="mb-2 d-flex flex-row justify-space-between align-center ga-4"
                     style="min-width: 6rem" />
        <v-card-text v-else>
          <div v-if="!message.complete"
               class="mb-4 text-body-sm text-animation"
               :style="{ 'background-image': `url(${gradientTextReveal})` }">
            <span v-if="loadingState === 'thinking'">{{
              $t("thinkingMessage")
            }}</span>
            <span v-if="loadingState === 'sources_done'">{{
              $t("sourcesMessage", { num: getNumberOfSources() })
            }}</span>
            <span v-if="loadingState === 'model_done'">{{
              $t("modelMessage", { model: message.meta_information.llm_model })
            }}</span>
            <span v-if="loadingState === 'model_and_sources_done'">{{
              $t("modelAndSourcesMessage", {
                model: message.meta_information.llm_model,
                num: getNumberOfSources(),
              })
            }}</span>
            <span v-if="(loadingState as LoadingState) === 'waiting'">{{
              $t("processingMessage")
            }}</span>
          </div>
          <span class="d-sr-only">
            {{
              message.sender === "assistant"
                ? $t("messageSenderBot")
                : $t("messageSenderYou")
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
                    {{ $t("thoughtsLabel") }}
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
          :class="{ 'order-first text-end': message.sender === 'user' }">
        <!--
          <v-btn v-if="message.sender === 'assistant'"
          :aria-label="$t('messageActionVoteUp')"
          icon
          variant="text"
          @click="voteMessage('up')">
          <v-icon icon="far fa-thumbs-up" size="small" />
          <v-tooltip activator="parent" :text="$t('messageActionVoteUp')" />
          </v-btn>
          <v-btn v-if="message.sender === 'assistant'"
          :aria-label="$t('messageActionVoteDown')"
          icon
          variant="text"
          @click="voteMessage('down')">
          <v-icon icon="far fa-thumbs-down" size="small" />
          <v-tooltip activator="parent" :text="$t('messageActionVoteDown')" />
          </v-btn>
        -->
        <v-btn v-if="messageInfo"
               :aria-label="messageInfo"
               icon
               variant="text">
          <v-icon icon="fas fa-circle-info" size="small" />
          <v-tooltip activator="parent">
            <span>{{ $t("senderLabel") }}: {{ message.sender }}</span><br>
            <span v-if="message.meta_information.llm_model">{{ $t("LLMLabel") }}: {{ message.meta_information.llm_model
            }}</span>
          </v-tooltip>
        </v-btn>
        <v-btn v-if="isClipboardSupported && !message.meta_information.isInspiration"
               :aria-label="$t('messageActionCopy')"
               icon
               variant="text"
               @click="copyToClipboard(message.message)">
          <v-icon icon="far fa-copy" size="small" />
          <v-tooltip activator="parent"
                     :text="copiedToClipboard
                       ? $t('messageActionCopied')
                       : $t('messageActionCopy')
                     " />
        </v-btn>
        <v-btn v-if="message.sender === 'assistant' && enableRetry"
               :aria-label="$t('messageActionResend')"
               icon
               variant="text"
               @click="resendMessage">
          <v-icon icon="fas fa-arrow-rotate-right" size="small" />
          <v-tooltip activator="parent" :text="$t('messageActionResend')" />
        </v-btn>
        <!--        <v-btn v-if="message.sender === 'user'" -->
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

  <!--  <v-card class="d-inline-block position-relative mt-4 message-parent" -->
  <!--          style="background: rgb(78, 97, 109) !important; color: white !important;" -->
  <!--          :class="{'rounded-bs-0': message.sender === 'assistant' || message.sender === 'system', 'rounded-be-0': message.sender === 'user'}" -->
  <!--          :color="color ? color : message.sender === 'user' ? 'primary' : 'secondary'" -->
  <!--          max-width="75%" -->
  <!--          :variant="variant"> -->
  <!--    <v-card-text v-if="loadingState === 'waiting'" class="mb-2 d-flex flex-row justify-space-between align-center ga-4"> -->
  <!--      <v-progress-linear class="min-w-3rem" indeterminate rounded /> -->
  <!--    </v-card-text> -->
  <!--    <v-card-text v-else> -->
  <!--      <div v-if="!message.complete" -->
  <!--           class="mb-4 text-body-sm text-animation" -->
  <!--           :style="{'background-image': `url(${gradientTextReveal})`}"> -->
  <!--        <span v-if="loadingState === 'thinking'">{{ $t('thinkingMessage') }}</span> -->
  <!--        <span v-if="loadingState === 'sources_done'">{{ $t('sourcesMessage', {sources: getSources()}) }}</span> -->
  <!--        <span v-if="loadingState === 'model_done'">{{ -->
  <!--            $t('modelMessage', {model: message.meta_information.llm_model}) -->
  <!--          }}</span> -->
  <!--        <span v-if="loadingState === 'model_and_sources_done'">{{ -->
  <!--            $t('modelAndSourcesMessage', { -->
  <!--              model: message.meta_information.llm_model, -->
  <!--              sources: getSources() -->
  <!--            }) -->
  <!--          }}</span> -->
  <!--        <span v-if="(loadingState as LoadingState) === 'waiting'">{{ $t('processingMessage') }}</span> -->
  <!--      </div> -->
  <!--      <v-expansion-panels v-if="getThoughts()" class="mb-3"> -->
  <!--        <v-expansion-panel class="rounded-lg border" -->
  <!--                           :class="{'border-white': !theme.current.value.dark, 'border-black': theme.current.value.dark}" -->
  <!--                           elevation="0"> -->
  <!--          <v-expansion-panel-title :class="{'border-white': !theme.current.value.dark, 'border-black': theme.current.value.dark}"> -->
  <!--            <template #default="{expanded}"> -->
  <!--              <div :class="{'border-bottom': expanded}"> -->
  <!--                {{ $t('thoughtsLabel') }} -->
  <!--              </div> -->
  <!--            </template> -->
  <!--          </v-expansion-panel-title> -->
  <!--          <v-expansion-panel-text> -->
  <!--            <VueMarkdown class="text-start chat-message mb-n4 text-body-sm" :source="getThoughts()" /> -->
  <!--          </v-expansion-panel-text> -->
  <!--        </v-expansion-panel> -->
  <!--      </v-expansion-panels> -->
  <!--      <VueMarkdown v-if="message.message && message.message.length > 0" -->
  <!--                   class="text-start chat-message text-body-md" -->
  <!--                   :class="{'mb-n4': message.sender === 'user' && !message.timestamp || !message.complete}" -->
  <!--                   :source="message.message" /> -->
  <!--      <div v-if="messageInfo || enableRetry" -->
  <!--           class="message-actions w-100 d-flex flex-row me-1 mb-1 justify-md-space-between align-center"> -->
  <!--          <span v-if="message.timestamp && message.complete" class="ps-4 ms-1 mt-3 mb-1"> -->
  <!--            {{ new Date(message.timestamp).toLocaleTimeString([], {timeStyle: 'short'}) }} -->
  <!--          </span> -->
  <!--        <span v-else class="ps-4 ms-1 mt-3 mb-1" /> -->
  <!--        <div v-if="message.sender === 'assistant'" class="d-flex flex-row ga-2 me-2 on-hover"> -->
  <!--          <v-btn v-if="messageInfo" -->
  <!--                 :aria-label="messageInfo" -->
  <!--                 class="message-info" -->
  <!--                 density="compact" -->
  <!--                 icon -->
  <!--                 :ripple="false" -->
  <!--                 size="small" -->
  <!--                 :slim="false" -->
  <!--                 variant="text"> -->
  <!--            <v-icon color="surface" icon="fas fa-circle-info" size="x-small" /> -->
  <!--            <v-tooltip activator="parent" location="bottom"> -->
  <!--              <span>{{ $t('senderLabel') }}: {{ message.sender }}</span><br> -->
  <!--              <span v-if="message.meta_information.llm_model">{{ -->
  <!--                  $t('LLMLabel') -->
  <!--                }}: {{ message.meta_information.llm_model }}<br></span> -->
  <!--              <span v-if="message.meta_information.sources">{{ $t('sourcesLabel') }}: {{ getSources() }}</span> -->
  <!--            </v-tooltip> -->
  <!--          </v-btn> -->
  <!--          <v-btn v-if="message.complete" -->
  <!--                 :aria-label="$t('copyTooltip')" -->
  <!--                 density="compact" -->
  <!--                 icon -->
  <!--                 size="small" -->
  <!--                 :slim="false" -->
  <!--                 variant="text" -->
  <!--                 @click="copy(message.message)"> -->
  <!--            <v-icon color="surface" icon="fas fa-copy" size="x-small" /> -->
  <!--            <v-tooltip activator="parent" location="bottom" :text="$t('copyTooltip')" /> -->
  <!--          </v-btn> -->
  <!--          <v-btn v-if="enableRetry" -->
  <!--                 color="secondary" -->
  <!--                 density="compact" -->
  <!--                 icon -->
  <!--                 size="small" -->
  <!--                 variant="text" -->
  <!--                 @click="$emit('retry')"> -->
  <!--            <v-icon color="surface" icon="fas fa-redo" size="x-small" /> -->
  <!--            <v-tooltip activator="parent" location="bottom" :text="$t('retryTooltip')" /> -->
  <!--          </v-btn> -->
  <!--        </div> -->
  <!--      </div> -->
  <!--    </v-card-text> -->

  <!--    <v-card-actions v-if="message.sender!='user' && !isLoading" -->
  <!--                    class="flex-wrap pb-10 pt-0 mt-n4" -->
  <!--                    :class="{'mt-n8': message.buttons.length == 0}"> -->
  <!--      <v-btn v-for="(button, index) in message.buttons" -->
  <!--             :key="index" -->
  <!--             class="text-label-sm" style="background: rgb(145, 172, 191) !important; color: white !important;" -->
  <!--             color="primary" -->
  <!--             :disabled="disabled" -->
  <!--             :slim="false" -->
  <!--             :text="button.label" -->
  <!--             variant="elevated" -->
  <!--             @click="$emit('action', button)" /> -->
  <!--    </v-card-actions> -->
  <!--  </v-card> -->
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

//.message-parent {
//  & .message-actions {
//    position: absolute;
//    opacity: 0.5;
//    right: 0rem;
//    bottom: 0rem;
//    transition: all 0.2s ease;
//
//    .on-hover {
//      opacity: 0.5; // 0;
//      transition: all 0.2s ease;
//    }
//
//    & .message-info {
//      cursor: default;
//    }
//
//    & .unavailable {
//      cursor: not-allowed;
//
//      &:hover {
//        opacity: 0.65;
//      }
//    }
//  }
//
//  &:hover {
//    & .message-actions {
//      opacity: .7;
//    }
//
//    .on-hover {
//      opacity: .85;
//    }
//  }
//}

//.min-w-3rem {
//  min-width: 3rem;
//}
//
//.border-white {
//  border-color: rgba(white, 0.5) !important;
//
//  &:has(.border-bottom) {
//    border-bottom: 1px solid rgba(white, 0.5) !important;
//  }
//}
//
//.border-black {
//  border-color: rgba(black, 0.5) !important;
//
//  &:has(.border-bottom) {
//    border-bottom: 1px solid rgba(black, 0.5) !important;
//  }
//}

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

@keyframes reveal {
  0% {
    background-position: 150% 0%;
  }

  100% {
    background-position: 350% 0%;
  }
}
</style>
