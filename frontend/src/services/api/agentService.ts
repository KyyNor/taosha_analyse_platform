/**
 * Agent API服务
 * 提供Agent对话相关的API调用
 */

import { API_ENDPOINTS, buildApiUrl, API_CONFIG } from '@/config/api'
import { api } from './client'

// 聊天请求接口
export interface ChatRequest {
  message: string
  conversation_history?: Array<{
    role: 'user' | 'assistant'
    content: string
  }>
}

// 聊天响应接口
export interface ChatResponse {
  content: string
  status: string
}

// 流式聊天数据类型
export interface StreamData {
  type: 'start' | 'content' | 'end' | 'error'
  content: string
}

// 健康检查响应
export interface HealthResponse {
  status: string
  service: string
  agent_status: string
  timestamp: string
}

/**
 * Agent API服务类
 */
export class AgentService {
  /**
   * 非流式聊天对话
   */
  async chat(request: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await api.post<ChatResponse>(
        buildApiUrl(API_ENDPOINTS.AGENTS.CHAT),
        request
      )
      return response
    } catch (error) {
      console.error('Chat API error:', error)
      throw error
    }
  }

  /**
   * 流式聊天对话
   * 返回Response对象用于处理Server-Sent Events
   */
  async chatStream(request: ChatRequest): Promise<Response> {
    const url = `${API_CONFIG.BASE_URL}${buildApiUrl(API_ENDPOINTS.AGENTS.CHAT_STREAM)}`

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return response
    } catch (error) {
      console.error('Stream chat API error:', error)
      throw error
    }
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<HealthResponse> {
    try {
      const response = await api.get<HealthResponse>(
        buildApiUrl(API_ENDPOINTS.AGENTS.HEALTH)
      )
      return response
    } catch (error) {
      console.error('Health check API error:', error)
      throw error
    }
  }
}

// 导出单例实例
export const agentService = new AgentService()