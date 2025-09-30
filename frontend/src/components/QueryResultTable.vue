<template>
  <div class="overflow-x-auto">
    <table class="min-w-full divide-y divide-gray-200">
      <thead class="bg-gray-50">
        <tr>
          <th
            v-for="column in columns"
            :key="column"
            class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
          >
            {{ column }}
          </th>
        </tr>
      </thead>
      <tbody class="bg-white divide-y divide-gray-200">
        <tr v-for="(row, index) in data" :key="index" class="hover:bg-gray-50">
          <td
            v-for="column in columns"
            :key="column"
            class="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
          >
            {{ formatValue(row[column]) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  data: Record<string, any>[]
}

const props = defineProps<Props>()

// 计算表格列名
const columns = computed(() => {
  if (props.data.length === 0) return []
  return Object.keys(props.data[0])
})

// 格式化值
const formatValue = (value: any): string => {
  if (value === null || value === undefined) {
    return '-'
  }

  if (typeof value === 'number') {
    // 格式化数字
    if (Number.isInteger(value)) {
      return value.toLocaleString()
    } else {
      return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
    }
  }

  if (typeof value === 'boolean') {
    return value ? '是' : '否'
  }

  if (value instanceof Date) {
    return value.toLocaleDateString() + ' ' + value.toLocaleTimeString()
  }

  // 字符串类型
  return String(value)
}
</script>