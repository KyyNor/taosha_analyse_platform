<template>
  <div v-if="!clarity.is_clear" class="bg-amber-50 border border-amber-200 rounded-lg p-6 mb-6">
    <div class="flex items-start space-x-3">
      <ExclamationTriangleIcon class="w-6 h-6 text-amber-600 mt-0.5 flex-shrink-0" />
      <div class="flex-1">
        <h3 class="text-lg font-semibold text-amber-800 mb-2">
          问题可能不够清晰
        </h3>
        
        <div v-if="clarity.reason" class="mb-4">
          <p class="text-amber-700">
            <strong>原因：</strong>{{ clarity.reason }}
          </p>
        </div>

        <div v-if="clarity.suggestions && clarity.suggestions.length > 0">
          <h4 class="text-amber-800 font-medium mb-3">💡 改进建议</h4>
          <p class="text-amber-700 text-sm mb-3">请选择以下建议之一来完善您的查询：</p>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
            <button
              v-for="(suggestion, index) in clarity.suggestions"
              :key="index"
              @click="selectSuggestion(suggestion)"
              class="text-left p-3 bg-white border border-amber-200 rounded-lg hover:bg-amber-50 hover:border-amber-300 transition-all duration-200 hover:shadow-sm"
            >
              <div class="text-sm text-amber-800 font-medium">
                建议 {{ index + 1 }}
              </div>
              <div class="text-sm text-amber-700 mt-1">
                {{ suggestion }}
              </div>
            </button>
          </div>

          <details class="mt-4">
            <summary class="cursor-pointer text-sm text-amber-700 hover:text-amber-800">
              📋 查看所有建议文本
            </summary>
            <div class="mt-2 space-y-2">
              <div 
                v-for="(suggestion, index) in clarity.suggestions"
                :key="index"
                class="bg-white rounded p-2 text-sm text-amber-700 font-mono border border-amber-200"
              >
                {{ index + 1 }}. {{ suggestion }}
              </div>
            </div>
          </details>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import type { ClarityCheck } from '@/types'

// 定义组件属性
interface Props {
  clarity: ClarityCheck
}

defineProps<Props>()

// 定义事件
const emit = defineEmits<{
  selectSuggestion: [suggestion: string]
}>()

// 选择建议
const selectSuggestion = (suggestion: string) => {
  emit('selectSuggestion', suggestion)
}
</script>