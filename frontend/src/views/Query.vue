<template>
<template>
  <div class="min-h-screen bg-base-100">
    <!-- 导航栏 -->
    <div class="navbar bg-base-200 shadow-lg">
      <div class="navbar-start">
        <div class="dropdown">
          <label tabindex="0" class="btn btn-ghost lg:hidden">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"></path>
            </svg>
          </label>
          <ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
            <li><RouterLink to="/query">智能查询</RouterLink></li>
            <li><RouterLink to="/history">查询历史</RouterLink></li>
            <li><RouterLink to="/favorites">收藏查询</RouterLink></li>
            <li v-if="authStore.hasPermission('metadata:read')">
              <details>
                <summary>元数据管理</summary>
                <ul class="p-2">
                  <li><RouterLink to="/metadata/tables">表管理</RouterLink></li>
                  <li><RouterLink to="/metadata/fields">字段管理</RouterLink></li>
                  <li><RouterLink to="/metadata/glossary">术语管理</RouterLink></li>
                  <li><RouterLink to="/metadata/themes">主题管理</RouterLink></li>
                </ul>
              </details>
            </li>
          </ul>
        </div>
        <RouterLink to="/" class="btn btn-ghost normal-case text-xl font-bold text-primary">
          淘沙分析平台
        </RouterLink>
      </div>
      
      <div class="navbar-center hidden lg:flex">
        <ul class="menu menu-horizontal px-1">
          <li><RouterLink to="/query" class="btn btn-ghost">智能查询</RouterLink></li>
          <li><RouterLink to="/history" class="btn btn-ghost">查询历史</RouterLink></li>
          <li><RouterLink to="/favorites" class="btn btn-ghost">收藏查询</RouterLink></li>
          <li v-if="authStore.hasPermission('metadata:read')" class="dropdown dropdown-hover">
            <label tabindex="0" class="btn btn-ghost">元数据管理</label>
            <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52">
              <li><RouterLink to="/metadata/tables">表管理</RouterLink></li>
              <li><RouterLink to="/metadata/fields">字段管理</RouterLink></li>
              <li><RouterLink to="/metadata/glossary">术语管理</RouterLink></li>
              <li><RouterLink to="/metadata/themes">主题管理</RouterLink></li>
            </ul>
          </li>
        </ul>
      </div>
      
      <div class="navbar-end">
        <!-- 主题切换 -->
        <button 
          @click="themeStore.toggleTheme()" 
          class="btn btn-ghost btn-circle"
          :title="themeStore.isDarkTheme() ? '切换到浅色主题' : '切换到深色主题'"
        >
          <span class="text-lg">{{ themeStore.getThemeIcon() }}</span>
        </button>
        
        <!-- 用户菜单 -->
        <div class="dropdown dropdown-end">
          <label tabindex="0" class="btn btn-ghost btn-circle avatar">
            <div class="w-8 rounded-full">
              <img v-if="authStore.user?.avatar" :src="authStore.user?.avatar" :alt="authStore.user?.nickname" />
              <div v-else class="bg-primary text-primary-content w-8 h-8 rounded-full flex items-center justify-center">
                {{ authStore.user?.nickname?.charAt(0) || 'U' }}
              </div>
            </div>
          </label>
          <ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
            <li class="menu-title">
              <span>{{ authStore.user?.nickname }}</span>
            </li>
            <li><a>个人设置</a></li>
            <li><a>帮助文档</a></li>
            <li><hr class="my-2"></li>
            <li><a @click="handleLogout" class="text-error">退出登录</a></li>
          </ul>
        </div>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <main class="container mx-auto px-4 py-6">
    <div class="page-header">
      <h1 class="page-title">智能查询</h1>
      <p class="page-subtitle">使用自然语言描述您的数据需求，系统将自动生成SQL并执行查询</p>
    </div>

    <!-- 查询界面 -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- 查询输入区域 -->
      <div class="lg:col-span-2">
        <div class="card bg-base-100 shadow-md">
          <div class="card-body">
            <h2 class="card-title">查询输入</h2>
            
            <!-- 数据主题选择 -->
            <div class="form-control">
              <label class="label">
                <span class="label-text font-medium">选择数据主题</span>
              </label>
              <select v-model="selectedTheme" class="select select-bordered w-full">
                <option value="">请选择数据主题...</option>
                <option v-for="theme in themes" :key="theme.id" :value="theme.id">
                  {{ theme.theme_name }} {{ theme.is_public ? '(公共)' : '' }}
                </option>
              </select>
            </div>

            <!-- 表选择 -->
            <div v-if="selectedTheme" class="form-control">
              <label class="label">
                <span class="label-text font-medium">选择数据表 (可选)</span>
              </label>
              <div class="flex flex-wrap gap-2">
                <label 
                  v-for="table in availableTables" 
                  :key="table.id"
                  class="cursor-pointer label"
                >
                  <input 
                    v-model="selectedTables" 
                    :value="table.id" 
                    type="checkbox" 
                    class="checkbox checkbox-primary checkbox-sm"
                  />
                  <span class="label-text ml-2">{{ table.table_name_cn }}</span>
                </label>
              </div>
            </div>

            <!-- 自然语言输入 -->
            <div class="form-control">
              <label class="label">
                <span class="label-text font-medium">描述您的查询需求</span>
                <span class="label-text-alt">支持中文自然语言</span>
              </label>
              <textarea 
                v-model="queryText"
                class="textarea textarea-bordered h-32 resize-none"
                placeholder="例如：查询最近30天每天的订单数量和销售金额，按日期排序"
                :disabled="isQuerying"
              ></textarea>
            </div>

            <!-- 操作按钮 -->
            <div class="card-actions justify-end">
              <button 
                @click="clearQuery" 
                class="btn btn-ghost"
                :disabled="isQuerying"
              >
                清空
              </button>
              <button 
                v-if="isQuerying"
                @click="cancelQuery" 
                class="btn btn-warning"
              >
                取消查询
              </button>
              <button 
                v-else
                @click="submitQuery" 
                class="btn btn-primary"
                :disabled="!canSubmit"
              >
                开始查询
              </button>
            </div>
          </div>
        </div>

        <!-- 查询结果区域 -->
        <div v-if="currentTask" class="card bg-base-100 shadow-md mt-6">
          <div class="card-body">
            <h2 class="card-title">查询结果</h2>
            
            <!-- 查询进度 -->
            <QueryProgress
              v-if="isQuerying"
              :current-step="currentTask.current_step || '准备中...'"
              :progress-percentage="Math.round((currentTask.progress_percentage || 0) * 100)"
              :logs="currentTask.logs || []"
              :cancellable="true"
              @cancel="cancelQuery"
            />
            
            <!-- 生成的SQL -->
            <div v-if="currentTask.generated_sql" class="space-y-2">
              <div class="flex items-center justify-between">
                <h3 class="font-semibold">生成的SQL</h3>
                <div class="space-x-2">
                  <span v-if="currentTask.sql_confidence" class="badge badge-info">
                    置信度: {{ Math.round(currentTask.sql_confidence * 100) }}%
                  </span>
                  <button @click="copySql" class="btn btn-ghost btn-sm">复制</button>
                </div>
              </div>
              <div class="mockup-code">
                <pre><code>{{ currentTask.generated_sql }}</code></pre>
              </div>
            </div>
            
            <!-- 查询结果展示 -->
            <QueryResult
              v-if="queryResult && queryResult.rows && queryResult.rows.length > 0"
              :result="queryResult"
              @export="handleExportResult"
            />
            
            <!-- 空结果提示 -->
            <div v-else-if="queryResult && (!queryResult.rows || queryResult.rows.length === 0)" class="text-center py-8">
              <svg class="w-16 h-16 mx-auto mb-4 text-base-content text-opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p class="text-base-content text-opacity-60">查询执行成功，但没有返回数据</p>
              <p class="text-sm text-base-content text-opacity-40 mt-2">请检查查询条件或数据范围</p>
            </div>

            <!-- 错误信息 -->
            <div v-if="currentTask.error_message" class="alert alert-error">
              <svg class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <h3 class="font-bold">查询执行失败</h3>
                <div class="text-xs">{{ currentTask.error_message }}</div>
                <div v-if="currentTask.error_details" class="text-xs mt-2 opacity-75">
                  <details>
                    <summary class="cursor-pointer">查看详细错误信息</summary>
                    <pre class="mt-2 text-xs">{{ currentTask.error_details }}</pre>
                  </details>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 侧边栏 -->
      <div class="space-y-6">
        <!-- 查询示例 -->
        <div class="card bg-base-100 shadow-md">
          <div class="card-body">
            <h2 class="card-title text-base">查询示例</h2>
            <div class="space-y-2">
              <div 
                v-for="example in queryExamples" 
                :key="example.id"
                @click="useExample(example.query)"
                class="p-3 bg-base-200 rounded-lg cursor-pointer hover:bg-base-300 transition-colors"
              >
                <p class="text-sm font-medium">{{ example.title }}</p>
                <p class="text-xs text-base-content text-opacity-70 mt-1">{{ example.query }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 最近查询 -->
        <div class="card bg-base-100 shadow-md">
          <div class="card-body">
            <h2 class="card-title text-base">最近查询</h2>
            <div class="space-y-2">
              <div 
                v-for="history in recentQueries" 
                :key="history.id"
                @click="useHistory(history)"
                class="p-3 bg-base-200 rounded-lg cursor-pointer hover:bg-base-300 transition-colors"
              >
                <p class="text-sm">{{ history.user_question }}</p>
                <p class="text-xs text-base-content text-opacity-70 mt-1">
                  {{ formatDate(history.created_at) }}
                </p>
              </div>
              <div v-if="recentQueries.length === 0" class="text-sm text-base-content text-opacity-50 text-center py-4">
                暂无查询记录
              </div>
            </div>
          </div>
        </div>
    </main>

    <!-- 通知组件 -->
    <div class="toast toast-end">
      <div 
        v-for="notification in notificationStore.notifications" 
        :key="notification.id"
        :class="['alert', notificationStore.getAlertClass(notification.type)]"
        class="mb-2"
      >
        <span>{{ notificationStore.getIcon(notification.type) }}</span>
        <div>
          <h4 v-if="notification.title" class="font-bold">{{ notification.title }}</h4>
          <div class="text-xs">{{ notification.message }}</div>
        </div>
        <button 
          @click="notificationStore.removeNotification(notification.id)"
          class="btn btn-sm btn-circle"
        >
          ✕
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useNotificationStore } from '@/stores/notification'
import { useQueryStore } from '@/stores/query'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { metadataApi } from '@/api/metadata'
import QueryProgress from '@/components/QueryProgress.vue'
import QueryResult from '@/components/QueryResult.vue'
import type { Theme, Table, QueryHistory } from '@/types'

