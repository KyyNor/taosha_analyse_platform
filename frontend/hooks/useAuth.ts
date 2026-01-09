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
}

// 权限检查结果接口
export interface PermissionResult {
  hasPermission: boolean
  loading: boolean
  error?: string
}

/**
 * 获取token的工具函数（简化版：只从cookie和localStorage获取）
 */
function getToken(): string | null {
  if (typeof window === 'undefined') return null
  
  // 优先从cookie获取
  const cookies = document.cookie.split(';')
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=')
    if (name === 'auth_token') {
      return decodeURIComponent(value)
    }
  }
  
  // 备用：从localStorage获取
  return localStorage.getItem('auth_token')
}

/**
 * 设置token的工具函数
 */
function setToken(token: string): void {
  if (typeof window === 'undefined') return
  
  // 设置cookie（7天过期）
  const expires = new Date()
  expires.setDate(expires.getDate() + 7)
  document.cookie = `auth_token=${encodeURIComponent(token)}; expires=${expires.toUTCString()}; path=/`
  
  // 设置localStorage
  localStorage.setItem('auth_token', token)
}

/**
 * 清除token的工具函数
 */
function clearToken(): void {
  if (typeof window === 'undefined') return
  
  // 清除cookie
  document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
  
  // 清除localStorage
  localStorage.removeItem('auth_token')
  localStorage.removeItem('user_info')
}

/**
 * 验证token并获取用户信息
 */
async function validateTokenAndGetUser(token: string): Promise<{ valid: boolean; userInfo?: UserInfo }> {
  try {
    // 使用临时axios实例，手动设置token
    const response = await api.get('/login-records/current/info', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    const data = response.data
    return {
      valid: true,
      userInfo: {
        user_id: data.user_id,
        user_name: data.user_name,
        branch_no: data.branch_no,
        branch_name: data.branch_name,
        role_id_list: data.role_id_list,
        role_name_list: data.role_name_list,
        is_admin: data.is_admin || false
      }
    }

  } catch (error) {
    console.error('Token validation error:', error)
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
    token: null
  })
  
  const router = useRouter()
  
  // 初始化认证状态
  useEffect(() => {
    const initAuth = async () => {
      const token = getToken()
      
      if (!token) {
        setAuthState({
          isAuthenticated: false,
          isLoading: false,
          user: null,
          token: null
        })
        return
      }
      
      const validation = await validateTokenAndGetUser(token)
      
      if (validation.valid && validation.userInfo) {
        setAuthState({
          isAuthenticated: true,
          isLoading: false,
          user: validation.userInfo,
          token
        })
      } else {
        // Token无效，清除并重定向
        clearToken()
        setAuthState({
          isAuthenticated: false,
          isLoading: false,
          user: null,
          token: null
        })
        router.push(`${getBasePath()}/info?reason=invalid_token`)
      }
    }
    
    initAuth()
  }, [router])
  
  // 登录函数
  const login = useCallback(async (token: string): Promise<boolean> => {
    const validation = await validateTokenAndGetUser(token)
    
    if (validation.valid && validation.userInfo) {
      setToken(token)
      setAuthState({
        isAuthenticated: true,
        isLoading: false,
        user: validation.userInfo,
        token
      })
      return true
    }
    
    return false
  }, [])
  
  // 登出函数
  const logout = useCallback(() => {
    clearToken()
    setAuthState({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      token: null
    })
    router.push(`${getBasePath()}/info?reason=no_token`)
  }, [router])
  
  // 刷新认证状态
  const refreshAuth = useCallback(async () => {
    const token = getToken()
    
    if (!token) {
      logout()
      return
    }
    
    const validation = await validateTokenAndGetUser(token)
    
    if (validation.valid && validation.userInfo) {
      setAuthState(prev => ({
        ...prev,
        user: validation.userInfo!,
        token
      }))
    } else {
      logout()
    }
  }, [logout])
  
  // 检查是否为管理员（完全依赖后端返回的is_admin字段）
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