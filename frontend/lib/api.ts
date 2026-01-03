/**
 * API调用工具和拦截器
 * 自动处理认证和错误响应
 */

import axios from "axios";

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
  
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || ''
  window.location.href = `${basePath}/info?reason=${reason}`
}

// 创建 axios 实例（保持向后兼容）
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE || "/api/taosha/v1"
});

// 请求拦截器：自动添加认证头
api.interceptors.request.use(
  (config) => {
    // 获取token
    const token = getToken()
    
    // 添加认证头
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：处理认证错误
api.interceptors.response.use(
  (res) => res,
  (err) => {
    // 处理认证错误
    if (err.response?.status === 401 || err.response?.status === 403) {
      handleAuthError(err.response.status)
    }
    return Promise.reject(err)
  }
);

export function buildApiUrl(path: string): string {
  const baseURL = process.env.NEXT_PUBLIC_API_BASE || "/api/taosha/v1";
  return `${baseURL}${path}`;
}

// 默认导出 axios 实例（保持向后兼容）
export default api;

// --- History API ---
export interface Session {
  id: string;
  title: string | null;
  updated_at: string;
}

export interface MessageResponse {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  type: string;
  created_at: string;
  meta_info?: any;
}

export const chatApi = {
  getHistory: async (userId: string) => {
    const res = await api.get<Session[]>(`/agents/history`, { params: { user_id: userId } });
    return res.data;
  },

  getSessionMessages: async (sessionId: string) => {
    const res = await api.get<MessageResponse[]>(`/agents/history/${sessionId}`);
    return res.data;
  },

  deleteSession: async (sessionId: string, userId: string) => {
    await api.delete(`/agents/history/${sessionId}`, { params: { user_id: userId } });
  },

  createSession: async (userId: string) => {
    const res = await api.post<Session>(`/agents/history`, { user_id: userId });
    return res.data;
  }
};

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
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers as Record<string, string>
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
  
  const headers: Record<string, string> = {}
  
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
  getPages: async () => {
    const res = await api.get('/permissions/pages')
    return res.data
  },
  
  // 同步页面配置
  syncPages: async () => {
    const res = await api.post('/permissions/pages/sync')
    return res.data
  },
  
  // 获取实体权限
  getEntityPermissions: async (entityId: string) => {
    const res = await api.get(`/permissions/entity/${entityId}`)
    return res.data
  },
  
  // 分配权限
  assignPermissions: async (entityId: string, pageIds: string[]) => {
    const res = await api.post('/permissions/assign', { entity_id: entityId, page_ids: pageIds })
    return res.data
  },
  
  // 获取权限矩阵
  getPermissionMatrix: async () => {
    const res = await api.get('/permissions/matrix')
    return res.data
  },
  
  // 获取权限摘要
  getPermissionSummary: async () => {
    const res = await api.get('/permissions/summary')
    return res.data
  },
  
  // 复制权限
  copyPermissions: async (sourceEntityId: string, targetEntityId: string) => {
    const res = await api.post(`/permissions/copy/${sourceEntityId}/${targetEntityId}`)
    return res.data
  }
}

/**
 * 实体管理相关的API调用
 */
export const entityApi = {
  // 获取实体列表
  getEntities: async (type?: 'department' | 'role') => {
    const res = await api.get('/entities/', { params: type ? { entity_type: type } : undefined })
    return res.data
  },
  
  // 创建实体
  createEntity: async (data: any) => {
    const res = await api.post('/entities/', data)
    return res.data
  },
  
  // 更新实体
  updateEntity: async (id: string, data: any) => {
    const res = await api.put(`/entities/${id}`, data)
    return res.data
  },
  
  // 删除实体
  deleteEntity: async (id: string) => {
    const res = await api.delete(`/entities/${id}`)
    return res.data
  },
  
  // 获取部门列表
  getDepartments: async () => {
    const res = await api.get('/entities/departments/')
    return res.data
  },
  
  // 获取角色列表
  getRoles: async () => {
    const res = await api.get('/entities/roles/')
    return res.data
  }
}

/**
 * 登录记录相关的API调用
 */
export const loginRecordApi = {
  // 获取登录记录列表
  getLoginRecords: async (params?: any) => {
    const res = await api.get('/login-records/', { params })
    return res.data
  },
  
  // 获取当前用户登录记录
  getCurrentUserRecord: async () => {
    const res = await api.get('/login-records/current/info')
    return res.data
  },
  
  // 获取登录统计
  getLoginSummary: async () => {
    const res = await api.get('/login-records/summary/stats')
    return res.data
  },
  
  // 获取部门登录统计
  getDepartmentStats: async (days: number = 30) => {
    const res = await api.get('/login-records/departments/stats', { params: { days } })
    return res.data
  }
}