/** TODO:
 * - Add a store for managing quiz state
 * - Generate HTML Markup for answer inputs dynamically
 * */

import { ref } from 'vue'
import { defineStore } from 'pinia'
import createClient from 'openapi-fetch';
import { useChatStore } from './chat';
import { useTopicsStore } from './topics';
import type { paths, components } from '@/types_api.ts'
import type { ChatCompletionsChunk, ChatMessage, ChatMessageFragment, ChatMessageMessage, Choice, ChoiceDelta, Quiz, QuizAnswer, QuizEvents, QuizQuestion } from "@/types.ts";



export const useQuizStore = defineStore('quiz', () => {
  const topicsStore = useTopicsStore();
  const chatStore = useChatStore();
  const client = createClient<paths>({baseUrl: import.meta.env.VITE_API_URL});
  const isLoading = ref<boolean>(false);
  const isError = ref<boolean>(false);
  const errorObject = ref<components['schemas']['ErrorReport'] | null>(null);

  const currentQuiz = ref<Quiz | null>(null); // The current quiz, which is worked on
  const showQuiz = ref<boolean>(false);

  // Streaming related
  const abortController = ref<AbortController | null>(null);
  const queueProcessor = ref<Promise<void> | null>(null)
  const processingQueue = ref(false)
  const chunkQueue = ref<ChatCompletionsChunk[]>([])
  const quizComplete = ref<boolean>(false)

  // Timeouts
  const eventTimeout = 3 * 60 * 1000 // time until error if no new chunk is received
  const notificationTimeout = 45 * 1000 // time until notification if no new chunk is received
  const notificationTimeoutHandle = ref<ReturnType<typeof setTimeout> | null>(null)
  const timeoutHandle = ref<ReturnType<typeof setTimeout> | null>(null)

  const loadQuestions = async (selectedCompetences: string[], quizId: string) => {
    isLoading.value = true;
    isError.value = false;
    showQuiz.value = true;
    if (!topicsStore.selectedTopic || !chatStore.currentChat) {
      isLoading.value = false;
      isError.value = true;
      throw new Error('No topic or chat selected');
    }
    const storage = {...chatStore.currentChat.storage};
    if (selectedCompetences && selectedCompetences.length > 0) {
      storage['selected_competences'] = selectedCompetences;
    }

    abortController.value = new AbortController()

    try {
      if (!chatStore.currentChat.quiz) {
        chatStore.currentChat.quiz = [];
      }

      chatStore.currentChat.quiz.push({
        id: quizId,
        title: '',
        description: '',
        questions: [],
        completed: false,
        score: [0, 0],
        events: [],
        state: 'loading',
        messages: []
      } as Quiz);

      if (showQuiz.value) currentQuiz.value = chatStore.currentChat.quiz.find(q => q.id === quizId) ?? null;

      const response = await fetch(`${import.meta.env.VITE_API_URL}/topic/${topicsStore.selectedTopic.endpoint}/quiz`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            id: quizId,
            response_preferences: chatStore.responsePreferences,
            storage: storage,
            language: chatStore.currentChat.language,
            chat_history: chatStore.currentChat.messages.map(m => {
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
            llm_purpose: chatStore.getSelectedLLMPurpose(),
            streaming: false
          }),
        signal: abortController.value.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const contentType = response.headers.get('content-type')
      
      if (contentType?.includes('application/json')) {
        // Handle non-streaming response (full JSON)
        const data = await response.json() as components['schemas']['QuizModel'];
        const receivedQuiz = data as Quiz;
        if (!receivedQuiz.questions || receivedQuiz.questions.length === 0) {
          isLoading.value = false;
          isError.value = true;
          console.error('[chat.createQuizFragment] No quiz questions received from API');
          return;
        }

        // save quiz to current chat
        const foundQuiz = chatStore.currentChat.quiz.find(q => q.id === quizId);
        if (foundQuiz) {
          foundQuiz.questions = receivedQuiz.questions ?? []
          foundQuiz.completed = false
          foundQuiz.title = receivedQuiz.title ?? foundQuiz.title
          foundQuiz.description = receivedQuiz.description ?? foundQuiz.description
          foundQuiz.score = receivedQuiz.score ?? foundQuiz.score

          if (showQuiz.value) currentQuiz.value = foundQuiz;
        } else {
          chatStore.currentChat.quiz.push(receivedQuiz);
          if (showQuiz.value) currentQuiz.value = receivedQuiz;
        }


      } else {
        // Handle streaming response (SSE)
        await processQuizStreamedResponse(response, quizId);
      }
    } catch (error) {
      console.error('[QuizOverlay.loadQuiz] Error during API call: ', error);
    }
    isLoading.value = false;
    isError.value = false;
    return;
  }

  async function processQuizStreamedResponse(response: Response, quizId: string) {
    queueProcessor.value = null
    chunkQueue.value = []

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) throw new Error('No reader available')

    let concatenatedEvents = []
    while (!quizComplete.value) {
      timeoutHandle.value = setTimeout(() => {
        if (quizComplete.value || chatStore.currentChat?.quiz?.find(q => q.id === quizId)?.completed) return
        console.error('Timeout waiting for next event chunk')
        chunkQueue.value.push({
          id: quizId,
          choices: [{
            delta: {
              instructions: ['quiz_generation_errored: {"timestamp": "' + new Date().toISOString() + '", "event": "quiz_generation_errored", "additional_info": {}}']
            } as ChoiceDelta
          } as Choice],
          created: new Date(Date.now()).toISOString(),
        } as ChatCompletionsChunk)
      }, eventTimeout)
      notificationTimeoutHandle.value = setTimeout(() => {
        if (quizComplete.value || chatStore.currentChat?.quiz?.find(q => q.id === quizId)?.completed) return
        console.warn('No event chunk received for a while, notifying user...')
        chunkQueue.value.push({
          id: quizId,
          choices: [{
            delta: {
              instructions: ['info: {"timestamp": "' + new Date().toISOString() + '", "event": "quiz_generation_delayed", "additional_info": {"message": "The quiz generation is taking longer than expected. Please wait..."}}']
            } as ChoiceDelta
          } as Choice],
          created: new Date(Date.now()).toISOString(),
        } as ChatCompletionsChunk)
      }, notificationTimeout)
      const {done, value} = await reader.read()
      if (done) break

      const eventsChunk = decoder.decode(value)
      const events = eventsChunk.split('\n\n').filter(e => e.trim())
      
      const processEvent = (event: string) => {
        if (notificationTimeoutHandle.value) clearTimeout(notificationTimeoutHandle.value)
        if (timeoutHandle.value) clearTimeout(timeoutHandle.value)

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
          quizComplete.value = true
        }
        timeoutHandle.value = setTimeout(() => {
          if (quizComplete.value || chatStore.currentChat?.quiz?.find(q => q.id === quizId)?.completed) return
          console.error('Timeout waiting for next event chunk')
          chunkQueue.value.push({
            id: quizId,
            choices: [{
              delta: {
                instructions: ['quiz_generation_errored: {"timestamp": "' + new Date().toISOString() + '", "event": "quiz_generation_errored", "additional_info": {}}']
              } as ChoiceDelta
            } as Choice],
            created: new Date(Date.now()).toISOString(),
          } as ChatCompletionsChunk)
          abortController.value?.abort()
          quizComplete.value = true
          isError.value = true
          errorObject.value = {
            error: 'Timeout waiting for next event chunk. Please try again later.',
            context: {}
          } as components['schemas']['ErrorReport']
        }, eventTimeout)
        notificationTimeoutHandle.value = setTimeout(() => {
          if (quizComplete.value || chatStore.currentChat?.quiz?.find(q => q.id === quizId)?.completed) return
          console.warn('No event chunk received for a while, notifying user...')
          chunkQueue.value.push({
            id: quizId,
            choices: [{
              delta: {
                instructions: ['info: {"timestamp": "' + new Date().toISOString() + '", "event": "quiz_generation_delayed", "additional_info": {"message": "The quiz generation is taking longer than expected. Please wait..."}}']
              } as ChoiceDelta
            } as Choice],
            created: new Date(Date.now()).toISOString(),
          } as ChatCompletionsChunk)
        }, notificationTimeout)
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
        startQuizQueueProcessor()
      }
    }

    if (notificationTimeoutHandle.value) clearTimeout(notificationTimeoutHandle.value)
    if (timeoutHandle.value) clearTimeout(timeoutHandle.value)

    return currentQuiz.value;
  }

  /**
   * Start processsing chunks from the chunk queue asynchronously
   * @returns 
   */
  async function startQuizQueueProcessor() {
    if (queueProcessor.value) return

    queueProcessor.value = (async () => {
      while (true) {
        if (chunkQueue.value.length > 0) {
          processingQueue.value = true
          const chunk = chunkQueue.value.shift()
          if (chunk) {
            const finished = readQuizChunk(chunk)
            if (finished) {
              quizComplete.value = true
            }
          }
        } else {
          processingQueue.value = false
          // Small delay when queue is empty to prevent busy waiting
          await new Promise(resolve => setTimeout(resolve, 10))
          // If queue has been empty for a while and quiz is complete, stop processor
          if (quizComplete.value && chunkQueue.value.length === 0) {
            queueProcessor.value = null
            break
          }
        }
      }
    })()

    queueProcessor.value = null
  }


  /**
   * Read and process a chunk of quiz events
   * @param chunk the chunk to read and process
   * @returns true if the chunk was processed successfully, false otherwise
   */
  function readQuizChunk(chunk: ChatCompletionsChunk) {
    const choice = chunk.choices[0]!
    const delta = choice.delta ?? ({} as Partial<typeof choice['delta']>)
    const chunk_id = chunk.id

    // get the quiz that matches the chunk id
    const quiz = chatStore.currentChat?.quiz?.find(q => q.id === chunk_id)
    if (!quiz || chunk.choices.length === 0 || !chatStore.currentChat){
      console.warn('No matching quiz found for chunk id:', chunk_id)
      return false
    } 

    if (delta.instructions?.length) {
      for (const instruction of delta.instructions) {
        const addEvent = (event: QuizEvents) => {
          if (!quiz.events) {
              quiz.events = []
            }
          quiz.events = [...quiz.events, event]
        }

        if (instruction.includes('info: ')) {
          const eventString = instruction.replace('info: ', '')
          try {
            const event = JSON.parse(eventString) as QuizEvents
            console.log(' \\- Received quiz event:', event)
            addEvent(event)
          } catch (e) {
            console.error(' \\- Failed to parse event JSON:', e, eventString)
          }
        } else if (instruction.includes('quiz_complete: ')) {
          const quizString = instruction.replace('quiz_complete: ', '')
          try {
            const quizEvent = JSON.parse(quizString) as QuizEvents
            console.log(' \\- Received quiz_complete event:', quizEvent)
            if (quizEvent.additional_info?.quiz) {
              const receivedQuiz = quizEvent.additional_info.quiz as Quiz
              if (!receivedQuiz.questions || receivedQuiz.questions.length === 0) {
                isLoading.value = false;
                isError.value = true;
                console.error('[chat.createQuizFragment] No quiz questions received from API');
                return '';
              }
              quiz.questions = receivedQuiz.questions ?? []
              quiz.completed = false
              quiz.title = receivedQuiz.title ?? quiz.title
              quiz.description = receivedQuiz.description ?? quiz.description
              quiz.score = receivedQuiz.score ?? quiz.score

              if (showQuiz.value) currentQuiz.value = quiz;
              quiz.state = 'ready'

              if (notificationTimeoutHandle.value) clearTimeout(notificationTimeoutHandle.value)
              if (timeoutHandle.value) clearTimeout(timeoutHandle.value)

              isLoading.value = false;
              isError.value = false;
            }
            addEvent(quizEvent)
          } catch (e) {
            console.error(' \\- Failed to parse quiz JSON:', e, quizString)
          }
        } else if (instruction.includes('quiz_generation_errored: ')) {
          const errorString = instruction.replace('quiz_generation_errored: ', '')
          try {
            const errorEvent = JSON.parse(errorString) as QuizEvents
            console.log(' \\- Received quiz_generation_errored event:', errorEvent)
            quiz.state = 'error'
            abortController.value?.abort()
            isLoading.value = false;
            quizComplete.value = true
            isError.value = true
            errorObject.value = {
              error: 'Timeout waiting for next event chunk. Please try again later.',
              context: {}
            } as components['schemas']['ErrorReport']
            addEvent(errorEvent)
          } catch (e) {
            console.error(' \\- Failed to parse error JSON:', e, errorString)
          }
        }
      }
    }

    if (choice.finish_reason === 'stop') {
      isLoading.value = false
      return true
    }

    return false
  }


  const openQuiz = (quizId: string) => {
    if (currentQuiz.value && quizId === currentQuiz.value.id && showQuiz.value) {
      return;
    }
    closeQuiz();
    showQuiz.value = true;
    isLoading.value = true;
    isError.value = false;
    const newQuiz = getQuiz(quizId);
    if (!newQuiz) {
      console.error('[quiz.openQuiz] Couldn\'t open quiz. No quiz found...');
      isError.value = true;
      isLoading.value = false;
      return;
    }

    currentQuiz.value = newQuiz;
    isLoading.value = false;
  }

  const closeQuiz = () => {
    showQuiz.value = false;
    isLoading.value = false;
    isError.value = false;
    currentQuiz.value = null;
  }

  const updateAnswer = (quizId: string, questionId: number, answer: QuizAnswer) => {
    if (!quizId) {
      console.error('[quiz.updateAnswers] Couldn\'t send message. No chat/topic found...');
      return;
    }

    const quiz = getQuiz(quizId);
    if (!quiz) {
      console.error('[quiz.updateAnswers] Couldn\'t update answers. No quiz found...');
      return;
    }

    const question = quiz.questions.find((q) => q.id === questionId);
    if (!question) {
      console.error('[quiz.updateAnswers] Couldn\'t update answers. Question not found in quiz...');
      return;
    }

    question.answer = answer;
    console.log('Updated answer for question', questionId, 'in quiz', quizId, 'to', answer);
  };

  const evaluateAnswer = async (quizId: string, question: QuizQuestion, userAnswer: QuizAnswer) => {
    if (!topicsStore.selectedTopic || !chatStore.currentChat) {
      console.error('[quiz.evaluateAnswer] No topic or chat selected');
      return null;
    }
    if (userAnswer === undefined || userAnswer === null) {
      console.error('[quiz.evaluateAnswer] No answer provided');
      return null;
    }

    try {
      const { data, error: fetchError } = await client.POST('/topic/{topic}/quiz/evaluate', {
        params: {
          path: {
            topic: topicsStore.selectedTopic.endpoint,
          }
        },
        body: {
          id: quizId,
          question: question,
          user_answer: userAnswer,
          response_preferences: chatStore.responsePreferences,
          storage: chatStore.currentChat.storage,
          language: chatStore.currentChat.language,
          chat_history: chatStore.currentChat.messages,
          llm_purpose: chatStore.getSelectedLLMPurpose(),
          streaming: false
        }
      });

      if (fetchError) {
        console.error('[quiz.evaluateAnswer] Error evaluating answer:', fetchError);
        return null;
      }

      // Update the question with evaluation results
      const quiz = getQuiz(quizId);
      if (quiz) {  // TODO: is this not passed or the next one? anyway, we don't get into the :166 console log
        const q = quiz.questions.find((q) => q.id === question.id);
        if (q) {
          q.answered = true;
          q.score = [data.score, data.max_score];
          // q.feedback = data.feedback;
          // q.solution = data.solution;
          // q.is_correct = data.is_correct;

          // Update total quiz score
          quiz.score = [
            quiz.questions.reduce((acc: number, question) => { acc += question.score?.[0] || 0; return acc }, 0),
            quiz.questions.reduce((acc: number, question) => { acc += question.score?.[1] || 0; return acc }, 0)
          ];          
        }
      }

      return data;
    } catch (error) {
      console.error('[quiz.evaluateAnswer] Error during API call:', error);
      return null;
    }
  };

  async function evaluateQuizCompletion(quiz: Quiz) {
    if (!topicsStore.selectedTopic || !chatStore.currentChat) {
      console.error('[quiz.evaluateQuizCompletion] No topic or chat selected');
      return;
    }
    console.log('[quiz.evaluateAnswer] Marking quiz as completed! Final score:', quiz.score);

    quiz.completed = true;    
    quiz.state = 'complete'

    // Force reactivity by reassigning the quiz array
    // This ensures useStorage detects the change and updates localStorage
    if (chatStore.currentChat && chatStore.currentChat.quiz) {
      chatStore.currentChat.quiz = [...chatStore.currentChat.quiz];
    }

    for (const question of quiz.questions) {
      if (question.type == 'multiple-choice' && typeof question.solution[0] === 'string') {
        question.solution = question.solution.map(sol => question.answer?.findIndex(ans => ans == sol) ?? -1)
      }
    }
    const {data, error: fetchError} = await client.POST('/topic/{topic}/quiz/complete', {
      params: {
        path: {
          topic: topicsStore.selectedTopic.endpoint
        }
      },
      body: {
        id: quiz.id,
        quiz: quiz,
        response_preferences: chatStore.responsePreferences,
        storage: chatStore.currentChat.storage,
        language: chatStore.currentChat.language,
        chat_history: chatStore.currentChat.messages,
        llm_purpose: chatStore.getSelectedLLMPurpose(),
        streaming: false
      }
    });
    if (fetchError) {
      throw fetchError
    }
    if (!data) {
      throw new Error('No data received from API.')
    }
    if (data.error) {
      chatStore.errorObject = data.error
      throw new Error(`Error from API: ${JSON.stringify(data.error, null, 2)}`)
    }
    chatStore.currentChat.storage = {...chatStore.currentChat.storage, ...data.storage};

    if (data.messages.length > 0) {
      quiz.messages = quiz.messages.concat(
        ...data.messages.map(message => ({
          ...message,
          complete: true,
          timestamp: new Date().toISOString()
        } as ChatMessageMessage))
      );
    }
  }

  const updateScore = (quizId: string, questionId: number, score: number) => {
    if (!quizId) {
      console.error('[quiz.updateAnswers] Couldn\'t send score. No chat/topic found...');
      return;
    }

    const quiz = getQuiz(quizId);
    if (!quiz) {
      console.error('[quiz.updateAnswers] Couldn\'t update score. No quiz found...');
      return;
    }

    const question = quiz.questions.find(q => q.id === questionId);
    if (!question) {
      console.error('[quiz.updateAnswers] Couldn\'t update score. Question not found in quiz...');
      return;
    }

    question.score[0] = score;
    quiz.score = [
      quiz.questions.reduce((acc: number, question) => { acc += question.score?.[0] || 0; return acc }, 0),
      quiz.questions.reduce((acc: number, question) => { acc += question.score?.[1] || 0; return acc }, 0)
    ];
  };

  const createQuizFragment = async (selectedCompetences: string[]) => {
    isLoading.value = true;
    isError.value = false;
    if (!chatStore.currentChat || !topicsStore.selectedTopic) {
      isLoading.value = false;
      isError.value = true;
      console.error('[chat.createQuizFragment] Couldn\'t send message. No chat/topic found...');
      return '';
    }
    const quizId = crypto.randomUUID();

    chatStore.currentChat.messages.push({
      fragment: true,
      type: 'assistant',
      content: '',
      quizId: quizId,
      buttons: [],
      meta_information: {} as ChatMessage['meta_information'],
      state: 'loading',
      timestamp: new Date().toISOString()
    } as ChatMessageFragment)
    await loadQuestions(selectedCompetences, quizId);
    if (showQuiz.value) openQuiz(quizId)
  }

  function getQuiz(quizId: string): Quiz | null {
    if (!chatStore.currentChat || !topicsStore.selectedTopic) {
      console.error('[chat.getQuiz] Couldn\'t send message. No chat/topic found...');
      return null;
    }
    if (!quizId) {
      console.error('[chat.getQuiz] No quiz ID provided');
      return null;
    }

    if (!chatStore.currentChat.quiz) {
      console.error('[chat.getQuiz] Quiz array not initialized');
      return null;
    }
    
    const foundQuiz = chatStore.currentChat.quiz.find(quiz => quiz.id === quizId) ?? null;
    console.log('[quiz.getQuiz] Retrieved quiz:', quizId, 'completed:', foundQuiz?.completed);
    return foundQuiz;
  }

  function updateQuizFragment(quizId: string, questions: QuizQuestion[]) {
    if (!chatStore.currentChat || !topicsStore.selectedTopic) {
      console.error('[chat.updateQuizFragment] Couldn\'t send message. No chat/topic found...');
      return;
    }
    if (!quizId) {
      console.error('[chat.updateQuizFragment] No quiz ID provided');
      return;
    }

    const quiz = getQuiz(quizId);
    if (!quiz) {
      console.error('[chat.updateQuizFragment] No quiz with provided quiz ID found');
      return;
    }

    quiz.questions = questions;
    quiz.score = [
      questions.reduce((acc, question) => { acc += question.score[0]; return acc }, 0),
      questions.reduce((acc, question) => { acc += question.score[1]; return acc }, 0)
    ]
  }

  function deleteQuizFragment(quizId: string) {
    if (!chatStore.currentChat || !topicsStore.selectedTopic) {
      console.error('[chat.deleteQuizFragment] Couldn\'t send message. No chat/topic found...');
      return;
    }
    if (!quizId) {
      console.error('[chat.deleteQuizFragment] No quiz ID provided');
      return;
    }

    if (!chatStore.currentChat.quiz) {
      console.error('[chat.deleteQuizFragment] Quiz array not initialized');
      return;
    }

    const quizIdx = chatStore.currentChat.quiz.findIndex(quiz => quiz.id === quizId);
    if (quizIdx === -1) {
      console.error('[chat.deleteQuizFragment] No quiz with provided quiz ID found');
      return;
    }
    chatStore.currentChat.quiz.splice(quizIdx, 1);
  }

  return {
    currentQuiz,
    isLoading,
    isError,
    showQuiz,
    createQuizFragment,
    deleteQuizFragment,
    updateQuizFragment,
    updateAnswer,
    evaluateAnswer,
    updateScore,
    evaluateQuizCompletion,
    openQuiz,
    closeQuiz,
    getQuiz
  };
});
