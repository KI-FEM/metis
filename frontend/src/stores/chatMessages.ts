import type {Chat, ChatMessage, ChatMessageEvent, ChatCompletionsChunk, ChatMessageMessage} from '@/types'
import type {components, paths} from '@/types_api'
import type { Client } from 'openapi-fetch'

import { ref, type Ref } from "vue"
import type { TopicsStoreInterface } from './topics'
import { useMemoryStore } from './memory'

// Context interface that the composable needs from the store
export interface ChatMessageContext {
  currentChat: Ref<Chat | null>
  messageComplete: Ref<boolean>
  isLoading: Ref<boolean>
  errorObject: Ref<components['schemas']['ErrorReport'] | null>
  topicsStore: TopicsStoreInterface
  client: Client<paths>
  locale: Ref<string>
  getCitationBotContext: () => Record<string, string>
  getSelectedLLMPurpose: () => components['schemas']['PurposeModel']['id'] | null
  responsePreferences: Ref<Record<keyof components['schemas']['ResponsePreferences'], number>>
  abortController: Ref<AbortController | null>
  checkAndGenerateTitle: () => Promise<void>
}

const queueProcessor = ref<Promise<void> | null>(null)
const processingQueue = ref(false)
const chunkQueue = ref<ChatCompletionsChunk[]>([])
const memoryStore = useMemoryStore()

/**
 * Update the learner model incrementally based on newly seen learning units
 * @param learnerModel The learner model to update
 * @param seenLearningUnitCodes Array of learning unit codes that were just seen
 * @param timestamp The timestamp to record for last_seen
 */
function updateLearnerModelWithSeenUnits(
  learnerModel: components["schemas"]["LearnerModel-Output"],
  seenLearningUnitCodes: string[],
  timestamp: string
): void {
  // Iterate through all competences and concepts to find and update the learning units
  for (const competence of Object.values(learnerModel.competences)) {
    for (const concept of Object.values(competence.concepts)) {
      for (const [luCode, lu] of Object.entries(concept.learning_units)) {
        if (seenLearningUnitCodes.includes(luCode)) {
          lu.times_seen = (lu.times_seen || 0) + 1
          lu.last_seen = timestamp
        }
      }
    }
  }
  
  // Also update the internal learning_units dictionary if it exists
  if (learnerModel.learning_units) {
    for (const luCode of seenLearningUnitCodes) {
      const internalLu = learnerModel.learning_units[luCode]
      if (internalLu) {
        internalLu.times_seen = (internalLu.times_seen || 0) + 1
        internalLu.last_seen = timestamp
      }
    }
  }
}

/**
 * Create a composable with chat message functionality
 * @param context The context from the chat store
 */
