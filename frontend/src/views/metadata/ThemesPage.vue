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
          placeholder="搜索主题名称或描述..."
          class="input input-bordered input-sm"
          @input="debouncedSearch"
        >
      </div>

      <div class="form-control">
        <label class="label">
          <span class="label-text">主题类型</span>
        </label>
        <select
          v-model="filters.themeType"
          class="select select-bordered select-sm"
          @change="loadThemes"
        >
          <option value="">
            全部
          </option>
          <option value="normal">
            一般主题
          </option>
          <option value="public">
            通用主题
          </option>
        </select>
      </div>

      <button
        class="btn btn-primary"
        @click="openAddTheme"
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
        添加主题
      </button>
    </div>

    <!-- Themes Table -->
    <div class="overflow-x-auto bg-base-100 rounded-lg shadow-md border border-base-300">
      <DataTable
        :data="themes"
        :columns="themeColumns"
        :loading="loading"
        :searchable="false"
        :paginated="true"
        :page-size="20"
        empty-state-type="no-data"
        row-key="id"
        :show-header="true"
        :column-settings="true"
      >
        <template #cell-theme_name="{ value }">
          <div class="font-medium">
            {{ value }}
          </div>
        </template>

        <template #cell-theme_type="{ value }">
          <div
            :class="[
              'badge badge-sm',
              value === 'public' ? 'badge-primary' : 'badge-secondary'
            ]"
          >
            {{ value === 'public' ? '通用主题' : '一般主题' }}
          </div>
        </template>

        <template #cell-theme_description="{ value }">
          <div
            class="max-w-xs truncate"
            :title="value"
          >
            {{ value || '-' }}
          </div>
        </template>

        <template #cell-department="{ value }">
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
              @click="openThemeDetail(record, false)"
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
              @click="confirmDeleteTheme(record)"
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

    <!-- Theme Detail Modal -->
    <div
      v-if="showDetailModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-base-100 rounded-lg w-11/12 max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <!-- Header -->
        <div class="p-6 border-b border-base-300 flex justify-between items-center flex-shrink-0">
          <h3 class="font-bold text-lg">
            {{ isNewTheme ? '添加主题' : editingTheme?.theme_name || '主题详情' }}
          </h3>
          <div class="flex gap-2">
            <button
              v-if="!isNewTheme && !isDetailEditMode"
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
          <!-- Theme Info Section -->
          <div class="mb-6">
            <h4 class="font-semibold text-lg mb-4 pb-2 border-b border-base-300">
              主题信息
            </h4>
            <form class="space-y-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="form-control">
                  <label class="label">
                    <span class="label-text">主题名称 *</span>
                  </label>
                  <input
                    v-model="themeForm.theme_name"
                    type="text"
                    placeholder="请输入主题名称"
                    class="input input-bordered"
                    :disabled="!isDetailEditMode && !isNewTheme"
                    required
                  >
                </div>

                <div class="form-control">
                  <label class="label">
                    <span class="label-text">主题类型 *</span>
                  </label>
                  <select
                    v-model="themeForm.theme_type"
                    class="select select-bordered"
                    :disabled="!isDetailEditMode && !isNewTheme"
                    required
                  >
                    <option value="normal">
                      一般主题
                    </option>
                    <option value="public">
                      通用主题
                    </option>
                  </select>
                </div>

                <div class="form-control md:col-span-2">
                  <label class="label">
                    <span class="label-text">主题描述</span>
                  </label>
                  <textarea
                    v-model="themeForm.theme_description"
                    placeholder="请输入主题描述"
                    class="textarea textarea-bordered"
                    rows="3"
                    :disabled="!isDetailEditMode && !isNewTheme"
                  />
                </div>

                <div class="form-control md:col-span-2">
                  <label class="label">
                    <span class="label-text">关联部门</span>
                  </label>
                  <input
                    v-model="themeForm.department"
                    type="text"
                    placeholder="请输入关联部门"
                    class="input input-bordered"
                    :disabled="!isDetailEditMode && !isNewTheme"
                  >
                </div>
              </div>
            </form>
          </div>

          <!-- Tables Section -->
          <div>
            <h4 class="font-semibold text-lg mb-4 pb-2 border-b border-base-300">
              关联表信息
            </h4>
            <div class="flex justify-between items-center mb-4">
              <div class="text-sm text-base-content/60">
                已选择 {{ selectedTables.length }} 张表
              </div>
              <button
                v-if="isDetailEditMode || isNewTheme"
                class="btn btn-primary btn-sm"
                @click="openTableSelector"
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
                选择表
              </button>
            </div>

            <!-- Tables List -->
            <div class="w-full overflow-x-auto">
              <table class="table table-sm w-full">
                <thead>
                  <tr>
                    <th class="w-48">
                      表名
                    </th>
                    <th class="w-64">
                      表注释
                    </th>
                    <th class="w-24">
                      状态
                    </th>
                    <th
                      v-if="isDetailEditMode || isNewTheme"
                      class="w-16"
                    >
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="table in selectedTables"
                    :key="table.id"
                  >
                    <td>
                      <span class="font-mono text-sm">
                        {{ table.name }}
                      </span>
                    </td>
                    <td>
                      <span class="max-w-xs truncate block">
                        {{ table.comment || '-' }}
                      </span>
                    </td>
                    <td>
                      <div
                        :class="[
                          'badge badge-sm',
                          table.is_available === 0 ? 'badge-success' : 'badge-error'
                        ]"
                      >
                        {{ table.is_available === 0 ? '可用' : '不可用' }}
                      </div>
                    </td>
                    <td v-if="isDetailEditMode || isNewTheme">
                      <div class="flex gap-1">
                        <button
                          class="btn btn-ghost btn-xs p-1"
                          title="移除表"
                          @click="removeTable(table)"
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
                              d="M6 18L18 6M6 6l12 12"
                            />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>

              <div
                v-if="selectedTables.length === 0"
                class="text-center py-8 text-base-content/60"
              >
                {{ isDetailEditMode || isNewTheme ? '暂无关联表，点击"选择表"按钮开始配置。' : '暂无关联表信息' }}
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
            {{ isDetailEditMode || isNewTheme ? '取消' : '关闭' }}
          </button>
          <button
            v-if="isDetailEditMode || isNewTheme"
            type="button"
            class="btn btn-primary"
            :disabled="saving"
            @click="saveThemeDetail"
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

    <!-- Table Selector Modal -->
    <div
      v-if="showTableSelector"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-base-100 rounded-lg w-11/12 max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <!-- Header -->
        <div class="p-6 border-b border-base-300 flex justify-between items-center flex-shrink-0">
          <h3 class="font-bold text-lg">
            选择关联表
          </h3>
          <button
            class="btn btn-ghost btn-sm"
            @click="closeTableSelector"
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto p-6">
          <div class="mb-4">
            <input
              v-model="tableSearchQuery"
              type="text"
              placeholder="搜索表名..."
              class="input input-bordered input-sm w-full"
            >
          </div>

          <div class="max-h-96 overflow-y-auto">
            <div
              v-for="table in filteredAvailableTables"
              :key="table.id"
              class="flex items-center justify-between p-3 border border-base-300 rounded-lg mb-2"
            >
              <div class="flex items-center gap-3">
                <input
                  v-model="selected_table_ids"
                  :value="table.id"
                  type="checkbox"
                  class="checkbox checkbox-sm"
                >
                <div>
                  <div class="font-medium">
                    {{ table.name }}
                  </div>
                  <div class="text-sm text-base-content/60">
                    {{ table.comment || '无注释' }}
                  </div>
                </div>
              </div>
              <div
                :class="[
                  'badge badge-sm',
                  table.is_available === 0 ? 'badge-success' : 'badge-error'
                ]"
              >
                {{ table.is_available === 0 ? '可用' : '不可用' }}
              </div>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="p-6 border-t border-base-300 flex justify-end gap-2 flex-shrink-0">
          <button
            class="btn btn-ghost"
            @click="closeTableSelector"
          >
            取消
          </button>
          <button
            class="btn btn-primary"
            @click="confirmTableSelection"
          >
            确认选择 ({{ selected_table_ids.length }})
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useToast } from '@/composables/useToast'
import { metadataService } from '@services/api'
import DataTable from '@/components/common/DataTable.vue'

