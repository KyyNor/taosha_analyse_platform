<template>
  <MainLayout>
    <div class="space-y-6">
      <!-- Page Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold">淘沙查询</h1>
          <p class="text-base-content/60 mt-1">使用自然语言进行数据查询分析</p>
        </div>
        <div class="flex gap-2">
          <button
            @click="showHistory = !showHistory"
            class="btn btn-ghost btn-sm"
            :class="{ 'btn-active': showHistory }"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            查询历史
          </button>
          <button
            @click="showFavorites = !showFavorites"
            class="btn btn-ghost btn-sm"
            :class="{ 'btn-active': showFavorites }"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
            </svg>
            我的收藏
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Left Column: Query Form & Progress -->
        <div class="lg:col-span-1 space-y-6">
          <!-- Query Form -->
          <QueryForm
            :initial-query="initialQuery"
            @submit="handleSubmitQuery"
            @cancel="handleCancelQuery"
          />

          <!-- Query Progress -->
          <QueryProgress
            v-if="hasActiveQuery"
            @cancel="handleCancelQuery"
            @copySQL="handleCopySQL"
          />
        </div>

        <!-- Right Column: Results & History/Favorites -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Query Results -->
          <div v-if="hasResults" class="card bg-base-100 shadow-lg">
            <div class="card-body">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold">查询结果</h3>
                <div class="flex gap-2">
                  <button
                    @click="addToFavorites"
                    class="btn btn-ghost btn-sm"
                    :disabled="!currentResult"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                    </svg>
                    收藏
                  </button>
                  <div class="dropdown dropdown-end">
                    <label tabindex="0" class="btn btn-ghost btn-sm">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      导出
                    </label>
                    <ul tabindex="0" class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-32">
                      <li><a @click="exportResults('csv')">CSV</a></li>
                      <li><a @click="exportResults('xlsx')">Excel</a></li>
                    </ul>
                  </div>
                </div>
              </div>

              <!-- Results Table -->
              <QueryResultsTable
                :data="resultData"
                :generated-sql="generatedSQL"
                :loading="isQueryRunning"
              />
            </div>
          </div>

          <!-- Query History -->
          <div v-if="showHistory" class="card bg-base-100 shadow-lg">
            <div class="card-body">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold">查询历史</h3>
                <div class="flex gap-2">
                  <input
                    v-model="historySearchQuery"
                    type="text"
                    placeholder="搜索历史..."
                    class="input input-bordered input-sm w-48"
                  />
                  <select
                    v-model="historyFilter"
                    class="select select-bordered select-sm"
                  >
                    <option value="">全部状态</option>
                    <option value="success">成功</option>
                    <option value="failed">失败</option>
                    <option value="running">运行中</option>
                  </select>
                </div>
              </div>

              <QueryHistoryList
                :history="filteredHistory"
                :loading="historyLoading"
                @rerun="handleRerunQuery"
                @view-details="handleViewHistoryDetails"
              />
            </div>
          </div>

          <!-- Favorites -->
          <div v-if="showFavorites" class="card bg-base-100 shadow-lg">
            <div class="card-body">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold">我的收藏</h3>
                <input
                  v-model="favoritesSearchQuery"
                  type="text"
                  placeholder="搜索收藏..."
                  class="input input-bordered input-sm w-48"
                />
              </div>

              <FavoritesList
                :favorites="filteredFavorites"
                :loading="favoritesLoading"
                @execute="handleExecuteFavorite"
                @edit="handleEditFavorite"
                @delete="handleDeleteFavorite"
              />
            </div>
          </div>

          <!-- Welcome State (when no results and not showing history/favorites) -->
          <div v-if="!hasResults && !showHistory && !showFavorites" class="card bg-base-100 shadow-lg">
            <div class="card-body text-center py-12">
              <div class="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 class="text-lg font-semibold mb-2">开始您的数据探索之旅</h3>
              <p class="text-base-content/60 mb-6 max-w-md mx-auto">
                使用自然语言描述您的查询需求，AI 将为您生成相应的 SQL 查询并执行分析。
              </p>
              <div class="flex flex-wrap gap-2 justify-center">
                <button
                  v-for="example in quickExamples"
                  :key="example"
                  @click="handleExampleClick(example)"
                  class="btn btn-outline btn-sm"
                >
                  {{ example }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add to Favorites Modal -->
    <dialog ref="addToFavoritesModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">添加到收藏</h3>
        <div class="form-control mt-4">
          <label class="label">
            <span class="label-text">收藏标题</span>
          </label>
          <input
            v-model="favoriteTitle"
            type="text"
            placeholder="请输入收藏标题..."
            class="input input-bordered"
            ref="favoriteTitleInput"
          />
        </div>
        <div class="modal-action">
          <button @click="closeAddToFavoritesModal" class="btn btn-ghost">取消</button>
          <button @click="confirmAddToFavorites" class="btn btn-primary" :disabled="!favoriteTitle.trim()">
            确认添加
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>
  </MainLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useQueryStore } from '@stores/query'
import { useToast } from '@/composables/useToast'
import MainLayout from '@/components/layout/MainLayout.vue'
import QueryForm from '@/components/common/QueryForm.vue'
import QueryProgress from '@/components/common/QueryProgress.vue'
import QueryResultsTable from '@/components/query/QueryResultsTable.vue'
import QueryHistoryList from '@/components/query/QueryHistoryList.vue'
import FavoritesList from '@/components/query/FavoritesList.vue'
import type { QueryRequest, QueryLog, Favorite } from '@types/index'

const queryStore = useQueryStore()
const { success, error, info } = useToast()

