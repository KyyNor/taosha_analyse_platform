import { api } from './client'
import { API_ENDPOINTS, buildApiUrl, replaceUrlParams } from '@/config/api'
import type {
  TableMetadata,
  ColumnMetadata,
  GlossaryTerm,
  RelationConfig,
  DataTheme,
} from '@types/index'

class MetadataService {
  // === Table Metadata ===

  // Get all tables
  async getTables(dataSource?: string, isActive?: boolean): Promise<TableMetadata[]> {
    const params: Record<string, any> = {}
    if (dataSource) params.dataSource = dataSource
    if (isActive !== undefined) params.isAvailable = isActive ? '1' : '0'

    return await api.get(buildApiUrl(API_ENDPOINTS.METADATA.TABLES.LIST, params))
  }

  // Get table by ID
  async getTable(id: number): Promise<TableMetadata> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.TABLES.DETAIL, { id })
    return await api.get(buildApiUrl(url))
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
    return await api.get(buildApiUrl(url))
  }

  // === Column Metadata ===

  // Get columns for a table
  async getColumns(tableId: number): Promise<ColumnMetadata[]> {
    return await api.get(buildApiUrl(API_ENDPOINTS.METADATA.COLUMNS.LIST, { tableId }))
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
  async getTerms(category?: string): Promise<GlossaryTerm[]> {
    const params = category ? { category } : {}
    return await api.get(buildApiUrl(API_ENDPOINTS.METADATA.GLOSSARY.TERMS.LIST, params))
  }

  // Search terms
  async searchTerms(query: string): Promise<GlossaryTerm[]> {
    return await api.get(buildApiUrl(API_ENDPOINTS.METADATA.GLOSSARY.TERMS.SEARCH, { q: query }))
  }

  // Get term by ID
  async getTerm(id: number): Promise<GlossaryTerm> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.GLOSSARY.TERMS.DETAIL, { id })
    return await api.get(buildApiUrl(url))
  }

  // Create new term
  async createTerm(data: {
    term: string
    definition: string
    sqlExpression?: string
    category?: string
    aliases?: string[]
  }): Promise<GlossaryTerm> {
    return await api.post(buildApiUrl(API_ENDPOINTS.METADATA.GLOSSARY.TERMS.CREATE), data)
  }

  // Update term
  async updateTerm(id: number, data: {
    term?: string
    definition?: string
    sqlExpression?: string
    category?: string
    aliases?: string[]
  }): Promise<GlossaryTerm> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.GLOSSARY.TERMS.UPDATE, { id })
    return await api.put(buildApiUrl(url), data)
  }

  // Delete term
  async deleteTerm(id: number): Promise<void> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.GLOSSARY.TERMS.DELETE, { id })
    return await api.delete(buildApiUrl(url))
  }

  // === Relation Configuration ===

  // Get all relation configurations
  async getRelationConfigs(): Promise<RelationConfig[]> {
    return await api.get(buildApiUrl(API_ENDPOINTS.METADATA.RELATIONS.LIST))
  }

  // Get relation config by ID
  async getRelationConfig(id: string): Promise<RelationConfig> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.RELATIONS.DETAIL, { id })
    return await api.get(buildApiUrl(url))
  }

  // Create new relation config
  async createRelationConfig(data: {
    relationFamily: string
    relationSubfamily: string
    relationDesc: string
  }): Promise<RelationConfig> {
    return await api.post(buildApiUrl(API_ENDPOINTS.METADATA.RELATIONS.CREATE), data)
  }

  // Update relation config
  async updateRelationConfig(id: string, data: {
    relationFamily?: string
    relationSubfamily?: string
    relationDesc?: string
  }): Promise<RelationConfig> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.RELATIONS.UPDATE, { id })
    return await api.put(buildApiUrl(url), data)
  }

  // Delete relation config
  async deleteRelationConfig(id: string): Promise<void> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.RELATIONS.DELETE, { id })
    return await api.delete(buildApiUrl(url))
  }

  // === Data Themes ===

  // Get all themes
  async getThemes(): Promise<DataTheme[]> {
    return await api.get(buildApiUrl(API_ENDPOINTS.METADATA.THEMES.LIST))
  }

  // Get theme by ID
  async getTheme(id: number): Promise<DataTheme> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.THEMES.DETAIL, { id })
    return await api.get(buildApiUrl(url))
  }

  // Create new theme
  async createTheme(data: {
    themeName: string
    themeDescription: string
    themeType: 'public' | 'normal'
  }): Promise<DataTheme> {
    return await api.post(buildApiUrl(API_ENDPOINTS.METADATA.THEMES.CREATE), data)
  }

  // Update theme
  async updateTheme(id: number, data: {
    themeName?: string
    themeDescription?: string
    themeType?: 'public' | 'normal'
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
    return await api.get(buildApiUrl(url))
  }

  // Add table to theme
  async addTableToTheme(themeId: number, tableId: number): Promise<void> {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.THEMES.TABLES, { themeId })
    return await api.post(buildApiUrl(url), { tableId })
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
    return await api.get(buildApiUrl(API_ENDPOINTS.METADATA.VALIDATE))
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

    return await api.get(buildApiUrl(API_ENDPOINTS.METADATA.SEARCH, params))
  }
}

export default new MetadataService()
