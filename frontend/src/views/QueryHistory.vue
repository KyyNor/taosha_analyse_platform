<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">查询历史</h1>
      <p class="page-subtitle">管理您的查询记录，重新执行或收藏常用查询</p>
    </div>

    <!-- 筛选和搜索 -->
    <div class="card bg-base-100 shadow-md mb-6">
      <div class="card-body">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <!-- 搜索框 -->
          <div class="form-control">
            <input 
              v-model="searchKeyword"
              type="text" 
              placeholder="搜索查询内容..." 
              class="input input-bordered"
              @input="handleSearch"
            />
          </div>
          
          <!-- 状态筛选 -->
          <div class="form-control">
            <select v-model="selectedStatus" class="select select-bordered" @change="handleFilter">
              <option value="">全部状态</option>
              <option value="completed">已完成</option>
              <option value="failed">已失败</option>
              <option value="cancelled">已取消</option>
            </select>
          </div>
          
          <!-- 主题筛选 -->
          <div class="form-control">
            <select v-model="selectedTheme" class="select select-bordered" @change="handleFilter">
              <option value="">全部主题</option>
              <option v-for="theme in themes" :key="theme.id" :value="theme.id">
                {{ theme.theme_name }}
              </option>
            </select>
          </div>
          
          <!-- 时间范围 -->
          <div class="form-control">
            <select v-model="dateRange" class="select select-bordered" @change="handleFilter">
              <option value="7">最近7天</option>
              <option value="30">最近30天</option>
              <option value="90">最近90天</option>
              <option value="">全部</option>
            </select>
          </div>
        </div>
        
        <!-- 操作按钮 -->
        <div class="flex justify-between items-center mt-4">
          <div class="flex items-center space-x-2">
            <input 
              v-model="selectAll" 
              type="checkbox" 
              class="checkbox checkbox-primary"
              @change="handleSelectAll"
            />
            <span class="text-sm">全选</span>
            
            <button 
              v-if="selectedHistories.length > 0"
              @click="batchDelete"
              class="btn btn-error btn-sm ml-4"
            >
              批量删除 ({{ selectedHistories.length }})
            </button>
          </div>
          
          <div class="flex space-x-2">
            <button @click="refreshHistory" class="btn btn-ghost btn-sm">
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              刷新
            </button>
            
            <button @click="exportHistory" class="btn btn-primary btn-sm">
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              导出
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 查询历史列表 -->
    <div class="space-y-4">
      <div v-if="loading" class="text-center py-8">
        <span class="loading loading-spinner loading-lg"></span>
        <p class="mt-2">加载中...</p>
      </div>
      
      <div v-else-if="histories.length === 0" class="text-center py-12">
        <svg class="w-16 h-16 mx-auto mb-4 text-base-content text-opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p class="text-base-content text-opacity-60">暂无查询历史</p>
        <p class="text-sm text-base-content text-opacity-40 mt-2">开始您的第一次查询吧</p>
      </div>
      
      <div v-else>
        <div 
          v-for="history in histories" 
          :key="history.id"
          class="card bg-base-100 shadow-md hover:shadow-lg transition-shadow"
        >
          <div class="card-body">
            <div class="flex items-start justify-between">
              <div class="flex items-start space-x-3 flex-1">
                <input 
                  v-model="selectedHistories" 
                  :value="history.id" 
                  type="checkbox" 
                  class="checkbox checkbox-primary mt-1"
                />
                
                <div class="flex-1">
                  <!-- 查询问题 -->
                  <h3 class="font-semibold text-lg mb-2">{{ history.user_question }}</h3>
                  
                  <!-- 元信息 -->
                  <div class="flex flex-wrap items-center gap-4 text-sm text-base-content text-opacity-70 mb-3">
                    <div class="flex items-center space-x-1">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span>{{ formatDate(history.created_at) }}</span>
                    </div>
                    
                    <div v-if="history.theme_name" class="flex items-center space-x-1">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                      </svg>
                      <span>{{ history.theme_name }}</span>
                    </div>
                    
                    <div v-if="history.execution_time_ms" class="flex items-center space-x-1">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      <span>{{ history.execution_time_ms }}ms</span>
                    </div>
                    
                    <div v-if="history.result_count" class="flex items-center space-x-1">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                      <span>{{ history.result_count }} 行</span>
                    </div>
                  </div>
                  
                  <!-- SQL预览 -->
                  <div v-if="history.generated_sql" class="mb-3">
                    <div class="collapse collapse-arrow border border-base-300 bg-base-200">
                      <input type="checkbox" class="peer" />
                      <div class="collapse-title text-sm font-medium">
                        查看生成的SQL
                      </div>
                      <div class="collapse-content">
                        <div class="mockup-code text-xs">
                          <pre><code>{{ history.generated_sql }}</code></pre>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- 错误信息 -->
                  <div v-if="history.status === 'failed' && history.error_message" class="alert alert-error text-sm mb-3">
                    <svg class="stroke-current shrink-0 h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{{ history.error_message }}</span>
                  </div>
                </div>
              </div>
              
              <!-- 状态和操作 -->
              <div class="flex flex-col items-end space-y-2 ml-4">
                <!-- 状态标签 -->
                <div class="badge" :class="getStatusBadgeClass(history.status)">
                  {{ getStatusText(history.status) }}
                </div>
                
                <!-- 收藏状态 -->
                <button 
                  @click="toggleFavorite(history)"
                  class="btn btn-ghost btn-xs"
                  :class="{ 'text-warning': history.is_favorite }"
                >
                  <svg class="w-4 h-4" :fill="history.is_favorite ? 'currentColor' : 'none'" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                  </svg>
                </button>
                
                <!-- 操作菜单 -->
                <div class="dropdown dropdown-end">
                  <label tabindex="0" class="btn btn-ghost btn-sm">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                    </svg>
                  </label>
                  <ul tabindex="0" class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-32">
                    <li><a @click="rerunQuery(history)">重新执行</a></li>
                    <li><a @click="viewDetail(history)">查看详情</a></li>
                    <li><a @click="copySQL(history)">复制SQL</a></li>
                    <li><a @click="deleteHistory(history)" class="text-error">删除</a></li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="pagination.pages > 1" class="flex justify-center mt-8">
      <div class="btn-group">
        <button 
          @click="goToPage(1)"
          class="btn btn-sm"
          :disabled="pagination.page === 1"
        >
          首页
        </button>
        <button 
          @click="goToPage(pagination.page - 1)"
          class="btn btn-sm"
          :disabled="pagination.page === 1"
        >
          上一页
        </button>
        
        <button 
          v-for="page in visiblePages"
          :key="page"
          @click="goToPage(page)"
          class="btn btn-sm"
          :class="{ 'btn-active': pagination.page === page }"
        >
          {{ page }}
        </button>
        
        <button 
          @click="goToPage(pagination.page + 1)"
          class="btn btn-sm"
          :disabled="pagination.page === pagination.pages"
        >
          下一页
        </button>
        <button 
          @click="goToPage(pagination.pages)"
          class="btn btn-sm"
          :disabled="pagination.page === pagination.pages"
        >
          尾页
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/stores/notification'
import { useQueryStore } from '@/stores/query'
import { metadataApi } from '@/api/metadata'
import type { QueryHistory, Theme } from '@/types'

