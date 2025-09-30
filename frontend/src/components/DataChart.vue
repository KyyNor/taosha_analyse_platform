<template>
  <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
    <!-- Chart Header -->
    <div v-if="title" class="mb-4">
      <h3 class="text-lg font-semibold text-slate-800">{{ title }}</h3>
      <p v-if="description" class="text-sm text-slate-500 mt-1">{{ description }}</p>
    </div>

    <!-- Chart Container -->
    <div 
      ref="chartContainer" 
      class="w-full"
      :style="{ height: `${height}px` }"
    >
      <div v-if="loading" class="flex items-center justify-center h-full">
        <div class="text-slate-500">图表加载中...</div>
      </div>
      <div v-else-if="error" class="flex items-center justify-center h-full">
        <div class="text-red-500">{{ error }}</div>
      </div>
      <div v-else-if="!hasData" class="flex items-center justify-center h-full">
        <div class="text-slate-500">暂无图表数据</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import * as Plotly from 'plotly.js-dist'

// 定义组件属性
interface Props {
  title?: string
  description?: string
  data: any[]
  chartType?: 'auto' | 'bar' | 'line' | 'scatter' | 'pie'
  height?: number
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  chartType: 'auto',
  height: 400,
  loading: false
})

// 响应式数据
const chartContainer = ref<HTMLElement>()
const error = ref<string>('')

// 计算属性
const hasData = computed(() => props.data && props.data.length > 0)

// 创建图表
const createChart = async () => {
  if (!chartContainer.value || !hasData.value || props.loading) {
    return
  }

  try {
    error.value = ''
    
    // 清除现有图表
    Plotly.purge(chartContainer.value)

    const df = props.data
    
    // 如果只有一行数据，不显示图表
    if (df.length === 1) {
      error.value = '数据行数太少，无法生成图表'
      return
    }

    // 自动判断图表类型和数据
    const numericCols = getNumericColumns(df)
    const categoricalCols = getCategoricalColumns(df)

    let plotData: any[] = []
    let layout: any = {
      autosize: true,
      margin: { l: 50, r: 50, t: 30, b: 50 },
      plot_bgcolor: 'white',
      paper_bgcolor: 'white',
      font: {
        family: 'Inter, system-ui, sans-serif',
        size: 12,
        color: '#1e293b'
      }
    }

    // 根据数据类型自动选择图表
    if (props.chartType === 'auto') {
      if (numericCols.length >= 1 && categoricalCols.length >= 1) {
        // 柱状图
        const xCol = categoricalCols[0]
        const yCol = numericCols[0]
        
        plotData = [{
          x: df.map(row => row[xCol]),
          y: df.map(row => row[yCol]),
          type: 'bar',
          marker: {
            color: '#3b82f6'
          }
        }]
        
        layout.xaxis = { title: xCol }
        layout.yaxis = { title: yCol }
        layout.title = `${yCol} 按 ${xCol} 分布`
        
      } else if (numericCols.length >= 2) {
        // 散点图
        plotData = [{
          x: df.map(row => row[numericCols[0]]),
          y: df.map(row => row[numericCols[1]]),
          mode: 'markers',
          type: 'scatter',
          marker: {
            color: '#3b82f6',
            size: 8
          }
        }]
        
        layout.xaxis = { title: numericCols[0] }
        layout.yaxis = { title: numericCols[1] }
        layout.title = `${numericCols[1]} vs ${numericCols[0]}`
      } else {
        error.value = '数据结构不适合生成图表'
        return
      }
    }

    // 配置响应式
    const config = {
      responsive: true,
      displayModeBar: false,
      displaylogo: false
    }

    await Plotly.newPlot(chartContainer.value, plotData, layout, config)
    
  } catch (err: any) {
    console.error('创建图表失败:', err)
    error.value = `图表创建失败: ${err.message}`
  }
}

// 获取数值列
const getNumericColumns = (data: any[]) => {
  if (!data.length) return []
  
  const firstRow = data[0]
  return Object.keys(firstRow).filter(key => {
    const value = firstRow[key]
    return typeof value === 'number' && !isNaN(value)
  })
}

// 获取分类列
const getCategoricalColumns = (data: any[]) => {
  if (!data.length) return []
  
  const firstRow = data[0]
  return Object.keys(firstRow).filter(key => {
    const value = firstRow[key]
    return typeof value === 'string' || typeof value === 'boolean'
  })
}

// 监听数据变化
watch(() => [props.data, props.chartType, props.loading], () => {
  nextTick(() => {
    createChart()
  })
}, { deep: true })

// 生命周期
onMounted(() => {
  nextTick(() => {
    createChart()
  })
})

onUnmounted(() => {
  if (chartContainer.value) {
    Plotly.purge(chartContainer.value)
  }
})

// 暴露重新绘制方法
defineExpose({
  refresh: createChart
})
</script>

<style scoped>
/* Plotly 图表容器样式 */
:deep(.js-plotly-plot) {
  border-radius: 0.5rem;
}
</style>