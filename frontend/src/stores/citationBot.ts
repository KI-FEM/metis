import { defineStore } from 'pinia'

type Deadline = {
  name: string
  date: string
}

type CitationBotContext = {
  title: string
  task: string
  deadlines: Deadline[]
  additionalInfo: string
}

const defaultContext: CitationBotContext = {
  title: '<leer>',
  task: '<leer>',
  deadlines: [],
  additionalInfo: '<leer>',
}

export const useCitationBotStore = defineStore('citationBot', {
  state: () => ({
    context: loadStoredContext(),
  }),
  
  actions: {
    updateTitle(title: string) {
      this.context.title = title
      this.saveContext()
    },
    
    updateTask(task: string) {
      this.context.task = task
      this.saveContext()
    },
    
    updateAdditionalInfo(info: string) {
      this.context.additionalInfo = info
      this.saveContext()
    },
    
    addDeadline(deadline: Deadline) {
      this.context.deadlines.push(deadline)
      this.saveContext()
    },
    
    removeDeadline(index: number) {
      this.context.deadlines.splice(index, 1)
      this.saveContext()
    },
    
    updateDeadline(index: number, deadline: Deadline) {
      this.context.deadlines[index] = deadline
      this.saveContext()
    },
    
    saveContext() {
      localStorage.setItem('citation_bot_context', JSON.stringify(this.context))
    },
  },
})

function loadStoredContext(): CitationBotContext {
  const storedContext = localStorage.getItem('citation_bot_context')
  if (storedContext) {
    return JSON.parse(storedContext)
  }
  return defaultContext
} 