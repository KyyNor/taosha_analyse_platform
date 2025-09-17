<template>
  <div class="min-h-screen bg-slate-50 p-4">
    <!-- 页面标题和统计信息 -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-slate-800 mb-4">操作追踪日志</h1>
      
      <!-- 统计卡片 -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4 mb-6">
        <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-4">
          <div class="text-sm text-slate-500">总会话数</div>
          <div class="text-2xl font-bold text-slate-800">{{ stats?.total_sessions || 0 }}</div>
        </div>
        <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-4">
          <div class="text-sm text-slate-500">运行中</div>
          <div class="text-2xl font-bold text-blue-600">{{ stats?.running_sessions || 0 }}</div>
        </div>
        <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-4">
          <div class="text-sm text-slate-500">已完成</div>
          <div class="text-2xl font-bold text-green-600">{{ stats?.completed_sessions || 0 }}</div>
        </div>
        <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-4">
          <div class="text-sm text-slate-500">已失败</div>
          <div class="text-2xl font-bold text-red-600">{{ stats?.failed_sessions || 0 }}</div>
        </div>
        <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-4">
          <div class="text-sm text-slate-500">平均耗时</div>
          <div class="text-2xl font-bold text-slate-800">{{ formatDuration(stats?.avg_duration || 0) }}</div>
        </div>
        <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-4">
          <div class="text-sm text-slate-500">成功率</div>
          <div class="text-2xl font-bold text-slate-800">{{ formatPercent(stats?.success_rate || 0) }}</div>
        </div>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-6 mb-6">
      <div class="flex flex-col sm:flex-row gap-4">
        <!-- 搜索框 -->
        <div class="flex-1">
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg class="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索会话ID、操作类型或操作员..."
              class="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-md leading-5 bg-white placeholder-slate-500 focus:outline-none focus:placeholder-slate-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              @keyup.enter="handleSearch"
            />
          </div>
        </div>

        <!-- 状态筛选 -->
        <div class="sm:w-48">
          <select
            v-model="selectedStatus"
            class="block w-full px-3 py-2 border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            @change="handleFilter"
          >
            <option value="">全部状态</option>
            <option value="running">运行中</option>
            <option value="completed">已完成</option>
            <option value="failed">已失败</option>
          </select>
        </div>

        <!-- 刷新按钮 -->
        <button
          @click="loadSessions"
          :disabled="loading"
          class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
        >
          <svg v-if="loading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ loading ? '刷新中...' : '刷新' }}
        </button>
      </div>
    </div>

    <!-- 会话列表 -->
    <div class="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
      <!-- 表头 -->
      <div class="px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h3 class="text-lg font-semibold text-slate-800">操作会话列表</h3>
        <p class="text-sm text-slate-500 mt-1">共 {{ totalCount }} 条记录</p>
      </div>

      <!-- 表格内容 -->
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">会话信息</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">操作详情</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">执行情况</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">状态</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">操作</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-slate-200">
            <!-- 加载状态 -->
            <tr v-if="loading && sessions.length === 0" class="animate-pulse">
              <td colspan="5" class="px-6 py-8 text-center text-slate-500">
                加载中...
              </td>
            </tr>
            
            <!-- 空状态 -->
            <tr v-else-if="sessions.length === 0">
              <td colspan="5" class="px-6 py-8 text-center text-slate-500">
                {{ searchQuery ? '未找到匹配的记录' : '暂无操作记录' }}
              </td>
            </tr>

            <!-- 会话记录 -->
            <template v-else>
              <template v-for="session in sessions" :key="session.session_id">
                <!-- 主记录行 -->
                <tr class="hover:bg-slate-50 transition-colors duration-200">
                  <!-- 会话信息 -->
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm">
                      <div class="font-medium text-slate-900">{{ session.session_id }}</div>
                      <div class="text-slate-500">{{ formatTime(session.start_time) }}</div>
                    </div>
                  </td>

                  <!-- 操作详情 -->
                  <td class="px-6 py-4">
                    <div class="text-sm">
                      <div class="font-medium text-slate-900">{{ session.operation_type }}</div>
                      <div class="text-slate-500">操作员: {{ session.operator }}</div>
                    </div>
                  </td>

                  <!-- 执行情况 -->
                  <td class="px-6 py-4">
                    <div class="text-sm">
                      <div class="text-slate-900">耗时: {{ formatDuration(session.total_duration) }}</div>
                      <div class="text-slate-500">
                        {{ session.step_count }} 步骤 | 成功率: {{ formatPercent(session.success_rate) }}
                      </div>
                    </div>
                  </td>

                  <!-- 状态 -->
                  <td class="px-6 py-4 whitespace-nowrap">
                    <span :class="getStatusClass(session.status)" class="inline-flex px-2 py-1 text-xs font-semibold rounded-full">
                      {{ getStatusText(session.status) }}
                    </span>
                    <div v-if="session.error_message" class="text-xs text-red-600 mt-1 max-w-xs truncate" :title="session.error_message">
                      {{ session.error_message }}
                    </div>
                  </td>

                  <!-- 操作 -->
                  <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      @click="toggleExpand(session.session_id)"
                      class="text-blue-600 hover:text-blue-900 mr-4 transition-colors duration-200"
                    >
                      {{ expandedSessions.has(session.session_id) ? '收起' : '展开' }}
                    </button>
                    <button
                      @click="refreshSession(session.session_id)"
                      class="text-slate-600 hover:text-slate-900 transition-colors duration-200"
                    >
                      刷新
                    </button>
                  </td>
                </tr>

                <!-- 展开的步骤详情 -->
                <tr v-if="expandedSessions.has(session.session_id)" class="bg-slate-50">
                  <td colspan="5" class="px-6 py-4">
                    <div class="bg-white rounded-lg border border-slate-200 p-4">
                      <h4 class="text-sm font-medium text-slate-900 mb-3">执行步骤详情</h4>
                      
                      <!-- 步骤加载状态 -->
                      <div v-if="loadingSteps.has(session.session_id)" class="text-center py-4">
                        <div class="inline-flex items-center text-sm text-slate-500">
                          <svg class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          加载步骤详情...
                        </div>
                      </div>

                      <!-- 步骤列表 -->
                      <div v-else-if="sessionSteps[session.session_id]?.length" class="space-y-4">
                        <div
                          v-for="step in sessionSteps[session.session_id]"
                          :key="step.step_sequence"
                          class="border border-slate-200 rounded-lg p-4 bg-slate-50"
                        >
                          <!-- 步骤标题行 -->
                          <div class="flex items-center space-x-2 mb-3">
                            <span class="text-sm font-medium text-slate-900">
                              步骤 {{ step.step_sequence }}: {{ step.step_name }}
                            </span>
                            <span :class="step.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'" 
                                  class="inline-flex px-2 py-1 text-xs font-semibold rounded-full">
                              {{ step.success ? '成功' : '失败' }}
                            </span>
                            <span v-if="step.has_sql" class="bg-blue-100 text-blue-800 inline-flex px-2 py-1 text-xs font-semibold rounded-full">
                              SQL
                            </span>
                            <span v-if="step.token_usage?.total_tokens" class="bg-purple-100 text-purple-800 inline-flex px-2 py-1 text-xs font-semibold rounded-full">
                              {{ step.token_usage.total_tokens }} tokens
                            </span>
                          </div>
                          
                          <!-- 基本信息 -->
                          <div class="grid grid-cols-2 gap-4 text-sm mb-3">
                            <div>
                              <span class="text-slate-500">调用方法:</span>
                              <span class="text-slate-900 ml-1">{{ step.call_method }}</span>
                            </div>
                            <div>
                              <span class="text-slate-500">耗时:</span>
                              <span class="text-slate-900 ml-1">{{ formatDuration(step.duration) }}</span>
                            </div>
                          </div>

                          <!-- 输入数据 -->
                          <div v-if="step.input_data" class="mb-3">
                            <div class="text-xs font-medium text-slate-500 mb-1">输入数据:</div>
                            <div class="bg-white border border-slate-200 rounded p-2 text-xs text-slate-700 max-h-32 overflow-y-auto">
                              <pre class="whitespace-pre-wrap">{{ formatJsonData(step.input_data) }}</pre>
                            </div>
                          </div>

                          <!-- 输出数据 -->
                          <div v-if="step.output_data" class="mb-3">
                            <div class="text-xs font-medium text-slate-500 mb-1">输出数据:</div>
                            <div class="bg-white border border-slate-200 rounded p-2 text-xs text-slate-700 max-h-32 overflow-y-auto">
                              <pre class="whitespace-pre-wrap">{{ step.output_data.substring(0, 500) }}{{ step.output_data.length > 500 ? '...' : '' }}</pre>
                            </div>
                          </div>

                          <!-- 生成的SQL -->
                          <div v-if="step.generated_sql" class="mb-3">
                            <div class="text-xs font-medium text-slate-500 mb-1">生成的SQL:</div>
                            <div class="bg-slate-800 text-green-400 rounded p-2 text-xs max-h-32 overflow-y-auto">
                              <pre class="whitespace-pre-wrap">{{ step.generated_sql }}</pre>
                            </div>
                          </div>

                          <!-- Token使用情况 -->
                          <div v-if="step.token_usage && step.token_usage.total_tokens > 0" class="mb-3">
                            <div class="text-xs font-medium text-slate-500 mb-1">Token使用:</div>
                            <div class="grid grid-cols-3 gap-2 text-xs">
                              <div class="bg-white border border-slate-200 rounded p-2 text-center">
                                <div class="text-slate-500">输入</div>
                                <div class="font-medium text-slate-900">{{ step.token_usage.prompt_tokens || 0 }}</div>
                              </div>
                              <div class="bg-white border border-slate-200 rounded p-2 text-center">
                                <div class="text-slate-500">输出</div>
                                <div class="font-medium text-slate-900">{{ step.token_usage.completion_tokens || 0 }}</div>
                              </div>
                              <div class="bg-white border border-slate-200 rounded p-2 text-center">
                                <div class="text-slate-500">总计</div>
                                <div class="font-medium text-slate-900">{{ step.token_usage.total_tokens || 0 }}</div>
                              </div>
                            </div>
                          </div>

                          <!-- 错误信息 -->
                          <div v-if="step.error_message" class="text-sm text-red-600 bg-red-50 p-2 rounded">
                            <div class="text-xs font-medium text-red-700 mb-1">错误信息:</div>
                            {{ step.error_message }}
                          </div>
                        </div>
                      </div>

                      <!-- 无步骤数据 -->
                      <div v-else class="text-center py-4 text-sm text-slate-500">
                        暂无步骤详情
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
            </template>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div v-if="totalCount > 0" class="px-6 py-3 bg-slate-50 border-t border-slate-200">
        <div class="flex items-center justify-between">
          <div class="text-sm text-slate-700">
            显示第 {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, totalCount) }} 条，共 {{ totalCount }} 条记录
          </div>
          <div class="flex items-center space-x-2">
            <button
              @click="changePage(currentPage - 1)"
              :disabled="currentPage <= 1"
              class="px-3 py-1 text-sm border border-slate-300 rounded text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
            >
              上一页
            </button>
            <span class="text-sm text-slate-700">
              第 {{ currentPage }} / {{ Math.ceil(totalCount / pageSize) }} 页
            </span>
            <button
              @click="changePage(currentPage + 1)"
              :disabled="currentPage >= Math.ceil(totalCount / pageSize)"
              class="px-3 py-1 text-sm border border-slate-300 rounded text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
            >
              下一页
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { apiClient } from '@/api'
import type { OperationSession, OperationStep, OperationStats } from '@/types'

