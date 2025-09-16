<template>
  <div class="min-h-screen bg-white">
    <!-- Hero Section -->
    <section class="bg-gradient-to-br from-blue-50 to-indigo-50 py-16">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <!-- Left: Text Content -->
          <div>
            <h1 class="text-4xl lg:text-5xl font-bold text-slate-800 leading-tight tracking-tight mb-6">
              淘沙数据分析助手
            </h1>
            <p class="text-xl text-slate-600 leading-relaxed mb-8">
              使用自然语言查询您的数据，获得即时的分析结果。让数据分析变得简单直观。
            </p>
            
            <!-- Query Input Section -->
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <label class="block text-sm font-medium text-slate-700 mb-3">
                请输入您的问题：
              </label>
              <div class="space-y-4">
                <textarea
                  v-model="queryInput"
                  rows="3"
                  placeholder="例如：显示北京地区本月的销售额，最近一周电子产品销量统计"
                  class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 resize-none"
                ></textarea>
                
                <div class="flex flex-col sm:flex-row gap-3">
                  <div class="flex items-center space-x-3">
                    <label class="text-sm text-slate-600">重试次数:</label>
                    <select 
                      v-model="maxRetries"
                      class="px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                    >
                      <option :value="0">0</option>
                      <option :value="1">1</option>
                      <option :value="2">2</option>
                      <option :value="3">3</option>
                    </select>
                  </div>
                  
                  <button
                    @click="submitQuery"
                    :disabled="!queryInput.trim() || isQuerying"
                    class="flex-1 sm:flex-none px-6 py-3 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 hover:scale-105 hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:hover:shadow-none"
                  >
                    <span v-if="!isQuerying" class="flex items-center justify-center space-x-2">
                      <MagnifyingGlassIcon class="w-5 h-5" />
                      <span>开始查询</span>
                    </span>
                    <span v-else class="flex items-center justify-center space-x-2">
                      <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>分析中...</span>
                    </span>
                  </button>
                </div>
              </div>

              <div class="mt-4 text-sm text-slate-500">
                💡 提示：尽量明确时间范围、统计指标和筛选条件，这样能得到更准确的结果
              </div>
            </div>
          </div>

          <!-- Right: Code Snippet Preview -->
          <div class="hidden lg:block">
            <div class="bg-slate-900 rounded-xl p-6 shadow-xl">
              <div class="flex items-center space-x-2 mb-4">
                <div class="w-3 h-3 bg-red-500 rounded-full"></div>
                <div class="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <div class="w-3 h-3 bg-green-500 rounded-full"></div>
                <div class="ml-4 text-slate-400 text-sm">SQL 查询示例</div>
              </div>
              <pre class="text-green-400 text-sm font-mono leading-relaxed"><code>SELECT region, SUM(sales_amount) as total_sales
FROM sales_data 
WHERE date >= '2024-01-01'
  AND product_category = '电子产品'
