<template>
  <div class="flex flex-col h-full">
    <!-- Chat Container -->
    <div class="flex-1 flex flex-col bg-base-100 rounded-lg shadow-lg border border-base-300 overflow-hidden">
      <!-- Messages Area -->
      <div
        ref="messagesContainer"
        class="flex-1 overflow-y-auto p-6 space-y-4"
      >
        <!-- Welcome Message -->
        <div v-if="messages.length === 0" class="text-center py-12">
          <div class="avatar placeholder">
            <div class="bg-neutral text-neutral-content rounded-full w-16 h-16 shadow-md">
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
          <div v-if="message.role === 'assistant'" class="avatar placeholder flex-shrink-0">
            <div class="bg-neutral text-neutral-content rounded-full w-8 h-8 shadow-md">
              <span class="text-sm">🤖</span>
            </div>
          </div>

          <!-- Message Bubble -->
          <div
            class="max-w-2xl shadow-md break-words"
            :class="message.role === 'user'
              ? 'bg-blue-500 text-white rounded-2xl rounded-br-sm px-4 py-3'
              : 'bg-base-200 text-base-content rounded-2xl rounded-bl-sm px-4 py-3'"
          >
            <!-- 渲染消息内容 -->
            <div
              v-if="message.role === 'assistant'"
              class="markdown-content prose prose-sm max-w-none"
              v-html="renderMessageContent(message.content)"
            ></div>
            <div v-else class="whitespace-pre-wrap">{{ message.content }}</div>

            <div
              v-if="message.timestamp"
              class="text-xs mt-2 opacity-70"
              :class="message.role === 'user' ? 'text-white/70' : 'text-base-content/50'"
            >
              {{ formatTime(message.timestamp) }}
            </div>
          </div>

          <!-- Avatar for User -->
          <div v-if="message.role === 'user'" class="avatar placeholder flex-shrink-0">
            <div class="bg-blue-500 text-white rounded-full w-8 h-8 shadow-md">
              <span class="text-sm">👤</span>
            </div>
          </div>
        </div>

        <!-- Processing Indicator -->
        <div v-if="isProcessing" class="flex gap-3 justify-start">
          <div class="avatar placeholder flex-shrink-0">
            <div class="bg-neutral text-neutral-content rounded-full w-8 h-8 shadow-md">
              <span class="text-sm">🤖</span>
            </div>
          </div>
          <div class="bg-base-200 text-base-content rounded-2xl rounded-bl-sm px-4 py-3 shadow-md">
            <div class="flex items-center gap-2">
              <span class="loading loading-dots loading-sm"></span>
              <span class="text-sm">{{ processingText }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="border-t border-base-300 bg-base-200 p-3">
        <div class="flex gap-3">
          <div class="flex-1">
            <textarea
              v-model="inputMessage"
              :disabled="isProcessing"
              placeholder="输入您的问题..."
              class="textarea textarea-bordered w-full resize-none shadow-md focus:shadow-lg transition-shadow bg-base-100 text-base-content"
              rows="2"
              @keydown.enter.prevent="handleEnterKey"
              @keydown.shift.enter.prevent="handleShiftEnter"
            />
          </div>
          <div class="flex flex-col gap-2">
            <button
              class="btn btn-primary shadow-md hover:shadow-lg transition-shadow"
              :disabled="!inputMessage.trim() || isProcessing"
              @click="sendMessage"
            >
              <svg
                v-if="!isProcessing"
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
              <span
                v-else
                class="loading loading-spinner loading-sm"
              />
            </button>

            <!-- 清空对话按钮 -->
            <div class="tooltip" data-tip="清空所有对话记录">
              <button
                class="btn btn-outline btn-xs shadow-sm"
                @click="clearConversation"
                :disabled="isProcessing"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
        <div class="text-xs text-base-content/50 mt-2 ml-1">
          按 Enter 发送，Shift + Enter 换行
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { useAgentStore } from '@/stores/agentStore'
import { renderMarkdown } from '@/utils/markdown'

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
  // 添加确认提示
  if (confirm('确定要清空所有对话记录吗？此操作无法撤销。')) {
    agentStore.clearMessages()
  }
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

// Markdown 渲染方法
const renderMessageContent = (content: string): string => {
  if (!content) return ''
  try {
    return renderMarkdown(content)
  } catch (error) {
    console.error('Markdown 渲染失败:', error)
    return content
  }
}

// Lifecycle
onMounted(() => {
  scrollToBottom()
})
</script>

<style scoped>
/* Markdown 内容样式 */
.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  font-weight: bold;
  margin-bottom: 0.5rem;
  margin-top: 1rem;
  color: var(--fallback-bc, oklch(var(--bc) / 0.9));
}

