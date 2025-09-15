<template>
  <div class="data-table">
    <el-table
      :data="data"
      stripe
      style="width: 100%"
      max-height="400"
      :default-sort="{ prop: Object.keys(data[0] || {})[0], order: 'ascending' }"
    >
      <el-table-column
        v-for="column in columns"
        :key="column"
        :prop="column"
        :label="column"
        :sortable="true"
        show-overflow-tooltip
        :width="getColumnWidth(column)"
      >
        <template #default="{ row }">
          <span :class="getValueClass(row[column])">
            {{ formatValue(row[column]) }}
          </span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  data: Record<string, any>[]
}

const props = defineProps<Props>()

// 获取列名
const columns = computed(() => {
  if (!props.data || props.data.length === 0) return []
  return Object.keys(props.data[0])
})

// 格式化值
const formatValue = (value: any) => {
  if (value === null || value === undefined) {
    return '—'
  }
  
  if (typeof value === 'number') {
    // 格式化数字
    if (Number.isInteger(value)) {
      return value.toLocaleString()
    } else {
      return value.toLocaleString(undefined, { 
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
      })
    }
  }
  
  if (typeof value === 'boolean') {
    return value ? '是' : '否'
  }
  
  return String(value)
}

// 获取值的CSS类
const getValueClass = (value: any) => {
  if (value === null || value === undefined) {
    return 'null-value'
  }
  
  if (typeof value === 'number') {
    return 'numeric-value'
  }
  
  if (typeof value === 'boolean') {
    return 'boolean-value'
  }
  
  return 'text-value'
}

// 计算列宽
const getColumnWidth = (column: string) => {
  // 根据列名长度和内容类型动态计算宽度
  const baseWidth = Math.max(column.length * 8, 80)
  
  if (!props.data || props.data.length === 0) {
    return baseWidth
  }
  
  // 检查列值的最大长度
  const maxValueLength = Math.max(
    ...props.data.map(row => {
      const value = formatValue(row[column])
      return String(value).length
    })
  )
  
  return Math.min(Math.max(baseWidth, maxValueLength * 8), 200)
}
</script>

<style scoped lang="scss">
.data-table {
  :deep(.el-table) {
    .null-value {
      color: #c0c4cc;
      font-style: italic;
    }
    
    .numeric-value {
      color: #409eff;
      font-weight: 500;
    }
    
    .boolean-value {
      color: #67c23a;
      font-weight: 500;
    }
    
    .text-value {
      color: #303133;
    }
  }
}
</style>