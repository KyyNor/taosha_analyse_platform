import { api, wsManager, type WebSocketManager } from './client'
import { API_ENDPOINTS, buildApiUrl, replaceUrlParams } from '@/config/api'
import type {
  QueryRequest,
  QueryTask,
  BaseNodeLog,
  ClarificationResponse,
  QuerySubmitResponse,
  FavoritesResponse,
  AddFavoriteRequest,
  UpdateFavoriteRequest,
  FeedbackRequest
} from '@/types/index'

class QueryService {
  private ws: WebSocketManager

  constructor() {
    this.ws = wsManager
  }

  // Initialize WebSocket connection
  async initializeWebSocket(): Promise<void> {
    if (!this.ws.isConnected()) {
      await this.ws.connect()
    }
  }

  // Disconnect WebSocket
  disconnectWebSocket(): void {
    this.ws.disconnect()
  }

  // Submit query
  async submitQuery(request: QueryRequest): Promise<QuerySubmitResponse> {
    return await api.post(buildApiUrl(API_ENDPOINTS.NL_QUERY.SUBMIT), request)
  }

  // Cancel query
  async cancelTask(taskId: string): Promise<void> {
    const url = replaceUrlParams(API_ENDPOINTS.NL_QUERY.CANCEL, { taskId })
    await api.post(buildApiUrl(url))
  }

  // Rerun query
  async rerunQuery(taskId: string): Promise<QuerySubmitResponse> {
    const url = replaceUrlParams(API_ENDPOINTS.NL_QUERY.RERUN, { taskId })
    return await api.post(buildApiUrl(url))
  }

  // Get query progress
  async getQueryProgress(taskId: string): Promise<any> {
    const url = replaceUrlParams(API_ENDPOINTS.NL_QUERY.PROGRESS, { taskId })
    return await api.get(buildApiUrl(url))
  }

  // Get query history
  async getQueryHistory(
    page: number = 1,
    pageSize: number = 20,
    filters: {
      status?: string
    } = {}
  ): Promise<{
      success: boolean
      data: QueryTask[]
      pagination: {
        page: number
        pageSize: number
        total: number
        totalPages: number
      }
    }> {
    const params = {
      page: page.toString(),
      page_size: pageSize.toString(),
      ...filters
    }

    return await api.get(buildApiUrl(API_ENDPOINTS.NL_QUERY.HISTORY, params))
  }

  // Get query history detail
  async getQueryHistoryDetail(taskId: string): Promise<{
      success: boolean
      data: QueryTask
      logs: BaseNodeLog[]
    }> {
    const url = replaceUrlParams(API_ENDPOINTS.NL_QUERY.HISTORY_DETAIL, { taskId })
    return await api.get(buildApiUrl(url))
  }

  // Submit feedback
  async submitFeedback(taskId: string, type: 'positive' | 'negative' | 'neutral', content?: string): Promise<void> {
    const request: FeedbackRequest = { type, content }
    const url = replaceUrlParams(API_ENDPOINTS.NL_QUERY.FEEDBACK, { taskId })
    await api.post(buildApiUrl(url), request)
  }

  // Subscribe to task progress updates
  subscribeToTaskProgress(taskId: string, handler: (data: any) => void): void {
    // Register handler for task-specific messages
    this.ws.onMessage(`task_${taskId}`, handler)

    // Send task_id to server to subscribe to this task's progress
    this.ws.send(taskId)

    console.log(`[WebSocket] Subscribed to task progress for task: ${taskId}`)
  }


  // Favorites management
  async getFavorites(page: number = 1, pageSize: number = 20): Promise<FavoritesResponse> {
    const params = {
      page: page.toString(),
      pageSize: pageSize.toString()
    }

    return await api.get(buildApiUrl(API_ENDPOINTS.FAVORITES.LIST, params))
  }

  async addToFavorites(taskId: string, title: string): Promise<void> {
    const request: AddFavoriteRequest = { taskId, title }
    await api.post(buildApiUrl(API_ENDPOINTS.FAVORITES.CREATE), request)
  }

  async updateFavorite(favoriteId: number, title: string): Promise<void> {
    const request: UpdateFavoriteRequest = { title }
    const url = replaceUrlParams(API_ENDPOINTS.FAVORITES.UPDATE, { id: favoriteId })
    await api.put(buildApiUrl(url), request)
  }

  async deleteFavorite(favoriteId: number): Promise<void> {
    const url = replaceUrlParams(API_ENDPOINTS.FAVORITES.DELETE, { id: favoriteId })
    await api.delete(buildApiUrl(url))
  }

  async executeFavorite(favoriteId: number): Promise<QuerySubmitResponse> {
    const url = replaceUrlParams(API_ENDPOINTS.FAVORITES.EXECUTE, { id: favoriteId })
    return await api.post(buildApiUrl(url))
  }

  // 提交澄清输入
  async submitClarification(
    taskId: string,
    clarification: string,
    clarificationOptions?: string[],
    optionIndex?: number
  ): Promise<ClarificationResponse> {
    // 构建澄清输入内容
    let clarificationInput = ''

    // 如果有选项索引，获取选项文字
    if (optionIndex !== undefined && optionIndex >= 0 && clarificationOptions && clarificationOptions[optionIndex]) {
      clarificationInput = clarificationOptions[optionIndex]
    }

    // 如果用户也输入了文字，将选项文字和用户输入拼接起来
    if (clarification.trim()) {
      clarificationInput = clarificationInput ? `${clarificationInput}：${clarification}` : clarification
    }

    const request = {
      clarification_input: clarificationInput
    }

    const url = replaceUrlParams(API_ENDPOINTS.NL_QUERY.CLARIFICATION, { taskId })
    return await api.post(buildApiUrl(url), request)
  }
}

export default new QueryService()