const { success, error } = useToast()

// State
const themes = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showDetailModal = ref(false)
const editingTheme = ref<any | null>(null)
const isDetailEditMode = ref(false)
const isNewTheme = ref(false)
const selectedTables = ref<any[]>([])
const availableTables = ref<any[]>([])
const showTableSelector = ref(false)
const selected_table_ids = ref<number[]>([])
const tableSearchQuery = ref('')

// Filters
const filters = reactive({
  search: '',
  themeType: ''
})

// Form
const themeForm = reactive<{
  theme_name: string
  theme_description: string
  theme_type: 'normal' | 'public'
  department: string
}>({
  theme_name: '',
  theme_description: '',
  theme_type: 'normal',
  department: ''
})

// Table columns
const themeColumns = [
  {
    key: 'theme_name',
    title: '主题名称',
    sortable: true,
    visible: true
  },
  {
    key: 'theme_type',
    title: '主题类型',
    sortable: true,
    visible: true
  },
  {
    key: 'theme_description',
    title: '主题描述',
    sortable: true,
    visible: true
  },
  {
    key: 'department',
    title: '关联部门',
    sortable: true,
    visible: true
  },
  {
    key: 'created_at',
    title: '创建时间',
    sortable: true,
    visible: true
  }
]

// Computed
const filteredAvailableTables = computed(() => {
  if (!tableSearchQuery.value) {
    return availableTables.value
  }
  const search = tableSearchQuery.value.toLowerCase()
  return availableTables.value.filter(table =>
    table.name.toLowerCase().includes(search) ||
    (table.comment && table.comment.toLowerCase().includes(search))
  )
})

// Debounced search
let searchTimeout: number
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(loadThemes, 500)
}

