'use client'

/**
 * 条件规则编辑器组件
 *
 * 功能：
 * - 指标选择（根据数据类型动态限制可用操作符）
 * - 操作符选择（支持基础比较、集合操作、正则匹配）
 * - 值输入（支持单值、多值数组、正则表达式）
 * - 自动类型转换（操作符切换时值类型自动适配）
 */

import { useState, useEffect } from 'react'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { X, Plus, AlertCircle } from 'lucide-react'
import {
  ConditionRule,
  Indicator,
  ComparisonOperator,
  OPERATOR_GROUPS,
  getAllowedOperatorsForType,
  isMultiValueOperator,
  isRegexpOperator,
  getOperatorLabel,
  getDefaultValue
} from '@/types/fraudhunter/rule'

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
      value: getDefaultValue(newIndicator?.data_type)
    })
  }

  // ==================== 操作符变更处理 ====================

  const handleOperatorChange = (newOperator: ComparisonOperator) => {
    let newValue = rule.value

    // 从单值切换到多值（in/not in）
    if (!isMultiValueOperator(rule.operator) && isMultiValueOperator(newOperator)) {
      newValue = rule.value !== '' ? [rule.value] : []
    }
    // 从多值切换到单值
    else if (isMultiValueOperator(rule.operator) && !isMultiValueOperator(newOperator)) {
      newValue = Array.isArray(rule.value) && rule.value.length > 0
        ? rule.value[0]
        : getDefaultValue(currentIndicator?.data_type)
    }
    // 从其他类型切换到正则
    else if (!isRegexpOperator(rule.operator) && isRegexpOperator(newOperator)) {
      newValue = ''
    }

    onChange({ ...rule, operator: newOperator, value: newValue })
  }

  // ==================== 值输入控件渲染 ====================

  const renderValueInput = () => {
    if (!currentIndicator) return null

    // 多值输入（in/not in）
    if (isMultiValueOperator(rule.operator)) {
      return <MultiValueInput
        dataType={currentIndicator.data_type}
        values={Array.isArray(rule.value) ? rule.value : []}
        onChange={(values) => onChange({ ...rule, value: values })}
      />
    }

    // 正则表达式输入（regexp/not regexp）
    if (isRegexpOperator(rule.operator)) {
      return <RegexpInput
        value={String(rule.value)}
        onChange={(value) => onChange({ ...rule, value })}
      />
    }

    // 单值输入
    switch (currentIndicator.data_type) {
      case 'numeric':
        return (
          <Input
            type="number"
            value={rule.value as number}
            onChange={(e) => onChange({ ...rule, value: Number(e.target.value) })}
            className="w-32"
            placeholder="输入数值"
          />
        )

      case 'boolean':
        return (
          <Select
            value={String(rule.value)}
            onValueChange={(v) => onChange({ ...rule, value: v === 'true' })}
          >
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="true">真</SelectItem>
              <SelectItem value="false">假</SelectItem>
            </SelectContent>
          </Select>
        )

      case 'enum':
        return (
          <Select
            value={String(rule.value)}
            onValueChange={(v) => onChange({ ...rule, value: v })}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="选择值" />
            </SelectTrigger>
            <SelectContent>
              {currentIndicator.enum_values?.map((val) => (
                <SelectItem key={val} value={val}>{val}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )

      default:
        return (
          <Input
            type="text"
            value={String(rule.value)}
            onChange={(e) => onChange({ ...rule, value: e.target.value })}
            className="w-40"
            placeholder="输入文本"
          />
        )
    }
  }

  // ==================== 渲染逻辑 ====================

  return (
    <Card className="p-3 bg-muted/50">
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

        {/* 值输入 */}
        <div className="flex-grow min-w-0">
          {renderValueInput()}
        </div>
      </div>
    </Card>
  )
}

// ==================== 多值输入组件 ====================

interface MultiValueInputProps {
  dataType: string
  values: (string | number)[]
  onChange: (values: (string | number)[]) => void
}

function MultiValueInput({ dataType, values, onChange }: MultiValueInputProps) {
  const [inputValue, setInputValue] = useState('')

  const handleAdd = () => {
    if (!inputValue.trim()) return

    const newValue = dataType === 'numeric' ? Number(inputValue) : inputValue
    onChange([...values, newValue])
    setInputValue('')
  }

  const handleRemove = (index: number) => {
    onChange(values.filter((_, i) => i !== index))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAdd()
    }
  }

  return (
    <div className="space-y-2 w-full">
      {/* 已添加的值 */}
      {values.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {values.map((val, idx) => (
            <Badge key={idx} variant="secondary" className="gap-1">
              {String(val)}
              <X
                className="h-3 w-3 cursor-pointer hover:text-destructive"
                onClick={() => handleRemove(idx)}
              />
            </Badge>
          ))}
        </div>
      )}

      {/* 输入框 */}
      <div className="flex gap-2">
        <Input
          type={dataType === 'numeric' ? 'number' : 'text'}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入值后按回车添加"
          className="flex-1"
        />
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={handleAdd}
          disabled={!inputValue.trim()}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      <p className="text-xs text-muted-foreground">
        已添加 {values.length} 个值
      </p>
    </div>
  )
}

// ==================== 正则表达式输入组件 ====================

interface RegexpInputProps {
  value: string
  onChange: (value: string) => void
}

function RegexpInput({ value, onChange }: RegexpInputProps) {
  const [isValid, setIsValid] = useState(true)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    // 实时验证正则表达式
    if (!value) {
      setIsValid(true)
      setError('')
      return
    }

    try {
      new RegExp(value)
      setIsValid(true)
      setError('')
    } catch (e: any) {
      setIsValid(false)
      setError(e.message)
    }
  }, [value])

  return (
    <div className="space-y-2 w-full">
      {/* 输入框 */}
      <Input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={!isValid ? 'border-destructive' : ''}
        placeholder="输入正则表达式，如：^admin|^test"
      />

      {/* 错误提示 */}
      {!isValid && error && (
        <div className="flex items-center gap-2 text-destructive text-xs">
          <AlertCircle className="h-3 w-3" />
          <span>{error}</span>
        </div>
      )}

      {/* 常用模式提示 */}
      <div className="text-xs text-muted-foreground space-y-1">
        <p className="font-medium">常用模式：</p>
        <ul className="space-y-0.5 ml-2">
          <li>• <code className="bg-muted px-1 rounded">ab|cd</code> - 包含 ab 或 cd</li>
          <li>• <code className="bg-muted px-1 rounded">^admin|^test</code> - 以 admin 或 test 开头</li>
          <li>• <code className="bg-muted px-1 rounded">@qq\.com$</code> - 以 @qq.com 结尾</li>
        </ul>
      </div>
    </div>
  )
}