// 响应式数据
const loading = ref(false)
const sessions = ref<OperationSession[]>([])
const sessionSteps = reactive<Record<string, OperationStep[]>>({})
const loadingSteps = reactive<Set<string>>(new Set())
const expandedSessions = reactive<Set<string>>(new Set())
const stats = ref<OperationStats | null>(null)

// 搜索和筛选
const searchQuery = ref('')
const selectedStatus = ref('')

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)

// 计算属性
const filteredSessions = computed(() => {
  let result = sessions.value

  // 状态筛选
  if (selectedStatus.value) {
    result = result.filter(session => session.status === selectedStatus.value)
  }

  return result
})

// 方法
const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

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

const formatPercent = (value: number) => {
  return `${(value * 100).toFixed(1)}%`
}

const formatJsonData = (data: string) => {
  if (!data) return ''
  try {
    const parsed = JSON.parse(data)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return data
  }
}

const getStatusClass = (status: string) => {
  switch (status) {
    case 'running':
      return 'bg-blue-100 text-blue-800'
    case 'completed':
      return 'bg-green-100 text-green-800'
    case 'failed':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-slate-100 text-slate-800'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'running':
      return '运行中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '已失败'
    default:
      return '未知'
  }
}

const loadSessions = async () => {
  loading.value = true
  try {
    console.log('正在加载会话数据...', {
      page: currentPage.value,
      pageSize: pageSize.value,
      search: searchQuery.value
    })
    
    const result = await apiClient.getOperationSessions(
      currentPage.value,
      pageSize.value,
      searchQuery.value || undefined
    )
    
    console.log('会话数据加载成功:', result)
    sessions.value = result.sessions
    totalCount.value = result.total
  } catch (error) {
    console.error('加载会话失败:', error)
    console.error('错误堆栈:', error.stack)
    
    // 显示用户友好的错误信息
    sessions.value = []
    totalCount.value = 0
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    console.log('正在加载统计信息...')
    stats.value = await apiClient.getOperationStats()
    console.log('统计信息加载成功:', stats.value)
  } catch (error) {
    console.error('加载统计信息失败:', error)
    console.error('错误堆栈:', error.stack)
    stats.value = null
  }
}

