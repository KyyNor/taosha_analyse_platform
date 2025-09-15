<template>
  <div class="result-display">
    <!-- SQL查询展示 -->
    <el-card v-if="result.sql_query" class="sql-card">
      <template #header>
        <span>生成的SQL查询</span>
      </template>
      <el-input
        v-model="result.sql_query"
        type="textarea"
        :rows="6"
        readonly
        class="sql-textarea"
      />
    </el-card>

    <!-- 数据结果展示 -->
    <div v-if="result.data && result.data.length > 0" class="data-results">
      <el-row :gutter="24">
        <el-col :span="12">
          <!-- 数据表格 -->
          <el-card class="table-card">
            <template #header>
              <span>数据表格</span>
            </template>
            <DataTable :data="result.data" />
            
            <!-- 数据统计 -->
            <div class="data-stats">
              <h4>数据统计</h4>
              <p><strong>总行数:</strong> {{ result.data.length }}</p>
              <p><strong>列数:</strong> {{ getColumnCount(result.data) }}</p>
            </div>

            <!-- 关键指标（单行数据时） -->
            <div v-if="result.data.length === 1" class="metrics-section">
              <h4>关键指标</h4>
              <div class="metrics-grid">
                <div
                  v-for="[key, value] in Object.entries(result.data[0])"
                  :key="key"
                  class="metric-item"
                >
                  <div class="metric-label">{{ key }}</div>
                  <div class="metric-value">{{ value }}</div>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :span="12">
          <!-- 可视化图表 -->
          <el-card class="chart-card">
            <template #header>
              <span>可视化图表</span>
            </template>
            <DataChart v-if="shouldShowChart(result.data)" :data="result.data" />
            <div v-else class="no-chart-message">
              <el-empty description="数据不适合图表展示，或行数太少" />
              <!-- 数值列统计 -->
              <div v-if="getNumericStats(result.data)" class="numeric-stats">
                <h4>数值列统计</h4>
                <el-table :data="getNumericStats(result.data)" size="small">
                  <el-table-column prop="column" label="列名" />
                  <el-table-column prop="count" label="计数" />
                  <el-table-column prop="mean" label="平均值" />
                  <el-table-column prop="std" label="标准差" />
                  <el-table-column prop="min" label="最小值" />
                  <el-table-column prop="max" label="最大值" />
                </el-table>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 无数据提示 -->
    <el-card v-else-if="result.success && (!result.data || result.data.length === 0)">
      <el-empty description="查询成功，但没有返回数据" />
    </el-card>

    <!-- 查询日志 -->
    <QueryLogs v-if="result.logs && result.logs.length > 0" :logs="result.logs" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { QueryResult } from '@/types'
import DataTable from './DataTable.vue'
import DataChart from './DataChart.vue'
import QueryLogs from './QueryLogs.vue'

interface Props {
  result: QueryResult
}

const props = defineProps<Props>()

// 计算列数
const getColumnCount = (data: Record<string, any>[]) => {
  return data.length > 0 ? Object.keys(data[0]).length : 0
}

// 判断是否应该显示图表
const shouldShowChart = (data: Record<string, any>[]) => {
  if (!data || data.length <= 1) return false
  
  // 检查是否有数值列和分类列
  const firstRow = data[0]
  const keys = Object.keys(firstRow)
  
  let hasNumeric = false
  let hasCategorical = false
  
  keys.forEach(key => {
    const values = data.map(row => row[key])
    const numericValues = values.filter(v => typeof v === 'number' && !isNaN(v))
    
    if (numericValues.length > 0) {
      hasNumeric = true
    } else {
      hasCategorical = true
    }
  })
  
  return hasNumeric && (hasCategorical || keys.length >= 2)
}

// 获取数值列统计
const getNumericStats = (data: Record<string, any>[]) => {
  if (!data || data.length === 0) return null
  
  const firstRow = data[0]
  const keys = Object.keys(firstRow)
  const numericStats: any[] = []
  
  keys.forEach(key => {
    const values = data.map(row => row[key]).filter(v => typeof v === 'number' && !isNaN(v))
    
    if (values.length > 0) {
      const sum = values.reduce((a, b) => a + b, 0)
      const mean = sum / values.length
      const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length
      const std = Math.sqrt(variance)
      
      numericStats.push({
        column: key,
        count: values.length,
        mean: mean.toFixed(2),
        std: std.toFixed(2),
        min: Math.min(...values),
        max: Math.max(...values)
      })
    }
  })
  
  return numericStats.length > 0 ? numericStats : null
}
</script>

<style scoped lang="scss">
.result-display {
  .sql-card {
    margin-bottom: 24px;
    
    .sql-textarea {
      :deep(.el-textarea__inner) {
        font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
        font-size: 13px;
        line-height: 1.5;
        background: #f8f9fa;
      }
    }
  }
  
  .data-results {
    .table-card,
    .chart-card {
      height: fit-content;
      
      .data-stats {
        margin-top: 20px;
        padding-top: 20px;
        border-top: 1px solid #ebeef5;
        
        h4 {
          margin: 0 0 12px 0;
          font-size: 16px;
          color: #303133;
        }
        
        p {
          margin: 8px 0;
          color: #606266;
        }
      }
      
      .metrics-section {
        margin-top: 20px;
        padding-top: 20px;
        border-top: 1px solid #ebeef5;
        
        h4 {
          margin: 0 0 16px 0;
          font-size: 16px;
          color: #303133;
        }
        
        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
          
          .metric-item {
            padding: 16px;
            background: #f5f7fa;
            border-radius: 8px;
            text-align: center;
            
            .metric-label {
              font-size: 14px;
              color: #909399;
              margin-bottom: 8px;
            }
            
            .metric-value {
              font-size: 24px;
              font-weight: 600;
              color: #409eff;
            }
          }
        }
      }
      
      .no-chart-message {
        .numeric-stats {
          margin-top: 20px;
          
          h4 {
            margin: 0 0 12px 0;
            font-size: 16px;
            color: #303133;
          }
        }
      }
    }
  }
}
</style>