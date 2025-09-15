import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 240000,
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// API 接口定义
export const apiClient = {
  // 健康检查
  healthCheck: () => api.get('/health'),
  
  // 系统状态
  getSystemStatus: () => api.get('/status'),
  
  // 数据表
  getTables: () => api.get('/tables'),
  
  // 查询
  query: (data: { query: string; max_retries: number }) => 
    api.post('/query', data),
  
  // 元数据管理
  metadata: {
    getTables: () => api.get('/dev/metadata/tables'),
    addTable: (data: { name: string; comment: string; is_available: number }) =>
      api.post('/dev/metadata/tables', data),
    updateTable: (tableName: string, data: any) =>
      api.put(`/dev/metadata/tables/${tableName}`, data),
    deleteTable: (tableName: string) =>
      api.delete(`/dev/metadata/tables/${tableName}`),
    
    addColumn: (data: {
      table_name: string;
      name: string;
      type: string;
      comment: string;
      is_available: number;
      business_type: string;
      relation_id: string;
    }) => api.post('/dev/metadata/columns', data),
    updateColumn: (tableName: string, columnName: string, data: any) =>
      api.put(`/dev/metadata/columns/${tableName}/${columnName}`, data),
    deleteColumn: (tableName: string, columnName: string) =>
      api.delete(`/dev/metadata/columns/${tableName}/${columnName}`),
    
    syncFromDatabase: () => api.post('/dev/metadata/sync-from-database'),
  },
  
  // 术语管理
  glossary: {
    getTerms: () => api.get('/dev/glossary/terms'),
    addTerm: (data: {
      term: string;
      definition: string;
      sql_expression: string;
      category: string;
      aliases: string[];
    }) => api.post('/dev/glossary/terms', data),
    updateTerm: (termId: number, data: any) =>
      api.put(`/dev/glossary/terms/${termId}`, data),
    deleteTerm: (termId: number) =>
      api.delete(`/dev/glossary/terms/${termId}`),
  },
  
  // 关联配置
  relationConfig: {
    getAll: () => api.get('/dev/relation-configs'),
    add: (data: {
      relation_family: string;
      relation_subfamily: string;
      relation_desc: string;
    }) => api.post('/dev/relation-configs', data),
    update: (relationId: string, data: any) =>
      api.put(`/dev/relation-configs/${relationId}`, data),
    delete: (relationId: string) =>
      api.delete(`/dev/relation-configs/${relationId}`),
    getIds: () => api.get('/dev/relation-configs/ids'),
  },
}

export default api