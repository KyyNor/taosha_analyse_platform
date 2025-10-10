import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  QueryRequest,
  QueryTask,
  QueryResult,
  Favorite,
  QueryLog
} from '@/types/index'
import queryService from '@services/api/queryService'

export const useQueryStore = defineStore('query', () => {
  // State
  const currentQuery = ref<QueryRequest | null>(null)
  const currentTask = ref<QueryTask | null>(null)
  const currentResult = ref<QueryResult | null>(null)
  const queryHistory = ref<QueryLog[]>([])
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
  const hasActiveQuery = computed(() => currentTask.value !== null)
  const isQueryRunning = computed(() =>
    (currentTask.value?.status as string) === 'running'
  )
  const queryProgress = computed(() => (currentTask.value as any)?.progress || null)
  const canCancelQuery = computed(() =>
    isQueryRunning.value && wsConnected.value
  )
  const hasResults = computed(() => currentResult.value !== null)
  const resultData = computed(() => {
    // Use execution_result from currentTask if available, otherwise fall back to currentResult
    if (currentTask.value && (currentTask.value as any).execution_result) {
      return (currentTask.value as any).execution_result
    }
    return currentResult.value?.result || null
  })
  const generatedSQL = computed(() => {
    // Use sql_query from currentTask, then generatedSql from currentResult, then generatedSql from currentTask
    if (currentTask.value && (currentTask.value as any).sql_query) {
      return (currentTask.value as any).sql_query
    }
    return currentResult.value?.generatedSql || (currentTask.value as any)?.generatedSql || ''
  })

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
      const task_id = response.task_id || response.taskId

      if (!task_id) {
        console.error('[QueryStore] Response structure:', JSON.stringify(response, null, 2))
        throw new Error('No task ID returned from server')
      }

      // Create task object with new TaskState structure
      currentTask.value = {
        task_id: task_id,
        user_input: request.query,
        operator: request.operator,
        flow_type: request.flow_type || 'fast',
        status: 'running',
        current_step: '初始化',
        progress: 0,
        created_at: new Date().toISOString(),
        sql_query: '',
        execution_result: null,
        clear_check_details: {},
        is_clear: false,
        error_message: null,
        retry_count: 0,
        max_retries: 5,
        logs: [],
        current_step_log: null,
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
      const newTaskId = response.task_id || response.taskId

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
      const blob = await queryService.exportResults(taskId, format)

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `query-results-${taskId}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
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

      queryHistory.value = response.items
      historyPage.value = response.page
      historyTotal.value = response.total
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

    queryHistory.value.push(...response.items)
    historyPage.value = response.page
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
      const taskId = response.task_id || response.taskId

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
        error_message: data.error_message || currentTask.value.error_message
      }

      // Update result if available
      if (data.status === 'success' && (data.data || data.execution_result)) {
        const resultData = data.data || data.execution_result

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
        } else if (resultData && typeof resultData === 'object' && resultData.columns && resultData.rows) {
          // Data might be in {columns: [], rows: []} format
          if (typeof resultData.columns[0] === 'string') {
            // Convert string array to column objects
            columns = resultData.columns.map((name: string) => ({ name, type: 'string' }))
          } else {
            columns = resultData.columns
          }
          rows = resultData.rows
          console.log('[QueryStore] Using columns/rows format', { columns, rowCount: rows.length })
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
    queryProgress,
    canCancelQuery,
    hasResults,
    resultData,
    generatedSQL,

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
    initializeWebSocket,
    disconnectWebSocket,
    cleanup
  }
})
