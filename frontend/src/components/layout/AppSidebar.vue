<template>
  <aside class="w-64 min-h-screen bg-base-200 border-r border-base-300">
    <div class="p-4">
      <!-- Quick Actions -->
      <div class="mb-6">
        <h3 class="text-sm font-semibold text-base-content/60 mb-3">
          快速操作
        </h3>
        <div class="space-y-2">
          <button
            class="btn btn-primary btn-block btn-sm"
            @click="$router.push('/query')"
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
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            新建查询
          </button>
          <button
            class="btn btn-outline btn-block btn-sm"
            @click="$router.push('/metadata/tables')"
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
                d="M12 4v16m8-8H4"
              />
            </svg>
            添加表元数据
          </button>
        </div>
      </div>

      <!-- Statistics -->
      <div class="mb-6">
        <h3 class="text-sm font-semibold text-base-content/60 mb-3">
          统计信息
        </h3>
        <div class="grid grid-cols-2 gap-3">
          <div class="stat p-3 bg-base-100 rounded-lg">
            <div class="stat-value text-lg">
              {{ queryStore.queryHistory.length }}
            </div>
            <div class="stat-desc text-xs">
              今日查询
            </div>
          </div>
          <div class="stat p-3 bg-base-100 rounded-lg">
            <div class="stat-value text-lg">
              {{ queryStore.favorites.length }}
            </div>
            <div class="stat-desc text-xs">
              收藏查询
            </div>
          </div>
        </div>
      </div>

      <!-- Recent Queries -->
      <div class="mb-6">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-semibold text-base-content/60">
            最近查询
          </h3>
          <router-link
            to="/logs"
            class="text-xs text-primary hover:underline"
          >
            查看全部
          </router-link>
        </div>
        <div class="space-y-2">
          <div
            v-for="query in recentQueries"
            :key="query.id"
            class="p-2 bg-base-100 rounded-lg cursor-pointer hover:bg-base-300 transition-colors"
            @click="handleRerunQuery(query)"
          >
            <div class="text-sm font-medium truncate">
              {{ query.userInput }}
            </div>
            <div class="text-xs text-base-content/60">
              {{ formatTime(query.createdAt) }}
            </div>
          </div>
          <div
            v-if="recentQueries.length === 0"
            class="text-sm text-base-content/40 text-center py-4"
          >
            暂无查询记录
          </div>
        </div>
      </div>

      <!-- Quick Links -->
      <div>
        <h3 class="text-sm font-semibold text-base-content/60 mb-3">
          快速链接
        </h3>
        <ul class="space-y-1">
          <li>
            <a
              href="https://github.com"
              target="_blank"
              class="flex items-center gap-2 text-sm text-base-content/80 hover:text-primary transition-colors"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
              GitHub 仓库
            </a>
          </li>
          <li>
            <a
              href="#"
              class="flex items-center gap-2 text-sm text-base-content/80 hover:text-primary transition-colors"
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
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              API 文档
            </a>
          </li>
          <li>
            <a
              href="#"
              class="flex items-center gap-2 text-sm text-base-content/80 hover:text-primary transition-colors"
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
                  d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              帮助中心
            </a>
          </li>
        </ul>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useQueryStore } from '@stores/query'
import type { QueryTask } from '@types/index'

const router = useRouter()
const queryStore = useQueryStore()

// Recent queries (last 5)
const recentQueries = computed(() => {
  return queryStore.queryHistory
    .slice(0, 5)
    .map(log => ({
      id: log.id,
      userInput: log.query,
      createdAt: log.createdAt
    }))
})

// Format time
const formatTime = (timeStr: string) => {
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days}天前`
  if (hours > 0) return `${hours}小时前`
  if (minutes > 0) return `${minutes}分钟前`
  return '刚刚'
}

// Handle rerun query
const handleRerunQuery = async (query: any) => {
  try {
    await queryStore.rerunQuery(query.id)
    router.push('/query')
  } catch (error) {
    console.error('Failed to rerun query:', error)
  }
}
</script>
