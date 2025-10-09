/**
 * API配置文件
 * 统一管理所有API端点和配置
 */

// API基础配置
export const API_CONFIG = {
  // 基础URL配置
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  WS_BASE_URL: import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000',

  // API版本前缀
  API_PREFIX: '/api/taosha/v1',

  // 请求超时时间（毫秒）
  TIMEOUT: 30000,

  // 重试配置
  RETRY: {
    MAX_ATTEMPTS: 3,
    DELAY: 1000
  }
}

// API端点配置
export const API_ENDPOINTS = {
  // === 自然语言查询相关 ===
  NL_QUERY: {
    SUBMIT: '/nlquery/submit',                    // 提交自然语言查询
    CANCEL: '/nlquery/cancel/:taskId',            // 取消查询任务
    RERUN: '/nlquery/rerun/:taskId',              // 重新运行查询
    PROGRESS: '/nlquery/progress/:taskId',        // 获取查询进度
    HISTORY: '/nlquery/history',                  // 查询历史
    EXPORT: '/nlquery/export/:taskId',            // 导出查询结果
    FEEDBACK: '/nlquery/feedback/:taskId'        // 提交反馈
  },

  // === 元数据管理相关 ===
  METADATA: {
    // 表管理
    TABLES: {
      LIST: '/metadata/tables',              // 获取表列表
      DETAIL: '/metadata/tables/:id',        // 获取表详情
      CREATE: '/metadata/tables',            // 创建表
      UPDATE: '/metadata/tables/:id',        // 更新表
      DELETE: '/metadata/tables/:id',        // 删除表
      SCHEMA: '/metadata/tables/:tableName/schema'  // 获取表结构
    },

    // 字段管理
    COLUMNS: {
      LIST: '/metadata/columns',             // 获取字段列表
      DETAIL: '/metadata/columns/:id',       // 获取字段详情
      CREATE: '/metadata/columns',           // 创建字段
      UPDATE: '/metadata/columns/:id',       // 更新字段
      DELETE: '/metadata/columns/:id'       // 删除字段
    },

    // 术语管理
    GLOSSARY: {
      TERMS: {
        LIST: '/metadata/glossary/terms',    // 获取术语列表
        DETAIL: '/metadata/glossary/terms/:id',  // 获取术语详情
        CREATE: '/metadata/glossary/terms',  // 创建术语
        UPDATE: '/metadata/glossary/terms/:id',  // 更新术语
        DELETE: '/metadata/glossary/terms/:id',  // 删除术语
        SEARCH: '/metadata/glossary/search' // 搜索术语
      }
    },

    // 关联配置
    RELATIONS: {
      LIST: '/metadata/relation-configs',    // 获取关联配置列表
      DETAIL: '/metadata/relation-configs/:id',  // 获取关联配置详情
      CREATE: '/metadata/relation-configs',  // 创建关联配置
      UPDATE: '/metadata/relation-configs/:id',  // 更新关联配置
      DELETE: '/metadata/relation-configs/:id'  // 删除关联配置
    },

    // 数据主题
    THEMES: {
      LIST: '/metadata/themes',              // 获取主题列表
      DETAIL: '/metadata/themes/:id',        // 获取主题详情
      CREATE: '/metadata/themes',            // 创建主题
      UPDATE: '/metadata/themes/:id',        // 更新主题
      DELETE: '/metadata/themes/:id',        // 删除主题
      TABLES: '/metadata/themes/:themeId/tables'  // 主题下的表
    },

    // 数据库同步
    SYNC: {
      FROM_DB: '/metadata/sync-from-database',  // 从数据库同步
      STATUS: '/metadata/sync-status'          // 同步状态
    },

    // 导入导出
    IMPORT_EXPORT: {
      EXPORT: '/metadata/export',           // 导出元数据
      IMPORT: '/metadata/import',           // 导入元数据
      TEMPLATE: '/metadata/import-template/:type'  // 导入模板
    },

    // 验证和统计
    VALIDATE: '/metadata/validate',         // 验证配置
    STATISTICS: '/metadata/statistics',     // 获取统计信息
    SEARCH: '/metadata/search'             // 搜索元数据
  },

  // === 收藏管理相关 ===
  FAVORITES: {
    LIST: '/favorites',                     // 获取收藏列表
    CREATE: '/favorites',                   // 添加收藏
    UPDATE: '/favorites/:id',               // 更新收藏
    DELETE: '/favorites/:id',               // 删除收藏
    EXECUTE: '/favorites/:id/execute'      // 执行收藏的查询
  },

  // === 操作日志相关 ===
  LOGS: {
    LIST: '/logs',                          // 获取日志列表
    DETAIL: '/logs/:id',                    // 获取日志详情
    EXPORT: '/logs/export',                 // 导出日志
    CLEAR: '/logs/clear'                   // 清理日志
  },

  // === 系统管理相关 ===
  SYSTEM: {
    HEALTH: '/system/health',               // 健康检查
    INFO: '/system/info',                   // 系统信息
    CONFIG: '/system/config'               // 系统配置
  }
}

// WebSocket端点配置
export const WS_ENDPOINTS = {
  // 任务进度更新
  TASK_PROGRESS: '/nlquery/ws/task_process'
}

// 辅助函数：构建完整的API URL
export const buildApiUrl = (endpoint: string, params?: Record<string, any>): string => {
  let url = `${API_CONFIG.API_PREFIX}${endpoint}`

  if (params) {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value))
      }
    })
    const queryString = searchParams.toString()
    if (queryString) {
      url += `?${queryString}`
    }
  }

  return url
}

// 辅助函数：替换URL中的路径参数
export const replaceUrlParams = (url: string, params: Record<string, any>): string => {
  let result = url
  Object.entries(params).forEach(([key, value]) => {
    result = result.replace(`:${key}`, String(value))
  })
  return result
}

// 辅助函数：构建WebSocket URL
export const buildWsUrl = (endpoint: string): string => {
  const wsBaseUrl = API_CONFIG.WS_BASE_URL.replace('http', 'ws')
  return `${wsBaseUrl}${API_CONFIG.API_PREFIX}${endpoint}`
}

// 环境类型
export type Environment = 'development' | 'production' | 'test'

// 获取当前环境
export const getCurrentEnvironment = (): Environment => {
  const env = import.meta.env.MODE
  switch (env) {
    case 'production':
      return 'production'
    case 'test':
      return 'test'
    default:
      return 'development'
  }
}

// 是否为开发环境
export const isDevelopment = (): boolean => getCurrentEnvironment() === 'development'

// 是否为生产环境
export const isProduction = (): boolean => getCurrentEnvironment() === 'production'

// 导出配置对象
export default {
  API_CONFIG,
  API_ENDPOINTS,
  WS_ENDPOINTS,
  buildApiUrl,
  replaceUrlParams,
  buildWsUrl,
  getCurrentEnvironment,
  isDevelopment,
  isProduction
}
