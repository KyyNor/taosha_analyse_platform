<template>
  <div class="space-y-4">
    <!-- Page Header -->
    <div class="grid grid-cols-1 gap-4">
      <!-- Query Form -->
      <div class="space-y-4">
        <!-- Query Form -->
        <QueryForm
          :initial-query="initialQuery"
          @submit="handleSubmitQuery"
          @cancel="handleCancelQuery"
        />
      </div>

      <!-- Query Results -->
      <div class="space-y-4">
        <!-- Query Results -->
        <div
          v-if="hasResults"
          class="card bg-base-100 shadow-lg"
        >
          <div class="card-body">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold">
                查询结果
              </h3>
              <div class="flex gap-2">
                <button
                  class="btn btn-ghost btn-sm"
                  :disabled="!currentResult"
                  @click="addToFavorites"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
                    />
                  </svg>
                  收藏
                </button>
                <div class="dropdown dropdown-end">
                  <label
                    tabindex="0"
                    class="btn btn-ghost btn-sm"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    导出
                  </label>
                  <ul
                    tabindex="0"
                    class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-32"
                  >
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

        <!-- Welcome State (when no results and no active query) -->
        <div
          v-if="!hasResults && !hasActiveQuery"
          class="card bg-base-100 shadow-lg"
        >
          <div class="card-body text-center py-12">
            <div class="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-8 w-8 text-primary"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
            <h3 class="text-lg font-semibold mb-2">
              开始您的数据探索之旅
            </h3>
            <p class="text-base-content/60 mb-6 max-w-md mx-auto">
              使用自然语言描述您的查询需求，AI 将为您生成相应的 SQL 查询并执行分析。
            </p>
            <div class="flex flex-wrap gap-2 justify-center">
              <button
                v-for="example in quickExamples"
                :key="example"
                class="btn btn-outline btn-sm"
                @click="handleExampleClick(example)"
              >
                {{ example }}
              </button>
            </div>
          </div>
        </div>

        <!-- Query Progress -->
        <QueryProgress
          v-if="hasActiveQuery"
          @cancel="handleCancelQuery"
          @copy-s-q-l="handleCopySQL"
        />
      </div>
    </div>

    <!-- Add to Favorites Modal -->
    <dialog
      ref="addToFavoritesModal"
      class="modal"
    >
      <div class="modal-box">
        <h3 class="font-bold text-lg">
          添加到收藏
        </h3>
        <div class="form-control mt-4">
          <label class="label">
            <span class="label-text">收藏标题</span>
          </label>
          <input
            ref="favoriteTitleInput"
            v-model="favoriteTitle"
            type="text"
            placeholder="请输入收藏标题..."
            class="input input-bordered"
          >
        </div>
        <div class="modal-action">
          <button
            class="btn btn-ghost"
            @click="closeAddToFavoritesModal"
          >
            取消
          </button>
          <button
            class="btn btn-primary"
            :disabled="!favoriteTitle.trim()"
            @click="confirmAddToFavorites"
          >
            确认添加
          </button>
        </div>
      </div>
      <form
        method="dialog"
        class="modal-backdrop"
      >
        <button>close</button>
      </form>
    </dialog>

    <!-- 日志详情弹框 -->
    <LogDetailModal
      :is-visible="showDetailModal"
      :task-id="detailTaskId"
      :task-info="detailTaskInfo"
      @close="closeDetailModal"
    />

    <!-- 悬浮球和侧边栏 -->
    <FloatingBall
      :is-expanded="isSidebarVisible"
      @toggle="toggleSidebar"
    />
    <SidebarPanel
      :is-visible="isSidebarVisible"
      @close="closeSidebar"
      @rerun-query="handleRerunQuery"
      @view-details="handleViewDetails"
      @execute-favorite="handleExecuteFavorite"
      @edit-favorite="handleEditFavorite"
      @delete-favorite="handleDeleteFavorite"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useQueryStore } from '@stores/query'
import { useToast } from '@/composables/useToast'
import QueryForm from '@/components/common/QueryForm.vue'
import QueryProgress from '@/components/common/QueryProgress.vue'
import QueryResultsTable from '@/components/query/QueryResultsTable.vue'
import FloatingBall from '@/components/common/FloatingBall.vue'
import SidebarPanel from '@/components/common/SidebarPanel.vue'
import LogDetailModal from '@/components/common/LogDetailModal.vue'
import type { QueryRequest } from '@/types/index'

const queryStore = useQueryStore()
const { success, error, info } = useToast()

// UI state
const initialQuery = ref('')
const isSidebarVisible = ref(false)

// Modal state
const addToFavoritesModal = ref<HTMLDialogElement>()
const favoriteTitle = ref('')
const favoriteTitleInput = ref<HTMLInputElement>()

// Detail modal state
const showDetailModal = ref(false)
const detailTaskId = ref('')
const detailTaskInfo = ref(null)

// Quick examples
const quickExamples = [
  '9月30日所有账户的余额',
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


// Handle query submission
const handleSubmitQuery = async (request: QueryRequest) => {
  try {
    // 清理上一次的查询结果，准备新的查询
    if (queryStore.currentResult) {
      queryStore.clearCurrentQuery()
    }

    await queryStore.submitQuery(request)
    success('查询已提交，正在处理...')
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
  // 给一点时间让组件更新，然后重置以便下次点击能触发
  setTimeout(() => {
    initialQuery.value = ''
  }, 100)
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
  } catch (err) {
    error('添加到收藏失败')
  }
}

// Sidebar functions
const toggleSidebar = () => {
  isSidebarVisible.value = !isSidebarVisible.value
}

const closeSidebar = () => {
  isSidebarVisible.value = false
}

// Handle history actions
const handleRerunQuery = async (taskId: string) => {
  try {
    await queryStore.rerunQuery(taskId)
    success('正在重新执行查询...')
    closeSidebar()
  } catch (err) {
    error('重新执行查询失败')
  }
}

// Handle view details
const handleViewDetails = (log: any) => {
  detailTaskId.value = log.task_id
  detailTaskInfo.value = log
  showDetailModal.value = true
}

const closeDetailModal = () => {
  showDetailModal.value = false
  detailTaskId.value = ''
  detailTaskInfo.value = null
}

// Handle favorites actions
const handleExecuteFavorite = async (favoriteId: number) => {
  try {
    await queryStore.executeFavorite(favoriteId)
    success('正在执行收藏的查询...')
    closeSidebar()
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

</script>
