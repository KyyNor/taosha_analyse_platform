import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useMetadataStore } from '@/store/use-metadata-store'
import { useAppStore } from '@/store/use-app-store'
import metadataService from '@/lib/services/metadataService'
import type { TableMetadata, GlossaryTerm, DataTheme, RelationConfig } from '@/types/index'

// 表数据查询
export function useTables() {
  const searchQuery = useMetadataStore(state => state.searchQuery)
  const filters = useMetadataStore(state => state.filters)

  return useQuery({
    queryKey: ['tables', searchQuery, filters],
    queryFn: () => metadataService.getTables(true, filters.isAvailable, searchQuery),
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    select: (data) => data.sort((a, b) => a.name.localeCompare(b.name)),
  })
}

// 创建表
export function useCreateTable() {
  const queryClient = useQueryClient()
  const setEditingTable = useMetadataStore(state => state.setEditingTable)
  const addNotification = useAppStore(state => state.addNotification)

  return useMutation({
    mutationFn: metadataService.createTable,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tables'] })
      setEditingTable(null)
      addNotification({
        id: Date.now().toString(),
        type: 'success',
        title: '创建成功',
        message: '表配置已创建'
      })
    },
    onError: (error: any) => {
      addNotification({
        id: Date.now().toString(),
        type: 'error',
        title: '创建失败',
        message: error.message || '创建表配置失败'
      })
    }
  })
}

// 更新表
export function useUpdateTable() {
  const queryClient = useQueryClient()
  const setEditingTable = useMetadataStore(state => state.setEditingTable)
  const addNotification = useAppStore(state => state.addNotification)

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      metadataService.updateTable(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tables'] })
      setEditingTable(null)
      addNotification({
        id: Date.now().toString(),
        type: 'success',
        title: '更新成功',
        message: '表配置已更新'
      })
    },
    onError: (error: any) => {
      addNotification({
        id: Date.now().toString(),
        type: 'error',
        title: '更新失败',
        message: error.message || '更新表配置失败'
      })
    }
  })
}

// 删除表
export function useDeleteTable() {
  const queryClient = useQueryClient()
  const addNotification = useAppStore(state => state.addNotification)

  return useMutation({
    mutationFn: metadataService.deleteTable,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tables'] })
      addNotification({
        id: Date.now().toString(),
        type: 'success',
        title: '删除成功',
        message: '表配置已删除'
      })
    },
    onError: (error: any) => {
      addNotification({
        id: Date.now().toString(),
        type: 'error',
        title: '删除失败',
        message: error.message || '删除表配置失败'
      })
    }
  })
}

// 业务术语查询
export function useGlossaryTerms() {
  const searchQuery = useMetadataStore(state => state.searchQuery)
  const filters = useMetadataStore(state => state.filters)

  return useQuery({
    queryKey: ['glossary', searchQuery, filters],
    queryFn: () => {
      if (filters.type) {
        return metadataService.getGlossaryTermsByType(filters.type)
      }
      return metadataService.getGlossaryTerms()
    },
    staleTime: 5 * 60 * 1000,
  })
}

// 创建业务术语
export function useCreateGlossaryTerm() {
  const queryClient = useQueryClient()
  const setEditingGlossary = useMetadataStore(state => state.setEditingGlossary)
  const addNotification = useAppStore(state => state.addNotification)

  return useMutation({
    mutationFn: metadataService.createGlossaryTerm,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['glossary'] })
      setEditingGlossary(null)
      addNotification({
        id: Date.now().toString(),
        type: 'success',
        title: '创建成功',
        message: '业务术语已创建'
      })
    },
    onError: (error: any) => {
      addNotification({
        id: Date.now().toString(),
        type: 'error',
        title: '创建失败',
        message: error.message || '创建业务术语失败'
      })
    }
  })
}

// 更新业务术语
export function useUpdateGlossaryTerm() {
  const queryClient = useQueryClient()
  const setEditingGlossary = useMetadataStore(state => state.setEditingGlossary)
  const addNotification = useAppStore(state => state.addNotification)

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      metadataService.updateGlossaryTerm(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['glossary'] })
      setEditingGlossary(null)
      addNotification({
        id: Date.now().toString(),
        type: 'success',
        title: '更新成功',
        message: '业务术语已更新'
      })
    },
    onError: (error: any) => {
      addNotification({
        id: Date.now().toString(),
        type: 'error',
        title: '更新失败',
        message: error.message || '更新业务术语失败'
      })
    }
  })
}

// 关联配置查询
export function useRelationConfigs() {
  return useQuery({
    queryKey: ['relations'],
    queryFn: () => metadataService.getRelationConfigs(),
    staleTime: 5 * 60 * 1000,
  })
}

// 数据主题查询
export function useThemes() {
  return useQuery({
    queryKey: ['themes'],
    queryFn: () => metadataService.getThemes(),
    staleTime: 5 * 60 * 1000,
    select: (data) => data.sort((a, b) => a.theme_name.localeCompare(b.theme_name)),
  })
}

// 批量更新表和字段
export function useBatchUpdate() {
  const queryClient = useQueryClient()
  const addNotification = useAppStore(state => state.addNotification)

  return useMutation({
    mutationFn: metadataService.batchUpdateTableAndColumns,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tables'] })
      addNotification({
        id: Date.now().toString(),
        type: 'success',
        title: '批量更新成功',
        message: `成功更新 ${data.success_count} 项，失败 ${data.error_count} 项`
      })
    },
    onError: (error: any) => {
      addNotification({
        id: Date.now().toString(),
        type: 'error',
        title: '批量更新失败',
        message: error.message || '批量更新操作失败'
      })
    }
  })
}