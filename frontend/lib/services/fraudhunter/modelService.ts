/**
 * FraudHunter模型服务 - 规则引擎API调用封装
 *
 * 版本: v2.0.0 (支持高级操作符)
 */

import api from '@/lib/api'
import type {
  RuleConfig,
  RuleValidationResult
} from '@/types/fraudhunter/rule'

const BASE_PATH = '/fraudhunter/models'

// ==================== 响应类型定义 ====================

/**
 * SQL预览结果
 */
export interface SQLPreviewResult {
  sql_expression: string
  extracted_indicators: string[]
  rule_summary: {
    total_rules: number
    max_depth: number
    indicator_count: number
    indicators: string[]
    root_logic: string
    output: {
      risk_level: string
      risk_score: number
      action?: string
    }
  }
  warnings: string[]
}

/**
 * 规则评估结果
 */
export interface RuleEvaluationResult {
  is_hit: boolean
  indicator_values: Record<string, any>
  output?: {
    risk_level: string
    risk_score: number
    action?: string
    description?: string
  }
}

/**
 * 健康检查结果
 */
export interface HealthCheckResult {
  status: string
  version: string
  supported_operators: {
    comparison: string[]
    set: string[]
    pattern: string[]
  }
}

// ==================== 服务方法 ====================

/**
 * 模型服务
 */
export const modelService = {
  /**
   * 验证规则配置
   *
   * @param ruleConfig 规则配置
   * @returns 验证结果
   */
  async validateRule(ruleConfig: RuleConfig): Promise<RuleValidationResult> {
    const response = await api.post<RuleValidationResult>(
      `${BASE_PATH}/validate-rule`,
      ruleConfig
    )
    return response.data
  },

  /**
   * 预览规则SQL表达式
   *
   * @param ruleConfig 规则配置
   * @returns SQL预览结果
   */
  async previewSQL(ruleConfig: RuleConfig): Promise<SQLPreviewResult> {
    const response = await api.post<SQLPreviewResult>(
      `${BASE_PATH}/preview-sql`,
      ruleConfig
    )
    return response.data
  },

  /**
   * 运行时评估规则
   *
   * @param ruleConfig 规则配置
   * @param indicatorValues 指标值字典
   * @returns 评估结果
   */
  async evaluateRule(
    ruleConfig: RuleConfig,
    indicatorValues: Record<string, any>
  ): Promise<RuleEvaluationResult> {
    const response = await api.post<RuleEvaluationResult>(
      `${BASE_PATH}/evaluate-rule`,
      {
        rule_config: ruleConfig,
        indicator_values: indicatorValues
      }
    )
    return response.data
  },

  /**
   * 健康检查
   *
   * @returns 健康状态
   */
  async healthCheck(): Promise<HealthCheckResult> {
    const response = await api.get<HealthCheckResult>(`${BASE_PATH}/health`)
    return response.data
  },
}

export default modelService
