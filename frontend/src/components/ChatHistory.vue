<script setup lang="ts">
  import {useChatStore} from '@/stores/chat'
  import ChatBubble from './ChatBubble.vue'
  import {useI18n} from 'vue-i18n'
  import {useRoute} from 'vue-router'
  import { watchEffect, nextTick } from 'vue'

  const chatStore = useChatStore()
  const {locale, t} = useI18n()
  const route = useRoute()

  function isFirstOfTheDay(index: number) {
    if (!chatStore.currentChat || !route.params.skillId) return false
    if (index === 0) return true
    const previousMessage = chatStore.currentChat.messages[index - 1]
    if (!previousMessage || !previousMessage.timestamp) return false
    const previousDate = new Date(previousMessage.timestamp)
    const currentMessage = chatStore.currentChat.messages[index]
    if (!currentMessage || !currentMessage.timestamp) return false
    const currentDate = new Date(currentMessage.timestamp)
    return previousDate.toDateString() !== currentDate.toDateString()
  }

  function formatDate(date: string) {
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(today.getDate() - 1)
    const yesterdayString = yesterday.toISOString().split('T')[0]
    const todayString = today.toISOString().split('T')[0]
    if (date.split('T')[0] === yesterdayString) return t('yesterday')
    if (date.split('T')[0] === todayString) return t('today')
    return new Date(date).toLocaleDateString(locale.value, {day: '2-digit', month: '2-digit', year: 'numeric'})
  }

  function retryMessage(index: number) {
    if (!chatStore.currentChat) return
    const lastUserMessage = chatStore.currentChat.messages.slice(0, index + 1).reverse().find(msg => msg.sender === 'user')
    if (lastUserMessage) {
      const index = chatStore.currentChat.messages.findIndex(msg => msg.timestamp === lastUserMessage.timestamp)
      if (index >= 0) {
        const resendMessage = chatStore.currentChat.messages[index].message
        chatStore.currentChat.messages = chatStore.currentChat.messages.slice(0, index)
        chatStore.sendUserMessage(resendMessage)
      }
    }
  }

  watchEffect(async () => {
    // when chat messages are added scroll to bottom
    if (!chatStore.currentChat?.messages.length) return
    await nextTick().then(scrollToBottom)
  })
  
  watchEffect(async () => {
    if (!chatStore.currentChat?.messages[chatStore.currentChat.messages.length - 1] || !chatStore.currentChat?.messages[chatStore.currentChat.messages.length - 1].message) return
    await nextTick().then(scrollToBottom)
  })
  
  function scrollToBottom() {
    const scrollContainer = document.getElementsByClassName('v-main__scroller')[0]
    scrollContainer?.scrollTo({top: scrollContainer.scrollHeight, behavior: 'smooth'})
  }
</script>

<template>
  <section :aria-label="$t('chatHistoryLabel')" aria-live="polite">
    <div v-for="(message, index) in chatStore.currentChat?.messages"
         :key="index">
      <div v-if="isFirstOfTheDay(index)" class="my-2">
        <v-divider v-if="index !== 0" />
        <div class="d-flex justify-center">
          <span class="text-body-sm text-secondary">{{ formatDate(message.timestamp) }}</span>
        </div>
      </div>
      <ChatBubble class="mt-3"
                  :disabled="index !== (chatStore.currentChat?.messages.length ?? 1) - 1 "
                  :message="message"
                  @retry="retryMessage(index)" />
    </div>
  </section>
</template>

<style lang="scss" scoped>

</style>
