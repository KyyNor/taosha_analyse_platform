/**
 * FraudHunter预警管控模型服务 - API调用封装
 */

import api from '@/lib/api'
import type {
  RiskControlModel,
  RiskControlModelCreate,
  RiskControlModelUpdate,
  RiskControlModelListResponse,
  RiskControlModelPublishRequest
} from '@/types/fraudhunter/risk-control-model'

const BASE_PATH = '/fraudhunter/risk-control-models'

// ==================== 历史回测相关类型 ====================

export interface ModelBacktestRequest {
  start_date: string
  end_date: string
}

export interface ModelBacktestResponse {
  success: boolean
  message: string
  execution_id?: string
}

export interface ModelBatchBacktestRequest extends ModelBacktestRequest {
  model_ids: number[]
}

export interface ModelBatchBacktestResponse {
  success: boolean
  message: string
  execution_id?: string
}

export interface ModelOnlineRequest {
  schedule_cron?: string
  description?: string
}

export interface ModelOnlineResponse {
  success: boolean
  message: string
  workflow_code?: string
}

// ==================== 列表查询参数 ====================

export interface ListRiskControlModelsParams {
  page?: number
  page_size?: number
  status?: string
  model_type?: string
  object_type?: string
  model_code?: string
}

// ==================== 服务方法 ====================

/**
 * 预警管控模型服务
 */
export const riskControlModelService = {
  /**
   * 获取预警管控模型列表
   *
   * @param params 查询参数
   * @returns 模型列表响应
   */
  async list(params?: ListRiskControlModelsParams): Promise<RiskControlModelListResponse> {
    const response = await api.get<RiskControlModelListResponse>(BASE_PATH, { params })
    return response.data
  },

  /**
   * 获取预警管控模型详情
   *
   * @param modelId 模型ID
   * @returns 模型详情
   */
  async get(modelId: number): Promise<RiskControlModel> {
    const response = await api.get<RiskControlModel>(`${BASE_PATH}/${modelId}`)
    return response.data
  },

  /**
   * 创建预警管控模型
   *
   * @param data 创建数据
   * @returns 创建的模型
   */
  async create(data: RiskControlModelCreate): Promise<RiskControlModel> {
    const response = await api.post<RiskControlModel>(BASE_PATH, data)
    return response.data
  },

  /**
   * 更新预警管控模型
   *
   * @param modelId 模型ID
   * @param data 更新数据
   * @returns 更新后的模型
   */
  async update(modelId: number, data: RiskControlModelUpdate): Promise<RiskControlModel> {
    const response = await api.put<RiskControlModel>(`${BASE_PATH}/${modelId}`, data)
    return response.data
  },

  /**
   * 删除预警管控模型
   *
   * @param modelId 模型ID
   */
  async delete(modelId: number): Promise<void> {
    await api.delete(`${BASE_PATH}/${modelId}`)
  },

  /**
   * 发布预警管控模型
   *
   * @param modelId 模型ID
   * @param data 发布数据
   * @returns 发布后的模型
   */
  async publish(modelId: number, data: RiskControlModelPublishRequest): Promise<RiskControlModel> {
    const response = await api.post<RiskControlModel>(`${BASE_PATH}/${modelId}/publish`, data)
    return response.data
  },

  /**
   * 归档预警管控模型
   *
   * @param modelId 模型ID
   * @returns 归档后的模型
   */
  async archive(modelId: number): Promise<RiskControlModel> {
    const response = await api.post<RiskControlModel>(`${BASE_PATH}/${modelId}/archive`)
    return response.data
  },

  /**
   * 提交模型历史回测任务
   *
   * @param modelId 模型ID
   * @param data 回测参数（开始日期、结束日期）
   * @returns 回测任务提交结果
   */
  async backtest(modelId: number, data: ModelBacktestRequest): Promise<ModelBacktestResponse> {
    const response = await api.post<ModelBacktestResponse>(`${BASE_PATH}/${modelId}/backtest`, data)
    return response.data
  },

  /**
   * 提交模型批量历史回测任务
   *
   * @param data 批量回测参数（模型ID列表、开始日期、结束日期）
   * @returns 批量回测任务提交结果
   */
  async batchBacktest(data: ModelBatchBacktestRequest): Promise<ModelBatchBacktestResponse> {
    const response = await api.post<ModelBatchBacktestResponse>(`${BASE_PATH}/batch-backtest`, data)
    return response.data
  }
}

export default riskControlModelService
