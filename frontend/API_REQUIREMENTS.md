# 淘沙分析平台前端 API 需求文档

## 概述

本文档描述了淘沙分析平台前端项目所需的后端 API 接口规范。前端基于 Vue 3 + TypeScript 开发，需要与后端进行数据交互来实现完整的功能。

## 基础规范

### 基础 URL
- 开发环境: `http://localhost:8000/api/v1`
- 生产环境: `https://api.taosha.com/v1`

### 通用响应格式
```typescript
interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}
```

### 认证方式
使用 Bearer Token 认证：
```http
Authorization: Bearer <access_token>
```

## 1. 认证相关 API

### 1.1 用户登录
- **接口**: `POST /auth/login`
- **描述**: 用户登录获取访问令牌
- **请求体**:
```typescript
interface LoginRequest {
  username: string
  password: string
  rememberMe?: boolean
}
```
- **响应**:
```typescript
interface LoginResponse {
  accessToken: string
  user: User
}
```

### 1.2 刷新令牌
- **接口**: `POST /auth/refresh`
- **描述**: 刷新访问令牌
- **响应**:
```typescript
interface RefreshResponse {
  accessToken: string
  user: User
}
```

### 1.3 用户注销
- **接口**: `POST /auth/logout`
- **描述**: 用户注销

### 1.4 验证令牌
- **接口**: `GET /auth/verify`
- **描述**: 验证令牌有效性

## 2. 查询相关 API

### 2.1 提交查询
- **接口**: `POST /query/submit`
- **描述**: 提交自然语言查询请求
- **请求体**:
```typescript
interface QueryRequest {
  query: string
  flowType: 'fast' | 'thorough'
  selectedThemeId?: number
  selectedTableIds?: number[]
}
```
- **响应**:
```typescript
interface QuerySubmitResponse {
  taskId: string
}
```

### 2.2 获取查询进度
- **接口**: `GET /query/progress/{taskId}`
- **描述**: 获取查询执行进度
- **响应**:
```typescript
interface QueryProgress {
  taskId: string
  status: 'running' | 'success' | 'failed' | 'cancelled'
  progress: number
  currentStep: string
  steps: QueryStep[]
  sqlQuery?: string
  result?: QueryResult
  errorMessage?: string
}
```

### 2.3 取消查询
- **接口**: `POST /query/cancel/{taskId}`
- **描述**: 取消正在执行的查询

### 2.4 重新执行查询
- **接口**: `POST /query/rerun/{taskId}`
- **描述**: 重新执行历史查询
- **响应**:
```typescript
interface QuerySubmitResponse {
  taskId: string
}
```

### 2.5 导出查询结果
- **接口**: `GET /query/export/{taskId}?format=csv|xlsx`
- **描述**: 导出查询结果
- **响应**: 文件流

### 2.6 获取查询历史
- **接口**: `GET /query/history?page=1&pageSize=20&status=&startTime=&endTime=`
- **描述**: 获取查询历史记录
- **响应**:
```typescript
interface QueryHistoryResponse {
  items: QueryLog[]
  page: number
  pageSize: number
  total: number
  totalPages: number
}
```

### 2.7 提交反馈
- **接口**: `POST /query/feedback/{taskId}`
- **描述**: 提交查询反馈
- **请求体**:
```typescript
interface FeedbackRequest {
  type: 'positive' | 'negative' | 'neutral'
  content?: string
}
```

## 3. 收藏相关 API

### 3.1 获取收藏列表
- **接口**: `GET /favorites?page=1&pageSize=20`
- **描述**: 获取用户收藏列表
- **响应**:
```typescript
interface FavoritesResponse {
  items: Favorite[]
  page: number
  pageSize: number
  total: number
  totalPages: number
}
```

### 3.2 添加到收藏
- **接口**: `POST /favorites`
- **描述**: 添加查询到收藏
- **请求体**:
```typescript
interface AddFavoriteRequest {
  taskId: string
  title: string
}
```

### 3.3 更新收藏
- **接口**: `PUT /favorites/{favoriteId}`
- **描述**: 更新收藏信息
- **请求体**:
```typescript
interface UpdateFavoriteRequest {
  title: string
}
```

