<template>
  <div class="space-y-4">
    <!-- 结果头部信息 -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <h3 class="font-semibold text-lg">查询结果</h3>
        <div class="flex items-center space-x-2 text-sm text-base-content text-opacity-60">
          <span>{{ result.total_count || result.rows.length }} 行</span>
          <span>•</span>
          <span>{{ result.columns.length }} 列</span>
          <span v-if="result.execution_time_ms">•</span>
          <span v-if="result.execution_time_ms">{{ result.execution_time_ms }}ms</span>
        </div>
      </div>
      
      <div class="flex items-center space-x-2">
        <!-- 视图切换 -->
        <div class="btn-group">
          <button 
            @click="viewMode = 'table'" 
            class="btn btn-sm"
            :class="{ 'btn-active': viewMode === 'table' }"
          >
            表格
          </button>
          <button 
            @click="viewMode = 'chart'" 
            class="btn btn-sm"
            :class="{ 'btn-active': viewMode === 'chart' }"
            :disabled="!canShowChart"
          >
            图表
          </button>
        </div>
        
        <!-- 导出按钮 -->
        <div class="dropdown dropdown-end">
          <label tabindex="0" class="btn btn-ghost btn-sm">
            导出
            <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </label>
          <ul tabindex="0" class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-32">
            <li><a @click="exportData('csv')">CSV</a></li>
            <li><a @click="exportData('excel')">Excel</a></li>
            <li><a @click="exportData('json')">JSON</a></li>
          </ul>
        </div>
      </div>
    </div>
    
    <!-- 表格视图 -->
    <div v-if="viewMode === 'table'" class="space-y-4">
      <!-- 搜索和筛选 -->
      <div class="flex items-center space-x-4">
        <div class="flex-1">
          <input 
            v-model="searchText"
            type="text" 
            placeholder="搜索结果..." 
            class="input input-bordered input-sm w-full max-w-md"
          />
        </div>
        
        <div class="flex items-center space-x-2">
          <span class="text-sm">每页显示:</span>
          <select v-model="pageSize" class="select select-bordered select-sm">
            <option :value="10">10</option>
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </div>
      </div>
      
      <!-- 数据表格 -->
      <div class="overflow-x-auto border rounded-lg">
        <table class="table table-zebra table-compact w-full">
          <thead class="bg-base-200">
            <tr>
              <th 
                v-for="(column, index) in result.columns" 
                :key="column"
                class="text-xs font-semibold cursor-pointer hover:bg-base-300"
                @click="sortBy(column)"
              >
                <div class="flex items-center justify-between">
                  <span>{{ column }}</span>
                  <svg 
                    v-if="sortColumn === column" 
                    class="w-3 h-3"
                    :class="sortDirection === 'asc' ? 'transform rotate-180' : ''"
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in paginatedRows" :key="rowIndex">
              <td 
                v-for="(value, colIndex) in row" 
                :key="colIndex" 
                class="text-xs"
                :title="String(value)"
              >
                <div class="max-w-32 truncate">
                  {{ formatCellValue(value) }}
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <!-- 分页控制 -->
      <div v-if="totalPages > 1" class="flex items-center justify-between">
        <div class="text-sm text-base-content text-opacity-60">
          显示 {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, filteredRows.length) }} 
          共 {{ filteredRows.length }} 条记录
        </div>
        
        <div class="btn-group">
          <button 
            @click="currentPage = 1"
            class="btn btn-sm"
            :disabled="currentPage === 1"
          >
            首页
          </button>
          <button 
            @click="currentPage--"
            class="btn btn-sm"
            :disabled="currentPage === 1"
          >
            上一页
          </button>
          
          <button 
            v-for="page in visiblePages"
            :key="page"
            @click="currentPage = page"
            class="btn btn-sm"
            :class="{ 'btn-active': currentPage === page }"
          >
            {{ page }}
          </button>
          
          <button 
            @click="currentPage++"
            class="btn btn-sm"
            :disabled="currentPage === totalPages"
          >
            下一页
          </button>
          <button 
            @click="currentPage = totalPages"
            class="btn btn-sm"
            :disabled="currentPage === totalPages"
          >
            尾页
          </button>
        </div>
      </div>
    </div>
    
    <!-- 图表视图 -->
    <div v-else-if="viewMode === 'chart'" class="space-y-4">
      <div class="text-center py-16 text-base-content text-opacity-50">
        <svg class="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p>图表功能开发中...</p>
        <p class="text-sm mt-2">将根据数据类型自动生成合适的图表</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface QueryResult {
  columns: string[]
  rows: any[][]
  total_count?: number
  execution_time_ms?: number
}

interface Props {
  result: QueryResult
}

const props = defineProps<Props>()

defineEmits<{
  export: [format: string, data: any]
}>()

// 响应式数据
const viewMode = ref<'table' | 'chart'>('table')
const searchText = ref('')
const sortColumn = ref<string | null>(null)
const sortDirection = ref<'asc' | 'desc'>('asc')
const currentPage = ref(1)
const pageSize = ref(25)

// 计算属性
const canShowChart = computed(() => {
  // 简单判断是否可以显示图表（包含数字列）
  return props.result.rows.some(row => 
    row.some(cell => typeof cell === 'number')
  )
})

const filteredRows = computed(() => {
  let rows = [...props.result.rows]
  
  // 搜索过滤
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    rows = rows.filter(row =>
      row.some(cell => 
        String(cell).toLowerCase().includes(search)
      )
    )
  }
  
  // 排序
  if (sortColumn.value) {
    const columnIndex = props.result.columns.indexOf(sortColumn.value)
    if (columnIndex !== -1) {
      rows.sort((a, b) => {
        const aVal = a[columnIndex]
        const bVal = b[columnIndex]
        
        // 处理数字比较
        if (typeof aVal === 'number' && typeof bVal === 'number') {
          return sortDirection.value === 'asc' ? aVal - bVal : bVal - aVal
        }
        
        // 字符串比较
        const aStr = String(aVal).toLowerCase()
        const bStr = String(bVal).toLowerCase()
        
        if (sortDirection.value === 'asc') {
          return aStr.localeCompare(bStr)
        } else {
          return bStr.localeCompare(aStr)
        }
      })
    }
  }
  
  return rows
})

const totalPages = computed(() => 
  Math.ceil(filteredRows.value.length / pageSize.value)
)

const paginatedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredRows.value.slice(start, end)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const pages = []
  
  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    if (current <= 4) {
      for (let i = 1; i <= 5; i++) pages.push(i)
      pages.push('...', total)
    } else if (current >= total - 3) {
      pages.push(1, '...')
      for (let i = total - 4; i <= total; i++) pages.push(i)
    } else {
      pages.push(1, '...')
      for (let i = current - 1; i <= current + 1; i++) pages.push(i)
      pages.push('...', total)
    }
  }
  
  return pages.filter(p => p !== '...' || pages.indexOf(p) === pages.lastIndexOf(p))
})

// 方法
const sortBy = (column: string) => {
  if (sortColumn.value === column) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = column
    sortDirection.value = 'asc'
  }
  currentPage.value = 1
}

const formatCellValue = (value: any) => {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value.toString() : value.toFixed(2)
  }
  return String(value)
}

const exportData = (format: string) => {
  const exportData = {
    format,
    columns: props.result.columns,
    rows: filteredRows.value,
    metadata: {
      total_count: props.result.total_count,
      execution_time_ms: props.result.execution_time_ms,
      exported_at: new Date().toISOString()
    }
  }
  
  // 触发导出事件
  // 实际导出逻辑在父组件中实现
  console.log('Export data:', exportData)
}
</script>