<template>
  <div class="min-h-screen bg-white">
    <!-- Hero Section -->
    <section class="bg-gradient-to-br from-blue-50 to-indigo-50 py-16">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-8">
          <h1 class="text-4xl lg:text-5xl font-bold text-slate-800 leading-tight tracking-tight mb-8">
            淘沙数据分析助手
          </h1>
          
          <!-- Query Input Section -->
          <div ref="querySection" class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 max-w-5xl mx-auto">
              <div class="flex flex-col lg:flex-row lg:items-center gap-4">
                <!-- 查询输入 -->
                <div class="lg:flex-[3]">
                  <label class="block text-sm font-medium text-slate-700 mb-2">
                    请输入您的问题：
                  </label>
                  <input
                    v-model="queryInput"
                    type="text"
                    placeholder="例如：显示北京地区本月的销售额，最近一周电子产品销量统计"
                    class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200"
                    @keydown.enter.ctrl="submitQuery"
                  />
                </div>
                
                <!-- 控制区域 -->
                <div class="lg:flex-[1] flex items-center gap-4">
                  <div class="flex items-center space-x-2">
                    <label class="text-sm text-slate-600">重试:</label>
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
                    class="px-6 py-3 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 hover:scale-105 hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:hover:shadow-none whitespace-nowrap"
                  >
                    <span v-if="!isQuerying" class="flex items-center space-x-2">
                      <MagnifyingGlassIcon class="w-5 h-5" />
                      <span>开始查询</span>
                    </span>
                    <span v-else class="flex items-center space-x-2">
                      <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>分析中...</span>
                    </span>
                  </button>
                </div>
              </div>

            <div class="mt-4 flex items-center space-x-2 text-sm text-slate-500">
              <LightBulbIcon class="w-4 h-4 text-amber-500" aria-label="提示图标" />
              <span>提示：尽量明确时间范围、统计指标和筛选条件，这样能得到更准确的结果</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Floating Query Bar -->
    <div 
      v-show="showFloatingBar" 
      class="fixed top-20 left-0 right-0 z-40 transition-all duration-300 transform"
      :class="showFloatingBar ? 'translate-y-0 opacity-100' : '-translate-y-full opacity-0'"
    >
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="bg-white rounded-xl shadow-lg border border-slate-200 p-4">
          <div class="flex flex-col sm:flex-row sm:items-center gap-3">
            <!-- 查询输入 -->
            <div class="sm:flex-[3]">
              <input
                v-model="queryInput"
                type="text"
                placeholder="例如：显示北京地区本月的销售额，最近一周电子产品销量统计"
                class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 text-sm"
                @keydown.enter.ctrl="submitQuery"
              />
            </div>
            
            <!-- 控制区域 -->
            <div class="sm:flex-[1] flex items-center gap-3">
              <div class="flex items-center space-x-2">
                <label class="text-sm text-slate-600">重试:</label>
                <select 
                  v-model="maxRetries"
                  class="px-2 py-1 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
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
                class="px-4 py-2 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 hover:scale-105 hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:hover:shadow-none whitespace-nowrap text-sm"
              >
                <span v-if="!isQuerying" class="flex items-center space-x-1">
                  <MagnifyingGlassIcon class="w-4 h-4" />
                  <span>查询</span>
                </span>
                <span v-else class="flex items-center space-x-1">
                  <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
                  <span>分析中</span>
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

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


  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { 
  MagnifyingGlassIcon, 
  ExclamationTriangleIcon,
  LightBulbIcon
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
const querySection = ref<HTMLElement>()
const showFloatingBar = ref(false)


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

// 滚动监听
const handleScroll = () => {
  if (!querySection.value) return
  
  const rect = querySection.value.getBoundingClientRect()
  // 当原始搜索框滚出视窗时显示浮动搜索框
  showFloatingBar.value = rect.bottom < 80
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
  
  // 添加事件监听
  document.addEventListener('keydown', handleKeyDown)
  window.addEventListener('scroll', handleScroll, { passive: true })

  return () => {
    document.removeEventListener('keydown', handleKeyDown)
    window.removeEventListener('scroll', handleScroll)
  }
})

onUnmounted(() => {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval)
  }
  // 移除滚动监听
  window.removeEventListener('scroll', handleScroll)
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