### 3.4 删除收藏
- **接口**: `DELETE /favorites/{favoriteId}`
- **描述**: 删除收藏

### 3.5 执行收藏查询
- **接口**: `POST /favorites/{favoriteId}/execute`
- **描述**: 执行收藏的查询
- **响应**:
```typescript
interface QuerySubmitResponse {
  taskId: string
}
```

## 4. 元数据管理 API

### 4.1 表管理

#### 4.1.1 获取表列表
- **接口**: `GET /metadata/tables?dataSource=&isAvailable=`
- **描述**: 获取表元数据列表
- **响应**: `TableMetadata[]`

#### 4.1.2 获取表详情
- **接口**: `GET /metadata/tables/{tableId}`
- **描述**: 获取表详细信息
- **响应**: `TableMetadata`

#### 4.1.3 创建表
- **接口**: `POST /metadata/tables`
- **描述**: 创建表元数据
- **请求体**:
```typescript
interface CreateTableRequest {
  name: string
  comment: string
  isAvailable: boolean
  dataSource?: string
  updateMethod?: string
}
```

#### 4.1.4 更新表
- **接口**: `PUT /metadata/tables/{tableId}`
- **描述**: 更新表元数据
- **请求体**:
```typescript
interface UpdateTableRequest {
  comment?: string
  isAvailable?: boolean
  dataSource?: string
  updateMethod?: string
}
```

#### 4.1.5 删除表
- **接口**: `DELETE /metadata/tables/{tableId}`
- **描述**: 删除表元数据

#### 4.1.6 获取表结构
- **接口**: `GET /metadata/tables/{tableName}/schema`
- **描述**: 获取表的实际结构信息
- **响应**:
```typescript
interface TableSchema {
  columns: ColumnMetadata[]
  relationships: any[]
  sampleData: any[]
}
```

### 4.2 字段管理

#### 4.2.1 获取字段列表
- **接口**: `GET /metadata/columns?tableId=`
- **描述**: 获取字段元数据列表
- **响应**: `ColumnMetadata[]`

#### 4.2.2 创建字段
- **接口**: `POST /metadata/columns`
- **描述**: 创建字段元数据
- **请求体**:
```typescript
interface CreateColumnRequest {
  tableName: string
  name: string
  type: string
  comment: string
  isAvailable: boolean
  businessType: string
  relationId?: string
  sampleValues?: string[]
}
```

#### 4.2.3 更新字段
- **接口**: `PUT /metadata/columns/{columnId}`
- **描述**: 更新字段元数据

#### 4.2.4 删除字段
- **接口**: `DELETE /metadata/columns/{columnId}`
- **描述**: 删除字段元数据

### 4.3 业务术语管理

#### 4.3.1 获取术语列表
- **接口**: `GET /metadata/glossary/terms?category=`
- **描述**: 获取业务术语列表
- **响应**: `GlossaryTerm[]`

#### 4.3.2 搜索术语
- **接口**: `GET /metadata/glossary/search?q=keyword`
- **描述**: 搜索业务术语
- **响应**: `GlossaryTerm[]`

#### 4.3.3 创建术语
- **接口**: `POST /metadata/glossary/terms`
- **描述**: 创建业务术语
- **请求体**:
```typescript
interface CreateTermRequest {
  term: string
  definition: string
  sqlExpression?: string
  category?: string
  aliases?: string[]
}
```

#### 4.3.4 更新术语
- **接口**: `PUT /metadata/glossary/terms/{termId}`
- **描述**: 更新业务术语

#### 4.3.5 删除术语
- **接口**: `DELETE /metadata/glossary/terms/{termId}`
- **描述**: 删除业务术语

### 4.4 关联配置管理

#### 4.4.1 获取关联配置列表
- **接口**: `GET /metadata/relation-configs`
- **描述**: 获取关联配置列表
- **响应**: `RelationConfig[]`

#### 4.4.2 创建关联配置
- **接口**: `POST /metadata/relation-configs`
- **描述**: 创建关联配置
- **请求体**:
```typescript
interface CreateRelationConfigRequest {
  relationFamily: string
  relationSubfamily: string
  relationDesc: string
}
```

