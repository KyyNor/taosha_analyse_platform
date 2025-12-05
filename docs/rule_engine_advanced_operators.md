# FraudHunter 规则引擎高级操作符扩展

## 文档信息
- **版本**: v1.0.0
- **创建日期**: 2025-12-05
- **作者**: Claude Code
- **关联文档**: [rule_engine_implementation_guide.md](./rule_engine_implementation_guide.md)

## 目录
1. [新增操作符概述](#新增操作符概述)
2. [前端实现更新](#前端实现更新)
3. [后端实现更新](#后端实现更新)
4. [使用示例](#使用示例)

---

## 新增操作符概述

### 操作符列表

| 操作符 | 语法示例 | 说明 | 适用数据类型 |
|-------|---------|------|------------|
| `in` | `in ('a','b','c')` | 值在指定集合内 | enum, text, numeric |
| `not in` | `not in ('x','y')` | 值不在指定集合内 | enum, text, numeric |
| `regexp` | `regexp 'ab\|cd'` | 正则匹配（包含） | text |
| `not regexp` | `not regexp 'xx\|ff'` | 正则不匹配（不包含） | text |

### 操作符兼容性矩阵（更新版）

| 数据类型 | 支持的操作符 |
|---------|------------|
| **numeric** | `>`, `>=`, `<`, `<=`, `=`, `!=`, `in`, `not in` |
| **enum** | `=`, `!=`, `in`, `not in` |
| **text** | `=`, `!=`, `in`, `not in`, `regexp`, `not regexp` |
| **boolean** | `=`, `!=` |

---

## 前端实现更新

### 1. 类型定义更新

**文件**: `frontend/types/fraudhunter/rule.ts`

```typescript
// ==================== 基础类型定义 ====================

// 比较操作符（扩展版）
export type ComparisonOperator =
  | '>'           // 大于
  | '>='          // 大于等于
  | '<'           // 小于
  | '<='          // 小于等于
  | '='           // 等于
  | '!='          // 不等于
  | 'in'          // 在集合内
  | 'not in'      // 不在集合内
  | 'regexp'      // 正则匹配
  | 'not regexp'  // 正则不匹配

// 逻辑操作符
export type LogicOperator = 'AND' | 'OR'

// 规则类型
export type RuleType = 'condition' | 'group'

// 指标数据类型
export type IndicatorDataType = 'numeric' | 'enum' | 'boolean' | 'text'

// ==================== 规则结构定义 ====================

// 条件规则（支持多值）
export interface ConditionRule {
  type: 'condition'
  indicator: string           // 指标编码
  operator: ComparisonOperator
  value: string | number | boolean | string[] | number[]  // 支持数组值
}

// 规则组（支持嵌套）
export interface GroupRule {
  type: 'group'
  logic: LogicOperator
  rules: Rule[]
}

// 联合类型
export type Rule = ConditionRule | GroupRule

// ==================== 辅助类型 ====================

// 操作符配置
export interface OperatorConfig {
  value: ComparisonOperator
  label: string
  description: string
  requiresMultiValue: boolean  // 是否需要多值输入
  requiresRegexp: boolean       // 是否需要正则表达式输入
}

// 操作符分组
export const OPERATOR_GROUPS: Record<string, OperatorConfig[]> = {
  comparison: [
    { value: '>', label: '大于 (>)', description: '数值比较', requiresMultiValue: false, requiresRegexp: false },
    { value: '>=', label: '大于等于 (≥)', description: '数值比较', requiresMultiValue: false, requiresRegexp: false },
    { value: '<', label: '小于 (<)', description: '数值比较', requiresMultiValue: false, requiresRegexp: false },
    { value: '<=', label: '小于等于 (≤)', description: '数值比较', requiresMultiValue: false, requiresRegexp: false },
    { value: '=', label: '等于 (=)', description: '精确匹配', requiresMultiValue: false, requiresRegexp: false },
    { value: '!=', label: '不等于 (≠)', description: '不匹配', requiresMultiValue: false, requiresRegexp: false },
  ],
  set: [
    { value: 'in', label: '在集合内 (IN)', description: '值在指定集合中', requiresMultiValue: true, requiresRegexp: false },
    { value: 'not in', label: '不在集合内 (NOT IN)', description: '值不在指定集合中', requiresMultiValue: true, requiresRegexp: false },
  ],
  pattern: [
    { value: 'regexp', label: '正则匹配 (REGEXP)', description: '文本包含指定模式', requiresMultiValue: false, requiresRegexp: true },
    { value: 'not regexp', label: '正则不匹配 (NOT REGEXP)', description: '文本不包含指定模式', requiresMultiValue: false, requiresRegexp: true },
  ],
}
```

### 2. 条件规则编辑器更新

**文件**: `frontend/components/fraudhunter/model/ConditionRuleEditor.tsx`

```tsx
import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { X, Plus } from 'lucide-react'
import { ConditionRule, Indicator, ComparisonOperator, OPERATOR_GROUPS } from '@/types/fraudhunter/rule'

interface ConditionRuleEditorProps {
  rule: ConditionRule
  indicators: Indicator[]
  onChange: (rule: ConditionRule) => void
}

export function ConditionRuleEditor({ rule, indicators, onChange }: ConditionRuleEditorProps) {
  // 获取当前指标信息
  const currentIndicator = indicators.find(ind => ind.indicator_code === rule.indicator)

  // ==================== 操作符兼容性逻辑 ====================

  // 根据数据类型获取允许的操作符
  const getAllowedOperatorsForType = (dataType?: string): ComparisonOperator[] => {
    switch (dataType) {
      case 'numeric':
        return ['>', '>=', '<', '<=', '=', '!=', 'in', 'not in']
      case 'enum':
        return ['=', '!=', 'in', 'not in']
      case 'text':
        return ['=', '!=', 'in', 'not in', 'regexp', 'not regexp']
      case 'boolean':
        return ['=', '!=']
      default:
        return ['>', '>=', '<', '<=', '=', '!=']
    }
  }

  const allowedOperators = getAllowedOperatorsForType(currentIndicator?.data_type)

  // 判断当前操作符是否需要多值输入
  const isMultiValueOperator = (op: ComparisonOperator): boolean => {
    return op === 'in' || op === 'not in'
  }

  // 判断当前操作符是否需要正则表达式输入
  const isRegexpOperator = (op: ComparisonOperator): boolean => {
    return op === 'regexp' || op === 'not regexp'
  }

  const requiresMultiValue = isMultiValueOperator(rule.operator)
  const requiresRegexp = isRegexpOperator(rule.operator)

  // ==================== 指标变更处理 ====================

  const handleIndicatorChange = (indicatorCode: string) => {
    const newIndicator = indicators.find(ind => ind.indicator_code === indicatorCode)
    const newAllowedOps = getAllowedOperatorsForType(newIndicator?.data_type)

    onChange({
      ...rule,
      indicator: indicatorCode,
      operator: newAllowedOps[0] || '>',
      value: getDefaultValue(newIndicator?.data_type, newAllowedOps[0])
    })
  }

  const getDefaultValue = (dataType?: string, operator?: ComparisonOperator) => {
    // 如果是多值操作符，返回空数组
    if (operator && isMultiValueOperator(operator)) {
      return []
    }

    switch (dataType) {
      case 'boolean': return false
      case 'numeric': return 0
      case 'enum': return ''
      default: return ''
    }
  }

  // ==================== 操作符变更处理 ====================

  const handleOperatorChange = (newOperator: ComparisonOperator) => {
    const oldRequiresMultiValue = isMultiValueOperator(rule.operator)
    const newRequiresMultiValue = isMultiValueOperator(newOperator)

    let newValue = rule.value

    // 从单值切换到多值
    if (!oldRequiresMultiValue && newRequiresMultiValue) {
      newValue = rule.value !== '' ? [rule.value] : []
    }
    // 从多值切换到单值
    else if (oldRequiresMultiValue && !newRequiresMultiValue) {
      newValue = Array.isArray(rule.value) && rule.value.length > 0
        ? rule.value[0]
        : getDefaultValue(currentIndicator?.data_type)
    }

    onChange({
      ...rule,
      operator: newOperator,
      value: newValue
    })
  }

  // ==================== 多值输入处理 ====================

  // 添加值到数组
  const addValueToArray = (newVal: string | number) => {
    const currentArray = Array.isArray(rule.value) ? rule.value : []
    onChange({
      ...rule,
      value: [...currentArray, newVal]
    })
  }

  // 从数组中删除值
  const removeValueFromArray = (index: number) => {
    const currentArray = Array.isArray(rule.value) ? rule.value : []
    const newArray = currentArray.filter((_, i) => i !== index)
    onChange({
      ...rule,
      value: newArray
    })
  }

  // 更新数组中的值
  const updateValueInArray = (index: number, newVal: string | number) => {
    const currentArray = Array.isArray(rule.value) ? rule.value : []
    const newArray = [...currentArray]
    newArray[index] = newVal
    onChange({
      ...rule,
      value: newArray
    })
  }

  // ==================== 值输入控件渲染 ====================

  const renderValueInput = () => {
    if (!currentIndicator) return null

    // 多值输入（in / not in）
    if (requiresMultiValue) {
      return <MultiValueInput
        dataType={currentIndicator.data_type}
        values={Array.isArray(rule.value) ? rule.value : []}
        enumValues={currentIndicator.enum_values}
        onAdd={addValueToArray}
        onRemove={removeValueFromArray}
        onUpdate={updateValueInArray}
      />
    }

    // 正则表达式输入（regexp / not regexp）
    if (requiresRegexp) {
      return <RegexpInput
        value={String(rule.value)}
        onChange={(v) => onChange({ ...rule, value: v })}
      />
    }

    // 单值输入
    return renderSingleValueInput()
  }

  const renderSingleValueInput = () => {
    if (!currentIndicator) return null

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
      <div className="space-y-3">
        <div className="flex items-center space-x-2 flex-wrap gap-2">
          {/* 指标选择 */}
          <Select value={rule.indicator} onValueChange={handleIndicatorChange}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="选择指标" />
            </SelectTrigger>
            <SelectContent>
              {indicators.map((ind) => (
                <SelectItem key={ind.indicator_code} value={ind.indicator_code}>
                  <div className="flex items-center justify-between">
                    <span>{ind.indicator_name}</span>
                    <span className="text-xs text-muted-foreground ml-2">
                      ({ind.data_type})
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* 操作符选择 */}
          <Select
            value={rule.operator}
            onValueChange={handleOperatorChange}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {/* 比较操作符组 */}
              {allowedOperators.some(op => ['>', '>=', '<', '<=', '=', '!='].includes(op)) && (
                <>
                  <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                    比较操作
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

              {/* 集合操作符组 */}
              {allowedOperators.some(op => ['in', 'not in'].includes(op)) && (
                <>
                  <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
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

              {/* 正则操作符组 */}
              {allowedOperators.some(op => ['regexp', 'not regexp'].includes(op)) && (
                <>
                  <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                    正则操作
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

        {/* 值输入区域 */}
        <div>
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
  enumValues?: string[]
  onAdd: (value: string | number) => void
  onRemove: (index: number) => void
  onUpdate: (index: number, value: string | number) => void
}

function MultiValueInput({
  dataType,
  values,
  enumValues,
  onAdd,
  onRemove,
  onUpdate
}: MultiValueInputProps) {
  const [inputValue, setInputValue] = useState<string>('')

  const handleAdd = () => {
    if (!inputValue.trim()) return

    const valueToAdd = dataType === 'numeric' ? Number(inputValue) : inputValue
    onAdd(valueToAdd)
    setInputValue('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAdd()
    }
  }

  return (
    <div className="space-y-2">
      {/* 已添加的值列表 */}
      {values.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {values.map((val, index) => (
            <Badge key={index} variant="secondary" className="pl-2 pr-1">
              <span>{String(val)}</span>
              <button
                onClick={() => onRemove(index)}
                className="ml-1 hover:bg-muted rounded-sm p-0.5"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* 输入框 */}
      <div className="flex items-center space-x-2">
        {dataType === 'enum' && enumValues ? (
          <Select value={inputValue} onValueChange={setInputValue}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="选择值" />
            </SelectTrigger>
            <SelectContent>
              {enumValues.map((val) => (
                <SelectItem key={val} value={val}>{val}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <Input
            type={dataType === 'numeric' ? 'number' : 'text'}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`输入${dataType === 'numeric' ? '数值' : '文本'}后按回车添加`}
            className="flex-1"
          />
        )}
        <Button
          type="button"
          size="sm"
          onClick={handleAdd}
          disabled={!inputValue.trim()}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      <div className="text-xs text-muted-foreground">
        已添加 {values.length} 个值
      </div>
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

  const handleChange = (newValue: string) => {
    onChange(newValue)

    // 验证正则表达式
    try {
      new RegExp(newValue)
      setIsValid(true)
      setError('')
    } catch (e) {
      setIsValid(false)
      setError((e as Error).message)
    }
  }

  return (
    <div className="space-y-2">
      <Textarea
        value={value}
        onChange={(e) => handleChange(e.target.value)}
        placeholder="输入正则表达式，例如：ab|cd 或 ^yy|^ii"
        rows={3}
        className={`font-mono ${!isValid ? 'border-destructive' : ''}`}
      />

      {/* 验证反馈 */}
      {!isValid && error && (
        <div className="text-xs text-destructive">
          正则表达式错误: {error}
        </div>
      )}

      {/* 常用模式提示 */}
      <div className="text-xs text-muted-foreground space-y-1">
        <div className="font-semibold">常用模式:</div>
        <div>• <code>ab|cd</code> - 包含 ab 或 cd</div>
        <div>• <code>^yy|^ii</code> - 以 yy 或 ii 开头</div>
        <div>• <code>xx$|ff$</code> - 以 xx 或 ff 结尾</div>
        <div>• <code>^\d{11}$</code> - 精确匹配11位数字</div>
      </div>
    </div>
  )
}
```

---

## 后端实现更新

### 1. Pydantic模型更新

**文件**: `backend/schemas/fraudhunter/rule.py`

```python
"""
FraudHunter规则引擎数据模型（扩展版）
"""

from typing import Literal, Union, List, Optional
from pydantic import BaseModel, Field, field_validator

# ==================== 基础类型定义 ====================

# 比较操作符（扩展版）
ComparisonOperator = Literal[
    ">", ">=", "<", "<=", "=", "!=",      # 基础比较
    "in", "not in",                       # 集合操作
    "regexp", "not regexp"                # 正则匹配
]

# 逻辑操作符
LogicOperator = Literal["AND", "OR"]

# 指标数据类型
IndicatorDataType = Literal["numeric", "enum", "boolean", "text"]

# ==================== 规则结构定义 ====================

class ConditionRule(BaseModel):
    """条件规则：支持单值和多值操作符"""

    type: Literal["condition"]
    indicator: str = Field(..., description="指标编码")
    operator: ComparisonOperator = Field(..., description="比较操作符")
    value: Union[str, int, float, bool, List[str], List[int], List[float]] = Field(
        ...,
        description="比较值，in/not in操作符使用数组"
    )

    @field_validator('value')
    @classmethod
    def validate_value_type(cls, v, info):
        """验证值类型与操作符匹配"""
        operator = info.data.get('operator')

        # in/not in 必须是数组
        if operator in ['in', 'not in']:
            if not isinstance(v, list):
                raise ValueError(f"操作符 {operator} 需要数组类型的值")
            if len(v) == 0:
                raise ValueError(f"操作符 {operator} 的值数组不能为空")

        # 其他操作符不应该是数组
        elif isinstance(v, list):
            raise ValueError(f"操作符 {operator} 不支持数组类型的值")

        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "type": "condition",
                    "indicator": "i_login_cnt_7d",
                    "operator": ">",
                    "value": 10
                },
                {
                    "type": "condition",
                    "indicator": "i_user_status",
                    "operator": "in",
                    "value": ["active", "premium", "vip"]
                },
                {
                    "type": "condition",
                    "indicator": "i_user_name",
                    "operator": "regexp",
                    "value": "^admin|^test"
                }
            ]
        }


class GroupRule(BaseModel):
    """规则组：多个规则的逻辑组合"""

    type: Literal["group"]
    logic: LogicOperator = Field(..., description="逻辑操作符")
    rules: List["Rule"] = Field(..., description="子规则列表")

    @field_validator('rules')
    @classmethod
    def validate_rules_not_empty(cls, v):
        if not v:
            raise ValueError("规则组的rules字段不能为空")
        return v


# 联合类型
Rule = Union[ConditionRule, GroupRule]

# 更新前向引用
GroupRule.model_rebuild()
```

### 2. RuleEngine验证逻辑更新

**文件**: `backend/services/fraudhunter/model_service/rule_engine.py`

```python
"""
RuleEngine 扩展：支持高级操作符
"""

import re
from typing import Dict, List, Set, Any, Optional
from backend.schemas.fraudhunter.rule import (
    RuleConfig, Rule, ConditionRule, GroupRule,
    ComparisonOperator, RuleValidationResult
)
from backend.models.fraudhunter.indicator import FraudHunterIndicatorDefinition
from sqlalchemy.orm import Session
from backend.utils.logger import logger


class RuleEngine:
    """规则引擎 - 支持高级操作符"""

    # 操作符兼容性矩阵（扩展版）
    ALLOWED_OPERATORS = {
        'numeric': ['>', '>=', '<', '<=', '=', '!=', 'in', 'not in'],
        'enum': ['=', '!=', 'in', 'not in'],
        'text': ['=', '!=', 'in', 'not in', 'regexp', 'not regexp'],
        'boolean': ['=', '!=']
    }

    def __init__(self, db: Session):
        self.db = db

    # ==================== 规则验证（扩展版） ====================

    def _validate_operator_compatibility(
        self,
        config: RuleConfig,
        result: RuleValidationResult
    ):
        """验证操作符与指标数据类型的兼容性（扩展版）"""

        # 获取所有指标的数据类型
        indicator_types = {}
        indicators = self.db.query(FraudHunterIndicatorDefinition).filter(
            FraudHunterIndicatorDefinition.indicator_code.in_(
                result.extracted_indicators
            )
        ).all()

        for ind in indicators:
            indicator_types[ind.indicator_code] = ind.data_type

        def validate_condition(condition: ConditionRule, path: str):
            data_type = indicator_types.get(condition.indicator)
            if not data_type:
                return  # 指标不存在的错误已在前面捕获

            allowed = self.ALLOWED_OPERATORS.get(data_type, [])
            if condition.operator not in allowed:
                result.errors.append(
                    f"{path}: 指标 {condition.indicator} (类型:{data_type}) "
                    f"不支持操作符 {condition.operator}，"
                    f"允许的操作符: {', '.join(allowed)}"
                )

            # 验证 in/not in 操作符的值必须是数组
            if condition.operator in ['in', 'not in']:
                if not isinstance(condition.value, list):
                    result.errors.append(
                        f"{path}: 操作符 {condition.operator} 需要数组类型的值"
                    )
                elif len(condition.value) == 0:
                    result.errors.append(
                        f"{path}: 操作符 {condition.operator} 的值数组不能为空"
                    )

            # 验证 regexp/not regexp 操作符的值必须是有效正则
            if condition.operator in ['regexp', 'not regexp']:
                if not isinstance(condition.value, str):
                    result.errors.append(
                        f"{path}: 操作符 {condition.operator} 需要字符串类型的值"
                    )
                else:
                    # 验证正则表达式语法
                    try:
                        re.compile(condition.value)
                    except re.error as e:
                        result.errors.append(
                            f"{path}: 正则表达式语法错误: {str(e)}"
                        )

        def traverse_rule(rule: Rule, path: str):
            if isinstance(rule, ConditionRule):
                validate_condition(rule, path)
            elif isinstance(rule, GroupRule):
                for i, sub_rule in enumerate(rule.rules):
                    traverse_rule(sub_rule, f"{path}.rules[{i}]")

        for i, rule in enumerate(config.rules):
            traverse_rule(rule, f"root.rules[{i}]")

    # ==================== 规则评估（扩展版） ====================

    def evaluate_rule(
        self,
        rule_config: RuleConfig,
        indicator_values: Dict[str, Any]
    ) -> bool:
        """执行规则评估（支持高级操作符）"""

        def evaluate_condition(condition: ConditionRule) -> bool:
            """评估单个条件（扩展版）"""
            actual_value = indicator_values.get(condition.indicator)
            if actual_value is None:
                logger.warning(
                    f"指标 {condition.indicator} 值不存在，默认为False"
                )
                return False

            expected_value = condition.value
            operator = condition.operator

            try:
                # ===== 基础比较操作符 =====
                if operator in ['>', '>=', '<', '<=', '=', '!=']:
                    return self._evaluate_basic_comparison(
                        actual_value, operator, expected_value
                    )

                # ===== 集合操作符 =====
                elif operator in ['in', 'not in']:
                    return self._evaluate_set_operation(
                        actual_value, operator, expected_value
                    )

                # ===== 正则操作符 =====
                elif operator in ['regexp', 'not regexp']:
                    return self._evaluate_regexp_operation(
                        actual_value, operator, expected_value
                    )

                else:
                    logger.error(f"不支持的操作符: {operator}")
                    return False

            except Exception as e:
                logger.error(
                    f"条件评估失败: {condition}, 错误: {e}",
                    exc_info=True
                )
                return False

        def evaluate_group(group: GroupRule) -> bool:
            """评估规则组"""
            if not group.rules:
                return False

            results = [evaluate_rule_item(rule) for rule in group.rules]

            if group.logic == 'AND':
                return all(results)
            elif group.logic == 'OR':
                return any(results)
            else:
                logger.error(f"不支持的逻辑操作符: {group.logic}")
                return False

        def evaluate_rule_item(rule: Rule) -> bool:
            """评估单个规则项"""
            if isinstance(rule, ConditionRule):
                return evaluate_condition(rule)
            elif isinstance(rule, GroupRule):
                return evaluate_group(rule)
            return False

        # 评估根规则组
        root_group = GroupRule(
            type='group',
            logic=rule_config.logic,
            rules=rule_config.rules
        )

        return evaluate_group(root_group)

    def _evaluate_basic_comparison(
        self,
        actual: Any,
        operator: str,
        expected: Any
    ) -> bool:
        """基础比较操作"""
        # 类型转换
        if isinstance(expected, (int, float)):
            actual = float(actual)
        elif isinstance(expected, bool):
            actual = bool(actual)
        else:
            actual = str(actual)
            expected = str(expected)

        # 执行比较
        if operator == '>':
            return actual > expected
        elif operator == '>=':
            return actual >= expected
        elif operator == '<':
            return actual < expected
        elif operator == '<=':
            return actual <= expected
        elif operator == '=':
            return actual == expected
        elif operator == '!=':
            return actual != expected

        return False

    def _evaluate_set_operation(
        self,
        actual: Any,
        operator: str,
        expected: List[Any]
    ) -> bool:
        """集合操作（in / not in）"""
        if not isinstance(expected, list):
            logger.error(f"集合操作符 {operator} 需要数组类型的值")
            return False

        # 类型转换：将 actual 和 expected 中的值转换为相同类型
        if expected and isinstance(expected[0], (int, float)):
            try:
                actual = float(actual)
                expected = [float(v) for v in expected]
            except (ValueError, TypeError):
                pass
        else:
            actual = str(actual)
            expected = [str(v) for v in expected]

        # 执行判断
        if operator == 'in':
            return actual in expected
        elif operator == 'not in':
            return actual not in expected

        return False

    def _evaluate_regexp_operation(
        self,
        actual: Any,
        operator: str,
        pattern: str
    ) -> bool:
        """正则操作（regexp / not regexp）"""
        if not isinstance(pattern, str):
            logger.error(f"正则操作符 {operator} 需要字符串类型的值")
            return False

        actual_str = str(actual)

        try:
            compiled_pattern = re.compile(pattern)
            match = compiled_pattern.search(actual_str)

            if operator == 'regexp':
                return match is not None
            elif operator == 'not regexp':
                return match is None

        except re.error as e:
            logger.error(f"正则表达式编译失败: {pattern}, 错误: {e}")
            return False

        return False

    # ==================== SQL生成（扩展版） ====================

    def generate_sql_expression(self, rule_config: RuleConfig) -> str:
        """将规则配置转换为SQL WHERE子句（支持高级操作符）"""

        def condition_to_sql(condition: ConditionRule) -> str:
            """将条件转换为SQL（扩展版）"""
            indicator = condition.indicator
            operator = condition.operator
            value = condition.value

            # ===== 基础比较操作符 =====
            if operator in ['>', '>=', '<', '<=', '=', '!=']:
                return self._basic_comparison_to_sql(indicator, operator, value)

            # ===== 集合操作符 =====
            elif operator in ['in', 'not in']:
                return self._set_operation_to_sql(indicator, operator, value)

            # ===== 正则操作符 =====
            elif operator in ['regexp', 'not regexp']:
                return self._regexp_operation_to_sql(indicator, operator, value)

            else:
                logger.error(f"不支持的操作符: {operator}")
                return "1=1"

        def group_to_sql(group: GroupRule) -> str:
            """将规则组转换为SQL"""
            if not group.rules:
                return "1=1"

            sub_expressions = []
            for rule in group.rules:
                if isinstance(rule, ConditionRule):
                    sub_expressions.append(condition_to_sql(rule))
                elif isinstance(rule, GroupRule):
                    sub_expressions.append(f"({group_to_sql(rule)})")

            logic_op = ' AND ' if group.logic == 'AND' else ' OR '
            return logic_op.join(sub_expressions)

        # 构建根表达式
        root_group = GroupRule(
            type='group',
            logic=rule_config.logic,
            rules=rule_config.rules
        )

        return f"({group_to_sql(root_group)})"

    def _basic_comparison_to_sql(
        self,
        indicator: str,
        operator: str,
        value: Any
    ) -> str:
        """基础比较操作转SQL"""
        if isinstance(value, str):
            value_sql = f"'{value.replace("'", "''")}'"
        elif isinstance(value, bool):
            value_sql = 'TRUE' if value else 'FALSE'
        else:
            value_sql = str(value)

        return f"{indicator} {operator} {value_sql}"

    def _set_operation_to_sql(
        self,
        indicator: str,
        operator: str,
        values: List[Any]
    ) -> str:
        """集合操作转SQL"""
        if not isinstance(values, list) or len(values) == 0:
            return "1=0"  # 空集合返回永假

        # 格式化值列表
        formatted_values = []
        for v in values:
            if isinstance(v, str):
                formatted_values.append(f"'{v.replace("'", "''")}'")
            elif isinstance(v, bool):
                formatted_values.append('TRUE' if v else 'FALSE')
            else:
                formatted_values.append(str(v))

        values_str = ', '.join(formatted_values)

        if operator == 'in':
            return f"{indicator} IN ({values_str})"
        elif operator == 'not in':
            return f"{indicator} NOT IN ({values_str})"

        return "1=1"

    def _regexp_operation_to_sql(
        self,
        indicator: str,
        operator: str,
        pattern: str
    ) -> str:
        """正则操作转SQL（Spark SQL / Hive语法）"""
        if not isinstance(pattern, str):
            return "1=1"

        # 转义单引号
        pattern_escaped = pattern.replace("'", "''")

        if operator == 'regexp':
            return f"{indicator} RLIKE '{pattern_escaped}'"
        elif operator == 'not regexp':
            return f"NOT ({indicator} RLIKE '{pattern_escaped}')"

        return "1=1"
```

---

## 使用示例

### 1. 集合操作示例

**场景**: 检测用户状态是否在高风险状态列表中

```json
{
  "logic": "AND",
  "rules": [
    {
      "type": "condition",
      "indicator": "i_user_status",
      "operator": "in",
      "value": ["suspended", "banned", "frozen"]
    },
    {
      "type": "condition",
      "indicator": "i_login_cnt_7d",
      "operator": ">",
      "value": 5
    }
  ],
  "output": {
    "risk_level": "high",
    "risk_score": 80,
    "action": "block"
  }
}
```

**生成的SQL**:
```sql
(i_user_status IN ('suspended', 'banned', 'frozen') AND i_login_cnt_7d > 5)
```

### 2. 正则匹配示例

**场景**: 检测用户名是否以特定前缀开头

```json
{
  "logic": "OR",
  "rules": [
    {
      "type": "condition",
      "indicator": "i_user_name",
      "operator": "regexp",
      "value": "^admin|^test|^demo"
    },
    {
      "type": "condition",
      "indicator": "i_email",
      "operator": "regexp",
      "value": "@temp\\.|@fake\\."
    }
  ],
  "output": {
    "risk_level": "medium",
    "risk_score": 60,
    "action": "review"
  }
}
```

**生成的SQL**:
```sql
(i_user_name RLIKE '^admin|^test|^demo' OR i_email RLIKE '@temp\\.|@fake\\.')
```

### 3. 排除集合示例

**场景**: 排除白名单用户

```json
{
  "logic": "AND",
  "rules": [
    {
      "type": "condition",
      "indicator": "i_user_id",
      "operator": "not in",
      "value": [1001, 1002, 1003, 1004]
    },
    {
      "type": "condition",
      "indicator": "i_trans_amt_1d",
      "operator": ">",
      "value": 50000
    }
  ],
  "output": {
    "risk_level": "high",
    "risk_score": 85,
    "action": "alert"
  }
}
```

**生成的SQL**:
```sql
(i_user_id NOT IN (1001, 1002, 1003, 1004) AND i_trans_amt_1d > 50000)
```

### 4. 复杂组合示例

**场景**: 检测异常登录行为

```json
{
  "logic": "AND",
  "rules": [
    {
      "type": "condition",
      "indicator": "i_login_ip",
      "operator": "not regexp",
      "value": "^192\\.168\\.|^10\\."
    },
    {
      "type": "group",
      "logic": "OR",
      "rules": [
        {
          "type": "condition",
          "indicator": "i_login_device_type",
          "operator": "in",
          "value": ["unknown", "simulator", "rooted"]
        },
        {
          "type": "condition",
          "indicator": "i_login_time",
          "operator": "regexp",
          "value": "^(0[0-4]|23):"
        }
      ]
    }
  ],
  "output": {
    "risk_level": "critical",
    "risk_score": 95,
    "action": "block"
  }
}
```

**生成的SQL**:
```sql
(
  NOT (i_login_ip RLIKE '^192\\.168\\.|^10\\.')
  AND
  (
    i_login_device_type IN ('unknown', 'simulator', 'rooted')
    OR
    i_login_time RLIKE '^(0[0-4]|23):'
  )
)
```

---

## 常见正则表达式模式

### 电话号码
```regexp
^1[3-9]\d{9}$         # 中国手机号
^\d{11}$              # 11位数字
```

### 邮箱
```regexp
@qq\.com$             # QQ邮箱
@(163|126|yeah)\.com$ # 网易邮箱
```

### 用户名
```regexp
^admin|^test|^demo    # 以admin、test或demo开头
_test$|_tmp$          # 以_test或_tmp结尾
```

### IP地址
```regexp
^192\.168\.|^10\.     # 内网IP
^(127\.|::1)          # 本地回环
```

### 时间
```regexp
^(0[0-5]|23):         # 凌晨0-5点或23点
^(09|10|11|12|13|14): # 工作时间
```

---

**文档结束**
