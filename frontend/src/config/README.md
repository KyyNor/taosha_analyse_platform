# API配置说明

## 概述

本项目采用统一的API配置管理，所有API端点都集中在 `src/config/api.ts` 文件中配置。

## 配置结构

### 基础配置 (`API_CONFIG`)

```typescript
export const API_CONFIG = {
  BASE_URL: 'http://localhost:8000',           // API基础URL
  WS_BASE_URL: 'ws://localhost:8000',           // WebSocket基础URL
  API_PREFIX: '/api/taosha/v1',                 // API版本前缀
  TIMEOUT: 30000,                               // 请求超时时间
  RETRY: {                                      // 重试配置
    MAX_ATTEMPTS: 3,
    DELAY: 1000,
  }
}
```

### API端点配置 (`API_ENDPOINTS`)

所有API端点按功能模块分类：

```typescript
export const API_ENDPOINTS = {
  // 自然语言查询
  NL_QUERY: {
    SUBMIT: '/nl/submit',
    CANCEL: '/nl/cancel/:taskId',
    // ...
  },

  // 元数据管理
  METADATA: {
    TABLES: {
      LIST: '/metadata/tables',
      DETAIL: '/metadata/tables/:id',
      // ...
    },
    // ...
  },

  // 收藏管理
  FAVORITES: {
    LIST: '/favorites',
    CREATE: '/favorites',
    // ...
  }
}
```

### WebSocket端点配置 (`WS_ENDPOINTS`)

```typescript
export const WS_ENDPOINTS = {
  TASK_PROGRESS: '/nlquery/ws/task_process',
  NOTIFICATIONS: '/ws/notifications',
  LOGS: '/ws/logs',
}
```

## 使用方法

### 1. 在Service中使用

```typescript
import { API_ENDPOINTS, buildApiUrl, replaceUrlParams } from '@/config/api'
import { api } from './client'

class MyService {
  // 获取列表数据
  async getList(params: any) {
    return await api.get(buildApiUrl(API_ENDPOINTS.METADATA.TABLES.LIST, params))
  }

  // 获取详情数据（带路径参数）
  async getDetail(id: number) {
    const url = replaceUrlParams(API_ENDPOINTS.METADATA.TABLES.DETAIL, { id })
    return await api.get(buildApiUrl(url))
  }

  // 创建数据
  async create(data: any) {
    return await api.post(buildApiUrl(API_ENDPOINTS.METADATA.TABLES.CREATE), data)
  }
}
```

### 2. 环境变量配置

创建 `.env.local` 文件来配置环境变量：

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

### 3. 辅助函数

#### `buildApiUrl(endpoint: string, params?: Record<string, any>)`

构建完整的API URL，自动添加API前缀和查询参数：

```typescript
buildApiUrl('/nl/submit')                    // -> '/api/taosha/v1/nl/submit'
buildApiUrl('/nl/history', { page: 1, pageSize: 20 })  // -> '/api/taosha/v1/nl/history?page=1&pageSize=20'
```

#### `replaceUrlParams(url: string, params: Record<string, any>)`

替换URL中的路径参数：

```typescript
replaceUrlParams('/nl/cancel/:taskId', { taskId: '123' })  // -> '/nl/cancel/123'
```

#### `buildWsUrl(endpoint: string)`

构建WebSocket URL：

```typescript
buildWsUrl('/nlquery/ws/task_process')  // -> 'ws://localhost:8000/nlquery/ws/task_process'
```

## 修改API端点

当需要修改API端点时，只需在 `src/config/api.ts` 文件中修改对应的配置：

```typescript
// 修改前
SUBMIT: '/nl/submit',

// 修改后
SUBMIT: '/api/nl/submit/v2',
```

所有使用该端点的代码都会自动使用新的URL。

## 添加新的API端点

1. 在 `API_ENDPOINTS` 中添加新的端点配置
2. 在相应的Service中使用新的端点

```typescript
// 1. 添加配置
export const API_ENDPOINTS = {
  MY_MODULE: {
    LIST: '/my-module/list',
    DETAIL: '/my-module/:id',
  }
}

// 2. 在Service中使用
class MyService {
  async getList() {
    return await api.get(buildApiUrl(API_ENDPOINTS.MY_MODULE.LIST))
  }
}
```

## 最佳实践

1. **统一使用配置文件**：不要在代码中硬编码API路径
2. **使用辅助函数**：始终使用 `buildApiUrl` 和 `replaceUrlParams` 函数
3. **环境变量**：使用环境变量来配置不同环境的API地址
4. **类型安全**：利用TypeScript类型检查确保参数正确
5. **文档同步**：修改API配置时，及时更新相关文档

## 优势

- **统一管理**：所有API端点集中配置，便于维护
- **易于修改**：修改API地址只需改配置文件
- **类型安全**：TypeScript提供完整的类型检查
- **环境隔离**：通过环境变量支持不同环境配置
- **减少错误**：统一的URL构建函数减少拼写错误