<template>
  <header class="navbar bg-base-100 shadow-lg px-4 lg:px-6">
    <div class="navbar-start">
      <!-- Logo -->
      <div class="flex items-center gap-2">
        <span class="text-xl font-semibold">淘沙分析平台</span>
      </div>
    </div>

    <div class="navbar-center lg:flex">
      <!-- Main Navigation -->
      <ul class="menu menu-horizontal px-1 gap-2">
        <li
          v-for="item in mainNavItems"
          :key="item.name"
        >
          <!-- Metadata Dropdown Menu -->
          <div
            v-if="item.name === 'Metadata'"
            class="dropdown dropdown-hover dropdown-bottom"
          >
            <label
              tabindex="0"
              :class="{ 'active': isMetadataRouteActive() }"
              class="flex items-center gap-2 cursor-pointer"
            >
              <component
                :is="item.icon"
                class="w-4 h-4"
              />
              {{ item.label }}
            </label>
            <ul
              tabindex="0"
              class="dropdown-content menu p-2 shadow bg-base-100 w-max rounded-box min-w-36 z-50"
            >
              <li
                v-for="subItem in metadataSubItems"
                :key="subItem.name"
              >
                <router-link
                  :to="subItem.path"
                  :class="{ 'active': $route.name === subItem.name }"
                  class="flex items-center gap-2"
                >
                  <component
                    :is="subItem.icon"
                    class="w-4 h-4"
                  />
                  {{ subItem.label }}
                </router-link>
              </li>
            </ul>
          </div>
          <!-- Regular Navigation Items -->
          <router-link
            v-else
            :to="item.path"
            :class="{ 'active': $route.name === item.name }"
            class="flex items-center gap-2"
          >
            <component
              :is="item.icon"
              class="w-4 h-4"
            />
            {{ item.label }}
          </router-link>
        </li>
      </ul>
    </div>

    <div class="navbar-end">
      <div class="flex items-center gap-2">
        <!-- Theme Toggle -->
        <button
          class="btn btn-ghost btn-circle"
          :title="`当前主题: ${themeStore.theme === 'light' ? '浅色' : '深色'} (点击切换)`"
          aria-label="主题切换"
          @click="toggleTheme"
        >
          <svg
            v-if="themeStore.theme === 'light'"
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
              d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
            />
          </svg>
          <svg
            v-else
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
        </button>

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
              <span class="badge badge-xs badge-primary indicator-item" />
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
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
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
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                系统设置
              </router-link>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </header>
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

// Metadata sub-menu icons
const TableIcon = () => h('svg', {
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

const ColumnIcon = () => h('svg', {
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
    d: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2'
  })
])

const LinkIcon = () => h('svg', {
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
    d: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1'
  })
])

const BookIcon = () => h('svg', {
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
    d: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253'
  })
])

const ThemeIcon = () => h('svg', {
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
    d: 'M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01'
  })
])

const PromptIcon = () => h('svg', {
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
  }),
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M14 8l-3 3-3-3'
  })
])

const router = useRouter()
const themeStore = useThemeStore()

// Toggle theme function
const toggleTheme = () => {
  themeStore.setTheme(themeStore.theme === 'light' ? 'dark' : 'light')
}

// Main navigation items
const mainNavItems = computed(() => [
  {
    name: 'Query',
    path: '/nlquery',
    label: '淘沙查询',
    icon: SearchIcon
  },
  {
    name: 'Metadata',
    path: '/metadata/tables',
    label: '元数据配置',
    icon: DatabaseIcon
  },
  {
    name: 'Logs',
    path: '/logs',
    label: '日志管理',
    icon: DocumentTextIcon
  },
  {
    name: 'Favorites',
    path: '/favorites',
    label: '我的收藏',
    icon: BookmarkIcon
  },
  {
    name: 'Settings',
    path: '/settings',
    label: '系统设置',
    icon: CogIcon
  }
])

// Metadata sub-menu items
const metadataSubItems = computed(() => [
  {
    name: 'MetadataTables',
    path: '/metadata/tables',
    label: '表配置',
    icon: TableIcon
  },
  {
    name: 'MetadataRelations',
    path: '/metadata/relations',
    label: '关联配置',
    icon: LinkIcon
  },
  {
    name: 'MetadataGlossary',
    path: '/metadata/glossary',
    label: '业务术语',
    icon: BookIcon
  },
  {
    name: 'MetadataPromptTemplates',
    path: '/metadata/prompt-templates',
    label: '提示词配置',
    icon: PromptIcon
  },
  {
    name: 'MetadataThemes',
    path: '/metadata/themes',
    label: '数据主题',
    icon: ThemeIcon
  }
])

// Check if any metadata route is active
const isMetadataRouteActive = () => {
  const currentRouteName = router.currentRoute.value.name
  return currentRouteName === 'Metadata' ||
         (typeof currentRouteName === 'string' && currentRouteName.startsWith('Metadata'))
}

</script>
