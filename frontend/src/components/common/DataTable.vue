<template>
  <div class="w-full">
    <!-- Table Header -->
    <div
      v-if="showHeader"
      class="flex items-center justify-between mb-4"
    >
      <div class="flex items-center gap-2">
        <h3
          v-if="title"
          class="text-lg font-semibold"
        >
          {{ title }}
        </h3>
        <span
          v-if="subtitle"
          class="text-sm text-base-content/60"
        >{{ subtitle }}</span>
      </div>

      <div class="flex items-center gap-2">
        <!-- Search -->
        <div
          v-if="searchable"
          class="form-control"
        >
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="searchPlaceholder"
            class="input input-bordered input-sm w-64"
          >
        </div>

        <!-- Actions -->
        <slot name="actions" />

        <!-- Column Settings -->
        <div
          v-if="columnSettings"
          class="dropdown dropdown-end"
        >
          <label
            tabindex="0"
            class="btn btn-ghost btn-sm btn-circle"
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
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </label>
          <ul
            tabindex="0"
            class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-52"
          >
            <li
              v-for="col in columns"
              :key="col.key"
            >
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  v-model="col.visible"
                  type="checkbox"
                  class="checkbox checkbox-sm"
                >
                <span>{{ col.title }}</span>
              </label>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Table Container -->
    <div
      class="overflow-x-auto bg-base-100 rounded-lg shadow"
      :class="tableContainerClass"
    >
      <table
        class="table table-zebra w-full"
        :class="tableClass"
      >
        <!-- Table Head -->
        <thead>
          <tr>
            <th
              v-if="selectable"
              class="w-12"
            >
              <input
                type="checkbox"
                class="checkbox checkbox-sm"
                :checked="allSelected"
                :indeterminate="someSelected"
                @change="toggleSelectAll"
              >
            </th>

            <th
              v-for="column in visibleColumns"
              :key="column.key"
              :class="[
                'cursor-pointer hover:bg-base-200',
                column.sortable ? 'select-none' : '',
                column.className
              ]"
              @click="handleSort(column)"
            >
              <div class="flex items-center gap-1">
                <span>{{ column.title }}</span>
                <div
                  v-if="column.sortable"
                  class="flex flex-col"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-3 w-3"
                    :class="{
                      'text-primary': sortBy === column.key && sortOrder === 'asc',
                      'text-base-content/30': sortBy !== column.key || sortOrder !== 'asc'
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
                      'text-primary': sortBy === column.key && sortOrder === 'desc',
                      'text-base-content/30': sortBy !== column.key || sortOrder !== 'desc'
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

            <th
              v-if="$slots.actions"
              class="w-24"
            >
              操作
            </th>
          </tr>
        </thead>

        <!-- Table Body -->
        <tbody>
          <tr v-if="loading">
            <td
              :colspan="columnCount"
              class="text-center py-8"
            >
              <LoadingSpinner size="sm" />
            </td>
          </tr>

          <tr v-else-if="paginatedData.length === 0">
            <td
              :colspan="columnCount"
              class="text-center py-8"
            >
              <EmptyState
                :type="emptyStateType"
                :title="emptyTitle"
                :description="emptyDescription"
                size="sm"
              />
            </td>
          </tr>

          <tr
            v-for="(item, index) in paginatedData"
            :key="getRowKey(item, index)"
            :class="[
              'hover:bg-base-200',
              getRowClass(item, index),
              selectedRows.includes(getRowKey(item, index)) ? 'bg-primary/10' : ''
            ]"
          >
            <!-- Selection Column -->
            <td
              v-if="selectable"
              class="w-12"
            >
              <input
                type="checkbox"
                class="checkbox checkbox-sm"
                :checked="selectedRows.includes(getRowKey(item, index))"
                @change="toggleRowSelection(getRowKey(item, index))"
              >
            </td>

            <!-- Data Columns -->
            <td
              v-for="column in visibleColumns"
              :key="column.key"
              :class="column.className"
            >
              <slot
                :name="`cell-${column.key}`"
                :record="item"
                :value="getNestedValue(item, column.key)"
                :index="index"
              >
                <span v-if="column.render">
                  {{ column.render(getNestedValue(item, column.key), item) }}
                </span>
                <span v-else>
                  {{ getNestedValue(item, column.key) }}
                </span>
              </slot>
            </td>

            <!-- Actions Column -->
            <td
              v-if="$slots.actions"
              class="w-24"
            >
              <slot
                name="actions"
                :record="item"
                :index="index"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div
      v-if="paginated && total > pageSize"
      class="flex items-center justify-between mt-4"
    >
      <div class="text-sm text-base-content/60">
        显示 {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, total) }} 条，共 {{ total }} 条
      </div>

      <div class="join">
        <button
          class="join-item btn btn-sm"
          :disabled="currentPage === 1"
          @click="goToPage(currentPage - 1)"
        >
          上一页
        </button>
        <button
          v-for="page in visiblePages"
          :key="page"
          class="join-item btn btn-sm"
          :class="{ 'btn-active': page === currentPage }"
          @click="goToPage(page)"
        >
          {{ page }}
        </button>
        <button
          class="join-item btn btn-sm"
          :disabled="currentPage === totalPages"
          @click="goToPage(currentPage + 1)"
        >
          下一页
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import LoadingSpinner from './LoadingSpinner.vue'
import EmptyState from './EmptyState.vue'

