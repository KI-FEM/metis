import {ref, computed} from 'vue'
import {defineStore} from 'pinia'
import {useRouter, useRoute} from 'vue-router'
import {useI18n} from 'vue-i18n'
import {StorageSerializers, useStorage} from '@vueuse/core'

import type {Chat, ChatMessage, ActionButton, Topic, Locale, ChatCompletionsChunk} from '@/types'

import {useLearningTypesStore} from '@/stores/learningTypes'
import {useTopicsStore} from '@/stores/topics'
import createClient from 'openapi-fetch'
import type {components, paths} from '@/types_api'


export const useChatStore = defineStore('chat', () => {
  const client = createClient<paths>({baseUrl: import.meta.env.VITE_API_URL})
  const router = useRouter()
  const route = useRoute()
  const {locale, t} = useI18n()

  const learningTypesStore = useLearningTypesStore()
  const topicsStore = useTopicsStore()

  const chatStorage = useStorage<Record<Topic['endpoint'], Chat[]>>('chats', {} as Record<Topic['endpoint'], Chat[]>, undefined, {serializer: StorageSerializers.object})

  const inspirations = ref<Record<Topic['endpoint'], string[]>>({} as Record<Topic['endpoint'], string[]>)
  const isLoading = ref(false)
  const isLoadingInspiration = ref(false)
  const isError = ref(false)
  const streaming = useStorage<boolean>('streaming', true)

  const chunkQueue = ref<ChatCompletionsChunk[]>([])
  const messageComplete = ref(false)
  const queueProcessor = ref<Promise<void> | null>(null)

  const isLoadingSummarization = ref(false)
  const summarizationTimeout = ref<number | null>(null)
  const summarizationDelay = 5000 // 5 seconds of idle time before summarizing

  const availableAIPurposes = ref<components['schemas']['PurposeModel'][]>([])
  const maxMessagesBeforeSummarization = ref(16)

  const processingQueue = ref(false)

  const allChats = computed(() => chatStorage.value)
  const topicChats = computed(() => chatStorage.value[route.params.endpoint as Topic['endpoint']] || [])

  const currentChat = computed(() => {
    if (!topicsStore.selectedTopic?.endpoint)
      return null
    return chatStorage.value[topicsStore.selectedTopic.endpoint]?.find(chat => chat.id === route.params.chatId) || null
    //
    // if (!route.params.endpoint)
    //   return null
    // if (!chatStorage.value[route.params.endpoint as Topic['endpoint']]) {
    //   return null
    // }
    // const botType = topicsStore.topics?.find(topic => topic.endpoint === route.params.endpoint)?.type
    // if (botType == 'skills') {
    //   //TODO does it always save skill as storage?
    //   return chatStorage.value[route.params.endpoint as Topic['endpoint']].find(chat => chat.storage['selected_module'] === route.params.skillId) || null
    // }
    // if (!route.params.skillId) {
    //   return chatStorage.value[route.params.endpoint as Topic['endpoint']].find(chat => chat.id === 'default') || null
    // }
    // return chatStorage.value[route.params.endpoint as Chat['topic']['endpoint']].find(chat => chat.id === route.params.skillId)
  })

  function importChats(chatBackup: Record<Topic['endpoint'], Chat[]>) {
    for (const topicEndpoint in chatBackup) {
      const topicChats = chatBackup[topicEndpoint as Topic['endpoint']]
      // if the topic doesn't exist, add it
      if (!chatStorage.value[topicEndpoint as Topic['endpoint']]) {
        chatStorage.value[topicEndpoint as Topic['endpoint']] = topicChats
        continue
      }
      // merge (add or overwrite) each chat from the backup
      for (const topicChat of topicChats) {
        const index = chatStorage.value[topicEndpoint as Topic['endpoint']].findIndex(chat => chat.id === topicChat.id)
        if (index === -1)
          chatStorage.value[topicEndpoint as Topic['endpoint']].push(topicChat)
        else chatStorage.value[topicEndpoint as Topic['endpoint']][index] = topicChat
      }
    }
  }

  const getSelectedLLMPurpose: () => components['schemas']['PurposeModel']['id'] | null = () => {
    if (!currentChat.value) {
      //console.log('No current chat')
      return null
    }
    if (Object.keys(currentChat.value.storage).includes('llm_purpose')) {
      return currentChat.value.storage['llm_purpose'] as components['schemas']['PurposeModel']['id']
    }
    return null
  }

  const randomInspirations = computed(() => {
    if (!topicsStore.selectedTopic?.endpoint) {
      return []
    }
    if (!inspirations.value[topicsStore.selectedTopic.endpoint]) {
      return []
    }
    let shuffledInspirations = inspirations.value[topicsStore.selectedTopic.endpoint].sort(() => 0.5 - Math.random())

    if (topicsStore.selectedTopic.features.includes('initiative')) {
      shuffledInspirations = shuffledInspirations.slice(0, 2)
      shuffledInspirations.push(t('inspirationInitiative'))
    } else {
      shuffledInspirations = shuffledInspirations.slice(0, 3)
    }
    return shuffledInspirations
  })

  function getLastChatId(endpoint: Topic['endpoint']) {
    if (chatStorage.value[endpoint]?.length)
      return chatStorage.value[endpoint][0].id
  }

  async function createChat() {
    if (!topicsStore.selectedTopic)
      throw new Error('No topic selected')
    const moduleId = topicsStore.selectedTopic?.modules.find(module => module.id === route.params.chatId)?.id
    if (topicsStore.selectedTopic?.type == 'skills' && topicsStore.selectedTopic?.modules.length && !moduleId)
      throw new Error('No module with matching ID')
    const chatId = moduleId || Date.now().toString()
    const uuid = crypto.randomUUID()
    //console.log('chatId')
    if (!chatStorage.value[topicsStore.selectedTopic.endpoint])
      chatStorage.value[topicsStore.selectedTopic.endpoint] = []
    const newStorage: Record<string, string> = {
      chat_id: chatId,
      unique_id: uuid // unique identifier for the chat in case chatId is not unique (module name)
    }
    // Set llm_purpose to the first available purpose if available
    newStorage['llm_purpose'] = availableAIPurposes.value.length > 0 ? availableAIPurposes.value[0].id : 'optimal'

    if (moduleId)
      newStorage['selected_module'] = moduleId
    const levelId = topicsStore.storedModuleLevelId(moduleId)
    if (levelId)
      newStorage['skill_level'] = levelId
    const customLearningGoal = topicsStore.storedModuleLevelObjective(moduleId, levelId)
    if (customLearningGoal)
      newStorage['custom_learning_goals'] = customLearningGoal.text

    chatStorage.value[topicsStore.selectedTopic.endpoint].unshift({
      id: chatId,
      title: '',
      language: locale.value as Locale,
      messages: [],
      storage: newStorage,
      topic: topicsStore.selectedTopic
    })
    await router.replace({params: {chatId: chatId}})


    // if (!topicsStore.selectedTopic)
    //   throw new Error('No topic selected')
    // if (!currentChat.value) {
    //   const chatId = defaultChatId ?? 'default'
    //   const storage: Record<string, string> = {}
    //   if (currentSkill.value) {
    //     storage['chat_id'] = Date.now().toString()
    //     storage['selected_module'] = currentSkill.value.id
    //   }
    //
    //   if (!Object.keys(chats.value).includes(topicsStore.selectedTopic.endpoint) && topicsStore.topics) {
    //     topicsStore.topics.forEach(topic => {
    //       if (!chats.value[topic.endpoint])
    //         chats.value[topic.endpoint] = []
    //     })
    //   }
    //   chats.value[topicsStore.selectedTopic.endpoint].push({
    //     id: chatId,
    //     title: getInitialChatTitle(topicsStore.selectedTopic.title[locale.value as keyof Topic['title']]),
    //     language: locale.value as Locale,
    //     topic: topicsStore.selectedTopic,
    //     messages: [],
    //     storage: storage
    //   })
    //   //if(route.params.skillId != chatId && (!currentSkill.value || route.params.skillId != currentSkill.value.id))
    //   //  await router.replace({params: {skillId: chatId}})
    // }
    // inspirations.value[topicsStore.selectedTopic.endpoint] = []
    isError.value = false
    if (!currentChat.value || currentChat.value.messages.length)
      return

    isLoading.value = true
    try {
      const {data, error: fetchError} = await client.POST('/topic/{topic}', {
        params: {
          path: {
            topic: topicsStore.selectedTopic?.endpoint
          }
        },
        body: {
          learning_type_id: "FEELING",
          language: locale.value,
          chat_history: currentChat.value.messages.map(message => {
            return {
              'message': message.message,
              'sender': message.sender
            }
          }),
          storage: currentChat.value?.storage,
          llm_purpose: getSelectedLLMPurpose(),
          streaming: false
        }
      })
      if (fetchError)
        console.error('Error during API call: ', fetchError)
      if (!data)
        throw new Error('No data received from API')
      const chatMessages = data.messages
      const storage = data.storage
      //const instructions = data.instructions // TODO handle instructions
      currentChat.value.messages.push(...chatMessages.map(message => ({
        ...message,
        complete: true,
        timestamp: new Date().toISOString()
      })))
      currentChat.value.storage = {...currentChat.value.storage, ...storage}
    } catch (e) {
      isError.value = true
      console.error('Error during API call: ', e)
    } finally {
      isLoading.value = false
    }
  }

  function deleteCurrentChat(endpoint: Topic['endpoint'], chatId: Chat['id']) {
    chatStorage.value[endpoint] = chatStorage.value[endpoint].filter(chat => chat.id !== chatId)
  }

  function deleteModuleChats(endpoint: Topic['endpoint']) {
    chatStorage.value[endpoint] = []
  }

  function getDefaultChatTitle(): string {
    return t('newChatLabel')
    //console.log('get initial chat title')
    // return t('initialChatTitle').replace('insertTopic', topicsStore.selectedTopic?.title)
  }

  async function fetchModels() {
    const {data, error: fetchError} = await client.GET('/models')
    if (fetchError || !data) {
      isError.value = fetchError
      return null
    }
    maxMessagesBeforeSummarization.value = data.config.max_messages_before_summarization
    availableAIPurposes.value = data.purposes
    return availableAIPurposes.value
  }

  // let retryDelay = 1000
  //
  // async function updateStores() {
  //   const fetchWithRetry = async (fetchFunction: () => Promise<unknown>) => {
  //     const result = await fetchFunction()
  //     if (!result) {
  //       await new Promise(resolve => setTimeout(resolve, retryDelay))
  //       retryDelay = Math.min(retryDelay * 2, 16000)
  //       await fetchWithRetry(fetchFunction)
  //     }
  //   }
  //   if (!topics.value) {
  //     await fetchWithRetry(fetchTopics)
  //   }
  //   if (!availableModels.value || availableModels.value.length == 0) {
  //     await fetchWithRetry(fetchModels)
  //   }
  // }

  // function createTempChat() {
  //   console.log('create chat')
  //   if (!topicsStore.selectedTopic) {
  //     console.error('[chat.createChat] No topic selected')
  //     return
  //   }
  //   const chatId = Date.now().toString()
  //   const chatCopied = JSON.parse(JSON.stringify(chatStorage.value[topicsStore.selectedTopic.endpoint].find(chat => chat.id === 'default')))
  //   if (!chatCopied) {
  //     console.error('[chat.createChat] Couldn\'t find chat to copy...')
  //     return
  //   }
  //   chatCopied.id = chatId
  //   chatCopied.storage = {...chatCopied.storage, 'chat_id': chatId}
  //   chatCopied.messages.map((message: ChatMessage) => {
  //     message.timestamp = new Date().toISOString()
  //     return message
  //   })
  //   chatStorage.value[topicsStore.selectedTopic.endpoint].push(chatCopied)
  //   return chatCopied
  // }

  async function startQueueProcessor() {
    //console.log('start queue processor')
    if (queueProcessor.value) return

    queueProcessor.value = (async () => {
      while (true) {
        if (chunkQueue.value.length > 0) {
          processingQueue.value = true
          const chunk = chunkQueue.value.shift()
          if (chunk) {
            const finished = readChunk(chunk)
            if (finished) {
              messageComplete.value = true
              await checkAndGenerateTitle()
            } else {
              // Add a smaller delay if message is complete, regular delay otherwise
              await new Promise(resolve => setTimeout(resolve, messageComplete.value ? 15 : 50))
            }
          }
        } else {
          processingQueue.value = false
          // Small delay when queue is empty to prevent busy waiting
          await new Promise(resolve => setTimeout(resolve, 10))
          // If queue has been empty for a while and message is complete, stop processor
          if (messageComplete.value && chunkQueue.value.length === 0) {
            queueProcessor.value = null
            break
          }
        }
      }
    })()
  }

  function readChunk(chunk: ChatCompletionsChunk) {
    if (chunk.choices.length > 0 && currentChat.value) {
      const assistantMessages = currentChat.value.messages.filter(message => message.sender === 'assistant')
      const lastMessage = assistantMessages[assistantMessages.length - 1]

      const choice = chunk.choices[0]
      const delta = choice.delta
      lastMessage.timestamp = chunk.created
      if (delta.sender) {
        lastMessage.sender = delta.sender as components['schemas']['Sender']
      }
      if (delta.buttons) {
        lastMessage.buttons.push(...delta.buttons)
      }
      if (delta.storage) {
        currentChat.value.storage = {...currentChat.value.storage, ...delta.storage}
      }
      if (delta.llm_model) {
        lastMessage.meta_information.llm_model = delta.llm_model
      }
      if (delta.citations) {
        lastMessage.meta_information.citations = delta.citations
      }
      if (delta.instructions) {
        for (const instruction of delta.instructions) {
          if (instruction.includes('discard')) {
            lastMessage.message = ''
          }
          if (instruction.includes('summary: ')) {
            const summary = JSON.parse(instruction.split('summary: ')[1] || '')
            const num_messages = summary.max_messages
            const summary_message = summary.summary
            currentChat.value.messages[currentChat.value.messages.length - num_messages - 1].summary = summary_message
          }
        }
      }
      if (delta.sources) {
        if (!lastMessage.meta_information) {
          lastMessage.meta_information = {} as ChatMessage['meta_information']
        }
        if (lastMessage.meta_information.sources === undefined)
          lastMessage.meta_information.sources = {...delta.sources}
        else
          lastMessage.meta_information.sources = {...lastMessage.meta_information.sources, ...delta.sources}
      }
      if (delta.thoughts) {
        lastMessage.thoughts = lastMessage.thoughts ? lastMessage.thoughts + delta.thoughts : delta.thoughts
      }
      if (choice.finish_reason == 'stop') {
        lastMessage.complete = true
        lastMessage.message = delta.content || lastMessage.message
        return true
      }
      if (delta.content) {
        lastMessage.message += delta.content
      }
    }
    return false
  }

  async function sendUserMessage(message: string) {
    //console.log('send user message', message)
    isLoading.value = true
    isError.value = false
    if (!currentChat.value || !topicsStore.selectedTopic) {
      console.error('[chat.sendUserMessage] Couldn\'t send message. No chat/topic found...')
      return
    }
    // if (currentChat.value.id == 'default') {
    //   const tempChat = createTempChat()
    //   if (!tempChat) {
    //     console.error('[chat.sendUserMessage] Couldn\'t create new chat...')
    //     return
    //   }
    //   await router.push({name: 'chat', params: {endpoint: topicsStore.selectedTopic.endpoint, skillId: tempChat.id}})
    // }
    currentChat.value.messages.push({
      sender: 'user',
      message: message,
      buttons: [],
      meta_information: {} as ChatMessage['meta_information'],
      complete: true,
      timestamp: new Date().toISOString()
    })
    try {
      // erstelle leere Nachricht des Bots
      currentChat.value.messages.push({
        sender: 'assistant',
        message: '',
        buttons: [],
        meta_information: {} as ChatMessage['meta_information'],
        complete: false,
        timestamp: new Date().toISOString()
      })
      messageComplete.value = false // streaming
      chunkQueue.value = []
      queueProcessor.value = null
      if (streaming.value && topicsStore.selectedTopic.features.includes('streaming')) {
        const response = await fetch(`${import.meta.env.VITE_API_URL}/topic/${topicsStore.selectedTopic.endpoint}/message`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            learning_type_id: "FEELING",
            language: locale.value,
            chat_history: currentChat.value.messages.map(m => {
              if (m.summary) {
                return {
                  'message': m.message,
                  'sender': 'assistant',
                  'summary': m.summary
                } as components['schemas']['Summary']
              }
              // pydantic
              return {
                'message': m.message,
                'sender': m.sender
              }
            }),
            storage: currentChat.value?.storage,
            llm_purpose: getSelectedLLMPurpose(),
            streaming: true
          })
        })

        const reader = response.body?.getReader()
        const decoder = new TextDecoder()

        if (!reader) throw new Error('No reader available')

        while (!messageComplete.value) {
          const {done, value} = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const events = chunk.split('\n\n').filter(e => e.trim())
          events.forEach(event => {
            const content = event.replace('data: ', '')
            const data = JSON.parse(content)
            const chunk = data as ChatCompletionsChunk
            if (chunk.choices.length > 0 && chunk.choices[0].finish_reason === 'stop') {
              messageComplete.value = true
            }
            chunkQueue.value.push(chunk)
          })
          if (!queueProcessor.value) {
            startQueueProcessor()
          }
        }
      } else {
        // non streaming
        const {data, error: fetchError} = await client.POST('/topic/{topic}/message', {
          params: {
            path: {
              topic: topicsStore.selectedTopic.endpoint
            }
          },
          body: {
            learning_type_id: "FEELING",
            language: locale.value,
            chat_history: currentChat.value.messages.map(m => {
              if (m.summary) {
                return {
                  'message': m.message,
                  'sender': 'assistant',
                  'summary': m.summary
                } as components['schemas']['Summary']
              }
              return {
                'message': m.message,
                'sender': m.sender
              }
            }),
            storage: currentChat.value?.storage,
            llm_purpose: getSelectedLLMPurpose(),
            streaming: false
          }
        })
        if (fetchError) {
          throw fetchError
        }
        if (!data) {
          throw new Error('No data received from API.')
        }
        const chatMessages = data.messages
        const storage = data.storage
        const instructions = data.instructions
        if (instructions) {
          for (const instruction of instructions) {
            if (instruction.includes('summary: ')) {
              const summary = JSON.parse(instruction.split('summary: ')[1] || '')
              const num_messages = summary.max_messages
              const summary_message = summary.summary
              currentChat.value.messages[currentChat.value.messages.length - num_messages - 1].summary = summary_message
            }
          }
        }
        const firstMessage = chatMessages.shift()
        // take loading message and update it with the first message from the API response
        currentChat.value.messages[currentChat.value.messages.length - 1] = {
          ...currentChat.value.messages[currentChat.value.messages.length - 1],
          message: firstMessage?.message || '',
          thoughts: firstMessage?.thoughts || '',
          buttons: firstMessage?.buttons || [],
          meta_information: firstMessage?.meta_information || {} as ChatMessage['meta_information'],
          complete: true
        }
        if (chatMessages.length > 0)
          currentChat.value?.messages.push(...chatMessages.map(message => ({
            ...message,
            complete: true,
            timestamp: new Date().toISOString()
          })))
        currentChat.value.storage = {...currentChat.value.storage, ...storage}
        await checkAndGenerateTitle()
      }
      if (topicsStore.selectedTopic && topicsStore.selectedTopic.features.includes('summary')) {
        // Check if we need to summarize after any message changes
        checkAndTriggerSummarization()
      }
    } catch (e) {
      isError.value = true
      console.error('[chat.sendUserMessage] Error during API call: ', e)
    } finally {
      isLoading.value = false
    }
  }

  async function checkAndGenerateTitle() {
    if (!currentChat.value || !topicsStore.selectedTopic) {
      console.error('[chat.checkAndGenerateTitle] No chat/topic selected')
      return
    }
    if (topicsStore.selectedTopic.type == 'skills') return // no title generation for skills since chat title is module name
    if (topicsStore.selectedTopic && topicsStore.selectedTopic.features.includes('title') && currentChat.value.title.length < 1) {
      const {data, error: fetchError} = await client.POST('/topic/{topic}/title', {
        params: {
          path: {
            topic: topicsStore.selectedTopic.endpoint
          }
        },
        body: {
          learning_type_id: "FEELING",
          language: locale.value,
          chat_history: currentChat.value?.messages,
          storage: currentChat.value?.storage,
          llm_purpose: getSelectedLLMPurpose(),
          streaming: false
        }
      })
      if (fetchError) {
        throw fetchError
      }
      if (!data) {
        throw new Error('No data received from API.')
      }
      const title = data.title
      currentChat.value.title = title
    }
  }

  async function sendButtonAction(button: ActionButton) {
    //console.log('send button action')
    isLoading.value = true
    isError.value = false
    if (!currentChat.value || !topicsStore.selectedTopic) {
      console.error('[chat.sendButtonAction] Couldn\'t send message. No chat/topic found...')
      return
    }
    // if (currentChat.value.id == 'default') {
    //   const tempChat = createTempChat()
    //   if (!tempChat) {
    //     console.error('[chat.sendUserMessage] Couldn\'t create new chat...')
    //     return
    //   }
    //   await router.push({params: {skillId: tempChat.id}})
    // }
    currentChat.value.messages.push({
      sender: 'user',
      message: button.chat_message,
      buttons: [],
      complete: true,
      timestamp: new Date().toISOString(),
      meta_information: {} as ChatMessage['meta_information']
    })
    try {
      setChatStorage(button.store)
      if (streaming.value && topicsStore.selectedTopic.features.includes('streaming')) {
        currentChat.value.messages.push({
          sender: 'assistant',
          message: '',
          buttons: [],
          meta_information: {} as ChatMessage['meta_information'],
          complete: false,
          timestamp: ''
        })
        messageComplete.value = false
        chunkQueue.value = []
        queueProcessor.value = null

        const response = await fetch(`${import.meta.env.VITE_API_URL}/topic/${topicsStore.selectedTopic.endpoint}/${button.callback.endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            learning_type_id: "FEELING",
            language: locale.value,
            chat_history: currentChat.value?.messages,
            storage: {
              ...currentChat.value.storage,
              ...button.callback.data
            },
            llm_purpose: getSelectedLLMPurpose(),
            streaming: true
          })
        })

        const reader = response.body?.getReader()
        const decoder = new TextDecoder()

        if (!reader) throw new Error('No reader available')

        while (!messageComplete.value) {
          const {done, value} = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const events = chunk.split('\n\n').filter(e => e.trim())
          events.forEach(event => {
            const content = event.replace('data: ', '')
            const data = JSON.parse(content)
            const chunk = data as ChatCompletionsChunk
            if (chunk.choices.length > 0 && chunk.choices[0].finish_reason === 'stop') {
              messageComplete.value = true
            }
            chunkQueue.value.push(chunk)
          })
          if (!queueProcessor.value) {
            startQueueProcessor()
          }
        }
      } else {
        const {data, error: fetchError} = await client.POST('/topic/{topic}/{endpoint}', {
          params: {
            path: {
              topic: topicsStore.selectedTopic.endpoint,
              endpoint: button.callback.endpoint
            }
          },
          body: {
            learning_type_id: "FEELING",
            language: locale.value,
            chat_history: currentChat.value?.messages,
            storage: {
              ...currentChat.value.storage,
              ...button.callback.data
            },
            llm_purpose: getSelectedLLMPurpose(),
            streaming: false
          }
        })
        if (fetchError) {
          throw fetchError
        }
        if (!data) {
          throw new Error('No data received from API.')
        }
        const dataCasted = data as components['schemas']['Response']
        //const instructions = dataCasted.instructions // TODO handle instructions
        currentChat.value.messages.push(...dataCasted.messages.map(message => ({
          ...message,
          complete: true,
          timestamp: new Date().toISOString()
        })))
        currentChat.value.storage = {...currentChat.value.storage, ...dataCasted.storage}
      }
      if (topicsStore.selectedTopic && topicsStore.selectedTopic.features.includes('summary')) {
        // Check if we need to summarize after any message changes
        checkAndTriggerSummarization()
      }
    } catch (e) {
      isError.value = true
      console.error('[chat.sendButtonAction] Error during API call: ', e)
    } finally {
      isLoading.value = false
    }
  }

  async function requestInspiration() {
    //console.log('request inspiration')
    if (!topicsStore.selectedTopic?.endpoint)
      return
    // if(!inspirations.value[topicsStore.selectedTopic.endpoint])
    inspirations.value[topicsStore.selectedTopic.endpoint] = []
    // if(inspirations.value[topicsStore.selectedTopic.endpoint].length > 0)
    //   return
    isLoadingInspiration.value = true
    if (!topicsStore.selectedTopic || !currentChat.value) {
      console.error('[chat.requestInspiration] No chat/topic selected')
      isLoadingInspiration.value = false
      isError.value = true
      return
    }
    try {
      const {data, error: fetchError} = await client.POST('/topic/{topic}/inspiration', {
        params: {
          path: {
            topic: topicsStore.selectedTopic.endpoint
          }
        },
        body: {
          learning_type_id: "FEELING",
          language: locale.value,
          chat_history: currentChat.value.messages,
          storage: currentChat.value.storage,
          streaming: false
        }
      })
      if (fetchError) {
        throw fetchError
      }
      if (!data) {
        console.error('[chat.requestInspiration] No data received from API.')
        isError.value = true
        return
      }
      const chatInspirations = data.messages
      inspirations.value[topicsStore.selectedTopic.endpoint].push(...chatInspirations)
    } catch (e) {
      console.error('[chat.requestInspiration] Error during API call: ', e)
      isError.value = true
    } finally {
      isLoadingInspiration.value = false
    }
  }

  function setChatStorage(storage: Chat['storage']) {
    //console.log('set chat storage')
    if (!currentChat.value)
      return
    currentChat.value.storage = {...currentChat.value.storage, ...storage}
  }

  async function checkAndTriggerSummarization() {
    //console.log('check and trigger summarization')
    if (!currentChat.value || isLoadingSummarization.value || !topicsStore.selectedTopic) return

    // Check if the bot supports summarization
    if (!currentChat.value.topic.features.includes('summary')) return

    // Clear any existing timeout
    if (summarizationTimeout.value) {
      clearTimeout(summarizationTimeout.value)
    }

    // Only summarize if we have enough messages
    if (currentChat.value.messages.length < maxMessagesBeforeSummarization.value) return

    // Check if we already have a summary in the recent messages
    const recentMessages = currentChat.value.messages.slice(-maxMessagesBeforeSummarization.value)
    const hasSummary = recentMessages.some(message => message.summary)
    if (hasSummary) return

    // Set a new timeout for summarization
    summarizationTimeout.value = setTimeout(async () => {
      try {
        isLoadingSummarization.value = true
        if (!topicsStore.selectedTopic || !currentChat.value) return
        const {data, error: fetchError} = await client.POST('/topic/{topic}/summarize', {
          params: {
            path: {
              topic: topicsStore.selectedTopic.endpoint
            }
          },
          body: {
            learning_type_id: "FEELING",
            language: locale.value,
            chat_history: currentChat.value.messages.map(message => {
              if (message.summary) {
                return {
                  'message': message.message,
                  'sender': 'assistant',
                  'summary': message.summary
                } as components['schemas']['Summary']
              }
              return {
                'message': message.message,
                'sender': message.sender
              }
            }),
            storage: currentChat.value.storage,
            llm_purpose: getSelectedLLMPurpose(),
            streaming: false
          }
        })

        if (fetchError) {
          console.error('[chat.checkAndTriggerSummarization] Error during API call:', fetchError)
          return
        }

        if (!data) {
          console.error('[chat.checkAndTriggerSummarization] No data received from API')
          return
        }

        const response = data as components['schemas']['SummaryResponse']
        // Handle summarization instructions
        if (response.summary && response.keep_last_messages_until) {
          currentChat.value.messages[currentChat.value.messages.length - response.keep_last_messages_until - 1].summary = response.summary
        }
      } catch (e) {
        console.error('[chat.checkAndTriggerSummarization] Error during summarization:', e)
      } finally {
        isLoadingSummarization.value = false
        summarizationTimeout.value = null
      }
    }, summarizationDelay)
  }

  return {
    createChat,
    deleteCurrentChat,
    deleteModuleChats,
    getLastChatId,
    sendUserMessage,
    sendButtonAction,
    requestInspiration,
    setChatStorage,
    getDefaultChatTitle,
    fetchModels,
    getSelectedLLMPurpose,
    importChats,
    allChats,
    topicChats,
    availableAIPurposes,
    currentChat,
    randomInspirations,
    isLoading,
    isLoadingInspiration,
    isError,
    streaming,
    checkAndTriggerSummarization
  }
})
