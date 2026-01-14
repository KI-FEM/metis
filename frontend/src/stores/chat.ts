import { StorageSerializers, useStorage } from '@vueuse/core'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import type {Chat, ChatMessage, ActionButton, Topic, Locale} from '@/types'

import {useTopicsStore} from '@/stores/topics'
import {useCitationBotStore} from '@/stores/citationBot'
import createClient from 'openapi-fetch'
import type {components, paths} from '@/types_api'
import { useChatMessageFunctions } from '@/stores/chatMessages'

export const useChatStore = defineStore('chat', () => {
  const client = createClient<paths>({baseUrl: import.meta.env.VITE_API_URL})
  const router = useRouter()
  const route = useRoute()
  const {locale, t} = useI18n()

  const topicsStore = useTopicsStore()
  const citationBotStore = useCitationBotStore()

  const showDashboard = ref<boolean | null>(null)

  const chatStorage = useStorage<Record<Topic['endpoint'], Chat[]>>('chats', {} as Record<Topic['endpoint'], Chat[]>, undefined, {serializer: StorageSerializers.object})
  const bookmarksStorage = useStorage<Record<Chat['id'], number[]>>('bookmarkedMessages', {}, undefined, {serializer: StorageSerializers.object})
  const inspirations = ref<Record<Topic['endpoint'], string[]>>({} as Record<Topic['endpoint'], string[]>)
  const isLoading = ref(false)
  const isLoadingInspiration = ref(false)
  const isError = ref(false)
  const errorObject = ref<components['schemas']['ErrorReport'] | null>(null)
  const responsePreferences = useStorage<Record<keyof components['schemas']['ResponsePreferences'], number>>('responsePreferences', {
    detail: 2,
    illustration: 2,
    language_style: 2,
    humour: 2,
    creativity: 2,
    emojis: 2
  }, undefined, {serializer: StorageSerializers.object})
  const streaming = useStorage<boolean>('streaming', true)

  const abortController = ref<AbortController | null>(null)

  const messageComplete = ref(false)

  const isLoadingSummarization = ref(false)
  const summarizationTimeout = ref<number | null>(null)
  const summarizationDelay = 5000 // 5 seconds of idle time before summarizing

  const availableAIPurposes = ref<components['schemas']['PurposeModel'][]>([])
  const maxMessagesBeforeSummarization = ref(16)


  const allChats = computed(() => chatStorage.value)
  const topicChats = computed(() => chatStorage.value[route.params.endpoint as Topic['endpoint']] || [])

  /**
   * The current chat based on the route parameters (topic endpoint and chat ID).
   */
  const currentChat = computed(() => {
    if (!topicsStore.selectedTopic?.endpoint)
      return null
    return chatStorage.value[topicsStore.selectedTopic.endpoint]?.find(chat => chat.id === route.params.chatId) || null
  })

  /**
   * Get context data for the citation bot (if the current topic supports it)
   * @returns Context data for the citation bot (if the current topic supports it)
   */
  function getCitationBotContext(): Record<string, string> {
    if (!topicsStore.selectedTopic?.features.includes('scientific_paper_context')) {
      return {}
    }

    const deadlines = citationBotStore.context.deadlines
      .map(d => `${d.name}: ${d.date}`)
      .join('\n')

    return {
      thesis_title: citationBotStore.context.title,
      thesis_task: citationBotStore.context.task,
      thesis_deadlines: deadlines || 'Keine Deadlines gesetzt',
      thesis_information: citationBotStore.context.additionalInfo
    }
  }

  /**
   * Import chat backups from a JSON file.
   * @param chatBackup the chat backup to import (usually from a JSON file)
   */
  function importChats(chatBackup: Record<Topic['endpoint'], Chat[]>) {
    for (const topicEndpoint in chatBackup) {
      const topicChats = chatBackup[topicEndpoint as Topic['endpoint']]
      if (!topicChats) continue
      
      // if the topic doesn't exist, add it
      if (!chatStorage.value[topicEndpoint as Topic['endpoint']]) {
        chatStorage.value[topicEndpoint as Topic['endpoint']] = topicChats
        continue
      }
      // merge (add or overwrite) each chat from the backup
      for (const topicChat of topicChats) {
        const chats = chatStorage.value[topicEndpoint as Topic['endpoint']]
        if (!chats) continue
        
        const index = chats.findIndex(chat => chat.id === topicChat.id)
        if (index === -1)
          chats.push(topicChat)
        else
          chats[index] = topicChat
      }
    }
  }

  /**
   * Get the selected LLM purpose from the current chat.
   * @returns the selected LLM purpose from the current chat, or null if none is selected
   */
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

  /**
   * Check if a chat title needs to be generated and generate it if necessary
   * @returns
   */
  async function checkAndGenerateTitle() {
    if (!currentChat.value || !topicsStore.selectedTopic) {
      console.error('[chat.checkAndGenerateTitle] No chat/topic selected')
      return
    }
    if (topicsStore.selectedTopic.type != 'basic') return // no title generation for skills since chat title is module name
    if (topicsStore.selectedTopic && topicsStore.selectedTopic.features.includes('title') && currentChat.value.title.length < 1) {
      const {data, error: fetchError} = await client.POST('/topic/{topic}/title', {
        params: {
          path: {
            topic: topicsStore.selectedTopic.endpoint
          }
        },
        body: {
          id: currentChat.value.id,
          language: locale.value,
          chat_history: currentChat.value?.messages,
          storage: currentChat.value?.storage,
          llm_purpose: getSelectedLLMPurpose(),
          response_preferences: responsePreferences.value,
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

  // Initialize chat message functions composable
  const chatMessageFunctions = useChatMessageFunctions({
    currentChat,
    messageComplete,
    errorObject,
    topicsStore,
    client,
    locale,
    getCitationBotContext,
    getSelectedLLMPurpose,
    responsePreferences,
    abortController,
    checkAndGenerateTitle,
    isLoading
  })

  /**
   * Get random inspirations for the current topic (if any are available).
   */
  const randomInspirations = computed(() => {
    if (!topicsStore.selectedTopic?.endpoint) {
      return []
    }
    const topicInspirations = inspirations.value[topicsStore.selectedTopic.endpoint]
    if (!topicInspirations) {
      return []
    }
    let shuffledInspirations = topicInspirations.sort(() => 0.5 - Math.random())

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
      return chatStorage.value[endpoint]?.[0]?.id
  }

  /**
   * Create a new chat and initialize it with a message from the bot
   * @returns
   */
  async function createChat() {
    if (!topicsStore.selectedTopic)
      throw new Error('No topic selected')
    let competenceCode = topicsStore.selectedTopic?.modules.find(module => module.code === route.params.chatId)?.code
    if (topicsStore.selectedTopic?.type == 'skills' && topicsStore.selectedTopic?.modules.length && !competenceCode) {
      console.error('No module with matching ID')
      await router.push({name: 'modules', params: {endpoint: topicsStore.selectedTopic.endpoint}})
      return
    }
    if (topicsStore.selectedTopic.type == 'coach') {
      competenceCode = 'coach'
    }
    const chatId = competenceCode || Date.now().toString()
    const uuid = crypto.randomUUID()
    //console.log('chatId')
    if (!chatStorage.value[topicsStore.selectedTopic.endpoint])
      chatStorage.value[topicsStore.selectedTopic.endpoint] = []
    const newStorage: Record<string, string> = {
      chat_id: chatId,
      unique_id: uuid // unique identifier for the chat in case chatId is not unique (module name)
    }
    // Set llm_purpose to the first available purpose if available
    newStorage['llm_purpose'] = availableAIPurposes.value[0]?.id ?? 'optimal'

    if (competenceCode)
      newStorage['selected_competence'] = competenceCode
    const levelId = topicsStore.storedModuleLevelId(competenceCode)
    if (levelId)
      newStorage['skill_level'] = levelId
    const customLearningGoal = topicsStore.storedModuleLevelObjective(competenceCode, levelId)
    if (customLearningGoal)
      newStorage['custom_learning_goals'] = customLearningGoal.text

    if (!chatStorage.value[topicsStore.selectedTopic.endpoint]) {
      chatStorage.value[topicsStore.selectedTopic.endpoint] = []
    }
    chatStorage.value[topicsStore.selectedTopic.endpoint]!.unshift({
      id: chatId,
      title: '',
      language: locale.value as Locale,
      messages: [],
      storage: newStorage,
      topic: topicsStore.selectedTopic
    })
    await router.replace({params: {chatId: chatId}})

    isError.value = false
    errorObject.value = null
    errorObject.value = null
    if (!currentChat.value || currentChat.value.messages.length)
      return

    // and initialize with a message from the bot
    initChat()
  }

  /**
   * Call the init endpoint and stream/send message to the chat
   * @returns
   */
  async function initChat() {
    if (!currentChat.value || !topicsStore.selectedTopic) return

    isLoading.value = true
    const timestamp = new Date().toISOString()
    currentChat.value.messages.push({
      fragment: false,
      type: 'assistant',
      content: '',
      buttons: [],
      meta_information: {} as ChatMessage['meta_information'],
      complete: false,
      timestamp: timestamp
    })
    if (streaming.value && topicsStore.selectedTopic.features.includes('streaming')) {
      // streaming
      messageComplete.value = false
      try {
        abortController.value = new AbortController()

        const response = await fetch(`${import.meta.env.VITE_API_URL}/topic/${topicsStore.selectedTopic.endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            id: timestamp,
            language: locale.value,
            chat_history: currentChat.value.messages.map(m => {
              if (!m.fragment && m.summary) {
                return {
                  'content': m.content,
                  'type': 'assistant',
                  'summary': m.summary,
                  'timestamp': m.timestamp,
                } as components['schemas']['Summary']
              }
              // pydantic
              return {
                'content': m.content,
                'type': m.type,
                'timestamp': m.timestamp
              }
            }),
            storage: {
              ...currentChat.value?.storage,
              ...getCitationBotContext(),
            },
            llm_purpose: getSelectedLLMPurpose(),
            response_preferences: responsePreferences.value,
            streaming: true
          }),
          signal: abortController.value.signal
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const contentType = response.headers.get('content-type')

        if (contentType?.includes('application/json')) {
          // Handle non-streaming response (full JSON)
          await chatMessageFunctions.processNonStreamingChatResponse(await response.json(), timestamp)
        } else {
          // Handle streaming response (SSE)
          await chatMessageFunctions.processStreamingChatResponse(response)
        }
      } catch (e) {
        isError.value = true
        console.error('Error during API call: ', e)
      } finally {
        isLoading.value = false
        abortController.value = null
      }
    } else {
      // non streaming
      try {
        const {data, error: fetchError} = await client.POST('/topic/{topic}', {
          params: {
            path: {
              topic: topicsStore.selectedTopic?.endpoint
            }
          },
          body: {
            id: currentChat.value.id,
            language: locale.value,
            chat_history: currentChat.value.messages.map(message => {
              return {
                'content': message.content,
                'type': message.type,
                'timestamp': message.timestamp,
              }
            }),
            storage: {
              ...currentChat.value?.storage,
              ...getCitationBotContext(),
            },
            llm_purpose: getSelectedLLMPurpose(),
            response_preferences: responsePreferences.value,
            streaming: false
          }
        })
        if (fetchError)
          console.error('Error during API call: ', fetchError)
        if (!data)
          throw new Error('No data received from API')
        const response = data as components['schemas']['Response']
        await chatMessageFunctions.processNonStreamingChatResponse(response, timestamp)
      } catch (e) {
        isError.value = true
        console.error('Error during API call: ', e)
      } finally {
        isLoading.value = false
      }
    }
  }

  /**
   * Delete a chat with the given ID
   * @param endpoint the topic endpoint
   * @param chatId the chat ID
   */
  function deleteCurrentChat(endpoint: Topic['endpoint'], chatId: Chat['id']) {
    const chats = chatStorage.value[endpoint]
    if (!chats) return
    chatStorage.value[endpoint] = chats.filter(chat => chat.id !== chatId)
    messageComplete.value = false
    errorObject.value = null
    isLoading.value = false
  }

  /**
   * Delete all chats for a given topic
   * @param endpoint the topic endpoint
   */
  function deleteModuleChats(endpoint: Topic['endpoint']) {
    chatStorage.value[endpoint] = []
    messageComplete.value = false
    errorObject.value = null
    isLoading.value = false
  }

  /**
   * Get the default chat title
   * @returns the default chat title
   */
  function getDefaultChatTitle(): string {
    return t('newChatLabel')
    //console.log('get initial chat title')
    // return t('initialChatTitle').replace('insertTopic', topicsStore.selectedTopic?.title)
  }

  /**
   * Fetch the available AI purposes from the backend
   * @returns the available AI purposes from the backend
   */
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

  // message streaming and processing


  /**
   * Resend a message in the chat by removing all messages at and after its index and retrying the API call with the preceding user message
   * @param messageIndex the index of the message to resend
   * @returns
   */
  async function resendMessage(messageIndex: number) {
    const chat = currentChat.value
    if (!chat) return

    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
    const resendMessage = chat.messages[messageIndex]
    if (!resendMessage || resendMessage.fragment) {
      return
    }
    const processExtra = (source: string) => {
        if (source === 'init_chat') {
          // drop all messages including and after the selected message
          chat.messages = chat.messages.slice(0, messageIndex)
          // re-init chat
          initChat()
          return
        }
    }
    if (resendMessage.meta_information && resendMessage.meta_information.source) {
      processExtra(resendMessage.meta_information.source as string)
    } 
    // else if (resendMessage.events && resendMessage.events.length > 0) {
    //   const init = resendMessage.events.find(event => event.event === 'initial_metadata')
    //   if (init && init.additional_info && init.additional_info['source']) {
    //     // special handling since source is not simple send message
    //     processExtra(init.additional_info['source'] as string)
    //   }
    // }
    
    const lastUserMessage = chat.messages
      .slice(0, messageIndex + 1)
      .reverse()
      .find(msg => msg.type === 'user')
    if (!lastUserMessage) return

    const index = chat.messages.findIndex(msg => msg.timestamp === lastUserMessage.timestamp)
    if (index === -1) return

    const msgAtIndex = chat.messages[index]
    if (!msgAtIndex) return

    const resendText = msgAtIndex.content ?? ''

    // drop messages after the one we’re resending
    chat.messages = chat.messages.slice(0, index)

    sendUserMessage(resendText)
  }


  /**
   * Send a user message to the chat endpoint of the current chat
   * @param message the user message to send
   * @returns
   */
  async function sendUserMessage(message: string) {
    isLoading.value = true
    isError.value = false
    errorObject.value = null
    errorObject.value = null
    if (!currentChat.value || !topicsStore.selectedTopic) {
      console.error('[chat.sendUserMessage] Couldn\'t send message. No chat/topic found...')
      return
    }

    currentChat.value.messages.push({
      fragment: false,
      type: 'user',
      content: message,
      buttons: [],
      meta_information: {} as ChatMessage['meta_information'],
      complete: true,
      timestamp: new Date().toISOString()
    })
    try {
      // create empty bot message
      // save the timestamp of the
      const timestamp = new Date().toISOString()
      currentChat.value.messages.push({
        fragment: false,
        type: 'assistant',
        content: '',
        buttons: [],
        meta_information: {} as ChatMessage['meta_information'],
        complete: false,
        timestamp: timestamp
      })
      const assistantMessageIndex = currentChat.value.messages.length - 1
      messageComplete.value = false // streaming
      if (streaming.value && topicsStore.selectedTopic.features.includes('streaming')) {
        // streaming
        await chatMessageFunctions.sendUserMessageStreaming(timestamp)

        // After streaming is done, check if we received a final answer
        const assistantMessage = currentChat.value?.messages[assistantMessageIndex]

        if (assistantMessage && !assistantMessage.fragment) {
          const allMessageEvents = assistantMessage?.events?.map(event => event.event) || []
          if (!allMessageEvents.includes('formulate_answer')) {
            // If we did not receive a final answer, mark the message as complete and add a note
            assistantMessage.content = t('noFinalAnswer')
            assistantMessage.complete = true
            messageComplete.value = true
          }
        } else {
          console.error('This shouldn\'t happen! Could not find assistant message after streaming')
        }
      } else {
        // non streaming
        await chatMessageFunctions.sendUserMessageNonStreaming(timestamp)
      }
      if (topicsStore.selectedTopic && topicsStore.selectedTopic.features.includes('summary')) {
        // Check if we need to summarize after any message changes
        checkAndTriggerSummarization()
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') {
        console.log('Fetch request aborted.')
      } else {
        console.error('[chat.sendUserMessage] Error during API call: ', e)
        let errorValue = true

        const assistantMessage = currentChat.value?.messages[currentChat.value.messages.length - 1]
        if (assistantMessage && !assistantMessage.fragment) {
          const allMessageEvents = assistantMessage.events?.map(event => event.event) || []
          if (allMessageEvents.includes('formulate_answer')) {
            errorValue = false // only set error if we didn't get a final answer, else only show error in console
            // TODO maybe show a warning?
          }
        }
        isError.value = errorValue
      }
    } finally {
      isLoading.value = false
      abortController.value = null
    }
  }

  /**
   * Send a message to the action endpoint according to the button pressed
   * @param button the action button that was clicked
   * @returns
   */
  async function sendButtonAction(button: ActionButton) {
    isLoading.value = true
    isError.value = false
    errorObject.value = null
    errorObject.value = null
    if (!currentChat.value || !topicsStore.selectedTopic) {
      console.error('[chat.sendButtonAction] Couldn\'t send message. No chat/topic found...')
      return
    }
    
    currentChat.value.messages.push({
      fragment: false,
      type: 'user',
      content: button.chat_message,
      buttons: [],
      complete: true,
      timestamp: new Date().toISOString(),
      meta_information: {} as ChatMessage['meta_information']
    })
    try {
      const timestamp = new Date().toISOString()
      setChatStorage(button.store)
      if (streaming.value && topicsStore.selectedTopic.features.includes('streaming')) {
        currentChat.value.messages.push({
          fragment: false,
          type: 'assistant',
          content: '',
          buttons: [],
          meta_information: {} as ChatMessage['meta_information'],
          complete: false,
          timestamp: timestamp
        })
        messageComplete.value = false

        // TODO: switch to client.POST
        const response = await fetch(`${import.meta.env.VITE_API_URL}/topic/${topicsStore.selectedTopic.endpoint}/${button.callback.endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            id: timestamp,
            language: locale.value,
            chat_history: currentChat.value?.messages,
            storage: {
              ...currentChat.value.storage,
              ...button.callback.data,
              ...getCitationBotContext(),
            },
            llm_purpose: getSelectedLLMPurpose(),
            response_preferences: responsePreferences.value,
            streaming: true
          })
        })

        const contentType = response.headers.get('content-type')

        if (contentType?.includes('application/json')) {
          // Handle non-streaming response (full JSON)
          await chatMessageFunctions.processNonStreamingChatResponse(await response.json(), timestamp)
        } else {
          // Handle streaming response (SSE)
          await chatMessageFunctions.processStreamingChatResponse(response)
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
            id: timestamp,
            language: locale.value,
            chat_history: currentChat.value?.messages,
            storage: {
              ...currentChat.value.storage,
              ...button.callback.data,
              ...getCitationBotContext(),
            },
            llm_purpose: getSelectedLLMPurpose(),
            response_preferences: responsePreferences.value,
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
        if (dataCasted.messages.length > 0) {
          currentChat.value.messages.push({
            fragment: false,
            type: 'assistant',
            content: '',
            buttons: [],
            meta_information: {} as ChatMessage['meta_information'],
            complete: false,
            timestamp: timestamp
          })
        }
        chatMessageFunctions.processNonStreamingChatResponse(dataCasted, timestamp)
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

  /**
   * Request inspiration messages from the API.
   * @returns
   */
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
          id: currentChat.value.id,
          language: locale.value,
          chat_history: currentChat.value.messages,
          storage: {
            ...currentChat.value.storage,
            ...getCitationBotContext(),
          },
          response_preferences: responsePreferences.value,
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
      if (!inspirations.value[topicsStore.selectedTopic.endpoint]) {
        inspirations.value[topicsStore.selectedTopic.endpoint] = []
      }
      inspirations.value[topicsStore.selectedTopic.endpoint]!.push(...chatInspirations)
    } catch (e) {
      console.error('[chat.requestInspiration] Error during API call: ', e)
      isError.value = true
    } finally {
      isLoadingInspiration.value = false
    }
  }

  /**
   * Set the storage for the current chat.
   * @param storage the storage to set for the current chat
   * @returns
   */
  function setChatStorage(storage: Chat['storage']) {
    //console.log('set chat storage')
    if (!currentChat.value)
      return
    currentChat.value.storage = {...currentChat.value.storage, ...storage}
  }

  /**
   * Check if a chat summary needs to be generated and generate it if necessary.
   * This sets the summary attribute on a message in the chat history, marking that all previous messages are summarized by this chat message.
   * @returns
   */
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
    const hasSummary = recentMessages.some(message => !message.fragment && message.summary)
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
            id: currentChat.value.id,
            language: locale.value,
            chat_history: currentChat.value.messages.map(message => {
              if (!message.fragment && message.summary) {
                return {
                  'content': message.content,
                  'type': 'assistant',
                  'summary': message.summary,
                  'timestamp': message.timestamp,
                } as components['schemas']['Summary']
              }
              return {
                'content': message.content,
                'type': message.type,
                'timestamp': message.timestamp,
              }
            }),
            storage: {
              ...currentChat.value.storage,
              ...getCitationBotContext(),
            },
            llm_purpose: getSelectedLLMPurpose(),
            response_preferences: responsePreferences.value,
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
          const idx = currentChat.value.messages.length - response.keep_last_messages_until - 1
          const msg = currentChat.value.messages[idx]
          if (msg && !msg.fragment) {
            msg.summary = response.summary
          }
        }
      } catch (e) {
        console.error('[chat.checkAndTriggerSummarization] Error during summarization:', e)
      } finally {
        isLoadingSummarization.value = false
        summarizationTimeout.value = null
      }
    }, summarizationDelay)
  }

  function addMessage(message: ChatMessage) {
    if (!currentChat.value) return
    currentChat.value.messages.push(message)
  }

  async function processQuizStreamedResponse(response: Response) {
    await chatMessageFunctions.processStreamingChatResponse(response)
  }

  async function addComment(messageId: string, comment: string, vote: number | null){
    if (!currentChat.value || !topicsStore.selectedTopic) return false
    const message = currentChat.value.messages.find(msg => msg.timestamp === messageId)
    if (message && message.meta_information && message.meta_information.trace_id) {
      const traceId = message.meta_information.trace_id
      const {data, error: fetchError} = await client.POST('/topic/{topic}/message/comment', {
        params: {
          path: {
            topic: topicsStore.selectedTopic.endpoint
          }
        },
        body: {
          comment,
          vote,
          trace_id: traceId
        }
      })

      if (fetchError) {
        console.error('Error adding comment: ', fetchError)
        return false
      }
      if (!data) {
        console.error('No data received from API when adding comment.')
        return false
      }
      if (data.error) {
        console.error('Error from API when adding comment: ', data.error)
        return false
      }
      return data.success
    }
    return false
  }

  async function voteMessage(messageId: string, vote: 'up' | 'down'){
    if (!currentChat.value || !topicsStore.selectedTopic) return false
    const message = currentChat.value.messages.find(msg => msg.timestamp === messageId)
    if (message && message.meta_information && message.meta_information.trace_id) {
      const traceId = message.meta_information.trace_id
      const {data, error: fetchError} = await client.POST('/topic/{topic}/message/vote', {
        params: {
          path: {
            topic: topicsStore.selectedTopic.endpoint
          }
        },
        body: {
          vote: vote == 'up' ? 1 : 0,
          trace_id: traceId
        }
      })

      if (fetchError) {
        console.error('Error voting message: ', fetchError)
        return false
      }
      if (!data) {
        console.error('No data received from API when voting message.')
        return false
      }
      if (data.error) {
        console.error('Error from API when voting message: ', data.error)
        return false
      }
      return data.success
    }
    return false
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
    initChat,
    addComment,
    voteMessage,
    messageComplete,
    allChats,
    topicChats,
    showDashboard,
    availableAIPurposes,
    currentChat,
    randomInspirations,
    isLoading,
    isLoadingInspiration,
    isError,
    errorObject,
    responsePreferences,
    streaming,
    bookmarksStorage,
    checkAndTriggerSummarization,
    processQuizStreamedResponse,
    resendMessage,
    addMessage,
  }
})
