<template>
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <div class="flex items-center justify-between mb-4">
        <h3 class="card-title text-lg">
          查询进度
        </h3>
        <button
          v-if="canCancel"
          class="btn btn-ghost btn-sm"
          @click="handleCancel"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
          取消
        </button>
      </div>

      <!-- Progress Bar -->
      <div class="mb-6">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium">{{ statusTitle }}</span>
          <span class="text-sm text-base-content/60">{{ progressPercentage }}%</span>
        </div>
        <div class="progress progress-primary w-full">
          <div
            class="progress-bar"
            :style="{ width: `${progressPercentage}%` }"
          />
        </div>
        <div
          v-if="currentStep?.description"
          class="text-xs text-base-content/60 mt-2"
        >
          {{ currentStep.description }}
        </div>
      </div>

      <!-- Error Message -->
      <div
        v-if="error"
        class="alert alert-error mt-4 shadow-md"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="stroke-current shrink-0 h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <div>
          <h3 class="font-bold">
            查询失败
          </h3>
          <div class="text-sm">
            {{ error }}
          </div>
        </div>
      </div>

      <!-- 澄清选项界面 -->
      <div
        v-if="isWaitingForClarification"
        class="alert alert-warning mt-4 shadow-md"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="stroke-current shrink-0 h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <div>
          <h3 class="font-bold">
            需要澄清
          </h3>
          <div class="text-sm">
            {{ clarificationQuestion }}
          </div>
        </div>
      </div>

      <!-- 澄清选项 -->
      <div
        v-if="isWaitingForClarification"
        class="mt-4 space-y-3 shadow-inner rounded-lg bg-base-200 p-4"
      >
        <!-- 预设选项 -->
        <div
          v-if="clarificationOptions.length > 0"
          class="space-y-2"
        >
          <label class="text-sm font-medium">请选择最符合您需求的选项：</label>
          <div class="space-y-2">
            <label
              v-for="(option, index) in clarificationOptions"
              :key="index"
              class="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-base-200 transition-colors"
              :class="{ 'border-primary bg-primary/5': selectedClarification === option }"
            >
              <input
                v-model="selectedClarification"
                type="radio"
                :value="option"
                class="radio radio-primary"
              >
              <span class="flex-1">{{ option }}</span>
            </label>
          </div>
        </div>

        <!-- 自定义输入 -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-medium">或输入您的具体需求：</span>
          </label>
          <textarea
            v-model="customClarification"
            class="textarea textarea-bordered"
            placeholder="请详细描述您的查询需求..."
            rows="3"
          />
        </div>

        <!-- 提交按钮 -->
        <div class="flex justify-end gap-2 mt-4">
          <button
            class="btn btn-primary"
            :disabled="!selectedClarification && !customClarification.trim()"
            @click="handleSubmitClarification"
          >
            <span
              v-if="isLoading"
              class="loading loading-spinner loading-sm"
            />
            提交澄清
          </button>
        </div>
      </div>

      <!-- Generated SQL Preview -->
      <div
        v-if="generatedSQL"
        class="mt-6"
      >
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium">生成的 SQL</span>
          <button
            class="btn btn-ghost btn-xs"
            @click="copySQL"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-3 w-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
            复制
          </button>
        </div>
        <div class="rounded-lg border">
          <pre
            v-if="generatedSQL"
            class="language-sql text-sm shadow-inner"
            style="margin: 0 !important;"
          ><code
class="language-sql"
                                                                                             v-html="highlightSql(generatedSQL)"
