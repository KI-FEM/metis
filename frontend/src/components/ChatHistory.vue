<script setup lang="ts">
  import {useChatStore} from '@/stores/chat'
  import ChatBubble from './ChatBubble.vue'
  import {useI18n} from 'vue-i18n'
  import {useRoute} from 'vue-router'
  import {watchEffect, nextTick, ref, onMounted, onUnmounted} from 'vue'
  import QuizFragment from '@/components/quiz/QuizFragment.vue'

  const chatStore = useChatStore()
  const {locale, t} = useI18n()
  const route = useRoute()
  const isAtBottom = ref(true)

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
    chatStore.resendMessage(index)
  }

  function bookmark(index: number) {
    if (!chatStore.currentChat) return
    const bookmarks = new Set(chatStore.bookmarksStorage[chatStore.currentChat.id] ?? [])
    bookmarks.add(index)
    chatStore.bookmarksStorage[chatStore.currentChat.id] = Array.from(bookmarks)
  }

  // Accomplish scroll behavior
  // only scroll to bottom if user is already at bottom
  // do not automatically scroll if the user is reading previous messages

  function checkIfAtBottom() {
    const scrollContainer = document.getElementsByClassName('v-main__scroller')[0]
    if (!scrollContainer) return true
    const threshold = 50 // pixels from bottom to consider "at bottom"
    const isNearBottom = scrollContainer.scrollHeight - scrollContainer.scrollTop - scrollContainer.clientHeight < threshold
    isAtBottom.value = isNearBottom
  }

  function handleScroll() {
    checkIfAtBottom()
  }

  onMounted(() => {
    const scrollContainer = document.getElementsByClassName('v-main__scroller')[0]
    scrollContainer?.addEventListener('scroll', handleScroll)
  })

  onUnmounted(() => {
    const scrollContainer = document.getElementsByClassName('v-main__scroller')[0]
    scrollContainer?.removeEventListener('scroll', handleScroll)
  })

  watchEffect(async () => {
    // when chat messages are added scroll to bottom
    if (!chatStore.currentChat?.messages.length) return
    if (!isAtBottom.value) return // Only scroll if user is at bottom
    await nextTick().then(scrollToBottom)
  })

  watchEffect(async () => {
    if (!chatStore.currentChat?.messages[chatStore.currentChat?.messages.length - 1]?.content) return
    if (!isAtBottom.value) return // Only scroll if user is at bottom
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
      <QuizFragment v-if="message.fragment" :id="message.quizId" />
      <ChatBubble v-else
                  class="mt-3"
                  :disabled="index !== (chatStore.currentChat?.messages.length ?? 1) - 1 "
                  :message="message"
                  @bookmark="bookmark(index)"
                  @retry="retryMessage(index)" />
    </div>
  </section>
</template>

<style lang="scss" scoped>

</style>