const router = useRouter()
const notificationStore = useNotificationStore()
const queryStore = useQueryStore()
const authStore = useAuthStore()
const themeStore = useThemeStore()

// 响应式数据
const selectedTheme = ref<number | string>('')
const selectedTables = ref<number[]>([])
const queryText = ref('')
const themes = ref<Theme[]>([])
const availableTables = ref<Table[]>([])
const recentQueries = ref<QueryHistory[]>([])

// 查询示例
const queryExamples = ref([
  {
    id: 1,
    title: '每日订单统计',
    query: '查询最近30天每天的订单数量和销售金额，按日期排序'
  },
  {
    id: 2,
    title: '用户活跃度分析',
    query: '统计最近一个月每天的活跃用户数量'
  },
  {
    id: 3,
    title: '热销产品排行',
    query: '查询本月销量前10的产品，包含产品名称和销量'
  }
])

// 计算属性
const canSubmit = computed(() => {
  return selectedTheme.value && queryText.value.trim().length > 0
})

const currentTask = computed(() => queryStore.currentTask)
const isQuerying = computed(() => queryStore.isQuerying)
const queryResult = computed(() => queryStore.queryResult)

// 监听主题选择变化
watch(selectedTheme, async (newTheme) => {
  if (newTheme) {
    await loadTablesForTheme(Number(newTheme))
  } else {
    availableTables.value = []
  }
  selectedTables.value = []
})

