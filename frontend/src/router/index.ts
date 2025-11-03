import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

// Import layouts
import MainLayout from '@/components/layout/MainLayout.vue'

// Import views
import QueryPage from '@/views/QueryPage.vue'
import AgentPage from '@/views/AgentPage.vue'
import MetadataPage from '@/views/MetadataPage.vue'
import LogsPage from '@/views/LogsPage.vue'
import FavoritesPage from '@/views/FavoritesPage.vue'
import SettingsPage from '@/views/SettingsPage.vue'

// Define routes
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    meta: {
      layout: 'main'
    },
    children: [
      {
        path: '',
        name: 'Home',
        redirect: '/nlquery'
      },
      {
        path: 'nlquery',
        name: 'Query',
        component: QueryPage,
        meta: {
          title: '淘沙查询 - 淘沙分析平台'
        }
      },
      {
        path: 'agent',
        name: 'Agent',
        component: AgentPage,
        meta: {
          title: '淘沙Agent - 淘沙分析平台'
        }
      },
      {
        path: 'metadata',
        name: 'Metadata',
        redirect: '/metadata/tables',
        component: MetadataPage,
        meta: {
          title: '元数据配置 - 淘沙分析平台'
        },
        children: [
          {
            path: 'tables',
            name: 'MetadataTables',
            component: () => import('@/views/metadata/TablesPage.vue'),
            meta: {
              title: '表配置 - 淘沙分析平台'
            }
          },
            {
            path: 'relations',
            name: 'MetadataRelations',
            component: () => import('@/views/metadata/RelationsPage.vue'),
            meta: {
              title: '关联配置 - 淘沙分析平台'
            }
          },
          {
            path: 'glossary',
            name: 'MetadataGlossary',
            component: () => import('@/views/metadata/GlossaryPage.vue'),
            meta: {
              title: '业务术语 - 淘沙分析平台'
            }
          },
          {
            path: 'themes',
            name: 'MetadataThemes',
            component: () => import('@/views/metadata/ThemesPage.vue'),
            meta: {
              title: '数据主题 - 淘沙分析平台'
            }
          },
          {
            path: 'prompt-templates',
            name: 'MetadataPromptTemplates',
            component: () => import('@/views/metadata/PromptTemplatesPage.vue'),
            meta: {
              title: '提示词配置 - 淘沙分析平台'
            }
          }
        ]
      },
      {
        path: 'logs',
        name: 'Logs',
        component: LogsPage,
        meta: {
          title: '日志管理 - 淘沙分析平台'
        }
      },
      {
        path: 'favorites',
        name: 'Favorites',
        component: FavoritesPage,
        meta: {
          title: '我的收藏 - 淘沙分析平台'
        }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: SettingsPage,
        meta: {
          title: '系统设置 - 淘沙分析平台'
        }
      }
    ]
  },
  // 404 page
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundPage.vue'),
    meta: {
      title: '页面未找到 - 淘沙分析平台',
      layout: 'error'
    }
  }
]

// Create router instance
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else if (to.hash) {
      return { el: to.hash, behavior: 'smooth' }
    } else {
      return { top: 0, behavior: 'smooth' }
    }
  }
})

// Navigation guards
router.beforeEach(async (to, _from, next) => {
  // Set page title
  if (to.meta.title) {
    document.title = to.meta.title as string
  }

  // Show loading state
  const appElement = document.getElementById('app')
  if (appElement) {
    appElement.classList.add('loading')
  }

  next()
})

router.afterEach(() => {
  // Hide loading state
  const appElement = document.getElementById('app')
  if (appElement) {
    appElement.classList.remove('loading')
  }
})

// Error handling
router.onError((error) => {
  console.error('Router error:', error)
  // You might want to redirect to an error page here
})

export default router