/></pre>
          <pre
            v-else
            class="text-sm text-gray-400 m-0"
          >无 SQL 代码</pre>
        </div>
      </div>

      <!-- Steps Timeline -->
      <div class="space-y-3">
        <div
          v-for="(step, index) in steps"
          :key="index"
          class="flex items-start gap-3 step-item p-2 rounded-lg"
          :class="{
            'opacity-40': step.status === 'pending',
            'text-primary': step.status === 'active',
            'text-success': step.status === 'completed',
            'text-error': step.status === 'failed'
          }"
        >
          <!-- Step Icon -->
          <div
            class="flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs"
            :class="{
              'border-primary bg-primary text-primary-content': step.status === 'active',
              'border-success bg-success text-success-content': step.status === 'completed',
              'border-error bg-error text-error-content': step.status === 'failed',
              'border-base-300 bg-base-100': step.status === 'pending'
            }"
          >
            <span v-if="step.status === 'completed'">✓</span>
            <span v-else-if="step.status === 'failed'">✕</span>
            <span
              v-else-if="step.status === 'active'"
              class="loading loading-spinner loading-xs"
            />
            <span v-else>{{ index + 1 }}</span>
          </div>

          <!-- Step Content -->
          <div class="flex-1 min-w-0">
            <div class="font-medium text-sm">
              {{ step.title }}
            </div>

            <!-- Input Section -->
            <div
              v-if="step.description"
              class="mt-2 p-3 bg-base-200 rounded-lg text-xs input-output-section input-section"
            >
              <div class="font-semibold text-primary mb-2 flex items-center gap-1">
                <svg
                  class="w-3 h-3"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                  <path
                    fill-rule="evenodd"
                    d="M4 5a2 2 0 012-2 1 1 0 000 2H6a2 2 0 100 4h2a2 2 0 100 4h2a1 1 0 100 2 2 2 0 01-2 2H6a2 2 0 01-2-2V5z"
                    clip-rule="evenodd"
                  />
                </svg>
                输入数据
              </div>
              <div class="formatted-content text-base-content/80">
                {{ step.description }}
              </div>
            </div>

            <!-- Output Section -->
            <div
              v-if="step.details"
              class="mt-2 p-3 bg-base-200 rounded-lg text-xs input-output-section output-section"
            >
              <div class="font-semibold text-success mb-2 flex items-center gap-1">
                <svg
                  class="w-3 h-3"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                  <path
                    fill-rule="evenodd"
                    d="M4 5a2 2 0 012-2 1 1 0 100 2H6a2 2 0 100 4h2a2 2 0 100 4h2a1 1 0 100 2 2 2 0 01-2 2H6a2 2 0 01-2-2V5z"
                    clip-rule="evenodd"
                  />
                </svg>
                输出结果
              </div>
              <div class="formatted-content text-base-content/80">
                {{ step.details }}
              </div>
            </div>

            <!-- Time Info -->
            <div
              v-if="step.startTime || step.completedAt"
              class="flex flex-wrap gap-2 mt-3"
            >
              <div
                v-if="step.startTime"
                class="time-info text-xs"
              >
                <span class="text-primary">⏰ 开始:</span> {{ step.startTime }}
              </div>
              <div
                v-if="step.completedAt"
                class="time-info text-xs"
              >
                <span class="text-success">✅ 完成:</span> {{ step.completedAt }}
              </div>
            </div>
          </div>

          <!-- Step Duration -->
          <div
            v-if="step.duration !== undefined"
            class="flex-shrink-0 text-right"
          >
            <div class="duration-display text-xs">
              ⏱️ {{ formatDuration(step.duration) }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { useQueryStore } from '@stores/query'
import { highlightSql, initHighlight } from '@utils/prism'
import { formatText } from '@utils/formatText'
import { formatDuration } from '@utils/duration'

interface QueryStep {
  title: string
  description?: string
  status: 'pending' | 'active' | 'completed' | 'failed'
  duration?: number
  details?: string
  completedAt?: string
  startTime?: string
  endTime?: string
}

const emit = defineEmits<{
  cancel: []
  copySQL: [sql: string]
}>()

const queryStore = useQueryStore()

// Steps derived from actual task logs
const steps = ref<QueryStep[]>([])
const error = ref<string>('')

// 人机交互相关
const isWaitingForClarification = computed(() => queryStore.isWaitingForClarification)
const clarificationOptions = computed(() => queryStore.clarificationOptions)
const clarificationQuestion = computed(() => queryStore.clarificationQuestion)
const selectedClarification = computed({
  get: () => queryStore.selectedClarification,
  set: (value: string) => {
    queryStore.selectedClarification = value
  }
})
const customClarification = computed({
  get: () => queryStore.customClarification,
  set: (value: string) => {
    queryStore.customClarification = value
  }
})
const isLoading = computed(() => queryStore.isLoading)

// Computed properties
const currentTask = computed(() => queryStore.currentTask)
const generatedSQL = computed(() => queryStore.generatedSQL)
const canCancel = computed(() => queryStore.canCancelQuery)

// Current active step
const currentStep = computed(() => {
  return steps.value.find(step => step.status === 'active')
})

// Status title based on task status
const statusTitle = computed(() => {
  if (!currentTask.value) {
    return '准备中...'
  }

  const taskStatus = (currentTask.value as any).status

  if (taskStatus === 'failed') {
    return '查询失败'
  } else if (taskStatus === 'success' || taskStatus === 'completed') {
    return '查询完成'
  } else if (taskStatus === 'cancelled') {
    return '查询已取消'
  } else if (currentStep.value && currentStep.value.title) {
    return currentStep.value.title
  } else if ((currentTask.value as any).current_step) {
    return (currentTask.value as any).current_step
  } else {
    return '执行中...'
  }
})

// Progress percentage from WebSocket progress field
const progressPercentage = computed(() => {
  // Use progress field from currentTask if available
  if (currentTask.value && (currentTask.value as any).progress !== undefined) {
    const progressValue = (currentTask.value as any).progress
    return Math.max(0, Math.min(100, Number(progressValue)))
  }
  // Fallback to calculated percentage based on completed steps
  if (steps.value.length === 0) return 0
  const completedSteps = steps.value.filter(step => step.status === 'completed').length
  const totalSteps = steps.value.length
  return Math.round((completedSteps / totalSteps) * 100)
})

// Map task logs to dynamic steps
const updateStepsFromLogs = () => {
  if (!currentTask.value || !(currentTask.value as any).logs) {
    steps.value = []
    return
  }

  const logs = (currentTask.value as any).logs
  const taskStatus = (currentTask.value as any).status

  // Check for errors in logs and update error state
  const errorLogs = logs.filter((log: any) => log.error || log.success === false)
  if (errorLogs.length > 0) {
    const latestErrorLog = errorLogs[errorLogs.length - 1]
    error.value = latestErrorLog.error || latestErrorLog.model_output || '执行步骤失败'
  } else if (taskStatus !== 'failed') {
    // Clear error if task is not failed and no log errors exist
    error.value = ''
  }

  // Convert logs to steps
  const newSteps: QueryStep[] = logs.map((log: any, index: number) => {
    let status: QueryStep['status'] = 'pending'

    if (log.success === true) {
      status = 'completed'
    } else if (log.success === false) {
      status = 'failed'
    } else if (log.error) {
      status = 'failed'
    } else if (index === logs.length - 1 && taskStatus === 'running') {
      // Last step is active if task is still running
      status = 'active'
    }

    // Calculate duration and format times
    let duration: number | undefined
    let completedAt: string | undefined
    let startTime: string | undefined
    let endTime: string | undefined

    if (log.start_time) {
      startTime = formatDateTime(log.start_time)
    }
    if (log.end_time) {
      endTime = formatDateTime(log.end_time)
      completedAt = endTime
    }
    if (log.start_time && log.end_time) {
      const startTimeMs = new Date(log.start_time).getTime()
      const endTimeMs = new Date(log.end_time).getTime()
      duration = endTimeMs - startTimeMs
    }

    // Format description (input data)
    const formattedDescription = formatText(log.input_data)

    // Format details (model output) - include error if present
    let formattedDetails = formatText(log.model_output)
    if (log.error) {
      formattedDetails = `❌ 错误: ${log.error}\n\n${formattedDetails}`
    }

    return {
      title: log.step,
      description: formattedDescription,
      status,
      duration,
      details: formattedDetails,
      completedAt,
      startTime,
      endTime
    }
  })

  // Add current step if task is running and last step doesn't have error
  if (taskStatus === 'running' && (currentTask.value as any).current_step) {
    const lastStep = newSteps[newSteps.length - 1]
    if (!lastStep || lastStep.status === 'completed') {
      newSteps.push({
        title: (currentTask.value as any).current_step,
        description: '',
        status: 'active'
      })
    }
  }

  // Reverse the order so that completed steps are at the bottom
  steps.value = newSteps.reverse()
}

// Format datetime string
const formatDateTime = (dateString: string): string => {
  return new Date(dateString).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}



// Watch for task changes to update steps
watch(currentTask, updateStepsFromLogs, { immediate: true, deep: true })

// Watch for task status changes to handle errors
watch(currentTask, (newTask) => {
  if (!newTask) {
    // Reset when task is cleared
    steps.value = []
    error.value = ''
  } else if ((newTask as any).status === 'failed') {
    error.value = (newTask as any).error_message || '查询执行失败'
    // Mark current step as failed
    const activeStep = steps.value.find(step => step.status === 'active')
    if (activeStep) {
      activeStep.status = 'failed'
    }
  } else if ((newTask as any).status === 'cancelled') {
    error.value = '查询已取消'
  }
}, { immediate: true })

// Watch for SQL changes to reinitialize highlighting
watch(generatedSQL, async () => {
  await initHighlight()
})

// 组件挂载时初始化 Prism
onMounted(() => {
  initHighlight()
})



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

// 处理澄清提交
const handleSubmitClarification = async () => {
  if (!currentTask.value) return
  try {
    await queryStore.submitClarification(currentTask.value.task_id)
    // 成功后继续监听进度，澄清选项卡会通过状态变化自动收起
  } catch (error) {
    console.error('提交澄清失败:', error)
    // 可以在这里显示错误提示
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
  font-family: 'Cascadia Code', 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.25;
  color: hsl(var(--bc));
}

/* Custom styles for formatted content */
.formatted-content {
  font-family: 'Cascadia Code', 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.75rem;
  line-height: 1.4;
  background-color: hsl(var(--b2));
  border: 1px solid hsl(var(--b3));
  border-radius: 0.375rem;
  padding: 0.75rem;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

/* JSON syntax highlighting */
.json-key {
  color: #0066cc;
  font-weight: 600;
}

.json-string {
  color: #008000;
}

.json-number {
  color: #ff6600;
}

.json-boolean {
  color: #cc0066;
  font-weight: 600;
}

.json-null {
  color: #999999;
  font-style: italic;
}

/* SQL syntax highlighting */
.sql-keyword {
  color: #0066cc;
  font-weight: 600;
  text-transform: uppercase;
}

.sql-function {
  color: #cc0066;
  font-weight: 600;
}

.sql-string {
  color: #008000;
}

.sql-number {
  color: #ff6600;
}

.sql-comment {
  color: #999999;
  font-style: italic;
}

/* Input/Output sections */
.input-output-section {
  border-left: 3px solid;
  transition: all 0.2s ease;
}

.input-section {
  border-left-color: hsl(var(--p));
}

.output-section {
  border-left-color: hsl(var(--su));
}

.input-output-section:hover {
  background-color: hsl(var(--b3));
  transform: translateX(2px);
}

/* Time display */
.time-info {
  font-family: monospace;
  background-color: hsl(var(--b1));
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  display: inline-block;
  margin: 0.125rem;
}

.duration-display {
  background-color: hsl(var(--p));
  color: hsl(var(--pc));
  padding: 0.25rem 0.5rem;
  border-radius: 0.5rem;
  font-weight: 600;
  min-width: 60px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* Step transitions */
.step-item {
  transition: all 0.3s ease;
}

.step-item:hover {
  background-color: hsl(var(--b2));
  border-radius: 0.5rem;
}
</style>
