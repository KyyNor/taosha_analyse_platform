<template>
  <div class="min-h-screen bg-base-100">
    <!-- 导航栏 -->
    <div class="navbar bg-base-200 shadow-lg">
      <div class="navbar-start">
        <div class="dropdown">
          <label tabindex="0" class="btn btn-ghost lg:hidden">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"></path>
            </svg>
          </label>
          <ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
            <li><RouterLink to="/query">智能查询</RouterLink></li>
            <li><RouterLink to="/history">查询历史</RouterLink></li>
            <li><RouterLink to="/favorites">收藏查询</RouterLink></li>
            <li v-if="authStore.hasPermission('metadata:read')">
              <details>
                <summary>元数据管理</summary>
                <ul class="p-2">
                  <li><RouterLink to="/metadata/tables">表管理</RouterLink></li>
                  <li><RouterLink to="/metadata/fields">字段管理</RouterLink></li>
                  <li><RouterLink to="/metadata/glossary">术语管理</RouterLink></li>
                  <li><RouterLink to="/metadata/themes">主题管理</RouterLink></li>
                </ul>
              </details>
            </li>
          </ul>
        </div>
        <RouterLink to="/" class="btn btn-ghost normal-case text-xl font-bold text-primary">
          淘沙分析平台
        </RouterLink>
      </div>
      
      <div class="navbar-center hidden lg:flex">
        <ul class="menu menu-horizontal px-1">
          <li><RouterLink to="/query" class="btn btn-ghost">智能查询</RouterLink></li>
          <li><RouterLink to="/history" class="btn btn-ghost">查询历史</RouterLink></li>
          <li><RouterLink to="/favorites" class="btn btn-ghost">收藏查询</RouterLink></li>
          <li v-if="authStore.hasPermission('metadata:read')" class="dropdown dropdown-hover">
            <label tabindex="0" class="btn btn-ghost">元数据管理</label>
            <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52">
              <li><RouterLink to="/metadata/tables">表管理</RouterLink></li>
              <li><RouterLink to="/metadata/fields">字段管理</RouterLink></li>
              <li><RouterLink to="/metadata/glossary">术语管理</RouterLink></li>
              <li><RouterLink to="/metadata/themes">主题管理</RouterLink></li>
            </ul>
          </li>
        </ul>
      </div>
      
      <div class="navbar-end">
        <!-- 主题切换 -->
        <button 
          @click="themeStore.toggleTheme()" 
          class="btn btn-ghost btn-circle"
          :title="themeStore.isDarkTheme() ? '切换到浅色主题' : '切换到深色主题'"
        >
          <span class="text-lg">{{ themeStore.getThemeIcon() }}</span>
        </button>
        
        <!-- 用户菜单 -->
        <div class="dropdown dropdown-end">
          <label tabindex="0" class="btn btn-ghost btn-circle avatar">
            <div class="w-8 rounded-full">
              <img v-if="authStore.user?.avatar" :src="authStore.user?.avatar" :alt="authStore.user?.nickname" />
              <div v-else class="bg-primary text-primary-content w-8 h-8 rounded-full flex items-center justify-center">
                {{ authStore.user?.nickname?.charAt(0) || 'U' }}
              </div>
            </div>
          </label>
          <ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
            <li class="menu-title">
              <span>{{ authStore.user?.nickname }}</span>
            </li>
            <li><a>个人设置</a></li>
            <li><a>帮助文档</a></li>
            <li><hr class="my-2"></li>
            <li><a @click="handleLogout" class="text-error">退出登录</a></li>
          </ul>
        </div>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <main class="container mx-auto px-4 py-6">
      <slot />
    </main>

    <!-- 通知组件 -->
    <div class="toast toast-end">
      <div 
        v-for="notification in notificationStore.notifications" 
        :key="notification.id"
        :class="['alert', notificationStore.getAlertClass(notification.type)]"
        class="mb-2"
      >
        <span>{{ notificationStore.getIcon(notification.type) }}</span>
        <div>
          <h4 v-if="notification.title" class="font-bold">{{ notification.title }}</h4>
          <div class="text-xs">{{ notification.message }}</div>
        </div>
        <button 
          @click="notificationStore.removeNotification(notification.id)"
          class="btn btn-sm btn-circle"
        >
          ✕
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useNotificationStore } from '@/stores/notification'

const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const notificationStore = useNotificationStore()

// 处理登出
const handleLogout = () => {
  authStore.logout()
  notificationStore.success('已退出登录')
  router.push('/login')
}
</script>