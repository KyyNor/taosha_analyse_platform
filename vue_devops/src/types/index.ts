// 通用响应类型
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

// 查询相关类型
export interface QueryRequest {
  query: string
  max_retries?: number
}

export interface QueryResponse {
  success: boolean
  sql_query?: string
  data?: any[]
  error?: string
  logs?: QueryLog[]
  clear_check_details?: ClarityCheck
}

export interface QueryLog {
  step: string
  success: boolean
  timestamp: string
  input_data?: string
  model_output?: string
  error?: string
  prompt?: string
}

export interface ClarityCheck {
  is_clear: boolean
  reason?: string
  suggestions?: string[]
}

// 元数据相关类型
export interface TableMetadata {
  name: string
  comment?: string
  is_available: number
  columns?: ColumnMetadata[]
}

export interface ColumnMetadata {
  name: string
  type: string
  comment?: string
  is_available: number
  business_type?: string
  relation_id?: string
}

export interface ColumnUpdateRequest {
  type?: string
  comment?: string
  is_available?: number
  business_type?: string
  relation_id?: string
}

// 术语相关类型
export interface Term {
  id?: number
  term: string
  definition: string
  sql_expression: string
  category: string
  aliases: string[]
}

// 关联配置类型
export interface RelationConfig {
  relation_id: string
  relation_family: string
  relation_subfamily: string
  relation_desc?: string
}

// 系统状态类型
export interface SystemStatus {
  app_name: string
  version: string
  database: {
    database_type: string
    total_tables: number
  }
}

// 数据表信息类型
export interface DataTable {
  table_name: string
  comment?: string
  row_count: number
}

// 表格列类型
export interface Column {
  key: string
  title: string
  type?: 'text' | 'number' | 'date' | 'boolean' | 'status'
}