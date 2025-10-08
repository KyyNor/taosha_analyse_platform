/**
 * 查询相关的API接口
 */
import { apiClient } from './client'
import type { ApiResponse, PaginatedResponse } from './client'

// 查询任务相关类型
export interface QueryTaskCreate {
  user_question: string
  query_type?: string
  selected_theme_id?: number
  selected_table_ids?: number[]
}

export interface QueryTaskStatus {
  task_id: string
  status: string
  current_step?: string
  progress_percentage: number
  error_message?: string
  created_at: string
  updated_at: string
}

export interface QueryTaskResult {
  task_id: string
  status: string
  user_question?: string
  generated_sql?: string
  final_sql?: string
  execution_result?: any
  result_row_count?: number
  result_columns?: string[]
  result_data?: any[][]
  error_message?: string
  llm_tokens_used?: number
  node_execution_log?: any[]
  pagination?: {
    page: number
    size: number
    total: number
    pages: number
  }
}

export interface QuerySuggestion {
  question: string
  similarity: number
  category: string
}

export interface QueryHistoryItem {
  id: number
  user_id: number
  task_id: string
  user_question: string
  generated_sql?: string
  task_status: string
  result_row_count?: number
  execution_time_ms?: number
  tags?: string[]
  category?: string
  access_count: number
  last_accessed_at?: string
  created_at: string
}

export interface QueryFavorite {
  id: number
  user_id: number
  favorite_title: string
  favorite_description?: string
  user_question: string
  generated_sql?: string
  folder_name?: string
  tags: string[]
  usage_count: number
  last_used_at?: string
  created_at: string
}

export interface QueryStatistics {
  total_queries: number
  successful_queries: number
  failed_queries: number
  success_rate: number
  avg_execution_time_ms: number
  most_used_tables: any[]
  popular_questions: any[]
  daily_query_counts: any[]
}

// 查询API类
export class QueryAPI {
  
  /**
   * 提交查询任务
   */
  static async submitQuery(data: QueryTaskCreate): Promise<ApiResponse<any>> {
    return apiClient.post('/nlquery/submit', data)
  }

  /**
   * 获取查询任务状态
   */
  static async getQueryStatus(taskId: string): Promise<ApiResponse<QueryTaskStatus>> {
    return apiClient.get(`/nlquery/status/${taskId}`)
  }

  /**
   * 获取查询任务结果
   */
  static async getQueryResult(
    taskId: string, 
    page: number = 1, 
    size: number = 20
  ): Promise<ApiResponse<QueryTaskResult>> {
    return apiClient.get(`/nlquery/result/${taskId}`, {
      params: { page, size }
    })
  }

  /**
   * 取消查询任务
   */
  static async cancelQuery(taskId: string): Promise<ApiResponse<any>> {
    return apiClient.post(`/nlquery/cancel/${taskId}`)
  }

  /**
   * 获取查询建议
   */
  static async getQuerySuggestions(
    query: string, 
    limit: number = 5
  ): Promise<ApiResponse<QuerySuggestion[]>> {
    return apiClient.get('/nlquery/suggestions', {
      params: { q: query, limit }
    })
  }

  /**
   * 获取查询历史
   */
  static async getQueryHistory(params: {
    page?: number
    size?: number
    keyword?: string
    task_status?: string
    category?: string
    start_date?: string
    end_date?: string
  } = {}): Promise<PaginatedResponse<QueryHistoryItem>> {
    return apiClient.get('/nlquery/history', { params })
  }

  /**
   * 重新执行历史查询
   */
  static async rerunHistoryQuery(historyId: number): Promise<ApiResponse<any>> {
    return apiClient.post(`/nlquery/history/${historyId}/rerun`)
  }

  /**
   * 添加收藏查询
   */
  static async createFavoriteQuery(data: {
    favorite_title: string
    favorite_description?: string
    user_question: string
    generated_sql?: string
    folder_name?: string
    tags?: string[]
  }): Promise<ApiResponse<QueryFavorite>> {
    return apiClient.post('/nlquery/favorites', data)
  }

  /**
   * 获取收藏查询列表
   */
  static async getFavoriteQueries(params: {
    page?: number
    size?: number
    folder_name?: string
    keyword?: string
  } = {}): Promise<PaginatedResponse<QueryFavorite>> {
    return apiClient.get('/nlquery/favorites', { params })
  }

  /**
   * 更新收藏查询
   */
  static async updateFavoriteQuery(
    favoriteId: number, 
    data: {
      favorite_title?: string
      favorite_description?: string
      folder_name?: string
      tags?: string[]
    }
  ): Promise<ApiResponse<QueryFavorite>> {
    return apiClient.put(`/nlquery/favorites/${favoriteId}`, data)
  }

  /**
   * 删除收藏查询
   */
  static async deleteFavoriteQuery(favoriteId: number): Promise<ApiResponse<boolean>> {
    return apiClient.delete(`/nlquery/favorites/${favoriteId}`)
  }

  /**
   * 执行收藏查询
   */
  static async executeFavoriteQuery(favoriteId: number): Promise<ApiResponse<any>> {
    return apiClient.post(`/nlquery/favorites/${favoriteId}/execute`)
  }

  /**
   * 提交查询反馈
   */
  static async submitQueryFeedback(data: {
    task_id: number
    feedback_type: string
    rating?: number
    feedback_content?: string
    sql_accuracy?: number
    result_relevance?: number
    response_speed?: number
    improvement_suggestions?: string
    expected_result?: string
  }): Promise<ApiResponse<any>> {
    return apiClient.post('/nlquery/feedback', data)
  }

  /**
   * 获取查询统计信息
   */
  static async getQueryStatistics(params: {
    start_date?: string
    end_date?: string
  } = {}): Promise<ApiResponse<QueryStatistics>> {
    return apiClient.get('/nlquery/statistics', { params })
  }

  /**
   * 获取查询优化建议
   */
  static async getOptimizationSuggestions(): Promise<ApiResponse<any[]>> {
    return apiClient.get('/nlquery/optimization-suggestions')
  }

  /**
   * 获取查询系统状态
   */
  static async getSystemStatus(): Promise<ApiResponse<any>> {
    return apiClient.get('/nlquery/system/status')
  }

  /**
   * 清理完成的任务
   */
  static async cleanupCompletedTasks(maxAgeHours: number = 24): Promise<ApiResponse<any>> {
    return apiClient.post('/nlquery/system/cleanup', null, {
      params: { max_age_hours: maxAgeHours }
    })
  }
}

export default QueryAPI