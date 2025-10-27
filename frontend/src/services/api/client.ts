import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type AxiosError
} from 'axios'
import type { ApiResponse } from '@/types/index'
import {
  API_CONFIG
} from '@/config/api'

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // Add request timestamp
    config.metadata = { startTime: new Date() }

    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
      params: config.params,
      data: config.data
    })

    return config
  },
  (error: AxiosError) => {
    console.error('[API Request Error]', error)
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    const endTime = new Date()
    const startTime = response.config.metadata?.startTime
    const duration = startTime ? endTime.getTime() - startTime.getTime() : 0

    console.log(
      `[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`,
      {
        status: response.status,
        duration: `${duration}ms`,
        data: response.data
      }
    )

    return response
  },
  (error: AxiosError) => {
    console.error('[API Response Error]', {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
      data: error.response?.data
    })

    // Handle common error scenarios
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      localStorage.removeItem('access_token')
      window.location.href = '/login'
      return Promise.reject(new Error('认证失败，请重新登录'))
    }

    if (error.response?.status === 403) {
      return Promise.reject(new Error('权限不足，无法访问该资源'))
    }

    if (error.response?.status === 404) {
      return Promise.reject(new Error('请求的资源不存在'))
    }

    if (error.response?.status === 500) {
      return Promise.reject(new Error('服务器内部错误，请稍后重试'))
    }

    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('请求超时，请检查网络连接'))
    }

    // Handle network errors
    if (!error.response) {
      return Promise.reject(new Error('网络连接失败，请检查网络设置'))
    }

    // Return error message from server if available
    const errorMessage = (error.response.data as any)?.error || error.message
    return Promise.reject(new Error(errorMessage))
  }
)

// Extend AxiosRequestConfig type to include metadata
declare module 'axios' {
  interface AxiosRequestConfig {
    metadata?: {
      startTime: Date
    }
  }
}

// API wrapper functions
export const api = {
  get: async <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    const response = await apiClient.get<ApiResponse<T>>(url, config)
    // Handle both nested data format (response.data.data) and direct data format (response.data)
    const responseData = response.data as any
    return responseData
  },

  post: async <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    const response = await apiClient.post<ApiResponse<T>>(url, data, config)
    // Handle both nested data format (response.data.data) and direct data format (response.data)
    const responseData = response.data as any
    return responseData
  },

  put: async <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    const response = await apiClient.put<ApiResponse<T>>(url, data, config)
    // Handle both nested data format (response.data.data) and direct data format (response.data)
    const responseData = response.data as any
    return responseData
  },

  delete: async <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    const response = await apiClient.delete<ApiResponse<T>>(url, config)
    // Handle both nested data format (response.data.data) and direct data format (response.data)
    const responseData = response.data as any
    return responseData.data || responseData as T
  },

  // Raw response access for special cases
  getRaw: async (url: string, config?: AxiosRequestConfig): Promise<AxiosResponse> => {
    return apiClient.get(url, config)
  },

  postRaw: async (url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse> => {
    return apiClient.post(url, data, config)
  }
}

// 长轮询管理器
export class PollingManager {
  private pollingIntervals: Map<string, ReturnType<typeof setTimeout>> = new Map()
  private lastUpdateTime: Map<string, string> = new Map()
  private messageHandlers: Map<string, (data: any) => void> = new Map()
  private pollInterval = 2000  // 轮询间隔：2秒
  private serverTimeout = 30    // 服务端等待时间：30秒
  private maxRetries = 5        // 最大重试次数：5次
  private abortControllers: Map<string, AbortController> = new Map()

  /**
   * 订阅任务进度（自动启动长轮询）
   */
  async subscribeToTaskProgress(
    taskId: string,
    handler: (data: any) => void,
    options?: {
      pollInterval?: number
      serverTimeout?: number
      maxRetries?: number
    }
  ): Promise<void> {
    const mergedOptions = {
      pollInterval: options?.pollInterval ?? this.pollInterval,
      serverTimeout: options?.serverTimeout ?? this.serverTimeout,
      maxRetries: options?.maxRetries ?? this.maxRetries
    }

    this.messageHandlers.set(`task_${taskId}`, handler)
    console.log(`[Polling] 开始订阅任务进度: ${taskId}`)

    // 如果已在轮询则停止
    if (this.pollingIntervals.has(taskId)) {
      this.unsubscribe(taskId)
    }

    // 启动长轮询
    await this.startPolling(taskId, mergedOptions)
  }

