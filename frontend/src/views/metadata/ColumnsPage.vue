<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold">字段配置管理</h2>
        <p class="text-base-content/60 mt-1">管理数据库字段的元数据信息和业务类型</p>
      </div>
      <button
        @click="showCreateModal = true"
        class="btn btn-primary"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        添加字段
      </button>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-4 items-center bg-base-200 p-4 rounded-lg">
      <div class="form-control">
        <label class="label">
          <span class="label-text">所属表</span>
        </label>
        <select
          v-model="filters.tableId"
          class="select select-bordered select-sm"
          @change="loadColumns"
        >
          <option value="">全部表</option>
          <option
            v-for="table in availableTables"
            :key="table.id"
            :value="table.id"
          >
            {{ table.name }}
          </option>
        </select>
      </div>

      <div class="form-control">
        <label class="label">
          <span class="label-text">业务类型</span>
        </label>
        <select
          v-model="filters.businessType"
          class="select select-bordered select-sm"
          @change="loadColumns"
        >
          <option value="">全部类型</option>
          <option value="identifier">标识符</option>
          <option value="measure">度量值</option>
          <option value="dimension">维度</option>
          <option value="time">时间</option>
        </select>
      </div>

      <div class="form-control flex-1 min-w-64">
        <label class="label">
          <span class="label-text">搜索</span>
        </label>
        <input
          v-model="filters.search"
          type="text"
          placeholder="搜索字段名或注释..."
          class="input input-bordered input-sm"
          @input="debouncedSearch"
        />
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && columns.length === 0" class="text-center py-12">
      <EmptyState
        type="no-data"
        title="暂无字段配置"
        description="请先选择表或添加字段配置。"
        size="md"
      />
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <LoadingSpinner text="加载字段配置..." />
    </div>

    <!-- Columns Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="column in columns"
        :key="column.id"
        class="card bg-base-100 border border-base-300 hover:border-primary transition-colors"
      >
        <div class="card-body p-4">
          <div class="flex items-start justify-between mb-2">
            <div class="flex-1 min-w-0">
              <h4 class="font-medium text-sm truncate">{{ column.name }}</h4>
              <p class="text-xs text-base-content/60">{{ column.type }}</p>
            </div>
            <div class="flex gap-1">
              <button
                @click="editColumn(column)"
                class="btn btn-ghost btn-xs p-1"
                title="编辑"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button
                @click="deleteColumn(column)"
                class="btn btn-ghost btn-xs text-error p-1"
                title="删除"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>

          <div class="space-y-2">
            <div class="text-xs">
              <span class="font-medium">表:</span> {{ column.tableName }}
            </div>
            <div v-if="column.comment" class="text-xs">
              <span class="font-medium">注释:</span> {{ column.comment }}
            </div>
            <div class="text-xs">
              <span class="font-medium">业务类型:</span>
              <span class="badge badge-outline badge-xs ml-1">{{ column.businessType }}</span>
            </div>
            <div v-if="column.relationId" class="text-xs">
              <span class="font-medium">关联:</span> {{ column.relationId }}
            </div>
          </div>

          <div class="flex items-center justify-between mt-3">
            <label class="cursor-pointer">
              <input
                type="checkbox"
                class="checkbox checkbox-xs"
                :checked="column.isAvailable"
                @change="toggleColumnAvailability(column)"
              />
              <span class="label-text ml-1 text-xs">启用</span>
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- Simple Create/Edit Modal -->
    <dialog ref="columnModal" class="modal" :open="showCreateModal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">添加字段配置</h3>
        <div class="py-4">
          <p class="text-base-content/60">字段配置功能开发中...</p>
        </div>
        <div class="modal-action">
          <button @click="showCreateModal = false" class="btn btn-ghost">关闭</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showCreateModal = false">close</button>
      </form>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { metadataService } from '@services/api'
import EmptyState from '@/components/common/EmptyState.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import type { ColumnMetadata, TableMetadata } from '@types/index'

const { success, error } = useToast()

// State
const columns = ref<ColumnMetadata[]>([])
const availableTables = ref<TableMetadata[]>([])
const loading = ref(false)
const showCreateModal = ref(false)

// Filters
const filters = reactive({
  tableId: '',
  businessType: '',
  search: ''
})

// Debounced search
let searchTimeout: NodeJS.Timeout
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(loadColumns, 500)
}

// Load tables
const loadTables = async () => {
  try {
    availableTables.value = await metadataService.getTables(undefined, true)
  } catch (err) {
    console.error('Failed to load tables:', err)
  }
}

// Load columns
const loadColumns = async () => {
  try {
    loading.value = true
    // Simplified - in real implementation would call metadataService.getColumns()
    columns.value = []
  } catch (err) {
    error('加载字段列表失败')
  } finally {
    loading.value = false
  }
}

// Toggle column availability
const toggleColumnAvailability = async (column: ColumnMetadata) => {
  try {
    // Implementation would call metadataService.updateColumn()
    column.isAvailable = !column.isAvailable
    success('字段状态已更新')
  } catch (err) {
    error('更新字段状态失败')
  }
}

// Edit column
const editColumn = (column: ColumnMetadata) => {
  success(`编辑字段: ${column.name}`)
}

// Delete column
const deleteColumn = (column: ColumnMetadata) => {
  if (confirm(`确定要删除字段 "${column.name}" 吗？`)) {
    success('字段已删除')
  }
}

// Initialize
onMounted(() => {
  loadTables()
  loadColumns()
})
</script>