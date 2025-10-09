<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold">表配置管理</h2>
        <p class="text-base-content/60 mt-1">管理数据库表的元数据信息</p>
      </div>
      <button
        @click="showCreateModal = true"
        class="btn btn-primary"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        添加表
      </button>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-4 items-center bg-base-200 p-4 rounded-lg">
      <div class="form-control">
        <label class="label">
          <span class="label-text">数据源</span>
        </label>
        <select
          v-model="filters.dataSource"
          class="select select-bordered select-sm"
          @change="loadTables"
        >
          <option value="">全部数据源</option>
          <option value="main">主数据库</option>
          <option value="analytics">分析数据库</option>
        </select>
      </div>

      <div class="form-control">
        <label class="label">
          <span class="label-text">状态</span>
        </label>
        <select
          v-model="filters.isActive"
          class="select select-bordered select-sm"
          @change="loadTables"
        >
          <option value="">全部状态</option>
          <option :value="true">活跃</option>
          <option :value="false">非活跃</option>
        </select>
      </div>

      <div class="form-control flex-1 min-w-64">
        <label class="label">
          <span class="label-text">搜索</span>
        </label>
        <input
          v-model="filters.search"
          type="text"
          placeholder="搜索表名或注释..."
          class="input input-bordered input-sm"
          @input="debouncedSearch"
        />
      </div>
    </div>

    <!-- Tables Table -->
    <div class="overflow-x-auto">
      <DataTable
        :data="tables"
        :columns="tableColumns"
        :loading="loading"
        :searchable="false"
        :paginated="true"
        :page-size="20"
        empty-state-type="no-data"
        row-key="id"
        :show-header="true"
        :column-settings="true"
      >
        <template #cell-isAvailable="{ value, record }">
          <input
            type="checkbox"
            class="checkbox checkbox-sm"
            :checked="value"
            @change="toggleTableAvailability(record)"
          />
        </template>

        <template #cell-name="{ value, record }">
          <div>
            <div class="font-medium">{{ value }}</div>
            <div class="text-xs text-base-content/60">{{ record.dataSource }}</div>
          </div>
        </template>

        <template #cell-comment="{ value }">
          <div class="max-w-xs truncate" :title="value">
            {{ value || '-' }}
          </div>
        </template>

        <template #cell-updateMethod="{ value }">
          <span
            class="badge badge-sm"
            :class="{
              'badge-success': value === 'auto',
              'badge-warning': value === 'manual',
              'badge-info': value === 'scheduled'
            }"
          >
            {{ getUpdateMethodText(value) }}
          </span>
        </template>

        <template #actions="{ record }">
          <div class="flex gap-1">
            <button
              @click="viewTableDetails(record)"
              class="btn btn-ghost btn-xs"
              title="查看详情"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </button>
            <button
              @click="editTable(record)"
              class="btn btn-ghost btn-xs"
              title="编辑"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
            <button
              @click="syncTableSchema(record)"
              class="btn btn-ghost btn-xs"
              title="同步结构"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <button
              @click="confirmDeleteTable(record)"
              class="btn btn-ghost btn-xs text-error"
              title="删除"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </template>
      </DataTable>
    </div>

    <!-- Create/Edit Modal -->
    <dialog ref="tableModal" class="modal" :open="showCreateModal || showEditModal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">
          {{ showEditModal ? '编辑表' : '添加表' }}
        </h3>
        <form @submit.prevent="saveTable" class="space-y-4 mt-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">表名 *</span>
            </label>
            <input
              v-model="tableForm.name"
              type="text"
              placeholder="请输入表名"
              class="input input-bordered"
              :disabled="showEditModal"
              required
            />
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">表注释</span>
            </label>
            <textarea
              v-model="tableForm.comment"
              placeholder="请输入表注释"
              class="textarea textarea-bordered"
              rows="3"
            ></textarea>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">数据源</span>
            </label>
            <select v-model="tableForm.dataSource" class="select select-bordered">
              <option value="main">主数据库</option>
              <option value="analytics">分析数据库</option>
            </select>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">更新方式</span>
            </label>
            <select v-model="tableForm.updateMethod" class="select select-bordered">
              <option value="auto">自动更新</option>
              <option value="manual">手动更新</option>
              <option value="scheduled">定时更新</option>
            </select>
          </div>

          <div class="form-control">
            <label class="label cursor-pointer">
              <span class="label-text">启用表</span>
              <input
                v-model="tableForm.isAvailable"
                type="checkbox"
                class="checkbox checkbox-primary"
              />
            </label>
          </div>

          <div class="modal-action">
            <button type="button" @click="closeModal" class="btn btn-ghost">
              取消
            </button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <span v-if="saving" class="loading loading-spinner loading-sm"></span>
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="closeModal">close</button>
      </form>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useToast } from '@/composables/useToast'
