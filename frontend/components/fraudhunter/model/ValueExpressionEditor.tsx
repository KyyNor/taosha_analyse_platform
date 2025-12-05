'use client'

/**
 * 值表达式编辑器组件
 *
 * 支持四种值表达式类型：
 * 1. 常量值 (ConstantValue)
 * 2. 指标引用 (IndicatorReference)
 * 3. 时间函数 (TimeFunction)
 * 4. 数学函数 (MathFunction)
 */

import React, { useMemo } from 'react'
import {
  ValueExpression,
  ConstantValue,
  IndicatorReference,
  TimeFunction,
  MathFunction,
  ValueType,
  TimeUnit,
  ComparisonOperator,
  Indicator,
  IndicatorDataType,
  getAllowedValueTypes,
  createDefaultConstantValue,
  createDefaultIndicatorReference,
  createDefaultTimeFunction,
  createDefaultMathFunction,
  valueExpressionToString,
  isMultiValueOperator,
  isRegexpOperator
} from '@/types/fraudhunter/rule'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { X } from 'lucide-react'

// ==================== 主组件 ====================

interface ValueExpressionEditorProps {
  leftIndicator?: Indicator
  operator: ComparisonOperator
  value: ValueExpression
  indicators: Indicator[]
  onChange: (value: ValueExpression) => void
}

export function ValueExpressionEditor({
  leftIndicator,
  operator,
  value,
  indicators,
  onChange
}: ValueExpressionEditorProps) {

  // 根据操作符限制可用值类型
  const availableTypes = useMemo(
    () => getAllowedValueTypes(operator),
    [operator]
  )

  // 值类型切换
  const handleTypeChange = (newType: ValueType) => {
    switch (newType) {
      case 'constant':
        onChange(createDefaultConstantValue(leftIndicator?.data_type))
        break

      case 'indicator':
        const compatibleIndicators = indicators.filter(
          ind => ind.data_type === leftIndicator?.data_type
        )
        const newRef = createDefaultIndicatorReference()
        if (compatibleIndicators.length > 0) {
          newRef.indicator = compatibleIndicators[0].indicator_code
        }
        onChange(newRef)
        break

      case 'time_function':
        const dateIndicators = indicators.filter(ind => ind.data_type === 'text')
        const newTimeFunc = createDefaultTimeFunction()
        if (dateIndicators.length > 0) {
          newTimeFunc.indicator = dateIndicators[0].indicator_code
        }
        onChange(newTimeFunc)
        break

      case 'math_function':
        const numericIndicators = indicators.filter(ind => ind.data_type === 'numeric')
        const newMathFunc = createDefaultMathFunction()
        if (numericIndicators.length > 0) {
          newMathFunc.indicator = numericIndicators[0].indicator_code
        }
        onChange(newMathFunc)
        break
    }
  }

  return (
    <div className="space-y-3 p-3 border rounded-md bg-muted/30">
      {/* 值类型选择 */}
      <div className="flex items-center gap-2">
        <Label className="text-xs w-20 shrink-0">值类型</Label>
        <Select value={value.type} onValueChange={handleTypeChange}>
          <SelectTrigger className="w-[160px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {availableTypes.includes('constant') && (
              <SelectItem value="constant">常量值</SelectItem>
            )}
            {availableTypes.includes('indicator') && (
              <SelectItem value="indicator">指标引用</SelectItem>
            )}
            {availableTypes.includes('time_function') && (
              <SelectItem value="time_function">时间函数</SelectItem>
            )}
            {availableTypes.includes('math_function') && (
              <SelectItem value="math_function">数学函数</SelectItem>
            )}
          </SelectContent>
        </Select>

        {/* 值预览 */}
        <Badge variant="outline" className="ml-auto font-mono text-xs">
          {valueExpressionToString(value)}
        </Badge>
      </div>

      {/* 根据类型渲染编辑器 */}
      {value.type === 'constant' && (
        <ConstantValueInput
          dataType={leftIndicator?.data_type}
          value={value.value}
          operator={operator}
          onChange={(v) => onChange({ ...value, value: v })}
        />
      )}

      {value.type === 'indicator' && (
        <IndicatorReferenceInput
          leftIndicator={leftIndicator}
          selectedCode={value.indicator}
          indicators={indicators}
          onChange={(ind) => onChange({ ...value, indicator: ind })}
        />
      )}

      {value.type === 'time_function' && (
        <TimeFunctionInput
          timeFunc={value}
          indicators={indicators}
          onChange={onChange}
        />
      )}

      {value.type === 'math_function' && (
        <MathFunctionInput
          mathFunc={value}
          indicators={indicators}
          onChange={onChange}
        />
      )}
    </div>
  )
}

