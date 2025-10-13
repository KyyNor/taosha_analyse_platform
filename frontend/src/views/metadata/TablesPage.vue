<template>
  <div class="space-y-6">
    <!-- Filters -->
    <div class="flex flex-wrap gap-4 items-center bg-base-200 p-4 rounded-lg">
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
        >
      </div>

      <button
        class="btn btn-primary"
        @click="showCreateModal = true"
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
            d="M12 4v16m8-8H4"
          />
        </svg>
        添加表
      </button>
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

        <template #cell-name="{ value }">
          <div class="font-medium">
            {{ value }}
          </div>
        </template>

        <template #cell-comment="{ value }">
          <div
            class="max-w-xs truncate"
            :title="value"
          >
            {{ value || '-' }}
          </div>
        </template>

  
        <template #actions="{ record }">
          <div class="flex gap-1">
            <button
              class="btn btn-ghost btn-xs"
              title="查看详情"
              @click="viewTableDetails(record)"
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
              class="btn btn-ghost btn-xs"
              title="编辑"
              @click="editTable(record)"
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
              class="btn btn-ghost btn-xs text-error"
              title="删除"
              @click="confirmDeleteTable(record)"
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
        </template>
      </DataTable>
    </div>

    <!-- Create/Edit Modal -->
    <dialog
      ref="tableModal"
      class="modal"
      :open="showCreateModal || showEditModal"
    >
      <div class="modal-box">
        <h3 class="font-bold text-lg">
          {{ showEditModal ? '编辑表' : '添加表' }}
        </h3>
        <form
          class="space-y-4 mt-4"
          @submit.prevent="saveTable"
        >
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
            >
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
            />
          </div>

  
  
          <div class="modal-action">
            <button
              type="button"
              class="btn btn-ghost"
              @click="closeModal"
            >
              取消
            </button>
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="saving"
            >
              <span
                v-if="saving"
                class="loading loading-spinner loading-sm"
              />
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
      <form
        method="dialog"
        class="modal-backdrop"
      >
        <button @click="closeModal">
          close
        </button>
      </form>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { metadataService } from '@services/api'
import DataTable from '@/components/common/DataTable.vue'
import type { TableMetadata } from '@/types/index'

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
  search: ''
})

// Form
const tableForm = reactive({
  name: '',
  comment: ''
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
  }
]

// Debounced search
let searchTimeout: number
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(loadTables, 500)
}

// Load tables
const loadTables = async () => {
  try {
    loading.value = true

    tables.value = await metadataService.getTables()

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
    comment: table.comment
  })
  showEditModal.value = true
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
        comment: tableForm.comment
      })
      success('表已更新')
    } else {
      await metadataService.createTable({
        name: tableForm.name,
        comment: tableForm.comment,
        isAvailable: true
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
    comment: ''
  })
}

// Initialize
onMounted(() => {
  loadTables()
})
</script>