const router = useRouter()
const notificationStore = useNotificationStore()
const queryStore = useQueryStore()

// 响应式数据
const loading = ref(false)
const histories = ref<QueryHistory[]>([])
const themes = ref<Theme[]>([])
const selectedHistories = ref<number[]>([])
const selectAll = ref(false)

// 筛选条件
const searchKeyword = ref('')
const selectedStatus = ref('')
const selectedTheme = ref('')
const dateRange = ref('30')

// 分页
const pagination = ref({
  page: 1,
  page_size: 20,
  total: 0,
  pages: 0
})

// 计算属性
const visiblePages = computed(() => {
  const total = pagination.value.pages
  const current = pagination.value.page
  const pages = []
  
  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    if (current <= 4) {
      for (let i = 1; i <= 5; i++) pages.push(i)
      pages.push('...', total)
    } else if (current >= total - 3) {
      pages.push(1, '...')
      for (let i = total - 4; i <= total; i++) pages.push(i)
    } else {
      pages.push(1, '...')
      for (let i = current - 1; i <= current + 1; i++) pages.push(i)
      pages.push('...', total)
    }
  }
  
  return pages.filter(p => p !== '...' || pages.indexOf(p) === pages.lastIndexOf(p))
})

// 监听全选状态
watch(selectAll, (newVal) => {
  if (newVal) {
    selectedHistories.value = histories.value.map(h => h.id)
  } else {
    selectedHistories.value = []
  }
})

// 监听选中项变化
watch(selectedHistories, (newVal) => {
  selectAll.value = newVal.length === histories.value.length && histories.value.length > 0
}, { deep: true })

