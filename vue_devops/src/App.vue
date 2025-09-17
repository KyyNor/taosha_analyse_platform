<template>
  <div class="min-h-screen bg-white">
    <!-- Sticky Navigation -->
    <nav class="sticky top-0 z-50 bg-white shadow-sm border-b border-slate-100">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <!-- Logo -->
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
              <MagnifyingGlassIcon class="w-5 h-5 text-white" />
            </div>
            <div class="font-bold text-xl text-slate-800 tracking-tight">
              淘沙分析平台
            </div>
          </div>

          <!-- Navigation Links -->
          <div class="hidden md:flex items-center space-x-1">
            <router-link
              v-for="route in navRoutes"
              :key="route.name"
              :to="{ name: route.name }"
              class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200"
              :class="isActiveRoute(route.name) 
                ? 'bg-blue-50 text-blue-600' 
                : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'"
            >
              {{ route.title }}
            </router-link>
            
            <!-- Health Status Indicator -->
            <div class="ml-4 flex items-center space-x-2">
              <div 
                :class="[
                  'w-2 h-2 rounded-full',
                  isHealthy ? 'bg-green-500' : 'bg-red-500'
                ]"
              ></div>
              <span class="text-xs text-slate-500">
                {{ isHealthy ? '服务正常' : '服务异常' }}
              </span>
            </div>
          </div>

          <!-- Mobile menu button -->
          <div class="md:hidden">
            <button
              @click="mobileMenuOpen = !mobileMenuOpen"
              class="p-2 rounded-lg text-slate-600 hover:text-slate-800 hover:bg-slate-50"
            >
              <Bars3Icon class="w-6 h-6" />
            </button>
          </div>
        </div>

        <!-- Mobile Navigation -->
        <div v-if="mobileMenuOpen" class="md:hidden py-3 border-t border-slate-100">
          <div class="space-y-1">
            <router-link
              v-for="route in navRoutes"
              :key="route.name"
              :to="{ name: route.name }"
              @click="mobileMenuOpen = false"
              class="block px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200"
              :class="isActiveRoute(route.name) 
                ? 'bg-blue-50 text-blue-600' 
                : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'"
            >
              {{ route.title }}
            </router-link>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="flex-1">
      <router-view />
    </main>

    <!-- Footer -->
    <footer class="bg-slate-100 border-t border-slate-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { MagnifyingGlassIcon, Bars3Icon } from '@heroicons/vue/24/outline'
import { apiClient } from '@/api'

// 响应式数据
const mobileMenuOpen = ref(false)
const isHealthy = ref(true)

// 导航路由配置
const navRoutes = [
  { name: 'DataQuery', title: '数据查询' },
  { name: 'MetadataManagement', title: '元数据管理' },
]

// 获取当前路由
const route = useRoute()

// 判断是否为当前激活路由
const isActiveRoute = (routeName: string) => {
  return route.name === routeName
}

// 健康检查
const checkHealth = async () => {
  try {
    isHealthy.value = await apiClient.healthCheck()
  } catch {
    isHealthy.value = false
  }
}

// 定时健康检查
let healthCheckInterval: number

onMounted(() => {
  // 立即执行一次健康检查
  checkHealth()
  
  // 每30秒检查一次
  healthCheckInterval = window.setInterval(checkHealth, 3600000)
})

onUnmounted(() => {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval)
  }
})
</script>

<style scoped>
/* 路由过渡动画 */
.router-enter-active,
.router-leave-active {
  transition: all 0.3s ease;
}

.router-enter-from,
.router-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>