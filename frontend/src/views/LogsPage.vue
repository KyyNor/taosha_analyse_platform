<template>
  <div class="space-y-6">
    <!-- Filters -->
    <div class="flex flex-wrap gap-4 items-center bg-base-200 p-4 rounded-lg">

      <div class="form-control">
        <label class="label">
          <span class="label-text">状态</span>
        </label>
        <select
          v-model="filters.status"
          class="select select-bordered select-sm"
          @change="loadLogs"
        >
          <option value="">
            全部状态
          </option>
          <option value="success">
            成功
          </option>
          <option value="failed">
            失败
          </option>
          <option value="running">
            运行中
          </option>
          <option value="completed">
            已完成
          </option>
        </select>
      </div>

      <div class="form-control">
        <label class="label">
          <span class="label-text">用户</span>
        </label>
        <input
          v-model="filters.user"
          type="text"
          placeholder="用户名"
          class="input input-bordered input-sm"
          @input="debouncedSearch"
        >
      </div>

      <div class="form-control flex-1 min-w-64">
        <label class="label">
          <span class="label-text">搜索查询</span>
        </label>
        <input
          v-model="filters.search"
          type="text"
          placeholder="搜索查询内容..."
          class="input input-bordered input-sm"
          @input="debouncedSearch"
        >
      </div>
    </div>

    <!-- Logs Table -->
    <div class="bg-base-100 rounded-lg shadow">
      <DataTable
        :data="logs"
        :columns="logColumns"
        :loading="loading"
        :searchable="false"
        :paginated="true"
        :page-size="50"
        empty-state-type="no-data"
        row-key="task_id"
      >
        <template #cell-status="{ value }">
          <span
            class="badge badge-sm"
            :class="{
              'badge-success': value === 'success',
              'badge-error': value === 'failed',
              'badge-warning': value === 'running',
              'badge-info': value === 'completed'
            }"
          >
            {{ getStatusText(value) }}
          </span>
        </template>

        <template #cell-user_input="{ value }">
          <div
            class="max-w-md truncate"
            :title="value"
          >
            {{ value }}
          </div>
        </template>

        <template #cell-operator="{ value }">
          <span class="badge badge-outline badge-sm">{{ value }}</span>
        </template>

        <template #cell-duration="{ record }">
          <span v-if="calculateDuration(record)">{{ formatDuration(calculateDuration(record) || 0) }}</span>
          <span
            v-else
            class="text-base-content/40"
          >-</span>
        </template>

        <template #cell-created_at="{ value }">
          <span v-if="value">{{ formatTime(value) }}</span>
          <span
            v-else
            class="text-base-content/40"
          >-</span>
        </template>

        <template #cell-completed_at="{ value }">
          <span v-if="value">{{ formatTime(value) }}</span>
          <span
            v-else
            class="text-base-content/40"
          >-</span>
        </template>

        <template #actions="{ task_id, task_status }">
          <div class="flex gap-1">
            <button
              class="btn btn-ghost btn-xs"
              title="查看详情"
              @click="viewLogDetails(task_id)"
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
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                />
              </svg>
            </button>
            <button
              v-if="task_status === 'success'"
              class="btn btn-ghost btn-xs"
              title="重新执行"
              @click="rerunQuery(task_id)"
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
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            </button>
          </div>
        </template>
      </DataTable>
    </div>

    <!-- 详情弹框 -->
    <div
      v-if="showDetailModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeDetailModal"
    >
      <div class="bg-white rounded-lg w-11/12 max-w-4xl max-h-[90vh] overflow-hidden">
        <!-- 弹框头部 -->
        <div class="bg-primary text-white p-4 flex justify-between items-center">
          <h3 class="text-lg font-semibold">查询详情 - {{ detailTaskId }}</h3>
          <button
            @click="closeDetailModal"
            class="btn btn-sm btn-circle btn-ghost text-white hover:bg-white hover:bg-opacity-20"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- 弹框内容 -->
        <div class="overflow-y-auto max-h-[calc(90vh-64px)]">
          <div v-if="detailLoading" class="flex justify-center items-center p-8">
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import DataTable from '@/components/common/DataTable.vue'
import queryService from '@/services/api/queryService'
import type { QueryTask, BaseNodeLog } from '@types/index'

const { success, info } = useToast()