.markdown-content :deep(h1) { font-size: 1.25rem; }
.markdown-content :deep(h2) { font-size: 1.125rem; }
.markdown-content :deep(h3) { font-size: 1rem; }

.markdown-content :deep(p) {
  margin-bottom: 0.75rem;
  line-height: 1.625;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-bottom: 0.75rem;
  padding-left: 1.5rem;
}

.markdown-content :deep(li) {
  margin-bottom: 0.25rem;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid var(--fallback-pc, oklch(var(--pc) / 0.3));
  padding-left: 1rem;
  font-style: italic;
  color: var(--fallback-bc, oklch(var(--bc) / 0.8));
  margin-bottom: 0.75rem;
}

.markdown-content :deep(pre) {
  background-color: var(--fallback-n, oklch(var(--n)));
  color: var(--fallback-nc, oklch(var(--nc)));
  border-radius: 0.5rem;
  padding: 0.75rem;
  overflow-x: auto;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
}

.markdown-content :deep(code) {
  background-color: var(--fallback-n, oklch(var(--n) / 0.2));
  color: var(--fallback-nc, oklch(var(--nc)));
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.markdown-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
}

.markdown-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid var(--fallback-b2, oklch(var(--b2)));
  padding: 0.5rem 0.75rem;
  text-align: left;
}

.markdown-content :deep(th) {
  background-color: var(--fallback-b2, oklch(var(--b2)));
  font-weight: 600;
}

.markdown-content :deep(a) {
  color: var(--fallback-p, oklch(var(--p)));
  text-decoration: underline;
}

.markdown-content :deep(a:hover) {
  opacity: 0.8;
}

.markdown-content :deep(strong) {
  font-weight: bold;
  color: var(--fallback-bc, oklch(var(--bc) / 0.9));
}

.markdown-content :deep(em) {
  font-style: italic;
}

/* 代码高亮主题适配 */
.markdown-content :deep(.hljs) {
  background-color: var(--fallback-n, oklch(var(--n)));
  color: var(--fallback-nc, oklch(var(--nc)));
  border-radius: 0.5rem;
}

/* 用户消息气泡特殊样式 */
.bg-blue-500 .markdown-content {
  color: white;
}

.bg-blue-500 .markdown-content :deep(h1),
.bg-blue-500 .markdown-content :deep(h2),
.bg-blue-500 .markdown-content :deep(h3),
.bg-blue-500 .markdown-content :deep(h4),
.bg-blue-500 .markdown-content :deep(h5),
.bg-blue-500 .markdown-content :deep(h6) {
  color: white;
}

.bg-blue-500 .markdown-content :deep(strong) {
  color: white;
  font-weight: bold;
}

.bg-blue-500 .markdown-content :deep(a) {
  color: white;
}

.bg-blue-500 .markdown-content :deep(a:hover) {
  opacity: 0.8;
}

.bg-blue-500 .markdown-content :deep(p) {
  color: white;
}

.bg-blue-500 .markdown-content :deep(li) {
  color: white;
}

.bg-blue-500 .markdown-content :deep(blockquote) {
  color: rgba(255, 255, 255, 0.9);
  border-left-color: rgba(255, 255, 255, 0.3);
}
</style>