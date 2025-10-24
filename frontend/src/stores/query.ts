import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  QueryRequest,
  QueryTask,
  QueryResult,
  Favorite,
  ClarificationResponse
} from '@/types/index'
import queryService from '@services/api/queryService'

export const useQueryStore = defineStore('query', () => {
  // State
  const currentQuery = ref<QueryRequest | null>(null)
  const currentTask = ref<QueryTask | null>(null)
  const currentResult = ref<QueryResult | null>(null)
  const queryHistory = ref<QueryTask[]>([])
  const favorites = ref<Favorite[]>([])
  const isLoading = ref(false)
  const wsConnected = ref(false)

  // Pagination
  const historyPage = ref(1)
  const historyPageSize = ref(20)
  const historyTotal = ref(0)
  const favoritesPage = ref(1)
  const favoritesPageSize = ref(20)
  const favoritesTotal = ref(0)

  // Filters
  const historyFilter = ref<{
    status?: string
    startTime?: string
    endTime?: string
  }>({})

  // Getters
  const hasActiveQuery = computed(() => {
    return currentTask.value !== null &&
           ['running', 'success', 'failed', 'waiting_for_input'].includes((currentTask.value as any).status)
  })
  const isQueryRunning = computed(() =>
    (currentTask.value?.status as string) === 'running'
  )
  // 新增：专门用于查询按钮状态，只在运行时显示取消
  const shouldShowCancelButton = computed(() =>
    (currentTask.value?.status as string) === 'running'
  )
  const queryProgress = computed(() => (currentTask.value as any)?.progress || null)
  const canCancelQuery = computed(() =>
    isQueryRunning.value && wsConnected.value
  )
  const hasResults = computed(() => currentResult.value !== null)
  const resultData = computed(() => {
    // Return the processed standard structure from currentResult
    return currentResult.value?.result || null
  })
  const generatedSQL = computed(() => {
    // Use sql_query from currentTask, then generatedSql from currentResult, then generatedSql from currentTask
    if (currentTask.value && (currentTask.value as any).sql_query) {
      return (currentTask.value as any).sql_query
    }
    return currentResult.value?.generatedSql || (currentTask.value as any)?.generatedSql || ''
  })

  // 人机交互相关状态
  const isWaitingForClarification = computed(() =>
    (currentTask.value as any)?.waiting_for_user_input || false
  )

  const clarificationOptions = computed(() =>
    (currentTask.value as any)?.clear_check_details.clarification_options || []
  )

  const clarificationQuestion = computed(() =>
    (currentTask.value as any)?.clear_check_details.clarification_question || ''
  )

  const selectedClarification = ref('')
  const customClarification = ref('')

  // Actions
  const submitQuery = async (request: QueryRequest) => {
    try {
      isLoading.value = true
      currentQuery.value = request

      // Initialize WebSocket connection if not already connected
      if (!wsConnected.value) {
        await queryService.initializeWebSocket()
        wsConnected.value = true
      }

      // Submit query
      console.log('[QueryStore] Submitting query request:', request)
      const response = await queryService.submitQuery(request)
      console.log('[QueryStore] Received response:', response)

      // Check if response exists
      if (!response) {
        throw new Error('No response received from server')
      }

      // Extract task_id from response (backend returns task_id, not taskId)
      const task_id = response.task_id

      if (!task_id) {
        console.error('[QueryStore] Response structure:', JSON.stringify(response, null, 2))
        throw new Error('No task ID returned from server')
      }

      // Create task object with new TaskState structure
      currentTask.value = {
        task_id,
        user_input: request.query,
        flow_type: request.flow_type || 'fast',
        status: 'running',
        current_step: '初始化',
        progress: 0,
        created_at: new Date().toISOString(),
        sql_query: '',
        execution_result: undefined,
        clear_check_details: {},
        is_clear: false,
        error_message: undefined,
        retry_count: 0,
        max_retries: 5,
        logs: [],
        current_step_log: undefined,
        waiting_for_user_input: false,
        return_to_node: '',
        current_step_name: '初始化'
      }

      // Subscribe to progress updates
      queryService.subscribeToTaskProgress(task_id, handleProgressUpdate)

      return task_id
    } catch (error) {
      console.error('Failed to submit query:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const cancelQuery = async () => {
    if (!currentTask.value || !canCancelQuery.value) return

    try {
      await queryService.cancelTask(currentTask.value.task_id)
      ;(currentTask.value as any).status = 'cancelled'
    } catch (error) {
      console.error('Failed to cancel query:', error)
      throw error
    }
  }

  const rerunQuery = async (taskId: string) => {
    try {
      isLoading.value = true
      const response = await queryService.rerunQuery(taskId)

      // Extract task_id from response (backend returns task_id, not taskId)
      const newTaskId = response.task_id

      if (!newTaskId) {
        throw new Error('No task ID returned from server')
      }

      // Update current task
      if (currentTask.value) {
        currentTask.value.task_id = newTaskId
        currentTask.value.status = 'running'
        currentTask.value.created_at = new Date().toISOString()
      }

      // Subscribe to progress updates
      queryService.subscribeToTaskProgress(newTaskId, handleProgressUpdate)

      return newTaskId
    } catch (error) {
      console.error('Failed to rerun query:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const exportResults = async (taskId: string, format: 'xlsx' | 'csv') => {
    try {
      // TODO: 实现导出功能
      console.log('Export results not implemented yet')
    } catch (error) {
      console.error('Failed to export results:', error)
      throw error
    }
  }

  const clearCurrentQuery = () => {
    currentQuery.value = null
    currentTask.value = null
    currentResult.value = null
  }

  // History management
  const loadQueryHistory = async (page = 1, filters = {}) => {
    try {
      isLoading.value = true
      const response = await queryService.getQueryHistory(
        page,
        historyPageSize.value,
        { ...historyFilter.value, ...filters }
      )

      queryHistory.value = response.data || []
      historyPage.value = response.pagination?.page || page
      historyTotal.value = response.pagination?.total || 0
    } catch (error) {
      console.error('Failed to load query history:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const loadMoreHistory = async () => {
    if (historyPage.value * historyPageSize.value >= historyTotal.value) return

    const nextPage = historyPage.value + 1
    const response = await queryService.getQueryHistory(
      nextPage,
      historyPageSize.value,
      historyFilter.value
    )

    queryHistory.value.push(...(response.data || []))
    historyPage.value = response.pagination?.page || nextPage
  }

  const setHistoryFilter = (filters: typeof historyFilter.value) => {
    historyFilter.value = { ...filters }
    historyPage.value = 1
    loadQueryHistory(1, filters)
  }

  // Favorites management
  const loadFavorites = async (page = 1) => {
    try {
      isLoading.value = true
      const response = await queryService.getFavorites(page, favoritesPageSize.value)

      if (page === 1) {
        favorites.value = response.items
      } else {
        favorites.value.push(...response.items)
      }

      favoritesPage.value = response.page
      favoritesTotal.value = response.total
    } catch (error) {
      console.error('Failed to load favorites:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const addToFavorites = async (taskId: string, title: string) => {
    try {
      await queryService.addToFavorites(taskId, title)
      // Reload favorites
      await loadFavorites(1)
    } catch (error) {
      console.error('Failed to add to favorites:', error)
      throw error
    }
  }

  const updateFavorite = async (favoriteId: number, title: string) => {
    try {
      await queryService.updateFavorite(favoriteId, title)
      // Update local favorite
      const favorite = favorites.value.find(f => f.id === favoriteId)
      if (favorite) {
        favorite.favoriteTitle = title
      }
    } catch (error) {
      console.error('Failed to update favorite:', error)
      throw error
    }
  }

  const deleteFavorite = async (favoriteId: number) => {
    try {
      await queryService.deleteFavorite(favoriteId)
      // Remove from local favorites
      favorites.value = favorites.value.filter(f => f.id !== favoriteId)
      favoritesTotal.value -= 1
    } catch (error) {
      console.error('Failed to delete favorite:', error)
      throw error
    }
  }

  const executeFavorite = async (favoriteId: number) => {
    try {
      const response = await queryService.executeFavorite(favoriteId)

      // Find the favorite and create query request
      const favorite = favorites.value.find(f => f.id === favoriteId)
      if (favorite) {
        const request: QueryRequest = {
          query: favorite.userQuestion,
          flow_type: 'thorough',
          selectedThemeId: favorite.selectedThemeId,
          selectedTableIds: favorite.selectedTableIds ?
            JSON.parse(favorite.selectedTableIds as any) : undefined
        }

        await submitQuery(request)
      }

      // Extract task_id from response (backend returns task_id, not taskId)
      const taskId = response.task_id

      if (!taskId) {
        throw new Error('No task ID returned from server')
      }

      return taskId
    } catch (error) {
      console.error('Failed to execute favorite:', error)
      throw error
    }
  }

  // Feedback management
  const submitFeedback = async (taskId: string, type: 'positive' | 'negative' | 'neutral', content?: string) => {
    try {
      await queryService.submitFeedback(taskId, type, content)
    } catch (error) {
      console.error('Failed to submit feedback:', error)
      throw error
    }
  }

  // 提交澄清
  const submitClarification = async (taskId: string) => {
    try {
      // 构建澄清内容：选中的选项 + 自定义输入
      const selectedOption = selectedClarification.value.trim()
      const customInput = customClarification.value.trim()
      
      let clarification = ''
      if (selectedOption && customInput) {
        clarification = `用户选择：${selectedOption}，用户补充输入：${customInput}`
      } else if (selectedOption) {
        clarification = `用户选择：${selectedOption}`
      } else if (customInput) {
        clarification = `用户补充输入：${customInput}`
      }
      
      if (!clarification) {
        throw new Error('请选择或输入澄清内容')
      }
      
      isLoading.value = true

      const response: ClarificationResponse = await queryService.submitClarification(
        taskId,
        clarification
      )

      if (response.success) {
        // 清空澄清相关状态
        selectedClarification.value = ''
        customClarification.value = ''

        // 继续监听任务进度
        queryService.subscribeToTaskProgress(taskId, handleProgressUpdate)

        return response
      } else {
        throw new Error('提交澄清失败')
      }
    } catch (error) {
      console.error('Failed to submit clarification:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  // WebSocket management
  const initializeWebSocket = async () => {
    try {
      await queryService.initializeWebSocket()
      wsConnected.value = true
    } catch (error) {
      console.error('Failed to initialize WebSocket:', error)
      wsConnected.value = false
    }
  }

  const disconnectWebSocket = () => {
    queryService.disconnectWebSocket()
    wsConnected.value = false
  }

  // Progress update handler
  const handleProgressUpdate = (data: any) => {
    if (currentTask.value && data.task_id === currentTask.value.task_id) {
      // Update task state with new TaskState structure
      currentTask.value = {
        ...currentTask.value,
        ...data,
        status: data.status || currentTask.value.status,
        progress: data.progress,
        sql_query: data.sql_query || currentTask.value.sql_query,
        current_step: data.current_step || currentTask.value.current_step,
        current_step_name: data.current_step_name || currentTask.value.current_step_name,
        logs: data.logs || currentTask.value.logs,
        execution_result: data.execution_result || currentTask.value.execution_result,
        error_message: data.error_message || currentTask.value.error_message,
        waiting_for_user_input: data.waiting_for_user_input || currentTask.value.waiting_for_user_input,
        return_to_node: data.return_to_node || currentTask.value.return_to_node,
        clear_check_details: data.clear_check_details || currentTask.value.clear_check_details
      }

      // Update result if available
      if (data.status === 'success' && data.execution_result) {
        const resultData = data.execution_result

        console.log('[QueryStore] Processing successful result data', {
          data,
          resultData,
          dataType: Array.isArray(resultData) ? 'array' : typeof resultData,
          rowCount: data.row_count,
          backendColumns: data.columns
        })

        // Handle different data formats
        let columns: any[] = []
        let rows: any[] = [] // Keep as array of objects for direct access in template

        // First, check if backend provided column information
        if (data.columns && Array.isArray(data.columns)) {
          // Backend provided columns with name and type
          columns = data.columns
          console.log('[QueryStore] Using backend column information', { columns })
        } else if (Array.isArray(resultData) && resultData.length > 0) {
          // Data is array of objects (records format), extract column names
          const columnNames = Object.keys(resultData[0])
          columns = columnNames.map(name => ({ name, type: 'string' })) // Default type to string
          console.log('[QueryStore] Extracted columns from records', { columns })
        }

        // Use execution_result directly as rows if it's an array of objects
        if (Array.isArray(resultData) && resultData.length > 0) {
          // Keep as array of objects for direct access in template using row[column.name]
          rows = resultData
          console.log('[QueryStore] Using execution_result as rows array', {
            rowCount: rows.length,
            sampleRow: resultData[0],
            columns
          })
        }

        currentResult.value = {
          taskId: data.task_id,
          status: data.status,
          generatedSql: data.sql_query || '',
          result: {
            columns,
            rows,
            rowCount: data.row_count || rows.length || 0
          }
        }

        console.log('[QueryStore] Final result set', currentResult.value)
      }

      // Handle completion
      if (data.status === 'success' || data.status === 'failed') {
        // Reload history to get the latest entry
        loadQueryHistory(1)
      }
    }
  }

  // Cleanup
  const cleanup = () => {
    clearCurrentQuery()
    disconnectWebSocket()
    queryHistory.value = []
    favorites.value = []
    historyPage.value = 1
    favoritesPage.value = 1
    historyTotal.value = 0
    favoritesTotal.value = 0
  }

  return {
    // State
    currentQuery,
    currentTask,
    currentResult,
    queryHistory,
    favorites,
    isLoading,
    wsConnected,
    historyPage,
    historyPageSize,
    historyTotal,
    favoritesPage,
    favoritesPageSize,
    favoritesTotal,
    historyFilter,

    // Getters
    hasActiveQuery,
    isQueryRunning,
    shouldShowCancelButton,
    queryProgress,
    canCancelQuery,
    hasResults,
    resultData,
    generatedSQL,
    isWaitingForClarification,
    clarificationOptions,
    clarificationQuestion,
    selectedClarification,
    customClarification,

    // Actions
    submitQuery,
    cancelQuery,
    rerunQuery,
    exportResults,
    clearCurrentQuery,
    loadQueryHistory,
    loadMoreHistory,
    setHistoryFilter,
    loadFavorites,
    addToFavorites,
    updateFavorite,
    deleteFavorite,
    executeFavorite,
    submitFeedback,
    submitClarification,
    initializeWebSocket,
    disconnectWebSocket,
    cleanup
  }
})
