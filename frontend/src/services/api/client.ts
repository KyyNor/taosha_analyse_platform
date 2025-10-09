import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type AxiosError
} from 'axios'
import type { ApiResponse } from '@types/index'
import {
  API_CONFIG,
  API_ENDPOINTS,
  WS_ENDPOINTS,
  buildApiUrl,
  replaceUrlParams,
  buildWsUrl
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
    return responseData.data || responseData as T
  },

  post: async <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    const response = await apiClient.post<ApiResponse<T>>(url, data, config)
    // Handle both nested data format (response.data.data) and direct data format (response.data)
    const responseData = response.data as any
    return responseData.data || responseData as T
  },

  put: async <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    const response = await apiClient.put<ApiResponse<T>>(url, data, config)
    // Handle both nested data format (response.data.data) and direct data format (response.data)
    const responseData = response.data as any
    return responseData.data || responseData as T
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

// WebSocket utility
export class WebSocketManager {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = API_CONFIG.RETRY.DELAY
  private messageHandlers: Map<string, (data: any) => void> = new Map()
  private connectionHandlers: { onOpen?: () => void; onClose?: () => void; onError?: (error: Event) => void } = {}

  constructor(endpoint: string = WS_ENDPOINTS.TASK_PROGRESS) {
    this.url = buildWsUrl(endpoint)
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = (event) => {
          console.log('[WebSocket] Connected', this.url)
          this.reconnectAttempts = 0
          this.connectionHandlers.onOpen?.()
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data)
            console.log('[WebSocket] Message received', message)

            // Handle task progress messages (backend sends {code: 0, data: {...}})
            if (message.code === 0 && message.data && message.data.task_id) {
              const taskId = message.data.task_id
              // Call task-specific handler
              if (this.messageHandlers.has(`task_${taskId}`)) {
                this.messageHandlers.get(`task_${taskId}`)?.(message.data)
              }
            }

            // Call registered message handlers for messages with type
            if (message.type && this.messageHandlers.has(message.type)) {
              this.messageHandlers.get(message.type)?.(message.data)
            }

            // Call default handler if registered
            if (this.messageHandlers.has('*')) {
              this.messageHandlers.get('*')?.(message)
            }
          } catch (error) {
            console.error('[WebSocket] Error parsing message', error)
          }
        }

        this.ws.onclose = (event) => {
          console.log('[WebSocket] Disconnected', { code: event.code, reason: event.reason })
          this.connectionHandlers.onClose?.()

          // Attempt to reconnect if not a normal closure
          if (event.code !== 1000 && this.reconnectAttempts < API_CONFIG.RETRY.MAX_ATTEMPTS) {
            setTimeout(() => {
              this.reconnectAttempts++
              console.log(`[WebSocket] Reconnecting... (${this.reconnectAttempts}/${API_CONFIG.RETRY.MAX_ATTEMPTS})`)
              this.connect()
            }, this.reconnectDelay * this.reconnectAttempts)
          }
        }

        this.ws.onerror = (error) => {
          console.error('[WebSocket] Error', error)
          this.connectionHandlers.onError?.(error)
          reject(error)
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
  }

  send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('[WebSocket] Cannot send message, connection not ready')
    }
  }

  onMessage(type: string, handler: (data: any) => void): void {
    this.messageHandlers.set(type, handler)
  }

  onConnection(handlers: { onOpen?: () => void; onClose?: () => void; onError?: (error: Event) => void }): void {
    this.connectionHandlers = handlers
  }

  getConnectionState(): 'connecting' | 'open' | 'closing' | 'closed' {
    if (!this.ws) return 'closed'
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting'
      case WebSocket.OPEN: return 'open'
      case WebSocket.CLOSING: return 'closing'
      case WebSocket.CLOSED: return 'closed'
      default: return 'closed'
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

// Export singleton WebSocket manager
export const wsManager = new WebSocketManager()

export default api
