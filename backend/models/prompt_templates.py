"""
提示词模板

存储各种LLM提示词模板，包括Schema Linking、SQL生成等。
支持Few-Shot学习和动态参数替换。
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """提示词模板基类"""
    name: str
    template: str
    description: str


class SchemaLinkingTemplates:
    """Schema Linking提示词模板"""

    # Few-Shot示例
    EXAMPLES = [
        {
            "question": "查询活期存款客户的数量",
            "candidate_tables": """- hxb_acct_dtl: 账户明细表，包含acct_desc（产品类型）、balance等字段
- hxb_cust_info: 客户信息表，包含cust_name、cert_type等字段
- hxb_trans_log: 交易流水表""",
            "selected_tables": ["hxb_acct_dtl"],
            "reasoning": "问题涉及活期存款客户数量统计，只需要账户明细表中的产品类型字段即可完成查询"
        },
        {
            "question": "查询2024年每月的交易总额",
            "candidate_tables": """- hxb_acct_dtl: 账户明细表
- hxb_trans_log: 交易流水表，包含trans_date（交易日期）、amount（交易金额）等字段
- hxb_cust_info: 客户信息表""",
            "selected_tables": ["hxb_trans_log"],
            "reasoning": "问题涉及交易统计，需要交易流水表中的交易日期和金额字段"
        },
        {
            "question": "查询客户张三的账户余额和交易记录",
            "candidate_tables": """- hxb_acct_dtl: 账户明细表，包含acct_no（账号）、balance（余额）等字段
- hxb_cust_info: 客户信息表，包含cust_name（客户姓名）、cert_no（证件号）等字段
- hxb_trans_log: 交易流水表，包含trans_date、amount等字段""",
            "selected_tables": ["hxb_acct_dtl", "hxb_cust_info", "hxb_trans_log"],
            "reasoning": "问题涉及客户信息、账户余额和交易记录，需要关联三个表：客户信息表用于定位客户，账户明细表用于查询余额，交易流水表用于查询交易记录"
        }
    ]

    # Schema Linking主模板
    SCHEMA_LINKING_TEMPLATE = """你是一个数据库专家，需要从候选表中选择与用户问题最相关的表。

## 选择原则
1. **最小化原则**：只选择解决问题必需的表，避免选择无关表
2. **优先级原则**：优先选择包含问题关键字段的表
3. **关联原则**：如果需要关联表，确保关联字段存在

## Few-Shot示例

### 示例1：简单单表查询
**问题**：{example1_question}
**候选表**：
{example1_tables}
**选择结果**：{example1_selected}
**理由**：{example1_reasoning}

### 示例2：简单单表查询
**问题**：{example2_question}
**候选表**：
{example2_tables}
**选择结果**：{example2_selected}
**理由**：{example2_reasoning}

### 示例3：多表关联查询
**问题**：{example3_question}
**候选表**：
{example3_tables}
**选择结果**：{example3_selected}
**理由**：{example3_reasoning}

## 当前任务
**问题**：{question}
**候选表**：
{candidate_tables}

请严格按照以下JSON格式返回结果（不要包含其他内容）：
```json
{{
  "selected_tables": ["表名1", "表名2"],
  "reasoning": "选择理由",
  "table_count": 数量
}}
```

**注意**：
1. selected_tables必须从候选表中选择
2. reasoning要简洁明确，说明为什么选择这些表
3. 一般选择1-5个表，不要超过5个
4. 表名必须是候选表中的完整表名
"""

    # 简化版本（用于快速筛选）
    SCHEMA_LINKING_SIMPLE_TEMPLATE = """你是一个数据库专家，需要从候选表中选择与用户问题最相关的表。

**问题**：{question}
**候选表**：
{candidate_tables}

请选择最相关的1-5个表，按重要性排序。

返回JSON格式：
```json
{{
  "selected_tables": ["表名1", "表名2"],
  "reasoning": "选择理由"
}}
```
"""

    @classmethod
    def get_template(cls, use_simple: bool = False) -> str:
        """获取Schema Linking模板

        Args:
            use_simple: 是否使用简化版本

        Returns:
            模板字符串（包含占位符 {question} 和 {candidate_tables}）
        """
        if use_simple:
            return cls.SCHEMA_LINKING_SIMPLE_TEMPLATE

        # 使用完整版本（Few-Shot），预填充示例
        return cls.SCHEMA_LINKING_TEMPLATE.format(
            example1_question=cls.EXAMPLES[0]["question"],
            example1_tables=cls.EXAMPLES[0]["candidate_tables"],
            example1_selected=cls.EXAMPLES[0]["selected_tables"],
            example1_reasoning=cls.EXAMPLES[0]["reasoning"],
            example2_question=cls.EXAMPLES[1]["question"],
            example2_tables=cls.EXAMPLES[1]["candidate_tables"],
            example2_selected=cls.EXAMPLES[1]["selected_tables"],
            example2_reasoning=cls.EXAMPLES[1]["reasoning"],
            example3_question=cls.EXAMPLES[2]["question"],
            example3_tables=cls.EXAMPLES[2]["candidate_tables"],
            example3_selected=cls.EXAMPLES[2]["selected_tables"],
            example3_reasoning=cls.EXAMPLES[2]["reasoning"]
        )


class SQLGenerationTemplates:
    """SQL生成提示词模板"""

    SQL_GENERATION_TEMPLATE = """你是一个SQL专家，需要根据用户问题和数据库Schema生成SQL查询。

## 数据库信息
{database_info}

## 用户问题
{question}

## 相关表的Schema
{schemas}

## 要求
1. 生成正确的SQL查询语句
2. 使用适当的WHERE条件进行过滤
3. 注意JOIN条件的正确性
4. 对于日期字段，使用合适的格式
5. 对于聚合查询，使用GROUP BY和聚合函数
6. 限制结果数量（LIMIT）

请只返回SQL语句，不要包含其他解释。
"""


class DataAnalysisTemplates:
    """数据分析提示词模板"""

    DATA_ANALYSIS_TEMPLATE = """你是一个数据分析专家，需要帮助用户分析数据。

## 用户问题
{question}

## 数据查询结果
{query_results}

## 要求
1. 理解用户的分析需求
2. 基于查询结果进行分析
3. 提供有价值的洞察
4. 使用清晰的语言解释结论
5. 如果需要，建议后续分析方向

请提供分析结果。
"""


# 模板注册表
TEMPLATE_REGISTRY = {
    "schema_linking": SchemaLinkingTemplates,
    "sql_generation": SQLGenerationTemplates,
    "data_analysis": DataAnalysisTemplates
}


def get_template(template_type: str, template_name: str = "", **kwargs) -> str:
    """获取提示词模板

    Args:
        template_type: 模板类型（schema_linking, sql_generation, data_analysis）
        template_name: 模板名称（可选）
        **kwargs: 模板参数

    Returns:
        模板字符串
    """
    template_class = TEMPLATE_REGISTRY.get(template_type)
    if not template_class:
        raise ValueError(f"未知的模板类型: {template_type}")

    if template_name:
        # 获取特定模板
        if hasattr(template_class, template_name):
            template = getattr(template_class, template_name)
            if callable(template):
                return template(**kwargs)
            return template
        else:
            raise ValueError(f"模板 {template_name} 在 {template_type} 中不存在")
    else:
        # 获取默认模板
        if hasattr(template_class, "get_template"):
            return template_class.get_template(**kwargs)
        else:
            raise ValueError(f"模板类型 {template_type} 没有默认模板")
