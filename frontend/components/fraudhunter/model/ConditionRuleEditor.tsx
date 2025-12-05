'use client'

/**
 * 条件规则编辑器组件 - 单行布局版本
 *
 * 版本: v2.2.0 (单行布局优化)
 *
 * 功能：
 * - 单行水平布局，所有元素在一行内显示
 * - 支持左元素指标选择和函数处理
 * - 支持右元素类型切换（常量/指标/时间函数）
 * - 自动类型验证和兼容性检查
 */

import { useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  ConditionRule,
  Indicator,
  ComparisonOperator,
  OPERATOR_GROUPS,
  getAllowedOperatorsForType,
  createDefaultConstantValue,
  isNumericType,
  isDateType,
  isCompatibleType,
  getInputType,
  isMultiValueOperator,
  isRegexpOperator
} from '@/types/fraudhunter/rule'

interface ConditionRuleEditorProps {
  rule: ConditionRule
  indicators: Indicator[]
  onChange: (rule: ConditionRule) => void
  showLogic?: boolean
  logic?: 'AND' | 'OR'
  onLogicChange?: (logic: 'AND' | 'OR') => void
}

export function ConditionRuleEditor({
  rule,
  indicators,
  onChange,
  showLogic = false,
  logic = 'AND',
  onLogicChange
}: ConditionRuleEditorProps) {
  // 获取当前指标信息
  const currentIndicator = indicators.find(ind => ind.indicator_code === rule.indicator)

  // ==================== 处理函数 ====================

  // 指标变更处理
  const handleIndicatorChange = (indicatorCode: string) => {
    const newIndicator = indicators.find(ind => ind.indicator_code === indicatorCode)
    const newAllowedOps = getAllowedOperatorsForType(newIndicator?.data_type)

    // 如果左元素函数不兼容，清除函数
    let leftFunction = rule.leftFunction
    if (leftFunction && leftFunction !== 'none' && !isNumericType(newIndicator?.data_type)) {
      leftFunction = undefined
    }

    onChange({
      ...rule,
      indicator: indicatorCode,
      operator: newAllowedOps[0] || '>',
      value: createDefaultConstantValue(newIndicator?.data_type),
      leftFunction
    })
  }

  // 左元素函数变更处理
  const handleLeftFunctionChange = (value: string) => {
    onChange({
      ...rule,
      leftFunction: value === 'none' ? undefined : (value as 'abs')
    })
  }

  // 操作符变更处理
  const handleOperatorChange = (newOperator: ComparisonOperator) => {
    onChange({ ...rule, operator: newOperator })
  }

  // 值类型变更处理
  const handleValueTypeChange = (valueType: string) => {
    let newValue: any

    switch (valueType) {
      case 'indicator':
        newValue = {
          type: 'indicator',
          indicator: indicators.find(ind =>
            isCompatibleType(currentIndicator?.data_type, ind.data_type)
          )?.indicator_code || ''
        }
        break
      case 'time_function':
        newValue = {
          type: 'time_function',
          function: 'date_add',
          indicator: indicators.find(ind => ind.data_type === 'date')?.indicator_code || '',
          offset: 7,
          unit: 'days' as const
        }
        break
      case 'math_function':
        newValue = {
          type: 'math_function',
          function: 'abs',
          indicator: indicators.find(ind => isNumericType(ind.data_type))?.indicator_code || ''
        }
        break
      default:
        newValue = createDefaultConstantValue(currentIndicator?.data_type)
    }

    onChange({ ...rule, value: newValue })
  }

  // 更新值表达式
  const updateValue = (newValue: any) => {
    onChange({ ...rule, value: newValue })
  }

  // ==================== 渲染右元素配置 ====================

  const renderValueConfig = () => {
    switch (rule.value.type) {
      case 'constant':
        if (isMultiValueOperator(rule.operator)) {
          return (
            <Textarea
              value={Array.isArray(rule.value.value) ? rule.value.value.join('\n') : (rule.value.value || '')}
              onChange={(e) => updateValue({
                ...rule.value,
                value: e.target.value.split('\n').filter(v => v.trim())
              })}
              placeholder="每行一个值"
              className="h-20 resize-none"
            />
          )
        } else if (isRegexpOperator(rule.operator)) {
          return (
            <Input
              value={rule.value.value || ''}
              onChange={(e) => updateValue({ ...rule.value, value: e.target.value })}
              placeholder="正则表达式"
              className="flex-1"
            />
          )
        } else {
          return (
            <Input
              value={rule.value.value || ''}
              onChange={(e) => updateValue({
                ...rule.value,
                value: currentIndicator?.data_type === 'bool' || currentIndicator?.data_type === 'boolean'
                  ? e.target.checked
                  : (currentIndicator?.data_type === 'int' || currentIndicator?.data_type === 'float' || currentIndicator?.data_type === 'numeric'
                      ? parseFloat(e.target.value) || 0
                      : e.target.value)
              })}
              type={getInputType(currentIndicator?.data_type)}
              className="flex-1"
            />
          )
        }

      case 'indicator':
        return (
          <Select
            value={rule.value.indicator}
            onValueChange={(value) => updateValue({ ...rule.value, indicator: value })}
          >
            <SelectTrigger className="w-[150px] h-8">
              <SelectValue placeholder="选择指标" />
            </SelectTrigger>
            <SelectContent>
              {indicators
                .filter(ind => isCompatibleType(currentIndicator?.data_type, ind.data_type))
                .map(ind => (
                  <SelectItem key={ind.indicator_code} value={ind.indicator_code}>
                    {ind.indicator_name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        )

      case 'time_function':
        return (
          <div className="flex items-center gap-1 flex-wrap">
            <Select
              value={rule.value.function}
              onValueChange={(value) => updateValue({ ...rule.value, function: value as 'date_add' | 'date_sub' })}
            >
              <SelectTrigger className="w-[100px] h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="date_add">date_add</SelectItem>
                <SelectItem value="date_sub">date_sub</SelectItem>
              </SelectContent>
            </Select>

            <span className="text-sm text-muted-foreground">(</span>

            <Select
              value={rule.value.indicator}
              onValueChange={(value) => updateValue({ ...rule.value, indicator: value })}
            >
              <SelectTrigger className="w-[150px] h-8">
                <SelectValue placeholder="时间指标" />
              </SelectTrigger>
              <SelectContent>
                {indicators
                  .filter(ind => ind.data_type === 'date')
                  .map(ind => (
                    <SelectItem key={ind.indicator_code} value={ind.indicator_code}>
                      {ind.indicator_name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>

            <Input
              type="number"
              value={rule.value.offset || 0}
              onChange={(e) => updateValue({ ...rule.value, offset: parseInt(e.target.value) || 0 })}
              className="w-[80px] h-8"
            />

            <Select
              value={rule.value.unit || 'days'}
              onValueChange={(value) => updateValue({ ...rule.value, unit: value as 'days' | 'months' })}
            >
              <SelectTrigger className="w-[80px] h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="days">天</SelectItem>
                <SelectItem value="months">月</SelectItem>
              </SelectContent>
            </Select>

            <span className="text-sm text-muted-foreground">)</span>
          </div>
        )

      case 'math_function':
        return (
          <div className="flex items-center gap-1">
            <span className="text-sm text-muted-foreground">{rule.value.function}(</span>
            <Select
              value={rule.value.indicator}
              onValueChange={(value) => updateValue({ ...rule.value, indicator: value })}
            >
              <SelectTrigger className="w-[150px] h-8">
                <SelectValue placeholder="数值指标" />
              </SelectTrigger>
              <SelectContent>
                {indicators
                  .filter(ind => isNumericType(ind.data_type))
                  .map(ind => (
                    <SelectItem key={ind.indicator_code} value={ind.indicator_code}>
                      {ind.indicator_name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
            <span className="text-sm text-muted-foreground">)</span>
          </div>
        )

      default:
        return null
    }
  }

  // ==================== 主渲染 ====================

  const allowedOperators = getAllowedOperatorsForType(currentIndicator?.data_type)

  return (
    <div className="flex items-center gap-2 w-full py-2">
      {/* 逻辑连接符 */}
      {showLogic && (
        <div className="flex-shrink-0">
          <Select value={logic} onValueChange={onLogicChange}>
            <SelectTrigger className="w-[80px] h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="AND">AND</SelectItem>
              <SelectItem value="OR">OR</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {/* 左元素：指标 + 可选函数 */}
      <div className="flex items-center gap-1 flex-shrink-0">
        <Select value={rule.indicator} onValueChange={handleIndicatorChange}>
          <SelectTrigger className="w-[180px] h-8">
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

        {/* 函数选择（仅数值类型显示） */}
        {isNumericType(currentIndicator?.data_type) && (
          <Select value={rule.leftFunction || 'none'} onValueChange={handleLeftFunctionChange}>
            <SelectTrigger className="w-[80px] h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">无</SelectItem>
              <SelectItem value="abs">abs</SelectItem>
            </SelectContent>
          </Select>
        )}
      </div>

      {/* 操作符 */}
      <div className="flex-shrink-0">
        <Select
          value={rule.operator}
          onValueChange={(v) => handleOperatorChange(v as ComparisonOperator)}
        >
          <SelectTrigger className="w-[120px] h-8">
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

      {/* 右元素：类型切换 + 动态配置 */}
      <div className="flex items-center gap-1 flex-1 min-w-[200px]">
        {/* 类型切换 */}
        <Select
          value={rule.value.type}
          onValueChange={handleValueTypeChange}
        >
          <SelectTrigger className="w-[100px] h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="constant">常量</SelectItem>
            <SelectItem value="indicator">指标</SelectItem>
            <SelectItem value="time_function">时间函数</SelectItem>
            <SelectItem value="math_function">数学函数</SelectItem>
          </SelectContent>
        </Select>

        {/* 根据类型显示配置 */}
        {renderValueConfig()}
      </div>

      {/* 类型预览标签 */}
      <div className="flex-shrink-0">
        <Badge variant="outline" className="text-xs">
          {currentIndicator?.data_type || 'unknown'}
        </Badge>
      </div>
    </div>
  )
}