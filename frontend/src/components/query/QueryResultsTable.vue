<template>
  <div class="space-y-4">
    <!-- Loading State -->
    <div
      v-if="loading"
      class="text-center py-8"
    >
      <LoadingSpinner text="正在执行查询..." />
    </div>

    <!-- Empty State -->
    <div
      v-else-if="!data || !data.rows || data.rows.length === 0"
      class="text-center py-8"
    >
      <EmptyState
        type="no-data"
        title="查询结果为空"
        description="查询执行成功，但没有返回任何数据。"
        size="sm"
      />
    </div>

    <!-- Results Table -->
    <div
      v-else
      class="space-y-4"
    >
      <!-- Results Summary -->
      <div class="flex items-center justify-between">
        <div class="text-sm text-base-content/60">
          查询结果：共 {{ data.rowCount }} 行数据
        </div>
        <div class="flex gap-2">
          <button
            class="btn btn-ghost btn-sm"
            @click="refreshData"
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
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            刷新
          </button>
          <div class="dropdown dropdown-end">
            <label
              tabindex="0"
              class="btn btn-ghost btn-sm"
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
                  d="M4 6h16M4 12h16m-7 6h7"
                />
              </svg>
              视图
            </label>
            <ul
              tabindex="0"
              class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-32"
            >
              <li><a @click="viewMode = 'table'">表格</a></li>
              <li><a @click="viewMode = 'chart'">图表</a></li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Table View -->
      <div
        v-if="viewMode === 'table'"
        class="overflow-x-auto"
        ref="tableContainer"
      >
        <!-- Fixed Header (only visible when table is scrolled) -->
        <div
          v-if="showFixedHeader"
          class="fixed-header-container"
          :style="fixedHeaderStyle"
        >
          <table class="table table-zebra w-full">
            <thead class="bg-base-100 shadow-md" style="background-color: hsl(var(--b1)); opacity: 1 !important;">
              <tr>
                <th
                  v-for="column in data.columns"
                  :key="column.name"
                  class="cursor-pointer hover:bg-base-200"
                  :style="{ width: getColumnWidth(column.name) + 'px' }"
                  @click="sortByColumn(column.name)"
                >
                  <div class="flex items-center gap-1">
                    <span>{{ column.name }}</span>
                    <div
                      v-if="sortColumn === column.name"
                      class="flex flex-col"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-3 w-3"
                        :class="{
                          'text-primary': sortOrder === 'asc'
                        }"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fill-rule="evenodd"
                          d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z"
                          clip-rule="evenodd"
                        />
                      </svg>
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-3 w-3 -mt-1"
                        :class="{
                          'text-primary': sortOrder === 'desc'
                        }"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fill-rule="evenodd"
                          d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                          clip-rule="evenodd"
                        />
                      </svg>
                    </div>
                  </div>
                </th>
              </tr>
            </thead>
          </table>
        </div>

        <!-- Original Table -->
        <table class="table table-zebra w-full" ref="originalTable">
          <thead ref="tableHeader">
            <tr>
              <th
                v-for="column in data.columns"
                :key="column.name"
                class="cursor-pointer hover:bg-base-200"
                @click="sortByColumn(column.name)"
              >
                <div class="flex items-center gap-1">
                  <span>{{ column.name }}</span>
                  <div
                    v-if="sortColumn === column.name"
                    class="flex flex-col"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-3 w-3"
                      :class="{
                        'text-primary': sortOrder === 'asc'
                      }"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z"
                        clip-rule="evenodd"
                      />
                    </svg>
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-3 w-3 -mt-1"
                      :class="{
                        'text-primary': sortOrder === 'desc'
                      }"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </div>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, index) in paginatedRows"
              :key="index"
              class="hover"
            >
              <td
                v-for="column in data.columns"
                :key="column.name"
                class="max-w-xs truncate"
                :title="formatCellValue(row[column.name], column.type)"
              >
                {{ formatCellValue(row[column.name], column.type) }}
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Pagination -->
        <div
          v-if="totalPages > 1"
          class="flex items-center justify-between mt-4"
        >
          <div class="text-sm text-base-content/60">
            显示 {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, sortedRows.length) }} 条，共 {{ sortedRows.length }} 条
          </div>

          <div class="join">
            <button
              class="join-item btn btn-sm"
              :disabled="currentPage === 1"
              @click="currentPage--"
            >
              上一页
            </button>
            <button
              v-for="page in visiblePages"
              :key="page"
              class="join-item btn btn-sm"
              :class="{ 'btn-active': page === currentPage }"
              @click="currentPage = page"
            >
              {{ page }}
            </button>
            <button
              class="join-item btn btn-sm"
              :disabled="currentPage === totalPages"
              @click="currentPage++"
            >
              下一页
            </button>
          </div>
        </div>
      </div>

      <!-- Chart View -->
      <div
        v-else-if="viewMode === 'chart'"
        class="space-y-4"
      >
        <div class="flex items-center gap-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">X轴</span>
            </label>
            <select
              v-model="chartConfig.xAxis"
              class="select select-bordered select-sm"
            >
              <option value="">
                选择字段
              </option>
              <option
                v-for="column in data.columns"
                :key="column.name"
                :value="column.name"
              >
                {{ column.name }}
              </option>
            </select>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">Y轴</span>
            </label>
            <select
              v-model="chartConfig.yAxis"
              class="select select-bordered select-sm"
            >
              <option value="">
                选择字段
              </option>
              <option
                v-for="column in numericColumns"
                :key="column.name"
                :value="column.name"
              >
                {{ column.name }}
              </option>
            </select>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">图表类型</span>
            </label>
            <select
              v-model="chartConfig.type"
              class="select select-bordered select-sm"
            >
              <option value="bar">
                柱状图
              </option>
              <option value="line">
                折线图
              </option>
              <option value="pie">
                饼图
              </option>
            </select>
          </div>
        </div>

        <div class="bg-base-200 rounded-lg p-4 min-h-96 flex items-center justify-center">
          <div
            v-if="!chartConfig.xAxis || !chartConfig.yAxis"
            class="text-center text-base-content/60"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-12 w-12 mx-auto mb-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <p>请选择 X轴 和 Y轴 字段来生成图表</p>
          </div>
          <div
            v-else
            class="w-full h-96"
          >
            <!-- 这里可以集成 Plotly.js 或其他图表库 -->
            <div class="flex items-center justify-center h-full text-base-content/60">
              图表功能开发中...
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, watchEffect, onMounted, onUnmounted, nextTick } from 'vue'
import { useToast } from '@/composables/useToast'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { QueryResult } from '@types/index'

