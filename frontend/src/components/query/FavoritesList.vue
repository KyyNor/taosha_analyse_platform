<template>
  <div class="space-y-3">
    <!-- Loading State -->
    <div
      v-if="loading"
      class="text-center py-8"
    >
      <LoadingSpinner
        size="sm"
        text="加载收藏列表..."
      />
    </div>

    <!-- Empty State -->
    <div
      v-else-if="favorites.length === 0"
      class="text-center py-8"
    >
      <EmptyState
        type="no-data"
        title="暂无收藏"
        description="您还没有收藏任何查询。"
        size="sm"
        :primary-action="{
          text: '开始查询',
          handler: () => $router.push('/query')
        }"
      />
    </div>

    <!-- Favorites List -->
    <div
      v-else
      class="space-y-3"
    >
      <div
        v-for="item in favorites"
        :key="item.id"
        class="card bg-base-100 border border-base-300 hover:border-primary transition-colors"
      >
        <div class="card-body p-4">
          <div class="flex items-start justify-between gap-3">
            <!-- Favorite Info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-2">
                <h4 class="font-medium text-sm">
                  {{ item.favoriteTitle }}
                </h4>
                <button
                  class="btn btn-ghost btn-xs p-1"
                  title="编辑标题"
                  @click="startEditing(item)"
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
              </div>

              <div class="mb-2">
                <p class="text-sm text-base-content/80 line-clamp-2">
                  {{ item.userQuestion }}
                </p>
              </div>

              <div class="flex items-center gap-3 text-xs text-base-content/60">
                <span>收藏于 {{ formatTime(item.createdAt) }}</span>
                <span v-if="item.lastExecutedAt">
                  最后执行 {{ formatTime(item.lastExecutedAt) }}
                </span>
                <span v-if="item.executionCount">
                  执行 {{ item.executionCount }} 次
                </span>
              </div>

              <!-- Tags -->
              <div
                v-if="item.tags"
                class="flex flex-wrap gap-1 mt-2"
              >
                <span
                  v-for="tag in item.tags.split(',')"
                  :key="tag"
                  class="badge badge-outline badge-xs"
                >
                  {{ tag.trim() }}
                </span>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex flex-col gap-2">
              <button
                class="btn btn-primary btn-xs"
                title="执行查询"
                @click="$emit('execute', item.id)"
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
                    d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </button>
              <button
                class="btn btn-ghost btn-xs"
                title="复制查询"
                @click="copyQuery(item.userQuestion)"
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
                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
              </button>
              <button
                class="btn btn-ghost btn-xs text-error"
                title="删除收藏"
                @click="confirmDelete(item)"
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

  <!-- Edit Title Modal -->
  <dialog
    ref="editModal"
    class="modal"
  >
    <div class="modal-box">
      <h3 class="font-bold text-lg">
        编辑收藏标题
      </h3>
      <div class="form-control mt-4">
        <label class="label">
          <span class="label-text">收藏标题</span>
        </label>
        <input
          ref="editTitleInput"
          v-model="editTitle"
          type="text"
          placeholder="请输入收藏标题..."
          class="input input-bordered"
        >
      </div>
      <div class="modal-action">
        <button
          class="btn btn-ghost"
          @click="closeEditModal"
        >
          取消
        </button>
        <button
          class="btn btn-primary"
          :disabled="!editTitle.trim()"
          @click="saveEdit"
        >
          保存
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
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { useQueryStore } from '@stores/query'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { Favorite } from '@types/index'

interface Props {
  favorites: Favorite[]
  loading: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  execute: [id: number]
  edit: [id: number, title: string]
  delete: [id: number]
}>()

const router = useRouter()
const queryStore = useQueryStore()
const { success, error } = useToast()

// Edit modal state
const editModal = ref<HTMLDialogElement>()
const editTitle = ref('')
const editTitleInput = ref<HTMLInputElement>()
const editingItem = ref<Favorite | null>(null)

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

// Copy query
const copyQuery = async (query: string) => {
  try {
    await navigator.clipboard.writeText(query)
    success('查询已复制到剪贴板')
  } catch (err) {
    error('复制失败')
  }
}

// Start editing
const startEditing = (item: Favorite) => {
  editingItem.value = item
  editTitle.value = item.favoriteTitle
  editModal.value?.showModal()

  nextTick(() => {
    editTitleInput.value?.focus()
    editTitleInput.value?.select()
  })
}

// Close edit modal
const closeEditModal = () => {
  editModal.value?.close()
  editTitle.value = ''
  editingItem.value = null
}

// Save edit
const saveEdit = async () => {
  if (!editingItem.value || !editTitle.value.trim()) return

  try {
    emit('edit', editingItem.value.id, editTitle.value.trim())
    success('收藏标题已更新')
    closeEditModal()
  } catch (err) {
    error('更新失败')
  }
}

// Confirm delete
const confirmDelete = (item: Favorite) => {
  if (confirm(`确定要删除收藏 "${item.favoriteTitle}" 吗？`)) {
    emit('delete', item.id)
  }
}
</script>

<style scoped>
.line-clamp-2 {
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
</style>
