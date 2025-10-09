<template>
  <MainLayout>
    <div class="space-y-6">
      <!-- Page Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold">日志管理</h1>
          <p class="text-base-content/60 mt-1">查看系统操作日志和查询执行记录</p>
        </div>
        <div class="flex gap-2">
          <button
            @click="refreshLogs"
            class="btn btn-ghost"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            刷新
          </button>
          <button
            @click="exportLogs"
            class="btn btn-primary"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            导出日志
          </button>
        </div>
      </div>

      <!-- Log Statistics -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="stat bg-base-100 rounded-lg shadow">
          <div class="stat-figure text-info">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="stat-title">总查询数</div>
          <div class="stat-value text-info">{{ statistics.totalQueries || 0 }}</div>
          <div class="stat-desc">今日 {{ statistics.todayQueries || 0 }}</div>
        </div>

        <div class="stat bg-base-100 rounded-lg shadow">
          <div class="stat-figure text-success">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="stat-title">成功率</div>
          <div class="stat-value text-success">{{ statistics.successRate || 0 }}%</div>
          <div class="stat-desc">{{ statistics.successCount || 0 }} 成功</div>
        </div>

        <div class="stat bg-base-100 rounded-lg shadow">
          <div class="stat-figure text-warning">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="stat-title">平均耗时</div>
          <div class="stat-value text-warning">{{ statistics.avgDuration || 0 }}s</div>
          <div class="stat-desc">查询执行时间</div>
        </div>

        <div class="stat bg-base-100 rounded-lg shadow">
          <div class="stat-figure text-error">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="stat-title">失败次数</div>
          <div class="stat-value text-error">{{ statistics.errorCount || 0 }}</div>
          <div class="stat-desc">需要关注</div>
        </div>
      </div>

      <!-- Filters -->
      <div class="flex flex-wrap gap-4 items-center bg-base-200 p-4 rounded-lg">
        <div class="form-control">
          <label class="label">
            <span class="label-text">时间范围</span>
          </label>
          <select
            v-model="filters.timeRange"
            class="select select-bordered select-sm"
            @change="loadLogs"
          >
            <option value="1h">最近1小时</option>
            <option value="24h">最近24小时</option>
            <option value="7d">最近7天</option>
            <option value="30d">最近30天</option>
          </select>
        </div>

        <div class="form-control">
          <label class="label">
            <span class="label-text">状态</span>
          </label>
          <select
            v-model="filters.status"
            class="select select-bordered select-sm"
            @change="loadLogs"
          >
            <option value="">全部状态</option>
            <option value="success">成功</option>
            <option value="failed">失败</option>
            <option value="running">运行中</option>
            <option value="cancelled">已取消</option>
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
          />
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
          />
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
            <div class="max-w-md truncate" :title="value">
              {{ value }}
            </div>
          </template>

          <template #cell-duration="{ value }">
            <span v-if="value">{{ formatDuration(value) }}</span>
            <span v-else class="text-base-content/40">-</span>
          </template>

          <template #cell-createdAt="{ value }">
            {{ formatTime(value) }}
          </template>

          <template #actions="{ record }">
            <div class="flex gap-1">
              <button
                @click="viewLogDetails(record)"
                class="btn btn-ghost btn-xs"
                title="查看详情"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </button>
              <button
                v-if="record.status === 'success'"
                @click="rerunQuery(record)"
                class="btn btn-ghost btn-xs"
                title="重新执行"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          </template>
        </DataTable>
      </div>
    </div>
  </MainLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import MainLayout from '@/components/layout/MainLayout.vue'
import DataTable from '@/components/common/DataTable.vue'
import type { QueryLog } from '@types/index'

const { success, info } = useToast()

// State
const logs = ref<QueryLog[]>([])
const loading = ref(false)
const statistics = ref({
  totalQueries: 0,
  todayQueries: 0,
  successRate: 0,
  successCount: 0,
  errorCount: 0,
  avgDuration: 0
})

// Filters
const filters = reactive({
  timeRange: '24h',
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
    // Mock data - in real implementation would call API
    logs.value = []
    statistics.value = {
      totalQueries: 0,
      todayQueries: 0,
      successRate: 0,
      successCount: 0,
      errorCount: 0,
      avgDuration: 0
    }
  } catch (err) {
    console.error('Failed to load logs:', err)
  } finally {
    loading.value = false
  }
}

// Refresh logs
const refreshLogs = () => {
  loadLogs()
}

// Export logs
const exportLogs = () => {
  info('导出日志功能开发中...')
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
const viewLogDetails = (log: QueryLog) => {
  info(`查看日志详情: ${log.id}`)
}

// Rerun query
const rerunQuery = (log: QueryLog) => {
  info(`重新执行查询: ${log.id}`)
}

// Initialize
onMounted(() => {
  loadLogs()
})
</script>