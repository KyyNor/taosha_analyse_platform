<template>
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <form
        class="grid grid-cols-1 lg:grid-cols-10 gap-4"
        @submit.prevent="handleSubmit"
      >
        <!-- 第一列：表选择区域 -->
        <div class="lg:col-span-2 space-y-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text font-medium">数据范围</span>
            </label>
            <div class="tabs tabs-boxed bg-base-300">
              <a
                class="tab flex-1"
                :class="{ 'tab-active': tableSelectionMode === 'theme', 'pointer-events-none opacity-50': loading }"
                @click="tableSelectionMode = 'theme'"
              >
                数据主题
              </a>
              <a
                class="tab flex-1"
                :class="{ 'tab-active': tableSelectionMode === 'table', 'pointer-events-none opacity-50': loading }"
                @click="tableSelectionMode = 'table'"
              >
                数据表
              </a>
            </div>
          </div>

          <!-- 数据主题选择 -->
          <div
            v-if="tableSelectionMode === 'theme'"
            class="form-control"
          >
            <select
              v-model="formData.selectedThemeId"
              class="select select-bordered"
              :disabled="loading || themesLoading"
            >
              <option value="">
                选择数据主题（可选）
              </option>
              <option
                v-for="theme in themes"
                :key="theme.id"
                :value="theme.id"
              >
                {{ theme.themeName }}
              </option>
            </select>
          </div>

          <!-- 数据表选择 -->
          <div
            v-else
            class="form-control"
          >
            <div class="dropdown dropdown-top">
              <label
                tabindex="0"
                class="btn btn-outline w-full justify-between"
                :class="{ 'btn-active': formData.selectedTableIds.length > 0 }"
              >
                <span class="truncate">
                  {{ formData.selectedTableIds.length > 0
                    ? `已选择 ${formData.selectedTableIds.length} 张表`
                    : '选择数据表（可选）'
                  }}
                </span>
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </label>
              <ul
                tabindex="0"
                class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-full max-h-60 overflow-y-auto z-10"
              >
                <div class="form-control mb-2">
                  <input
                    v-model="tableSearchQuery"
                    type="text"
                    placeholder="搜索表名..."
                    class="input input-bordered input-sm"
                  >
                </div>
                <li
                  v-for="table in filteredTables"
                  :key="table.id"
                >
                  <label class="cursor-pointer flex items-center gap-2 p-1">
                    <input
                      :id="`table-${table.id}`"
                      v-model="formData.selectedTableIds"
                      type="checkbox"
                      :value="table.id"
                      class="checkbox checkbox-sm"
                      :disabled="loading"
                    >
                    <span class="flex-1">{{ table.name }}</span>
                    <span class="badge badge-outline badge-xs">{{ table.dataSource }}</span>
                  </label>
                </li>
                <li
                  v-if="filteredTables.length === 0"
                  class="text-center text-base-content/60 py-2"
                >
                  未找到匹配的表
                </li>
              </ul>
            </div>

            <!-- 已选择的表标签 -->
            <div
              v-if="formData.selectedTableIds.length > 0"
              class="flex flex-wrap gap-1 mt-2"
            >
              <span
                v-for="tableId in formData.selectedTableIds"
                :key="tableId"
                class="badge badge-primary badge-sm"
              >
                {{ getTableName(tableId) }}
                <button
                  type="button"
                  class="ml-1"
                  @click="removeTable(tableId)"
                >
                  ✕
                </button>
              </span>
            </div>
          </div>
        </div>

        <!-- 第二列：查询问题输入 -->
        <div class="lg:col-span-6 space-y-2">
          <div class="form-control h-full">
            <label class="label">
              <span class="label-text font-medium">查询问题</span>
            </label>
            <textarea
              v-model="formData.query"
              class="textarea textarea-bordered h-24 resize-none"
              placeholder="请输入您的查询问题...&#10;例如：显示最近一个月的销售额"
              required
              :disabled="loading"
            />
            <label class="label">
              <span class="label-text-alt text-base-content/60">
                如："显示最近一个月的销售额"
              </span>
            </label>
          </div>
        </div>

        <!-- 第三列：模式切换和按钮 -->
        <div class="lg:col-span-2 space-y-4">
          <!-- 查询模式切换 -->
          <div class="form-control">
            <label class="label">
              <span class="label-text font-medium">查询模式</span>
            </label>

            <!-- DaisyUI Tabs 切换开关 -->
            <div class="flex justify-center">
              <div class="tabs tabs-boxed bg-base-300 inline-flex">
                <a
                  class="tab w-1/2"
                  :class="{ 'tab-active': !useThoroughMode, 'pointer-events-none opacity-50': loading }"
                  @click="useThoroughMode = false"
                >
                  优先验证
                </a>
                <a
                  class="tab w-1/2"
                  :class="{ 'tab-active': useThoroughMode, 'pointer-events-none opacity-50': loading }"
                  @click="useThoroughMode = true"
                >
                  优先生成
                </a>
              </div>
            </div>
          </div>

          <!-- 查询按钮组 -->
          <div class="pt-2">
            <!-- 有活跃查询时显示取消按钮 -->
            <button
              v-if="hasActiveQuery"
              type="button"
              class="btn btn-error w-full h-10"
              @click="handleCancel"
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
              取消查询
            </button>

            <!-- 无活跃查询时显示查询和重置按钮行 -->
            <div
              v-else
              class="flex gap-2"
            >
              <button
                type="submit"
                class="btn btn-primary h-10 flex-grow"
                :disabled="loading || !formData.query.trim()"
              >
                <span
                  v-if="loading"
                  class="loading loading-spinner loading-sm"
                />
                {{ loading ? '查询中...' : '开始查询' }}
              </button>

              <button
                type="button"
                class="btn btn-outline h-10 w-10 flex-shrink-0"
                title="重置"
                @click="handleReset"
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
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useQueryStore } from '@stores/query'
import { metadataService } from '@services/api'
import type { QueryRequest, DataTheme, TableMetadata } from '@/types/index'