// 方法
const loadThemes = async () => {
  try {
    const response = await metadataApi.getThemes()
    themes.value = response.data
  } catch (error) {
    console.error('加载数据主题失败:', error)
    notificationStore.error('加载数据主题失败')
  }
}

const loadTablesForTheme = async (themeId: number) => {
  try {
    const response = await metadataApi.getTablesByTheme(themeId)
    availableTables.value = response.data
  } catch (error) {
    console.error('加载数据表失败:', error)
    notificationStore.error('加载数据表失败')
  }
}

const loadRecentQueries = async () => {
  try {
    // TODO: 实现查询历史API调用
    // const response = await queryApi.getRecentQueries()
    // recentQueries.value = response.data
  } catch (error) {
    console.error('加载查询历史失败:', error)
  }
}

const clearQuery = () => {
  queryText.value = ''
  selectedTables.value = []
  queryStore.clearCurrentTask()
}

const submitQuery = async () => {
  if (!canSubmit.value) return
  
  try {
    const queryRequest = {
      user_question: queryText.value,
      theme_id: Number(selectedTheme.value),
      table_ids: selectedTables.value,
      context: {
        selected_theme: themes.value.find(t => t.id === Number(selectedTheme.value))?.theme_name,
        selected_tables: availableTables.value.filter(t => selectedTables.value.includes(t.id)).map(t => t.table_name_cn)
      }
    }
    
    await queryStore.submitQuery(queryRequest)
    notificationStore.success('查询任务已提交，正在处理中...')
  } catch (error) {
    console.error('提交查询失败:', error)
    notificationStore.error('提交查询失败，请重试')
  }
}

