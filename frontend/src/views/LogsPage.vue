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
          <option value="cancelled">
            已取消
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
        row-key="id"
      >
        <template #cell-status="{ value }">
          <span
            class="badge badge-sm"
            :class="{
              'badge-success': value === 'success',
              'badge-error': value === 'failed',
              'badge-warning': value === 'running',
              'badge-info': value === 'cancelled'
            }"
          >
            {{ getStatusText(value) }}
          </span>
        </template>

        <template #cell-query="{ value }">
          <div
            class="max-w-md truncate"
            :title="value"
          >
            {{ value }}
          </div>
        </template>

        <template #cell-duration="{ value }">
          <span v-if="value">{{ formatDuration(value) }}</span>
          <span
            v-else
            class="text-base-content/40"
          >-</span>
        </template>

        <template #cell-createdAt="{ value }">
          {{ formatTime(value) }}
        </template>

        <template #actions="{ record }">
          <div class="flex gap-1">
            <button
              class="btn btn-ghost btn-xs"
              title="查看详情"
              @click="viewLogDetails(record)"
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
              v-if="record.status === 'success'"
              class="btn btn-ghost btn-xs"
              title="重新执行"
              @click="rerunQuery(record)"
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import DataTable from '@/components/common/DataTable.vue'
import queryService from '@/services/api/queryService'
import type { QueryLog } from '@types/index'

const { success, info } = useToast()

// State
const logs = ref<QueryLog[]>([])
const loading = ref(false)
const pagination = ref({
  page: 1,
  pageSize: 50,
  total: 0,
  totalPages: 0
})

// Filters
const filters = reactive({
  status: '',
  user: '',
  search: ''
})

// Table columns
const logColumns = [
  {
    key: 'id',
    title: 'ID',
    sortable: true,
    visible: false
  },
  {
    key: 'query',
    title: '查询内容',
    sortable: true,
    visible: true
  },
  {
    key: 'status',
    title: '状态',
    sortable: true,
    visible: true,
    className: 'text-center'
  },
  {
    key: 'duration',
    title: '耗时',
    sortable: true,
    visible: true,
    className: 'text-center'
  },
  {
    key: 'createdAt',
    title: '时间',
    sortable: true,
    visible: true
  }
]

// Debounced search
let searchTimeout: NodeJS.Timeout
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
      pagination.value = response.pagination || pagination.value
    } else {
      logs.value = []
      console.error('Failed to load logs: API returned success=false')
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
  const statusMap = {
    'success': '成功',
    'failed': '失败',
    'running': '运行中',
    'cancelled': '已取消'
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
const formatTime = (timeStr: string) => {
  return new Date(timeStr).toLocaleString()
}

// View log details
const viewLogDetails = async (log: QueryLog) => {
  try {
    const response = await queryService.getQueryHistoryDetail(log.id)
    if (response.success) {
      console.log('Log details:', response.data)
      info(`查看日志详情: ${log.id}`)
      // TODO: 可以在这里添加显示详情的逻辑，比如弹窗或跳转
    } else {
      console.error('Failed to get log details')
    }
  } catch (err) {
    console.error('Failed to get log details:', err)
  }
}

// Rerun query
const rerunQuery = async (log: QueryLog) => {
  try {
    const response = await queryService.rerunQuery(log.id)
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
