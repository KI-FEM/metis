import { defineStore } from 'pinia'
import { useStorage } from '@vueuse/core'
import type { Chat } from '@/types'
import { ref } from 'vue'
import { v4 as uuidv4 } from 'uuid';

const USER_ID_KEY = 'user_id'
const REQUIRED_DAYS = 5
const SESSION_THRESHOLD_MS = 30 * 60 * 1000 // 30 minutes in milliseconds
const FEEDBACK_ENTRIES_KEY = 'feedbackEntries' 
const TARGET_DATE = new Date(2025, 6, 22); // July 22nd, 2025 -> ST Eval beginning of end

export interface FeedbackEntry {
  correctness: number
  relevance: number
  complexity: number
  comment: string
  timestamp: string
}

export const useStudyStore = defineStore('study', () => {
  const userId = useStorage<string | null>(USER_ID_KEY, null)
  const chats = useStorage<Record<string, Chat[]>>('chats', {})
  const feedbackEntries = useStorage<FeedbackEntry[]>(FEEDBACK_ENTRIES_KEY, [])
  const showPostQuestionnaire = ref(false)

  const questionnaireUrls = {
    pre: 'https://bildungsportal.sachsen.de/umfragen/limesurvey/index.php/686373?lang=de',
    post: 'https://bildungsportal.sachsen.de/umfragen/limesurvey/index.php/739489?lang=de'
  }

  function saveFeedback(correctness: number, relevance: number, complexity: number, comment: string) {
    const newFeedback: FeedbackEntry = {
      correctness,
      relevance,
      complexity,
      comment,
      timestamp: new Date().toISOString()
    }
    feedbackEntries.value.push(newFeedback)
  }

  // Updates storage when the user uses the chat
  window.addEventListener('storage', (event) => {
    if (event.key === 'chats') {
      // Update the reactive chats variable when local storage changes
      chats.value = JSON.parse(event.newValue || '{}');
    }
  });

  function generateUserId() {
    userId.value = uuidv4();
  }

  function hasUserId(): boolean {
    return userId.value !== null && userId.value !== ""
  }

  function isDateAfterTarget(): boolean {
    const today = new Date();
    return today >= TARGET_DATE;
  }

  function generateCompressedUsageData(chatType: string = 'st'): string {
    const chatsOfType = chats.value[chatType]
    if (!chatsOfType || chatsOfType.length === 0) {
      return ''
    }

    // Collect and sort all valid timestamps
    const timestampsByDate: Record<string, Date[]> = {}

    chatsOfType.forEach(chat => {
      chat.messages.forEach(message => {
        if (!message.timestamp) return

        try {
          const timestamp = new Date(message.timestamp)
          if (!isNaN(timestamp.getTime())) {
            const dateStr = timestamp.toISOString().split('T')[0]
            if (!timestampsByDate[dateStr]) {
              timestampsByDate[dateStr] = []
            }
            timestampsByDate[dateStr].push(timestamp)
          }
        } catch (e) {
          console.warn('Invalid timestamp encountered:', message.timestamp)
        }
      })
    })

    // Generate compressed format: YYMMDD:HHMM-HHMM,HHMM-HHMM;YYMMDD...
    const compressedData: string[] = []

    Object.entries(timestampsByDate).forEach(([dateStr, timestamps]) => {
      timestamps.sort((a, b) => a.getTime() - b.getTime())

      const sessions: { start: Date; end: Date }[] = []
      let currentSession: { start: Date; end: Date } | null = null

      timestamps.forEach(timestamp => {
        if (!currentSession) {
          currentSession = { start: timestamp, end: timestamp }
        } else {
          const timeDiff = timestamp.getTime() - currentSession.end.getTime()

          if (timeDiff <= SESSION_THRESHOLD_MS) {
            currentSession.end = timestamp
          } else {
            sessions.push(currentSession)
            currentSession = { start: timestamp, end: timestamp }
          }
        }
      })

      if (currentSession) {
        sessions.push(currentSession)
      }

      if (sessions.length > 0) {
        // Format: YYMMDD
        const dateFormat = dateStr.slice(2).replace(/-/g, '')

        // Format: HHMM-HHMM;HHMM-HHMM
        const sessionTimes = sessions.map(session => {
          const startTime = session.start.toTimeString().slice(0, 5).replace(':', '')
          const endTime = session.end.toTimeString().slice(0, 5).replace(':', '')
          return `${startTime}-${endTime}`
        }).join(',')

        compressedData.push(`${dateFormat}:${sessionTimes}`)
      }
    })

    return compressedData.join(';')
  }

  function generateCompressedFeedbackData(): string {
    return feedbackEntries.value.map((entry) => {
      // Convert ISO timestamp to yymmdd:hhmm format
      const date = new Date(entry.timestamp)
      const yymmdd = date.toISOString().slice(2, 10).replace(/-/g, '')
      const hhmm = date.toTimeString().slice(0, 5).replace(':', '')
      const shortTimestamp = `${yymmdd}:${hhmm}`
      
      // URL-encode the comment to handle special characters
      const comment = entry.comment.replace(/;/g, ' semicolon ')
      const encodedComment = encodeURIComponent(comment)
      
      return `${shortTimestamp},${entry.correctness},${entry.relevance},${entry.complexity},${encodedComment}`
    }).join(';')
  }

  function getQuestionnaireUrl(questionnaireType: string): string {
    if (!Object.keys(questionnaireUrls).includes(questionnaireType)) {
      return ''
    }
    
    const baseUrl = questionnaireUrls[questionnaireType as keyof typeof questionnaireUrls]
    const uidParam = `&QID2=${userId.value}`
    
    // Add usage and feedback data only for post-questionnaire
    if (questionnaireType === 'post') {
      const usageData = generateCompressedUsageData()
      const feedbackData = generateCompressedFeedbackData()
      return `${baseUrl}${uidParam}&QND2=${usageData}&QFD2=${feedbackData}`
    }
    
    return `${baseUrl}${uidParam}`
  }

  function hasUserSentMessage(chatType: string = 'st'): boolean {
    const chatsOfType = chats.value[chatType];
    if (!chatsOfType || chatsOfType.length === 0) {
      console.warn(`No chats found for type: ${chatType}`);
      return false;
    }

    for (let i = chatsOfType.length - 1; i >= 0; i--) {
      const chat = chatsOfType[i];
      for (const message of chat.messages) {
        if (message.sender === 'user') {
          console.log(`User message found in chat ${chat.id} at ${message.timestamp}`);
          return true;
        }
      }
    }
    console.warn(`No user messages found in chats of type: ${chatType}`);
    return false;
  }

  return {
    userId,
    REQUIRED_DAYS,
    feedbackEntries,
    showPostQuestionnaire,
    saveFeedback,
    generateUserId,
    hasUserId,
    isDateAfterTarget,
    getQuestionnaireUrl,
    hasUserSentMessage,
  }
})
