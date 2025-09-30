<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <div class="bg-white border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">淘沙数据分析助手</h1>
            <p class="mt-1 text-sm text-gray-500">基于AI的自然语言查询分析平台</p>
          </div>
          <button
            @click="refreshTasks"
            :disabled="isRefreshing"
            class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 flex items-center space-x-2"
          >
            <ArrowPathIcon :class="['w-4 h-4', isRefreshing ? 'animate-spin' : '']" />
            <span>刷新</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Query Input Section -->
    <div class="bg-white border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex flex-col lg:flex-row gap-4">
          <!-- 查询输入 -->
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              请输入您的问题：
            </label>
            <input
              v-model="queryInput"
              type="text"
              placeholder="例如：显示北京地区本月的销售额，最近一周电子产品销量统计"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              @keydown.enter.ctrl="submitQuery"
            />
          </div>

          <!-- 控制区域 -->
          <div class="lg:w-48 flex flex-col gap-3">
            <!-- 流程选择 -->
            <div class="flex bg-gray-100 rounded-lg p-1">
              <button
                @click="flowType = 'fast'"
                :class="[
                  'flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                  flowType === 'fast'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-800'
                ]"
              >
                快速
              </button>
              <button
                @click="flowType = 'thorough'"
                :class="[
                  'flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                  flowType === 'thorough'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-800'
                ]"
              >
                深度
              </button>
            </div>

            <!-- 查询按钮 -->
            <button
              @click="submitQuery"
              :disabled="!queryInput.trim() || isSubmitting"
              class="w-full px-6 py-3 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span v-if="!isSubmitting" class="flex items-center justify-center space-x-2">
                <MagnifyingGlassIcon class="w-5 h-5" />
                <span>开始查询</span>
              </span>
              <span v-else class="flex items-center justify-center space-x-2">
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>提交中...</span>
              </span>
            </button>
          </div>
        </div>

        <div class="mt-3 text-sm text-gray-500">
          <LightBulbIcon class="w-4 h-4 inline text-amber-500 mr-1" />
          提示：尽量明确时间范围、统计指标和筛选条件，这样能得到更准确的结果
        </div>
      </div>
    </div>

    <!-- Tasks Section -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="mb-4">
        <h2 class="text-lg font-semibold text-gray-900">查询记录</h2>
        <p class="text-sm text-gray-500">点击查询记录查看详细结果</p>
      </div>

      <!-- Tasks Container -->
      <div class="space-y-4">
        <!-- 查询任务卡片 -->
        <div
          v-for="task in tasks"
          :key="task.task_id"
          class="bg-white rounded-lg border border-gray-200 overflow-hidden transition-all duration-200 hover:shadow-lg"
        >
          <!-- Task Header -->
          <div
            class="p-4 border-b border-gray-200 cursor-pointer hover:bg-gray-50"
            @click="toggleTask(task.task_id)"
          >
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <div class="flex items-center space-x-3">
                  <!-- 状态图标 -->
                  <div class="flex-shrink-0">
                    <div v-if="task.status === 'running'" class="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
                    <div v-else-if="task.status === 'success'" class="w-3 h-3 bg-green-500 rounded-full"></div>
                    <div v-else-if="task.status === 'failed'" class="w-3 h-3 bg-red-500 rounded-full"></div>
                    <div v-else class="w-3 h-3 bg-gray-400 rounded-full"></div>
                  </div>

                  <!-- 查询内容 -->
                  <div class="flex-1">
                    <p class="text-sm font-medium text-gray-900 truncate">
                      {{ task.user_input }}
                    </p>
                    <p class="text-xs text-gray-500 mt-1">
                      {{ formatTime(task.created_at) }}
                    </p>
                  </div>

                  <!-- 状态标签 -->
                  <div class="flex-shrink-0">
                    <span
                      :class="[
                        'px-2 py-1 text-xs font-medium rounded-full',
                        task.status === 'running' ? 'bg-blue-100 text-blue-800' :
                        task.status === 'success' ? 'bg-green-100 text-green-800' :
                        task.status === 'failed' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      ]"
                    >
                      {{ getStatusText(task.status) }}
                    </span>
                  </div>

                  <!-- 展开图标 -->
                  <ChevronDownIcon
                    :class="[
                      'w-5 h-5 text-gray-400 transition-transform duration-200',
                      expandedTasks.includes(task.task_id) ? 'transform rotate-180' : ''
                    ]"
                  />
                </div>

                <!-- 进度条 (运行中的任务) -->
                <div v-if="task.status === 'running'" class="mt-3">
                  <div class="flex items-center justify-between text-xs text-gray-600 mb-1">
                    <span>{{ task.current_step }}</span>
                    <span>{{ task.progress }}%</span>
                  </div>
                  <div class="w-full bg-gray-200 rounded-full h-2">
                    <div
                      class="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      :style="{ width: `${task.progress}%` }"
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Task Details -->
          <div
            v-show="expandedTasks.includes(task.task_id)"
            class="border-t border-gray-200"
          >
            <div v-if="task.status === 'running'" class="p-4">
              <!-- 运行中的状态 -->
              <div class="text-center text-gray-500">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-3"></div>
                <p class="text-sm">{{ task.current_step }}</p>
                <p class="text-xs text-gray-400 mt-1">请稍候，正在处理您的查询...</p>
              </div>
            </div>

            <div v-else-if="task.status === 'success' && task.result" class="p-4">
              <!-- 成功的结果展示 -->
              <div class="space-y-4">
                <!-- SQL 查询区域 (可收缩) -->
                <div>
                  <button
                    @click="toggleSql(task.task_id)"
                    class="flex items-center space-x-2 text-sm font-medium text-gray-700 hover:text-gray-900 mb-2"
                  >
                    <ChevronRightIcon
                      :class="[
                        'w-4 h-4 transition-transform duration-200',
                        expandedSql.includes(task.task_id) ? 'transform rotate-90' : ''
                      ]"
                    />
                    <span>SQL 查询语句</span>
                  </button>

                  <div v-show="expandedSql.includes(task.task_id)" class="bg-gray-50 p-3 rounded-lg">
                    <pre class="text-sm text-gray-800 font-mono overflow-x-auto">{{ task.result.sql_query }}</pre>
                  </div>
                </div>

                <!-- 查询结果数据 -->
                <div>
                  <h4 class="text-sm font-medium text-gray-700 mb-2">查询结果</h4>
                  <div class="bg-gray-50 p-3 rounded-lg max-h-96 overflow-auto">
                    <QueryResultTable
                      v-if="task.result.data && task.result.data.length > 0"
                      :data="task.result.data"
                    />
                    <div v-else class="text-center text-gray-500 py-8">
                      <div class="text-gray-400 mb-2">
                        <DocumentIcon class="w-12 h-12 mx-auto" />
                      </div>
                      <p class="text-sm">查询结果为空</p>
                    </div>
                  </div>
                </div>

                <!-- 执行信息 -->
                <div class="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span class="text-gray-500">行数：</span>
                    <span class="font-medium">{{ task.result.row_count || 0 }}</span>
                  </div>
                  <div>
                    <span class="text-gray-500">执行时间：</span>
                    <span class="font-medium">{{ task.result.execution_time?.toFixed(2) || 0 }}s</span>
                  </div>
                </div>

                <!-- SQL 解释 -->
                <div v-if="task.result.sql_explanation">
                  <h4 class="text-sm font-medium text-gray-700 mb-2">查询说明</h4>
                  <div class="bg-blue-50 p-3 rounded-lg">
                    <p class="text-sm text-gray-700">{{ task.result.sql_explanation }}</p>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="task.status === 'failed'" class="p-4">
              <!-- 失败状态 -->
              <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                <div class="flex items-start space-x-3">
                  <ExclamationTriangleIcon class="w-5 h-5 text-red-500 mt-0.5" />
                  <div>
                    <h4 class="text-sm font-medium text-red-800">查询失败</h4>
                    <p class="text-sm text-red-700 mt-1">{{ task.error || '未知错误' }}</p>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="p-4">
              <!-- 其他状态 -->
              <div class="text-center text-gray-500">
                <p class="text-sm">等待处理中...</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="tasks.length === 0" class="text-center py-12">
          <DocumentIcon class="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 class="text-lg font-medium text-gray-900 mb-2">暂无查询记录</h3>
          <p class="text-gray-500">输入您的问题开始第一个查询</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { MagnifyingGlassIcon, ChevronDownIcon, ChevronRightIcon, LightBulbIcon, ArrowPathIcon, DocumentIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import QueryResultTable from '@/components/QueryResultTable.vue'
import { queryApi } from '@/services/api'

interface Task {
  task_id: string
  user_input: string
  status: 'pending' | 'running' | 'success' | 'failed'
  current_step: string
  progress: number
  created_at: string
  started_at?: string
  completed_at?: string
  has_result: boolean
  has_error: boolean
  result?: any
  error?: string
}

// 响应式数据
const queryInput = ref('')
const flowType = ref<'fast' | 'thorough'>('fast')
const isSubmitting = ref(false)
const isRefreshing = ref(false)
const tasks = ref<Task[]>([])
const expandedTasks = ref<string[]>([])
const expandedSql = ref<string[]>([])

// 轮询定时器
let pollTimer: NodeJS.Timeout | null = null

// 提交查询
const submitQuery = async () => {
  if (!queryInput.value.trim() || isSubmitting.value) return

  isSubmitting.value = true

  try {
    const response = await queryApi.submitQuery({
      query: queryInput.value.trim(),
      flow_type: flowType.value
    })

    if (response.success) {
      // 清空输入框
      queryInput.value = ''

      // 刷新任务列表
      await refreshTasks()

      // 展开新任务
      if (response.task_id) {
        expandedTasks.value.push(response.task_id)
      }
    } else {
      console.error('提交查询失败:', response.error)
    }
  } catch (error) {
    console.error('提交查询异常:', error)
  } finally {
    isSubmitting.value = false
  }
}

// 刷新任务列表
const refreshTasks = async () => {
  isRefreshing.value = true

  try {
    const tasksData = await queryApi.getAllTasks()

    // 更新任务列表
    tasks.value = tasksData.sort((a: Task, b: Task) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )

    // 对于运行中的任务，获取详细信息
    for (const task of tasks.value.filter(t => t.status === 'running')) {
      try {
        const detail = await queryApi.getTaskResult(task.task_id)
        if (detail) {
          Object.assign(task, detail)
        }
      } catch (error) {
        console.error(`获取任务 ${task.task_id} 详情失败:`, error)
      }
    }
  } catch (error) {
    console.error('刷新任务列表失败:', error)
  } finally {
    isRefreshing.value = false
  }
}

// 切换任务展开状态
const toggleTask = (taskId: string) => {
  const index = expandedTasks.value.indexOf(taskId)
  if (index > -1) {
    expandedTasks.value.splice(index, 1)
  } else {
    expandedTasks.value.push(taskId)
  }
}

// 切换SQL展开状态
const toggleSql = (taskId: string) => {
  const index = expandedSql.value.indexOf(taskId)
  if (index > -1) {
    expandedSql.value.splice(index, 1)
  } else {
    expandedSql.value.push(taskId)
  }
}

// 获取状态文本
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'pending': '等待中',
    'running': '运行中',
    'success': '已完成',
    'failed': '失败'
  }
  return statusMap[status] || status
}

// 格式化时间
const formatTime = (timeStr: string) => {
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) { // 1分钟内
    return '刚刚'
  } else if (diff < 3600000) { // 1小时内
    return `${Math.floor(diff / 60000)}分钟前`
  } else if (diff < 86400000) { // 1天内
    return `${Math.floor(diff / 3600000)}小时前`
  } else {
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
  }
}

// 开始轮询
const startPolling = () => {
  pollTimer = setInterval(() => {
    refreshTasks()
  }, 2000) // 每2秒轮询一次
}

// 停止轮询
const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 生命周期
onMounted(() => {
  refreshTasks()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>