export function useChatMessageFunctions(context: ChatMessageContext) {
  const {
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
  } = context

  /**
   * Start processsing chunks from the chunk queue asynchronously
   * @returns 
   */
  async function startQueueProcessor() {
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

    queueProcessor.value = null
  }

  /**
   * Read and process a chunk of chat completions
   * @param chunk the chunk to read and process
   * @returns true if the chunk was processed successfully, false otherwise
   */
  function readChunk(chunk: ChatCompletionsChunk) {
    const chat = currentChat.value
    if (!chat || chunk.choices.length === 0) return false

    const choice = chunk.choices[0]!
    const delta = choice.delta ?? ({} as Partial<typeof choice['delta']>)
    const chunk_id = chunk.id
    const message_id = chunk_id.slice(chunk_id.indexOf('-')+1) // split on the first '-'

    // find the assistant message that matches the message id
    const msg = chat.messages.find(m => m.type === 'assistant' && !m.fragment && m.timestamp === message_id)
    if (!msg || msg.fragment) {
      console.warn('No matching assistant message found for chunk id:', chunk_id)
      return false
    }

    //lastMsg.timestamp = chunk.created

    if (delta.type) {
      msg.type = delta.type as components['schemas']['MessageType']
    }

    if (delta.buttons?.length) {
      // ensure array exists before pushing
      msg.buttons = msg.buttons ?? []
      msg.buttons.push(...delta.buttons)
    }

    if (delta.storage) {
      chat.storage = {...chat.storage, ...delta.storage}
    }

    // ensure meta_information exists before writing into it
    msg.meta_information = msg.meta_information ?? ({} as ChatMessage['meta_information'])

    if (delta.llm_model) {
      msg.meta_information.llm_model = delta.llm_model
    }

    if (delta.citations) {
      msg.meta_information.citations = delta.citations
    }

    if (delta.trace_id) {
      msg.meta_information.trace_id = delta.trace_id
    }

    if (delta.instructions?.length) {
      for (const instruction of delta.instructions) {
        if (instruction.includes('discard')) {
          msg.content = ''
        }
        if (instruction.includes('answer_end')) {
          msg.complete = true
          isLoading.value = false
          msg.content = delta.content ?? msg.content
        }
        if (instruction.includes('summary: ')) {
          const jsonText = instruction.slice(instruction.indexOf('summary: ') + 'summary: '.length)

          // parse defensively
          let parsed: { max_messages?: number; summary?: string } | null = null
          try {
            parsed = JSON.parse(jsonText)
          } catch {
            parsed = null
          }

          const numMessages = typeof parsed?.max_messages === 'number' ? parsed.max_messages : undefined
          const summaryMessage = parsed?.summary

          if (summaryMessage && numMessages !== undefined) {
            const idx = chat.messages.length - numMessages - 1
            const target = chat.messages.filter(m => !m.fragment)[idx]
            if (target) {
              target.summary = summaryMessage
            }
          }
        }
        const addEvent = (event: ChatMessageEvent) => {
          if (msg.fragment) return;
          if (!msg.events) {
              msg.events = []
            }
          msg.events = [...msg.events, event]
        }

        if (instruction.includes('info: ')) {
          const eventString = instruction.replace('info: ', '')
          try {
            const event = JSON.parse(eventString) as ChatMessageEvent
            console.log(' \\- Received agent event:', event)
            addEvent(event)
            if (event.event === 'initial_metadata' && event.additional_info) {
              // merge initial metadata into message meta_information
              msg.meta_information = {
                ...msg.meta_information,
                ...event.additional_info
              }
            }
          } catch (e) {
            console.error(' \\- Failed to parse event JSON:', e, eventString)
          }
        } else if (instruction.includes('update_memory: ')) {
          const memoryString = instruction.replace('update_memory: ', '')
          try {
            const memoryEvent = JSON.parse(memoryString) as ChatMessageEvent
            console.log(' \\- Received update_memory event:', memoryEvent)
            if (memoryEvent.additional_info?.new_memory) {
              memoryStore.addPotentialMemory(message_id, memoryEvent.additional_info.new_memory as string)
            }
            addEvent(memoryEvent)
          } catch (e) {
            console.error(' \\- Failed to parse update_memory JSON:', e, memoryString)
          }
        } else if (instruction.includes('update_learner_model: ')) {
          const modelString = instruction.replace('update_learner_model: ', '')
          try {
            const modelEvent = JSON.parse(modelString) as ChatMessageEvent
            console.log(' \\- Received update_learner_model event:', modelEvent)
            
            // Update learner model incrementally based on newly seen learning units
            if (modelEvent.additional_info?.seen_learner_model && currentChat.value) {
              const seenLearningUnitCodes = modelEvent.additional_info.seen_learner_model as string[]
              const learnerModel = currentChat.value.storage['learner_model'] as components["schemas"]["LearnerModel-Output"] | undefined
              
              if (learnerModel) {
                updateLearnerModelWithSeenUnits(learnerModel, seenLearningUnitCodes, new Date().toISOString())
              }
            }
            
            addEvent(modelEvent)
          } catch (e) {
            console.error(' \\- Failed to parse update_learner_model JSON:', e, modelString)
          }
        } else if (instruction.includes('updated_conversation_strategy: ')) {
          const planString = instruction.replace('updated_conversation_strategy: ', '')
          try {
            const planEvent = JSON.parse(planString) as ChatMessageEvent
            console.log(' \\- Received updated_conversation_strategy event:', planEvent)
            if (planEvent.additional_info?.conversation_strategy && currentChat.value) {
              currentChat.value.storage['conversation_strategy'] = planEvent.additional_info.conversation_strategy as string
            }
            addEvent(planEvent)
          } catch (e) {
            console.error(' \\- Failed to parse planned_conversation JSON:', e, planString)
          }
        }
      }
    }

    if (delta.sources) {
      const existing = msg.meta_information.sources
      msg.meta_information.sources = existing ? {...existing, ...delta.sources} : {...delta.sources}
    }

    if (delta.thoughts) {
      msg.thoughts = delta.thoughts
    }

    if (choice.finish_reason === 'stop') {
      msg.complete = true
      msg.content = delta.content ?? msg.content
      isLoading.value = false
      return true
    }

    if (delta.content) {
      msg.content = delta.content
    }

    return false
  }


  /**
   * Process the non-streaming response data from a message API endpoint
   * @param data the non-streaming response data from the API
   * @returns 
   */
  async function processNonStreamingChatResponse(data: components['schemas']['Response'], timestamp: string) {
    if (!currentChat.value) return

    if (data.error) {
      errorObject.value = data.error
      throw new Error(`Error from API: ${JSON.stringify(data.error, null, 2)}`)
    }
    
    queueProcessor.value = null
    const chatMessages : components['schemas']['Response']['messages'] = data.messages
    const storage = data.storage
    const instructions = data.instructions
    
    if (instructions) {
      for (const instruction of instructions) {
        if (instruction.includes('summary: ')) {
          const summary = JSON.parse(instruction.split('summary: ')[1] || '')
          const num_messages = summary.max_messages
          const summaryContent = summary.summary
          const messageToAppendSummary = currentChat.value.messages.filter(m => !m.fragment)[currentChat.value.messages.length - num_messages - 1]
          if (messageToAppendSummary) messageToAppendSummary.summary = summaryContent
        }
      }
    }
    
    const firstMessage = chatMessages.shift()
    // Update loading message with the first message from the API response
    currentChat.value.messages[currentChat.value.messages.length - 1] = {
      ...currentChat.value.messages[currentChat.value.messages.length - 1],
      content: firstMessage?.content || '',
      type: firstMessage?.type || 'assistant',
      thoughts: firstMessage?.thoughts || '',
      buttons: firstMessage?.buttons || [],
      timestamp: timestamp,
      meta_information: firstMessage?.meta_information || {} as ChatMessage['meta_information'],
      complete: true
    } as ChatMessageMessage
    
    if (chatMessages.length > 0) {
      currentChat.value?.messages.push(...chatMessages.map(message => ({
        ...message,
        complete: true,
        timestamp: timestamp
      } as ChatMessageMessage)))
    }
    
    currentChat.value.storage = {...currentChat.value.storage, ...storage}
    await checkAndGenerateTitle()
  }

  /**
   * Proces the streaming response data from a message API endpoint
   * @param response the streaming response
   */
  async function processStreamingChatResponse(response: Response) {
    queueProcessor.value = null
    chunkQueue.value = []

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) throw new Error('No reader available')

    let concatenatedEvents = []
    while (!messageComplete.value) {
      const {done, value} = await reader.read()
      if (done) break

      const eventsChunk = decoder.decode(value)
      const events = eventsChunk.split('\n\n').filter(e => e.trim())
      
      const processEvent = (event: string) => {
        const content = event.replace('data: ', '')
        let data
        //console.log("Received chunk:", content)
        try {
          data = JSON.parse(content)
        } catch (e) {
          console.error('Failed to parse chunk JSON:', e, content)
          return false
        }
        if (data.error) {
          errorObject.value = data.error
          throw new Error(`Error from API: ${JSON.stringify(errorObject.value, null, 2)}`)
        }
        const chunk = data as ChatCompletionsChunk
        chunkQueue.value.push(chunk)
        if (chunk.choices[0]?.finish_reason === 'stop') {
          messageComplete.value = true
        }
        return true
      }

      for (const event of events) {
        if (event.startsWith('data: ') && concatenatedEvents.length > 0) {
          // process the previous concatenated event
          const fullEvent = concatenatedEvents.join('')
          if (!processEvent(fullEvent)) {
            console.error('Failed to process concatenated event:', fullEvent)
            // this should never fail, since we received a new 'data: ' event
            // therefore this previous event must have been complete
            // but just in case, we log an error and continue
          }
          concatenatedEvents = []
        }
        concatenatedEvents.push(event)
      }
      if (concatenatedEvents.length > 0) {
        // process the previous concatenated event
        const fullEvent = concatenatedEvents.join('')
        if (!processEvent(fullEvent)) {
          console.error('Failed to process concatenated event:', fullEvent)
          // maybe we need to wait for the next event to be received?
          // so we keep the concatenatedEvents as is and continue
          continue
        }
        concatenatedEvents = []
      }
      if (!queueProcessor.value) {
        startQueueProcessor()
      }
    }
  }

  /**
   * Invoke the message endpoint with streaming enabled
   * @returns 
   */
  async function sendUserMessageStreaming(timestamp: string) {
    if (!currentChat.value || !topicsStore.selectedTopic) return
    
    // stop any in-flight streaming and clear queued chunks
    if (chunkQueue.value.length > 0) {
      messageComplete.value = true
      chunkQueue.value = []
    }

    abortController.value = new AbortController()
    // wait until the queue processor finishes
    while (queueProcessor.value) {
      await new Promise(resolve => setTimeout(resolve, 50))
    }
    queueProcessor.value = null
    // TODO: switch to client.POST
    const response = await fetch(`${import.meta.env.VITE_API_URL}/topic/${topicsStore.selectedTopic.endpoint}/message`, {
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
              'timestamp': m.timestamp
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
      await processNonStreamingChatResponse(await response.json(), timestamp)
    } else {
      // Handle streaming response (SSE)
      await processStreamingChatResponse(response)
    }
  }


  /**
   * Invoke the message endpoint with streaming disabled
   * @returns 
   */
  async function sendUserMessageNonStreaming(timestamp: string) {
    if (!currentChat.value || !topicsStore.selectedTopic) return

    abortController.value = new AbortController()
    chunkQueue.value = []

    // wait until the queue processor finishes
    while (queueProcessor.value) {
      await new Promise(resolve => setTimeout(resolve, 50))
    }
    const {data, error: fetchError} = await client.POST('/topic/{topic}/message', {
      params: {
        path: {
          topic: topicsStore.selectedTopic.endpoint
        }
      },
      body: {
        id: timestamp,
        language: locale.value,
        chat_history: currentChat.value.messages.map(m => {
          if (!m.fragment && m.summary) {
            return {
              'content': m.content,
              'type': 'assistant',
              'summary': m.summary,
              'timestamp': m.timestamp
            } as components['schemas']['Summary']
          }
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
        streaming: false
      },
      signal: abortController.value.signal
    })
    if (fetchError) {
      throw fetchError
    }
    if (!data) {
      throw new Error('No data received from API.')
    }
    if (data.error) {
      errorObject.value = data.error
      throw new Error(`Error from API: ${JSON.stringify(data.error, null, 2)}`)
    }
    await processNonStreamingChatResponse(data, timestamp)
  }

  return {
    queueProcessor,
    processingQueue,
    startQueueProcessor,
    readChunk,
    processNonStreamingChatResponse,
    processStreamingChatResponse,
    sendUserMessageStreaming,
    sendUserMessageNonStreaming
  }
}

export {
    queueProcessor,
    processingQueue,
    chunkQueue
}