// Load themes
const loadThemes = async () => {
  try {
    loading.value = true

    themes.value = await metadataService.getThemes()

    // Apply client-side filters
    if (filters.search) {
      const search = filters.search.toLowerCase()
      themes.value = themes.value.filter(theme =>
        theme.theme_name.toLowerCase().includes(search) ||
        (theme.theme_description && theme.theme_description.toLowerCase().includes(search)) ||
        (theme.department && theme.department.toLowerCase().includes(search))
      )
    }

    if (filters.themeType) {
      themes.value = themes.value.filter(theme => theme.theme_type === filters.themeType)
    }
  } catch (err) {
    error('加载主题列表失败')
  } finally {
    loading.value = false
  }
}

// Load available tables
const loadAvailableTables = async () => {
  try {
    availableTables.value = await metadataService.getTables()
  } catch (err) {
    error('加载表列表失败')
  }
}

// Open add theme modal
const openAddTheme = () => {
  isNewTheme.value = true
  isDetailEditMode.value = true
  editingTheme.value = null
  selectedTables.value = []

  // Reset form
  Object.assign(themeForm, {
    theme_name: '',
    theme_description: '',
    theme_type: 'normal',
    department: ''
  })

  showDetailModal.value = true
}

// Open theme detail
const openThemeDetail = async (theme: any, editMode: boolean = false) => {
  isNewTheme.value = false
  isDetailEditMode.value = editMode
  editingTheme.value = theme

  // Set form data
  Object.assign(themeForm, {
    theme_name: theme.theme_name,
    theme_description: theme.theme_description || '',
    theme_type: theme.theme_type,
    department: theme.department || ''
  })

  // Load tables for this theme
  await loadThemeTables(theme)

  showDetailModal.value = true
}

// Load theme tables
const loadThemeTables = async (theme: any) => {
  try {
    selectedTables.value = await metadataService.getThemeTables(theme.id)
  } catch (err) {
    error('加载主题关联表失败')
  }
}

// Enter edit mode
const enterEditMode = () => {
  isDetailEditMode.value = true
}

// Close detail modal
const closeDetailModal = () => {
  showDetailModal.value = false
  editingTheme.value = null
  isDetailEditMode.value = false
  isNewTheme.value = false
  selectedTables.value = []

  // Reset form
  Object.assign(themeForm, {
    theme_name: '',
    theme_description: '',
    theme_type: 'normal',
    department: ''
  })
}

// Open table selector
const openTableSelector = () => {
  selected_table_ids.value = selectedTables.value.map(table => table.id)
  tableSearchQuery.value = ''
  showTableSelector.value = true
}

// Close table selector
const closeTableSelector = () => {
  showTableSelector.value = false
  selected_table_ids.value = []
  tableSearchQuery.value = ''
}

// Confirm table selection
const confirmTableSelection = () => {
  selectedTables.value = availableTables.value.filter(table =>
  selected_table_ids.value.includes(table.id)
  )
  closeTableSelector()
}

// Remove table
const removeTable = (table: any) => {
  selectedTables.value = selectedTables.value.filter(t => t.id !== table.id)
}

// Save theme detail
const saveThemeDetail = async () => {
  try {
    saving.value = true

    let themeId: number
    if (isNewTheme.value) {
      // Create new theme first
      const newTheme = await metadataService.createTheme(themeForm)
      editingTheme.value = newTheme
      themeId = newTheme.id
      success('主题已创建')
    } else {
      // Update existing theme
      themeId = editingTheme.value.id
      await metadataService.updateTheme(themeId, themeForm)
      success('主题已更新')
    }

    // Save theme table associations only if we have tables to save
    if (selectedTables.value.length > 0) {
      try {
        // For existing themes, remove all existing associations first
        if (!isNewTheme.value) {
          const currentTables = await metadataService.getThemeTables(themeId)
          for (const table of currentTables) {
            await metadataService.removeTableFromTheme(themeId, table.id)
          }
        }

        // Add new associations
        for (const table of selectedTables.value) {
          await metadataService.addTableToTheme(themeId, table.id)
        }
        success('关联表已更新')
      } catch (tableErr) {
        error('保存关联表失败')
        console.error('Table association error:', tableErr)
      }
    }

    closeDetailModal()
    await loadThemes()
  } catch (err) {
    error(isNewTheme.value ? '创建主题失败' : '更新主题失败')
    console.error('Save theme error:', err)
  } finally {
    saving.value = false
  }
}

// Confirm delete theme
const confirmDeleteTheme = (theme: any) => {
  if (confirm(`确定要删除主题 "${theme.theme_name}" 吗？此操作不可恢复。`)) {
    deleteTheme(theme)
  }
}

// Delete theme
const deleteTheme = async (theme: any) => {
  try {
    await metadataService.deleteTheme(theme.id)
    success('主题已删除')
    await loadThemes()
  } catch (err) {
    error('删除主题失败')
  }
}

// Initialize
onMounted(() => {
  loadThemes()
  loadAvailableTables()
})
</script>