GROUP BY region
ORDER BY total_sales DESC;</code></pre>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Results Section -->
    <section v-if="queryResult" class="py-8">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <!-- Clarity Check -->
        <ClarityCheck
          v-if="queryResult.clear_check_details"
          :clarity="queryResult.clear_check_details"
          @select-suggestion="selectSuggestion"
        />

        <!-- Success Result -->
        <ResultDisplay
          v-if="queryResult.success"
          :sql-query="queryResult.sql_query"
          :data="queryResult.data"
          :execution-time="executionTime"
        />

        <!-- Error Result -->
        <div v-else class="bg-red-50 border border-red-200 rounded-lg p-6">
          <div class="flex items-start space-x-3">
            <ExclamationTriangleIcon class="w-6 h-6 text-red-600 mt-0.5 flex-shrink-0" />
            <div>
              <h3 class="text-lg font-semibold text-red-800 mb-2">查询失败</h3>
              <p class="text-red-700">{{ queryResult.error || '未知错误' }}</p>
            </div>
          </div>
        </div>

        <!-- Query Logs -->
        <div v-if="queryResult.logs && queryResult.logs.length > 0" class="mt-6">
          <QueryLogs :logs="queryResult.logs" />
        </div>
      </div>
    </section>

    <!-- Features Section -->
    <section class="py-16 bg-slate-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-12">
          <h2 class="text-3xl font-bold text-slate-800 mb-4">
            强大的数据分析能力
          </h2>
          <p class="text-xl text-slate-600 max-w-3xl mx-auto">
            基于先进的自然语言处理技术，为您提供智能、准确、高效的数据查询体验
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div 
            v-for="feature in features"
            :key="feature.title"
            class="bg-white rounded-xl p-8 shadow-sm border border-slate-200 hover:-translate-y-1 transition-all duration-300 hover:shadow-md"
          >
            <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-6">
              <component :is="feature.icon" class="w-6 h-6 text-blue-600" />
            </div>
            <h3 class="text-xl font-semibold text-slate-800 mb-3">{{ feature.title }}</h3>
            <p class="text-slate-600 leading-relaxed">{{ feature.description }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Sidebar: System Info -->
    <div class="fixed bottom-6 right-6 w-80 bg-white rounded-lg shadow-lg border border-slate-200 p-4 z-40">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-semibold text-slate-800">系统信息</h3>
        <button
          @click="sidebarCollapsed = !sidebarCollapsed"
          class="p-1 hover:bg-slate-100 rounded"
        >
          <ChevronUpIcon :class="['w-4 h-4 text-slate-500 transition-transform duration-200', sidebarCollapsed ? 'rotate-180' : '']" />
        </button>
      </div>

      <div v-if="!sidebarCollapsed" class="space-y-4">
        <!-- Health Status -->
        <div class="flex items-center space-x-2">
          <div :class="['w-2 h-2 rounded-full', isHealthy ? 'bg-green-500' : 'bg-red-500']"></div>
          <span class="text-sm text-slate-600">{{ isHealthy ? '服务正常' : '服务异常' }}</span>
        </div>

        <!-- System Status -->
        <div v-if="systemStatus" class="text-sm text-slate-600 space-y-1">
          <div><strong>应用:</strong> {{ systemStatus.app_name }}</div>
          <div><strong>版本:</strong> {{ systemStatus.version }}</div>
          <div><strong>数据库:</strong> {{ systemStatus.database?.database_type }}</div>
          <div><strong>表数量:</strong> {{ systemStatus.database?.total_tables }}</div>
        </div>

        <!-- Example Queries -->
        <div>
          <div class="text-sm font-medium text-slate-700 mb-2">💡 示例查询</div>
          <div class="space-y-1">
            <button
              v-for="example in exampleQueries"
              :key="example"
              @click="selectExample(example)"
              class="block w-full text-left text-xs text-slate-600 hover:text-blue-600 hover:bg-blue-50 p-2 rounded transition-colors duration-200"
            >
              {{ example }}
            </button>
          </div>
        </div>

        <!-- Query History -->
        <div v-if="queryHistory.length > 0">
          <div class="text-sm font-medium text-slate-700 mb-2">📜 查询历史</div>
          <div class="space-y-1 max-h-32 overflow-y-auto">
            <div
              v-for="(entry, index) in queryHistory.slice(-5)"
              :key="index"
              class="text-xs p-2 bg-slate-50 rounded"
            >
              <div class="flex items-center space-x-2">
                <div :class="['w-1.5 h-1.5 rounded-full', entry.success ? 'bg-green-500' : 'bg-red-500']"></div>
                <span class="text-slate-600 truncate flex-1">{{ entry.query }}</span>
                <button
                  @click="retryQuery(entry.query)"
                  class="text-blue-600 hover:text-blue-800"
                  title="重新查询"
                >
                  ↻
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { 
  MagnifyingGlassIcon, 
  ExclamationTriangleIcon,
  ChevronUpIcon,
  ChatBubbleLeftRightIcon,
  ChartBarIcon,
  CpuChipIcon
} from '@heroicons/vue/24/outline'
import { apiClient } from '@/api'
import type { QueryResponse, SystemStatus } from '@/types'
import ClarityCheck from '@/components/ClarityCheck.vue'
import ResultDisplay from '@/components/ResultDisplay.vue'
import QueryLogs from '@/components/QueryLogs.vue'

// 响应式数据
const queryInput = ref('')
const maxRetries = ref(2)
const isQuerying = ref(false)
const queryResult = ref<QueryResponse | null>(null)
const executionTime = ref(0)
const isHealthy = ref(true)
const systemStatus = ref<SystemStatus | null>(null)
const sidebarCollapsed = ref(false)
const queryHistory = ref<Array<{ query: string; success: boolean; timestamp: number }>>([])

// 功能特性
const features = [
  {
    title: '自然语言查询',
    description: '使用日常语言描述您的需求，无需学习复杂的SQL语法',
    icon: ChatBubbleLeftRightIcon
  },
  {
    title: '智能数据可视化',
    description: '自动生成合适的图表，直观展示查询结果和数据趋势',
    icon: ChartBarIcon
  },
  {
    title: '高性能分析引擎',
    description: '基于DuckDB的轻量级OLAP引擎，提供秒级查询响应',
    icon: CpuChipIcon
  }
]

// 示例查询
const exampleQueries = [
  '显示所有销售数据',
  '北京地区的销售额是多少？',
  '按产品类别统计销售量',
  '哪个客户购买最多？',
  '今年的总销售额',
  '电子产品的平均价格'
]

// 提交查询
const submitQuery = async () => {
  if (!queryInput.value.trim() || isQuerying.value) return

  isQuerying.value = true
  queryResult.value = null
  executionTime.value = 0

  try {
    const startTime = Date.now()
    const result = await apiClient.query(queryInput.value.trim(), maxRetries.value)
    const endTime = Date.now()
    
    executionTime.value = (endTime - startTime) / 1000
    queryResult.value = result

    // 添加到查询历史
    queryHistory.value.push({
      query: queryInput.value.trim(),
      success: result.success,
      timestamp: Date.now()
    })

    // 保持最近10条历史
    if (queryHistory.value.length > 10) {
      queryHistory.value = queryHistory.value.slice(-10)
    }
  } catch (error) {
    console.error('查询失败:', error)
    queryResult.value = {
      success: false,
      error: '查询过程中发生错误，请稍后重试'
    }
  } finally {
    isQuerying.value = false
  }
}

// 选择建议
const selectSuggestion = (suggestion: string) => {
  queryInput.value = suggestion
}

// 选择示例查询
const selectExample = (example: string) => {
  queryInput.value = example
}

// 重新查询
const retryQuery = (query: string) => {
  queryInput.value = query
}

// 健康检查
const checkHealth = async () => {
  try {
    isHealthy.value = await apiClient.healthCheck()
    if (isHealthy.value && !systemStatus.value) {
      systemStatus.value = await apiClient.getSystemStatus()
    }
  } catch {
    isHealthy.value = false
  }
}

// 定时健康检查
let healthCheckInterval: number

onMounted(() => {
  checkHealth()
  healthCheckInterval = window.setInterval(checkHealth, 30000)

  // 键盘事件监听
  const handleKeyDown = (event: KeyboardEvent) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      submitQuery()
    }
  }
  
  document.addEventListener('keydown', handleKeyDown)

  return () => {
    document.removeEventListener('keydown', handleKeyDown)
  }
})

onUnmounted(() => {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval)
  }
})
</script>

<style scoped>
/* 自定义滚动条 */
.overflow-y-auto::-webkit-scrollbar {
  width: 4px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 2px;
}

/* 渐变动画 */
@keyframes gradient {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.bg-gradient-to-br {
  background-size: 200% 200%;
  animation: gradient 15s ease infinite;
}
</style>