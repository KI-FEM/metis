import {computed} from 'vue'
import {defineStore} from 'pinia'
import {useStorage, StorageSerializers} from '@vueuse/core'

export type storageKeyString =
  'topicSelection'
  | 'topicAddition'
  | 'settings'
  | 'moduleSelection'
  | 'levelSelection'
  | 'startChat'
  | 'chatActions'
  | 'switchModuleLevel'
  | 'switchChats'
  | 'dashboard'

export const useOnboardingStore = defineStore('onboarding', () => {
  const onboardingStorage = useStorage<Set<storageKeyString>>('onboarding', new Set(), undefined, {serializer: StorageSerializers.set})

  const isRead = computed(() => (key: storageKeyString) => onboardingStorage.value.has(key))

  function markAsRead(key: storageKeyString) {
    onboardingStorage.value.add(key)
  }

  function reset() {
    onboardingStorage.value.clear()
  }

  return {
    isRead,
    markAsRead,
    reset
  }
})
