// API Response types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
  code?: number
}


// Query types
export interface QueryRequest {
  query: string
  flow_type: 'fast' | 'thorough'
  maxRetries?: number
  selectedThemeId?: number
  selectedTableIds?: number[]
}

export interface QueryLogEntry {
  step: string
  input_data: string
  prompt: string
  model_output: string
  start_time: string
  end_time: string
  error: any
  success: boolean
}

export interface BaseNodeLog {
  step: string
  input_data: string
  prompt: string
  model_output: string
  success: boolean
  error?: string
  start_time: string
  end_time: string
}

export interface QueryTask {
  task_id: string
  user_input: string
  operator?: string
  flow_type: string

  // 进度信息
  status: 'running' | 'success' | 'failed' | 'completed'
  current_step: string
  progress: number
  created_at?: string
  completed_at?: string

  // 业务数据
  sql_query: string
  execution_result?: any[]
  clear_check_details?: Record<string, any>
  is_clear: boolean

  // 错误和重试
  error_message?: string
  retry_count: number
  max_retries: number

  // 日志
  logs?: BaseNodeLog[]
  current_step_log?: BaseNodeLog
  current_step_name: string
}

export interface TaskProgress {
  currentStep: string
  completedNodes: TaskNode[]
  progress: number
}

export interface TaskNode {
  nodeName: string
  startTime?: string
  endTime?: string
  durationMs?: number
  status: 'success' | 'failed' | 'running'
  errorMessage?: string
  input?: any
  output?: any
}

export interface ColumnInfo {
  name: string
  type: string
}

export interface QueryResult {
  taskId: string
  status: string
  generatedSql: string
  result: {
    columns: ColumnInfo[]
    rows: any[][]
    rowCount: number
  }
  chartConfig?: ChartConfig
}

export interface ChartConfig {
  type: 'line' | 'bar' | 'pie' | 'scatter'
  xAxis?: string
  yAxis?: string | string[]
  title?: string
}

// Metadata types
export interface TableMetadata {
  id: number
  name: string
  comment: string
  isAvailable: boolean
  dataSource?: string
  updateMethod?: string
  createdAt: string
  updatedAt: string
}

export interface ColumnMetadata {
  id: number
  tableName: string
  name: string
  type: string
  comment: string
  isAvailable: boolean
  businessType: string
  relationId?: string
  sampleValues?: string[]
  createdAt: string
  updatedAt: string
}

export interface GlossaryTerm {
  id: number
  term: string
  definition: string
  sqlExpression?: string
  category: string
  aliases: string[]
  userId?: number
  createdAt: string
  updatedAt: string
}

export interface RelationConfig {
  id: string
  relationFamily: string
  relationSubfamily: string
  relationDesc: string
  createdAt: string
  updatedAt: string
}

export interface DataTheme {
  id: number
  themeName: string
  themeDescription: string
  themeType: 'public' | 'normal'
  createdAt: string
  updatedAt: string
}

// Favorites types
export interface Favorite {
  id: number
  userId: number
  favoriteTitle: string
  userQuestion: string
  generatedSql: string
  selectedThemeId?: number
  selectedTableIds?: number[]
  createdAt: string
  updatedAt: string
}

// Feedback types
export interface Feedback {
  id: number
  taskId: string
  userId: number
  feedbackType: 'positive' | 'negative' | 'neutral'
  feedbackContent: string
  createdAt: string
}

// Log types
export interface QueryLog {
  id: number
  taskId: string
  userId: number
  userQuestion: string
  generatedSql: string
  status: string
  startTime: string
  endTime?: string
  durationMs?: number
  errorMessage?: string
  nodes: TaskNode[]
  createdAt: string
}

export interface LogFilter {
  userId?: number
  status?: string
  startTime?: string
  endTime?: string
  page?: number
  pageSize?: number
}

// Pagination types
export interface PaginationParams {
  page: number
  pageSize: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

// UI State types
export interface LoadingState {
  [key: string]: boolean
}

export interface ErrorState {
  [key: string]: string | null
}

// WebSocket types
export interface WebSocketMessage {
  type: 'progress' | 'result' | 'error'
  data: any
  timestamp: string
}

// Chart data types
export interface ChartData {
  labels: string[]
  datasets: ChartDataset[]
}

export interface ChartDataset {
  label: string
  data: number[]
  backgroundColor?: string | string[]
  borderColor?: string | string[]
  borderWidth?: number
}

// Export types
export type ExportFormat = 'xlsx' | 'csv' | 'json'

// Component props types
export interface ComponentSize {
  width: number
  height: number
}

// Form validation types
export interface ValidationRule {
  required?: boolean
  minLength?: number
  maxLength?: number
  pattern?: RegExp
  validator?: (value: any) => boolean | string
}

export interface FormField {
  name: string
  label: string
  type: 'text' | 'number' | 'select' | 'textarea' | 'date'
  value: any
  rules?: ValidationRule[]
  placeholder?: string
  disabled?: boolean
  options?: { label: string; value: any }[]
}

// Menu and navigation types
export interface MenuItem {
  id: string
  label: string
  icon?: string
  path?: string
  children?: MenuItem[]
  badge?: string | number
  disabled?: boolean
}

// Statistics types
export interface DashboardStats {
  totalUsers: number
  totalQueriesToday: number
  successRate: number
  avgResponseTime: number
  totalQueries: number
  activeUsers: number
  errorRate: number
  popularQueries: Array<{
    query: string
    count: number
  }>
}

// Search and filter types
export interface SearchParams {
  keyword: string
  filters?: Record<string, any>
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

export interface TableColumn {
  key: string
  label: string
  sortable?: boolean
  width?: string
  align?: 'left' | 'center' | 'right'
  render?: (value: any, record: any) => string
}

// Notification types
export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  duration?: number
  closable?: boolean
  timestamp: string
}
