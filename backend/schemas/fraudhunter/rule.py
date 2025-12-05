"""
FraudHunter规则引擎数据模型

版本: v2.0.0 (支持高级操作符)
定义规则配置的数据结构，用于：
1. API请求/响应验证
2. 规则存储和序列化
3. 规则执行和评估

支持操作符: 基础比较、集合操作(in/not in)、正则匹配(regexp/not regexp)
"""

from typing import Literal, Union, List, Optional
from pydantic import BaseModel, Field, field_validator
import re

# ==================== 基础类型定义 ====================

# 完整操作符类型（包含高级操作符）
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
    """条件规则：单个指标的比较判断（支持多值）"""

    type: Literal["condition"]
    indicator: str = Field(..., description="指标编码，如 i_login_cnt_7d")
    operator: ComparisonOperator = Field(..., description="比较操作符")
    value: Union[str, int, float, bool, List[str], List[int], List[float]] = Field(
        ...,
        description="比较值，支持单值或数组"
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
                    "value": ["suspended", "banned", "frozen"]
                },
                {
                    "type": "condition",
                    "indicator": "i_user_name",
                    "operator": "regexp",
                    "value": "^admin|^test|^demo"
                }
            ]
        }


class GroupRule(BaseModel):
    """规则组：多个规则的逻辑组合，支持嵌套"""

    type: Literal["group"]
    logic: LogicOperator = Field(..., description="逻辑操作符：AND/OR")
    rules: List["Rule"] = Field(..., description="子规则列表")

    @field_validator('rules')
    @classmethod
    def validate_rules_not_empty(cls, v):
        """验证规则列表不能为空"""
        if not v:
            raise ValueError("规则组的rules字段不能为空")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "type": "group",
                "logic": "AND",
                "rules": [
                    {
                        "type": "condition",
                        "indicator": "i_login_cnt_7d",
                        "operator": ">",
                        "value": 10
                    }
                ]
            }
        }


# 联合类型定义
Rule = Union[ConditionRule, GroupRule]

# 更新前向引用（Pydantic递归模型）
GroupRule.model_rebuild()

# ==================== 输出配置 ====================

class RuleOutput(BaseModel):
    """规则命中后的输出配置"""

    risk_level: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="风险等级"
    )
    risk_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="风险分数，范围0-100"
    )
    action: Optional[Literal["block", "review", "alert", "pass"]] = Field(
        None,
        description="处理动作：拦截/审核/告警/放行"
    )
    description: Optional[str] = Field(
        None,
        description="输出描述"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "risk_level": "high",
                "risk_score": 85,
                "action": "review",
                "description": "高风险登录行为，需人工审核"
            }
        }


# ==================== 完整规则配置 ====================

class RuleConfig(BaseModel):
    """完整的规则配置"""

    logic: LogicOperator = Field(..., description="根逻辑操作符")
    rules: List[Rule] = Field(..., description="根规则列表")
    output: RuleOutput = Field(..., description="输出配置")

    @field_validator('rules')
    @classmethod
    def validate_rules_not_empty(cls, v):
        """验证根规则列表不能为空"""
        if not v:
            raise ValueError("规则配置的rules字段不能为空")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "logic": "AND",
                "rules": [
                    {
                        "type": "condition",
                        "indicator": "i_login_cnt_7d",
                        "operator": ">",
                        "value": 10
                    },
                    {
                        "type": "group",
                        "logic": "OR",
                        "rules": [
                            {
                                "type": "condition",
                                "indicator": "i_device_change_cnt",
                                "operator": ">=",
                                "value": 3
                            },
                            {
                                "type": "condition",
                                "indicator": "i_user_status",
                                "operator": "in",
                                "value": ["suspended", "banned"]
                            }
                        ]
                    }
                ],
                "output": {
                    "risk_level": "high",
                    "risk_score": 85,
                    "action": "review"
                }
            }
        }


# ==================== 验证结果 ====================

class RuleValidationResult(BaseModel):
    """规则验证结果"""

    valid: bool = Field(..., description="是否验证通过")
    errors: List[str] = Field(
        default_factory=list,
        description="错误信息列表"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="警告信息列表"
    )
    extracted_indicators: List[str] = Field(
        default_factory=list,
        description="提取到的指标编码列表"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "errors": [],
                "warnings": ["规则嵌套深度为4，建议不超过3层"],
                "extracted_indicators": ["i_login_cnt_7d", "i_device_change_cnt"]
            }
        }


# ==================== SQL预览结果 ====================

class SQLPreviewResult(BaseModel):
    """SQL预览结果"""

    sql_expression: str = Field(..., description="生成的SQL WHERE子句")
    extracted_indicators: List[str] = Field(..., description="提取到的指标列表")
    rule_summary: dict = Field(..., description="规则摘要信息")
    warnings: List[str] = Field(default_factory=list, description="警告信息")

    class Config:
        json_schema_extra = {
            "example": {
                "sql_expression": "(i_login_cnt_7d > 10 AND (i_device_change_cnt >= 3 OR i_user_status IN ('suspended', 'banned')))",
                "extracted_indicators": ["i_login_cnt_7d", "i_device_change_cnt", "i_user_status"],
                "rule_summary": {
                    "total_rules": 3,
                    "max_depth": 2,
                    "indicator_count": 3,
                    "indicators": ["i_login_cnt_7d", "i_device_change_cnt", "i_user_status"],
                    "root_logic": "AND"
                },
                "warnings": []
            }
        }


# ==================== 运行时评估结果 ====================

class RuleEvaluationResult(BaseModel):
    """运行时评估结果"""

    is_hit: bool = Field(..., description="规则是否命中")
    indicator_values: dict = Field(..., description="输入的指标值")
    output: Optional[dict] = Field(None, description="规则命中时的输出配置")

    class Config:
        json_schema_extra = {
            "example": {
                "is_hit": True,
                "indicator_values": {
                    "i_login_cnt_7d": 15,
                    "i_device_change_cnt": 5,
                    "i_user_status": "suspended"
                },
                "output": {
                    "risk_level": "high",
                    "risk_score": 85,
                    "action": "review",
                    "description": "高风险登录行为，需人工审核"
                }
            }
        }
