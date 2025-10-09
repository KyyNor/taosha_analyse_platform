import { api } from './client'
import type {
  TableMetadata,
  ColumnMetadata,
  GlossaryTerm,
  RelationConfig,
  DataTheme,
  PaginatedResponse
} from '@types/index'

class MetadataService {
  // === Table Metadata ===

  // Get all tables
  async getTables(dataSource?: string, isActive?: boolean): Promise<TableMetadata[]> {
    const params = new URLSearchParams()
    if (dataSource) params.append('dataSource', dataSource)
    if (isActive !== undefined) params.append('isAvailable', isActive ? '1' : '0')

    return await api.get(`/metadata/tables?${params}`)
  }

  // Get table by ID
  async getTable(id: number): Promise<TableMetadata> {
    return await api.get(`/metadata/tables/${id}`)
  }

  // Create new table
  async createTable(data: {
    name: string
    comment: string
    isAvailable: boolean
    dataSource?: string
    updateMethod?: string
  }): Promise<TableMetadata> {
    return await api.post('/metadata/tables', data)
  }

  // Update table
  async updateTable(id: number, data: {
    comment?: string
    isAvailable?: boolean
    dataSource?: string
    updateMethod?: string
  }): Promise<TableMetadata> {
    return await api.put(`/metadata/tables/${id}`, data)
  }

  // Delete table
  async deleteTable(id: number): Promise<void> {
    return await api.delete(`/metadata/tables/${id}`)
  }

  // Get table schema information
  async getTableSchema(tableName: string): Promise<{
    columns: ColumnMetadata[]
    relationships: any[]
    sampleData: any[]
  }> {
    return await api.get(`/metadata/tables/${tableName}/schema`)
  }

  // === Column Metadata ===

  // Get columns for a table
  async getColumns(tableId: number): Promise<ColumnMetadata[]> {
    return await api.get(`/metadata/columns?tableId=${tableId}`)
  }

  // Get column by ID
  async getColumn(id: number): Promise<ColumnMetadata> {
    return await api.get(`/metadata/columns/${id}`)
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
    return await api.post('/metadata/columns', data)
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
    return await api.put(`/metadata/columns/${id}`, data)
  }

  // Delete column
  async deleteColumn(id: number): Promise<void> {
    return await api.delete(`/metadata/columns/${id}`)
  }

  // === Glossary Management ===

  // Get all terms
  async getTerms(category?: string): Promise<GlossaryTerm[]> {
    const params = category ? `?category=${category}` : ''
    return await api.get(`/metadata/glossary/terms${params}`)
  }

  // Search terms
  async searchTerms(query: string): Promise<GlossaryTerm[]> {
    return await api.get(`/metadata/glossary/search?q=${encodeURIComponent(query)}`)
  }

  // Get term by ID
  async getTerm(id: number): Promise<GlossaryTerm> {
    return await api.get(`/metadata/glossary/terms/${id}`)
  }

  // Create new term
  async createTerm(data: {
    term: string
    definition: string
    sqlExpression?: string
    category?: string
    aliases?: string[]
  }): Promise<GlossaryTerm> {
    return await api.post('/metadata/glossary/terms', data)
  }

  // Update term
  async updateTerm(id: number, data: {
    term?: string
    definition?: string
    sqlExpression?: string
    category?: string
    aliases?: string[]
  }): Promise<GlossaryTerm> {
    return await api.put(`/metadata/glossary/terms/${id}`, data)
  }

  // Delete term
  async deleteTerm(id: number): Promise<void> {
    return await api.delete(`/metadata/glossary/terms/${id}`)
  }

  // === Relation Configuration ===

  // Get all relation configurations
  async getRelationConfigs(): Promise<RelationConfig[]> {
    return await api.get('/metadata/relation-configs')
  }

  // Get relation config by ID
  async getRelationConfig(id: string): Promise<RelationConfig> {
    return await api.get(`/metadata/relation-configs/${id}`)
  }

