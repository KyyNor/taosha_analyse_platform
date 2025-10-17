import { api } from './client'
import { API_ENDPOINTS, buildApiUrl, replaceUrlParams } from '@/config/api'
import type {
  TableMetadata,
  ColumnMetadata,
  GlossaryTerm,
  RelationConfig,
  DataTheme
} from '@types/index'

class MetadataService {
  // === Table Metadata ===

  // Get all tables
  async getTables(dataSource?: string, isActive?: boolean): Promise<TableMetadata[]> {
    const params: Record<string, any> = {}
    if (dataSource) params.dataSource = dataSource
    if (isActive !== undefined) params.isAvailable = isActive ? '1' : '0'

    const response = await api.get(buildApiUrl(API_ENDPOINTS.METADATA.TABLES.LIST, params))
    // Extract data from response object
    return response.data || []
  }

  // Get table by ID
  async getTable(id: number): Promise<TableMetadata> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.TABLES.DETAIL, { id })
    const response = await api.get(buildApiUrl(url))
    return response.data
  }

  // Create new table
  async createTable(data: {
    name: string
    comment: string
    isAvailable: boolean
    dataSource?: string
    updateMethod?: string
  }): Promise<TableMetadata> {
    return await api.post(buildApiUrl(API_ENDPOINTS.METADATA.TABLES.CREATE), data)
  }

  // Update table
  async updateTable(id: number, data: {
    comment?: string
    isAvailable?: boolean
    dataSource?: string
    updateMethod?: string
  }): Promise<TableMetadata> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.TABLES.UPDATE, { id })
    return await api.put(buildApiUrl(url), data)
  }

  // Delete table
  async deleteTable(id: number): Promise<void> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.TABLES.DELETE, { id })
    return await api.delete(buildApiUrl(url))
  }

  // Get table schema information
  async getTableSchema(tableName: string): Promise<{
    columns: ColumnMetadata[]
    relationships: any[]
    sampleData: any[]
  }> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.TABLES.SCHEMA, { tableName })
    const response = await api.get(buildApiUrl(url))
    return response.data
  }

  // === Column Metadata ===

  // Get columns for a table
  async getColumns(tableId: number): Promise<ColumnMetadata[]> {
    const response = await api.get(buildApiUrl(API_ENDPOINTS.METADATA.COLUMNS.LIST, { tableId }))
    return response.data || []
  }

  // Get column by ID
  async getColumn(id: number): Promise<ColumnMetadata> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.COLUMNS.DETAIL, { id })
    return await api.get(buildApiUrl(url))
  }

  // Create new column
  async createColumn(data: {
    tableName: string
    name: string
    type: string
    comment: string
    isAvailable: boolean
    businessType: string
    relationId?: string
    sampleValues?: string[]
  }): Promise<ColumnMetadata> {
    return await api.post(buildApiUrl(API_ENDPOINTS.METADATA.COLUMNS.CREATE), data)
  }

  // Update column
  async updateColumn(id: number, data: {
    type?: string
    comment?: string
    isAvailable?: boolean
    businessType?: string
    relationId?: string
    sampleValues?: string[]
  }): Promise<ColumnMetadata> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.COLUMNS.UPDATE, { id })
    return await api.put(buildApiUrl(url), data)
  }

  // Delete column
  async deleteColumn(id: number): Promise<void> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.COLUMNS.DELETE, { id })
    return await api.delete(buildApiUrl(url))
  }

  // === Glossary Management ===

  // Get all terms
  async getGlossaryTerms(): Promise<any[]> {
    const response = await api.get(buildApiUrl(API_ENDPOINTS.METADATA.GLOSSARY.TERMS.LIST))
    return response.data || []
  }

  // Get terms by type
  async getGlossaryTermsByType(type: string): Promise<any[]> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.GLOSSARY.TERMS.BY_TYPE, { type })
    const response = await api.get(buildApiUrl(url))
    return response.data || []
  }

  // Search terms
  async searchGlossaryTerms(query: string): Promise<any> {
    const response = await api.get(buildApiUrl(API_ENDPOINTS.METADATA.GLOSSARY.TERMS.SEARCH, { q: query }))
    return response.data
  }

  // Create new term
  async createGlossaryTerm(data: {
    name: string
    type: string
    content: any
    creator?: string
  }): Promise<any> {
    return await api.post(buildApiUrl(API_ENDPOINTS.METADATA.GLOSSARY.TERMS.CREATE), data)
  }

  // Update term
  async updateGlossaryTerm(id: number, data: {
    name?: string
    type?: string
    content?: any
  }): Promise<any> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.GLOSSARY.TERMS.UPDATE, { id })
    return await api.put(buildApiUrl(url), data)
  }

  // Delete term
  async deleteGlossaryTerm(id: number): Promise<void> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.GLOSSARY.TERMS.DELETE, { id })
    return await api.delete(buildApiUrl(url))
  }

  // === Relation Configuration ===

  // Get all relation configurations
  async getRelationConfigs(): Promise<any[]> {
    const response = await api.get(buildApiUrl(API_ENDPOINTS.METADATA.RELATIONS.LIST))
    return response.data || []
  }

  // Create new relation config
  async createRelationConfig(data: {
    relation_family: string
    relation_subfamily: string
    relation_desc?: string
  }): Promise<any> {
    return await api.post(buildApiUrl(API_ENDPOINTS.METADATA.RELATIONS.CREATE), data)
  }

  // Update relation config
  async updateRelationConfig(id: string, data: {
    relation_family?: string
    relation_subfamily?: string
    relation_desc?: string
  }): Promise<any> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.RELATIONS.UPDATE, { id })
    return await api.put(buildApiUrl(url), data)
  }

  // Delete relation config
  async deleteRelationConfig(id: string): Promise<void> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.RELATIONS.DELETE, { id })
    return await api.delete(buildApiUrl(url))
  }

  // === Prompt Templates ===

  // Get all prompt templates
  async getPromptTemplates(): Promise<any[]> {
    const response = await api.get(buildApiUrl(API_ENDPOINTS.METADATA.PROMPT_TEMPLATES.LIST))
    return response.data || []
  }

  // Create new prompt template
  async createPromptTemplate(data: {
    name: string
    fields: string[]
    template: string
  }): Promise<any> {
    return await api.post(buildApiUrl(API_ENDPOINTS.METADATA.PROMPT_TEMPLATES.CREATE), data)
  }

  // Update prompt template
  async updatePromptTemplate(id: number, data: {
    name?: string
    template?: string
  }): Promise<any> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.PROMPT_TEMPLATES.UPDATE, { id })
    return await api.put(buildApiUrl(url), data)
  }

  // Delete prompt template
  async deletePromptTemplate(id: number): Promise<void> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.PROMPT_TEMPLATES.DELETE, { id })
    return await api.delete(buildApiUrl(url))
  }

  // === Data Themes ===

  // Get all themes
  async getThemes(): Promise<DataTheme[]> {
    const response = await api.get(buildApiUrl(API_ENDPOINTS.METADATA.THEMES.LIST))
    return response.data || []
  }

  // Get theme by ID
  async getTheme(id: number): Promise<DataTheme> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.THEMES.DETAIL, { id })
    const response = await api.get(buildApiUrl(url))
    return response.data
  }

  // Create new theme
  async createTheme(data: {
    theme_name: string
    theme_description: string
    theme_type: 'public' | 'normal'
    department: string
  }): Promise<DataTheme> {
    return await api.post(buildApiUrl(API_ENDPOINTS.METADATA.THEMES.CREATE), data)
  }

  // Update theme
  async updateTheme(id: number, data: {
    theme_name?: string
    theme_description?: string
    theme_type?: 'public' | 'normal'
    department?: string
  }): Promise<DataTheme> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.THEMES.UPDATE, { id })
    return await api.put(buildApiUrl(url), data)
  }

  // Delete theme
  async deleteTheme(id: number): Promise<void> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.THEMES.DELETE, { id })
    return await api.delete(buildApiUrl(url))
  }

  // Get tables in a theme
  async getThemeTables(themeId: number): Promise<TableMetadata[]> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.THEMES.TABLES, { themeId })
    const response = await api.get(buildApiUrl(url))
    return response.data || []
  }

  // Add table to theme
  async addTableToTheme(themeId: number, tableId: number): Promise<void> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.THEMES.TABLES, { themeId })
    return await api.post(buildApiUrl(url), { table_id: tableId })
  }

  // Remove table from theme
  async removeTableFromTheme(themeId: number, tableId: number): Promise<void> {
    const url = `${replaceUrlParams(API_ENDPOINTS.METADATA.THEMES.TABLES, { themeId })  }/${tableId}`
    return await api.delete(buildApiUrl(url))
  }

  // === Validation ===

  // Validate metadata configuration
  async validateConfig(): Promise<{
    valid: boolean
    errors: Array<{
      type: 'table' | 'column' | 'relation' | 'glossary'
      id: number | string
      message: string
    }>
    warnings: Array<{
      type: 'table' | 'column' | 'relation' | 'glossary'
      id: number | string
      message: string
    }>
  }> {
    const response = await api.get(buildApiUrl(API_ENDPOINTS.METADATA.VALIDATE))
    return response.data
  }

  // === Search and Filter ===

  // Search metadata
  async searchMetadata(query: string, filters?: {
    type?: 'table' | 'column' | 'glossary'
    dataSource?: string
    category?: string
  }): Promise<{
    tables: TableMetadata[]
    columns: ColumnMetadata[]
    terms: GlossaryTerm[]
  }> {
    const params: Record<string, any> = { q: query }
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params[key] = value
      })
    }

    const response = await api.get(buildApiUrl(API_ENDPOINTS.METADATA.SEARCH, params))
    return response.data
  }
}

export default new MetadataService()
