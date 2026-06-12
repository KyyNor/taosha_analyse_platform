/**
 * FraudHunter 预警管控模型类型定义
 */

import { RuleConfig } from './rule'

/**
 * 模型状态
 */
export type ModelStatus = 'draft' | 'testing' | 'online' | 'offline' | 'archived'
export type ModelType = 'normal' | 'prefix'

/**
 * 预警管控模型基础信息
 */
export interface RiskControlModel {
  id: number
  model_code: string
  model_name: string
  model_type: ModelType
  description?: string

  // 规则配置
  rule_config: RuleConfig

  // 生成的SQL
  offline_model_sql?: string
  realtime_model_sql?: string

  // 告警配置
  is_send_alert_message: boolean
  alert_message_target?: string
  is_acct_control: boolean
  is_send_financial_manager_alert?: boolean

  // 关联指标
  indicator_codes?: string

  // 版本管理
  current_version: number
  latest_version: number

  // 状态
  status: ModelStatus
  online_at?: string
  online_by?: string

  // 审计字段
  created_by?: string
  created_at: string
  updated_by?: string
  updated_at: string
}

/**
 * 创建预警管控模型请求
 */
export interface RiskControlModelCreate {
  model_code?: string  // 可选，后端会自动生成
  model_name: string
  model_type?: ModelType
  description?: string
  rule_config: RuleConfig
  is_send_alert_message?: boolean
  alert_message_target?: string
  is_acct_control?: boolean
  is_send_financial_manager_alert?: boolean
}

/**
 * 更新预警管控模型请求
 */
export interface RiskControlModelUpdate {
  model_name?: string
  model_type?: ModelType
  description?: string
  rule_config?: RuleConfig
  is_send_alert_message?: boolean
  alert_message_target?: string
  is_acct_control?: boolean
  is_send_financial_manager_alert?: boolean
}

/**
 * 预警管控模型列表响应
 */
export interface RiskControlModelListResponse {
  total: number
  page: number
  page_size: number
  items: RiskControlModel[]
}

/**
 * 预警管控模型发布请求
 */
export interface RiskControlModelPublishRequest {
  version: number
  change_description?: string
}

// ==================== 辅助类型和常量 ====================

/**
 * 模型状态标签映射
 */
export const MODEL_STATUS_LABELS: Record<ModelStatus, string> = {
  'draft': '草稿',
  'testing': '测试中',
  'online': '已上线',
  'offline': '已下线',
  'archived': '已归档'
}

/**
 * 模型状态颜色变体
 */
export const MODEL_STATUS_VARIANTS: Record<ModelStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  'draft': 'outline',
  'testing': 'secondary',
  'online': 'default',
  'offline': 'destructive',
  'archived': 'outline'
}


/**
 * 获取模型状态标签
 */
export function getModelStatusLabel(status: ModelStatus): string {
  return MODEL_STATUS_LABELS[status] || status
}

/**
 * 获取模型状态颜色变体
 */
export function getModelStatusVariant(status: ModelStatus): 'default' | 'secondary' | 'destructive' | 'outline' {
  return MODEL_STATUS_VARIANTS[status] || 'default'
}
