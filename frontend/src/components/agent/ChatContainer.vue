<template>
  <div class="flex-1 flex flex-col">
    <!-- Messages Area -->
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
      <ChatMessage
        v-for="message in messages"
        :key="message.id"
        :message="message"
      />

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
    <ChatInput
      :disabled="isProcessing"
      @send="handleSendMessage"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import ChatMessage from './ChatMessage.vue'
import ChatInput from './ChatInput.vue'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp?: Date
}

interface Props {
  messages: ChatMessage[]
  isProcessing: boolean
  processingText: string
}

interface Emits {
  (e: 'send-message', message: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const messagesContainer = ref<HTMLElement>()

const handleSendMessage = (message: string) => {
  emit('send-message', message)
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// Watch for new messages and scroll to bottom
watch(
  () => props.messages.length,
  () => {
    scrollToBottom()
  }
)

// Watch for processing state changes
watch(
  () => props.isProcessing,
  () => {
    scrollToBottom()
  }
)

onMounted(() => {
  scrollToBottom()
})
</script>