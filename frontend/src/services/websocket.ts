/**
 * WebSocket服务 - 处理实时通信
 */
import { ref, reactive } from 'vue'
import type { WebSocketMessage } from '@/types'

export interface WebSocketConfig {
  url: string
  reconnectInterval?: number
  maxReconnectAttempts?: number
  heartbeatInterval?: number
}

export interface WebSocketEventHandlers {
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: Event) => void
  onMessage?: (message: WebSocketMessage) => void
  onTaskUpdate?: (taskId: string, data: any) => void
  onQueryProgress?: (taskId: string, progress: any) => void
  onQueryCompleted?: (taskId: string, result: any) => void
  onQueryError?: (taskId: string, error: any) => void
}

class WebSocketService {
  private ws: WebSocket | null = null
  private config: WebSocketConfig
  private handlers: WebSocketEventHandlers = {}
  private reconnectTimer: number | null = null
  private heartbeatTimer: number | null = null
  private reconnectAttempts = 0
  private isConnecting = false
  private subscribedTasks = new Set<string>()

  // 响应式状态
  public readonly connected = ref(false)
  public readonly connecting = ref(false)
  public readonly lastError = ref<string | null>(null)
  public readonly connectionId = ref<string | null>(null)

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000,
      ...config
    }
  }

  /**
   * 连接WebSocket
   */
  async connect(handlers: WebSocketEventHandlers = {}): Promise<void> {
    if (this.isConnecting || this.connected.value) {
      return
    }

    this.handlers = handlers
    this.isConnecting = true
    this.connecting.value = true
    this.lastError.value = null

    try {
      // 构建WebSocket URL（可以包含认证token）
      const token = this.getAuthToken()
      const wsUrl = token 
        ? `${this.config.url}?token=${encodeURIComponent(token)}`
        : this.config.url

      this.ws = new WebSocket(wsUrl)
      this.setupEventListeners()

      // 等待连接建立
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('WebSocket连接超时'))
        }, 10000)

        this.ws!.onopen = () => {
          clearTimeout(timeout)
          resolve()
        }

        this.ws!.onerror = (error) => {
          clearTimeout(timeout)
          reject(error)
        }
      })

    } catch (error) {
      this.isConnecting = false
      this.connecting.value = false
      this.lastError.value = error instanceof Error ? error.message : '连接失败'
      throw error
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.clearTimers()
    this.reconnectAttempts = 0

    if (this.ws) {
      this.ws.close(1000, '客户端主动断开')
      this.ws = null
    }

    this.connected.value = false
    this.connecting.value = false
    this.connectionId.value = null
    this.subscribedTasks.clear()
  }

  /**
   * 发送消息
   */
  send(message: any): boolean {
    if (!this.connected.value || !this.ws) {
      console.warn('WebSocket未连接，无法发送消息')
      return false
    }

    try {
      this.ws.send(JSON.stringify(message))
      return true
    } catch (error) {
      console.error('发送WebSocket消息失败:', error)
      return false
    }
  }

  /**
   * 订阅任务更新
   */
  subscribeTask(taskId: string): void {
    if (this.subscribedTasks.has(taskId)) {
      return
    }

    this.send({
      type: 'subscribe_task',
      data: { task_id: taskId }
    })

    this.subscribedTasks.add(taskId)
  }

  /**
   * 取消订阅任务更新
   */
  unsubscribeTask(taskId: string): void {
    if (!this.subscribedTasks.has(taskId)) {
      return
    }

    this.send({
      type: 'unsubscribe_task',
      data: { task_id: taskId }
    })

    this.subscribedTasks.delete(taskId)
  }

  /**
   * 发送心跳
   */
  private sendHeartbeat(): void {
    this.send({
      type: 'ping',
      data: { timestamp: Date.now() }
    })
  }

  /**
   * 设置事件监听器
   */
  private setupEventListeners(): void {
    if (!this.ws) return

    this.ws.onopen = () => {
      console.log('WebSocket连接已建立')
      this.isConnecting = false
      this.connecting.value = false
      this.connected.value = true
      this.reconnectAttempts = 0
      this.lastError.value = null

      // 启动心跳
      this.startHeartbeat()

      // 重新订阅之前的任务
      this.subscribedTasks.forEach(taskId => {
        this.send({
          type: 'subscribe_task',
          data: { task_id: taskId }
        })
      })

      this.handlers.onOpen?.()
    }

    this.ws.onclose = (event) => {
      console.log('WebSocket连接已关闭:', event.code, event.reason)
      this.connected.value = false
      this.connecting.value = false
      this.connectionId.value = null
      this.clearTimers()

      this.handlers.onClose?.()

      // 自动重连（除非是主动关闭）
      if (event.code !== 1000 && this.reconnectAttempts < this.config.maxReconnectAttempts!) {
        this.scheduleReconnect()
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket错误:', error)
      this.lastError.value = 'WebSocket连接错误'
      this.handlers.onError?.(error)
    }

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        this.handleMessage(message)
      } catch (error) {
        console.error('解析WebSocket消息失败:', error)
      }
    }
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(message: WebSocketMessage): void {
    // 通用消息处理
    this.handlers.onMessage?.(message)

    // 特定类型消息处理
    switch (message.type) {
      case 'connection_established':
        this.connectionId.value = message.data.connection_id
        break

      case 'task_update':
        if (message.task_id) {
          this.handleTaskUpdate(message.task_id, message.data)
        }
        break

      case 'query_progress':
        if (message.task_id) {
          this.handlers.onQueryProgress?.(message.task_id, message.data)
        }
        break

      case 'query_completed':
        if (message.task_id) {
          this.handlers.onQueryCompleted?.(message.task_id, message.data)
        }
        break

      case 'query_error':
        if (message.task_id) {
          this.handlers.onQueryError?.(message.task_id, message.data)
        }
        break

      case 'system_message':
        console.log('系统消息:', message.data)
        break

      case 'pong':
        // 心跳响应，无需处理
        break

      default:
        console.log('未处理的消息类型:', message.type)
    }
  }

  /**
   * 处理任务更新
   */
  private handleTaskUpdate(taskId: string, data: any): void {
    this.handlers.onTaskUpdate?.(taskId, data)

    // 根据更新类型分发到具体处理器
    switch (data.type) {
      case 'progress_update':
        this.handlers.onQueryProgress?.(taskId, data)
        break
      case 'query_completed':
        this.handlers.onQueryCompleted?.(taskId, data)
        break
      case 'query_error':
        this.handlers.onQueryError?.(taskId, data)
        break
    }
  }

  /**
   * 安排重连
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    this.reconnectAttempts++
    const delay = this.config.reconnectInterval! * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`将在${delay}ms后尝试第${this.reconnectAttempts}次重连`)

    this.reconnectTimer = setTimeout(async () => {
      try {
        await this.connect(this.handlers)
      } catch (error) {
        console.error('重连失败:', error)
      }
    }, delay)
  }

  /**
   * 启动心跳
   */
  private startHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
    }

    this.heartbeatTimer = setInterval(() => {
      this.sendHeartbeat()
    }, this.config.heartbeatInterval!)
  }

  /**
   * 清理定时器
   */
  private clearTimers(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 获取认证token
   */
  private getAuthToken(): string | null {
    // 从localStorage或其他地方获取token
    return localStorage.getItem('auth_token')
  }
}

// 创建全局WebSocket服务实例
const wsUrl = import.meta.env.DEV 
  ? 'ws://localhost:8000/api/v1/ws'
  : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/ws`

export const webSocketService = new WebSocketService({ url: wsUrl })

// 自动连接（可选）
export const useWebSocket = () => {
  return {
    webSocketService,
    connected: webSocketService.connected,
    connecting: webSocketService.connecting,
    lastError: webSocketService.lastError,
    connectionId: webSocketService.connectionId
  }
}