// UI state
const showHistory = ref(false)
const showFavorites = ref(false)
const initialQuery = ref('')
const historySearchQuery = ref('')
const historyFilter = ref('')
const favoritesSearchQuery = ref('')
const historyLoading = ref(false)
const favoritesLoading = ref(false)

// Modal state
const addToFavoritesModal = ref<HTMLDialogElement>()
const favoriteTitle = ref('')
const favoriteTitleInput = ref<HTMLInputElement>()

// Quick examples
const quickExamples = [
  '显示最近一个月的销售数据',
  '查询各产品类别的销售占比',
  '找出注册用户最多的地区',
  '分析订单金额分布情况'
]

// Computed properties
const hasActiveQuery = computed(() => queryStore.hasActiveQuery)
const isQueryRunning = computed(() => queryStore.isQueryRunning)
const hasResults = computed(() => queryStore.hasResults)
const currentResult = computed(() => queryStore.currentResult)
const resultData = computed(() => queryStore.resultData)
const generatedSQL = computed(() => queryStore.generatedSQL)

const queryHistory = computed(() => queryStore.queryHistory)
const favorites = computed(() => queryStore.favorites)

const filteredHistory = computed(() => {
  let filtered = queryHistory.value

  if (historySearchQuery.value) {
    const query = historySearchQuery.value.toLowerCase()
    filtered = filtered.filter(item =>
      item.query.toLowerCase().includes(query) ||
      item.generatedSql?.toLowerCase().includes(query)
    )
  }

  if (historyFilter.value) {
    filtered = filtered.filter(item => item.status === historyFilter.value)
  }

  return filtered
})

const filteredFavorites = computed(() => {
  if (!favoritesSearchQuery.value) return favorites.value

  const query = favoritesSearchQuery.value.toLowerCase()
  return favorites.value.filter(item =>
    item.favoriteTitle.toLowerCase().includes(query) ||
    item.userQuestion.toLowerCase().includes(query)
  )
})

// Load data
const loadHistory = async () => {
  try {
    historyLoading.value = true
    await queryStore.loadQueryHistory()
  } catch (err) {
    error('加载查询历史失败')
  } finally {
    historyLoading.value = false
  }
}

const loadFavorites = async () => {
  try {
    favoritesLoading.value = true
    await queryStore.loadFavorites()
  } catch (err) {
    error('加载收藏列表失败')
  } finally {
    favoritesLoading.value = false
  }
}

// Handle query submission
const handleSubmitQuery = async (request: QueryRequest) => {
  try {
    await queryStore.submitQuery(request)
    success('查询已提交，正在处理...')
    showHistory.value = false
    showFavorites.value = false
  } catch (err) {
    error('查询提交失败')
  }
}

// Handle query cancellation
const handleCancelQuery = async () => {
  try {
    await queryStore.cancelQuery()
    info('查询已取消')
  } catch (err) {
    error('取消查询失败')
  }
}

// Handle example click
const handleExampleClick = (example: string) => {
  initialQuery.value = example
  nextTick(() => {
    initialQuery.value = ''
  })
}

// Handle SQL copy
const handleCopySQL = (sql: string) => {
  navigator.clipboard.writeText(sql)
  success('SQL 已复制到剪贴板')
}

// Handle export results
const exportResults = async (format: 'csv' | 'xlsx') => {
  if (!currentResult.value) return

  try {
    await queryStore.exportResults(currentResult.value.taskId, format)
    success(`正在导出 ${format.toUpperCase()} 文件...`)
  } catch (err) {
    error('导出失败')
  }
}

// Handle add to favorites
const addToFavorites = () => {
  if (!currentResult.value) return

  favoriteTitle.value = `查询 - ${new Date().toLocaleString()}`
  addToFavoritesModal.value?.showModal()

  nextTick(() => {
    favoriteTitleInput.value?.focus()
    favoriteTitleInput.value?.select()
  })
}

const closeAddToFavoritesModal = () => {
  addToFavoritesModal.value?.close()
  favoriteTitle.value = ''
}

const confirmAddToFavorites = async () => {
  if (!currentResult.value || !favoriteTitle.value.trim()) return

  try {
    await queryStore.addToFavorites(currentResult.value.taskId, favoriteTitle.value.trim())
    success('已添加到收藏')
    closeAddToFavoritesModal()
    if (showFavorites.value) {
      await loadFavorites()
    }
  } catch (err) {
    error('添加到收藏失败')
  }
}

// Handle history actions
const handleRerunQuery = async (taskId: string) => {
  try {
    await queryStore.rerunQuery(taskId)
    success('正在重新执行查询...')
    showHistory.value = false
  } catch (err) {
    error('重新执行查询失败')
  }
}

const handleViewHistoryDetails = (log: QueryLog) => {
  // 可以在这里显示详情模态框或导航到详情页面
  info(`查看查询详情: ${log.query}`)
}

// Handle favorites actions
const handleExecuteFavorite = async (favoriteId: number) => {
  try {
    await queryStore.executeFavorite(favoriteId)
    success('正在执行收藏的查询...')
    showFavorites.value = false
  } catch (err) {
    error('执行收藏查询失败')
  }
}

const handleEditFavorite = async (favoriteId: number, newTitle: string) => {
  try {
    await queryStore.updateFavorite(favoriteId, newTitle)
    success('收藏已更新')
  } catch (err) {
    error('更新收藏失败')
  }
}

const handleDeleteFavorite = async (favoriteId: number) => {
  if (!confirm('确定要删除这个收藏吗？')) return

  try {
    await queryStore.deleteFavorite(favoriteId)
    success('收藏已删除')
  } catch (err) {
    error('删除收藏失败')
  }
}

// Initialize
onMounted(async () => {
  await Promise.all([
    loadHistory(),
    loadFavorites()
  ])
})
</script>