const cancelQuery = async () => {
  try {
    await queryStore.cancelQuery()
    notificationStore.info('查询已取消')
  } catch (error) {
    console.error('取消查询失败:', error)
    notificationStore.error('取消查询失败')
  }
}

const useExample = (query: string) => {
  queryText.value = query
  if (themes.value.length > 0) {
    selectedTheme.value = themes.value[0].id
  }
}

const useHistory = (history: QueryHistory) => {
  queryText.value = history.user_question
  selectedTheme.value = history.theme_id || (themes.value.length > 0 ? themes.value[0].id : '')
}

const copySql = () => {
  if (currentTask.value?.generated_sql) {
    navigator.clipboard.writeText(currentTask.value.generated_sql)
    notificationStore.success('SQL已复制到剪贴板')
  }
}

const exportResult = (format: string) => {
  if (!queryResult.value) {
    notificationStore.warning('没有可导出的查询结果')
    return
  }
  
  // TODO: 实现结果导出功能
  notificationStore.info(`导出${format.toUpperCase()}功能开发中...`)
}

const handleExportResult = (data: any) => {
  // 处理结果导出
  const { format, columns, rows, metadata } = data
  
  try {
    switch (format) {
      case 'csv':
        exportToCSV(columns, rows)
        break
      case 'excel':
        exportToExcel(columns, rows, metadata)
        break
      case 'json':
        exportToJSON({ columns, rows, metadata })
        break
      default:
        notificationStore.error('不支持的导出格式')
    }
  } catch (error) {
    console.error('导出失败:', error)
    notificationStore.error('导出失败，请重试')
  }
}

const exportToCSV = (columns: string[], rows: any[][]) => {
  const csvContent = [
    columns.join(','),
    ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
  ].join('\n')
  
  downloadFile(csvContent, 'query-result.csv', 'text/csv')
  notificationStore.success('CSV文件已下载')
}

const exportToJSON = (data: any) => {
  const jsonContent = JSON.stringify(data, null, 2)
  downloadFile(jsonContent, 'query-result.json', 'application/json')
  notificationStore.success('JSON文件已下载')
}

const exportToExcel = (columns: string[], rows: any[][], metadata: any) => {
  // TODO: 实现Excel导出
  notificationStore.info('Excel导出功能开发中...')
}

const downloadFile = (content: string, filename: string, type: string) => {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

const formatTime = (timestamp: string | number) => {
  return new Date(timestamp).toLocaleTimeString('zh-CN')
}

// 处理登出
const handleLogout = () => {
  authStore.logout()
  notificationStore.success('已退出登录')
  router.push('/login')
}

onMounted(async () => {
  await loadThemes()
  await loadRecentQueries()
  
  // 初始化WebSocket连接
  try {
    await queryStore.initWebSocketConnection()
  } catch (error) {
    console.warn('WebSocket连接失败，将使用轮询方式:', error)
  }
})
</script>