// ==================== 常量值输入组件 ====================

interface ConstantValueInputProps {
  dataType?: IndicatorDataType
  value: string | number | boolean | string[] | number[]
  operator: ComparisonOperator
  onChange: (value: string | number | boolean | string[] | number[]) => void
}

function ConstantValueInput({ dataType, value, operator, onChange }: ConstantValueInputProps) {
  // 多值输入（用于 in/not in）
  if (isMultiValueOperator(operator)) {
    return (
      <MultiValueInput
        values={Array.isArray(value) ? value : []}
        dataType={dataType}
        onChange={onChange}
      />
    )
  }

  // 正则输入
  if (isRegexpOperator(operator)) {
    return (
      <div className="space-y-2">
        <Label className="text-xs">正则表达式</Label>
        <Input
          type="text"
          value={typeof value === 'string' ? value : ''}
          onChange={(e) => onChange(e.target.value)}
          placeholder="如：^admin|^test"
          className="font-mono"
        />
      </div>
    )
  }

  // 布尔值
  if (dataType === 'boolean') {
    return (
      <div className="space-y-2">
        <Label className="text-xs">布尔值</Label>
        <Select
          value={String(value)}
          onValueChange={(v) => onChange(v === 'true')}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="true">True</SelectItem>
            <SelectItem value="false">False</SelectItem>
          </SelectContent>
        </Select>
      </div>
    )
  }

  // 数值输入
  if (dataType === 'numeric') {
    return (
      <div className="space-y-2">
        <Label className="text-xs">数值</Label>
        <Input
          type="number"
          value={typeof value === 'number' ? value : 0}
          onChange={(e) => onChange(Number(e.target.value))}
        />
      </div>
    )
  }

  // 文本输入（默认）
  return (
    <div className="space-y-2">
      <Label className="text-xs">常量值</Label>
      <Input
        type="text"
        value={String(value)}
        onChange={(e) => onChange(e.target.value)}
        placeholder="请输入值"
      />
    </div>
  )
}

// ==================== 多值输入组件 ====================

interface MultiValueInputProps {
  values: (string | number)[]
  dataType?: IndicatorDataType
  onChange: (values: string[] | number[]) => void
}

function MultiValueInput({ values, dataType, onChange }: MultiValueInputProps) {
  const [inputValue, setInputValue] = React.useState('')

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      e.preventDefault()
      const newValue = dataType === 'numeric' ? Number(inputValue) : inputValue.trim()
      onChange([...values, newValue] as any)
      setInputValue('')
    }
  }

  const handleRemove = (index: number) => {
    onChange(values.filter((_, i) => i !== index) as any)
  }

  return (
    <div className="space-y-2">
      <Label className="text-xs">数组值（按 Enter 添加）</Label>
      <div className="flex flex-wrap gap-2 p-2 border rounded-md min-h-[40px]">
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
      <Input
        type={dataType === 'numeric' ? 'number' : 'text'}
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="输入值后按 Enter 添加"
      />
    </div>
  )
}

// ==================== 指标引用输入组件 ====================

interface IndicatorReferenceInputProps {
  leftIndicator?: Indicator
  selectedCode: string
  indicators: Indicator[]
  onChange: (indicator: string) => void
}

