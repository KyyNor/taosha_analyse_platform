import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export const useAgentStore = defineStore('agent', () => {
  // State
  const messages = ref<ChatMessage[]>([])
  const isProcessing = ref(false)
  const processingText = ref('正在思考中...')
  const currentResponse = ref('')
  const currentSessionId = ref<string | null>(null)
  const currentUserId = ref<string>('api_user')

  // Getters
  const conversationHistory = computed(() => {
    return messages.value.map(msg => ({
      role: msg.role,
      content: msg.content
    }))
  })

  const hasMessages = computed(() => messages.value.length > 0)

  // Actions
  const addMessage = (role: 'user' | 'assistant', content: string) => {
    const message: ChatMessage = {
      id: generateId(),
      role,
      content,
      timestamp: new Date()
    }
    messages.value.push(message)
    return message
  }

  const sendMessage = async (userMessage: string) => {
    if (isProcessing.value || !userMessage.trim()) return

    // Add user message
    addMessage('user', userMessage)

    // Set processing state
    isProcessing.value = true
    processingText.value = '正在思考中...'
    currentResponse.value = ''

    try {
      // Import agent service dynamically to avoid circular dependencies
      const { agentService } = await import('@services/api/agentService')

      // Start streaming response
      const response = await agentService.chatStream({
        message: userMessage,
        session_id: currentSessionId.value || undefined,
        user_id: currentUserId.value,
        conversation_history: conversationHistory.value.slice(0, -1) // Exclude current user message
      })

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('无法获取响应流')
      }

      // Add empty assistant message for streaming
      addMessage('assistant', '')

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              switch (data.type) {
                case 'start':
                  processingText.value = '正在生成回答...'
                  // 提取并保存session_id
                  if (data.session_id) {
                    currentSessionId.value = data.session_id
                  }
                  break
                case 'content':
                  currentResponse.value += data.content
                  // Update the assistant message content
                  const lastMessage = messages.value[messages.value.length - 1]
                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.content = currentResponse.value
                  }
                  break
                case 'end':
                  processingText.value = '回答完成'
                  break
                case 'error':
                  throw new Error(data.content)
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', line, e)
            }
          }
        }
      }

    } catch (error) {
      console.error('Error sending message:', error)

      // Add error message
      addMessage('assistant', `抱歉，处理您的请求时出现错误：${error instanceof Error ? error.message : '未知错误'}`)

    } finally {
      // Reset processing state
      isProcessing.value = false
      processingText.value = '正在思考中...'
      currentResponse.value = ''
    }
  }

  const clearMessages = () => {
    messages.value = []
    currentResponse.value = ''
    currentSessionId.value = null  // 清理session_id，下次请求将生成新的
  }

  const generateId = () => {
    return Date.now().toString(36) + Math.random().toString(36).substr(2)
  }

  return {
    // State
    messages,
    isProcessing,
    processingText,
    currentResponse,
    currentSessionId,
    currentUserId,

    // Getters
    conversationHistory,
    hasMessages,

    // Actions
    sendMessage,
    addMessage,
    clearMessages
  }
})