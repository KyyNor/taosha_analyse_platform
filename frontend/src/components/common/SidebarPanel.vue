<template>
  <div
    class="fixed top-0 left-0 h-full w-80 bg-base-100 shadow-2xl z-40 transform transition-transform duration-300 ease-in-out"
    :class="isVisible ? 'translate-x-0' : '-translate-x-full'"
  >
    <div class="flex flex-col h-full">
      <!-- 标题栏 -->
      <div class="flex items-center justify-between p-4 border-b border-base-300">
        <h2 class="text-lg font-semibold">
          查询历史与收藏
        </h2>
        <button
          class="btn btn-ghost btn-sm btn-square"
          @click="$emit('close')"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <!-- Tab 切换 -->
      <div class="tabs tabs-boxed bg-base-300 m-4">
        <a
          class="tab flex-1"
          :class="{ 'tab-active': activeTab === 'history' }"
          @click="activeTab = 'history'"
        >
          查询历史
        </a>
        <a
          class="tab flex-1"
          :class="{ 'tab-active': activeTab === 'favorites' }"
          @click="activeTab = 'favorites'"
        >
          我的收藏
        </a>
      </div>

      <!-- 内容区域 -->
      <div class="flex-1 overflow-hidden px-4 pb-4">
        <!-- 查询历史 -->
        <div
          v-if="activeTab === 'history'"
          class="h-full flex flex-col"
        >
          <!-- 搜索和筛选 -->
          <div class="mb-4 space-y-2">
            <input
              v-model="historySearchQuery"
              type="text"
              placeholder="搜索历史..."
              class="input input-bordered input-sm w-full"
            >
            <select
              v-model="historyFilter"
              class="select select-bordered select-sm w-full"
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
            </select>
          </div>

          <!-- 历史列表 -->
          <div class="flex-1 overflow-y-auto">
            <QueryHistoryList
              :history="filteredHistory"
              :loading="historyLoading"
              @rerun="$emit('rerun-query', $event)"
              @view-details="$emit('view-details', $event)"
            />
          </div>
        </div>

        <!-- 收藏列表 -->
        <div
          v-if="activeTab === 'favorites'"
          class="h-full flex flex-col"
        >
          <!-- 搜索 -->
          <div class="mb-4">
            <input
              v-model="favoritesSearchQuery"
              type="text"
              placeholder="搜索收藏..."
              class="input input-bordered input-sm w-full"
            >
          </div>

          <!-- 收藏列表 -->
          <div class="flex-1 overflow-y-auto">
            <div
              v-if="favoritesLoading"
              class="flex items-center justify-center py-8"
            >
              <span class="loading loading-spinner loading-md" />
              <span class="ml-2">加载中...</span>
            </div>
            <div
              v-else-if="filteredFavorites.length === 0"
              class="text-center py-8 text-base-content/60"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-12 w-12 mx-auto mb-2"
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
              <p>暂无收藏</p>
            </div>
            <div
              v-else
              class="space-y-2"
            >
              <div
                v-for="item in filteredFavorites"
                :key="item.id"
                class="card bg-base-200 hover:bg-base-300 transition-colors cursor-pointer group"
              >
                <div class="card-body p-3">
                  <div class="flex items-start justify-between">
                    <div
                      class="flex-1 min-w-0"
                      @click="$emit('execute-favorite', item.id)"
                    >
                      <p class="text-sm font-medium truncate">
                        {{ item.favoriteTitle }}
                      </p>
                      <p class="text-xs text-base-content/60 truncate mt-1">
                        {{ item.userQuestion }}
                      </p>
                      <p class="text-xs text-base-content/40 mt-1">
                        {{ formatTime(item.createdAt) }}
                      </p>
                    </div>
                    <div class="flex gap-1 ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        class="btn btn-ghost btn-xs btn-square"
                        @click.stop="$emit('edit-favorite', item.id, item.favoriteTitle)"
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
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                          />
                        </svg>
                      </button>
                      <button
                        class="btn btn-ghost btn-xs btn-square text-error"
                        @click.stop="$emit('delete-favorite', item.id)"
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
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 遮罩层 -->
  <div
    v-if="isVisible"
    class="fixed inset-0 bg-black/50 z-30"
    @click="$emit('close')"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQueryStore } from '@stores/query'
import QueryHistoryList from '@/components/query/QueryHistoryList.vue'
import type { QueryTask, Favorite } from '@types/index'

interface Emits {
  (e: 'close'): void
  (e: 'rerun-query', taskId: string): void
  (e: 'view-details', log: QueryTask): void
  (e: 'execute-favorite', favoriteId: number): void
  (e: 'edit-favorite', favoriteId: number, newTitle: string): void
  (e: 'delete-favorite', favoriteId: number): void
}

const props = defineProps<{
  isVisible: boolean
}>()

const emit = defineEmits<Emits>()

const queryStore = useQueryStore()

// Tab 状态
const activeTab = ref<'history' | 'favorites'>('history')

// 搜索和筛选状态
const historySearchQuery = ref('')
const historyFilter = ref('')
const favoritesSearchQuery = ref('')
const historyLoading = ref(false)
const favoritesLoading = ref(false)

// 计算属性
const queryHistory = computed(() => queryStore.queryHistory)
const favorites = computed(() => queryStore.favorites)

const filteredHistory = computed(() => {
  let filtered = queryHistory.value || []

  if (historySearchQuery.value) {
    const query = historySearchQuery.value.toLowerCase()
    filtered = filtered.filter(item =>
      item.user_input.toLowerCase().includes(query) ||
      item.sql_query?.toLowerCase().includes(query)
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

// 辅助函数
const getStatusBadgeClass = (status: string) => {
  switch (status) {
    case 'success':
      return 'badge-success'
    case 'failed':
      return 'badge-error'
    case 'running':
      return 'badge-info'
    default:
      return 'badge-ghost'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'success':
      return '成功'
    case 'failed':
      return '失败'
    case 'running':
      return '运行中'
    default:
      return '未知'
  }
}

const formatTime = (timeString: string) => {
  const date = new Date(timeString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))

  if (diffHours < 1) {
    const diffMinutes = Math.floor(diffMs / (1000 * 60))
    return `${diffMinutes}分钟前`
  } else if (diffHours < 24) {
    return `${diffHours}小时前`
  } else {
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}天前`
  }
}

// 加载数据
const loadHistory = async () => {
  try {
    historyLoading.value = true
    await queryStore.loadQueryHistory()
  } catch (err) {
    console.error('加载查询历史失败:', err)
  } finally {
    historyLoading.value = false
  }
}

const loadFavorites = async () => {
  try {
    favoritesLoading.value = true
    await queryStore.loadFavorites()
  } catch (err) {
    console.error('加载收藏列表失败:', err)
  } finally {
    favoritesLoading.value = false
  }
}

// 监听显示状态变化，自动加载数据
onMounted(() => {
  loadHistory()
  loadFavorites()
})
</script>
