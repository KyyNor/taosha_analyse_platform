// API Response types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
  code?: number
}

// User types
export interface User {
  id: number
  username: string
  realName?: string
  roles: string[]
  department?: string
  departmentId?: string
  avatar?: string
  email?: string
  createdAt: string
  updatedAt: string
}

// Auth types
export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  success: boolean
  data?: {
    accessToken: string
    user: User
  }
  error?: string
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

export interface QueryTask {
  taskId: string
  userId?: number
  userInput: string
  workflowType: number
  selectedThemeId?: number
  selectedTableIds?: number[]
  taskStatus: 'running' | 'success' | 'failed' | 'cancelled'
  progress?: TaskProgress
  generatedSql?: string
  sqlExecutionResult?: any
  resultRowCount?: number
  errorMessage?: string
  startTime: string
  endTime?: string
  durationMs?: number
  createdAt: string
  updatedAt: string
  current_step?: string
  logs?: QueryLogEntry[]
  error?: string
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

export interface BreadcrumbItem {
  label: string
  path?: string
  active?: boolean
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
