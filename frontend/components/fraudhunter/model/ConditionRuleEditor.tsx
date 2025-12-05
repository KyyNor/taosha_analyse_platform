'use client'

/**
 * 条件规则编辑器组件
 *
 * 版本: v2.1.0 (支持值表达式)
 *
 * 功能：
 * - 指标选择（根据数据类型动态限制可用操作符）
 * - 操作符选择（支持基础比较、集合操作、正则匹配）
 * - 值表达式编辑（支持常量值、指标引用、时间函数、数学函数）
 * - 自动类型转换（操作符切换时值类型自动适配）
 */

import { useState, useEffect } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card } from '@/components/ui/card'
import {
  ConditionRule,
  Indicator,
  ComparisonOperator,
  OPERATOR_GROUPS,
  getAllowedOperatorsForType,
  createDefaultConstantValue
} from '@/types/fraudhunter/rule'
import { ValueExpressionEditor } from './ValueExpressionEditor'

interface ConditionRuleEditorProps {
  rule: ConditionRule
  indicators: Indicator[]
  onChange: (rule: ConditionRule) => void
}

export function ConditionRuleEditor({ rule, indicators, onChange }: ConditionRuleEditorProps) {
  // 获取当前指标信息
  const currentIndicator = indicators.find(ind => ind.indicator_code === rule.indicator)

  // ==================== 操作符兼容性逻辑 ====================

  const allowedOperators = getAllowedOperatorsForType(currentIndicator?.data_type)

  // ==================== 指标变更处理 ====================

  const handleIndicatorChange = (indicatorCode: string) => {
    const newIndicator = indicators.find(ind => ind.indicator_code === indicatorCode)
    const newAllowedOps = getAllowedOperatorsForType(newIndicator?.data_type)

    onChange({
      ...rule,
      indicator: indicatorCode,
      operator: newAllowedOps[0] || '>',
      value: createDefaultConstantValue(newIndicator?.data_type)
    })
  }

  // ==================== 操作符变更处理 ====================

  const handleOperatorChange = (newOperator: ComparisonOperator) => {
    // 操作符变更时保持现有值表达式，或重置为默认常量值
    // ValueExpressionEditor 组件会根据操作符自动限制可用的值类型
    onChange({ ...rule, operator: newOperator })
  }

  // ==================== 渲染逻辑 ====================

  return (
    <Card className="p-3 bg-muted/50 space-y-3">
      <div className="flex items-center space-x-2 flex-wrap gap-2">
        {/* 指标选择 */}
        <div className="flex-shrink-0">
          <Select value={rule.indicator} onValueChange={handleIndicatorChange}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="选择指标" />
            </SelectTrigger>
            <SelectContent>
              {indicators.map((ind) => (
                <SelectItem key={ind.indicator_code} value={ind.indicator_code}>
                  <div className="flex items-center justify-between w-full">
                    <span>{ind.indicator_name}</span>
                    <span className="text-xs text-muted-foreground ml-2">
                      ({ind.data_type})
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 操作符选择 */}
        <div className="flex-shrink-0">
          <Select
            value={rule.operator}
            onValueChange={(v) => handleOperatorChange(v as ComparisonOperator)}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {/* 基础比较操作符 */}
              {OPERATOR_GROUPS.comparison.some(op => allowedOperators.includes(op.value)) && (
                <>
                  <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
                    基础比较
                  </div>
                  {OPERATOR_GROUPS.comparison
                    .filter(op => allowedOperators.includes(op.value))
                    .map((op) => (
                      <SelectItem key={op.value} value={op.value}>
                        {op.label}
                      </SelectItem>
                    ))}
                </>
              )}

              {/* 集合操作符 */}
              {OPERATOR_GROUPS.set.some(op => allowedOperators.includes(op.value)) && (
                <>
                  <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground border-t mt-1">
                    集合操作
                  </div>
                  {OPERATOR_GROUPS.set
                    .filter(op => allowedOperators.includes(op.value))
                    .map((op) => (
                      <SelectItem key={op.value} value={op.value}>
                        {op.label}
                      </SelectItem>
                    ))}
                </>
              )}

              {/* 正则匹配操作符 */}
              {OPERATOR_GROUPS.pattern.some(op => allowedOperators.includes(op.value)) && (
                <>
                  <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground border-t mt-1">
                    正则匹配
                  </div>
                  {OPERATOR_GROUPS.pattern
                    .filter(op => allowedOperators.includes(op.value))
                    .map((op) => (
                      <SelectItem key={op.value} value={op.value}>
                        {op.label}
                      </SelectItem>
                    ))}
                </>
              )}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 值表达式编辑器 */}
      <ValueExpressionEditor
        leftIndicator={currentIndicator}
        operator={rule.operator}
        value={rule.value}
        indicators={indicators}
        onChange={(value) => onChange({ ...rule, value })}
      />
    </Card>
  )
}
