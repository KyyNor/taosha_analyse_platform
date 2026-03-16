# 淘沙分析平台数据分析Agent改进计划

## 背景

淘沙分析平台的数据分析Agent目前面临的核心问题：

### 准确性问题
1. **表/字段选择不准确**：无法准确识别应该使用的表和字段
2. **查询条件错误**：即使选对字段，查询条件也可能错误
   - 示例：注释为 `acct_desc String 产品类型（S-活期 T-定期）`
   - AI可能生成 `acct_desc='S-活期'`，实际应为 `acct_desc='S'`

### 根本原因分析
当前系统的schema向量化只包含表名、字段名、字段类型、注释等静态信息，缺少：
- **字段实际值样例**：LLM无法理解字段的真实取值范围
- **丰富的schema摘要**：无法向LLM传递足够的上下文信息
- **智能表筛选**：完全依赖向量相似度，召回的表可能包含大量无关表

## 解决方案架构

本计划实现三个相互关联的功能，形成完整的Schema增强体系：

```
字段值样本增强 → Schema摘要生成 → Schema Linking智能筛选
     (基础)           (中间层)            (应用层)
```

1. **字段值样本增强服务**：从数据库采样字段的实际值，为Schema摘要提供数据
2. **Schema摘要服务**：生成包含字段值样例的丰富schema描述，用于向量化
3. **Schema Linking服务**：基于Schema摘要进行两阶段筛选（向量检索→LLM筛选）

## 当前系统现状

**已有优势：**
- ✅ 向量检索：Qdrant + qwen3-embedding-0.6b
- ✅ 重排序：bge-reranker-v2-m3
- ✅ 元数据管理：MetadataTable/MetadataColumn模型
- ✅ 表信息工具：get_table_sample_data、get_table_statistics、get_column_statistics
- ✅ 缓存机制：表信息缓存（100天过期）

**存在的缺陷：**
- ❌ Schema向量化信息不丰富：只包含静态schema信息
- ❌ 缺少字段值样例：无法帮助LLM理解字段真实取值
- ❌ 缺少Schema Linking：完全依赖向量检索，召回准确率低

## 功能实现计划

### 功能1：字段值样本增强服务

**解决问题：** 字段注释理解不准确（如"S-活期" vs "S"）

**核心设计：**
- 从数据库采样每个字段的实际值（TOP 20去重值）
- 对不同类型字段采用不同采样策略：
  - 枚举型/低基数：采样所有去重值
  - 数值型：采样min、max、平均值+随机样例
  - 文本型：采样TOP 20（按频次或随机）
- 缓存采样结果，避免重复查询

**需要修改的文件：**
- 新增：`/home/kyynor/dbgpt/taosha_analyse_platform/backend/services/vector_store/field_value_sampler.py`
- 修改：`/home/kyynor/dbgpt/taosha_analyse_platform/backend/services/vector_store/vector_training_service.py`

**参考DB-GPT：**
- `/home/kyynor/dbgpt/packages/dbgpt-core/src/dbgpt/datasource/rdbms/base.py`（_get_sample_rows方法，第540-565行）

**实现复杂度：** 中

**预期效果：**
- 为Schema摘要提供字段实际值数据
- 帮助LLM理解字段真实取值（如"产品类型字段实际值为'S','T'"）

---

### 功能2：Schema摘要生成服务

**解决问题：** Schema向量化信息不丰富，无法提供足够的上下文

**核心设计：**
- 生成包含以下信息的丰富schema描述：
  1. **表基本信息**：表名、表注释、业务描述
  2. **字段详细信息**：字段名、类型、注释
  3. **字段值样例**：（使用功能1的数据）实际值、值范围、去重值数量
  4. **表统计信息**：总行数、ETL_DATE范围
  5. **业务关系**：关联表、外键关系（如果有）
- 支持大表字段分离：对于字段过多的表，分离表级和字段级摘要
- 生成格式化的文本摘要，用于向量化

**示例Schema摘要格式：**
```
表名：hxb_acct_dtl
注释：账户明细表
业务描述：存储客户账户的交易明细信息

字段列表：
1. acct_no VARCHAR(50) - 账号
   值样例：['6222021234567890', '6222029876543210']
   去重值数量：1523412

2. acct_desc VARCHAR(10) - 产品类型（S-活期 T-定期）
   值样例：['S', 'T']
   取值说明：S=活期, T=定期
   去重值数量：2

3. balance DECIMAL(18,2) - 账户余额
   值范围：0.00 ~ 999999999.99
   平均值：15234.56

表统计：
- 总行数：约5000万
- ETL_DATE范围：2024-01-01 ~ 2024-12-31
```

**需要修改的文件：**
- 新增：`/home/kyynor/dbgpt/taosha_analyse_platform/backend/services/vector_store/schema_summary_service.py`
- 修改：`/home/kyynor/dbgpt/taosha_analyse_platform/backend/services/vector_store/vector_training_service.py`
- 修改：`/home/kyynor/dbgpt/taosha_analyse_platform/backend/services/agents/tools/qdrant_vector_store_tool.py`（返回schema摘要）

