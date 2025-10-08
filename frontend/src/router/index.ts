import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 路由组件懒加载
const Dashboard = () => import('@/views/Dashboard.vue')
const Query = () => import('@/views/Query.vue')
const History = () => import('@/views/QueryHistory.vue')
const Favorites = () => import('@/views/Favorites.vue')
const Metadata = () => import('@/views/metadata/MetadataLayout.vue')
const Tables = () => import('@/views/metadata/Tables.vue')
const Fields = () => import('@/views/metadata/Fields.vue')
const Glossary = () => import('@/views/metadata/Glossary.vue')
const Themes = () => import('@/views/metadata/Themes.vue')
// const System = () => import('@/views/system/SystemLayout.vue')
// const Users = () => import('@/views/system/Users.vue')
// const Roles = () => import('@/views/system/Roles.vue')
// const Logs = () => import('@/views/system/Logs.vue')
// const Settings = () => import('@/views/system/Settings.vue')
const Login = () => import('@/views/Login.vue')
const NotFound = () => import('@/views/NotFound.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: {
      title: '登录',
      requiresAuth: false
    }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: {
      title: '仪表板',
      requiresAuth: true
    }
  },
  {
    path: '/query',
    name: 'Query',
    component: Query,
    meta: {
      title: '智能查询',
      requiresAuth: true
    }
  },
  {
    path: '/history',
    name: 'History',
    component: History,
    meta: {
      title: '查询历史',
      requiresAuth: true
    }
  },
  {
    path: '/favorites',
    name: 'Favorites',
    component: Favorites,
    meta: {
      title: '收藏查询',
      requiresAuth: true
    }
  },
  {
    path: '/metadata',
    component: Metadata,
    meta: {
      title: '元数据管理',
      requiresAuth: true,
      requiresPermission: 'metadata:read'
    },
    children: [
      {
        path: '',
        redirect: '/metadata/tables'
      },
      {
        path: 'tables',
        name: 'MetadataTables',
        component: Tables,
        meta: {
          title: '表管理',
          requiresPermission: 'metadata:table:read'
        }
      },
      {
        path: 'fields',
        name: 'MetadataFields',
        component: Fields,
        meta: {
          title: '字段管理',
          requiresPermission: 'metadata:field:read'
        }
      },
      {
        path: 'glossary',
        name: 'MetadataGlossary',
        component: Glossary,
        meta: {
          title: '术语管理',
          requiresPermission: 'metadata:glossary:read'
        }
      },
      {
        path: 'themes',
        name: 'MetadataThemes',
        component: Themes,
        meta: {
          title: '主题管理',
          requiresPermission: 'metadata:theme:read'
        }
      }
    ]
  },
  /*
  {
    path: '/system',
    component: System,
    meta: {
      title: '系统管理',
      requiresAuth: true,
      requiresPermission: 'system:read'
    },
    children: [
      {
        path: '',
        redirect: '/system/users'
      },
      {
        path: 'users',
        name: 'SystemUsers',
        component: Users,
        meta: {
          title: '用户管理',
          requiresPermission: 'system:user:read'
        }
      },
      {
        path: 'roles',
        name: 'SystemRoles',
        component: Roles,
        meta: {
          title: '角色管理',
          requiresPermission: 'system:role:read'
        }
      },
      {
        path: 'logs',
        name: 'SystemLogs',
        component: Logs,
        meta: {
          title: '日志管理',
          requiresPermission: 'system:log:read'
        }
      },
      {
        path: 'settings',
        name: 'SystemSettings',
        component: Settings,
        meta: {
          title: '系统设置',
          requiresPermission: 'system:setting:read'
        }
      }
    ]
  },
  */
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFound,
    meta: {
      title: '页面未找到',
      requiresAuth: false
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // 设置页面标题
  document.title = to.meta?.title 
    ? `${to.meta.title} - 淘沙分析平台` 
    : '淘沙分析平台'
  
  // 检查认证状态
  if (to.meta?.requiresAuth !== false) {
    if (!authStore.isAuthenticated) {
      // 未登录，重定向到登录页
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
      return
    }
    
    // 检查权限
    if (to.meta?.requiresPermission) {
      const permission = to.meta.requiresPermission as string
      if (!authStore.hasPermission(permission)) {
        // 权限不足，显示错误页面或重定向
        next({ name: 'NotFound' })
        return
      }
    }
  }
  
  // 已登录用户访问登录页，重定向到首页
  if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
    return
  }
  
  next()
})

export default router