### 4.5 数据主题管理

#### 4.5.1 获取主题列表
- **接口**: `GET /metadata/themes`
- **描述**: 获取数据主题列表
- **响应**: `DataTheme[]`

#### 4.5.2 创建主题
- **接口**: `POST /metadata/themes`
- **描述**: 创建数据主题
- **请求体**:
```typescript
interface CreateThemeRequest {
  themeName: string
  themeDescription: string
  themeType: 'public' | 'normal'
}
```

#### 4.5.3 获取主题下的表
- **接口**: `GET /metadata/themes/{themeId}/tables`
- **描述**: 获取主题下的表列表
- **响应**: `TableMetadata[]`

#### 4.5.4 添加表到主题
- **接口**: `POST /metadata/themes/{themeId}/tables`
- **描述**: 将表添加到主题

### 4.6 数据同步

#### 4.6.1 从数据库同步
- **接口**: `POST /metadata/sync-from-database`
- **描述**: 从实际数据库同步元数据
- **响应**:
```typescript
interface SyncResponse {
  success: boolean
  message: string
  syncedTables: string[]
}
```

#### 4.6.2 获取同步状态
- **接口**: `GET /metadata/sync-status`
- **描述**: 获取同步状态
- **响应**:
```typescript
interface SyncStatus {
  lastSyncTime: string
  pendingSyncCount: number
  syncing: boolean
}
```

### 4.7 导入导出

#### 4.7.1 导出元数据
- **接口**: `GET /metadata/export?format=json|xlsx`
- **描述**: 导出元数据
- **响应**: 文件流

#### 4.7.2 导入元数据
- **接口**: `POST /metadata/import`
- **描述**: 导入元数据
- **请求**: multipart/form-data
- **字段**:
  - `file`: 文件
  - `type`: 类型 (tables|columns|glossary)
- **响应**:
```typescript
interface ImportResponse {
  success: boolean
  message: string
  importedCount: number
  errors: string[]
}
```

#### 4.7.3 获取导入模板
- **接口**: `GET /metadata/import-template/{type}`
- **描述**: 获取导入模板
- **响应**: 文件流

### 4.8 验证和统计

#### 4.8.1 验证配置
- **接口**: `GET /metadata/validate`
- **描述**: 验证元数据配置
- **响应**:
```typescript
interface ValidationResult {
  valid: boolean
  errors: ValidationError[]
  warnings: ValidationWarning[]
}
```

#### 4.8.2 获取统计信息
- **接口**: `GET /metadata/statistics`
- **描述**: 获取元数据统计信息
- **响应**:
```typescript
interface MetadataStatistics {
  totalTables: number
  totalColumns: number
  totalTerms: number
  totalRelations: number
  tablesByDataSource: Array<{ dataSource: string; count: number }>
  termsByCategory: Array<{ category: string; count: number }>
}
```

#### 4.8.3 搜索元数据
- **接口**: `GET /metadata/search?q=keyword&type=table|column|glossary&dataSource=&category=`
- **描述**: 搜索元数据
- **响应**:
```typescript
interface SearchResponse {
  tables: TableMetadata[]
  columns: ColumnMetadata[]
  terms: GlossaryTerm[]
}
```

## 5. WebSocket 连接

### 5.1 查询进度推送
- **连接**: `ws://localhost:8000/ws/query-progress`
- **描述**: 实时推送查询执行进度
- **消息格式**:
```typescript
interface QueryProgressMessage {
  taskId: string
  status: string
  progress: number
  currentStep: string
  data?: any
  sqlQuery?: string
  error?: string
}
```

## 6. 错误码规范

| 错误码 | 描述 | HTTP状态码 |
|--------|------|-----------|
| 10001 | 参数错误 | 400 |
| 10002 | 认证失败 | 401 |
| 10003 | 权限不足 | 403 |
| 10004 | 资源不存在 | 404 |
| 10005 | 服务器内部错误 | 500 |
| 20001 | 查询执行失败 | 400 |
| 20002 | 查询超时 | 408 |
| 20003 | SQL 语法错误 | 400 |
| 30001 | 元数据已存在 | 409 |
| 30002 | 元数据不存在 | 404 |
| 30003 | 同步失败 | 500 |

