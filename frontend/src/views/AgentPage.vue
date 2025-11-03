<template>
  <div class="h-full flex flex-col bg-base-100">
    <!-- Header -->
    <div class="bg-base-200 border-b border-base-300 px-6 py-4">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-base-content">淘沙 Agent</h1>
          <p class="text-sm text-base-content/70 mt-1">基于LangChain的智能对话助手</p>
        </div>
        <div class="flex gap-2">
          <button
            class="btn btn-outline btn-sm"
            @click="clearConversation"
            :disabled="isProcessing"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            清空对话
          </button>
        </div>
      </div>
    </div>

    <!-- Chat Container -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Messages Area -->
      <div class="flex-1 flex flex-col">
        <div
          ref="messagesContainer"
          class="flex-1 overflow-y-auto px-6 py-4 space-y-4"
        >
          <!-- Welcome Message -->
          <div v-if="messages.length === 0" class="text-center py-12">
            <div class="avatar placeholder">
              <div class="bg-neutral text-neutral-content rounded-full w-16 h-16">
                <span class="text-2xl">🤖</span>
              </div>
            </div>
            <h3 class="text-lg font-semibold mt-4 text-base-content">欢迎使用淘沙 Agent</h3>
            <p class="text-base-content/70 mt-2">我是您的智能助手，可以帮助您进行数据分析和问答</p>
          </div>

          <!-- Messages -->
          <div
            v-for="message in messages"
            :key="message.id"
            class="flex gap-3"
            :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <!-- Avatar for Assistant -->
            <div v-if="message.role === 'assistant'" class="avatar placeholder">
              <div class="bg-neutral text-neutral-content rounded-full w-8 h-8">
                <span class="text-sm">🤖</span>
              </div>
            </div>

            <!-- Message Bubble -->
            <div
              class="max-w-2xl px-4 py-3 rounded-lg"
              :class="message.role === 'user'
                ? 'bg-primary text-primary-content'
                : 'bg-base-200 text-base-content'"
            >
              <div class="whitespace-pre-wrap">{{ message.content }}</div>
              <div
                v-if="message.timestamp"
                class="text-xs mt-2 opacity-70"
              >
                {{ formatTime(message.timestamp) }}
              </div>
            </div>

            <!-- Avatar for User -->
            <div v-if="message.role === 'user'" class="avatar placeholder">
              <div class="bg-primary text-primary-content rounded-full w-8 h-8">
                <span class="text-sm">👤</span>
              </div>
            </div>
          </div>

          <!-- Processing Indicator -->
          <div v-if="isProcessing" class="flex gap-3 justify-start">
            <div class="avatar placeholder">
              <div class="bg-neutral text-neutral-content rounded-full w-8 h-8">
                <span class="text-sm">🤖</span>
              </div>
            </div>
            <div class="bg-base-200 text-base-content px-4 py-3 rounded-lg">
              <div class="flex items-center gap-2">
                <span class="loading loading-dots loading-sm"></span>
                <span class="text-sm">{{ processingText }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Input Area -->
        <div class="border-t border-base-300 bg-base-200 px-6 py-4">
          <div class="flex gap-3">
            <div class="flex-1">
              <textarea
                v-model="inputMessage"
                :disabled="isProcessing"
                placeholder="输入您的问题..."
                class="textarea textarea-bordered w-full resize-none"
                rows="3"
                @keydown.enter.prevent="handleEnterKey"
                @keydown.shift.enter.prevent="handleShiftEnter"
              ></textarea>
            </div>
            <div class="flex flex-col gap-2">
              <button
                class="btn btn-primary"
                @click="sendMessage"
                :disabled="!inputMessage.trim() || isProcessing"
              >
                <svg v-if="!isProcessing" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
                <span v-else class="loading loading-spinner loading-sm"></span>
              </button>
            </div>
          </div>
          <div class="text-xs text-base-content/50 mt-2">
            按 Enter 发送，Shift + Enter 换行
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { useAgentStore } from '@/stores/agentStore'

// Store
const agentStore = useAgentStore()

// Refs
const messagesContainer = ref<HTMLElement>()
const inputMessage = ref('')

// Computed
const messages = computed(() => agentStore.messages)
const isProcessing = computed(() => agentStore.isProcessing)
const processingText = computed(() => agentStore.processingText)

// Methods
const sendMessage = async () => {
  if (!inputMessage.value.trim() || isProcessing.value) return

  const message = inputMessage.value.trim()
  inputMessage.value = ''

  await agentStore.sendMessage(message)
  await scrollToBottom()
}

const clearConversation = () => {
  agentStore.clearMessages()
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const formatTime = (timestamp: Date) => {
  return timestamp.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

const handleEnterKey = () => {
  sendMessage()
}

const handleShiftEnter = () => {
  inputMessage.value += '\n'
}

// Lifecycle
onMounted(() => {
  scrollToBottom()
})
</script>