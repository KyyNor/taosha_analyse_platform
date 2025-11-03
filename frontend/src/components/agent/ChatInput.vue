<template>
  <div class="border-t border-base-300 bg-base-200 px-6 py-4">
    <div class="flex gap-3">
      <div class="flex-1">
        <textarea
          v-model="inputMessage"
          :disabled="disabled"
          :placeholder="placeholder"
          class="textarea textarea-bordered w-full resize-none focus:outline-none focus:ring-2 focus:ring-primary"
          rows="3"
          @keydown.enter.prevent="handleEnterKey"
          @keydown.shift.enter.prevent="handleShiftEnter"
        ></textarea>
      </div>
      <div class="flex flex-col gap-2">
        <button
          class="btn btn-primary h-auto min-h-0 px-4 py-2"
          @click="handleSend"
          :disabled="!canSend"
        >
          <svg v-if="!disabled" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  disabled?: boolean
  placeholder?: string
}

interface Emits {
  (e: 'send', message: string): void
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  placeholder: '输入您的问题...'
})

const emit = defineEmits<Emits>()

const inputMessage = ref('')

const canSend = computed(() => {
  return inputMessage.value.trim() && !props.disabled
})

const handleSend = () => {
  if (!canSend.value) return

  const message = inputMessage.value.trim()
  inputMessage.value = ''
  emit('send', message)
}

const handleEnterKey = () => {
  handleSend()
}

const handleShiftEnter = () => {
  inputMessage.value += '\n'
}
</script>