const loadSessionSteps = async (sessionId: string) => {
  if (sessionSteps[sessionId]) {
    return // 已加载过，直接返回
  }

  loadingSteps.add(sessionId)
  try {
    const steps = await apiClient.getOperationSteps(sessionId)
    sessionSteps[sessionId] = steps
  } catch (error) {
    console.error('加载步骤详情失败:', error)
    sessionSteps[sessionId] = []
  } finally {
    loadingSteps.delete(sessionId)
  }
}

const toggleExpand = async (sessionId: string) => {
  if (expandedSessions.has(sessionId)) {
    expandedSessions.delete(sessionId)
  } else {
    expandedSessions.add(sessionId)
    await loadSessionSteps(sessionId)
  }
}

const refreshSession = async (sessionId: string) => {
  // 清除缓存的步骤数据
  delete sessionSteps[sessionId]
  
  // 如果当前展开，重新加载步骤
  if (expandedSessions.has(sessionId)) {
    await loadSessionSteps(sessionId)
  }
  
  // 重新加载会话列表
  await loadSessions()
}

const handleSearch = async () => {
  currentPage.value = 1
  await loadSessions()
}

const handleFilter = async () => {
  currentPage.value = 1
  await loadSessions()
}

const changePage = async (page: number) => {
  if (page < 1 || page > Math.ceil(totalCount.value / pageSize.value)) {
    return
  }
  currentPage.value = page
  await loadSessions()
}

// 监听搜索查询变化，实现防抖搜索
let searchTimer: number | null = null
watch(searchQuery, (newQuery, oldQuery) => {
  if (newQuery !== oldQuery) {
    if (searchTimer) {
      clearTimeout(searchTimer)
    }
    searchTimer = setTimeout(() => {
      handleSearch()
    }, 500)
  }
})

// 生命周期
onMounted(() => {
  loadSessions()
  loadStats()
})
</script>

<style scoped>
/* 自定义滚动条 */
.overflow-x-auto::-webkit-scrollbar {
  height: 6px;
}

.overflow-x-auto::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.overflow-x-auto::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.overflow-x-auto::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>