import {ref} from 'vue'
import {defineStore} from 'pinia'
import {useStorage, StorageSerializers} from '@vueuse/core'

export const useOnboardingStore = defineStore('onboarding', () => {
  const onboardingCompleted = useStorage<boolean>('onboardingCompleted', false, undefined, {serializer: StorageSerializers.boolean})

  const showOnboarding = ref(false)

  type Onboarding = {
    element: string;
    textCode: string;
    position?: { mobile: string, desktop?: string };
  }

  const onboardingSteps: Onboarding[] = [
    {element: '', textCode: 'onboardingIntro'},
    {element: '#settings', textCode: 'onboardingSettings'},
    {element: '#topics', textCode: 'onboardingSimpleTopics', position: {mobile: 'end'}},
    {element: '#topic-card', textCode: 'onboardingTopic'},
    {element: '#chat', textCode: 'onboardingChat', position: {mobile: 'center', desktop: 'center'}},
    {element: '#feedback', textCode: 'onboardingFeedback'},
    {element: '#survey', textCode: 'onboardingEvaluation', position: {mobile: 'start', desktop: 'start'}},
    {element: '#other-chatbots', textCode: 'onboardingOtherChatbots', position: {mobile: 'start', desktop: 'start'}},
    {element: '', textCode: 'onboardingAIDisclaimer'},
    {element: '', textCode: 'onboardingOutro'}
  ]

  const setOnboardingCompleted = (completed: boolean) => {
    onboardingCompleted.value = completed
  }

  return {
    showOnboarding,
    onboardingSteps,
    onboardingCompleted,
    setOnboardingCompleted
  }
})