**参考DB-GPT：**
- `/home/kyynor/dbgpt/packages/dbgpt-ext/src/dbgpt_ext/rag/summary/rdbms_db_summary.py`（完整实现）
- `/home/kyynor/dbgpt/packages/dbgpt-ext/src/dbgpt_ext/rag/retriever/db_schema.py`（字段分离检索）

**实现复杂度：** 高

**预期效果：**
- 向量检索时返回更丰富的schema信息
- LLM能够基于字段值样例理解字段真实含义
- 减少"S-活期"类注释导致的查询错误

---

### 功能3：Schema Linking智能筛选服务

**解决问题：** 表/字段选择不准确，向量检索召回包含大量无关表

**核心设计：**
- **两阶段筛选流程**：
  1. **向量检索召回**：基于Schema摘要进行向量检索，召回候选表（top_k=10）
  2. **LLM精确筛选**：使用Few-Shot提示，让LLM从候选表中选择最相关的3-5个表
- **Few-Shot提示设计**：提供3个示例
  - 示例1：简单单表查询
  - 示例2：两表关联查询
  - 示例3：多表聚合查询
- **异步处理**：LLM筛选使用异步调用，提高响应速度

**工作流程：**
```
用户问题："查询活期存款和定期存款的余额分布"
    ↓
1. 向量检索召回候选表（top_k=10）
   候选表：[hxb_acct_dtl, hxb_cust_info, hxb_trans_log, ...]
    ↓
2. Schema Linking筛选（Few-Shot LLM）
   输入：用户问题 + 候选表的Schema摘要
   输出：相关表=[hxb_acct_dtl]
   理由："问题涉及活期和定期存款的余额分布，只需要账户明细表"
    ↓
3. 使用筛选后的表生成SQL
```

**需要修改的文件：**
- 新增：`/home/kyynor/dbgpt/taosha_analyse_platform/backend/services/agents/schema_linking_service.py`
- 修改：`/home/kyynor/dbgpt/taosha_analyse_platform/backend/services/agents/deepagents/data_analyser_agent.py`
- 新增：`/home/kyynor/dbgpt/taosha_analyse_platform/backend/models/prompt_templates.py`（存储Few-Shot模板）

**参考DB-GPT：**
- `/home/kyynor/dbgpt/packages/dbgpt-ext/src/dbgpt_ext/rag/schemalinker/schema_linking.py`（完整实现）
- `/home/kyynor/dbgpt/packages/dbgpt-app/src/dbgpt_app/scene/chat_db/auto_execute/chat.py`（第67-84行，集成Schema Linking）

**实现复杂度：** 高

**预期效果：**
- 表选择准确率提升40%以上
- 减少无关表的干扰
- 降低LLM处理的Token数量
- 提升SQL生成准确性

## 实施计划

### 第一阶段：字段值样本增强（1周）
**目标：** 实现字段值采样功能

**任务：**
1. 创建 `field_value_sampler.py`
   - 实现字段值采样逻辑
   - 支持不同类型字段的采样策略
   - 添加缓存机制
2. 修改 `vector_training_service.py`
   - 集成字段值采样
   - 在向量训练时调用采样服务
3. 测试验证
   - 验证不同类型字段的采样结果
   - 验证缓存有效性

**产出：**
- 字段值采样服务可用
- 元数据库中存储字段值样例

---

### 第二阶段：Schema摘要生成（1-2周）
**目标：** 实现Schema摘要生成和向量化

**任务：**
1. 创建 `schema_summary_service.py`
   - 实现Schema摘要生成逻辑
   - 包含字段值样例、统计信息
   - 支持大表字段分离
2. 修改 `vector_training_service.py`
   - 使用Schema摘要替代简单的schema信息
   - 调整向量训练流程
3. 修改 `qdrant_vector_store_tool.py`
   - search_knowledge_base返回Schema摘要
   - 调整检索结果格式
4. 测试验证
   - 验证Schema摘要的完整性
   - 验证向量检索效果

**产出：**
- Schema摘要生成服务可用
- 向量数据库存储Schema摘要
- 检索时返回丰富的schema信息

---

### 第三阶段：Schema Linking（1-2周）
**目标：** 实现两阶段Schema筛选

**任务：**
1. 创建 `schema_linking_service.py`
   - 实现Few-Shot提示模板
   - 实现LLM筛选逻辑
   - 异步调用优化
2. 修改 `data_analyser_agent.py`
   - 在SQL生成前调用Schema Linking
   - 使用筛选后的表生成SQL
3. 创建 `prompt_templates.py`
   - 存储Schema Linking提示词
   - 支持动态更新
4. 测试验证
   - 验证两阶段筛选流程
   - 对比筛选前后的准确性

**产出：**
- Schema Linking服务可用
- Agent集成Schema Linking
- 表选择准确率提升

## 预期整体效果