interface Props {
  data: QueryResult['result'] | null
  generatedSql: string
  loading: boolean
}

const props = withDefaults(defineProps<Props>(), {
  data: null,
  generatedSql: '',
  loading: false
})

// Add debug logging
watchEffect(() => {
  console.log('[QueryResultsTable] Props changed:', {
    data: props.data,
    hasData: !!props.data,
    columns: props.data?.columns,
    rows: props.data?.rows,
    rowCount: props.data?.rowCount,
    generatedSql: props.generatedSql,
    loading: props.loading,
    sampleRow: props.data?.rows?.[0],
    rowType: Array.isArray(props.data?.rows?.[0]) ? 'array' : typeof props.data?.rows?.[0]
  })
})

const { success, error } = useToast()

// State
const viewMode = ref<'table' | 'chart'>('table')
const sortColumn = ref<string>('')
const sortOrder = ref<'asc' | 'desc'>('asc')
const currentPage = ref(1)
const pageSize = ref(50)

// Fixed header state
const showFixedHeader = ref(false)
const fixedHeaderStyle = ref({})
const tableContainer = ref<HTMLElement>()
const originalTable = ref<HTMLElement>()
const tableHeader = ref<HTMLElement>()
const columnWidths = ref<Record<string, number>>({})

// Intersection Observer for detecting when table header is out of view
let observer: IntersectionObserver | null = null

const chartConfig = ref({
  type: 'bar',
  xAxis: '',
  yAxis: ''
})

// Computed properties
const numericColumns = computed(() => {
  if (!props.data?.columns) return []
  return props.data.columns.filter(col =>
    col.type?.toLowerCase().includes('int') ||
    col.type?.toLowerCase().includes('float') ||
    col.type?.toLowerCase().includes('decimal') ||
    col.type?.toLowerCase().includes('number')
  )
})

const sortedRows = computed(() => {
  if (!props.data?.rows || !sortColumn.value) return props.data.rows || []

  return [...props.data.rows].sort((a, b) => {
    const aValue = a[sortColumn.value]
    const bValue = b[sortColumn.value]

    if (aValue === bValue) return 0

    let comparison = 0
    if (aValue < bValue) comparison = -1
    if (aValue > bValue) comparison = 1

    return sortOrder.value === 'desc' ? -comparison : comparison
  })
})

const totalPages = computed(() => {
  return Math.ceil(sortedRows.value.length / pageSize.value)
})

const paginatedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return sortedRows.value.slice(start, end)
})

const visiblePages = computed(() => {
  const pages = []
  const maxVisible = 5

  if (totalPages.value <= maxVisible) {
    for (let i = 1; i <= totalPages.value; i++) {
      pages.push(i)
    }
  } else {
    const start = Math.max(1, currentPage.value - 2)
    const end = Math.min(totalPages.value, start + maxVisible - 1)

    for (let i = start; i <= end; i++) {
      pages.push(i)
    }
  }

  return pages
})


const formatCellValue = (value: any, columnType?: string) => {
  if (value === null || value === undefined) return '-'

  // Format based on column type
  if (columnType) {
    const type = columnType.toLowerCase()
    if (type.includes('date') || type.includes('time')) {
      try {
        return new Date(value).toLocaleString()
      } catch {
        return value
      }
    }
    if (type.includes('decimal') || type.includes('float') || type.includes('double')) {
      return Number(value).toLocaleString()
    }
  }

  return String(value)
}