  // Create new relation config
  async createRelationConfig(data: {
    relationFamily: string
    relationSubfamily: string
    relationDesc: string
  }): Promise<RelationConfig> {
    return await api.post('/metadata/relation-configs', data)
  }

  // Update relation config
  async updateRelationConfig(id: string, data: {
    relationFamily?: string
    relationSubfamily?: string
    relationDesc?: string
  }): Promise<RelationConfig> {
    return await api.put(`/metadata/relation-configs/${id}`, data)
  }

  // Delete relation config
  async deleteRelationConfig(id: string): Promise<void> {
    return await api.delete(`/metadata/relation-configs/${id}`)
  }

  // === Data Themes ===

  // Get all themes
  async getThemes(): Promise<DataTheme[]> {
    return await api.get('/metadata/themes')
  }

  // Get theme by ID
  async getTheme(id: number): Promise<DataTheme> {
    return await api.get(`/metadata/themes/${id}`)
  }

  // Create new theme
  async createTheme(data: {
    themeName: string
    themeDescription: string
    themeType: 'public' | 'normal'
  }): Promise<DataTheme> {
    return await api.post('/metadata/themes', data)
  }

  // Update theme
  async updateTheme(id: number, data: {
    themeName?: string
    themeDescription?: string
    themeType?: 'public' | 'normal'
  }): Promise<DataTheme> {
    return await api.put(`/metadata/themes/${id}`, data)
  }

  // Delete theme
  async deleteTheme(id: number): Promise<void> {
    return await api.delete(`/metadata/themes/${id}`)
  }

  // Get tables in a theme
  async getThemeTables(themeId: number): Promise<TableMetadata[]> {
    return await api.get(`/metadata/themes/${themeId}/tables`)
  }

  // Add table to theme
  async addTableToTheme(themeId: number, tableId: number): Promise<void> {
    return await api.post(`/metadata/themes/${themeId}/tables`, { tableId })
  }

  // Remove table from theme
  async removeTableFromTheme(themeId: number, tableId: number): Promise<void> {
    return await api.delete(`/metadata/themes/${themeId}/tables/${tableId}`)
  }

  // === Database Sync ===

  // Sync metadata from actual database
  async syncFromDatabase(): Promise<{
    success: boolean
    message: string
    syncedTables: string[]
  }> {
    return await api.post('/metadata/sync-from-database')
  }

  // Get sync status
  async getSyncStatus(): Promise<{
    lastSyncTime: string
    pendingSyncCount: number
    syncing: boolean
  }> {
    return await api.get('/metadata/sync-status')
  }

  // === Import/Export ===

  // Export metadata
  async exportMetadata(format: 'json' | 'xlsx'): Promise<Blob> {
    const response = await api.getRaw(`/metadata/export?format=${format}`)
    return response.data
  }

  // Import metadata
  async importMetadata(file: File, type: 'tables' | 'columns' | 'glossary'): Promise<{
    success: boolean
    message: string
    importedCount: number
    errors: string[]
  }> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('type', type)

    return await api.post('/metadata/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  }

  // Get import template
  async getImportTemplate(type: 'tables' | 'columns' | 'glossary'): Promise<Blob> {
    const response = await api.getRaw(`/metadata/import-template/${type}`)
    return response.data
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
    return await api.get('/metadata/validate')
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
    const params = new URLSearchParams({ q: query })
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value)
      })
    }

    return await api.get(`/metadata/search?${params}`)
  }

  // Get metadata statistics
  async getStatistics(): Promise<{
    totalTables: number
    totalColumns: number
    totalTerms: number
    totalRelations: number
    tablesByDataSource: Array<{ dataSource: string; count: number }>
    termsByCategory: Array<{ category: string; count: number }>
  }> {
    return await api.get('/metadata/statistics')
  }
}

export default new MetadataService()