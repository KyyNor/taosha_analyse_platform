# FraudHunter 规则引擎快速开始指南

## 📋 目录
- [功能概述](#功能概述)
- [快速测试](#快速测试)
- [API使用示例](#api使用示例)
- [前端组件使用](#前端组件使用)
- [常见问题](#常见问题)

## 🎯 功能概述

FraudHunter规则引擎是一个强大的可视化规则配置和执行系统，支持：

### 核心功能
- ✅ **完整操作符支持**: 基础比较、集合操作(in/not in)、正则匹配(regexp/not regexp)
- ✅ **嵌套规则**: 支持AND/OR逻辑的任意嵌套组合
- ✅ **实时验证**: 规则配置的完整性和正确性检查
- ✅ **SQL生成**: 自动转换为Spark SQL WHERE子句
- ✅ **运行时评估**: Python运行时规则判断

### 支持的操作符

| 类型 | 操作符 | 适用数据类型 | 示例 |
|------|--------|------------|------|
| 基础比较 | `>`, `>=`, `<`, `<=`, `=`, `!=` | numeric | `i_login_cnt_7d > 10` |
| 集合操作 | `in`, `not in` | numeric, enum, text | `i_user_status in ['suspended', 'banned']` |
| 正则匹配 | `regexp`, `not regexp` | text | `i_user_name regexp '^admin\|^test'` |

## 🚀 快速测试

### 1. 启动后端服务

```bash
cd /home/kyynor/code/taosha_workspace/rule
./sbackend.sh
```

### 2. 访问API文档

浏览器打开: http://localhost:50020/docs

在文档中找到 **"模型管理"** 标签，可以看到以下端点：

- `POST /api/taosha/v1/fraudhunter/models/validate-rule` - 验证规则
- `POST /api/taosha/v1/fraudhunter/models/preview-sql` - 预览SQL
- `POST /api/taosha/v1/fraudhunter/models/evaluate-rule` - 评估规则
- `GET /api/taosha/v1/fraudhunter/models/health` - 健康检查

### 3. 运行测试脚本

```bash
python test_rule_engine.py
```

这将自动测试所有API端点并输出详细结果。

## 📝 API使用示例

### 示例1: 验证规则配置

**请求**:
```bash
POST /api/taosha/v1/fraudhunter/models/validate-rule
Content-Type: application/json

{
  "logic": "AND",
  "rules": [
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
      "value": ["suspended", "banned"]
    }
  ],
  "output": {
    "risk_level": "high",
    "risk_score": 85,
    "action": "review"
  }
}
```

**响应**:
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "extracted_indicators": ["i_login_cnt_7d", "i_user_status"]
}
```

### 示例2: 预览SQL表达式

使用相同的规则配置调用 `/preview-sql` 端点，将返回：

```json
{
  "sql_expression": "(i_login_cnt_7d > 10 AND i_user_status IN ('suspended', 'banned'))",
  "extracted_indicators": ["i_login_cnt_7d", "i_user_status"],
  "rule_summary": {
    "total_rules": 2,
    "max_depth": 1,
    "indicator_count": 2,
    "indicators": ["i_login_cnt_7d", "i_user_status"],
    "root_logic": "AND"
  },
  "warnings": []
}
```

### 示例3: 运行时评估规则

**请求**:
```bash
POST /api/taosha/v1/fraudhunter/models/evaluate-rule
Content-Type: application/json

{
  "rule_config": {
    "logic": "AND",
    "rules": [
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
        "value": ["suspended", "banned"]
      }
    ],
    "output": {
      "risk_level": "high",
      "risk_score": 85,
      "action": "review"
    }
  },
  "indicator_values": {
    "i_login_cnt_7d": 15,
    "i_user_status": "suspended"
  }
}
```

**响应**:
```json
{
  "is_hit": true,
  "indicator_values": {
    "i_login_cnt_7d": 15,
    "i_user_status": "suspended"
  },
  "output": {
    "risk_level": "high",
    "risk_score": 85,
    "action": "review"
  }
}
```

### 示例4: 正则匹配规则

**检测测试账号**:
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

生成的SQL:
```sql
(i_user_name RLIKE '^admin|^test|^demo' OR i_email RLIKE '@temp\\.|@fake\\.')
```

### 示例5: 复杂嵌套规则

**异常登录检测**:
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

## 🎨 前端组件使用

### 导入类型和组件

```typescript
import { ConditionRuleEditor } from '@/components/fraudhunter/model/ConditionRuleEditor'
import type {
  RuleConfig,
  ConditionRule,
  Indicator
} from '@/types/fraudhunter/rule'
```

### 使用ConditionRuleEditor

```tsx
import { useState } from 'react'
import { ConditionRuleEditor } from '@/components/fraudhunter/model/ConditionRuleEditor'

function MyComponent() {
  const [rule, setRule] = useState<ConditionRule>({
    type: 'condition',
    indicator: 'i_login_cnt_7d',
    operator: '>',
    value: 0
  })

  const indicators: Indicator[] = [
    {
      indicator_code: 'i_login_cnt_7d',
      indicator_name: '7日登录次数',
      data_type: 'numeric'
    },
    {
      indicator_code: 'i_user_status',
      indicator_name: '用户状态',
      data_type: 'enum',
      enum_values: ['normal', 'suspended', 'banned']
    },
    {
      indicator_code: 'i_user_name',
      indicator_name: '用户名',
      data_type: 'text'
    }
  ]

  return (
    <ConditionRuleEditor
      rule={rule}
      indicators={indicators}
      onChange={setRule}
    />
  )
}
```

### 调用API服务

```typescript
import { modelService } from '@/lib/services/fraudhunter/modelService'

// 验证规则
const result = await modelService.validateRule(ruleConfig)
if (result.valid) {
  console.log('规则验证通过', result.extracted_indicators)
} else {
  console.error('验证失败', result.errors)
}

// 预览SQL
const sqlResult = await modelService.previewSQL(ruleConfig)
console.log('生成的SQL:', sqlResult.sql_expression)

// 评估规则
const evalResult = await modelService.evaluateRule(
  ruleConfig,
  { i_login_cnt_7d: 15, i_user_status: 'suspended' }
)
console.log('规则命中:', evalResult.is_hit)
```

## 🔧 常见问题

### Q1: 如何测试后端API？

**方法1: 使用Swagger UI**
- 访问 http://localhost:50020/docs
- 找到"模型管理"标签
- 点击端点，填写请求体，点击"Try it out"

**方法2: 使用测试脚本**
```bash
python test_rule_engine.py
```

**方法3: 使用curl**
```bash
curl -X POST "http://localhost:50020/api/taosha/v1/fraudhunter/models/health" -H "accept: application/json"
```

### Q2: 指标不存在怎么办？

规则引擎会查询数据库中的指标定义。如果指标不存在，验证会失败并返回错误：

```json
{
  "valid": false,
  "errors": ["以下指标不存在: i_invalid_indicator"]
}
```

确保先在数据库中创建指标定义。

### Q3: 如何添加新的操作符？

1. 在 `frontend/types/fraudhunter/rule.ts` 中的 `ComparisonOperator` 类型添加新操作符
2. 在 `backend/schemas/fraudhunter/rule.py` 中的 `ComparisonOperator` Literal 添加新操作符
3. 在 `backend/services/fraudhunter/model_service/rule_engine.py` 中实现新操作符的评估逻辑
4. 在 `ALLOWED_OPERATORS` 矩阵中配置兼容性

### Q4: 正则表达式语法错误？

使用Python re模块语法。常见错误：

❌ **错误**: `[[[` （未闭合的括号）
✅ **正确**: `^admin|^test`

❌ **错误**: `\d+` （需要转义）
✅ **正确**: `\\d+`

在前端，RegexpInput组件会实时验证语法。

### Q5: in/not in 操作符如何使用？

**要求**:
- value必须是数组类型
- 数组不能为空
- 数组元素类型应与指标类型匹配

**正确示例**:
```json
{
  "type": "condition",
  "indicator": "i_user_status",
  "operator": "in",
  "value": ["suspended", "banned"]
}
```

**错误示例**:
```json
{
  "type": "condition",
  "indicator": "i_user_status",
  "operator": "in",
  "value": "suspended"  // ❌ 应该是数组
}
```

### Q6: 如何查看生成的SQL？

调用 `/preview-sql` 端点即可获得完整的SQL WHERE子句：

```bash
POST /api/taosha/v1/fraudhunter/models/preview-sql
```

返回的 `sql_expression` 字段包含生成的SQL。

### Q7: 规则嵌套深度限制？

- **建议**: 不超过3层
- **前端**: RuleBuilder组件默认限制3层（可配置）
- **后端**: 无硬性限制，但超过3层会收到警告

### Q8: 如何调试规则评估？

使用 `/evaluate-rule` 端点进行测试：

```json
{
  "rule_config": { /* 你的规则 */ },
  "indicator_values": {
    "i_login_cnt_7d": 15,
    "i_user_status": "suspended"
  }
}
```

响应会告诉你规则是否命中，以及如果命中会输出什么。

## 📚 参考文档

- 完整实现指南: `docs/rule_engine_implementation_guide.md`
- 实现总结: `docs/implementation_summary.md`
- 项目文档: `CLAUDE.md`
- API文档: http://localhost:50020/docs

## 🆘 获取帮助

如遇问题，请：
1. 查看API文档（Swagger UI）
2. 运行测试脚本验证环境
3. 查看后端日志文件
4. 参考完整实现指南

---

**版本**: v2.0.0 | **更新日期**: 2025-12-05
