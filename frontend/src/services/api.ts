import { apiClient } from '@/api'

export const queryApi = {
  // 提交异步查询
  async submitQuery(params: {
    query: string
    flow_type?: string
    max_retries?: number
  }) {
    return await apiClient.submitQuery(
      params.query,
      params.max_retries || 2,
      params.flow_type || 'fast'
    )
  },

  // 获取任务结果
  async getTaskResult(taskId: string) {
    return await apiClient.getTaskResult(taskId)
  },

  // 获取所有任务
  async getAllTasks() {
    return await apiClient.getAllTasks()
  }
}