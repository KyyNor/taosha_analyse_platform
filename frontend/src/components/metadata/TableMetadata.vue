<template>
  <div class="space-y-6">
    <!-- Add Table Section -->
    <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
      <div class="flex items-center space-x-2 mb-4">
        <PlusIcon class="w-5 h-5 text-blue-600" aria-label="添加图标" />
        <h3 class="text-lg font-semibold text-slate-800">添加新表</h3>
      </div>
      
      <form @submit.prevent="addTable" class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">表名</label>
            <input
              v-model="newTable.name"
              type="text"
              required
              placeholder="输入表名"
              class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">状态</label>
            <select
              v-model="newTable.isAvailable"
              class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option :value="0">可用</option>
              <option :value="1">不可用</option>
            </select>
          </div>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">表描述</label>
          <textarea
            v-model="newTable.comment"
            rows="3"
            placeholder="输入表的描述信息"
            class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          ></textarea>
        </div>
        
        <button
          type="submit"
          :disabled="!newTable.name || isAdding"
          class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 hover:scale-105 hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
        >
          {{ isAdding ? '添加中...' : '添加表' }}
        </button>
      </form>
    </div>

    <!-- Tables List -->
    <div class="bg-white rounded-lg border border-slate-200 shadow-sm">
      <div class="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <ClipboardDocumentListIcon class="w-5 h-5 text-blue-600" aria-label="表管理图标" />
          <h3 class="text-lg font-semibold text-slate-800">表元数据管理</h3>
        </div>
        <button
          @click="refreshTables"
          :disabled="isRefreshing"
          class="px-3 py-1 text-sm bg-slate-100 text-slate-600 rounded hover:bg-slate-200 transition-colors duration-200 disabled:opacity-50"
        >
          <ArrowPathIcon class="w-4 h-4 mr-1" aria-label="刷新图标" />
          <span>{{ isRefreshing ? '刷新中...' : '刷新' }}</span>
        </button>
      </div>

      <div class="p-6">
        <div v-if="isLoading" class="text-center py-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <div class="text-slate-500 mt-2">加载中...</div>
        </div>

        <div v-else-if="tables.length === 0" class="text-center py-8">
          <div class="text-slate-500">暂无表元数据</div>
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="table in tables"
            :key="table.name"
            class="border border-slate-200 rounded-lg overflow-hidden"
          >
            <!-- Table Header -->
            <div class="bg-slate-50 px-4 py-3 flex items-center justify-between">
              <div class="flex items-center space-x-3">
                <div :class="['w-3 h-3 rounded-full', table.is_available === 0 ? 'bg-green-500' : 'bg-red-500']"></div>
                <div class="flex items-center space-x-2">
                  <TableCellsIcon class="w-4 h-4 text-blue-600" aria-label="表格图标" />
                  <h4 class="font-medium text-slate-800">{{ table.name }}</h4>
                </div>
                <span :class="['px-2 py-1 text-xs rounded', table.is_available === 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800']">
                  {{ table.is_available === 0 ? '可用' : '不可用' }}
                </span>
              </div>
              
              <div class="flex items-center space-x-2">
                <button
                  @click="toggleTableExpansion(table.name)"
                  class="p-1 hover:bg-slate-200 rounded transition-colors duration-200"
                >
                  <ChevronDownIcon 
                    :class="['w-4 h-4 text-slate-500 transition-transform duration-200', 
                             expandedTables.has(table.name) ? 'rotate-180' : '']" 
                  />
                </button>
              </div>
            </div>

            <!-- Table Details -->
            <div v-if="expandedTables.has(table.name)" class="p-4 space-y-4">
              <!-- Basic Info -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-2">描述</label>
                  <textarea
                    v-model="table.comment"
                    rows="2"
                    class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  ></textarea>
                </div>
                
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-2">状态</label>
                  <select
                    v-model="table.is_available"
                    class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option :value="0">可用</option>
                    <option :value="1">不可用</option>
                  </select>
                </div>
              </div>

              <!-- Action Buttons -->
              <div class="flex space-x-2">
                <button
                  @click="updateTable(table)"
                  class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors duration-200"
                >
                  <PencilIcon class="w-4 h-4 mr-1" aria-label="编辑图标" />
                  <span>更新</span>
                </button>
                <button
                  @click="confirmDeleteTable(table.name)"
                  class="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600 transition-colors duration-200"
                >
                  <TrashIcon class="w-4 h-4 mr-1" aria-label="删除图标" />
                  <span>删除</span>
                </button>
              </div>

              <!-- Columns Section -->
              <div class="border-t border-slate-200 pt-4">
                <h5 class="font-medium text-slate-800 mb-3">列信息 ({{ table.columns?.length || 0 }})</h5>
                
                <!-- Add Column Form -->
                <div class="mb-4 p-4 bg-slate-50 rounded-lg">
                  <h6 class="text-sm font-medium text-slate-700 mb-3">添加新列</h6>
                  <ColumnEditor
                    :table-name="table.name"
                    @column-added="handleColumnAdded"
                  />
                </div>

                <!-- Columns List -->
                <div v-if="table.columns && table.columns.length > 0">
                  <DataTable
                    :columns="columnTableColumns"
                    :data="table.columns"
                    :show-footer="false"
                  >
                    <template #column-is_available="{ value }">
                      <span :class="['px-2 py-1 text-xs rounded', value === 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800']">
                        {{ value === 0 ? '可用' : '不可用' }}
                      </span>
                    </template>
                    
                    <template #actions="{ row }">
                      <div class="flex space-x-1">
                        <button
                          @click="editColumn(table.name, row as ColumnMetadata)"
                          class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded hover:bg-blue-200 transition-colors duration-200"
                        >
                          编辑
                        </button>
                        <button
                          @click="deleteColumn(table.name, row.name)"
                          class="px-2 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200 transition-colors duration-200"
                        >
                          删除
                        </button>
                      </div>
                    </template>
                  </DataTable>
                </div>
                
                <div v-else class="text-center text-slate-500 py-4">
                  该表暂无列元数据
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Column Modal -->
    <div v-if="editingColumn" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <h3 class="text-lg font-semibold text-slate-800 mb-4">编辑列: {{ editingColumn.name }}</h3>
        
        <ColumnEditor
          :table-name="editingTableName"
          :column="editingColumn"
          :is-editing="true"
          @column-updated="handleColumnUpdated"
          @cancel="cancelEdit"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ChevronDownIcon, PlusIcon, ClipboardDocumentListIcon, ArrowPathIcon, TableCellsIcon, PencilIcon, TrashIcon } from '@heroicons/vue/24/outline'
