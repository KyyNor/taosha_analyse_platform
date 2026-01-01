/**
 * API调用工具和拦截器
 * 自动处理认证和错误响应
 */

import { useRouter } from 'next/navigation'

// API响应接口
export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
  status: number
}

// API错误类
export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public data?: any
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * 获取token的工具函数
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
  
  // 从localStorage获取
  return localStorage.getItem('auth_token')
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
 * 处理认证错误
 */
function handleAuthError(status: number): void {
  if (typeof window === 'undefined') return
  
  clearToken()
  
  let reason = 'invalid_token'
  if (status === 401) {
    reason = 'expired_token'
  } else if (status === 403) {
    reason = 'no_permission'
  }
  
  window.location.href = `/info?reason=${reason}`
}

/**
 * 基础API调用函数
 */
export async function apiCall<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
  const url = `${baseUrl}${endpoint}`
  
  // 获取token
  const token = getToken()
  
  // 准备请求头
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers
  }
  
  // 添加认证头
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  try {
    const response = await fetch(url, {
      ...options,
      headers
    })
    
    // 处理认证错误
    if (response.status === 401 || response.status === 403) {
      handleAuthError(response.status)
      throw new ApiError(response.status, 'Authentication failed')
    }
    
    // 解析响应
    let data: any
    const contentType = response.headers.get('content-type')
    
    if (contentType && contentType.includes('application/json')) {
      data = await response.json()
    } else {
      data = await response.text()
    }
    
    // 检查响应状态
    if (!response.ok) {
      const errorMessage = data?.detail || data?.message || `HTTP ${response.status}`
      throw new ApiError(response.status, errorMessage, data)
    }
    
    return data
    
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    // 网络错误或其他错误
    console.error('API call failed:', error)
    throw new ApiError(0, 'Network error or server unavailable')
  }
}

/**
 * GET请求
 */
export async function apiGet<T = any>(endpoint: string): Promise<T> {
  return apiCall<T>(endpoint, { method: 'GET' })
}

/**
 * POST请求
 */
export async function apiPost<T = any>(endpoint: string, data?: any): Promise<T> {
  return apiCall<T>(endpoint, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined
  })
}

/**
 * PUT请求
 */
export async function apiPut<T = any>(endpoint: string, data?: any): Promise<T> {
  return apiCall<T>(endpoint, {
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined
  })
}

/**
 * DELETE请求
 */
export async function apiDelete<T = any>(endpoint: string): Promise<T> {
  return apiCall<T>(endpoint, { method: 'DELETE' })
}

/**
 * 文件上传请求
 */
export async function apiUpload<T = any>(
  endpoint: string, 
  formData: FormData
): Promise<T> {
  const token = getToken()
  const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
  const url = `${baseUrl}${endpoint}`
  
  const headers: HeadersInit = {}
  
  // 添加认证头
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData
    })
    
    // 处理认证错误
    if (response.status === 401 || response.status === 403) {
      handleAuthError(response.status)
      throw new ApiError(response.status, 'Authentication failed')
    }
    
    const data = await response.json()
    
    if (!response.ok) {
      const errorMessage = data?.detail || data?.message || `HTTP ${response.status}`
      throw new ApiError(response.status, errorMessage, data)
    }
    
    return data
    
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    console.error('Upload failed:', error)
    throw new ApiError(0, 'Upload failed')
  }
}

/**
 * React Hook for API calls with loading state
 */
export function useApi() {
  const router = useRouter()
  
  const callApi = async <T = any>(
    apiFunction: () => Promise<T>,
    onSuccess?: (data: T) => void,
    onError?: (error: ApiError) => void
  ): Promise<{ data?: T; error?: ApiError }> => {
    try {
      const data = await apiFunction()
      onSuccess?.(data)
      return { data }
    } catch (error) {
      const apiError = error instanceof ApiError ? error : new ApiError(0, 'Unknown error')
      
      // 处理认证错误
      if (apiError.status === 401 || apiError.status === 403) {
        // 错误处理已在apiCall中完成，这里不需要额外处理
        return { error: apiError }
      }
      
      onError?.(apiError)
      return { error: apiError }
    }
  }
  
  return { callApi }
}

/**
 * 权限管理相关的API调用
 */
export const permissionApi = {
  // 获取页面列表
  getPages: () => apiGet('/api/permissions/pages'),
  
  // 同步页面配置
  syncPages: () => apiPost('/api/permissions/pages/sync'),
  
  // 获取实体权限
  getEntityPermissions: (entityId: string) => apiGet(`/api/permissions/entity/${entityId}`),
  
  // 分配权限
  assignPermissions: (entityId: string, pageIds: string[]) => 
    apiPost('/api/permissions/assign', { entity_id: entityId, page_ids: pageIds }),
  
  // 获取权限矩阵
  getPermissionMatrix: () => apiGet('/api/permissions/matrix'),
  
  // 获取权限摘要
  getPermissionSummary: () => apiGet('/api/permissions/summary'),
  
  // 复制权限
  copyPermissions: (sourceEntityId: string, targetEntityId: string) => 
    apiPost(`/api/permissions/copy/${sourceEntityId}/${targetEntityId}`)
}

/**
 * 实体管理相关的API调用
 */
export const entityApi = {
  // 获取实体列表
  getEntities: (type?: 'department' | 'role') => {
    const params = type ? `?entity_type=${type}` : ''
    return apiGet(`/api/entities/${params}`)
  },
  
  // 创建实体
  createEntity: (data: any) => apiPost('/api/entities/', data),
  
  // 更新实体
  updateEntity: (id: string, data: any) => apiPut(`/api/entities/${id}`, data),
  
  // 删除实体
  deleteEntity: (id: string) => apiDelete(`/api/entities/${id}`),
  
  // 获取部门列表
  getDepartments: () => apiGet('/api/entities/departments/'),
  
  // 获取角色列表
  getRoles: () => apiGet('/api/entities/roles/')
}

/**
 * 登录记录相关的API调用
 */
export const loginRecordApi = {
  // 获取登录记录列表
  getLoginRecords: (params?: any) => {
    const queryString = params ? `?${new URLSearchParams(params).toString()}` : ''
    return apiGet(`/api/login-records/${queryString}`)
  },
  
  // 获取当前用户登录记录
  getCurrentUserRecord: () => apiGet('/api/login-records/current/info'),
  
  // 获取登录统计
  getLoginSummary: () => apiGet('/api/login-records/summary/stats'),
  
  // 获取部门登录统计
  getDepartmentStats: (days: number = 30) => apiGet(`/api/login-records/departments/stats?days=${days}`)
}