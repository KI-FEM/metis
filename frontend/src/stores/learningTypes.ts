import {ref, computed} from 'vue'
import {defineStore} from 'pinia'
import createClient from 'openapi-fetch'
import {useStorage, StorageSerializers} from '@vueuse/core'

import type {paths} from '@/types_api'
import type {LearningType} from '@/types'

export const useLearningTypesStore = defineStore('learningTypes', () => {
  const client = createClient<paths>({baseUrl: import.meta.env.VITE_API_URL})

  const learningTypes = ref<LearningType[]>([])
  const isFetching = ref(false)
  const isError = ref(false)
  const selectedLearningTypeId = useStorage<LearningType['id']>('learningType', null, undefined, {serializer: StorageSerializers.string})

  const selectedLearningType = computed(() => learningTypes.value.find(lt => lt.id === selectedLearningTypeId.value))

  async function fetchLearningTypes() {
    try {
      if (isError.value) {
        isError.value = false
        isFetching.value = true
        await new Promise(resolve => setTimeout(resolve, 1000)) // add fake loading if user requests reload
      }
      isError.value = false
      isFetching.value = true
      const {
        data,
        error
      } = await client.GET('/learning_types', {signal: AbortSignal.timeout(import.meta.env.VITE_API_TIMEOUT)}) // TODO: API: change to /learning-types
      if (error) throw error
      learningTypes.value = data.learning_types // TODO: API: remove .learning_types
    } catch (error) {
      isError.value = true
    } finally {
      isFetching.value = false
    }
  }

  async function convertPersonalityType(personalityType: paths['/learning_types/from_personality/{personality_type}']['get']['parameters']['path']['personality_type']) {
    selectedLearningTypeId.value = null
    const {data, error} = await client.GET('/learning_types/from_personality/{personality_type}', { // TODO: API: change to /learning-types/{personality}
      signal: AbortSignal.timeout(import.meta.env.VITE_API_TIMEOUT),
      params: {path: {personality_type: personalityType}}
    })
    if (error) throw error
    selectedLearningTypeId.value = data.learning_type // TODO: API: change to data.id
    return data.learning_type
  }

  return {
    learningTypes,
    selectedLearningTypeId,
    selectedLearningType,
    isFetching,
    isError,
    fetchLearningTypes,
    convertPersonalityType
  }
})
