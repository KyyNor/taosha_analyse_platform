<template>
  <header class="navbar bg-base-100 shadow-lg px-4 lg:px-6">
    <div class="navbar-start">
      <!-- Logo -->
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
          <span class="text-primary-content font-bold text-lg">淘</span>
        </div>
        <span class="text-xl font-semibold">淘沙分析平台</span>
      </div>
    </div>

    <div class="navbar-center hidden lg:flex">
      <!-- Main Navigation -->
      <ul class="menu menu-horizontal px-1 gap-2">
        <li v-for="item in mainNavItems" :key="item.name">
          <router-link
            :to="item.path"
            :class="{ 'active': $route.name === item.name }"
            class="flex items-center gap-2"
          >
            <component :is="item.icon" class="w-4 h-4" />
            {{ item.label }}
          </router-link>
        </li>
      </ul>
    </div>

    <div class="navbar-end">
      <div class="flex items-center gap-2">
        <!-- Theme Toggle -->
        <div class="dropdown dropdown-end">
          <label
            tabindex="0"
            class="btn btn-ghost btn-circle"
            role="button"
            aria-label="主题切换"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
              />
            </svg>
          </label>
          <ul
            tabindex="0"
            class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-52"
          >
            <li @click="themeStore.setTheme('light')">
              <a :class="{ 'active': themeStore.theme === 'light' }">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                浅色主题
              </a>
            </li>
            <li @click="themeStore.setTheme('dark')">
              <a :class="{ 'active': themeStore.theme === 'dark' }">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
                深色主题
              </a>
            </li>
            <li @click="themeStore.setAutoSwitch(!themeStore.autoSwitch)">
              <a>
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                自动切换 ({{ themeStore.autoSwitch ? '开' : '关' }})
              </a>
            </li>
          </ul>
        </div>

        <!-- Notifications -->
        <div class="dropdown dropdown-end">
          <label
            tabindex="0"
            class="btn btn-ghost btn-circle"
            role="button"
            aria-label="通知"
          >
            <div class="indicator">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                />
              </svg>
              <span class="badge badge-xs badge-primary indicator-item"></span>
            </div>
          </label>
          <ul
            tabindex="0"
            class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-80"
          >
            <li class="menu-title">
              <span>通知</span>
            </li>
            <li><a>暂无新通知</a></li>
          </ul>
        </div>

        <!-- Settings (instead of User Menu for development) -->
        <div class="dropdown dropdown-end">
          <label
            tabindex="0"
            class="btn btn-ghost btn-circle"
            role="button"
            aria-label="设置"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </label>
          <ul
            tabindex="0"
            class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-52"
          >
            <li class="menu-title">
              <span>开发阶段</span>
            </li>
            <li>
              <router-link to="/settings">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                系统设置
              </router-link>
            </li>
          </ul>
        </div>

        <!-- Mobile Menu Toggle -->
        <div class="lg:hidden">
          <label
            for="mobile-menu-drawer"
            class="btn btn-ghost btn-circle"
            role="button"
            aria-label="菜单"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </label>
        </div>
      </div>
    </div>
  </header>

  <!-- Mobile Menu Drawer -->
  <input id="mobile-menu-drawer" type="checkbox" class="drawer-toggle" />
  <div class="drawer-side lg:hidden">
    <label for="mobile-menu-drawer" class="drawer-overlay"></label>
    <aside class="w-64 min-h-full bg-base-100">
      <div class="p-4">
        <div class="flex items-center gap-2 mb-6">
          <div class="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <span class="text-primary-content font-bold text-lg">淘</span>
          </div>
          <span class="text-xl font-semibold">淘沙分析平台</span>
        </div>

        <ul class="menu menu-vertical gap-2">
          <li v-for="item in mainNavItems" :key="item.name">
            <router-link
              :to="item.path"
              :class="{ 'active': $route.name === item.name }"
              class="flex items-center gap-2"
              @click="closeMobileDrawer"
            >
              <component :is="item.icon" class="w-4 h-4" />
              {{ item.label }}
            </router-link>
          </li>
        </ul>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeStore } from '@stores/theme'

// Icons (using heroicons outlines)
const SearchIcon = () => h('svg', {
  xmlns: 'http://www.w3.org/2000/svg',
  class: 'h-5 w-5',
  fill: 'none',
  viewBox: '0 0 24 24',
  stroke: 'currentColor'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z'
  })
])

const DatabaseIcon = () => h('svg', {
  xmlns: 'http://www.w3.org/2000/svg',
  class: 'h-5 w-5',
  fill: 'none',
  viewBox: '0 0 24 24',
  stroke: 'currentColor'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4'
  })
])

const DocumentTextIcon = () => h('svg', {
  xmlns: 'http://www.w3.org/2000/svg',
  class: 'h-5 w-5',
  fill: 'none',
  viewBox: '0 0 24 24',
  stroke: 'currentColor'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
  })
])

const BookmarkIcon = () => h('svg', {
  xmlns: 'http://www.w3.org/2000/svg',
  class: 'h-5 w-5',
  fill: 'none',
  viewBox: '0 0 24 24',
  stroke: 'currentColor'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z'
  })
])

const CogIcon = () => h('svg', {
  xmlns: 'http://www.w3.org/2000/svg',
  class: 'h-5 w-5',
  fill: 'none',
  viewBox: '0 0 24 24',
  stroke: 'currentColor'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z'
  }),
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z'
  })
])

const router = useRouter()
const themeStore = useThemeStore()

// Main navigation items
const mainNavItems = computed(() => [
  {
    name: 'Query',
    path: '/query',
    label: '淘沙查询',
    icon: SearchIcon,
  },
  {
    name: 'Metadata',
    path: '/metadata',
    label: '元数据配置',
    icon: DatabaseIcon,
  },
  {
    name: 'Logs',
    path: '/logs',
    label: '日志管理',
    icon: DocumentTextIcon,
  },
  {
    name: 'Favorites',
    path: '/favorites',
    label: '我的收藏',
    icon: BookmarkIcon,
  },
  {
    name: 'Settings',
    path: '/settings',
    label: '系统设置',
    icon: CogIcon,
  },
])

// Close mobile drawer
const closeMobileDrawer = () => {
  const drawer = document.getElementById('mobile-menu-drawer') as HTMLInputElement
  if (drawer) {
    drawer.checked = false
  }
}
</script>