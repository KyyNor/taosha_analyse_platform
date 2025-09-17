import axios from 'axios'
import type {
  ApiResponse,
  QueryRequest,
  QueryResponse,
  TableMetadata,
  ColumnMetadata,
  ColumnUpdateRequest,
  Term,
  RelationConfig,
  SystemStatus,
  DataTable,
  OperationSession,
  OperationStep,
  OperationStats
} from '@/types'

// 创建axios实例
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 240000, // 4分钟超时
})

// 响应拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export class TaoshaAPIClient {
  // 健康检查
  async healthCheck(): Promise<boolean> {
    try {
      const response = await api.get('/health')
      return response.status === 200
    } catch {
      return false
    }
  }

  // 系统状态
  async getSystemStatus(): Promise<SystemStatus | null> {
    try {
      const response = await api.get<SystemStatus>('/status')
      return response.data
    } catch (error) {
      console.error('获取系统状态失败:', error)
      return null
    }
  }

  // 数据查询
  async query(queryText: string, maxRetries: number = 2): Promise<QueryResponse> {
    try {
      const response = await api.post<QueryResponse>('/query', {
        query: queryText,
        max_retries: maxRetries
      })
      return response.data
    } catch (error: any) {
      return {
        success: false,
        error: `查询失败: ${error.message || error}`
      }
    }
  }

  // 获取数据表信息
  async getTables(): Promise<DataTable[]> {
    try {
      const response = await api.get<DataTable[]>('/tables')
      return response.data
    } catch (error) {
      console.error('获取数据表信息失败:', error)
      return []
    }
  }

  // ===== 元数据管理 =====

  // 获取所有表元数据
  async getAllMetadataTables(): Promise<TableMetadata[]> {
    try {
      const response = await api.get<ApiResponse<TableMetadata[]>>('/dev/metadata/tables')
      return response.data.data || []
    } catch (error) {
      console.error('获取表元数据失败:', error)
      return []
    }
  }

  // 添加表元数据
  async addTableMetadata(name: string, comment: string, isAvailable: number = 0): Promise<boolean> {
    try {
      await api.post('/dev/metadata/tables', {
        name,
        comment,
        is_available: isAvailable
      })
      return true
    } catch (error) {
      console.error('添加表元数据失败:', error)
      return false
    }
  }

  // 更新表元数据
  async updateTableMetadata(tableName: string, comment?: string, isAvailable?: number): Promise<boolean> {
    try {
      const updateData: any = {}
      if (comment !== undefined) updateData.comment = comment
      if (isAvailable !== undefined) updateData.is_available = isAvailable

      await api.put(`/dev/metadata/tables/${tableName}`, updateData)
      return true
    } catch (error) {
      console.error('更新表元数据失败:', error)
      return false
    }
  }

  // 删除表元数据
  async deleteTableMetadata(tableName: string): Promise<boolean> {
    try {
      await api.delete(`/dev/metadata/tables/${tableName}`)
      return true
    } catch (error) {
      console.error('删除表元数据失败:', error)
      return false
    }
  }

  // 添加列元数据
  async addColumnMetadata(
    tableName: string,
    columnName: string,
    columnType: string,
    comment: string,
    isAvailable: number = 0,
    businessType: string = '',
    relationId: string = ''
  ): Promise<boolean> {
    try {
      await api.post('/dev/metadata/columns', {
        table_name: tableName,
        name: columnName,
        type: columnType,
        comment,
        is_available: isAvailable,
        business_type: businessType,
        relation_id: relationId
      })
      return true
    } catch (error) {
      console.error('添加列元数据失败:', error)
      return false
    }
  }

  // 更新列元数据
  async updateColumnMetadata(
    tableName: string,
    columnName: string,
    updateData: ColumnUpdateRequest
  ): Promise<boolean> {
    try {
      await api.put(`/dev/metadata/columns/${tableName}/${columnName}`, updateData)
      return true
    } catch (error) {
      console.error('更新列元数据失败:', error)
      return false
    }
  }

  // 删除列元数据
  async deleteColumnMetadata(tableName: string, columnName: string): Promise<boolean> {
    try {
      await api.delete(`/dev/metadata/columns/${tableName}/${columnName}`)
      return true
    } catch (error) {
      console.error('删除列元数据失败:', error)
      return false
    }
  }

  // ===== 术语管理 =====

  // 获取所有术语
  async getAllTerms(): Promise<Term[]> {
    try {
      const response = await api.get<ApiResponse<Term[]>>('/dev/glossary/terms')
      return response.data.data || []
    } catch (error) {
      console.error('获取术语失败:', error)
      return []
    }
  }

  // 添加术语
  async addTerm(term: string, definition: string, sqlExpression: string, category: string, aliases: string[]): Promise<boolean> {
    try {
      await api.post('/dev/glossary/terms', {
        term,
        definition,
        sql_expression: sqlExpression,
        category,
        aliases
      })
      return true
    } catch (error) {
      console.error('添加术语失败:', error)
      return false
    }
  }

  // 更新术语
  async updateTerm(termId: number, updates: Partial<Term>): Promise<boolean> {
    try {
      await api.put(`/dev/glossary/terms/${termId}`, updates)
      return true
    } catch (error) {
      console.error('更新术语失败:', error)
      return false
    }
  }

  // 删除术语
  async deleteTerm(termId: number): Promise<boolean> {
    try {
      await api.delete(`/dev/glossary/terms/${termId}`)
      return true
    } catch (error) {
      console.error('删除术语失败:', error)
      return false
    }
  }

  // ===== 关联配置管理 =====

  // 获取所有关联配置
  async getAllRelationConfigs(): Promise<RelationConfig[]> {
    try {
      const response = await api.get<ApiResponse<RelationConfig[]>>('/dev/relation-configs')
      return response.data.data || []
    } catch (error) {
      console.error('获取关联配置失败:', error)
      return []
    }
  }

  // 获取关联ID列表
  async getRelationIds(): Promise<string[]> {
    try {
      const response = await api.get<ApiResponse<string[]>>('/dev/relation-configs/ids')
      return response.data.data || []
    } catch (error) {
      console.error('获取关联ID列表失败:', error)
      return []
    }
  }

  // 添加关联配置
  async addRelationConfig(family: string, subfamily: string, desc: string = ''): Promise<boolean> {
    try {
      await api.post('/dev/relation-configs', {
        relation_family: family,
        relation_subfamily: subfamily,
        relation_desc: desc
      })
      return true
    } catch (error) {
      console.error('添加关联配置失败:', error)
      return false
    }
  }

  // 更新关联配置
  async updateRelationConfig(relationId: string, updates: Partial<RelationConfig>): Promise<boolean> {
    try {
      const updateData: any = {}
      if (updates.relation_family !== undefined) updateData.relation_family = updates.relation_family
      if (updates.relation_subfamily !== undefined) updateData.relation_subfamily = updates.relation_subfamily
      if (updates.relation_desc !== undefined) updateData.relation_desc = updates.relation_desc

      await api.put(`/dev/relation-configs/${relationId}`, updateData)
      return true
    } catch (error) {
      console.error('更新关联配置失败:', error)
      return false
    }
  }

  // 删除关联配置
  async deleteRelationConfig(relationId: string): Promise<boolean> {
    try {
      await api.delete(`/dev/relation-configs/${relationId}`)
      return true
    } catch (error) {
      console.error('删除关联配置失败:', error)
      return false
    }
  }

  // ===== 操作追踪管理 =====

  // 获取会话列表
  async getOperationSessions(page: number = 1, limit: number = 20, search?: string): Promise<{sessions: OperationSession[], total: number}> {
    try {
      const params: any = { page, limit }
      if (search) params.q = search
      
      const response = await api.get<ApiResponse<{sessions: OperationSession[], total: number}>>('/tracking/sessions', { params })
      return response.data.data || { sessions: [], total: 0 }
    } catch (error) {
      console.error('获取操作会话失败:', error)
      return { sessions: [], total: 0 }
    }
  }

  // 获取会话详情
  async getOperationSession(sessionId: string): Promise<OperationSession | null> {
    try {
      const response = await api.get<ApiResponse<OperationSession>>(`/tracking/sessions/${sessionId}`)
      return response.data.data || null
    } catch (error) {
      console.error('获取会话详情失败:', error)
      return null
    }
  }

  // 获取会话步骤
  async getOperationSteps(sessionId: string): Promise<OperationStep[]> {
    try {
      const response = await api.get<ApiResponse<OperationStep[]>>(`/tracking/sessions/${sessionId}/steps`)
      return response.data.data || []
    } catch (error) {
      console.error('获取会话步骤失败:', error)
      return []
    }
  }

  // 获取统计信息
  async getOperationStats(): Promise<OperationStats | null> {
    try {
      const response = await api.get<ApiResponse<OperationStats>>('/tracking/stats')
      return response.data.data || null
    } catch (error) {
      console.error('获取统计信息失败:', error)
      return null
    }
  }

  // 搜索会话
  async searchOperationSessions(query: string): Promise<OperationSession[]> {
    try {
      const response = await api.get<ApiResponse<OperationSession[]>>('/tracking/search', {
        params: { q: query }
      })
      return response.data.data || []
    } catch (error) {
      console.error('搜索会话失败:', error)
      return []
    }
  }
}

// 创建单例API客户端
export const apiClient = new TaoshaAPIClient()
export default apiClient