实施完这三个功能后，预期可以达到：

1. **SQL准确性提升50%以上**
   - 字段值样例帮助LLM理解真实取值
   - Schema Linking减少无关表干扰
   - 丰富的Schema摘要提供更好的上下文

2. **Token消耗降低30%**
   - Schema Linking筛选后只传递相关表
   - 减少LLM处理的无关信息

3. **用户体验显著改善**
   - 更准确的表/字段选择
   - 更准确的查询条件
   - 更快的响应速度

## 关键文件清单

### 需要新增的文件
- `/home/kyynor/dbgpt/taosha_analyse_platform/backend/services/vector_store/field_value_sampler.py`
- `/home/kyynor/dbgpt/taosha_analyse_platform/backend/services/vector_store/schema_summary_service.py`
- `/home/kyynor/dbgpt/taosha_analyse_platform/backend/services/agents/schema_linking_service.py`
- `/home/kyynor/dbgpt/taosha_analyse_platform/backend/models/prompt_templates.py`

### 需要修改的文件
- `/home/kyynor/dbgpt/taosha_analyse_platform/backend/services/vector_store/vector_training_service.py`
- `/home/kyynor/dbgpt/taosha_analyse_platform/backend/services/agents/tools/qdrant_vector_store_tool.py`
- `/home/kyynor/dbgpt/taosha_analyse_platform/backend/services/agents/deepagents/data_analyser_agent.py`

### 参考实现（DB-GPT）
- `/home/kyynor/dbgpt/packages/dbgpt-core/src/dbgpt/datasource/rdbms/base.py` - 字段值采样
- `/home/kyynor/dbgpt/packages/dbgpt-ext/src/dbgpt_ext/rag/summary/rdbms_db_summary.py` - Schema摘要
- `/home/kyynor/dbgpt/packages/dbgpt-ext/src/dbgpt_ext/rag/schemalinker/schema_linking.py` - Schema Linking
- `/home/kyynor/dbgpt/packages/dbgpt-ext/src/dbgpt_ext/rag/retriever/db_schema.py` - Schema检索
- `/home/kyynor/dbgpt/packages/dbgpt-app/src/dbgpt_app/scene/chat_db/auto_execute/chat.py` - Schema Linking集成

## 技术要点

### 字段值采样策略
```python
# 伪代码示例
def sample_field_values(field_name, field_type, table_name, limit=20):
    if field_type in ['VARCHAR', 'TEXT']:
        # 文本型：采样TOP 20去重值
        return query_top_distinct_values(table_name, field_name, limit)
    elif field_type in ['INT', 'DECIMAL', 'FLOAT']:
        # 数值型：采样统计信息 + 随机样例
        stats = query_field_statistics(table_name, field_name)
        samples = query_random_samples(table_name, field_name, 5)
        return {**stats, 'samples': samples}
    elif field_type == 'DATE':
        # 日期型：采样范围
        return query_date_range(table_name, field_name)
```

### Schema摘要格式化
```python
# 伪代码示例
def generate_schema_summary(table_name, columns, field_samples):
    summary = f"表名：{table_name}\n"
    summary += f"注释：{table.comment}\n\n"
    summary += "字段列表：\n"
    for col in columns:
        summary += f"- {col.name} {col.type} - {col.comment}\n"
        samples = field_samples.get(col.name, [])
        if samples:
            summary += f"  值样例：{samples[:5]}\n"
    return summary
```

### Schema Linking Few-Shot模板
```python
SCHEMA_LINKING_TEMPLATE = """
你是一个数据库专家，需要从候选表中选择与用户问题最相关的表。

## 示例1
问题：查询活期存款客户的数量
候选表：
- hxb_acct_dtl: 账户明细表，包含acct_desc（产品类型）、balance等字段
- hxb_cust_info: 客户信息表，包含cust_name、cert_type等字段
- hxb_trans_log: 交易流水表
选择结果：hxb_acct_dtl
理由：问题涉及活期存款，只需要账户明细表

## 示例2
问题：查询2024年每月的交易总额
候选表：
- hxb_acct_dtl: 账户明细表
- hxb_trans_log: 交易流水表，包含trans_date、amount等字段
选择结果：hxb_trans_log
理由：问题涉及交易统计，需要交易流水表

## 当前任务
问题：{question}
候选表：
{candidate_tables}

请返回：
1. 选择的表列表
2. 选择理由
"""
```

## 风险与缓解

### 风险1：字段值采样性能影响
**缓解措施：**
- 使用缓存机制，避免重复采样
- 限制采样数量（TOP 20）
- 异步后台采样

### 风险2：大表Schema摘要过长
**缓解措施：**
- 实现字段分离机制（参考DB-GPT）
- 对字段摘要进行截断
- 分表级和字段级两次检索

### 风险3：Schema Linking增加延迟
**缓解措施：**
- 使用异步LLM调用
- 缓存常见问题的筛选结果
- 提供降级策略（直接使用向量检索结果）
