/**
 * 认证相关的React Hook
 * 提供用户认证状态管理和权限验证功能
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'

// 获取基础路径的工具函数
function getBasePath(): string {
  return process.env.NEXT_PUBLIC_BASE_PATH || ''
}

// 用户信息接口
export interface UserInfo {
  user_id: string
  user_name: string
  branch_no: string
  branch_name: string
  role_id_list: string[]
  role_name_list: string[]
  is_admin: boolean  // 是否为管理员（由后端根据实体的is_admin字段计算）
}

// 认证状态接口
export interface AuthState {
  isAuthenticated: boolean
  isLoading: boolean
  user: UserInfo | null
  token: string | null
  accessiblePages: string[]  // 用户可访问的页面路径列表
}

// 权限检查结果接口
export interface PermissionResult {
  hasPermission: boolean
  loading: boolean
  error?: string
}

// Token管理工具函数
const tokenManager = {
  get(): string | null {
    if (typeof window === 'undefined') return null

    const cookies = document.cookie.split(';')
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=')
      if (name === 'auth_token') {
        return decodeURIComponent(value)
      }
    }

    return localStorage.getItem('auth_token')
  },

  set(token: string): void {
    if (typeof window === 'undefined') return

    const expires = new Date()
    expires.setDate(expires.getDate() + 7)
    document.cookie = `auth_token=${encodeURIComponent(token)}; expires=${expires.toUTCString()}; path=/`
    localStorage.setItem('auth_token', token)
  },

  clear(): void {
    if (typeof window === 'undefined') return

    document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_info')
  }
}

/**
 * 设置认证状态的辅助函数
 */
function updateAuthState(
  state: Partial<AuthState>,
  isAuthenticated: boolean,
  userInfo?: UserInfo,
  token?: string,
  accessiblePages: string[] = []
) {
  setAuthState((prev: AuthState) => ({
    ...prev,
    ...state,
    isAuthenticated,
    user: userInfo,
    token,
    accessiblePages,
    isLoading: false
  }))
}

/**
 * 获取用户可访问的页面列表
 */
