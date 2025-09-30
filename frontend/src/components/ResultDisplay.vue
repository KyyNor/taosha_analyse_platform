<template>
  <div class="space-y-6">
    <!-- Query Result Header -->
    <div class="bg-green-50 border border-green-200 rounded-lg p-4">
      <div class="flex items-center space-x-2">
        <CheckCircleIcon class="w-5 h-5 text-green-600" />
        <span class="font-medium text-green-800">查询成功！</span>
        <span class="text-sm text-green-600">耗时: {{ executionTime }}秒</span>
      </div>
    </div>

    <!-- Generated SQL -->
    <div v-if="sqlQuery" class="bg-white rounded-lg border border-slate-200 shadow-sm">
      <div class="px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h3 class="text-lg font-semibold text-slate-800">生成的SQL查询</h3>
      </div>
      <div class="p-6">
        <div class="bg-slate-900 rounded-lg p-4 overflow-x-auto">
          <pre class="text-sm text-green-400 font-mono whitespace-pre-wrap">{{ sqlQuery }}</pre>
        </div>
        <button
          @click="copySql"
          class="mt-3 px-3 py-1 text-xs bg-slate-100 text-slate-600 rounded hover:bg-slate-200 transition-colors duration-200"
        >
          {{ copyButtonText }}
        </button>
      </div>
    </div>

    <!-- Data Results -->
    <div v-if="data && data.length > 0" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Data Table -->
      <div class="lg:col-span-1">
        <DataTable
          title="数据表格"
          :columns="tableColumns"
          :data="data"
          :show-footer="true"
          :total="data.length"
        />
        
        <!-- Data Statistics -->
        <div class="mt-4 bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h4 class="text-lg font-semibold text-slate-800 mb-3">数据统计</h4>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <div class="text-2xl font-bold text-blue-600">{{ data.length }}</div>
              <div class="text-sm text-slate-500">总行数</div>
            </div>
            <div>
              <div class="text-2xl font-bold text-blue-600">{{ tableColumns.length }}</div>
              <div class="text-sm text-slate-500">列数</div>
            </div>
          </div>
        </div>

        <!-- Key Metrics for Single Row -->
        <div v-if="data.length === 1" class="mt-4 bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <div class="flex items-center space-x-2 mb-4">
            <FlagIcon class="w-5 h-5 text-blue-600" aria-label="关键指标图标" />
            <h4 class="text-lg font-semibold text-slate-800">关键指标</h4>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div 
              v-for="[key, value] in Object.entries(data[0])"
              :key="key"
              class="bg-slate-50 rounded-lg p-4"
            >
              <div class="text-lg font-semibold text-slate-800">{{ formatMetricValue(value) }}</div>
              <div class="text-sm text-slate-500">{{ key }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Data Visualization -->
      <div class="lg:col-span-1">
        <DataChart
          title="可视化图表"
          :data="data"
          :height="400"
        />

        <!-- Numeric Statistics -->
        <div v-if="numericStats.length > 0" class="mt-4 bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h4 class="text-lg font-semibold text-slate-800 mb-4">数值列统计</h4>
          <DataTable
            :columns="statsColumns"
            :data="numericStats"
            :show-footer="false"
          />
        </div>
      </div>
    </div>

    <!-- No Data Message -->
    <div v-else-if="data && data.length === 0" class="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
      <div class="flex flex-col items-center space-y-2">
        <InformationCircleIcon class="w-8 h-8 text-blue-600" />
        <div class="text-blue-800 font-medium">查询成功，但没有返回数据</div>
        <div class="text-blue-600 text-sm">请检查查询条件是否正确</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { CheckCircleIcon, InformationCircleIcon, FlagIcon } from '@heroicons/vue/24/outline'
import type { Column } from '@/types'
import DataTable from './DataTable.vue'
import DataChart from './DataChart.vue'

// 定义组件属性
interface Props {
  sqlQuery?: string
  data?: any[]
  executionTime: number
}

const props = defineProps<Props>()

// 响应式数据
const copyButtonText = ref('复制SQL')

// 计算表格列
const tableColumns = computed((): Column[] => {
  if (!props.data || props.data.length === 0) return []
  
  const firstRow = props.data[0]
  return Object.keys(firstRow).map(key => ({
    key,
    title: key,
    type: getColumnType(firstRow[key])
  }))
})

// 计算数值统计
const numericStats = computed(() => {
  if (!props.data || props.data.length === 0) return []
  
  const numericColumns = tableColumns.value.filter(col => col.type === 'number')
  if (numericColumns.length === 0) return []

  return numericColumns.map(col => {
    const values = props.data!.map(row => row[col.key]).filter(val => typeof val === 'number')
    
    if (values.length === 0) return { column: col.title, count: 0, mean: 0, min: 0, max: 0 }
    
    const sum = values.reduce((a, b) => a + b, 0)
    const mean = sum / values.length
    const min = Math.min(...values)
    const max = Math.max(...values)
    
    return {
      column: col.title,
      count: values.length,
      mean: Number(mean.toFixed(2)),
      min,
      max
    }
  })
})

// 统计表格列定义
const statsColumns: Column[] = [
  { key: 'column', title: '列名', type: 'text' },
  { key: 'count', title: '数量', type: 'number' },
  { key: 'mean', title: '平均值', type: 'number' },
  { key: 'min', title: '最小值', type: 'number' },
  { key: 'max', title: '最大值', type: 'number' }
]

// 获取列类型
const getColumnType = (value: any): Column['type'] => {
  if (typeof value === 'number') return 'number'
  if (typeof value === 'boolean') return 'boolean'
  if (value instanceof Date) return 'date'
  return 'text'
}

// 格式化指标值
const formatMetricValue = (value: any) => {
  if (typeof value === 'number') {
    return value.toLocaleString()
  }
  return value
}

// 复制SQL
const copySql = async () => {
  if (!props.sqlQuery) return
  
  try {
    await navigator.clipboard.writeText(props.sqlQuery)
    copyButtonText.value = '已复制!'
    setTimeout(() => {
      copyButtonText.value = '复制SQL'
    }, 2000)
  } catch (err) {
    console.error('复制失败:', err)
    copyButtonText.value = '复制失败'
    setTimeout(() => {
      copyButtonText.value = '复制SQL'
    }, 2000)
  }
}
</script>