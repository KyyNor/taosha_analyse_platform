<template>
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <div class="flex items-center justify-between mb-4">
        <h3 class="card-title text-lg">查询进度</h3>
        <button
          v-if="canCancel"
          @click="handleCancel"
          class="btn btn-ghost btn-sm"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
          取消
        </button>
      </div>

      <!-- Progress Bar -->
      <div class="mb-6">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium">{{ currentStep?.title || '准备中...' }}</span>
          <span class="text-sm text-base-content/60">{{ progressPercentage }}%</span>
        </div>
        <div class="progress progress-primary w-full">
          <div
            class="progress-bar"
            :style="{ width: `${progressPercentage}%` }"
          ></div>
        </div>
        <div v-if="currentStep?.description" class="text-xs text-base-content/60 mt-2">
          {{ currentStep.description }}
        </div>
      </div>

      <!-- Steps Timeline -->
      <div class="space-y-3">
        <div
          v-for="(step, index) in steps"
          :key="index"
          class="flex items-start gap-3"
          :class="{
            'opacity-40': step.status === 'pending',
            'text-primary': step.status === 'active',
            'text-success': step.status === 'completed',
            'text-error': step.status === 'failed'
          }"
        >
          <!-- Step Icon -->
          <div class="flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs"
               :class="{
                 'border-primary bg-primary text-primary-content': step.status === 'active',
                 'border-success bg-success text-success-content': step.status === 'completed',
                 'border-error bg-error text-error-content': step.status === 'failed',
                 'border-base-300 bg-base-100': step.status === 'pending'
               }">
            <span v-if="step.status === 'completed'">✓</span>
            <span v-else-if="step.status === 'failed'">✕</span>
            <span v-else-if="step.status === 'active'" class="loading loading-spinner loading-xs"></span>
            <span v-else>{{ index + 1 }}</span>
          </div>

          <!-- Step Content -->
          <div class="flex-1 min-w-0">
            <div class="font-medium text-sm">{{ step.title }}</div>
            <div v-if="step.description" class="text-xs text-base-content/60 mt-1">
              {{ step.description }}
            </div>
            <div v-if="step.details" class="text-xs text-base-content/40 mt-1">
              {{ step.details }}
            </div>
          </div>

          <!-- Step Duration -->
          <div v-if="step.duration" class="flex-shrink-0 text-xs text-base-content/60">
            {{ formatDuration(step.duration) }}
          </div>
        </div>
      </div>

      <!-- Generated SQL Preview -->
      <div v-if="generatedSQL" class="mt-6">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium">生成的 SQL</span>
          <button
            @click="copySQL"
            class="btn btn-ghost btn-xs"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            复制
          </button>
        </div>
        <div class="mockup-code">
          <pre><code>{{ generatedSQL }}</code></pre>
        </div>
      </div>

      <!-- Error Message -->
      <div v-if="error" class="alert alert-error mt-4">
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <h3 class="font-bold">查询失败</h3>
          <div class="text-sm">{{ error }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQueryStore } from '@stores/query'

interface QueryStep {
  title: string
  description?: string
  status: 'pending' | 'active' | 'completed' | 'failed'
  duration?: number
  details?: string
}

const emit = defineEmits<{
  cancel: []
  copySQL: [sql: string]
}>()

const queryStore = useQueryStore()

// Define query steps based on the workflow
const querySteps: QueryStep[] = [
  {
    title: '检查训练状态',
    description: '检查 Vanna 模型训练状态',
    status: 'pending'
  },
  {
    title: '输入验证',
    description: '验证查询输入的清晰度',
    status: 'pending'
  },
  {
    title: '生成 SQL',
    description: '基于自然语言生成 SQL 查询',
    status: 'pending'
  },
  {
    title: '执行查询',
    description: '执行生成的 SQL 查询',
    status: 'pending'
  },
  {
    title: '解释结果',
    description: '分析并解释查询结果',
    status: 'pending'
  },
  {
    title: '差异分析',
    description: '分析自然语言与结果的差异',
    status: 'pending'
  }
]

const steps = ref<QueryStep[]>(querySteps)
const error = ref<string>('')