// 方法
const loadThemes = async () => {
  try {
    const response = await metadataApi.getThemes()
    themes.value = response.data
  } catch (error) {
    console.error('加载主题失败:', error)
  }
}

const loadHistory = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.page_size,
      status: selectedStatus.value || undefined,
      theme_id: selectedTheme.value ? Number(selectedTheme.value) : undefined,
      keyword: searchKeyword.value || undefined
    }
    
    // 处理时间范围
    if (dateRange.value) {
      const days = Number(dateRange.value)
      const endDate = new Date()
      const startDate = new Date(endDate.getTime() - days * 24 * 60 * 60 * 1000)
      params.start_date = startDate.toISOString()
      params.end_date = endDate.toISOString()
    }
    
    const response = await queryStore.fetchQueryHistory(params)
    histories.value = response.data
    pagination.value = response.pagination
    
  } catch (error) {
    console.error('加载查询历史失败:', error)
    notificationStore.error('加载查询历史失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = debounce(() => {
  pagination.value.page = 1
  loadHistory()
}, 500)

const handleFilter = () => {
  pagination.value.page = 1
  loadHistory()
}

const handleSelectAll = () => {
  // selectAll 的 watch 会处理具体逻辑
}

const goToPage = (page: number) => {
  pagination.value.page = page
  loadHistory()
}

const refreshHistory = () => {
  loadHistory()
}

const rerunQuery = async (history: QueryHistory) => {
  try {
    await queryStore.rerunHistoryQuery(history.id)
    notificationStore.success('查询已重新提交')
    // 跳转到查询页面
    router.push('/query')
  } catch (error) {
    console.error('重新执行查询失败:', error)
    notificationStore.error('重新执行查询失败')
  }
}

const viewDetail = (history: QueryHistory) => {
  // 可以打开详情模态框或跳转到详情页面
  console.log('查看详情:', history)
}

const copySQL = (history: QueryHistory) => {
  if (history.generated_sql) {
    navigator.clipboard.writeText(history.generated_sql)
    notificationStore.success('SQL已复制到剪贴板')
  } else {
    notificationStore.warning('该查询没有生成SQL')
  }
}

const deleteHistory = async (history: QueryHistory) => {
  if (!confirm('确定要删除这条查询历史吗？')) {
    return
  }
  
  try {
    // TODO: 调用删除API
    notificationStore.success('查询历史已删除')
    await loadHistory()
  } catch (error) {
    console.error('删除查询历史失败:', error)
    notificationStore.error('删除查询历史失败')
  }
}

const batchDelete = async () => {
  if (!confirm(`确定要删除选中的 ${selectedHistories.value.length} 条查询历史吗？`)) {
    return
  }
  
  try {
    // TODO: 调用批量删除API
    notificationStore.success(`已删除 ${selectedHistories.value.length} 条查询历史`)
    selectedHistories.value = []
    selectAll.value = false
    await loadHistory()
  } catch (error) {
    console.error('批量删除失败:', error)
    notificationStore.error('批量删除失败')
  }
}

const toggleFavorite = async (history: QueryHistory) => {
  try {
    if (history.is_favorite) {
      // TODO: 调用取消收藏API
      history.is_favorite = false
      notificationStore.info('已取消收藏')
    } else {
      // TODO: 调用添加收藏API
      history.is_favorite = true
      notificationStore.success('已添加到收藏')
    }
  } catch (error) {
    console.error('操作收藏失败:', error)
    notificationStore.error('操作收藏失败')
  }
}

const exportHistory = () => {
  // TODO: 实现导出功能
  notificationStore.info('导出功能开发中...')
}

const getStatusBadgeClass = (status: string) => {
  switch (status) {
    case 'completed':
      return 'badge-success'
    case 'failed':
      return 'badge-error'
    case 'cancelled':
      return 'badge-warning'
    case 'processing':
      return 'badge-info'
    default:
      return 'badge-neutral'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'completed':
      return '已完成'
    case 'failed':
      return '已失败'
    case 'cancelled':
      return '已取消'
    case 'processing':
      return '处理中'
    case 'pending':
      return '等待中'
    default:
      return '未知'
  }
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 防抖函数
function debounce(func: Function, wait: number) {
  let timeout: NodeJS.Timeout
  return function executedFunction(...args: any[]) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

onMounted(async () => {
  await loadThemes()
  await loadHistory()
})
</script>