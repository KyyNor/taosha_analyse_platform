import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 用户信息类型
export interface User {
  id: number
  username: string
  nickname?: string
  email?: string
  roles: string[]
  permissions: string[]
  avatar?: string
  lastLoginTime?: string
  createdAt?: string
}

// 登录请求类型
export interface LoginRequest {
  username: string
  password: string
}

// 登录响应类型
export interface LoginResponse {
  user: User
  token: string
  refreshToken?: string
  expiresIn: number
}

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const loading = ref(false)

  // 计算属性
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const userRoles = computed(() => user.value?.roles || [])
  const userPermissions = computed(() => user.value?.permissions || [])

  // 初始化状态（从 localStorage 恢复）
  function initializeAuth() {
    const storedToken = localStorage.getItem('taosha_token')
    const storedUser = localStorage.getItem('taosha_user')
    const storedRefreshToken = localStorage.getItem('taosha_refresh_token')

    if (storedToken && storedUser) {
      try {
        token.value = storedToken
        user.value = JSON.parse(storedUser)
        refreshToken.value = storedRefreshToken
      } catch (error) {
        console.error('恢复登录状态失败:', error)
        clearAuth()
      }
    }
  }

  // 登录
  async function login(credentials: LoginRequest): Promise<void> {
    loading.value = true
    try {
      // TODO: 替换为实际的 API 调用
      const response = await mockLogin(credentials)
      
      // 保存认证信息
      token.value = response.token
      user.value = response.user
      refreshToken.value = response.refreshToken || null

      // 持久化到 localStorage
      localStorage.setItem('taosha_token', response.token)
      localStorage.setItem('taosha_user', JSON.stringify(response.user))
      if (response.refreshToken) {
        localStorage.setItem('taosha_refresh_token', response.refreshToken)
      }
    } finally {
      loading.value = false
    }
  }

  // 登出
  function logout() {
    clearAuth()
    // 可以在这里调用后端的登出接口
  }

  // 清除认证状态
  function clearAuth() {
    user.value = null
    token.value = null
    refreshToken.value = null
    localStorage.removeItem('taosha_token')
    localStorage.removeItem('taosha_user')
    localStorage.removeItem('taosha_refresh_token')
  }

  // 检查是否有指定权限
  function hasPermission(permission: string): boolean {
    if (!user.value) return false
    return userPermissions.value.includes(permission)
  }

  // 检查是否有指定角色
  function hasRole(role: string): boolean {
    if (!user.value) return false
    return userRoles.value.includes(role)
  }

  // 检查是否有任意一个权限
  function hasAnyPermission(permissions: string[]): boolean {
    if (!user.value) return false
    return permissions.some(permission => userPermissions.value.includes(permission))
  }

  // 检查是否有任意一个角色
  function hasAnyRole(roles: string[]): boolean {
    if (!user.value) return false
    return roles.some(role => userRoles.value.includes(role))
  }

  // 更新用户信息
  function updateUser(updatedUser: Partial<User>) {
    if (user.value) {
      user.value = { ...user.value, ...updatedUser }
      localStorage.setItem('taosha_user', JSON.stringify(user.value))
    }
  }

  // 刷新 token
  async function refreshAuthToken(): Promise<boolean> {
    if (!refreshToken.value) return false

    try {
      // TODO: 调用刷新 token 的 API
      const response = await mockRefreshToken(refreshToken.value)
      
      token.value = response.token
      if (response.refreshToken) {
        refreshToken.value = response.refreshToken
      }

      localStorage.setItem('taosha_token', response.token)
      if (response.refreshToken) {
        localStorage.setItem('taosha_refresh_token', response.refreshToken)
      }

      return true
    } catch (error) {
      console.error('刷新 token 失败:', error)
      clearAuth()
      return false
    }
  }

  return {
    // 状态
    user,
    token,
    refreshToken,
    loading,
    
    // 计算属性
    isAuthenticated,
    userRoles,
    userPermissions,
    
    // 方法
    initializeAuth,
    login,
    logout,
    clearAuth,
    hasPermission,
    hasRole,
    hasAnyPermission,
    hasAnyRole,
    updateUser,
    refreshAuthToken
  }
})

// 模拟登录 API（开发环境使用）
async function mockLogin(credentials: LoginRequest): Promise<LoginResponse> {
  // 模拟网络延迟
  await new Promise(resolve => setTimeout(resolve, 1000))

  // 简单的用户名密码验证
  if (credentials.username === 'admin' && credentials.password === 'admin123') {
    return {
      user: {
        id: 1,
        username: 'admin',
        nickname: '管理员',
        email: 'admin@taosha.com',
        roles: ['admin', 'user'],
        permissions: [
          'system:read', 'system:write',
          'metadata:read', 'metadata:write',
          'metadata:table:read', 'metadata:table:write',
          'metadata:field:read', 'metadata:field:write',
          'metadata:glossary:read', 'metadata:glossary:write',
          'metadata:theme:read', 'metadata:theme:write',
          'query:read', 'query:write'
        ],
        avatar: '',
        lastLoginTime: new Date().toISOString(),
        createdAt: '2024-01-01T00:00:00Z'
      },
      token: 'mock-jwt-token-admin',
      refreshToken: 'mock-refresh-token-admin',
      expiresIn: 7200
    }
  } else if (credentials.username === 'user' && credentials.password === 'user123') {
    return {
      user: {
        id: 2,
        username: 'user',
        nickname: '普通用户',
        email: 'user@taosha.com',
        roles: ['user'],
        permissions: ['query:read', 'query:write'],
        avatar: '',
        lastLoginTime: new Date().toISOString(),
        createdAt: '2024-01-01T00:00:00Z'
      },
      token: 'mock-jwt-token-user',
      refreshToken: 'mock-refresh-token-user',
      expiresIn: 7200
    }
  } else {
    throw new Error('用户名或密码错误')
  }
}

// 模拟刷新 token API
async function mockRefreshToken(refreshToken: string): Promise<{ token: string; refreshToken?: string }> {
  await new Promise(resolve => setTimeout(resolve, 500))
  
  if (refreshToken.includes('admin')) {
    return {
      token: 'new-mock-jwt-token-admin',
      refreshToken: 'new-mock-refresh-token-admin'
    }
  } else {
    return {
      token: 'new-mock-jwt-token-user',
      refreshToken: 'new-mock-refresh-token-user'
    }
  }
}