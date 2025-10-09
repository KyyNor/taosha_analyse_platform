import { api, wsManager, type WebSocketManager } from './client'
import type {
  QueryRequest,
  QuerySubmitResponse,
  QueryHistoryResponse,
  Favorite,
  FavoritesResponse,
  AddFavoriteRequest,
  UpdateFavoriteRequest,
  FeedbackRequest,
  QueryLog,
  PaginatedResponse
} from '@types/index'

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
    return await api.post('/query/submit', request)
  }

  // Cancel query
  async cancelTask(taskId: string): Promise<void> {
    await api.post(`/query/cancel/${taskId}`)
  }

  // Rerun query
  async rerunQuery(taskId: string): Promise<QuerySubmitResponse> {
    return await api.post(`/query/rerun/${taskId}`)
  }

  // Get query progress
  async getQueryProgress(taskId: string): Promise<any> {
    return await api.get(`/query/progress/${taskId}`)
  }

  // Get query history
  async getQueryHistory(
    page: number = 1,
    pageSize: number = 20,
    filters: {
      status?: string
      startTime?: string
      endTime?: string
    } = {}
  ): Promise<PaginatedResponse<QueryLog>> {
    const params = new URLSearchParams({
      page: page.toString(),
      pageSize: pageSize.toString(),
      ...filters
    })

    return await api.get(`/query/history?${params}`)
  }

  // Export query results
  async exportResults(taskId: string, format: 'csv' | 'xlsx'): Promise<Blob> {
    const response = await api.getRaw(`/query/export/${taskId}?format=${format}`)
    return response.data
  }

  // Submit feedback
  async submitFeedback(taskId: string, type: 'positive' | 'negative' | 'neutral', content?: string): Promise<void> {
    const request: FeedbackRequest = { type, content }
    await api.post(`/query/feedback/${taskId}`, request)
  }

  // Subscribe to task progress updates
  subscribeToTaskProgress(taskId: string, handler: (data: any) => void): void {
    this.ws.onMessage(`task_${taskId}`, handler)
  }

  // Unsubscribe from task progress updates
  unsubscribeFromTaskProgress(taskId: string): void {
    // Note: We need to implement unsubscribe method in WebSocketManager
    // For now, we'll leave this as a placeholder
  }

  // Favorites management
  async getFavorites(page: number = 1, pageSize: number = 20): Promise<FavoritesResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      pageSize: pageSize.toString()
    })

    return await api.get(`/favorites?${params}`)
  }

  async addToFavorites(taskId: string, title: string): Promise<void> {
    const request: AddFavoriteRequest = { taskId, title }
    await api.post('/favorites', request)
  }

  async updateFavorite(favoriteId: number, title: string): Promise<void> {
    const request: UpdateFavoriteRequest = { title }
    await api.put(`/favorites/${favoriteId}`, request)
  }

  async deleteFavorite(favoriteId: number): Promise<void> {
    await api.delete(`/favorites/${favoriteId}`)
  }

  async executeFavorite(favoriteId: number): Promise<QuerySubmitResponse> {
    return await api.post(`/favorites/${favoriteId}/execute`)
  }
}

export default new QueryService()
