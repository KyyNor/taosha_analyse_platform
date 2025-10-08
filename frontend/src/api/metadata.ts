/**
 * 元数据管理相关API
 */
import { apiClient } from './client'
import type { ApiResponse, PaginatedResponse } from './client'

// 元数据相关类型定义
export interface DataTheme {
  id: number
  name: string
  description?: string
  icon?: string
  color?: string
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface DataTable {
  id: number
  theme_id: number
  table_name: string
  table_alias: string
  table_description?: string
  is_active: boolean
  created_at: string
  updated_at: string
  theme?: DataTheme
}

export interface DataField {
  id: number
  table_id: number
  field_name: string
  field_alias: string
  field_description?: string
  data_type: string
  is_primary_key: boolean
  is_nullable: boolean
  default_value?: string
  is_active: boolean
  created_at: string
  updated_at: string
  table?: DataTable
}

export interface GlossaryTerm {
  id: number
  term_name: string
  term_description: string
  category?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// API请求参数类型
export interface ThemeListParams {
  page?: number
  size?: number
  keyword?: string
  is_active?: boolean
}

export interface TableListParams {
  page?: number
  size?: number
  theme_id?: number
  keyword?: string
  is_active?: boolean
}

export interface FieldListParams {
  page?: number
  size?: number
  table_id?: number
  keyword?: string
  is_active?: boolean
}

export interface GlossaryListParams {
  page?: number
  size?: number
  keyword?: string
  category?: string
  is_active?: boolean
}

/**
 * 元数据API类
 */
export class MetadataApi {
  // 数据主题相关
  async getThemes(params?: ThemeListParams): Promise<ApiResponse<DataTheme[]>> {
    const response = await apiClient.get('/metadata/themes', { params })
    // 从分页响应中提取items
    return {
      ...response,
      data: response.data.items || []
    }
  }

  async getTheme(id: number): Promise<ApiResponse<DataTheme>> {
    return apiClient.get(`/metadata/themes/${id}`)
  }

  async createTheme(data: Partial<DataTheme>): Promise<ApiResponse<DataTheme>> {
    return apiClient.post('/metadata/themes', data)
  }

  async updateTheme(id: number, data: Partial<DataTheme>): Promise<ApiResponse<DataTheme>> {
    return apiClient.put(`/metadata/themes/${id}`, data)
  }

  async deleteTheme(id: number): Promise<ApiResponse<void>> {
    return apiClient.delete(`/metadata/themes/${id}`)
  }

  // 数据表相关
  async getTables(params?: TableListParams): Promise<ApiResponse<PaginatedResponse<DataTable>>> {
    return apiClient.get('/metadata/tables', { params })
  }

  async getTable(id: number): Promise<ApiResponse<DataTable>> {
    return apiClient.get(`/metadata/tables/${id}`)
  }

  async getTablesByTheme(themeId: number): Promise<ApiResponse<DataTable[]>> {
    const response = await apiClient.get('/metadata/tables', { 
      params: { theme_id: themeId, size: 100 } 
    })
    // 从分页响应中提取items
    return {
      ...response,
      data: response.data.items || []
    }
  }

  async createTable(data: Partial<DataTable>): Promise<ApiResponse<DataTable>> {
    return apiClient.post('/metadata/tables', data)
  }

  async updateTable(id: number, data: Partial<DataTable>): Promise<ApiResponse<DataTable>> {
    return apiClient.put(`/metadata/tables/${id}`, data)
  }

  async deleteTable(id: number): Promise<ApiResponse<void>> {
    return apiClient.delete(`/metadata/tables/${id}`)
  }

  // 数据字段相关
  async getFields(params?: FieldListParams): Promise<ApiResponse<PaginatedResponse<DataField>>> {
    return apiClient.get('/metadata/fields', { params })
  }

  async getField(id: number): Promise<ApiResponse<DataField>> {
    return apiClient.get(`/metadata/fields/${id}`)
  }

  async createField(data: Partial<DataField>): Promise<ApiResponse<DataField>> {
    return apiClient.post('/metadata/fields', data)
  }

  async updateField(id: number, data: Partial<DataField>): Promise<ApiResponse<DataField>> {
    return apiClient.put(`/metadata/fields/${id}`, data)
  }

  async deleteField(id: number): Promise<ApiResponse<void>> {
    return apiClient.delete(`/metadata/fields/${id}`)
  }

  // 术语词汇相关
  async getGlossaryTerms(params?: GlossaryListParams): Promise<ApiResponse<PaginatedResponse<GlossaryTerm>>> {
    return apiClient.get('/metadata/glossary', { params })
  }

  async getGlossaryTerm(id: number): Promise<ApiResponse<GlossaryTerm>> {
    return apiClient.get(`/metadata/glossary/${id}`)
  }

  async createGlossaryTerm(data: Partial<GlossaryTerm>): Promise<ApiResponse<GlossaryTerm>> {
    return apiClient.post('/metadata/glossary', data)
  }

  async updateGlossaryTerm(id: number, data: Partial<GlossaryTerm>): Promise<ApiResponse<GlossaryTerm>> {
    return apiClient.put(`/metadata/glossary/${id}`, data)
  }

  async deleteGlossaryTerm(id: number): Promise<ApiResponse<void>> {
    return apiClient.delete(`/metadata/glossary/${id}`)
  }

  // 元数据统计
  async getMetadataStats(): Promise<ApiResponse<{
    theme_count: number
    table_count: number
    field_count: number
    glossary_count: number
  }>> {
    return apiClient.get('/metadata/stats')
  }

  // 元数据搜索
  async searchMetadata(keyword: string): Promise<ApiResponse<{
    themes: DataTheme[]
    tables: DataTable[]
    fields: DataField[]
    glossary: GlossaryTerm[]
  }>> {
    return apiClient.get('/metadata/search', { params: { keyword } })
  }
}

// 导出API实例
export const metadataApi = new MetadataApi()

// 默认导出
export default metadataApi