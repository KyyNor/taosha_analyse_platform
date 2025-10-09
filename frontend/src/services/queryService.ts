import { api, wsManager } from './api/client'
import type {
  QueryRequest,
  QueryTask,
  QueryResult,
  Favorite,
  Feedback,
  LogFilter,
  PaginatedResponse,
  QueryLog
} from '@types/index'

class QueryService {
  // Submit a natural language query
  async submitQuery(request: QueryRequest): Promise<{ taskId: string }> {
    return await api.post('/nlquery/submit', request)
  }

  // Get task result by ID
  async getTaskResult(taskId: string): Promise<QueryTask> {
    return await api.get(`/nlquery/result/${taskId}`)
  }

  // Subscribe to task progress updates via WebSocket
  subscribeToTaskProgress(taskId: string, callback: (data: any) => void): void {
    wsManager.send(taskId) // Send task ID to subscribe
    wsManager.onMessage('progress', callback)
  }

  // Cancel a running task
  async cancelTask(taskId: string): Promise<void> {
    return await api.post(`/nlquery/cancel/${taskId}`)
  }

  // Rerun a previous query
  async rerunQuery(taskId: string): Promise<{ taskId: string }> {
    return await api.post(`/nlquery/rerun/${taskId}`)
  }

  // Export query results
  async exportResults(taskId: string, format: 'xlsx' | 'csv'): Promise<Blob> {
    const response = await api.getRaw(`/nlquery/export/${taskId}`, {
      params: { format },
      responseType: 'blob'
    })
    return response.data
  }

  // Get query history
  async getQueryHistory(
    page: number = 1,
    pageSize: number = 20,
    filters?: LogFilter
  ): Promise<PaginatedResponse<QueryLog>> {
    return await api.get('/nlquery/history', {
      params: { page, pageSize, ...filters }
    })
  }

  // Get query log details
  async getQueryLogDetails(taskId: string): Promise<QueryLog> {
    return await api.get(`/nlquery/logs/${taskId}`)
  }

  // === Favorites Management ===

  // Add query to favorites
  async addToFavorites(taskId: string, title: string): Promise<{ favoriteId: number }> {
    return await api.post('/nlquery/favorite', {
      taskId,
      favoriteTitle: title
    })
  }

  // Get user's favorites
  async getFavorites(page: number = 1, pageSize: number = 20): Promise<PaginatedResponse<Favorite>> {
    return await api.get('/nlquery/favorite', {
      params: { page, pageSize }
    })
  }

  // Update favorite title
  async updateFavorite(favoriteId: number, title: string): Promise<void> {
    return await api.post(`/nlquery/favorite/${favoriteId}/update`, {
      favoriteTitle: title
    })
  }

  // Delete favorite
  async deleteFavorite(favoriteId: number): Promise<void> {
    return await api.post(`/nlquery/favorite/${favoriteId}/delete`)
  }

  // Execute favorite query
  async executeFavorite(favoriteId: number): Promise<{ taskId: string }> {
    return await api.post(`/nlquery/favorite/${favoriteId}/execute`)
  }

  // === Feedback Management ===

  // Submit feedback for a query
  async submitFeedback(taskId: string, type: 'positive' | 'negative' | 'neutral', content?: string): Promise<void> {
    return await api.post('/nlquery/feedback', {
      taskId,
      feedbackType: type,
      feedbackContent: content
    })
  }

  // Get all feedback (admin only)
  async getFeedback(
    page: number = 1,
    pageSize: number = 20,
    type?: string
  ): Promise<PaginatedResponse<Feedback>> {
    return await api.get('/nlquery/feedback', {
      params: { page, pageSize, feedbackType: type }
    })
  }

  // === Query Suggestions ===

  // Get popular queries
  async getPopularQueries(limit: number = 10): Promise<Array<{ query: string; count: number }>> {
    return await api.get('/nlquery/popular', {
      params: { limit }
    })
  }

  // Get query suggestions based on input
  async getQuerySuggestions(input: string, limit: number = 5): Promise<string[]> {
    return await api.get('/nlquery/suggestions', {
      params: { q: input, limit }
    })
  }

  // === Data Export ===

  // Export query data in various formats
  async exportQueryData(
    taskId: string,
    format: 'xlsx' | 'csv' | 'json',
    options?: {
      includeHeaders?: boolean
      maxRows?: number
    }
  ): Promise<Blob> {
    const response = await api.getRaw(`/nlquery/export/${taskId}`, {
      params: { format, ...options },
      responseType: 'blob'
    })
    return response.data
  }

  // === Statistics ===

  // Get query statistics
  async getQueryStats(timeRange?: '7d' | '30d' | '90d'): Promise<{
    totalQueries: number
    successRate: number
    avgResponseTime: number
    popularQueries: Array<{ query: string; count: number }>
    errorTypes: Array<{ type: string; count: number }>
  }> {
    return await api.get('/nlquery/stats', {
      params: { timeRange }
    })
  }

  // === Batch Operations ===

  // Batch delete queries
  async batchDeleteQueries(taskIds: string[]): Promise<void> {
    return await api.post('/nlquery/batch-delete', { taskIds })
  }

  // Batch add to favorites
  async batchAddToFavorites(taskIds: string[], titlePrefix: string = 'Batch'): Promise<void> {
    return await api.post('/nlquery/batch-favorite', {
      taskIds,
      titlePrefix
    })
  }

  // === WebSocket Management ===

  // Initialize WebSocket connection
  async initializeWebSocket(): Promise<void> {
    if (!wsManager.isConnected()) {
      await wsManager.connect()
    }
  }

  // Disconnect WebSocket
  disconnectWebSocket(): void {
    wsManager.disconnect()
  }

  // Check WebSocket connection status
  isWebSocketConnected(): boolean {
    return wsManager.isConnected()
  }
}

export default new QueryService()
