import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiClient } from '@/api'
import type { SystemStatus, DataTable, ChatHistory } from '@/types'

export const useAppStore = defineStore('app', () => {
  // 状态
  const loading = ref(false)
  const systemStatus = ref<SystemStatus | null>(null)
  const tables = ref<DataTable[]>([])
  const chatHistory = ref<ChatHistory[]>([])
  const isBackendHealthy = ref(false)

  // 计算属性
  const hasData = computed(() => tables.value.length > 0)

  // 方法
  const setLoading = (value: boolean) => {
    loading.value = value
  }

  const checkHealth = async () => {
    try {
      await apiClient.healthCheck()
      isBackendHealthy.value = true
      return true
    } catch {
      isBackendHealthy.value = false
      return false
    }
  }

  const fetchSystemStatus = async () => {
    try {
      const status = await apiClient.getSystemStatus()
      systemStatus.value = status
    } catch (error) {
      console.error('获取系统状态失败:', error)
    }
  }

  const fetchTables = async () => {
    try {
      const tableList = await apiClient.getTables()
      tables.value = tableList
    } catch (error) {
      console.error('获取数据表失败:', error)
    }
  }

  const addChatHistory = (entry: ChatHistory) => {
    chatHistory.value.push(entry)
    // 只保留最近10条记录
    if (chatHistory.value.length > 10) {
      chatHistory.value = chatHistory.value.slice(-10)
    }
  }

  const clearChatHistory = () => {
    chatHistory.value = []
  }

  // 初始化
  const init = async () => {
    setLoading(true)
    try {
      await checkHealth()
      if (isBackendHealthy.value) {
        await Promise.all([
          fetchSystemStatus(),
          fetchTables()
        ])
      }
    } finally {
      setLoading(false)
    }
  }

  return {
    // 状态
    loading,
    systemStatus,
    tables,
    chatHistory,
    isBackendHealthy,
    
    // 计算属性
    hasData,
    
    // 方法
    setLoading,
    checkHealth,
    fetchSystemStatus,
    fetchTables,
    addChatHistory,
    clearChatHistory,
    init
  }
})