<template>
  <div class="bg-white rounded-lg border border-slate-200 shadow-sm">
    <div class="px-6 py-4 border-b border-slate-200 bg-slate-50">
      <h3 class="text-lg font-semibold text-slate-800">查询执行日志</h3>
      <p class="text-sm text-slate-500 mt-1">详细的查询执行过程和步骤</p>
    </div>

    <div class="p-6 space-y-4 max-h-96 overflow-y-auto">
      <div v-if="logs.length === 0" class="text-center text-slate-500 py-8">
        暂无执行日志
      </div>

      <div v-else v-for="(log, index) in logs" :key="index" class="border border-slate-200 rounded-lg p-4">
        <!-- 步骤标题 -->
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center space-x-2">
            <div 
              :class="[
                'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium',
                log.success ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
              ]"
            >
              {{ index + 1 }}
            </div>
            <h4 class="font-medium text-slate-800">{{ log.step }}</h4>
            <div 
              :class="[
                'px-2 py-1 rounded text-xs font-medium',
                log.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              ]"
            >
              {{ log.success ? '成功' : '失败' }}
            </div>
          </div>
          <div class="text-xs text-slate-500">
            {{ formatTimestamp(log.timestamp) }}
          </div>
        </div>

        <!-- 输入输出 -->
        <div v-if="log.input_data || log.model_output" class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
          <div v-if="log.input_data">
            <label class="block text-xs font-medium text-slate-600 mb-1">输入数据</label>
            <div class="bg-slate-50 rounded p-3 text-sm font-mono text-slate-700 max-h-32 overflow-y-auto">
              {{ log.input_data }}
            </div>
          </div>
          
          <div v-if="log.model_output">
            <label class="block text-xs font-medium text-slate-600 mb-1">模型输出</label>
            <div class="bg-slate-50 rounded p-3 text-sm font-mono text-slate-700 max-h-32 overflow-y-auto">
              {{ log.model_output }}
            </div>
          </div>
        </div>

        <!-- 错误信息 -->
        <div v-if="log.error" class="mb-3">
          <div class="bg-red-50 border border-red-200 rounded p-3">
            <div class="flex items-start space-x-2">
              <ExclamationTriangleIcon class="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
              <div>
                <div class="text-sm font-medium text-red-800">错误信息</div>
                <div class="text-sm text-red-700 mt-1">{{ log.error }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 提示词 -->
        <div v-if="log.prompt" class="mt-3">
          <button
            @click="togglePrompt(index)"
            class="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-800 transition-colors duration-200"
          >
            <ChevronRightIcon 
              :class="[
                'w-4 h-4 transition-transform duration-200',
                expandedPrompts.has(index) ? 'rotate-90' : ''
              ]" 
            />
            <span>查看提示词</span>
          </button>
          
          <div v-if="expandedPrompts.has(index)" class="mt-2">
            <div class="bg-slate-50 rounded p-3 text-sm font-mono text-slate-700 max-h-48 overflow-y-auto whitespace-pre-wrap">
              {{ log.prompt }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ExclamationTriangleIcon, ChevronRightIcon } from '@heroicons/vue/24/outline'
import type { QueryLog } from '@/types'

// 定义组件属性
interface Props {
  logs: QueryLog[]
}

defineProps<Props>()

// 响应式数据
const expandedPrompts = ref<Set<number>>(new Set())

// 切换提示词显示
const togglePrompt = (index: number) => {
  if (expandedPrompts.value.has(index)) {
    expandedPrompts.value.delete(index)
  } else {
    expandedPrompts.value.add(index)
  }
}

// 格式化时间戳
const formatTimestamp = (timestamp: string) => {
  if (!timestamp) return ''
  try {
    return new Date(timestamp).toLocaleTimeString('zh-CN')
  } catch {
    return timestamp
  }
}
</script>

<style scoped>
/* 自定义滚动条 */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>