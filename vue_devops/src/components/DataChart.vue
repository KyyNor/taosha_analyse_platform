<template>
  <div class="data-chart">
    <v-chart
      v-if="chartOption"
      :option="chartOption"
      :style="{ height: '400px', width: '100%' }"
      autoresize
    />
    <el-empty v-else description="无法生成图表" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import {
  BarChart,
  LineChart,
  PieChart,
  ScatterChart
} from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DatasetComponent
} from 'echarts/components'

// 注册必要的组件
use([
  CanvasRenderer,
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DatasetComponent
])

interface Props {
  data: Record<string, any>[]
}

const props = defineProps<Props>()

// 分析数据特征
const analyzeData = (data: Record<string, any>[]) => {
  if (!data || data.length === 0) return null
  
  const firstRow = data[0]
  const keys = Object.keys(firstRow)
  
  const numericColumns: string[] = []
  const categoricalColumns: string[] = []
  
  keys.forEach(key => {
    const values = data.map(row => row[key])
    const numericValues = values.filter(v => typeof v === 'number' && !isNaN(v))
    
    if (numericValues.length > values.length * 0.8) { // 80%以上是数值
      numericColumns.push(key)
    } else {
      categoricalColumns.push(key)
    }
  })
  
  return {
    numericColumns,
    categoricalColumns,
    totalColumns: keys.length,
    totalRows: data.length
  }
}

// 生成图表配置
const chartOption = computed(() => {
  const analysis = analyzeData(props.data)
  if (!analysis) return null
  
  const { numericColumns, categoricalColumns, totalRows } = analysis
  
  // 如果只有一行数据，不显示图表
  if (totalRows <= 1) return null
  
  // 柱状图：有分类列和数值列
  if (categoricalColumns.length >= 1 && numericColumns.length >= 1) {
    return createBarChart(props.data, categoricalColumns[0], numericColumns[0])
  }
  
  // 散点图：有两个或更多数值列
  if (numericColumns.length >= 2) {
    return createScatterChart(props.data, numericColumns[0], numericColumns[1])
  }
  
  // 饼图：一个分类列，数据量不太大
  if (categoricalColumns.length >= 1 && totalRows <= 20) {
    return createPieChart(props.data, categoricalColumns[0])
  }
  
  return null
})

// 创建柱状图
const createBarChart = (data: Record<string, any>[], xColumn: string, yColumn: string) => {
  const xData = data.map(row => row[xColumn])
  const yData = data.map(row => row[yColumn])
  
  return {
    title: {
      text: `${yColumn} 按 ${xColumn} 分布`,
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'normal'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: {
        rotate: xData.some(item => String(item).length > 6) ? 45 : 0
      }
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: yColumn,
        type: 'bar',
        data: yData,
        itemStyle: {
          color: '#409eff',
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  }
}

// 创建散点图
const createScatterChart = (data: Record<string, any>[], xColumn: string, yColumn: string) => {
  const seriesData = data.map(row => [row[xColumn], row[yColumn]])
  
  return {
    title: {
      text: `${yColumn} vs ${xColumn}`,
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'normal'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        return `${xColumn}: ${params.data[0]}<br/>${yColumn}: ${params.data[1]}`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: xColumn,
      nameLocation: 'middle',
      nameGap: 30
    },
    yAxis: {
      type: 'value',
      name: yColumn,
      nameLocation: 'middle',
      nameGap: 50
    },
    series: [
      {
        type: 'scatter',
        data: seriesData,
        itemStyle: {
          color: '#409eff'
        },
        symbolSize: 8
      }
    ]
  }
}

// 创建饼图
const createPieChart = (data: Record<string, any>[], column: string) => {
  // 统计各分类的数量
  const categoryCount = data.reduce((acc, row) => {
    const category = String(row[column])
    acc[category] = (acc[category] || 0) + 1
    return acc
  }, {} as Record<string, number>)
  
  const pieData = Object.entries(categoryCount).map(([name, value]) => ({
    name,
    value
  }))
  
  return {
    title: {
      text: `${column} 分布`,
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'normal'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'middle'
    },
    series: [
      {
        name: column,
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: pieData,
        itemStyle: {
          borderRadius: 4,
          borderWidth: 2,
          borderColor: '#fff'
        }
      }
    ]
  }
}
</script>

<style scoped lang="scss">
.data-chart {
  width: 100%;
}
</style>