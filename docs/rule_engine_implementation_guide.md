# FraudHunter 可视化规则引擎完整实现指南

## 文档信息
- **版本**: v2.0.0（支持高级操作符）
- **创建日期**: 2025-12-05
- **作者**: Claude Code
- **说明**: 本文档整合了基础规则引擎和高级操作符（in/not in/regexp/not regexp）的完整实现方案

## 目录
1. [整体架构设计](#1-整体架构设计)
2. [操作符支持](#2-操作符支持)
3. [前端实现方案](#3-前端实现方案)
4. [后端实现方案](#4-后端实现方案)
5. [使用示例](#5-使用示例)
6. [开发清单](#6-开发清单)

---

## 1. 整体架构设计

### 数据流向
```
用户交互 → RuleBuilder组件
         ↓
      规则JSON生成
         ↓
      后端验证API
         ↓
    规则持久化(MySQL)
         ↓
    规则执行引擎(RuleEngine)
         ↓
  Spark SQL执行 / Python运行时评估
```

### 技术栈
| 层级 | 技术选型 | 用途 |
|------|---------|------|
| 前端UI | React 18 + TypeScript | 组件化开发 |
| 前端组件 | Radix UI + Tailwind CSS | UI组件库和样式 |
| 后端框架 | FastAPI 0.116 | REST API |
| 数据验证 | Pydantic 2.0 | 数据模型和验证 |
| 规则引擎 | 自研RuleEngine | 规则解析和执行 |

---

## 2. 操作符支持

### 完整操作符列表

| 操作符类型 | 操作符 | 语法示例 | 说明 | 适用数据类型 |
|-----------|-------|---------|------|------------|
| **基础比较** | `>`, `>=`, `<`, `<=` | `> 10` | 数值比较 | numeric |
| | `=`, `!=` | `= 'value'` | 相等/不等 | all |
| **集合操作** | `in` | `in ('a','b','c')` | 值在集合内 | numeric, enum, text |
| | `not in` | `not in ('x','y')` | 值不在集合内 | numeric, enum, text |
| **正则匹配** | `regexp` | `regexp 'ab\|cd'` | 包含模式 | text |
| | `not regexp` | `not regexp 'xx\|ff'` | 不包含模式 | text |

### 操作符兼容性矩阵

| 数据类型 | 支持的操作符 |
|---------|------------|
| **numeric** | `>`, `>=`, `<`, `<=`, `=`, `!=`, `in`, `not in` |
| **enum** | `=`, `!=`, `in`, `not in` |
| **text** | `=`, `!=`, `in`, `not in`, `regexp`, `not regexp` |
| **boolean** | `=`, `!=` |

---

## 3. 前端实现方案

### 核心文件列表

```
frontend/
├── types/fraudhunter/rule.ts           # TypeScript类型定义
├── components/fraudhunter/model/
│   ├── RuleBuilder.tsx                  # 主规则构建器
│   ├── ConditionRuleEditor.tsx          # 条件编辑器（支持高级操作符）
│   ├── RuleOutputEditor.tsx             # 输出配置编辑器
│   └── RulePreview.tsx                  # 规则预览
└── lib/services/fraudhunter/
    └── modelService.ts                  # API服务封装
```

### 关键实现要点

#### 1. 类型定义（支持多值和正则）

**文件**: `frontend/types/fraudhunter/rule.ts`

```typescript
// 完整操作符类型
export type ComparisonOperator =
  | '>' | '>=' | '<' | '<=' | '=' | '!='      // 基础比较
  | 'in' | 'not in'                            // 集合操作
  | 'regexp' | 'not regexp'                    // 正则匹配

// 条件规则（value支持数组）
export interface ConditionRule {
  type: 'condition'
  indicator: string
  operator: ComparisonOperator
  value: string | number | boolean | string[] | number[]  // 关键：支持数组
}

// 操作符配置（用于UI分组显示）
export const OPERATOR_GROUPS = {
  comparison: [
    { value: '>', label: '大于 (>)', requiresMultiValue: false, requiresRegexp: false },
    // ... 其他基础操作符
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
```

#### 2. 条件编辑器核心逻辑

**文件**: `frontend/components/fraudhunter/model/ConditionRuleEditor.tsx`

**关键功能**：
- ✅ 根据指标数据类型动态限制可用操作符
- ✅ 操作符切换时自动转换值类型（单值 ↔ 多值）
- ✅ 多值输入组件（MultiValueInput）
- ✅ 正则表达式输入组件（RegexpInput）带实时验证

```typescript
// 操作符兼容性判断
const getAllowedOperatorsForType = (dataType?: string): ComparisonOperator[] => {
  switch (dataType) {
    case 'numeric': return ['>', '>=', '<', '<=', '=', '!=', 'in', 'not in']
    case 'enum': return ['=', '!=', 'in', 'not in']
    case 'text': return ['=', '!=', 'in', 'not in', 'regexp', 'not regexp']
    case 'boolean': return ['=', '!=']
    default: return ['>', '>=', '<', '<=', '=', '!=']
  }
}

// 操作符切换时的值类型转换
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
  
  onChange({ ...rule, operator: newOperator, value: newValue })
}
```

**MultiValueInput 组件**（用于 in/not in）:
```typescript
function MultiValueInput({ dataType, values, onAdd, onRemove }) {
  return (
    <div>
      {/* 已添加的值显示为Badge，可点击删除 */}
      {values.map((val, idx) => (
        <Badge>
          {val}
          <X onClick={() => onRemove(idx)} />
        </Badge>
      ))}
      
      {/* 输入框（支持回车添加） */}
      <Input 
        onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
      />
    </div>
  )
}
```

**RegexpInput 组件**（用于 regexp/not regexp）:
```typescript
function RegexpInput({ value, onChange }) {
  const [isValid, setIsValid] = useState(true)
  
  const handleChange = (newValue: string) => {
    onChange(newValue)
    
    // 实时验证正则表达式
    try {
      new RegExp(newValue)
      setIsValid(true)
    } catch (e) {
      setIsValid(false)
      setError(e.message)
    }
  }
  
  return (
    <div>
      <Textarea className={!isValid ? 'border-destructive' : ''} />
      {!isValid && <div className="text-destructive">{error}</div>}
      
      {/* 常用模式提示 */}
      <div>
        • <code>ab|cd</code> - 包含 ab 或 cd
        • <code>^yy|^ii</code> - 以 yy 或 ii 开头
      </div>
    </div>
  )
}
```

---

## 4. 后端实现方案

### 核心文件列表

```
backend/
├── schemas/fraudhunter/rule.py          # Pydantic数据模型
├── services/fraudhunter/model_service/
│   └── rule_engine.py                    # 规则引擎核心
└── api/fraudhunter/model_routes.py      # API路由
```

### 关键实现要点

#### 1. Pydantic模型（支持多值验证）

**文件**: `backend/schemas/fraudhunter/rule.py`

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Union, List

# 完整操作符类型
ComparisonOperator = Literal[
    ">", ">=", "<", "<=", "=", "!=",      # 基础
    "in", "not in",                       # 集合
    "regexp", "not regexp"                # 正则
]

class ConditionRule(BaseModel):
    type: Literal["condition"]
    indicator: str
    operator: ComparisonOperator
    value: Union[str, int, float, bool, List[str], List[int], List[float]]  # 支持数组
    
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
```

#### 2. 规则引擎核心逻辑

**文件**: `backend/services/fraudhunter/model_service/rule_engine.py`

```python
import re
from typing import Dict, List, Any

class RuleEngine:
    """规则引擎 - 支持完整操作符"""
    
    # 操作符兼容性矩阵
    ALLOWED_OPERATORS = {
        'numeric': ['>', '>=', '<', '<=', '=', '!=', 'in', 'not in'],
        'enum': ['=', '!=', 'in', 'not in'],
        'text': ['=', '!=', 'in', 'not in', 'regexp', 'not regexp'],
        'boolean': ['=', '!=']
    }
    
    def evaluate_rule(self, rule_config: RuleConfig, indicator_values: Dict[str, Any]) -> bool:
        """执行规则评估（支持所有操作符）"""
        
        def evaluate_condition(condition: ConditionRule) -> bool:
            actual_value = indicator_values.get(condition.indicator)
            operator = condition.operator
            expected_value = condition.value
            
            # 基础比较
            if operator in ['>', '>=', '<', '<=', '=', '!=']:
                return self._evaluate_basic_comparison(actual_value, operator, expected_value)
            
            # 集合操作
            elif operator in ['in', 'not in']:
                return self._evaluate_set_operation(actual_value, operator, expected_value)
            
            # 正则匹配
            elif operator in ['regexp', 'not regexp']:
                return self._evaluate_regexp_operation(actual_value, operator, expected_value)
        
        # ... 递归评估逻辑
    
    def _evaluate_set_operation(self, actual: Any, operator: str, expected: List[Any]) -> bool:
        """集合操作（in / not in）"""
        # 类型转换
        if expected and isinstance(expected[0], (int, float)):
            actual = float(actual)
            expected = [float(v) for v in expected]
        else:
            actual = str(actual)
            expected = [str(v) for v in expected]
        
        # 判断
        if operator == 'in':
            return actual in expected
        elif operator == 'not in':
            return actual not in expected
    
    def _evaluate_regexp_operation(self, actual: Any, operator: str, pattern: str) -> bool:
        """正则操作（regexp / not regexp）"""
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
    
    def generate_sql_expression(self, rule_config: RuleConfig) -> str:
        """生成SQL WHERE子句（支持所有操作符）"""
        
        def condition_to_sql(condition: ConditionRule) -> str:
            indicator = condition.indicator
            operator = condition.operator
            value = condition.value
            
            # 基础比较
            if operator in ['>', '>=', '<', '<=', '=', '!=']:
                return f"{indicator} {operator} {format_value(value)}"
            
            # 集合操作
            elif operator in ['in', 'not in']:
                values_str = ', '.join([format_value(v) for v in value])
                op_sql = 'IN' if operator == 'in' else 'NOT IN'
                return f"{indicator} {op_sql} ({values_str})"
            
            # 正则匹配（Spark SQL语法）
            elif operator in ['regexp', 'not regexp']:
                pattern_escaped = value.replace("'", "''")
                if operator == 'regexp':
                    return f"{indicator} RLIKE '{pattern_escaped}'"
                else:
                    return f"NOT ({indicator} RLIKE '{pattern_escaped}')"
        
        # ... 递归生成SQL
```

#### 3. 规则验证逻辑

```python
def _validate_operator_compatibility(self, config, result):
    """验证操作符与数据类型的兼容性"""
    
    def validate_condition(condition: ConditionRule, path: str):
        data_type = indicator_types.get(condition.indicator)
        allowed = self.ALLOWED_OPERATORS.get(data_type, [])
        
        if condition.operator not in allowed:
            result.errors.append(
                f"{path}: 指标 {condition.indicator} (类型:{data_type}) "
                f"不支持操作符 {condition.operator}"
            )
        
        # 验证 in/not in 的值必须是数组
        if condition.operator in ['in', 'not in']:
            if not isinstance(condition.value, list):
                result.errors.append(f"{path}: 操作符 {condition.operator} 需要数组类型的值")
        
        # 验证正则表达式语法
        if condition.operator in ['regexp', 'not regexp']:
            try:
                re.compile(condition.value)
            except re.error as e:
                result.errors.append(f"{path}: 正则表达式语法错误: {str(e)}")
```

---

## 5. 使用示例

### 示例1: 集合操作 - 检测高风险用户状态

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

### 示例2: 正则匹配 - 检测测试账号

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

### 示例3: 复杂组合 - 异常登录检测

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

### 常用正则表达式模式参考

```regexp
# 电话号码
^1[3-9]\d{9}$         # 中国手机号
^\d{11}$              # 11位数字

# 邮箱
@qq\.com$             # QQ邮箱
@(163|126|yeah)\.com$ # 网易邮箱

# 用户名
^admin|^test|^demo    # 以admin、test或demo开头
_test$|_tmp$          # 以_test或_tmp结尾

# IP地址
^192\.168\.|^10\.     # 内网IP
^(127\.|::1)          # 本地回环

# 时间
^(0[0-5]|23):         # 凌晨0-5点或23点
^(09|10|11|12|13|14): # 工作时间
```

---

## 6. 开发清单

### 前端开发任务

- [ ] **类型定义**
  - [ ] 创建 `types/fraudhunter/rule.ts`（包含高级操作符）
  - [ ] 定义 `OPERATOR_GROUPS` 常量

- [ ] **核心组件**
  - [ ] `RuleBuilder.tsx` - 主规则构建器
  - [ ] `ConditionRuleEditor.tsx` - 条件编辑器（包含 MultiValueInput 和 RegexpInput）
  - [ ] `RuleOutputEditor.tsx` - 输出配置编辑器
  - [ ] `RulePreview.tsx` - 规则预览（支持数组值显示）

- [ ] **API服务**
  - [ ] `modelService.ts` - 封装 validateRule、previewSQL、evaluateRule

### 后端开发任务

- [ ] **数据模型**
  - [ ] `schemas/fraudhunter/rule.py`（包含 field_validator 验证逻辑）

- [ ] **核心服务**
  - [ ] `rule_engine.py` - 实现三个评估方法：
    - [ ] `_evaluate_basic_comparison`
    - [ ] `_evaluate_set_operation`
    - [ ] `_evaluate_regexp_operation`
  - [ ] SQL生成支持 IN/NOT IN/RLIKE

- [ ] **API路由**
  - [ ] `model_routes.py` - 三个核心端点：
    - [ ] `POST /models/validate-rule`
    - [ ] `POST /models/preview-sql`
    - [ ] `POST /models/evaluate-rule`

### 测试任务

- [ ] **单元测试**
  - [ ] 集合操作测试（in/not in，空数组、类型转换）
  - [ ] 正则匹配测试（语法错误、特殊字符转义）
  - [ ] SQL生成测试（验证生成的SQL正确性）

- [ ] **集成测试**
  - [ ] 前端操作符切换时值类型自动转换
  - [ ] 正则表达式实时验证
  - [ ] 复杂嵌套规则的SQL生成

---

## 附录

### A. 关键技术要点

1. **递归组件设计**: RuleBuilder通过depth参数控制嵌套深度（最多3层）
2. **类型安全**: 前后端使用相同的类型结构（TypeScript ↔ Pydantic）
3. **操作符兼容性**: 根据指标数据类型动态限制可用操作符
4. **值类型自动转换**: 操作符切换时自动在单值和多值之间转换
5. **实时验证**: 正则表达式输入时实时验证语法
6. **SQL生成**: 支持Spark SQL的 IN/NOT IN/RLIKE 语法

### B. API端点汇总

| 端点 | 方法 | 功能 |
|-----|------|-----|
| `/models/validate-rule` | POST | 验证规则配置（检查指标存在性、操作符兼容性、正则语法） |
| `/models/preview-sql` | POST | 生成Spark SQL WHERE子句 |
| `/models/evaluate-rule` | POST | 运行时评估规则（用于测试） |
| `/models` | POST | 创建模型 |
| `/models/{id}` | GET | 获取模型详情 |
| `/models/{id}` | PUT | 更新模型 |

### C. 性能优化建议

1. **前端**: useMemo缓存指标列表、防抖验证API调用
2. **后端**: 缓存指标元数据查询、批量验证规则
3. **数据库**: 指标编码字段添加索引

---

**文档结束**

如需查看完整的组件代码，请参考原始文档 `rule_engine_implementation_guide.md`。
