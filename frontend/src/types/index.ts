// 主题相关类型
export interface Theme {
  id: number
  theme_name: string
  theme_description?: string
  is_public: boolean
  created_by?: number
  created_at?: string
  updated_at?: string
}

// 表相关类型
export interface Table {
  id: number
  table_name_en: string
  table_name_cn: string
  table_description?: string
  theme_id: number
  is_active: boolean
  created_at?: string
  updated_at?: string
}

// 字段相关类型
export interface Field {
  id: number
  table_id: number
  field_name_en: string
  field_name_cn: string
  field_type: string
  field_description?: string
  is_primary_key: boolean
  is_nullable: boolean
  default_value?: string
  created_at?: string
  updated_at?: string
}

// 查询历史类型
export interface QueryHistory {
  id: number
  user_question: string
  generated_sql?: string
  theme_id?: number
  table_ids?: number[]
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
  result_count?: number
  execution_time_ms?: number
  error_message?: string
  created_at: string
  updated_at?: string
}

// 查询任务类型
export interface QueryTask {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
  current_step: string
  progress_percentage: number
  generated_sql?: string
  sql_confidence?: number
  result?: QueryResult
  error_message?: string
  error_details?: string
  logs?: LogEntry[]
  created_at: string
  updated_at?: string
}

// 查询结果类型
export interface QueryResult {
  columns: string[]
  rows: any[][]
  total_count?: number
  execution_time_ms?: number
  metadata?: Record<string, any>
}

// 日志条目类型
export interface LogEntry {
  timestamp: string | number
  level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG'
  message: string
  details?: any
}

// 查询请求类型
export interface QueryRequest {
  user_question: string
  theme_id?: number
  table_ids?: number[]
  context?: Record<string, any>
  options?: QueryOptions
}

// 查询选项类型
export interface QueryOptions {
  max_rows?: number
  timeout_seconds?: number
  explain_sql?: boolean
  use_cache?: boolean
}

// 用户相关类型
export interface User {
  id: number
  username: string
  email: string
  full_name?: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at?: string
}

// 角色相关类型
export interface Role {
  id: number
  role_name: string
  description?: string
  permissions: string[]
  created_at: string
  updated_at?: string
}

// API响应类型
export interface ApiResponse<T = any> {
  success: boolean
  data: T
  message?: string
  code?: number
}

// 分页响应类型
export interface PaginatedResponse<T = any> {
  success: boolean
  data: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// 错误响应类型
export interface ErrorResponse {
  success: false
  message: string
  code?: number
  details?: any
}

// 表单验证规则类型
export interface ValidationRule {
  required?: boolean
  min?: number
  max?: number
  pattern?: RegExp
  validator?: (value: any) => boolean | string
}

// 表单字段类型
export interface FormField {
  key: string
  label: string
  type: 'text' | 'textarea' | 'select' | 'checkbox' | 'number' | 'email' | 'password'
  placeholder?: string
  options?: Array<{ label: string; value: any }>
  rules?: ValidationRule[]
  disabled?: boolean
  readonly?: boolean
}

// 导出相关类型
export interface ExportOptions {
  format: 'csv' | 'excel' | 'json'
  filename?: string
  includeHeaders?: boolean
  encoding?: string
}

// WebSocket消息类型
export interface WebSocketMessage {
  type: 'query_progress' | 'query_completed' | 'query_error' | 'system_message'
  task_id?: string
  data: any
  timestamp: string
}