interface Props {
  initialQuery?: string
  initialFlowType?: 'fast' | 'thorough'
  initialThemeId?: number
  initialTableIds?: number[]
}

const props = withDefaults(defineProps<Props>(), {
  initialQuery: '',
  initialFlowType: 'thorough',
  initialThemeId: 0,
  initialTableIds: () => []
})

const emit = defineEmits<{
  submit: [request: QueryRequest]
  cancel: []
}>()

const queryStore = useQueryStore()

// Form data
const formData = ref<QueryRequest>({
  query: props.initialQuery,
  flow_type: props.initialFlowType,
  selectedThemeId: props.initialThemeId || undefined,
  selectedTableIds: props.initialTableIds
})

// 监听 initialQuery 变化，更新表单数据
watch(() => props.initialQuery, (newQuery) => {
  if (newQuery) {
    formData.value.query = newQuery
  }
}, { immediate: true })

// UI state
const tableSelectionMode = ref<'theme' | 'table'>('theme')
const tableSearchQuery = ref('')
const themes = ref<DataTheme[]>([])
const availableTables = ref<TableMetadata[]>([])
const themesLoading = ref(false)

// 模式切换的响应式绑定
const useThoroughMode = computed({
  get: () => formData.value.flow_type === 'thorough',
  set: (value: boolean) => {
    formData.value.flow_type = value ? 'thorough' : 'fast'
  }
})

// 过滤后的表列表
const filteredTables = computed(() => {
  if (!tableSearchQuery.value.trim()) {
    return availableTables.value
  }
  const query = tableSearchQuery.value.toLowerCase()
  return availableTables.value.filter(table =>
    table.name.toLowerCase().includes(query) ||
    table.dataSource?.toLowerCase().includes(query)
  )
})

// Computed
const loading = computed(() => queryStore.isLoading)
const hasActiveQuery = computed(() => queryStore.hasActiveQuery)

// 监听表选择模式切换，清理相关选择
watch(tableSelectionMode, (newMode) => {
  if (newMode === 'theme') {
    // 切换到主题模式时，清空表选择
    formData.value.selectedTableIds = []
  } else {
    // 切换到表模式时，清空主题选择
    formData.value.selectedThemeId = undefined
  }
})


// Load themes
const loadThemes = async () => {
  try {
    themesLoading.value = true
    themes.value = await metadataService.getThemes()
  } catch (error) {
    console.error('Failed to load themes:', error)
  } finally {
    themesLoading.value = false
  }
}

// Load available tables
const loadAvailableTables = async () => {
  try {
    availableTables.value = await metadataService.getTables(undefined, true)
  } catch (error) {
    console.error('Failed to load tables:', error)
  }
}

// Get table name by ID
const getTableName = (tableId: number) => {
  const table = availableTables.value.find(t => t.id === tableId)
  return table?.name || `Table ${tableId}`
}

// Remove table from selection
const removeTable = (tableId: number) => {
  const index = formData.value.selectedTableIds?.indexOf(tableId)
  if (index > -1 && formData.value.selectedTableIds) {
    formData.value.selectedTableIds.splice(index, 1)
  }
}

// Handle form submit
const handleSubmit = () => {
  if (!formData.value.query.trim()) return

  const request: QueryRequest = {
    query: formData.value.query.trim(),
    flow_type: formData.value.flow_type,
    selectedThemeId: formData.value.selectedThemeId,
    selectedTableIds: formData.value.selectedTableIds?.length
      ? formData.value.selectedTableIds
      : undefined
  }

  emit('submit', request)
}

// Handle cancel
const handleCancel = () => {
  emit('cancel')
}

// Handle reset
const handleReset = () => {
  formData.value = {
    query: '',
    flow_type: 'thorough',
    selectedThemeId: undefined,
    selectedTableIds: []
  }
  tableSearchQuery.value = ''
  tableSelectionMode.value = 'theme'
}

// Initialize
onMounted(() => {
  loadThemes()
  loadAvailableTables()
})
</script>
