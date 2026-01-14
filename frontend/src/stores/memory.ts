import {ref} from 'vue'
import {defineStore} from 'pinia'
import type { ChatMessageMessage } from '@/types'
import type { useChatStore } from '@/stores/chat'

export const useMemoryStore = defineStore('memory', () => {
  const potentialMemory = ref<Map<string, string>>(new Map())
  const hasPotentialMemory = (messageId: string) => potentialMemory.value.has(messageId)

  function acceptPotentialMemory(message: ChatMessageMessage, chatStore: ReturnType<typeof useChatStore>) {
    if (!chatStore.currentChat || potentialMemory.value.size === 0 || !potentialMemory.value.has(message.timestamp)) {
      return
    }

    chatStore.currentChat.storage['user_memory'] = potentialMemory.value.get(message.timestamp) as string
    message.meta_information['user_memory'] = potentialMemory.value.get(message.timestamp) as string
    potentialMemory.value.delete(message.timestamp)
  }

  function rejectPotentialMemory(messageId: string) {
    potentialMemory.value.delete(messageId)
  }

  function addPotentialMemory(messageId: string, memory: string) {
    potentialMemory.value.set(messageId, memory)
  }

  function getPotentialMemory(messageId: string): string | undefined {
    return potentialMemory.value.get(messageId)
  }

  return {
    potentialMemory,
    hasPotentialMemory,
    addPotentialMemory,
    getPotentialMemory,
    acceptPotentialMemory,
    rejectPotentialMemory
  }
})
