<template>
  <div
    v-if="isVisible"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    @click.self="handleClose"
  >
    <div class="bg-white rounded-lg w-11/12 max-w-4xl max-h-[90vh] overflow-hidden">
      <!-- 弹框头部 -->
      <div class="bg-primary text-white p-4 flex justify-between items-center">
        <h3 class="text-lg font-semibold">查询详情 - {{ taskId }}</h3>
        <button
          @click="handleClose"
          class="btn btn-sm btn-circle btn-ghost text-white hover:bg-white hover:bg-opacity-20"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 弹框内容 -->
      <div class="overflow-y-auto max-h-[calc(90vh-64px)]">
        <div v-if="isLoading" class="flex justify-center items-center p-8">
          <span class="loading loading-spinner loading-lg"></span>
        </div>

        <div v-else-if="detailData.task" class="p-6">
          <!-- 任务基本信息 -->
          <div class="mb-6">
            <h4 class="text-lg font-semibold mb-4">任务信息</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 bg-gray-50 p-4 rounded">
              <div>
                <label class="font-medium text-gray-600">任务ID:</label>
                <p class="font-mono text-sm">{{ detailData.task.task_id }}</p>
              </div>
              <div>
                <label class="font-medium text-gray-600">用户:</label>
                <p>{{ detailData.task.operator }}</p>
              </div>
              <div>
                <label class="font-medium text-gray-600">查询内容:</label>
                <p class="text-sm">{{ detailData.task.user_input }}</p>
              </div>
              <div>
                <label class="font-medium text-gray-600">状态:</label>
                <p>
                  <span
                    class="badge badge-sm"
                    :class="{
                      'badge-success': detailData.task.status === 'success',
                      'badge-error': detailData.task.status === 'failed',
                      'badge-warning': detailData.task.status === 'running',
                      'badge-info': detailData.task.status === 'completed'
                    }"
                  >
                    {{ getStatusText(detailData.task.status) }}
                  </span>
                </p>
              </div>
              <div>
                <label class="font-medium text-gray-600">开始时间:</label>
                <p class="text-sm">{{ formatTime(detailData.task.created_at) }}</p>
              </div>
              <div>
                <label class="font-medium text-gray-600">结束时间:</label>
                <p class="text-sm">{{ detailData.task.completed_at ? formatTime(detailData.task.completed_at) : '进行中' }}</p>
              </div>
              <div>
                <label class="font-medium text-gray-600">SQL查询:</label>
                <pre class="bg-gray-100 p-2 rounded text-xs overflow-x-auto">{{ detailData.task.sql_query || '无' }}</pre>
              </div>
              <div>
                <label class="font-medium text-gray-600">执行结果:</label>
                <p class="text-sm">{{ detailData.task.execution_result?.length || 0 }} 条记录</p>
              </div>
            </div>
          </div>

          <!-- 执行步骤日志 -->
          <div>
            <h4 class="text-lg font-semibold mb-4">执行步骤</h4>
            <div v-if="detailData.logs.length === 0" class="text-center py-8 text-gray-500">
              暂无执行步骤日志
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="(log, index) in detailData.logs"
                :key="index"
                class="border rounded-lg p-4"
                :class="{
                  'border-green-200 bg-green-50': log.success,
                  'border-red-200 bg-red-50': !log.success
                }"
              >
                <div class="flex justify-between items-start mb-2">
                  <div class="flex items-center gap-2">
                    <span class="font-medium">{{ log.step }}</span>
                    <span
                      class="badge badge-sm"
                      :class="{
                        'badge-success': log.success,
                        'badge-error': !log.success
                      }"
                    >
                      {{ log.success ? '成功' : '失败' }}
                    </span>
                  </div>
                  <span class="text-xs text-gray-500">
                    {{ log.start_time ? formatTime(log.start_time) : '' }} -
                    {{ log.end_time ? formatTime(log.end_time) : '' }}
                  </span>
                </div>

                <div v-if="log.error" class="text-red-600 text-sm mb-2 p-2 bg-red-100 rounded">
                  <strong>错误:</strong> {{ log.error }}
                </div>

                <div v-if="log.prompt" class="mb-2">
                  <details class="text-sm">
                    <summary class="font-medium cursor-pointer hover:text-primary">提示词</summary>
                    <pre class="bg-gray-100 p-2 rounded mt-1 text-xs overflow-x-auto">{{ log.prompt }}</pre>
                  </details>
                </div>

                <div v-if="log.input_data" class="mb-2">
                  <details class="text-sm">
                    <summary class="font-medium cursor-pointer hover:text-primary">输入数据</summary>
                    <pre class="bg-gray-100 p-2 rounded mt-1 text-xs overflow-x-auto">{{ log.input_data }}</pre>
                  </details>
                </div>

                <div v-if="log.model_output" class="mb-2">
                  <details class="text-sm">
                    <summary class="font-medium cursor-pointer hover:text-primary">模型输出</summary>
                    <pre class="bg-gray-100 p-2 rounded mt-1 text-xs overflow-x-auto">{{ log.model_output }}</pre>
                  </details>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="p-8 text-center text-gray-500">
          加载详情失败
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import queryService from '@services/api/queryService'
import type { QueryTask, BaseNodeLog } from '@types/index'

interface Props {
  isVisible: boolean
  taskId: string
  taskInfo?: QueryTask | null
}

interface Emits {
  (e: 'close'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// State
const isLoading = ref(false)
const detailData = ref<{
  task: QueryTask | null
  logs: BaseNodeLog[]
}>({
  task: null,
  logs: []
})

// Methods
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'success': '成功',
    'failed': '失败',
    'running': '运行中',
    'completed': '已完成',
    'pending': '等待中'
  }
  return statusMap[status] || status
}

const formatTime = (timeStr: string | undefined | null) => {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString()
}

const loadDetails = async () => {
  if (!props.taskId) return

  try {
    isLoading.value = true

    // 使用传入的任务信息或从详情API获取
    const taskInfo = props.taskInfo

    // 获取步骤日志
    const response = await queryService.getQueryHistoryDetail(props.taskId)
    if (response.success) {
      detailData.value = {
        task: taskInfo || null,
        logs: response.data || []
      }
      console.log('Log details loaded:', detailData.value)
    } else {
      console.error('Failed to get log details')
      detailData.value = { task: taskInfo || null, logs: [] }
    }
  } catch (err) {
    console.error('Failed to get log details:', err)
    // 即使获取步骤失败，也要显示任务基本信息
    const taskInfo = props.taskInfo
    detailData.value = { task: taskInfo || null, logs: [] }
  } finally {
    isLoading.value = false
  }
}

const handleClose = () => {
  emit('close')
}

// Watch for visibility changes to load data
watch(
  () => props.isVisible,
  (visible) => {
    if (visible && props.taskId) {
      loadDetails()
    }
  }
)

// Watch for taskId changes
watch(
  () => props.taskId,
  (newTaskId) => {
    if (newTaskId && props.isVisible) {
      loadDetails()
    }
  }
)
</script>