interface Column {
  key: string
  title: string
  sortable?: boolean
  visible?: boolean
  className?: string
  render?: (value: any, record: any) => string
}

interface Props {
  data: any[]
  columns: Column[]
  loading?: boolean
  title?: string
  subtitle?: string
  searchable?: boolean
  searchPlaceholder?: string
  selectable?: boolean
  paginated?: boolean
  pageSize?: number
  emptyStateType?: 'no-data' | 'no-results' | 'error' | 'custom'
  emptyTitle?: string
  emptyDescription?: string
  rowKey?: string | ((record: any) => string)
  getRowClass?: (record: any, index: number) => string
  showHeader?: boolean
  columnSettings?: boolean
  tableClass?: string
  tableContainerClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  searchPlaceholder: '搜索...',
  selectable: false,
  paginated: false,
  pageSize: 20,
  emptyStateType: 'no-data',
  showHeader: true,
  columnSettings: false,
  rowKey: 'id'
})

// Reactive state
const searchQuery = ref('')
const sortBy = ref<string>('')
const sortOrder = ref<'asc' | 'desc'>('asc')
const currentPage = ref(1)
const selectedRows = ref<string[]>([])

// Ensure columns have visibility state
const columns = computed(() => {
  return props.columns.map(col => ({
    ...col,
    visible: col.visible !== false
  }))
})

// Visible columns
const visibleColumns = computed(() => {
  return columns.value.filter(col => col.visible)
})

// Column count
const columnCount = computed(() => {
  let count = visibleColumns.value.length
  if (props.selectable) count++
  if (props.$slots.actions) count++
  return count
})

// Filtered data
const filteredData = computed(() => {
  if (!searchQuery.value) return props.data

  return props.data.filter(item => {
    return visibleColumns.value.some(col => {
      const value = getNestedValue(item, col.key)
      return String(value).toLowerCase().includes(searchQuery.value.toLowerCase())
    })
  })
})

// Sorted data
const sortedData = computed(() => {
  if (!sortBy.value) return filteredData.value

  return [...filteredData.value].sort((a, b) => {
    const aValue = getNestedValue(a, sortBy.value)
    const bValue = getNestedValue(b, sortBy.value)

    if (aValue === bValue) return 0

    let comparison = 0
    if (aValue < bValue) comparison = -1
    if (aValue > bValue) comparison = 1

    return sortOrder.value === 'desc' ? -comparison : comparison
  })
})

// Total count
const total = computed(() => sortedData.value.length)

// Total pages
const totalPages = computed(() => {
  return Math.ceil(total.value / props.pageSize)
})

// Paginated data
const paginatedData = computed(() => {
  if (!props.paginated) return sortedData.value

  const start = (currentPage.value - 1) * props.pageSize
  const end = start + props.pageSize
  return sortedData.value.slice(start, end)
})

// Visible page numbers
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

// Selection state
const allSelected = computed(() => {
  return paginatedData.value.length > 0 &&
    paginatedData.value.every(item =>
      selectedRows.value.includes(getRowKey(item))
    )
})

const someSelected = computed(() => {
  return selectedRows.value.length > 0 && !allSelected.value
})

// Get nested value
const getNestedValue = (obj: any, path: string) => {
  return path.split('.').reduce((current, key) => current?.[key], obj)
}

// Get row key
const getRowKey = (record: any, index?: number) => {
  if (typeof props.rowKey === 'function') {
    return props.rowKey(record)
  }
  return record[props.rowKey] || index
}

// Get row class
const getRowClass = (record: any, index: number) => {
  if (props.getRowClass) {
    return props.getRowClass(record, index)
  }
  return ''
}

// Handle sort
const handleSort = (column: Column) => {
  if (!column.sortable) return

  if (sortBy.value === column.key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = column.key
    sortOrder.value = 'asc'
  }
}

// Toggle row selection
const toggleRowSelection = (key: string) => {
  const index = selectedRows.value.indexOf(key)
  if (index > -1) {
    selectedRows.value.splice(index, 1)
  } else {
    selectedRows.value.push(key)
  }
}

// Toggle select all
const toggleSelectAll = () => {
  if (allSelected.value) {
    selectedRows.value = []
  } else {
    selectedRows.value = paginatedData.value.map(item => getRowKey(item))
  }
}

// Go to page
const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
  }
}

// Watch for data changes
watch(() => props.data, () => {
  currentPage.value = 1
})

// Watch for search query changes
watch(searchQuery, () => {
  currentPage.value = 1
})

// Expose methods
defineExpose({
  selectedRows,
  clearSelection: () => { selectedRows.value = [] },
  refresh: () => { /* 可以添加刷新逻辑 */ }
})
</script>