## 7. 数据类型定义

### User
```typescript
interface User {
  id: number
  username: string
  realName: string
  email?: string
  avatar?: string
  roles: string[]
  createdAt: string
  updatedAt: string
}
```

### QueryTask
```typescript
interface QueryTask {
  taskId: string
  userInput: string
  workflowType: number
  selectedThemeId?: number
  selectedTableIds?: number[]
  taskStatus: 'running' | 'success' | 'failed' | 'cancelled'
  startTime: string
  endTime?: string
  progress?: number
  generatedSql?: string
  errorMessage?: string
}
```

### QueryResult
```typescript
interface QueryResult {
  taskId: string
  status: string
  generatedSql: string
  result: {
    columns: Array<{
      name: string
      type: string
    }>
    rows: any[]
    rowCount: number
  }
}
```

### QueryLog
```typescript
interface QueryLog {
  id: string
  query: string
  generatedSql?: string
  status: 'success' | 'failed' | 'running' | 'cancelled'
  duration?: number
  createdAt: string
  updatedAt: string
  errorMessage?: string
  userId?: number
}
```

### Favorite
```typescript
interface Favorite {
  id: number
  userId: number
  taskId: string
  userQuestion: string
  favoriteTitle: string
  selectedThemeId?: number
  selectedTableIds?: string
  tags?: string
  createdAt: string
  updatedAt: string
  lastExecutedAt?: string
  executionCount: number
}
```

### TableMetadata
```typescript
interface TableMetadata {
  id: number
  name: string
  comment?: string
  isAvailable: boolean
  dataSource?: string
  updateMethod?: string
  createdAt: string
  updatedAt: string
}
```

### ColumnMetadata
```typescript
interface ColumnMetadata {
  id: number
  tableId: number
  tableName: string
  name: string
  type: string
  comment?: string
  isAvailable: boolean
  businessType: string
  relationId?: string
  sampleValues?: string[]
  createdAt: string
  updatedAt: string
}
```

### GlossaryTerm
```typescript
interface GlossaryTerm {
  id: number
  term: string
  definition: string
  sqlExpression?: string
  category?: string
  aliases?: string[]
  createdAt: string
  updatedAt: string
}
```

### RelationConfig
```typescript
interface RelationConfig {
  id: string
  relationFamily: string
  relationSubfamily: string
  relationDesc: string
  createdAt: string
  updatedAt: string
}
```

### DataTheme
```typescript
interface DataTheme {
  id: number
  themeName: string
  themeDescription: string
  themeType: 'public' | 'normal'
  createdAt: string
  updatedAt: string
}
```

## 8. 注意事项

1. **认证**: 所有需要认证的接口都需要在请求头中包含有效的访问令牌
2. **分页**: 列表接口支持分页，默认每页20条记录
3. **错误处理**: 前端需要根据错误码进行相应的错误处理和用户提示
4. **超时设置**: 查询接口建议设置较长的超时时间，因为AI生成SQL可能需要较长时间
5. **WebSocket**: 查询进度通过WebSocket实时推送，前端需要维护连接状态
6. **文件上传**: 导入功能使用multipart/form-data格式
7. **文件下载**: 导出功能返回文件流，前端需要处理文件下载

## 9. 开发优先级

### 高优先级 (核心功能)
1. 认证相关 API (1.x)
2. 查询提交和进度 API (2.1-2.3)
3. WebSocket 查询进度推送 (5.1)
4. 查询历史 API (2.6)

### 中优先级 (重要功能)
1. 收藏相关 API (3.x)
2. 表管理 API (4.1)
3. 数据同步 API (4.6)

### 低优先级 (辅助功能)
1. 字段管理 API (4.2)
2. 业务术语管理 API (4.3)
3. 关联配置 API (4.4)
4. 数据主题管理 API (4.5)
5. 导入导出 API (4.7)
6. 统计验证 API (4.8)

---

本文档将随着项目开发的进展持续更新和完善。