async function getAccessiblePages(token: string): Promise<string[]> {
  try {
    const response = await api.get('/permissions/my-pages', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    return response.data.page_paths || []
  } catch {
    return []
  }
}

async function validateTokenAndGetUser(token: string) {
  try {
    const response = await api.get('/login-records/current/info', {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    return {
      valid: true,
      userInfo: {
        user_id: response.data.user_id,
        user_name: response.data.user_name,
        branch_no: response.data.branch_no,
        branch_name: response.data.branch_name,
        role_id_list: response.data.role_id_list,
        role_name_list: response.data.role_name_list,
        is_admin: response.data.is_admin || false
      }
    }
  } catch {
    return { valid: false }
  }
}

/**
 * 主要的认证Hook
 */
export function useAuth(): AuthState & {
  login: (token: string) => Promise<boolean>
  logout: () => void
  refreshAuth: () => Promise<void>
  isAdmin: boolean
} {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    user: null,
    token: null,
    accessiblePages: []
  })
  
  const router = useRouter()
  
  // 初始化认证状态
  useEffect(() => {
    const initAuth = async () => {
      const token = tokenManager.get()

      if (!token) {
        updateAuthState({}, false)
        router.push(`${getBasePath()}/info?reason=no_token`)
        return
      }

      const validation = await validateTokenAndGetUser(token)

      if (validation.valid && validation.userInfo) {
        const accessiblePages = await getAccessiblePages(token)
        updateAuthState({}, true, validation.userInfo, token, accessiblePages)
      } else {
        tokenManager.clear()
        updateAuthState({}, false)
        router.push(`${getBasePath()}/info?reason=invalid_token`)
      }
    }

    initAuth()
  }, [router])

  // 登录函数
  const login = useCallback(async (token: string): Promise<boolean> => {
    const validation = await validateTokenAndGetUser(token)

    if (validation.valid && validation.userInfo) {
      tokenManager.set(token)
      const accessiblePages = await getAccessiblePages(token)
      updateAuthState({}, true, validation.userInfo, token, accessiblePages)
      return true
    }

    return false
  }, [])

  // 登出函数
  const logout = useCallback(() => {
    tokenManager.clear()
    updateAuthState({}, false)
    router.push(`${getBasePath()}/info?reason=no_token`)
  }, [router])

  // 刷新认证状态
  const refreshAuth = useCallback(async () => {
    const token = tokenManager.get()

    if (!token) {
      logout()
      return
    }

    const validation = await validateTokenAndGetUser(token)

    if (validation.valid && validation.userInfo) {
      const accessiblePages = await getAccessiblePages(token)
      updateAuthState({}, true, validation.userInfo, token, accessiblePages)
    } else {
      logout()
    }
  }, [logout])

  const isAdmin = authState.user?.is_admin || false

  return {
    ...authState,
    login,
    logout,
    refreshAuth,
    isAdmin
  }
}

/**
 * 页面权限验证Hook
 */
export function usePagePermission(pagePath: string): PermissionResult {
  const [result, setResult] = useState<PermissionResult>({
    hasPermission: false,
    loading: true
  })
  
  const { isAuthenticated, token, user } = useAuth()
  
  useEffect(() => {
    if (!isAuthenticated || !token) {
      setResult({
        hasPermission: false,
        loading: false,
        error: 'Not authenticated'
      })
      return
    }
    
    // 检查管理员路径
    const adminPaths = ['/admin/departments', '/admin/roles', '/admin/permissions', '/admin/login-records']
    const isAdminPath = adminPaths.some(path => pagePath.startsWith(path))
    
    if (isAdminPath) {
      // 使用后端返回的is_admin字段
      const isAdmin = user?.is_admin || false

      setResult({
        hasPermission: isAdmin,
        loading: false,
        error: isAdmin ? undefined : 'Admin permission required'
      })
      return
    }
    
    // 调用后端API检查权限
    const checkPermission = async () => {
      try {
        const response = await api.post('/permissions/check-access', {
          page_path: pagePath
        })

        setResult({
          hasPermission: response.data.has_access === true,
          loading: false
        })
      } catch (error) {
        console.error('Permission check error:', error)
        setResult({
          hasPermission: false,
          loading: false,
          error: 'Permission check error'
        })
      }
    }
    
    checkPermission()
  }, [isAuthenticated, token, user, pagePath])
  
  return result
}

/**
 * API调用Hook，自动添加认证头
 */
export function useAuthenticatedFetch() {
  const { token, isAuthenticated } = useAuth()
  
  const authenticatedFetch = useCallback(async (
    url: string, 
    options: RequestInit = {}
  ): Promise<Response> => {
    if (!isAuthenticated || !token) {
      throw new Error('Not authenticated')
    }
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
    
    return fetch(url, {
      ...options,
      headers
    })
  }, [token, isAuthenticated])
  
  return authenticatedFetch
}

/**
 * 权限保护的组件Hook
 */
export function useRequireAuth(redirectTo: string = `${getBasePath()}/info?reason=no_token`) {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push(redirectTo)
    }
  }, [isAuthenticated, isLoading, router, redirectTo])
  
  return { isAuthenticated, isLoading }
}

/**
 * 管理员权限保护Hook
 */
export function useRequireAdmin(redirectTo: string = `${getBasePath()}/info?reason=no_permission`) {
  const { isAuthenticated, isLoading, user } = useAuth()
  const router = useRouter()

  // 使用后端返回的is_admin字段
  const isAdmin = user?.is_admin || false

  useEffect(() => {
    if (!isLoading && isAuthenticated && !isAdmin) {
      router.push(redirectTo)
    }
  }, [isAuthenticated, isLoading, isAdmin, router, redirectTo])

  return { isAuthenticated, isLoading, isAdmin }
}