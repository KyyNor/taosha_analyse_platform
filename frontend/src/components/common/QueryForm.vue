<template>
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <h2 class="card-title text-xl mb-4">
        自然语言查询
      </h2>

      <form
        class="space-y-4"
        @submit.prevent="handleSubmit"
      >
        <!-- Query Input -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-medium">查询问题</span>
            <span class="label-text-alt text-base-content/60">
              支持自然语言描述，如："显示最近一个月的销售额"
            </span>
          </label>
          <textarea
            v-model="formData.query"
            class="textarea textarea-bordered h-24 resize-none"
            placeholder="请输入您的查询问题..."
            required
            :disabled="loading"
          />
        </div>

        <!-- Query Options -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Flow Type -->
          <div class="form-control">
            <label class="label">
              <span class="label-text font-medium">查询模式</span>
            </label>
            <select
              v-model="formData.flowType"
              class="select select-bordered"
              :disabled="loading"
            >
              <option value="fast">
                快速模式（先验证后生成）
              </option>
              <option value="thorough">
                详细模式（先生成后验证）
              </option>
            </select>
            <label class="label">
              <span class="label-text-alt text-base-content/60">
                {{ formData.flowType === 'fast' ? '适合简单查询，速度更快' : '适合复杂查询，准确性更高' }}
              </span>
            </label>
          </div>

          <!-- Data Theme -->
          <div class="form-control">
            <label class="label">
              <span class="label-text font-medium">数据主题</span>
            </label>
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
            <label class="label">
              <span class="label-text-alt text-base-content/60">
                选择相关数据主题可以提高查询准确性
              </span>
            </label>
          </div>
        </div>

        <!-- Table Selection -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-medium">相关表（可选）</span>
            <span class="label-text-alt">
              <button
                type="button"
                class="link link-primary text-xs"
                @click="toggleTableSelection"
              >
                {{ showAllTables ? '隐藏' : '显示' }}所有表
              </button>
            </span>
          </label>

          <div
            v-if="showAllTables"
            class="space-y-2 max-h-40 overflow-y-auto border rounded-lg p-2"
          >
            <div
              v-for="table in availableTables"
              :key="table.id"
              class="flex items-center gap-2"
            >
              <input
                :id="`table-${table.id}`"
                v-model="formData.selectedTableIds"
                type="checkbox"
                :value="table.id"
                class="checkbox checkbox-sm"
                :disabled="loading"
              >
              <label
                :for="`table-${table.id}`"
                class="cursor-pointer text-sm flex-1 flex items-center justify-between"
              >
                <span>{{ table.name }}</span>
                <span class="badge badge-outline badge-xs">{{ table.dataSource }}</span>
              </label>
            </div>
          </div>

          <div
            v-else-if="formData.selectedTableIds.length > 0"
            class="flex flex-wrap gap-2"
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

          <div
            v-else
            class="text-sm text-base-content/60"
          >
            未选择表，系统将自动选择相关表
          </div>
        </div>

        <!-- Examples -->
        <div class="collapse collapse-arrow bg-base-200">
          <input type="checkbox">
          <div class="collapse-title text-sm font-medium">
            查询示例
          </div>
          <div class="collapse-content">
            <div class="space-y-2">
              <button
                v-for="example in queryExamples"
                :key="example"
                type="button"
                class="btn btn-ghost btn-sm text-left w-full justify-start h-auto py-2"
                @click="formData.query = example"
              >
                {{ example }}
              </button>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-3 pt-4">
          <button
            type="submit"
            class="btn btn-primary flex-1"
            :disabled="loading || !formData.query.trim()"
          >
            <span
              v-if="loading"
              class="loading loading-spinner loading-sm"
            />
            {{ loading ? '查询中...' : '开始查询' }}
          </button>

          <button
            v-if="hasActiveQuery"
            type="button"
            class="btn btn-error"
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

          <button
            type="button"
            class="btn btn-ghost"
            @click="handleReset"
          >
            重置
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQueryStore } from '@stores/query'
import { metadataService } from '@services/api'
import type { QueryRequest, DataTheme, TableMetadata } from '@types/index'

interface Props {
  initialQuery?: string
  initialFlowType?: 'fast' | 'thorough'
  initialThemeId?: number
  initialTableIds?: number[]
}

const props = withDefaults(defineProps<Props>(), {
  initialQuery: '',
  initialFlowType: 'fast',
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
  flowType: props.initialFlowType,
  selectedThemeId: props.initialThemeId || undefined,
  selectedTableIds: props.initialTableIds
})

// UI state
const showAllTables = ref(false)
const themes = ref<DataTheme[]>([])
const availableTables = ref<TableMetadata[]>([])
const themesLoading = ref(false)

// Computed
const loading = computed(() => queryStore.isLoading)
const hasActiveQuery = computed(() => queryStore.hasActiveQuery)

// Query examples
const queryExamples = [
  '显示最近一个月的销售额',
  '查询各个产品类别的销售占比',
  '找出销售额最高的前10个产品',
  '分析用户注册趋势',
  '统计各地区的订单数量',
  '查询库存不足的产品'
]

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

// Toggle table selection
const toggleTableSelection = () => {
  showAllTables.value = !showAllTables.value
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
    flowType: formData.value.flowType,
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
    flowType: 'fast',
    selectedThemeId: undefined,
    selectedTableIds: []
  }
  showAllTables.value = false
}

// Initialize
onMounted(() => {
  loadThemes()
  loadAvailableTables()
})
</script>
