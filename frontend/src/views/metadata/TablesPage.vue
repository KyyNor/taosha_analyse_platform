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
      <div class="modal-box max-w-4xl">
        <h3 class="font-bold text-lg">
          {{ showEditModal ? '编辑表' : '添加表' }}
        </h3>

        <!-- Tabs -->
        <div class="tabs tabs-boxed mt-4">
          <a
            class="tab"
            :class="{ 'tab-active': activeTab === 'table' }"
            @click="activeTab = 'table'"
          >
            表信息
          </a>
          <a
            v-if="showEditModal"
            class="tab"
            :class="{ 'tab-active': activeTab === 'columns' }"
            @click="activeTab = 'columns'"
          >
            字段配置
          </a>
        </div>

        <!-- Table Info Tab -->
        <div
          v-if="activeTab === 'table'"
          class="mt-4"
        >
          <form
            class="space-y-4"
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

        <!-- Columns Tab -->
        <div
          v-if="activeTab === 'columns' && showEditModal"
          class="mt-4"
        >
          <div class="flex justify-between items-center mb-4">
            <h4 class="font-semibold">字段列表</h4>
            <button
              class="btn btn-primary btn-sm"
              @click="showColumnModal = true"
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
              添加字段
            </button>
          </div>

          <!-- Columns List -->
          <div class="overflow-x-auto">
            <table class="table table-sm">
              <thead>
                <tr>
                  <th>字段名</th>
                  <th>类型</th>
                  <th>注释</th>
                  <th>业务类型</th>
                  <th>启用</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="column in columns"
                  :key="column.id"
                >
                  <td class="font-mono text-sm">
                    {{ column.name }}
                  </td>
                  <td class="font-mono text-sm text-base-content/60">
                    {{ column.type }}
                  </td>
                  <td class="max-w-xs truncate">
                    {{ column.comment || '-' }}
                  </td>
                  <td>
                    <span class="badge badge-outline badge-xs">
                      {{ column.businessType }}
                    </span>
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      class="checkbox checkbox-xs"
                      :checked="column.isAvailable"
                      @change="toggleColumnAvailability(column)"
                    >
                  </td>
                  <td>
                    <div class="flex gap-1">
                      <button
                        class="btn btn-ghost btn-xs p-1"
                        title="编辑"
                        @click="editColumn(column)"
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
                        class="btn btn-ghost btn-xs text-error p-1"
                        title="删除"
                        @click="deleteColumn(column)"
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
                  </td>
                </tr>
              </tbody>
            </table>

            <div
              v-if="columns.length === 0"
              class="text-center py-8 text-base-content/60"
            >
              暂无字段配置，点击"添加字段"按钮开始配置。
            </div>
          </div>

          <div class="modal-action">
            <button
              class="btn btn-ghost"
              @click="closeModal"
            >
              关闭
            </button>
          </div>
        </div>
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

    <!-- Column Create/Edit Modal -->
    <dialog
      ref="columnModal"
      class="modal"
      :open="showColumnModal"
    >
      <div class="modal-box">
        <h3 class="font-bold text-lg">
          {{ editingColumn ? '编辑字段' : '添加字段' }}
        </h3>
        <form
          class="space-y-4 mt-4"
          @submit.prevent="saveColumn"
        >
          <div class="form-control">
            <label class="label">
              <span class="label-text">字段名 *</span>
            </label>
            <input
              v-model="columnForm.name"
              type="text"
              placeholder="请输入字段名"
              class="input input-bordered"
              :disabled="editingColumn"
              required
            >
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">字段类型 *</span>
            </label>
            <select
              v-model="columnForm.type"
              class="select select-bordered"
              :disabled="editingColumn"
              required
            >
              <option value="VARCHAR">
                VARCHAR
              </option>
              <option value="INTEGER">
                INTEGER
              </option>
              <option value="DECIMAL">
                DECIMAL
              </option>
              <option value="DATE">
                DATE
              </option>
              <option value="TIMESTAMP">
                TIMESTAMP
              </option>
              <option value="BOOLEAN">
                BOOLEAN
              </option>
            </select>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">字段注释</span>
            </label>
            <textarea
              v-model="columnForm.comment"
              placeholder="请输入字段注释"
              class="textarea textarea-bordered"
              rows="2"
            />
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">业务类型</span>
            </label>
            <select
              v-model="columnForm.businessType"
              class="select select-bordered"
            >
              <option value="">
                请选择
              </option>
              <option value="identifier">
                标识符
              </option>
              <option value="measure">
                度量值
              </option>
              <option value="dimension">
                维度
              </option>
              <option value="time">
                时间
              </option>
            </select>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">关联ID</span>
            </label>
            <input
              v-model="columnForm.relationId"
              type="text"
              placeholder="请输入关联ID（可选）"
              class="input input-bordered"
            >
          </div>

          <div class="form-control">
            <label class="label cursor-pointer">
              <span class="label-text">启用字段</span>
              <input
                v-model="columnForm.isAvailable"
                type="checkbox"
                class="checkbox checkbox-primary"
              >
            </label>
          </div>

          <div class="modal-action">
            <button
              type="button"
              class="btn btn-ghost"
              @click="closeColumnModal"
            >
              取消
            </button>
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="savingColumn"
            >
              <span
                v-if="savingColumn"
                class="loading loading-spinner loading-sm"
              />
              {{ savingColumn ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
      <form
        method="dialog"
        class="modal-backdrop"
      >
        <button @click="closeColumnModal">
          close
        </button>
      </form>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useToast } from '@/composables/useToast'
import { metadataService } from '@services/api'
import DataTable from '@/components/common/DataTable.vue'
// import type { TableMetadata, ColumnMetadata } from '@/types/index'

const { success, error } = useToast()

// State
const tables = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showCreateModal = ref(false)
const showEditModal = ref(false)
const editingTable = ref<any | null>(null)

// Column management state
const activeTab = ref('table')
const columns = ref<any[]>([])
const showColumnModal = ref(false)
const editingColumn = ref<any | null>(null)
const savingColumn = ref(false)

// Filters
const filters = reactive({
  search: ''
})

// Form
const tableForm = reactive({
  name: '',
  comment: ''
})

// Column form
const columnForm = reactive({
  name: '',
  type: 'VARCHAR',
  comment: '',
  businessType: '',
  relationId: '',
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
const viewTableDetails = (table: any) => {
  // Navigate to table details page
  success(`查看表详情: ${table.name}`)
}

// Load columns for current table
const loadColumns = async () => {
  if (!editingTable.value) return

  try {
    // Get tables data to find the current table with its columns
    const tables = await metadataService.getTables()
    const currentTable = tables.find(table => table.name === editingTable.value.name)

    if (currentTable && currentTable.columns) {
      // Transform API response to match our component format
      columns.value = currentTable.columns.map((column: any, index: number) => ({
        id: index + 1, // Generate temporary ID
        name: column.name,
        type: column.type,
        comment: column.comment,
        businessType: column.business_type,
        relationId: column.relation_id,
        isAvailable: Boolean(column.is_available)
      }))
    } else {
      columns.value = []
    }
  } catch (err) {
    error('加载字段列表失败')
  }
}

// Toggle column availability
const toggleColumnAvailability = async (column: any) => {
  try {
    // In real implementation, call metadataService.updateColumn()
    column.isAvailable = !column.isAvailable
    success('字段状态已更新')
  } catch (err) {
    error('更新字段状态失败')
  }
}

// Edit column
const editColumn = (column: any) => {
  editingColumn.value = column
  Object.assign(columnForm, {
    name: column.name,
    type: column.type,
    comment: column.comment,
    businessType: column.businessType,
    relationId: column.relationId,
    isAvailable: column.isAvailable
  })
  showColumnModal.value = true
}

// Delete column
const deleteColumn = async (column: any) => {
  if (confirm(`确定要删除字段 "${column.name}" 吗？此操作不可恢复。`)) {
    try {
      // In real implementation, call metadataService.deleteColumn()
      columns.value = columns.value.filter(c => c.id !== column.id)
      success('字段已删除')
    } catch (err) {
      error('删除字段失败')
    }
  }
}

// Save column
const saveColumn = async () => {
  try {
    savingColumn.value = true

    if (editingColumn.value) {
      // Update existing column
      // In real implementation, call metadataService.updateColumn()
      Object.assign(editingColumn.value, columnForm)
      success('字段已更新')
    } else {
      // Create new column
      // In real implementation, call metadataService.createColumn()
      const newColumn = {
        id: Date.now(), // Mock ID
        tableName: editingTable.value?.name,
        ...columnForm
      }
      columns.value.push(newColumn)
      success('字段已创建')
    }

    closeColumnModal()
  } catch (err) {
    error(editingColumn.value ? '更新字段失败' : '创建字段失败')
  } finally {
    savingColumn.value = false
  }
}

// Close column modal
const closeColumnModal = () => {
  showColumnModal.value = false
  editingColumn.value = null

  // Reset form
  Object.assign(columnForm, {
    name: '',
    type: 'VARCHAR',
    comment: '',
    businessType: '',
    relationId: '',
    isAvailable: true
  })
}

// Edit table
const editTable = (table: any) => {
  editingTable.value = table
  Object.assign(tableForm, {
    name: table.name,
    comment: table.comment
  })
  showEditModal.value = true
  activeTab.value = 'table'
  // Load columns for this table
  loadColumns()
}

// Confirm delete table
const confirmDeleteTable = (table: any) => {
  if (confirm(`确定要删除表 "${table.name}" 吗？此操作不可恢复。`)) {
    deleteTable(table)
  }
}

// Delete table
const deleteTable = async (table: any) => {
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

// Watch for tab changes to load columns
watch(activeTab, (newTab) => {
  if (newTab === 'columns' && editingTable.value) {
    loadColumns()
  }
})

// Initialize
onMounted(() => {
  loadTables()
})
</script>