const sortByColumn = (columnName: string) => {
  if (sortColumn.value === columnName) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = columnName
    sortOrder.value = 'asc'
  }
  currentPage.value = 1
}

const copySQL = async () => {
  try {
    await navigator.clipboard.writeText(props.generatedSql)
    success('SQL 已复制到剪贴板')
  } catch (err) {
    error('复制失败')
  }
}

const explainSQL = () => {
  // 这里可以实现 SQL 解释功能
  info('SQL 解释功能开发中...')
}

const refreshData = () => {
  // 这里可以实现数据刷新功能
  info('刷新功能开发中...')
}

// Fixed header methods
const getColumnWidth = (columnName: string): number => {
  return columnWidths.value[columnName] || 150 // Default width
}

const updateColumnWidths = () => {
  if (!tableHeader.value) return

  const headers = tableHeader.value.querySelectorAll('th')
  const widths: Record<string, number> = {}

  headers.forEach((header, index) => {
    const column = props.data?.columns?.[index]
    if (column) {
      widths[column.name] = header.offsetWidth
    }
  })

  columnWidths.value = widths
}

const updateFixedHeaderPosition = () => {
  if (!tableHeader.value || !tableContainer.value) return

  const containerRect = tableContainer.value.getBoundingClientRect()
  const headerRect = tableHeader.value.getBoundingClientRect()

  fixedHeaderStyle.value = {
    position: 'fixed',
    top: '0px',
    left: `${containerRect.left}px`,
    width: `${containerRect.width}px`,
    zIndex: 40,
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    backgroundColor: 'hsl(var(--b1))'
  }
}

const initializeFixedHeader = () => {
  if (!tableHeader.value || viewMode.value !== 'table') return

  // Set up Intersection Observer
  observer = new IntersectionObserver(
    (entries) => {
      const [entry] = entries
      showFixedHeader.value = !entry.isIntersecting

      if (showFixedHeader.value) {
        updateColumnWidths()
        updateFixedHeaderPosition()
      }
    },
    {
      root: null,
      rootMargin: '-1px 0px 0px 0px',
      threshold: 0
    }
  )

  observer.observe(tableHeader.value)

  // Update positions on scroll and resize
  window.addEventListener('scroll', updateFixedHeaderPosition)
  window.addEventListener('resize', () => {
    updateColumnWidths()
    updateFixedHeaderPosition()
  })
}

const cleanupFixedHeader = () => {
  if (observer) {
    observer.disconnect()
    observer = null
  }

  window.removeEventListener('scroll', updateFixedHeaderPosition)
  window.removeEventListener('resize', updateFixedHeaderPosition)

  showFixedHeader.value = false
}

// Watch for data changes
watch(() => props.data, async () => {
  currentPage.value = 1
  sortColumn.value = ''
  sortOrder.value = 'asc'

  // Reinitialize fixed header when data changes
  await nextTick()
  if (viewMode.value === 'table') {
    cleanupFixedHeader()
    initializeFixedHeader()
  }
})

// Watch for view mode changes
watch(viewMode, (newMode) => {
  if (newMode === 'table') {
    nextTick(() => {
      initializeFixedHeader()
    })
  } else {
    cleanupFixedHeader()
  }
})

// Lifecycle hooks
onMounted(() => {
  nextTick(() => {
    if (viewMode.value === 'table') {
      initializeFixedHeader()
    }
  })
})

onUnmounted(() => {
  cleanupFixedHeader()
})
</script>

<style scoped>
.mockup-code {
  background-color: hsl(var(--b2));
  border-radius: 0.5rem;
  padding: 1rem;
  overflow-x: auto;
}

.mockup-code pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.25;
  color: hsl(var(--bc));
}

/* Fixed header styles */
.fixed-header-container {
  transition: opacity 0.2s ease-in-out;
  opacity: 1 !important;
}

.fixed-header-container table {
  border-collapse: separate;
  border-spacing: 0;
}

.fixed-header-container thead {
  background-color: hsl(var(--b1));
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  border-bottom: 2px solid hsl(var(--b2));
  color: hsl(var(--bc));
  opacity: 1 !important;
}

.fixed-header-container th {
  background-color: hsl(var(--b1));
  position: relative;
  color: hsl(var(--bc));
  font-weight: 600;
  opacity: 1 !important;
}

.fixed-header-container th span {
  color: hsl(var(--bc)) !important;
}

/* Add a subtle border to distinguish fixed header */
.fixed-header-container::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg,
    transparent 0%,
    hsl(var(--bc) / 0.1) 50%,
    transparent 100%
  );
}

/* Ensure smooth transitions when switching between table and chart views */
.overflow-x-auto {
  position: relative;
}

/* Hide original header when fixed header is visible */
.overflow-x-auto:has(.fixed-header-container) thead {
  opacity: 0;
  height: 0;
  overflow: hidden;
}

/* Fallback for browsers that don't support :has() */
@media (hover: hover) {
  .overflow-x-auto thead {
    transition: opacity 0.2s ease-in-out;
  }
}
</style>
