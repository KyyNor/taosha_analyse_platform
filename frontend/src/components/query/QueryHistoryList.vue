<template>
  <div class="space-y-3">
    <!-- Loading State -->
    <div
      v-if="loading"
      class="text-center py-8"
    >
      <LoadingSpinner
        size="sm"
        text="加载查询历史..."
      />
    </div>

    <!-- Empty State -->
    <div
      v-else-if="history.length === 0"
      class="text-center py-8"
    >
      <EmptyState
        type="no-data"
        title="暂无查询历史"
        description="您还没有进行过任何查询。"
        size="sm"
      />
    </div>

    <!-- History List -->
    <div
      v-else
      class="space-y-3"
    >
      <div
        v-for="item in history"
        :key="item.id"
        class="card bg-base-100 border border-base-300 hover:border-primary transition-colors"
      >
        <div class="card-body p-4">
          <div class="flex items-start justify-between gap-3">
            <!-- Query Info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-2">
                <span
                  class="badge badge-sm"
                  :class="{
                    'badge-success': item.status === 'success',
                    'badge-error': item.status === 'failed',
                    'badge-warning': item.status === 'running',
                    'badge-info': item.status === 'cancelled'
                  }"
                >
                  {{ getStatusText(item.status) }}
                </span>
                <span class="text-xs text-base-content/60">
                  {{ formatTime(item.createdAt) }}
                </span>
                <span
                  v-if="item.duration"
                  class="text-xs text-base-content/60"
                >
                  {{ formatDuration(item.duration) }}
                </span>
              </div>

              <div class="mb-2">
                <p class="text-sm font-medium line-clamp-2">
                  {{ item.query }}
                </p>
                <p
                  v-if="item.generatedSql"
                  class="text-xs text-base-content/60 mt-1 font-mono line-clamp-1"
                >
                  {{ item.generatedSql }}
                </p>
              </div>

              <!-- Result Summary -->
              <div
                v-if="item.result"
                class="text-xs text-base-content/60"
              >
                返回 {{ item.result.rowCount || 0 }} 行数据
              </div>

              <!-- Error Message -->
              <div
                v-if="item.errorMessage"
                class="text-xs text-error mt-2"
              >
                {{ item.errorMessage }}
              </div>
            </div>

            <!-- Actions -->
            <div class="flex flex-col gap-2">
              <button
                v-if="item.status === 'success'"
                class="btn btn-ghost btn-xs"
                title="重新运行"
                @click="$emit('rerun', item.id)"
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
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              </button>
              <button
                class="btn btn-ghost btn-xs"
                title="查看详情"
                @click="$emit('view-details', item)"
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
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                  />
                </svg>
              </button>
              <button
                v-if="item.status === 'success'"
                class="btn btn-ghost btn-xs"
                title="添加到收藏"
                @click="addToFavorites(item)"
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
                    d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import { useQueryStore } from '@stores/query'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { QueryLog } from '@types/index'

interface Props {
  history: QueryLog[]
  loading: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  rerun: [id: string]
  viewDetails: [log: QueryLog]
}>()

const queryStore = useQueryStore()
const { success, error } = useToast()

// Format time
const formatTime = (timeStr: string) => {
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days}天前`
  if (hours > 0) return `${hours}小时前`
  if (minutes > 0) return `${minutes}分钟前`
  return '刚刚'
}

// Format duration
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

// Get status text
const getStatusText = (status: string) => {
  const statusMap = {
    'success': '成功',
    'failed': '失败',
    'running': '运行中',
    'cancelled': '已取消',
    'pending': '等待中'
  }
  return statusMap[status] || status
}

// Add to favorites
const addToFavorites = async (log: QueryLog) => {
  try {
    const title = `${log.query.substring(0, 20)}${log.query.length > 20 ? '...' : ''}`
    await queryStore.addToFavorites(log.id, title)
    success('已添加到收藏')
  } catch (err) {
    error('添加到收藏失败')
  }
}
</script>

<style scoped>
.line-clamp-1 {
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
}

.line-clamp-2 {
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
</style>
