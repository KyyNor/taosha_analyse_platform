<template>
  <div class="space-y-6">
    <!-- Filters -->
    <div class="flex flex-wrap gap-4 items-center bg-base-200 p-4 rounded-lg shadow-md">
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
        @click="openAddTable"
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
    <div class="overflow-x-auto bg-base-100 rounded-lg shadow-md">
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
              @click="openTableDetail(record, false)"
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

    <!-- Table Detail Modal -->
    <div
      v-if="showDetailModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-base-100 rounded-lg w-11/12 max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        <!-- Header -->
        <div class="p-6 border-b border-base-300 flex justify-between items-center flex-shrink-0">
          <h3 class="font-bold text-lg">
            {{ isNewTable ? '添加表' : editingTable?.name || '表详情' }}
          </h3>
          <div class="flex gap-2">
            <button
              v-if="!isNewTable && !isDetailEditMode"
              class="btn btn-primary btn-sm"
              @click="enterEditMode"
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
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
              编辑
            </button>
          </div>
        </div>

        <!-- Content Area -->
        <div class="flex-1 overflow-y-auto p-6">
          <!-- Table Info Section -->
          <div class="mb-6">
            <h4 class="font-semibold text-lg mb-4 pb-2 border-b border-base-300">
              表信息
            </h4>
            <form class="space-y-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="form-control">
                  <label class="label">
                    <span class="label-text">表名 *</span>
                  </label>
                  <input
                    v-model="tableForm.name"
                    type="text"
                    placeholder="请输入表名"
                    class="input input-bordered"
                    :disabled="!isDetailEditMode && !isNewTable"
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
                    :disabled="!isDetailEditMode && !isNewTable"
                  />
                </div>
              </div>
            </form>
          </div>

          <!-- Columns Section -->
          <div>
            <h4 class="font-semibold text-lg mb-4 pb-2 border-b border-base-300">
              字段信息
            </h4>
            <div class="flex justify-between items-center mb-4">
              <button
                v-if="isDetailEditMode || isNewTable"
                class="btn btn-primary btn-sm"
                @click="addNewColumn"
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
            <div class="w-full overflow-x-auto">
              <table class="table table-sm w-full">
                <thead>
                  <tr>
                    <th class="w-32">
                      字段名
                    </th>
                    <th class="w-32">
                      类型
                    </th>
                    <th class="w-48">
                      注释
                    </th>
                    <th class="w-32">
                      业务类型
                    </th>
                    <th class="w-32">
                      关联ID
                    </th>
                    <th class="w-16">
                      启用
                    </th>
                    <th
                      v-if="isDetailEditMode || isNewTable"
                      class="w-16"
                    >
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(column, index) in columns"
                    :key="column.id || index"
                  >
                    <td>
                      <input
                        v-if="isDetailEditMode || isNewTable"
                        v-model="column.name"
                        type="text"
                        class="input input-bordered input-xs w-full"
                        placeholder="字段名"
                      >
                      <span
                        v-else
                        class="font-mono text-sm block"
                      >
                        {{ column.name }}
                      </span>
                    </td>
                    <td>
                      <input
                        v-if="isDetailEditMode || isNewTable"
                        v-model="column.type"
                        type="text"
                        class="input input-bordered input-xs w-full"
                        placeholder="数据类型"
                      >
                      <span
                        v-else
                        class="font-mono text-sm text-base-content/60 block"
                      >
                        {{ column.type }}
                      </span>
                    </td>
                    <td>
                      <input
                        v-if="isDetailEditMode || isNewTable"
                        v-model="column.comment"
                        type="text"
                        class="input input-bordered input-xs w-full"
                        placeholder="字段注释"
                      >
                      <span
                        v-else
                        class="max-w-xs truncate block"
                      >
                        {{ column.comment || '-' }}
                      </span>
                    </td>
                    <td>
                      <input
                        v-if="isDetailEditMode || isNewTable"
                        v-model="column.businessType"
                        type="text"
                        class="input input-bordered input-xs w-full"
                        placeholder="业务类型"
                      >
                      <span
                        v-else
                        class="text-sm block"
                      >
                        {{ column.businessType || '-' }}
                      </span>
                    </td>
                    <td>
                      <select
                        v-if="isDetailEditMode || isNewTable"
                        v-model="column.relationConfigId"
                        class="select select-bordered select-xs w-full"
                      >
                        <option value="">
                          无关联
                        </option>
                        <option
                          v-for="relation in availableRelations"
                          :key="relation.id"
                          :value="relation.id"
                        >
                          {{ relation.id }} ({{ relation.relation_desc || '无描述' }})
                        </option>
                      </select>
                      <span
                        v-else
                        class="block"
                      >
                        {{ column.relationConfigId || '-' }}
                      </span>
                    </td>
                    <td>
                      <input
                        v-if="isDetailEditMode || isNewTable"
                        v-model="column.isAvailable"
                        type="checkbox"
                        class="checkbox checkbox-xs"
                      >
                      <input
                        v-else
                        type="checkbox"
                        class="checkbox checkbox-xs"
                        :checked="column.isAvailable"
                        disabled
                      >
                    </td>
                    <td v-if="isDetailEditMode || isNewTable">
                      <div class="flex gap-1">
                        <button
                          class="btn btn-ghost btn-xs p-1"
                          title="删除字段"
                          @click="removeColumn(index)"
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
                {{ isDetailEditMode || isNewTable ? '暂无字段，点击"添加字段"按钮开始配置。' : '暂无字段信息' }}
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Actions -->
        <div class="p-6 border-t border-base-300 flex justify-end gap-2 flex-shrink-0">
          <button
            type="button"
            class="btn btn-ghost shadow"
            @click="closeDetailModal"
          >
            {{ isDetailEditMode || isNewTable ? '取消' : '关闭' }}
          </button>
          <button
            v-if="isDetailEditMode || isNewTable"
            type="button"
            class="btn btn-primary"
            :disabled="saving"
            @click="saveTableDetail"
          >
            <span
              v-if="saving"
              class="loading loading-spinner loading-sm"
            />
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { metadataService } from '@services/api'
import DataTable from '@/components/common/DataTable.vue'
// import type { TableMetadata, ColumnMetadata } from '@/types/index'

