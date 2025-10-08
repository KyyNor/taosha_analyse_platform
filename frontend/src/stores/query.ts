import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import QueryAPI from '@/api/query'
import { webSocketService } from '@/services/websocket'
import type { 
  QueryTaskCreate, QueryTaskStatus, QueryTaskResult, 
  QuerySuggestion, QueryHistoryItem, QueryFavorite,
  QueryStatistics
} from '@/api/query'

// 查询状态枚举
export enum QueryStatus {
  PENDING = 'pending',
  RUNNING = 'running', 
  SUCCESS = 'success',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  TIMEOUT = 'timeout'
}

// 当前查询任务接口
export interface CurrentQueryTask {
  task_id: string
  user_question: string
  status: QueryStatus
  current_step?: string
  progress_percentage: number
  generated_sql?: string
  final_sql?: string
  result_columns?: string[]
  result_data?: any[][]
  result_row_count?: number
  error_message?: string
  created_at: string
  updated_at?: string
  llm_tokens_used?: number
  pagination?: {
    page: number
    size: number
    total: number
    pages: number
  }
}

export const useQueryStore = defineStore('query', () => {
  // 状态
  const currentTask = ref<CurrentQueryTask | null>(null)
  const loading = ref(false)
  const submitting = ref(false)
  const queryHistory = ref<QueryHistoryItem[]>([])
  const favoriteQueries = ref<QueryFavorite[]>([])
  const queryStatistics = ref<QueryStatistics | null>(null)
  const suggestions = ref<QuerySuggestion[]>([])
  
  // 实时状态轮询
  const statusPollingInterval = ref<NodeJS.Timeout | null>(null)
  const isPolling = ref(false)
  const webSocketConnected = ref(false)
  const useWebSocketUpdate = ref(true)

  // 计算属性
  const isTaskRunning = computed(() => {
    return currentTask.value?.status === QueryStatus.RUNNING || 
           currentTask.value?.status === QueryStatus.PENDING
  })

  const hasResult = computed(() => {
    return currentTask.value?.status === QueryStatus.SUCCESS && 
           currentTask.value?.result_data && 
           currentTask.value.result_data.length > 0
  })

  const hasError = computed(() => {
    return currentTask.value?.status === QueryStatus.FAILED ||
           currentTask.value?.status === QueryStatus.TIMEOUT
  })

  // 提交查询
  const submitQuery = async (queryData: QueryTaskCreate) => {
    try {
      submitting.value = true
      loading.value = true

      const response = await QueryAPI.submitQuery(queryData)
      
      if (response.data) {
        // 创建新的任务对象
        currentTask.value = {
          task_id: response.data.task_id,
          user_question: queryData.user_question,
          status: QueryStatus.PENDING,
          progress_percentage: 0,
          created_at: new Date().toISOString()
        }

        // 优先使用WebSocket进行实时更新
        if (useWebSocketUpdate.value && webSocketConnected.value) {
          subscribeToTaskUpdates(response.data.task_id)
        } else {
          // 退而求其次使用轮询
          startStatusPolling(response.data.task_id)
        }
      }

      return response
    } catch (error) {
      console.error('提交查询失败:', error)
      throw error
    } finally {
      submitting.value = false
    }
  }

  // 开始状态轮询
  const startStatusPolling = (taskId: string) => {
    if (isPolling.value) {
      stopStatusPolling()
    }

    isPolling.value = true
    
    const pollStatus = async () => {
      try {
        const statusResponse = await QueryAPI.getQueryStatus(taskId)
        
        if (currentTask.value && statusResponse.data) {
          // 更新任务状态
          currentTask.value.status = statusResponse.data.status as QueryStatus
          currentTask.value.current_step = statusResponse.data.current_step
          currentTask.value.progress_percentage = statusResponse.data.progress_percentage
          currentTask.value.error_message = statusResponse.data.error_message
          currentTask.value.updated_at = statusResponse.data.updated_at

          // 如果任务完成，获取结果
          if (statusResponse.data.status === QueryStatus.SUCCESS) {
            await fetchQueryResult(taskId)
            stopStatusPolling()
            loading.value = false
          } else if ([QueryStatus.FAILED, QueryStatus.CANCELLED, QueryStatus.TIMEOUT].includes(statusResponse.data.status as QueryStatus)) {
            stopStatusPolling()
            loading.value = false
          }
        }
      } catch (error) {
        console.error('轮询任务状态失败:', error)
        // 继续轮询，不中断
      }
    }

    // 立即执行一次
    pollStatus()
    
    // 设置定时轮询
    statusPollingInterval.value = setInterval(pollStatus, 2000) // 每2秒轮询一次
  }

  // 停止状态轮询
  const stopStatusPolling = () => {
    if (statusPollingInterval.value) {
      clearInterval(statusPollingInterval.value)
      statusPollingInterval.value = null
    }
    isPolling.value = false
  }

  // 获取查询结果
  const fetchQueryResult = async (taskId: string, page: number = 1, size: number = 20) => {
    try {
      const response = await QueryAPI.getQueryResult(taskId, page, size)
      
      if (currentTask.value && response.data) {
        currentTask.value.generated_sql = response.data.generated_sql
        currentTask.value.final_sql = response.data.final_sql
        currentTask.value.result_columns = response.data.result_columns
        currentTask.value.result_data = response.data.result_data
        currentTask.value.result_row_count = response.data.result_row_count
        currentTask.value.llm_tokens_used = response.data.llm_tokens_used
        currentTask.value.pagination = response.data.pagination
      }

      return response
    } catch (error) {
      console.error('获取查询结果失败:', error)
      throw error
    }
  }

  // 取消查询
  const cancelQuery = async (taskId: string) => {
    try {
      await QueryAPI.cancelQuery(taskId)
      
      if (currentTask.value && currentTask.value.task_id === taskId) {
        currentTask.value.status = QueryStatus.CANCELLED
        currentTask.value.current_step = '任务已取消'
      }

      stopStatusPolling()
      loading.value = false
    } catch (error) {
      console.error('取消查询失败:', error)
      throw error
    }
  }

  // 获取查询建议
  const fetchQuerySuggestions = async (query: string, limit: number = 5) => {
    try {
      if (!query.trim()) {
        suggestions.value = []
        return
      }

      const response = await QueryAPI.getQuerySuggestions(query, limit)
      suggestions.value = response.data || []
    } catch (error) {
      console.error('获取查询建议失败:', error)
      suggestions.value = []
    }
  }

  // 获取查询历史
  const fetchQueryHistory = async (params: any = {}) => {
    try {
      const response = await QueryAPI.getQueryHistory(params)
      queryHistory.value = response.data?.items || []
      return response
    } catch (error) {
      console.error('获取查询历史失败:', error)
      throw error
    }
  }

  // 重新执行历史查询
  const rerunHistoryQuery = async (historyId: number) => {
    try {
      const response = await QueryAPI.rerunHistoryQuery(historyId)
      return response
    } catch (error) {
      console.error('重新执行历史查询失败:', error)
      throw error
    }
  }

  // 获取收藏查询列表
  const fetchFavoriteQueries = async (params: any = {}) => {
    try {
      const response = await QueryAPI.getFavoriteQueries(params)
      favoriteQueries.value = response.data?.items || []
      return response
    } catch (error) {
      console.error('获取收藏查询失败:', error)
      throw error
    }
  }

  // 添加收藏查询
  const addFavoriteQuery = async (data: any) => {
    try {
      const response = await QueryAPI.createFavoriteQuery(data)
      // 刷新收藏列表
      await fetchFavoriteQueries()
      return response
    } catch (error) {
      console.error('添加收藏查询失败:', error)
      throw error
    }
  }

  // 删除收藏查询
  const deleteFavoriteQuery = async (favoriteId: number) => {
    try {
      await QueryAPI.deleteFavoriteQuery(favoriteId)
      // 从本地列表中移除
      favoriteQueries.value = favoriteQueries.value.filter(item => item.id !== favoriteId)
    } catch (error) {
      console.error('删除收藏查询失败:', error)
      throw error
    }
  }

  // 执行收藏查询
  const executeFavoriteQuery = async (favoriteId: number) => {
    try {
      const response = await QueryAPI.executeFavoriteQuery(favoriteId)
      return response
    } catch (error) {
      console.error('执行收藏查询失败:', error)
      throw error
    }
  }

  // 获取查询统计
  const fetchQueryStatistics = async (params: any = {}) => {
    try {
      const response = await QueryAPI.getQueryStatistics(params)
      queryStatistics.value = response.data
      return response
    } catch (error) {
      console.error('获取查询统计失败:', error)
      throw error
    }
  }

  // 提交查询反馈
  const submitQueryFeedback = async (data: any) => {
    try {
      const response = await QueryAPI.submitQueryFeedback(data)
      return response
    } catch (error) {
      console.error('提交查询反馈失败:', error)
      throw error
    }
  }

  // 清理当前任务
  const clearCurrentTask = () => {
    currentTask.value = null
    stopStatusPolling()
    loading.value = false
    submitting.value = false
  }

  // 重置所有状态
  const resetStore = () => {
    clearCurrentTask()
    queryHistory.value = []
    favoriteQueries.value = []
    queryStatistics.value = null
    suggestions.value = []
  }

  // 导出查询结果
  const exportQueryResult = async (format: 'csv' | 'excel' = 'csv') => {
    if (!currentTask.value || !hasResult.value) {
      throw new Error('没有可导出的查询结果')
    }

    try {
      // 这里实现导出逻辑
      const { result_columns, result_data } = currentTask.value
      
      if (format === 'csv') {
        return exportToCSV(result_columns || [], result_data || [])
      } else {
        return exportToExcel(result_columns || [], result_data || [])
      }
    } catch (error) {
      console.error('导出查询结果失败:', error)
      throw error
    }
  }

  // 导出为CSV
  const exportToCSV = (columns: string[], data: any[][]) => {
    const csvContent = [
      columns.join(','),
      ...data.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    
    link.setAttribute('href', url)
    link.setAttribute('download', `query_result_${new Date().getTime()}.csv`)
    link.style.visibility = 'hidden'
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // 导出为Excel（需要额外的库支持）
  const exportToExcel = (columns: string[], data: any[][]) => {
    // TODO: 实现Excel导出，需要引入如SheetJS等库
    console.log('Excel导出功能待实现')
  }
  
  // ========== WebSocket相关方法 ==========
  
  // 初始化WebSocket连接
  const initWebSocketConnection = async () => {
    try {
      await webSocketService.connect({
        onOpen: () => {
          console.log('WebSocket连接已建立')
          webSocketConnected.value = true
        },
        onClose: () => {
          console.log('WebSocket连接已断开')
          webSocketConnected.value = false
        },
        onError: (error) => {
          console.error('WebSocket连接错误:', error)
          webSocketConnected.value = false
        },
        onQueryProgress: (taskId: string, progress: any) => {
          handleTaskProgressUpdate(taskId, progress)
        },
        onQueryCompleted: (taskId: string, result: any) => {
          handleTaskCompletionUpdate(taskId, result)
        },
        onQueryError: (taskId: string, error: any) => {
          handleTaskErrorUpdate(taskId, error)
        }
      })
    } catch (error) {
      console.error('WebSocket连接失败:', error)
      webSocketConnected.value = false
    }
  }
  
  // 订阅任务更新
  const subscribeToTaskUpdates = (taskId: string) => {
    if (webSocketConnected.value) {
      webSocketService.subscribeTask(taskId)
    }
  }
  
  // 取消订阅任务更新
  const unsubscribeFromTaskUpdates = (taskId: string) => {
    if (webSocketConnected.value) {
      webSocketService.unsubscribeTask(taskId)
    }
  }
  
  // 处理任务进度更新
  const handleTaskProgressUpdate = (taskId: string, progress: any) => {
    if (currentTask.value && currentTask.value.task_id === taskId) {
      currentTask.value.current_step = progress.current_step
      currentTask.value.progress_percentage = Math.round(progress.progress_percentage * 100)
      currentTask.value.generated_sql = progress.generated_sql
      
      if (progress.progress_percentage > 0 && currentTask.value.status === QueryStatus.PENDING) {
        currentTask.value.status = QueryStatus.RUNNING
      }
    }
  }
  
  // 处理任务完成更新
  const handleTaskCompletionUpdate = (taskId: string, result: any) => {
    if (currentTask.value && currentTask.value.task_id === taskId) {
      currentTask.value.status = QueryStatus.SUCCESS
      currentTask.value.progress_percentage = 100
      currentTask.value.current_step = result.final_step || '查询完成'
      currentTask.value.generated_sql = result.generated_sql
      currentTask.value.final_sql = result.generated_sql
      currentTask.value.result_columns = result.result?.columns
      currentTask.value.result_data = result.result?.rows
      currentTask.value.result_row_count = result.result?.total_count
      currentTask.value.llm_tokens_used = result.total_tokens
      
      loading.value = false
    }
  }
  
  // 处理任务错误更新
  const handleTaskErrorUpdate = (taskId: string, error: any) => {
    if (currentTask.value && currentTask.value.task_id === taskId) {
      currentTask.value.status = QueryStatus.FAILED
      currentTask.value.error_message = error.error_message
      currentTask.value.current_step = error.failed_step || '执行失败'
      
      loading.value = false
    }
  }
  
  // 断开WebSocket连接
  const disconnectWebSocket = () => {
    webSocketService.disconnect()
    webSocketConnected.value = false
  }

  return {
    // 状态
    currentTask,
    loading,
    submitting,
    queryHistory,
    favoriteQueries,
    queryStatistics,
    suggestions,
    isPolling,
    webSocketConnected,

    // 计算属性
    isTaskRunning,
    hasResult,
    hasError,

    // 查询相关方法
    submitQuery,
    fetchQueryResult,
    cancelQuery,
    fetchQuerySuggestions,
    fetchQueryHistory,
    rerunHistoryQuery,
    fetchFavoriteQueries,
    addFavoriteQuery,
    deleteFavoriteQuery,
    executeFavoriteQuery,
    fetchQueryStatistics,
    submitQueryFeedback,
    clearCurrentTask,
    resetStore,
    exportQueryResult,
    startStatusPolling,
    stopStatusPolling,
    
    // WebSocket相关方法
    initWebSocketConnection,
    subscribeToTaskUpdates,
    unsubscribeFromTaskUpdates,
    disconnectWebSocket
  }
})

export default useQueryStore