// State
const logs = ref<QueryTask[]>([])
const loading = ref(false)
const pagination = ref({
  page: 1,
  pageSize: 50,
  total: 0,
  totalPages: 0
})

// 详情弹框状态
const showDetailModal = ref(false)
const detailTaskId = ref<string>('')
const detailData = ref<{
  task: QueryTask | null
  logs: BaseNodeLog[]
}>({
  task: null,
  logs: []
})
const detailLoading = ref(false)

// Filters
const filters = reactive({
  status: '',
  user: '',
  search: ''
})

// Table columns
const logColumns = [
  {
    key: 'task_id',
    title: 'ID',
    sortable: true,
    visible: false
  },
  {
    key: 'user_input',
    title: '查询内容',
    sortable: true,
    visible: true
  },
  {
    key: 'operator',
    title: '用户',
    sortable: true,
    visible: true,
    className: 'text-center',
    width: '100px'
  },
  {
    key: 'status',
    title: '状态',
    sortable: true,
    visible: true,
    className: 'text-center'
  },
  {
    key: 'created_at',
    title: '开始时间',
    sortable: true,
    visible: true,
    width: '150px'
  },
  {
    key: 'completed_at',
    title: '结束时间',
    sortable: true,
    visible: true,
    width: '150px'
  },
  {
    key: 'duration',
    title: '耗时',
    sortable: true,
    visible: true,
    className: 'text-center'
  }
]

// Debounced search
let searchTimeout: number
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(loadLogs, 500)
}


// Load logs
const loadLogs = async () => {
  try {
    loading.value = true

    const params = {
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      ...(filters.status && { status: filters.status })
    }

    const response = await queryService.getQueryHistory(
      params.page,
      params.pageSize,
      {
        status: params.status
      }
    )

    if (response.success) {
      logs.value = response.data || []
      if (response.pagination) {
        pagination.value = {
          page: response.pagination.page || pagination.value.page,
          pageSize: response.pagination.pageSize || pagination.value.pageSize,
          total: response.pagination.total || 0,
          totalPages: response.pagination.totalPages || Math.ceil((response.pagination.total || 0) / (response.pagination.pageSize || pagination.value.pageSize))
        }
      }
    } else {
      console.error('[LogsPage] API returned success=false:', response)
      logs.value = []
    }
  } catch (err) {
    console.error('Failed to load logs:', err)
    logs.value = []
  } finally {
    loading.value = false
  }
}

// Get status text
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'success': '成功',
    'failed': '失败',
    'running': '运行中',
    'completed': '已完成'
  }
  return statusMap[status] || status
}

// Format duration
const formatDuration = (duration: number) => {
  if (duration < 1000) {
    return `${duration}ms`
  } else {
    return `${(duration / 1000).toFixed(1)}s`
  }
}

// Format time
const formatTime = (timeStr: string | undefined | null) => {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString()
}

// Calculate duration from created_at and completed_at
const calculateDuration = (record: QueryTask) => {
  if (!record.created_at) return null

  const startTime = new Date(record.created_at).getTime()
  const endTime = record.completed_at ? new Date(record.completed_at).getTime() : Date.now()

  return endTime - startTime
}

// View log details
const viewLogDetails = async (task_id: string) => {
  try {
    detailTaskId.value = task_id
    showDetailModal.value = true
    detailLoading.value = true

    const response = await queryService.getQueryHistoryDetail(task_id)
    if (response.success) {
      detailData.value = {
        task: response.data,
        logs: response.logs || []
      }
      console.log('Log details loaded:', detailData.value)
    } else {
      console.error('Failed to get log details')
      detailData.value = { task: null, logs: [] }
    }
  } catch (err) {
    console.error('Failed to get log details:', err)
    detailData.value = { task: null, logs: [] }
  } finally {
    detailLoading.value = false
  }
}

// Close detail modal
const closeDetailModal = () => {
  showDetailModal.value = false
  detailTaskId.value = ''
  detailData.value = { task: null, logs: [] }
}

// Rerun query
const rerunQuery = async (task_id: string) => {
  try {
    const response = await queryService.rerunQuery(task_id)
    if (response.success) {
      success('查询已重新提交执行')
      // 刷新列表
      await loadLogs()
    } else {
      console.error('Failed to rerun query')
    }
  } catch (err) {
    console.error('Failed to rerun query:', err)
  }
}

// Initialize
onMounted(() => {
  loadLogs()
})
</script>
