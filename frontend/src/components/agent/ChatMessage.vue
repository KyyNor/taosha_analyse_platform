<template>
  <div
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
      class="max-w-2xl px-4 py-3 rounded-lg shadow-sm"
      :class="message.role === 'user'
        ? 'bg-primary text-primary-content'
        : 'bg-base-200 text-base-content'"
    >
      <div class="whitespace-pre-wrap break-words">{{ message.content }}</div>
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
</template>

<script setup lang="ts">

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp?: Date
}

interface Props {
  message: ChatMessage
}

defineProps<Props>()

const formatTime = (timestamp: Date) => {
  return timestamp.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>