  /**
   * 启动长轮询
   */
  private async startPolling(
    taskId: string,
    options: {
      pollInterval: number
      serverTimeout: number
      maxRetries: number
    }
  ): Promise<void> {
    let retryCount = 0

    const poll = async () => {
      try {
        // 构建请求URL
        const lastUpdate = this.lastUpdateTime.get(taskId)
        const params = new URLSearchParams({
          timeout: String(options.serverTimeout)
        })
        if (lastUpdate) {
          params.append('last_update_time', lastUpdate)
        }

        const url = `${API_CONFIG.BASE_URL}/api/taosha/v1/nlquery/progress/${taskId}?${params}`

        // 创建AbortController用于超时控制
        const abortController = new AbortController()
        const clientTimeout = (options.serverTimeout + 15) * 1000  // 客户端超时：45秒
        const timeoutId = setTimeout(() => abortController.abort(), clientTimeout)
        this.abortControllers.set(taskId, abortController)

        console.log(`[Polling] 发送请求: ${taskId} (重试: ${retryCount}/${options.maxRetries})`)

        // 发起HTTP请求（使用axios）
        const response = await apiClient.get(url, {
          signal: abortController.signal
        })

        clearTimeout(timeoutId)

        if (response.status !== 200) {
          throw new Error(`HTTP ${response.status}`)
        }

        const responseData = response.data
        const taskData = responseData.data || responseData
        retryCount = 0  // 重置重试计数

        // 更新时间戳
        if (taskData?.update_time) {
          this.lastUpdateTime.set(taskId, taskData.update_time)
        }

        // 调用处理器
        const handler = this.messageHandlers.get(`task_${taskId}`)
        if (handler) {
          handler(taskData)
        }

        // 如果任务完成则停止轮询
        if (taskData?.complete) {
          console.log(`[Polling] 任务完成，停止轮询: ${taskId}`)
          this.unsubscribe(taskId)
          return
        }

        // 继续下一轮轮询（等待pollInterval后）
        const interval = setTimeout(poll, options.pollInterval)
        this.pollingIntervals.set(taskId, interval)

      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error)

        // 检查是否超时
        if (errorMsg.includes('aborted') || errorMsg.includes('timeout')) {
          console.warn(`[Polling] 请求超时: ${taskId}, 继续轮询...`)
          retryCount = 0  // 超时不计入重试次数
        } else {
          // 处理其他错误
          if (retryCount < options.maxRetries) {
            retryCount++
            console.warn(`[Polling] 请求失败 (${retryCount}/${options.maxRetries}): ${errorMsg}`)
          } else {
            console.error(`[Polling] 达到最大重试次数，停止轮询: ${taskId}`)
            this.unsubscribe(taskId)

            // 通知错误给处理器
            const handler = this.messageHandlers.get(`task_${taskId}`)
            if (handler) {
              handler({
                error: '轮询连接失败，请检查网络',
                status: 'failed'
              })
            }
            return
          }
        }

        // 继续下一轮轮询
        const interval = setTimeout(poll, options.pollInterval)
        this.pollingIntervals.set(taskId, interval)
      }
    }

    // 立即执行第一次轮询
    await poll()
  }

  /**
   * 取消订阅
   */
  unsubscribe(taskId: string): void {
    const interval = this.pollingIntervals.get(taskId)
    if (interval) {
      clearTimeout(interval)
      this.pollingIntervals.delete(taskId)
    }

    const controller = this.abortControllers.get(taskId)
    if (controller) {
      controller.abort()
      this.abortControllers.delete(taskId)
    }

    this.messageHandlers.delete(`task_${taskId}`)
    this.lastUpdateTime.delete(taskId)
    console.log(`[Polling] 已取消订阅: ${taskId}`)
  }

  /**
   * 检查是否正在轮询
   */
  isPolling(taskId: string): boolean {
    return this.pollingIntervals.has(taskId)
  }

  /**
   * 停止所有轮询
   */
  stopAll(): void {
    for (const taskId of Array.from(this.pollingIntervals.keys())) {
      this.unsubscribe(taskId)
    }
    console.log('[Polling] 已停止所有轮询')
  }
}

// Export singleton polling manager
export const wsManager = new PollingManager()

export default api
