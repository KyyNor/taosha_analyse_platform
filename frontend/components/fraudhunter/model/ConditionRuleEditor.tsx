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

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { X, Plus } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import React, { useRef, useEffect, useState } from 'react'
import {
  ConditionRule,
  Indicator,
  ComparisonOperator,
  OPERATOR_GROUPS,
  getAllowedOperatorsForType,
  createDefaultConstantValue,
  isNumericType,
  isCompatibleType,
  getInputType,
  isMultiValueOperator,
  isRegexpOperator,
  getIndicatorDisplayName
} from '@/types/fraudhunter/rule'
import { IndicatorCombobox } from './IndicatorCombobox'

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
    let left_function = rule.left_function
    if (left_function && !isNumericType(newIndicator?.data_type)) {
      left_function = undefined
    }

    onChange({
      ...rule,
      indicator: indicatorCode,
      operator: newAllowedOps[0] || '>',
      value: createDefaultConstantValue(newIndicator?.data_type),
      left_function
    })
  }

  // 左元素函数变更处理
  const handleLeftFunctionChange = (value: string) => {
    onChange({
      ...rule,
      left_function: value === 'none' ? undefined : 'abs'
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
      case 'relative_calculation':
        newValue = {
          type: 'relative_calculation',
          indicator: indicators.find(ind => isNumericType(ind.data_type))?.indicator_code || '',
          operation: 'multiply',
          value: 1.0
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
        if (isMultiValueOperator(rule.operator) || isRegexpOperator(rule.operator)) {
          // 将值转换为数组，并过滤掉布尔值（多值输入不支持布尔类型）
          const valueArray = Array.isArray(rule.value.value)
            ? rule.value.value.filter((v): v is string | number => typeof v !== 'boolean')
            : (rule.value.value !== undefined && typeof rule.value.value !== 'boolean' ? [rule.value.value] : []);

          return (
            <MultiValueInput
              values={valueArray}
              dataType={currentIndicator?.data_type}
              onChange={(values) => updateValue({ ...rule.value, value: values })}
            />
          )
        } else {
          // 其他类型使用普通输入框
          return (
            <Input
              value={String(rule.value.value || '')}
              onChange={(e) => {
                let newValue: string | number | boolean | string[] | number[]
                if (currentIndicator?.data_type === 'int' || currentIndicator?.data_type === 'float' || currentIndicator?.data_type === 'numeric') {
                  if (isNaN(parseFloat(e.target.value)) || parseFloat(e.target.value) === 0){
                    newValue = '0'
                  } else {
                    newValue = parseFloat(e.target.value)
                  }
                } else {
                  newValue = e.target.value
                }
                updateValue({ ...rule.value, value: newValue })
              }}
              type={getInputType(currentIndicator?.data_type)}
              className="flex-1"
            />
          )
        }

      case 'indicator':
        return (
          <IndicatorCombobox
            indicators={indicators}
            value={rule.value.indicator}
            onChange={(value) => updateValue({ ...rule.value, indicator: value })}
            placeholder="选择指标"
            className="w-[220px]"
            filterFn={(ind) => isCompatibleType(currentIndicator?.data_type, ind.data_type)}
          />
        )

      case 'time_function':
        // 特殊时间变量的显示名称
        const getTimeIndicatorDisplayValue = (indicator: string) => {
          if (indicator === '__T0__') return 'T日 (实时数据日期)'
          if (indicator === '__T_1__') return 'T-1日 (离线数据日期)'
          const ind = indicators.find(i => i.indicator_code === indicator)
          return ind ? getIndicatorDisplayName(ind) : indicator
        }

        return (
          <div className="flex items-center gap-1 flex-wrap">

            <span className="text-sm text-muted-foreground">(</span>

            <Select
              value={rule.value.indicator}
              onValueChange={(value) => updateValue({ ...rule.value, indicator: value })}
            >
              <SelectTrigger className="w-[180px] h-8">
                <SelectValue placeholder="时间指标">
                  {rule.value.indicator && getTimeIndicatorDisplayValue(rule.value.indicator)}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {/* 系统内置时间变量 */}
                <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
                  系统日期
                </div>
                <SelectItem value="__T0__">T日 (实时数据日期)</SelectItem>
                <SelectItem value="__T_1__">T-1日 (离线数据日期)</SelectItem>
                
                {/* 日期类型指标 */}
                {indicators.filter(ind => ind.data_type === 'date').length > 0 && (
                  <>
                    <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground border-t mt-1">
                      日期指标
                    </div>
                    {indicators
                      .filter(ind => ind.data_type === 'date')
                      .map(ind => (
                        <SelectItem key={ind.indicator_code} value={ind.indicator_code}>
                          {getIndicatorDisplayName(ind)}
                        </SelectItem>
                      ))}
                  </>
                )}
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
            <IndicatorCombobox
              indicators={indicators}
              value={rule.value.indicator}
              onChange={(value) => updateValue({ ...rule.value, indicator: value })}
              placeholder="数值指标"
              className="w-[220px]"
              filterFn={(ind) => isNumericType(ind.data_type)}
            />
            <span className="text-sm text-muted-foreground">)</span>
          </div>
        )

      case 'relative_calculation':
        return (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-muted-foreground">(</span>

            {/* 指标选择器 */}
            <IndicatorCombobox
              indicators={indicators.filter(ind => isNumericType(ind.data_type))}
              value={rule.value.indicator}
              onChange={(value) => updateValue({ ...rule.value, indicator: value })}
              placeholder="选择数值指标"
              className="w-[200px]"
            />

            {/* 运算符选择器 */}
            <Select
              value={rule.value.operation}
              onValueChange={(value) => updateValue({ ...rule.value, operation: value as any })}
            >
              <SelectTrigger className="w-[80px] h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="add">+</SelectItem>
                <SelectItem value="subtract">−</SelectItem>
                <SelectItem value="multiply">×</SelectItem>
                <SelectItem value="divide">÷</SelectItem>
              </SelectContent>
            </Select>

            {/* 常量数值输入 */}
            <Input
              type="number"
              step="any"
              value={rule.value.value}
              onChange={(e) => updateValue({ ...rule.value, value: parseFloat(e.target.value) || 0 })}
              className="w-[100px] h-8"
              placeholder="数值"
            />

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
    <>
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
          <IndicatorCombobox
            indicators={indicators}
            value={rule.indicator}
            onChange={handleIndicatorChange}
            placeholder="选择指标"
            className="w-[250px]"
          />

          {/* 函数选择（仅数值类型显示） */}
          {isNumericType(currentIndicator?.data_type) && (
            <Select value={rule.left_function || 'none'} onValueChange={handleLeftFunctionChange}>
              <SelectTrigger className="w-[80px] h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">无</SelectItem>
                <SelectItem value="abs">abs(绝对值)</SelectItem>
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
                    集合操作(精确匹配)
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

              {/* 包含匹配操作符 */}
              {OPERATOR_GROUPS.inclusion.some(op => allowedOperators.includes(op.value)) && (
                <>
                  <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground border-t mt-1">
                    包含/不包含(模糊匹配)
                  </div>
                  {OPERATOR_GROUPS.inclusion
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
              <SelectItem value="relative_calculation">相对计算</SelectItem>
            </SelectContent>
          </Select>

          {/* 根据类型显示配置 */}
          {renderValueConfig()}
        </div>
      </div>

    </>
  )
}

// ==================== 多值输入组件 ====================

interface MultiValueInputProps {
  values: (string | number)[]
  dataType?: string
  onChange: (values: (string | number)[]) => void
}

function MultiValueInput({ values, dataType, onChange }: MultiValueInputProps) {
  console.log('MultiValueInput 组件初始化, dataType:', dataType, 'initial values:', values)

  const [inputValue, setInputValue] = useState('')
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editValue, setEditValue] = useState('')
  const [showInput, setShowInput] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const editInputRef = useRef<HTMLInputElement>(null)

  // 自动聚焦输入框
  useEffect(() => {
    if (showInput && inputRef.current) {
      inputRef.current.focus()
    }
  }, [showInput])

  useEffect(() => {
    if (editingIndex !== null && editInputRef.current) {
      editInputRef.current.focus()
    }
  }, [editingIndex])

  // 类型转换函数
  const convertValue = (value: string): string | number => {
    if (dataType === 'numeric' || dataType === 'int' || dataType === 'float') {
      const num = Number(value)
      return isNaN(num) ? 0 : num
    }
    return value
  }

  // 验证输入值
  const validateValue = (value: string): boolean => {
    // 对于空值直接返回false
    if (!value || value.trim().length === 0) {
      return false
    }

    // 数值类型验证
    if (dataType === 'numeric' || dataType === 'int' || dataType === 'float') {
      const num = Number(value)
      const isValid = !isNaN(num)
      console.log(`数值验证: ${value} -> ${num}, valid: ${isValid}`)
      return isValid
    }

    // 其他类型默认通过验证
    console.log(`非数值验证通过: ${value}, dataType: ${dataType}`)
    return true
  }

  // 添加标签
  const addTag = () => {
    console.log('addTag called with inputValue:', inputValue, 'dataType:', dataType)

    if (!inputValue.trim()) {
      console.log('输入值为空，不添加')
      return
    }

    if (!validateValue(inputValue)) {
      console.log('验证失败，不添加值:', inputValue)
      return
    }

    const newValues = [...values, convertValue(inputValue.trim())]
    console.log('添加新标签:', newValues)
    onChange(newValues)
    setInputValue('')
    setShowInput(false)
  }

  // 删除标签
  const removeTag = (index: number) => {
    const newValues = values.filter((_, i) => i !== index)
    onChange(newValues)
  }

  // 开始编辑标签
  const startEditing = (index: number) => {
    setEditingIndex(index)
    setEditValue(String(values[index]))
  }

  // 完成编辑
  const finishEditing = () => {
    if (editingIndex !== null && editValue.trim() && validateValue(editValue)) {
      const newValues = [...values]
      newValues[editingIndex] = convertValue(editValue.trim())
      onChange(newValues)
    }
    setEditingIndex(null)
    setEditValue('')
  }

  // 取消编辑
  const cancelEditing = () => {
    setEditingIndex(null)
    setEditValue('')
  }

  // 处理键盘事件
  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    console.log('键盘事件:', e.key, 'inputValue:', inputValue)

    if (e.key === 'Enter') {
      console.log('按下Enter键，准备添加标签')
      e.preventDefault()
      addTag()
    } else if (e.key === 'Escape') {
      console.log('按下Escape键，取消输入')
      setShowInput(false)
      setInputValue('')
    }
  }

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      finishEditing()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      cancelEditing()
    }
  }

  // 截断长文本
  const truncateText = (text: string | number, maxLength: number = 15): string => {
    const str = String(text)
    return str.length > maxLength ? `${str.slice(0, maxLength)}...` : str
  }

  return (
    <div className="flex flex-wrap items-center gap-2 p-2 border rounded-md min-h-[40px]">
      {/* 现有标签 */}
      {values.map((value, index) => (
        <div key={index} className="relative">
          {editingIndex === index ? (
            <Input
              ref={editInputRef}
              type={dataType === 'numeric' || dataType === 'int' || dataType === 'float' ? 'number' : 'text'}
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={finishEditing}
              onKeyDown={handleEditKeyDown}
              className="h-6 w-20 text-xs"
            />
          ) : (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge
                  variant="secondary"
                  className="gap-1 cursor-pointer hover:bg-secondary/80"
                  onDoubleClick={() => startEditing(index)}
                >
                  <span>{truncateText(value)}</span>
                  <X
                    className="h-3 w-3 cursor-pointer hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation()
                      removeTag(index)
                    }}
                  />
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p>{String(value)}</p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      ))}

      {/* 添加按钮 */}
      {showInput ? (
        <Input
          ref={inputRef}
          type={dataType === 'numeric' || dataType === 'int' || dataType === 'float' ? 'number' : 'text'}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onBlur={addTag}
          onKeyDown={handleInputKeyDown}
          placeholder={dataType === 'numeric' || dataType === 'int' || dataType === 'float' ? "输入数值" : "输入文本"}
          className="h-6 w-24 text-xs"
        />
      ) : (
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowInput(true)}
          className="h-6 px-2 text-xs"
        >
          <Plus className="h-3 w-3 mr-1" />
          添加
        </Button>
      )}
    </div>
  )
}