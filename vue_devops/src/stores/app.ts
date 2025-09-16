import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { SystemStatus, TableMetadata, Term, RelationConfig } from '@/types'
import { apiClient } from '@/api'

export const useAppStore = defineStore('app', () => {
  // 状态
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const systemStatus = ref<SystemStatus | null>(null)
  const isHealthy = ref(true)

  // 元数据缓存
  const metadataTables = ref<TableMetadata[]>([])
  const terms = ref<Term[]>([])
  const relationConfigs = ref<RelationConfig[]>([])
  const relationIds = ref<string[]>([])

  // 缓存时间戳
  const lastUpdated = ref({
    tables: 0,
    terms: 0,
    relations: 0,
    system: 0
  })

  // 计算属性
  const stats = computed(() => ({
    tables: metadataTables.value.length,
    columns: metadataTables.value.reduce((total, table) => {
      return total + (table.columns?.length || 0)
    }, 0),
    terms: terms.value.length,
    relations: relationConfigs.value.length
  }))

  const uniqueFamilies = computed(() => {
    const families = new Set(relationConfigs.value.map(config => config.relation_family))
    return Array.from(families)
  })

  // Actions
  const setLoading = (loading: boolean) => {
    isLoading.value = loading
  }

  const setError = (errorMessage: string | null) => {
    error.value = errorMessage
  }

  const clearError = () => {
    error.value = null
  }

  // 健康检查
  const checkHealth = async () => {
    try {
      isHealthy.value = await apiClient.healthCheck()
      return isHealthy.value
    } catch (err) {
      isHealthy.value = false
      return false
    }
  }

  // 获取系统状态
  const fetchSystemStatus = async (forceRefresh = false) => {
    const now = Date.now()
    const cacheTimeout = 60000 // 1分钟缓存

    if (!forceRefresh && systemStatus.value && (now - lastUpdated.value.system) < cacheTimeout) {
      return systemStatus.value
    }

    try {
      setLoading(true)
      clearError()
      
      systemStatus.value = await apiClient.getSystemStatus()
      lastUpdated.value.system = now
      
      return systemStatus.value
    } catch (err: any) {
      setError(`获取系统状态失败: ${err.message}`)
      return null
    } finally {
      setLoading(false)
    }
  }

  // 获取表元数据
  const fetchMetadataTables = async (forceRefresh = false) => {
    const now = Date.now()
    const cacheTimeout = 30000 // 30秒缓存

    if (!forceRefresh && metadataTables.value.length > 0 && (now - lastUpdated.value.tables) < cacheTimeout) {
      return metadataTables.value
    }

    try {
      setLoading(true)
      clearError()
      
      metadataTables.value = await apiClient.getAllMetadataTables()
      lastUpdated.value.tables = now
      
      return metadataTables.value
    } catch (err: any) {
      setError(`获取表元数据失败: ${err.message}`)
      return []
    } finally {
      setLoading(false)
    }
  }

  // 获取术语列表
  const fetchTerms = async (forceRefresh = false) => {
    const now = Date.now()
    const cacheTimeout = 30000 // 30秒缓存

    if (!forceRefresh && terms.value.length > 0 && (now - lastUpdated.value.terms) < cacheTimeout) {
      return terms.value
    }

    try {
      setLoading(true)
      clearError()
      
      terms.value = await apiClient.getAllTerms()
      lastUpdated.value.terms = now
      
      return terms.value
    } catch (err: any) {
      setError(`获取术语列表失败: ${err.message}`)
      return []
    } finally {
      setLoading(false)
    }
  }

  // 获取关联配置
  const fetchRelationConfigs = async (forceRefresh = false) => {
    const now = Date.now()
    const cacheTimeout = 30000 // 30秒缓存

    if (!forceRefresh && relationConfigs.value.length > 0 && (now - lastUpdated.value.relations) < cacheTimeout) {
      return relationConfigs.value
    }

    try {
      setLoading(true)
      clearError()
      
      const [configs, ids] = await Promise.all([
        apiClient.getAllRelationConfigs(),
        apiClient.getRelationIds()
      ])
      
      relationConfigs.value = configs
      relationIds.value = ids
      lastUpdated.value.relations = now
      
      return relationConfigs.value
    } catch (err: any) {
      setError(`获取关联配置失败: ${err.message}`)
      return []
    } finally {
      setLoading(false)
    }
  }

  // 刷新所有数据
  const refreshAllData = async () => {
    try {
      setLoading(true)
      clearError()
      
      await Promise.all([
        fetchSystemStatus(true),
        fetchMetadataTables(true),
        fetchTerms(true),
        fetchRelationConfigs(true)
      ])
    } catch (err: any) {
      setError(`刷新数据失败: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  // 清除所有缓存
  const clearCache = () => {
    metadataTables.value = []
    terms.value = []
    relationConfigs.value = []
    relationIds.value = []
    systemStatus.value = null
    lastUpdated.value = {
      tables: 0,
      terms: 0,
      relations: 0,
      system: 0
    }
  }

  // 初始化应用数据
  const initApp = async () => {
    try {
      setLoading(true)
      clearError()
      
      // 先检查健康状态
      const healthy = await checkHealth()
      
      if (healthy) {
        // 并行加载基础数据
        await Promise.all([
          fetchSystemStatus(),
          fetchMetadataTables(),
          fetchTerms(),
          fetchRelationConfigs()
        ])
      }
    } catch (err: any) {
      setError(`应用初始化失败: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return {
    // 状态
    isLoading: readonly(isLoading),
    error: readonly(error),
    systemStatus: readonly(systemStatus),
    isHealthy: readonly(isHealthy),
    metadataTables: readonly(metadataTables),
    terms: readonly(terms),
    relationConfigs: readonly(relationConfigs),
    relationIds: readonly(relationIds),
    lastUpdated: readonly(lastUpdated),
    
    // 计算属性
    stats,
    uniqueFamilies,
    
    // Actions
    setLoading,
    setError,
    clearError,
    checkHealth,
    fetchSystemStatus,
    fetchMetadataTables,
    fetchTerms,
    fetchRelationConfigs,
    refreshAllData,
    clearCache,
    initApp
  }
})

// 只读工具函数
function readonly<T>(ref: any): T {
  return ref as T
}