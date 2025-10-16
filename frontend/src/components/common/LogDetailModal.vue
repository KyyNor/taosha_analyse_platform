<template>
  <div
    v-if="isVisible"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    @click.self="handleClose"
  >
    <div class="bg-base-100 rounded-lg w-11/12 max-w-4xl max-h-[90vh] overflow-hidden">
      <!-- 弹框头部 -->
      <div class="bg-primary text-white p-4 flex justify-between items-center">
        <h3 class="text-lg font-semibold">
          查询详情 - {{ taskId }}
        </h3>
        <button
          class="btn btn-sm btn-circle btn-ghost text-white hover:bg-white hover:bg-opacity-20"
          @click="handleClose"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-6 w-6"
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
        </button>
      </div>

      <!-- 弹框内容 -->
      <div class="overflow-y-auto max-h-[calc(90vh-64px)]">
        <div
          v-if="isLoading"
          class="flex justify-center items-center p-8"
        >
          <span class="loading loading-spinner loading-lg" />
        </div>

        <div
          v-else-if="detailData.task"
          class="p-6"
        >
          <!-- 任务基本信息 -->
          <div class="mb-6">
            <h4 class="text-lg font-semibold mb-4">
              任务信息
            </h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 bg-base-200 p-4 rounded-lg shadow-md">
              <div>
                <label class="font-medium text-base-content/70">任务ID:</label>
                <p class="font-mono text-sm text-base-content">
                  {{ detailData.task.task_id }}
                </p>
              </div>
              <div>
                <label class="font-medium text-base-content/70">用户:</label>
                <p class="text-base-content">
                  {{ detailData.task.operator }}
                </p>
              </div>
              <div>
                <label class="font-medium text-base-content/70">查询内容:</label>
                <p class="text-sm text-base-content">
                  {{ detailData.task.user_input }}
                </p>
              </div>
              <div>
                <label class="font-medium text-base-content/70">状态:</label>
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
                <label class="font-medium text-base-content/70">开始时间:</label>
                <p class="text-sm text-base-content">
                  {{ formatTime(detailData.task.created_at) }}
                </p>
              </div>
              <div>
                <label class="font-medium text-base-content/70">结束时间:</label>
                <p class="text-sm text-base-content">
                  {{ detailData.task.completed_at ? formatTime(detailData.task.completed_at) : '进行中' }}
                </p>
              </div>
              <div>
                <label class="font-medium text-base-content/70">SQL查询:</label>
                <div class="rounded-lg text-xs overflow-x-auto border">
                  <pre
                    v-if="detailData.task.sql_query"
                    class="language-sql shadow-inner"
                    style="margin: 0 !important;"
                  ><code
class="language-sql"
                                                                                             v-html="highlightSql(detailData.task.sql_query)"
/></pre>
                  <pre
                    v-else
                    class="text-base-content/50 m-0"
                  >无</pre>
                </div>
              </div>
              <div>
                <label class="font-medium text-base-content/70">执行结果:</label>
                <p class="text-sm text-base-content">
                  {{ detailData.task.execution_result?.length || 0 }} 条记录
                </p>
              </div>
              <div v-if="detailData.task.clear_check_details && Object.keys(detailData.task.clear_check_details).length > 0">
                <label class="font-medium text-base-content/70">输入验证结果:</label>
                <div class="rounded-lg text-xs overflow-x-auto border">
                  <pre class="bg-base-200 p-2 rounded-lg shadow-inner">{{ formatText(detailData.task.clear_check_details) }}</pre>
                </div>
              </div>
            </div>
          </div>

          <!-- 执行步骤日志 -->
          <div>
            <h4 class="text-lg font-semibold mb-4">
              执行步骤
            </h4>
            <div
              v-if="detailData.logs.length === 0"
              class="text-center py-8 text-base-content/60"
            >
              暂无执行步骤日志
            </div>
            <div
              v-else
              class="space-y-3"
            >
              <div
                v-for="(log, index) in detailData.logs"
                :key="index"
                class="border rounded-lg p-4 shadow-md"
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
                    <!-- 展开/收起按钮 -->
                    <button
                      v-if="hasDetails(log)"
                      class="btn btn-ghost btn-xs p-1 hover:bg-base-200"
                      :title="expandedLogs[index] ? '收起详情' : '展开详情'"
                      @click="toggleLogDetails(index)"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-4 w-4 transition-transform duration-200"
                        :class="{ 'rotate-180': expandedLogs[index] }"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </button>
                  </div>
                  <div class="text-right">
                    <div class="text-xs text-gray-500">
                      {{ log.start_time ? formatTime(log.start_time) : '' }} -
                      {{ log.end_time ? formatTime(log.end_time) : '' }}
                    </div>
                    <!-- 耗时信息 -->
                    <div class="duration-display text-xs mt-1">
                      ⏱️ {{ formatDuration(calculateDuration(log.start_time, log.end_time)) }}
                    </div>
                  </div>
                </div>

                <!-- 详情内容 - 统一展开/收起 -->
                <div
                  v-show="expandedLogs[index]"
                  class="space-y-2 border-t border-base-300 pt-2 mt-2"
                >
                  <!-- 错误信息 - 跟随展开状态 -->
                  <div
                    v-if="log.error"
                    class="text-error text-sm p-2 bg-error/10 rounded border border-error/20 shadow-inner"
                  >
                    <div class="font-medium mb-1">
                      错误信息:
                    </div>
                    <pre class="whitespace-pre-wrap text-xs">{{ formatText(log.error) }}</pre>
                  </div>

                  <div
                    v-if="log.prompt"
                    class="text-sm"
                  >
                    <div class="font-medium text-base-content/80 mb-1">
                      提示词:
                    </div>
                    <pre class="bg-base-200 p-2 rounded-lg text-xs overflow-x-auto shadow-inner">{{ formatText(log.prompt) }}</pre>
                  </div>

                  <div
                    v-if="log.input_data"
                    class="text-sm"
                  >
                    <div class="font-medium text-base-content/80 mb-1">
                      输入数据:
                    </div>
                    <pre class="bg-base-200 p-2 rounded-lg text-xs overflow-x-auto shadow-inner">{{ formatText(log.input_data) }}</pre>
                  </div>

                  <div
                    v-if="log.model_output"
                    class="text-sm"
                  >
                    <div class="font-medium text-base-content/80 mb-1">
                      模型输出:
                    </div>
                    <pre class="bg-base-200 p-2 rounded-lg text-xs overflow-x-auto shadow-inner">{{ formatText(log.model_output) }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div
          v-else
          class="p-8 text-center text-gray-500"
        >
          加载详情失败
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import queryService from '@services/api/queryService'
import type { QueryTask, BaseNodeLog } from '@types/index'
import { highlightSql, initHighlight, applyPrismTheme } from '@utils/prism'
import { calculateDuration, formatDuration, formatTime } from '@utils/duration'
import { formatText } from '@utils/formatText'

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
const expandedLogs = ref<Record<number, boolean>>({})
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

// 检查是否有详情内容
const hasDetails = (log: BaseNodeLog) => {
  return !!(log.prompt || log.input_data || log.model_output || log.error)
}

// 切换展开/收起状态
const toggleLogDetails = (index: number) => {
  expandedLogs.value[index] = !expandedLogs.value[index]
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

      // 初始化代码高亮
      await initHighlight()
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

// 组件挂载时初始化 Prism
onMounted(() => {
  initHighlight()
})
</script>

<style scoped>
/* Duration display styles - from QueryProgress */
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
</style>
