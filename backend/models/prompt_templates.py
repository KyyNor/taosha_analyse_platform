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
class KnowledgeFragmentationTemplates:
    """知识片段生成提示词模板"""

    # 片段生成模板
    FRAGMENT_GENERATION_TEMPLATE = """你是一个知识管理专家，需要将给定的内容拆分为{fragment_count}个独立、完整的知识片段。

## 拆分原则
1. **完整性**：每个片段应该是一个完整的知识单元，可以独立理解
2. **简洁性**：片段标题简洁明了，内容精炼准确
3. **独立性**：片段之间尽量避免重复，各有侧重
4. **实用性**：优先提取业务规则、计算逻辑、关键概念等实用信息

## 内容类型
当前内容类型：{content_type}

## Few-Shot示例

### 示例1：SQL脚本拆分
**原始内容**：
```sql
-- 客户积分计算规则
-- 每消费100元积1分
-- 生日当天消费双倍积分
UPDATE customer_points SET points = points + FLOOR(amount / 100) * 2
WHERE cust_id IN (SELECT cust_id FROM customer WHERE birthday = TODAY());
```

**拆分结果**：
```json
[
  {{
    "title": "客户积分基础计算规则",
    "content": "客户每消费100元获得1积分，积分计算公式为：FLOOR(消费金额 / 100)",
    "summary": "客户积分基础累加规则"
  }},
  {{
    "title": "生日双倍积分特殊规则",
    "content": "客户生日当天消费享受双倍积分优惠，通过识别生日字段并应用2倍乘数实现",
    "summary": "生日专属积分加倍规则"
  }}
]
```

### 示例2：业务文档拆分
**原始内容**：
```
活期存款产品说明
活期存款是一种无固定期限、可以随时存取的存款方式。
特点：1. 灵活性高 2. 利率较低 3. 适合日常资金管理
计息方式：按日计息，按月结息
利率：年化利率0.30%
```

**拆分结果**：
```json
[
  {{
    "title": "活期存款产品定义",
    "content": "活期存款是无固定期限、可随时存取的存款方式，具有高灵活性特点",
    "summary": "活期存款基本定义"
  }},
  {{
    "title": "活期存款产品特点",
    "content": "活期存款三大特点：1. 灵活性高-随时存取 2. 利率较低-年化0.30% 3. 适合日常资金管理",
    "summary": "活期存款核心特征"
  }},
  {{
    "title": "活期存款计息规则",
    "content": "活期存款采用按日计息、按月结息的方式，年化利率为0.30%",
    "summary": "活期存款利息计算方法"
  }}
]
```

## 当前任务
**原始内容**：
```
{content}
```

请严格按照以下JSON格式返回{fragment_count}个知识片段（不要包含其他内容）：
```json
[
  {{
    "title": "片段标题",
    "content": "片段详细内容",
    "summary": "简短摘要"
  }},
  ...
]
```

**注意**：
1. 必须恰好返回{fragment_count}个片段
2. 每个片段的title要简洁明确
3. content要包含完整的信息，可以适当扩展和解释
4. summary是对content的简短概括（不超过50字）
5. 避免片段之间的内容重复
6. 对于技术内容，保持专业术语和逻辑的准确性
"""

    # 主题提取模板
    TOPIC_EXTRACTION_TEMPLATE = """你是一个知识提取专家，需要根据用户的主题需求，从给定的内容中提取相关知识。

## 提取原则
1. **相关性**：只提取与主题直接相关的知识
2. **完整性**：提取的知识应该完整，不要遗漏关键信息
3. **准确性**：保持原文的业务逻辑和技术细节
4. **可读性**：提取的内容应该清晰易懂

## 提取主题
**主题**：{extraction_theme}

## 提取要求
{extraction_prompt}

## Few-Shot示例

### 示例1：提取数据质量规则
**主题**：数据质量校验规则
**提取要求**：提取所有数据校验相关的规则和阈值
**原始内容**：
```
客户信息表数据质量规则：
1. 客户姓名不能为空
2. 手机号必须是11位数字
3. 身份证号必须是18位且符合校验规则
4. 年龄必须在18-120岁之间
5. 客户状态必须是：正常、冻结、注销之一
```

**提取结果**：
```json
{{
  "title": "客户信息表数据质量校验规则",
  "content": "客户信息表包含5个数据质量校验规则：1. 客户姓名非空校验 2. 手机号格式校验（11位数字） 3. 身份证号格式校验（18位+校验规则） 4. 年龄范围校验（18-120岁） 5. 客户状态枚举值校验（正常/冻结/注销）",
  "summary": "客户信息表数据质量规则集"
}}
```

### 示例2：提取计算逻辑
**主题**：利息计算方法
**提取要求**：提取所有利息计算相关的公式和规则
**原始内容**：
```
存款利息计算：
- 活期：按日计息，日利率 = 年利率 / 360
- 定期：到期一次性还本付息，利息 = 本金 × 年利率 × 存期（年）
- 逾期：逾期部分按活期利率计算
```

**提取结果**：
```json
{{
  "title": "存款利息计算方法汇总",
  "content": "存款利息分为三种计算方式：1. 活期存款按日计息，日利率=年利率/360 2. 定期存款到期一次性还本付息，利息=本金×年利率×存期(年) 3. 逾期部分按活期利率计算",
  "summary": "存款利息计算公式和规则"
}}
```

## 当前任务
**原始内容**：
```
{content}
```

请严格按照以下JSON格式返回提取的知识片段（不要包含其他内容）：
```json
{{
  "title": "知识标题",
  "content": "知识详细内容",
  "summary": "简短摘要"
}}
```

**注意**：
1. 严格围绕"{extraction_theme}"主题提取
2. 按照用户的要求进行提取：{extraction_prompt}
3. content要包含完整的信息，可以适当整合和优化表述
4. summary是对content的简短概括（不超过50字）
5. 如果原文中没有相关主题的知识，返回相关内容为空的提示
"""

    # SQL总结模板
    SQL_SUMMARY_TEMPLATE = """你是一个SQL专家，需要将SQL脚本的业务逻辑总结为非技术人员也能理解的说明。

## 总结原则
1. **业务导向**：从业务角度解释SQL的功能，而不是技术角度
2. **简洁明了**：使用通俗易懂的语言，避免技术术语
3. **结构清晰**：按照数据来源、处理逻辑、输出结果的结构组织
4. **重点突出**：突出核心业务规则和计算逻辑

## Few-Shot示例

### 示例1：简单查询
**SQL脚本**：
```sql
SELECT cust_name, balance
FROM customer_account
WHERE balance > 10000
  AND status = 'ACTIVE';
```

**总结结果**：
```
这个查询用于查找所有活跃状态的高价值客户（余额大于1万元），
返回客户姓名和账户余额信息，用于客户价值分析。
```

### 示例2：复杂计算
**SQL脚本**：
```sql
UPDATE customer_points
SET points = points + FLOOR(amount / 100) * 2
WHERE cust_id IN (
  SELECT cust_id
  FROM customer
  WHERE birthday = TODAY()
);
```

**总结结果**：
```
这个脚本用于给生日客户发放双倍积分奖励。
具体逻辑：1. 找出今天过生日的所有客户 2. 根据他们的消费金额计算积分（每100元积2分） 3. 将计算出的积分累加到客户的积分账户中
```

## 当前任务
**SQL脚本**：
```sql
{sql_content}
```

请返回业务逻辑总结（不要包含其他内容）：
```
（在这里写总结）
```

**注意**：
1. 从业务角度解释，不要说"JOIN"、"WHERE"等技术词
2. 使用"查找"、"筛选"、"计算"、"更新"等业务用语
3. 总结长度控制在200字以内
4. 突出核心业务价值
"""


TEMPLATE_REGISTRY = {
    "schema_linking": SchemaLinkingTemplates,
    "sql_generation": SQLGenerationTemplates,
    "data_analysis": DataAnalysisTemplates,
    "knowledge_fragmentation": KnowledgeFragmentationTemplates
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
