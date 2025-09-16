<template>
  <div class="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
    <!-- Table Header -->
    <div v-if="title" class="px-6 py-4 border-b border-slate-200 bg-slate-50">
      <h3 class="text-lg font-semibold text-slate-800">{{ title }}</h3>
      <p v-if="description" class="text-sm text-slate-500 mt-1">{{ description }}</p>
    </div>

    <!-- Table Content -->
    <div class="overflow-x-auto">
      <table class="w-full">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th
              v-for="column in columns"
              :key="column.key"
              class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider"
            >
              {{ column.title }}
            </th>
            <th v-if="hasActions" class="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">
              操作
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-slate-200">
          <tr v-if="loading" class="animate-pulse">
            <td :colspan="columns.length + (hasActions ? 1 : 0)" class="px-6 py-4 text-center text-slate-500">
              加载中...
            </td>
          </tr>
          <tr v-else-if="data.length === 0">
            <td :colspan="columns.length + (hasActions ? 1 : 0)" class="px-6 py-4 text-center text-slate-500">
              {{ emptyText }}
            </td>
          </tr>
          <tr 
            v-else
            v-for="(row, index) in data" 
            :key="index"
            class="hover:bg-slate-50 transition-colors duration-200"
          >
            <td
              v-for="column in columns"
              :key="column.key"
              class="px-6 py-4 whitespace-nowrap text-sm text-slate-900"
            >
              <slot 
                :name="`column-${column.key}`"
                :row="row"
                :value="row[column.key]"
                :index="index"
              >
                {{ formatValue(row[column.key], column.type) }}
              </slot>
            </td>
            <td v-if="hasActions" class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <slot name="actions" :row="row" :index="index" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Table Footer -->
    <div v-if="showFooter" class="px-6 py-3 bg-slate-50 border-t border-slate-200">
      <div class="flex items-center justify-between">
        <div class="text-sm text-slate-700">
          共 {{ total || data.length }} 条记录
        </div>
        <div v-if="$slots.footer" class="flex items-center space-x-2">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue'
import type { Column } from '@/types'

interface Props {
  title?: string
  description?: string
  columns: Column[]
  data: Record<string, any>[]
  loading?: boolean
  emptyText?: string
  showFooter?: boolean
  total?: number
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  emptyText: '暂无数据',
  showFooter: true
})

const slots = useSlots()

// 判断是否有操作列
const hasActions = computed(() => !!slots.actions)

// 格式化值显示
const formatValue = (value: any, type?: string) => {
  if (value === null || value === undefined) {
    return '-'
  }

  switch (type) {
    case 'number':
      return typeof value === 'number' ? value.toLocaleString() : value
    case 'date':
      return new Date(value).toLocaleString('zh-CN')
    case 'boolean':
      return value ? '是' : '否'
    case 'status':
      return value === 0 ? '可用' : '不可用'
    default:
      return value
  }
}
</script>

<style scoped>
/* 自定义滚动条 */
.overflow-x-auto::-webkit-scrollbar {
  height: 6px;
}

.overflow-x-auto::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.overflow-x-auto::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.overflow-x-auto::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>