import { metadataService } from '@services/api'
import DataTable from '@/components/common/DataTable.vue'
import type { TableMetadata } from '@types/index'

const { success, error } = useToast()

// State
const tables = ref<TableMetadata[]>([])
const loading = ref(false)
const saving = ref(false)
const showCreateModal = ref(false)
const showEditModal = ref(false)
const editingTable = ref<TableMetadata | null>(null)

// Filters
const filters = reactive({
  dataSource: '',
  isActive: '',
  search: ''
})

// Form
const tableForm = reactive({
  name: '',
  comment: '',
  dataSource: 'main',
  updateMethod: 'auto',
  isAvailable: true
})

// Table columns
const tableColumns = [
  {
    key: 'name',
    title: '表名',
    sortable: true,
    visible: true
  },
  {
    key: 'comment',
    title: '表注释',
    sortable: true,
    visible: true
  },
  {
    key: 'dataSource',
    title: '数据源',
    sortable: true,
    visible: true
  },
  {
    key: 'updateMethod',
    title: '更新方式',
    sortable: true,
    visible: true
  },
  {
    key: 'isAvailable',
    title: '启用',
    sortable: true,
    visible: true,
    className: 'text-center'
  }
]

// Debounced search
let searchTimeout: NodeJS.Timeout
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(loadTables, 500)
}

// Load tables
const loadTables = async () => {
  try {
    loading.value = true
    const dataSource = filters.dataSource || undefined
    const isActive = filters.isActive === '' ? undefined : filters.isActive

    tables.value = await metadataService.getTables(dataSource, isActive)

    // Apply client-side search
    if (filters.search) {
      const search = filters.search.toLowerCase()
      tables.value = tables.value.filter(table =>
        table.name.toLowerCase().includes(search) ||
        (table.comment && table.comment.toLowerCase().includes(search))
      )
    }
  } catch (err) {
    error('加载表列表失败')
  } finally {
    loading.value = false
  }
}

// Get update method text
const getUpdateMethodText = (method: string) => {
  const methods = {
    'auto': '自动',
    'manual': '手动',
    'scheduled': '定时'
  }
  return methods[method] || method
}

// Toggle table availability
const toggleTableAvailability = async (table: TableMetadata) => {
  try {
    await metadataService.updateTable(table.id, {
      isAvailable: !table.isAvailable
    })
    table.isAvailable = !table.isAvailable
    success('表状态已更新')
  } catch (err) {
    error('更新表状态失败')
  }
}

// View table details
const viewTableDetails = (table: TableMetadata) => {
  // Navigate to table details page
  success(`查看表详情: ${table.name}`)
}

// Edit table
const editTable = (table: TableMetadata) => {
  editingTable.value = table
  Object.assign(tableForm, {
    name: table.name,
    comment: table.comment,
    dataSource: table.dataSource,
    updateMethod: table.updateMethod,
    isAvailable: table.isAvailable
  })
  showEditModal.value = true
}

// Sync table schema
const syncTableSchema = async (table: TableMetadata) => {
  try {
    // This would trigger schema sync for the specific table
    success(`正在同步表结构: ${table.name}`)
  } catch (err) {
    error('同步表结构失败')
  }
}

// Confirm delete table
const confirmDeleteTable = (table: TableMetadata) => {
  if (confirm(`确定要删除表 "${table.name}" 吗？此操作不可恢复。`)) {
    deleteTable(table)
  }
}

// Delete table
const deleteTable = async (table: TableMetadata) => {
  try {
    await metadataService.deleteTable(table.id)
    success('表已删除')
    await loadTables()
  } catch (err) {
    error('删除表失败')
  }
}

// Save table
const saveTable = async () => {
  try {
    saving.value = true

    if (showEditModal.value && editingTable.value) {
      await metadataService.updateTable(editingTable.value.id, {
        comment: tableForm.comment,
        dataSource: tableForm.dataSource,
        updateMethod: tableForm.updateMethod,
        isAvailable: tableForm.isAvailable
      })
      success('表已更新')
    } else {
      await metadataService.createTable({
        name: tableForm.name,
        comment: tableForm.comment,
        isAvailable: tableForm.isAvailable,
        dataSource: tableForm.dataSource,
        updateMethod: tableForm.updateMethod
      })
      success('表已创建')
    }

    closeModal()
    await loadTables()
  } catch (err) {
    error(showEditModal.value ? '更新表失败' : '创建表失败')
  } finally {
    saving.value = false
  }
}

// Close modal
const closeModal = () => {
  showCreateModal.value = false
  showEditModal.value = false
  editingTable.value = null

  // Reset form
  Object.assign(tableForm, {
    name: '',
    comment: '',
    dataSource: 'main',
    updateMethod: 'auto',
    isAvailable: true
  })
}

// Initialize
onMounted(() => {
  loadTables()
})
</script>