import type { TableMetadata, ColumnMetadata, Column } from '@/types'
import { apiClient } from '@/api'
import DataTable from '@/components/DataTable.vue'
import ColumnEditor from './ColumnEditor.vue'

// 响应式数据
const tables = ref<TableMetadata[]>([])
const isLoading = ref(false)
const isRefreshing = ref(false)
const isAdding = ref(false)
const expandedTables = ref<Set<string>>(new Set())
const editingColumn = ref<ColumnMetadata | null>(null)
const editingTableName = ref('')

// 新表表单
const newTable = ref({
  name: '',
  comment: '',
  isAvailable: 0
})

// 列表格列定义
const columnTableColumns: Column[] = [
  { key: 'name', title: '列名', type: 'text' },
  { key: 'type', title: '存储类型', type: 'text' },
  { key: 'business_type', title: '业务类型', type: 'text' },
  { key: 'is_available', title: '状态', type: 'status' },
  { key: 'relation_id', title: '关联ID', type: 'text' },
  { key: 'comment', title: '描述', type: 'text' }
]

// 加载表数据
const loadTables = async () => {
  isLoading.value = true
  try {
    tables.value = await apiClient.getAllMetadataTables()
  } catch (error) {
    console.error('加载表数据失败:', error)
  } finally {
    isLoading.value = false
  }
}

// 刷新表数据
const refreshTables = async () => {
  isRefreshing.value = true
  try {
    tables.value = await apiClient.getAllMetadataTables()
  } catch (error) {
    console.error('刷新表数据失败:', error)
  } finally {
    isRefreshing.value = false
  }
}

// 添加表
const addTable = async () => {
  if (!newTable.value.name) return
  
  isAdding.value = true
  try {
    const success = await apiClient.addTableMetadata(
      newTable.value.name,
      newTable.value.comment,
      newTable.value.isAvailable
    )
    
    if (success) {
      // 重置表单
      newTable.value = {
        name: '',
        comment: '',
        isAvailable: 0
      }
      
      // 刷新列表
      await refreshTables()
    }
  } catch (error) {
    console.error('添加表失败:', error)
  } finally {
    isAdding.value = false
  }
}

// 更新表
const updateTable = async (table: TableMetadata) => {
  try {
    const success = await apiClient.updateTableMetadata(
      table.name,
      table.comment,
      table.is_available
    )
    
    if (success) {
      await refreshTables()
    }
  } catch (error) {
    console.error('更新表失败:', error)
  }
}

// 删除表确认
const confirmDeleteTable = (tableName: string) => {
  if (confirm(`确定要删除表 "${tableName}" 吗？此操作不可恢复。`)) {
    deleteTable(tableName)
  }
}

// 删除表
const deleteTable = async (tableName: string) => {
  try {
    const success = await apiClient.deleteTableMetadata(tableName)
    
    if (success) {
      await refreshTables()
    }
  } catch (error) {
    console.error('删除表失败:', error)
  }
}

// 切换表展开状态
const toggleTableExpansion = (tableName: string) => {
  if (expandedTables.value.has(tableName)) {
    expandedTables.value.delete(tableName)
  } else {
    expandedTables.value.add(tableName)
  }
}

// 编辑列
const editColumn = (tableName: string, column: ColumnMetadata) => {
  editingTableName.value = tableName
  editingColumn.value = { ...column }
}

// 取消编辑
const cancelEdit = () => {
  editingColumn.value = null
  editingTableName.value = ''
}

// 删除列
const deleteColumn = async (tableName: string, columnName: string) => {
  if (confirm(`确定要删除列 "${columnName}" 吗？`)) {
    try {
      const success = await apiClient.deleteColumnMetadata(tableName, columnName)
      if (success) {
        await refreshTables()
      }
    } catch (error) {
      console.error('删除列失败:', error)
    }
  }
}

// 处理列添加
const handleColumnAdded = () => {
  refreshTables()
}

// 处理列更新
const handleColumnUpdated = () => {
  editingColumn.value = null
  editingTableName.value = ''
  refreshTables()
}

// 初始化
onMounted(() => {
  loadTables()
})
</script>