const { success, error } = useToast()

// State
const tables = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showDetailModal = ref(false)
const editingTable = ref<any | null>(null)
const isDetailEditMode = ref(false)
const isNewTable = ref(false)
const columns = ref<any[]>([])
const availableRelations = ref<any[]>([])

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

// Load available relations
const loadRelations = async () => {
  try {
    availableRelations.value = await metadataService.getRelationConfigs()
  } catch (err) {
    error('加载关联配置失败')
  }
}

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

// Open add table modal
const openAddTable = () => {
  isNewTable.value = true
  isDetailEditMode.value = true
  editingTable.value = null

  // Start with empty columns for new table
  columns.value = []

  // Reset form
  Object.assign(tableForm, {
    name: '',
    comment: ''
  })

  showDetailModal.value = true
}

// Open table detail
const openTableDetail = async (table: any, editMode: boolean = false) => {
  isNewTable.value = false
  isDetailEditMode.value = editMode
  editingTable.value = table

  // Set form data
  Object.assign(tableForm, {
    name: table.name,
    comment: table.comment || ''
  })

  // Load columns for this table
  await loadColumns(table)

  showDetailModal.value = true
}

// Enter edit mode
const enterEditMode = () => {
  isDetailEditMode.value = true
}

// Close detail modal
const closeDetailModal = () => {
  showDetailModal.value = false
  editingTable.value = null
  isDetailEditMode.value = false
  isNewTable.value = false
  columns.value = []

  // Reset form
  Object.assign(tableForm, {
    name: '',
    comment: ''
  })
}

// Handle backdrop click
const handleBackdropClick = () => {
  // 只在非编辑模式下允许点击背景关闭
  if (!isDetailEditMode.value && !isNewTable.value) {
    closeDetailModal()
  }
}

// Load columns for a table
const loadColumns = async (table?: any) => {
  const targetTable = table || editingTable.value
  if (!targetTable) return

  try {
    // Get tables data to find the current table with its columns
    const tables = await metadataService.getTables()
    const currentTable = tables.find((t: any) => t.name === targetTable.name)

    if (currentTable && (currentTable as any).columns) {
      // Transform API response to match our component format
      columns.value = (currentTable as any).columns.map((column: any, index: number) => ({
        id: column.id || index + 1, // Use real column ID if available
        name: column.name,
        type: column.type,
        comment: column.comment,
        businessType: column.business_type,
        relationConfigId: column.relation_config_id,
        isAvailable: column.is_available === undefined ? true : column.is_available === 0
      }))
    } else {
      columns.value = []
    }
  } catch (err) {
    error('加载字段列表失败')
  }
}

// Add new column
const addNewColumn = () => {
  const newColumn = {
    id: Date.now(),
    name: '',
    type: 'VARCHAR',
    comment: '',
    businessType: '',
    relationConfigId: null,
    isAvailable: 0 // 0 代表启用
  }
  columns.value.push(newColumn)
}

// Remove column
const removeColumn = (index: number) => {
  const column = columns.value[index]
  if (confirm(`确定要删除字段 "${column.name || '未命名字段'}" 吗？此操作不可恢复。`)) {
    columns.value.splice(index, 1)
  }
}

// Save table detail
const saveTableDetail = async () => {
  try {
    saving.value = true

    let tableId: number
    if (isNewTable.value) {
      // Create new table
      const response = await metadataService.createTable({
        name: tableForm.name,
        comment: tableForm.comment,
        isAvailable: true
      })
      tableId = response.data.id  // 从data字段获取表ID
      success('表已创建')
    } else {
      // Update existing table
      await metadataService.updateTable(editingTable.value.id, {
        comment: tableForm.comment
      })
      tableId = editingTable.value.id
      success('表已更新')
    }

    // Save columns using new API
    if (columns.value.length > 0) {
      for (const column of columns.value) {
        const columnData = {
          table_id: tableId,
          name: column.name,
          type: column.type,
          comment: column.comment,
          is_available: column.isAvailable ? 0 : 1, // 转换为后端格式：0=启用，1=不启用
          business_type: column.businessType,
          relation_config_id: column.relationConfigId || null
        }

        if (typeof column.id === 'number' && column.id > 1000000) {
          // New column (temporary ID), create it
          await metadataService.createColumn(columnData)
        } else if (typeof column.id === 'number') {
          // Existing column, update it
          await metadataService.updateColumn(column.id, columnData)
        }
      }
      success('字段配置已保存')
    }

    closeDetailModal()
    await loadTables()
  } catch (err) {
    error(isNewTable.value ? '创建表失败' : '更新表失败')
  } finally {
    saving.value = false
  }
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

// Initialize
onMounted(() => {
  loadTables()
  loadRelations()
})
</script>
