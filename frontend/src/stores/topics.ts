import {ref, computed} from 'vue'
import {defineStore} from 'pinia'
import createClient from 'openapi-fetch'
import {useStorage} from '@vueuse/core'
import {useRoute} from 'vue-router'

import type {paths, components} from '@/types_api'

type Topic = components['schemas']['TopicModel']

interface SkillStorage {
  topics: {
    endpoint: Topic['endpoint'];
    modules: {
      moduleId: string;
      selectedLevelId: string;
      customLearningObjectives: {
        levelId: string;
        text: string;
        locale: string;
      }[];
    }[];
  }[];
}

export const useTopicsStore = defineStore('topics', () => {
  const client = createClient<paths>({baseUrl: import.meta.env.VITE_API_URL})

  const topics = ref<Topic[]>([])
  const isFetching = ref(false)
  const isError = ref(false)
  const skillStorage = useStorage<SkillStorage>('skills', {topics: []}) // old storage used "topic" instead of "topics"

  // update Local Storage
  if (localStorage.getItem('version') == null) {
    skillStorage.value = {topics: []} // reset storage if version changed
    localStorage.setItem('version', import.meta.env.VITE_APP_VERSION) // set the new version in localStorage
  }
  
  const versionStorage = useStorage<string>('version', import.meta.env.VITE_APP_VERSION, undefined)
  const route = useRoute()

  const version = computed(() => versionStorage.value)
  const selectedTopic = computed(() => topics.value.find(topic => topic.endpoint === route.params.endpoint))
  const storedModuleLevelData = computed(() => (moduleId?: string) => skillStorage.value.topics.find(topic => topic.endpoint === selectedTopic.value?.endpoint)?.modules.find(module => module.moduleId === moduleId))
  const storedModuleLevelId = computed(() => (moduleId?: string) => storedModuleLevelData.value(moduleId)?.selectedLevelId)
  const storedModuleLevelObjective = computed(() => (moduleId?: string, levelId?: string) => storedModuleLevelData.value(moduleId)?.customLearningObjectives.find(objective => objective.levelId === levelId))

  async function fetchTopics() {
    try {
      isError.value = false
      isFetching.value = true
      const {data, error} = await client.GET('/topics', {signal: AbortSignal.timeout(import.meta.env.VITE_API_TIMEOUT)})
      if (error) throw error
      topics.value = data.topics.sort((a, b) => b.priority - a.priority) // TODO: API: remove .topics
    } catch (error) {
      isError.value = true
    } finally {
      isFetching.value = false
    }
  }

  function storeModuleLevel(moduleId: string, levelId: string) {
    if (!selectedTopic.value)
      return
    let storedTopic = skillStorage.value.topics.find(topic => topic.endpoint === selectedTopic.value?.endpoint)
    if (!storedTopic) {
      storedTopic = {endpoint: selectedTopic.value.endpoint, modules: []}
      skillStorage.value.topics.push(storedTopic)
    }
    let storedModule = storedTopic.modules.find(module => module.moduleId === moduleId)
    if (!storedModule) {
      storedModule = {moduleId: moduleId, selectedLevelId: levelId, customLearningObjectives: []}
      storedTopic.modules.push(storedModule)
    } else storedModule.selectedLevelId = levelId
  }

  function storeCustomLearningObjective(moduleId: string, levelId: string, objectiveText: string, locale: string) {
    const storedTopic = skillStorage.value.topics.find(topic => topic.endpoint === selectedTopic.value?.endpoint)
    const storedModule = storedTopic?.modules.find(module => module.moduleId === moduleId)
    const storedObjective = storedModule?.customLearningObjectives?.find(objective => objective.levelId === levelId)
    if (!storedObjective) {
      storedModule?.customLearningObjectives.push({
        levelId: levelId,
        text: objectiveText,
        locale: locale
      })
    } else {
      storedObjective.text = objectiveText
      storedObjective.locale = locale
    }
  }

  return {
    topics,
    selectedTopic,
    storedModuleLevelId,
    storedModuleLevelObjective,
    isFetching,
    isError,
    version,
    fetchTopics,
    storeModuleLevel,
    storeCustomLearningObjective
  }
})