// Computed properties
const currentTask = computed(() => queryStore.currentTask)
const progress = computed(() => queryStore.queryProgress)
const generatedSQL = computed(() => queryStore.generatedSQL)
const canCancel = computed(() => queryStore.canCancelQuery)

// Current active step
const currentStep = computed(() => {
  return steps.value.find(step => step.status === 'active')
})

// Progress percentage
const progressPercentage = computed(() => {
  if (!progress.value) return 0
  return Math.round(progress.value.progress * 100)
})

// Map progress data to steps
const updateStepsFromProgress = () => {
  if (!progress.value) return

  // Reset all steps to pending first
  steps.value = steps.value.map(step => ({
    ...step,
    status: 'pending' as const,
    duration: undefined,
    details: undefined
  }))

  // Update steps based on progress data
  const progressData = progress.value

  if (progressData.check_vanna_status) {
    steps.value[0].status = progressData.check_vanna_status.success ? 'completed' : 'failed'
    steps.value[0].details = progressData.check_vanna_status.result
  }

  if (progressData.clarity_validation) {
    steps.value[1].status = progressData.clarity_validation.success ? 'completed' : 'failed'
    steps.value[1].details = progressData.clarity_validation.result
  }

  if (progressData.sql_generation) {
    steps.value[2].status = progressData.sql_generation.success ? 'completed' : 'failed'
    steps.value[2].details = progressData.sql_generation.result
  }

  if (progressData.sql_execution) {
    steps.value[3].status = progressData.sql_execution.success ? 'completed' : 'failed'
    steps.value[3].details = `执行时间: ${progressData.sql_execution.result?.execution_time}ms`
  }

  if (progressData.sql_explanation) {
    steps.value[4].status = progressData.sql_explanation.success ? 'completed' : 'failed'
    steps.value[4].details = progressData.sql_explanation.result
  }

  if (progressData.diff_analysis) {
    steps.value[5].status = progressData.diff_analysis.success ? 'completed' : 'failed'
    steps.value[5].details = progressData.diff_analysis.result
  }

  // Set active step based on current state
  const activeStepIndex = steps.value.findIndex(step => step.status === 'completed') + 1
  if (activeStepIndex < steps.value.length && steps.value[activeStepIndex].status === 'pending') {
    steps.value[activeStepIndex].status = 'active'
  }
}

// Watch for progress changes
watch(progress, updateStepsFromProgress, { immediate: true })

// Watch for task status changes
watch(currentTask, (newTask) => {
  if (!newTask) {
    // Reset when task is cleared
    steps.value = querySteps.map(step => ({ ...step, status: 'pending' }))
    error.value = ''
  } else if (newTask.taskStatus === 'failed') {
    error.value = newTask.errorMessage || '查询执行失败'
    // Mark current step as failed
    const activeStep = steps.value.find(step => step.status === 'active')
    if (activeStep) {
      activeStep.status = 'failed'
    }
  } else if (newTask.taskStatus === 'cancelled') {
    error.value = '查询已取消'
  }
}, { immediate: true })

// Format duration
const formatDuration = (duration: number) => {
  if (duration < 1000) {
    return `${duration}ms`
  } else if (duration < 60000) {
    return `${(duration / 1000).toFixed(1)}s`
  } else {
    const minutes = Math.floor(duration / 60000)
    const seconds = Math.floor((duration % 60000) / 1000)
    return `${minutes}m ${seconds}s`
  }
}

// Handle cancel
const handleCancel = () => {
  emit('cancel')
}

// Copy SQL
const copySQL = () => {
  if (generatedSQL.value) {
    navigator.clipboard.writeText(generatedSQL.value)
    emit('copySQL', generatedSQL.value)
  }
}
</script>

<style scoped>
.progress {
  appearance: none;
  height: 8px;
  border-radius: 9999px;
  background-color: hsl(var(--b2));
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: hsl(var(--p));
  transition: width 0.3s ease;
}

.mockup-code {
  background-color: hsl(var(--b2));
  border-radius: 0.5rem;
  padding: 1rem;
  overflow-x: auto;
}

.mockup-code pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.25;
  color: hsl(var(--bc));
}
</style>