function IndicatorReferenceInput({
  leftIndicator,
  selectedCode,
  indicators,
  onChange
}: IndicatorReferenceInputProps) {
  // 只显示类型兼容的指标（严格类型验证）
  const compatibleIndicators = useMemo(() => {
    if (!leftIndicator) return indicators
    return indicators.filter(ind => ind.data_type === leftIndicator.data_type)
  }, [indicators, leftIndicator])

  return (
    <div className="space-y-2">
      <Label className="text-xs">选择指标</Label>
      <Select value={selectedCode} onValueChange={onChange}>
        <SelectTrigger>
          <SelectValue placeholder="选择指标" />
        </SelectTrigger>
        <SelectContent>
          {compatibleIndicators.map(ind => (
            <SelectItem key={ind.indicator_code} value={ind.indicator_code}>
              <div className="flex items-center justify-between w-full gap-2">
                <span className="text-sm">{ind.indicator_name}</span>
                <Badge variant="secondary" className="text-xs">
                  {ind.data_type}
                </Badge>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {compatibleIndicators.length === 0 && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="text-xs">
            没有类型兼容的指标（需要 {leftIndicator?.data_type || 'unknown'} 类型）
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}

// ==================== 时间函数输入组件 ====================

interface TimeFunctionInputProps {
  timeFunc: TimeFunction
  indicators: Indicator[]
  onChange: (timeFunc: TimeFunction) => void
}

function TimeFunctionInput({ timeFunc, indicators, onChange }: TimeFunctionInputProps) {
  // 只显示 text 类型的指标（日期字段）
  const dateIndicators = useMemo(
    () => indicators.filter(ind => ind.data_type === 'text'),
    [indicators]
  )

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <Label className="text-xs">函数</Label>
          <Select
            value={timeFunc.function}
            onValueChange={(v: 'date_add' | 'date_sub') =>
              onChange({ ...timeFunc, function: v })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="date_add">date_add（加）</SelectItem>
              <SelectItem value="date_sub">date_sub（减）</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label className="text-xs">时间单位</Label>
          <Select
            value={timeFunc.unit}
            onValueChange={(v: TimeUnit) =>
              onChange({ ...timeFunc, unit: v })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="days">天 (days)</SelectItem>
              <SelectItem value="months">月 (months)</SelectItem>
              <SelectItem value="years">年 (years)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label className="text-xs">日期指标</Label>
        <Select
          value={timeFunc.indicator}
          onValueChange={(v) => onChange({ ...timeFunc, indicator: v })}
        >
          <SelectTrigger>
            <SelectValue placeholder="选择日期指标" />
          </SelectTrigger>
          <SelectContent>
            {dateIndicators.map(ind => (
              <SelectItem key={ind.indicator_code} value={ind.indicator_code}>
                <div className="flex items-center justify-between w-full gap-2">
                  <span className="text-sm">{ind.indicator_name}</span>
                  <span className="text-xs text-muted-foreground">
                    {ind.indicator_code}
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label className="text-xs">偏移量</Label>
        <Input
          type="number"
          value={timeFunc.offset}
          onChange={(e) => onChange({ ...timeFunc, offset: Number(e.target.value) })}
          min={-3650}
          max={3650}
        />
      </div>

      <Alert>
        <AlertDescription className="text-xs font-mono">
          {timeFunc.function}({timeFunc.indicator || '<选择指标>'}, {timeFunc.offset}, '{timeFunc.unit}')
        </AlertDescription>
      </Alert>
    </div>
  )
}

// ==================== 数学函数输入组件 ====================

interface MathFunctionInputProps {
  mathFunc: MathFunction
  indicators: Indicator[]
  onChange: (mathFunc: MathFunction) => void
}

function MathFunctionInput({ mathFunc, indicators, onChange }: MathFunctionInputProps) {
  // 只显示 numeric 类型的指标
  const numericIndicators = useMemo(
    () => indicators.filter(ind => ind.data_type === 'numeric'),
    [indicators]
  )

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <Label className="text-xs">函数</Label>
        <Select value="abs" disabled>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="abs">abs (绝对值)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label className="text-xs">数值指标</Label>
        <Select
          value={mathFunc.indicator}
          onValueChange={(v) => onChange({ ...mathFunc, indicator: v })}
        >
          <SelectTrigger>
            <SelectValue placeholder="选择数值指标" />
          </SelectTrigger>
          <SelectContent>
            {numericIndicators.map(ind => (
              <SelectItem key={ind.indicator_code} value={ind.indicator_code}>
                <div className="flex items-center justify-between w-full gap-2">
                  <span className="text-sm">{ind.indicator_name}</span>
                  <span className="text-xs text-muted-foreground">
                    {ind.indicator_code}
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Alert>
        <AlertDescription className="text-xs font-mono">
          abs({mathFunc.indicator || '<选择指标>'})
        </AlertDescription>
      </Alert>
    </div>
  )
}
