<template>
  <div class="space-y-4">
    <!-- 进度条 -->
    <div class="flex items-center justify-between">
      <span class="text-sm font-medium">{{ currentStep }}</span>
      <span class="text-sm text-base-content text-opacity-60">{{ progressPercentage }}%</span>
    </div>
    
    <div class="w-full bg-base-200 rounded-full h-2">
      <div 
        class="bg-primary h-2 rounded-full transition-all duration-300 ease-in-out"
        :style="{ width: `${progressPercentage}%` }"
      ></div>
    </div>
    
    <!-- 步骤指示器 -->
    <div class="flex items-center justify-between text-xs">
      <div 
        v-for="(step, index) in steps" 
        :key="index"
        class="flex flex-col items-center space-y-1"
        :class="getStepClass(index)"
      >
        <div 
          class="w-6 h-6 rounded-full flex items-center justify-center border-2 transition-colors"
          :class="getStepIconClass(index)"
        >
          <svg v-if="index < currentStepIndex" class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
          <span v-else class="text-xs">{{ index + 1 }}</span>
        </div>
        <span class="text-center max-w-16 truncate">{{ step.name }}</span>
      </div>
    </div>
    
    <!-- 实时日志 -->
    <div v-if="logs && logs.length > 0" class="space-y-2">
      <div class="flex items-center justify-between">
        <h4 class="text-sm font-medium">执行日志</h4>
        <button 
          @click="toggleLogExpanded" 
          class="btn btn-ghost btn-xs"
        >
          {{ isLogExpanded ? '收起' : '展开' }}
        </button>
      </div>
      
      <div 
        class="bg-base-200 rounded-lg p-3 transition-all duration-300 overflow-hidden"
        :class="isLogExpanded ? 'max-h-64' : 'max-h-20'"
      >
        <div class="space-y-1 overflow-y-auto h-full">
          <div 
            v-for="(log, index) in logs" 
            :key="index" 
            class="text-xs flex items-start space-x-2"
            :class="getLogLevelClass(log.level)"
          >
            <span class="text-base-content text-opacity-50 shrink-0 font-mono">
              [{{ formatTime(log.timestamp) }}]
            </span>
            <span class="shrink-0 font-medium uppercase">{{ log.level }}:</span>
            <span>{{ log.message }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 取消按钮 -->
    <div class="flex justify-end">
      <button 
        @click="$emit('cancel')" 
        class="btn btn-warning btn-sm"
        :disabled="!cancellable"
      >
        取消查询
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface LogEntry {
  timestamp: string | number
  level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG'
  message: string
}

interface QueryStep {
  name: string
  description?: string
}

interface Props {
  currentStep: string
  progressPercentage: number
  logs?: LogEntry[]
  cancellable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  logs: () => [],
  cancellable: true
})

defineEmits<{
  cancel: []
}>()

const isLogExpanded = ref(false)

// 查询步骤定义
const steps: QueryStep[] = [
  { name: '分析', description: '分析用户问题' },
  { name: '生成', description: '生成SQL语句' },
  { name: '验证', description: '验证SQL正确性' },
  { name: '执行', description: '执行查询' },
  { name: '完成', description: '处理结果' }
]

const currentStepIndex = computed(() => {
  // 根据进度百分比计算当前步骤
  if (props.progressPercentage < 20) return 0
  if (props.progressPercentage < 40) return 1
  if (props.progressPercentage < 60) return 2
  if (props.progressPercentage < 80) return 3
  return 4
})

const getStepClass = (index: number) => {
  if (index < currentStepIndex.value) return 'text-success'
  if (index === currentStepIndex.value) return 'text-primary'
  return 'text-base-content text-opacity-40'
}

const getStepIconClass = (index: number) => {
  if (index < currentStepIndex.value) {
    return 'bg-success text-success-content border-success'
  }
  if (index === currentStepIndex.value) {
    return 'bg-primary text-primary-content border-primary'
  }
  return 'bg-base-100 border-base-300 text-base-content text-opacity-60'
}

const getLogLevelClass = (level: string) => {
  switch (level) {
    case 'ERROR':
      return 'text-error'
    case 'WARNING':
      return 'text-warning'
    case 'INFO':
      return 'text-info'
    case 'DEBUG':
      return 'text-base-content text-opacity-60'
    default:
      return ''
  }
}

const formatTime = (timestamp: string | number) => {
  return new Date(timestamp).toLocaleTimeString('zh-CN')
}

const toggleLogExpanded = () => {
  isLogExpanded.value = !isLogExpanded.value
}
</script>