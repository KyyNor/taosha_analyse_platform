/**
 * FraudHunter 规则引擎类型定义
 *
 * 版本: v2.0.0 (支持高级操作符)
 * 支持操作符: 基础比较、集合操作(in/not in)、正则匹配(regexp/not regexp)
 */

// ==================== 基础类型定义 ====================

/**
 * 完整操作符类型（包含高级操作符）
 */
export type ComparisonOperator =
  | '>' | '>=' | '<' | '<=' | '=' | '!='      // 基础比较
  | 'in' | 'not in'                            // 集合操作
  | 'regexp' | 'not regexp'                    // 正则匹配

/**
 * 逻辑操作符
 */
export type LogicOperator = 'AND' | 'OR'

/**
 * 规则类型
 */
export type RuleType = 'condition' | 'group'

/**
 * 指标数据类型
 */
export type IndicatorDataType = 'numeric' | 'enum' | 'boolean' | 'text'

// ==================== 规则结构定义 ====================

/**
 * 条件规则（支持多值）
 */
export interface ConditionRule {
  type: 'condition'
  indicator: string           // 指标编码，如 'i_login_cnt_7d'
  operator: ComparisonOperator
  value: string | number | boolean | string[] | number[]  // 关键：支持数组
}

/**
 * 规则组（支持嵌套）
 */
export interface GroupRule {
  type: 'group'
  logic: LogicOperator
  rules: Rule[]
}

/**
 * 联合类型
 */
export type Rule = ConditionRule | GroupRule

// ==================== 输出配置 ====================

/**
 * 规则命中后的输出配置
 */
export interface RuleOutput {
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  risk_score: number          // 0-100
  action?: 'block' | 'review' | 'alert' | 'pass'
  description?: string
}

// ==================== 完整规则配置 ====================

/**
 * 完整的规则配置
 */
export interface RuleConfig {
  logic: LogicOperator
  rules: Rule[]
  output: RuleOutput
}

// ==================== 辅助类型 ====================

/**
 * 指标信息（用于下拉选择）
 */
export interface Indicator {
  indicator_code: string
  indicator_name: string
  data_type: IndicatorDataType
  enum_values?: string[]      // 枚举类型的可选值
  description?: string
}

/**
 * 规则验证结果
 */
export interface RuleValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
  extracted_indicators: string[]
}

// ==================== 操作符配置 ====================

/**
 * 操作符选项
 */
export interface OperatorOption {
  value: ComparisonOperator
  label: string
  requiresMultiValue: boolean   // 是否需要多值输入（in/not in）
  requiresRegexp: boolean        // 是否需要正则输入（regexp/not regexp）
}

/**
 * 操作符分组配置（用于UI分组显示）
 */
export const OPERATOR_GROUPS: Record<string, OperatorOption[]> = {
  comparison: [
    { value: '>', label: '大于 (>)', requiresMultiValue: false, requiresRegexp: false },
    { value: '>=', label: '大于等于 (≥)', requiresMultiValue: false, requiresRegexp: false },
    { value: '<', label: '小于 (<)', requiresMultiValue: false, requiresRegexp: false },
    { value: '<=', label: '小于等于 (≤)', requiresMultiValue: false, requiresRegexp: false },
    { value: '=', label: '等于 (=)', requiresMultiValue: false, requiresRegexp: false },
    { value: '!=', label: '不等于 (≠)', requiresMultiValue: false, requiresRegexp: false },
  ],
  set: [
    { value: 'in', label: '在集合内 (IN)', requiresMultiValue: true, requiresRegexp: false },
    { value: 'not in', label: '不在集合内 (NOT IN)', requiresMultiValue: true, requiresRegexp: false },
  ],
  pattern: [
    { value: 'regexp', label: '正则匹配 (REGEXP)', requiresMultiValue: false, requiresRegexp: true },
    { value: 'not regexp', label: '正则不匹配 (NOT REGEXP)', requiresMultiValue: false, requiresRegexp: true },
  ],
}

/**
 * 操作符兼容性矩阵
 */
export const ALLOWED_OPERATORS: Record<IndicatorDataType, ComparisonOperator[]> = {
  numeric: ['>', '>=', '<', '<=', '=', '!=', 'in', 'not in'],
  enum: ['=', '!=', 'in', 'not in'],
  text: ['=', '!=', 'in', 'not in', 'regexp', 'not regexp'],
  boolean: ['=', '!='],
}

// ==================== 辅助函数 ====================

/**
 * 判断操作符是否需要多值输入
 */
export function isMultiValueOperator(operator: ComparisonOperator): boolean {
  return operator === 'in' || operator === 'not in'
}

/**
 * 判断操作符是否需要正则输入
 */
export function isRegexpOperator(operator: ComparisonOperator): boolean {
  return operator === 'regexp' || operator === 'not regexp'
}

/**
 * 获取操作符标签
 */
export function getOperatorLabel(operator: ComparisonOperator): string {
  const allOperators = [
    ...OPERATOR_GROUPS.comparison,
    ...OPERATOR_GROUPS.set,
    ...OPERATOR_GROUPS.pattern,
  ]
  const option = allOperators.find(op => op.value === operator)
  return option?.label || operator
}

/**
 * 根据数据类型获取允许的操作符
 */
export function getAllowedOperatorsForType(dataType?: IndicatorDataType): ComparisonOperator[] {
  if (!dataType) {
    return ALLOWED_OPERATORS.numeric // 默认返回numeric的操作符
  }
  return ALLOWED_OPERATORS[dataType] || []
}

/**
 * 获取默认值
 */
export function getDefaultValue(dataType?: IndicatorDataType): string | number | boolean {
  switch (dataType) {
    case 'boolean':
      return false
    case 'numeric':
      return 0
    case 'enum':
    case 'text':
    default:
      return ''
  }
}
