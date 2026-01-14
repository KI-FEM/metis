<script setup lang="ts">
  import {nextTick, onMounted, watch} from 'vue'
  import {useI18n} from 'vue-i18n'

  import {useChatStore} from '@/stores/chat.ts'

  import ChatBubble from '@/components/ChatBubble.vue'

  const emit = defineEmits<{ 'sendInspo': [value: string] }>()
  const chatStore = useChatStore()
  const {t} = useI18n()

  const showInspiration = defineModel<boolean>()

  onMounted(async () => {
    if (showInspiration.value) {
      chatStore.requestInspiration()
      await nextTick().then(scrollToBottom)
    }
  })

  watch(() => showInspiration.value, async (newVal) => {
    if (newVal) {
      chatStore.requestInspiration()
      await nextTick().then(scrollToBottom)
    }
  })

  function scrollToBottom() {
    const scrollContainer = document.getElementsByClassName('v-main__scroller')[0]
    scrollContainer?.scrollTo({top: scrollContainer.scrollHeight, behavior: 'smooth'})
  }

  function selectInspiration(message: string) {
    showInspiration.value = false
    if (message === t('inspirationInitiative') && chatStore.currentChat) {
      chatStore.setChatStorage({initiative: 'bot'}) // user gives initiative to bot
      chatStore.sendUserMessage(message)
      if (chatStore.currentChat?.storage && 'initiative' in chatStore.currentChat.storage) {
        const {...rest} = chatStore.currentChat.storage
        chatStore.currentChat.storage = rest
      }
    } else {
      emit('sendInspo', message)
    }
  }
</script>

<template>
  <v-divider v-if="showInspiration" class="mt-6 mb-3" />
  <section v-if="showInspiration" :aria-label="$t('inspiration')">
    <div class="d-flex justify-end align-center ga-1">
      <h3>{{ $t('inspiration') }}</h3>
      <v-btn :aria-label="$t('inspirationReload')"
             :disabled="chatStore.isLoadingInspiration"
             icon
             variant="text"
             @click="chatStore.requestInspiration">
        <v-icon icon="fas fa-arrow-rotate-right" size="small" />
        <v-tooltip activator="parent" :text="$t('inspirationReload')" />
      </v-btn>
      <v-btn :aria-label="$t('inspirationClose')"
             icon
             variant="text"
             @click="showInspiration = false">
        <v-icon icon="fas fa-close" size="small" />
        <v-tooltip activator="parent" :text="$t('inspirationClose')" />
      </v-btn>
    </div>
    <div class="w-75 ms-auto text-end">
      {{ $t('inspirationIntro') }}
    </div>
    <div v-if="chatStore.isLoadingInspiration" class="ms-auto text-end">
      <div class="w-75 ms-auto text-end text-body-2 text-medium-emphasis mb-3">
        {{ $t('inspirationLoadingDisclaimer') }}
      </div>
      <v-skeleton-loader class="ms-auto"
                         loading
                         max-width="50%"
                         type="heading@3" />
    </div>
    <ChatBubble v-for="(inspiration, index) in chatStore.randomInspirations"
                v-else
                :key="index"
                class="mt-3"
                :message="{
                  content: inspiration,
                  fragment: false,
                  type: 'user',
                  buttons: [],
                  complete: true,
                  timestamp: '',
                  meta_information: {
                    sources: {},
                    citations: [],
                    llm_model: '',
                    isInspiration: true
                  }
                }"
                @click="selectInspiration(inspiration)" />
  </section>
</template>

<style scoped lang="scss">
  :deep(.v-skeleton-loader__bone) {
    height: 3rem;
    border-radius: 20px;
    margin: 12px 0 0 !important;
  }
</style>
