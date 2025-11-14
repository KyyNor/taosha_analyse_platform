# 数据分析Agent系统 - 详细设计文档

## 1. 系统概述

淘沙分析平台升级为**智能数据分析Agent系统**，支持自然语言查询、多源数据分析、意图识别与复杂查询拆解，提供Generative UI实时可视化和完整的会话管理能力。

**核心目标**：
- 统一的数据查询入口（自然语言 → SQL/报表/代码）
- 智能意图识别，自动选择最优查询路径
- 支持复杂多步分析的DeepAgent工作流
- 用户友好的可视化和会话管理

---

## 2. 功能架构

```
┌─────────────────────────────────────────────────────────────┐
│                       前端交互层                              │
│  ┌──────────────┬──────────────┬──────────────────────────┐ │
│  │ 聊天对话界面  │ 会话管理界面  │ 数据可视化(Generative UI)│ │
│  └──────────────┴──────────────┴──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         ↓ WebSocket/SSE流式通信 ↓
┌─────────────────────────────────────────────────────────────┐
│                    Agent编排层 (LangGraph)                    │
│  ┌───────────┬──────────┬────────────┬──────────────────┐   │
│  │ 意图识别  │ 路由决策 │ DeepAgent工作流 │ 普通Agent查询  │   │
│  └───────────┴──────────┴────────────┴──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│                    工具执行层 (Tools)                         │
│  ┌─────────────┬──────────┬──────────┬─────────────────┐    │
│  │ 查询引擎    │ 报表工具 │ 信息检索 │ 代码Sandbox    │    │
│  │(Spark/MySQL)│(Playwright)│(向量+全文)│(Python Exec)   │    │
│  └─────────────┴──────────┴──────────┴─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│                    数据存储层                                 │
│  ┌──────┬────────┬─────────────┬──────────┐               │
│  │ Spark│ MySQL  │ 元数据DB    │ 向量DB  │               │
│  └──────┴────────┴─────────────┴──────────┘               │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 里程碑一：基础Agent与数据管理功能

### 3.1 里程碑一预期效果

**完成后的核心能力**：
- 用户可以通过自然语言进行基础的数据查询和分析
- 系统能够智能理解用户意图并选择合适的数据源
- 提供基础的数据可视化和会话管理功能
- 支持报表元数据配置和知识库检索

**用户体验提升**：
- 从传统的SQL查询界面升级为自然语言对话界面
- 降低数据分析门槛，业务人员可以直接使用
- 统一的查询入口，无需了解底层数据结构
- 实时获取查询结果和基础图表展示

**开发计划**：

---

### 3.2 数据分析工具集（优先级：P0）

**工具列表**：
1. **Spark查询引擎** - 大规模数据处理，支持SQL和DataFrame API
2. **MySQL查询引擎** - 结构化业务数据查询
3. **报表查询工具** - Playwright自动化操作报表系统，支持参数传递和数据提取
4. **信息检索工具** - 多模态知识库检索

**实现思路**：
- 统一Tool接口：`BaseTool(name, description, execute())`
- 每个工具独立实现，支持超时/重试机制
- 集成到Agent的Tool Registry中
- 支持工具链式调用（Tool A结果 → Tool B输入）

**后端实现**：
```
backend/services/tools/
  ├── spark_tool.py           # Spark查询
  ├── mysql_tool.py           # MySQL查询
  ├── report_tool.py          # 报表查询（Playwright）
  └── retrieval_tool.py       # 信息检索
```

---

### 3.3 多模态信息检索（优先级：P0）

**检索流程**：
```
用户查询 → 分词 + 同义词扩展 → 全文检索 + 向量检索 → BM25重排 → TopK结果
```

**核心能力**：
1. **分词 + 同义词扩展** - 基于业务术语表，扩展查询词汇
2. **全文检索** - Elasticsearch/DuckDB FTS，精确匹配
3. **向量检索** - Qdrant，语义相似度
4. **智能重排** - BM25 + 向量相似度加权排序

**数据源**：
- 表字段定义（schema）
- 报表元数据（描述、说明）
- 业务术语表（glossary）
- 历史查询（成功案例）

**后端实现**：
```
backend/services/retrieval_service/
  ├── text_processor.py       # 分词、同义词扩展
  ├── full_text_search.py     # 全文检索
  ├── vector_search.py        # 向量检索
  └── reranker.py             # 智能重排
```

---

### 3.4 报表元数据配置管理（优先级：P0）

**元数据包含**：
- 报表名称、链接、类型（汇总表/明细表）
- 报表说明、适用场景、参数定义
- 字段映射（报表字段 → 数据库字段）
- 访问权限、更新频率

**功能需求**：
1. **配置页面** - CRUD操作，支持批量导入
2. **知识库训练** - 报表信息加入向量库用于检索
3. **参数管理** - 支持动态参数定义（日期、维度、指标）

**后端实现**：
```
扩展现有 metadata_service
  ├── report_repository.py    # 报表CRUD
  └── report_metadata_sync.py # 报表信息同步到向量库
```

**前端实现**：
```
- src/components/metadata/ReportConfigForm.vue      # 报表配置表单
- src/views/MetadataReportPage.vue                  # 报表管理页面
```

---

### 3.5 Generative UI - 动态可视化组件（优先级：P1）

**支持的组件**：
- 饼图/环形图 - 占比分析
- 树图 - 层级关系展示
- 折线图 - 时间序列趋势
- 柱状图 - 分类对比
- 对比表 - 多维数据对标

**实现思路**：
1. **Agent决策** - 根据数据特征自动选择组件类型
   ```
   if data.has_time_dimension and data.is_trend:
       component = LineChart
   elif data.is_hierarchical:
       component = TreeChart
   elif data.is_percentage:
       component = PieChart
   ```

2. **组件库** - 基于ECharts/AntV G2
   ```
   前端：
   - src/components/charts/
     ├── LineChart.vue
     ├── BarChart.vue
     ├── PieChart.vue
     ├── TreeChart.vue
     └── ComparisonTable.vue
   ```

3. **数据格式化** - 标准化接口
   ```typescript
   interface ChartData {
     type: 'line' | 'bar' | 'pie' | 'tree' | 'table'
     data: any[]
     config?: any  // ECharts option
   }
   ```

---

### 3.6 会话管理与历史记录（优先级：P0）

**会话信息包含**：
- 会话ID、用户、创建时间、更新时间
- 消息历史（用户输入、Agent输出）
- 查询结果（SQL、数据、可视化配置）
- 执行状态（进行中/成功/失败）

**核心功能**：
1. **实时会话** - 创建、更新、持久化
2. **后台查询** - 关闭页面查询继续执行
3. **历史查看** - 支持回溯查询过程和结果
4. **会话搜索** - 按关键词、时间、查询类型搜索

**后端实现**：
```
- backend/models/conversation.py        # 会话ORM模型
- backend/repositories/conversation_repository.py
- backend/services/conversation_service.py
- backend/api/conversation_routes.py   # /api/conversations
```

**前端实现**：
```
- src/stores/conversationStore.ts      # 会话状态管理
- src/views/ConversationPage.vue       # 对话页面
- src/views/HistoryPage.vue            # 历史记录页面
```

**数据库表结构**：
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255),
    title VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    status ENUM('active', 'archived'),
    metadata JSON  -- 存储上下文信息
);

CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID,
    role ENUM('user', 'assistant'),
    content TEXT,
    tool_calls JSON,          -- 工具调用记录
    execution_time INTEGER,   -- ms
    created_at TIMESTAMP
);

CREATE TABLE query_results (
    id UUID PRIMARY KEY,
    conversation_id UUID,
    message_id UUID,
    result_type ENUM('sql', 'report', 'code', 'analysis'),
    result_data JSON,
    visualization_config JSON,
    created_at TIMESTAMP
);
```

---

## 4. 里程碑二：高级分析与协作功能

### 4.1 里程碑二预期效果

**完成后的核心能力**：
- 支持复杂的多步骤数据分析工作流
- 提供智能的意图识别和路由决策
- 用户可以收藏和分享分析结果
- 支持定时任务和批量数据处理

**用户体验提升**：
- 从简单查询升级到复杂分析工作流
- AI辅助的多步骤分析，自动拆解复杂任务
- 个性化的收藏管理和团队协作功能
- 自动化的定时报表和监控能力

**开发计划**：

---

### 4.2 意图识别与路由决策（优先级：P0）

**意图分类**：
```
用户查询
  ├─ 明细表查询 → 从报表中找合适的报表链接返回
  ├─ 复杂分析 → DeepAgent工作流
  └─ 普通查询 → Agent查询
      ├─ 从表字段检索
      ├─ 从报表检索
      └─ 选择最优查询路径 → 生成SQL/调用报表
```

**实现思路**：
1. **意图分类模型** - 基于LLM的零样本分类
   ```python
   intent_classifier = LLMChain(
       llm=llm,
       prompt=Intent classification template,
       output_parser=EnumOutputParser(Intent)
   )
   ```

2. **路由逻辑**
   ```python
   def route_query(intent: Intent, complexity: float):
       if intent == DetailedTableQuery:
           return find_report_link()
       elif complexity > THRESHOLD:
           return deep_agent_workflow()
       else:
           return normal_agent_workflow()
   ```

3. **查询路径选择** - 检索+排序
   ```python
   # 从表字段检索
   table_candidates = retrieval_tool.search(
       query, source='table_schema'
   )

   # 从报表检索
   report_candidates = retrieval_tool.search(
       query, source='reports'
   )

   # 合并+重排
   candidates = merge_and_rerank(
       table_candidates, report_candidates
   )

   # 生成SQL或返回报表链接
   best = candidates[0]
   if best.source == 'report':
       return {'type': 'report', 'link': best.link}
   else:
       return {'type': 'sql', 'query': generate_sql(best)}
   ```

**后端实现**：
```
- backend/services/nlquery_service/intent_classifier.py
- backend/services/nlquery_service/router.py
- backend/services/nlquery_service/query_path_selector.py
```

---

### 4.3 DeepAgent工作流（优先级：P1）

**工作流特点**：
- 多步骤分析任务
- 实时进度反馈（Todo列表）
- 支持代码执行Sandbox
- 步骤结果持久化
- 最终HTML汇总报告

**工作流步骤**：
```
1. 分析问题 → 生成任务清单 (Todo List)
   ├─ 子任务1：数据采集
   ├─ 子任务2：数据处理
   ├─ 子任务3：分析计算
   └─ 子任务4：结果展示

2. 逐步执行
   ├─ 每个步骤可能调用工具（SQL、报表、代码）
   ├─ 步骤结果保存到本地文件
   └─ 实时推送进度到前端

3. 汇总输出
   └─ 将所有步骤结果转换为HTML页面
```

**后端实现**：
```python
# backend/services/agents/deep_agent.py
class DeepAgent:
    def execute(self, query: str) -> AgentExecutionPlan:
        # 1. 分析问题，生成任务清单
        plan = self.analyze_and_plan(query)

        # 2. 逐步执行任务
        for step in plan.steps:
            result = self.execute_step(step)
            self.save_step_result(step.id, result)
            self.notify_progress(step.id, result.status)

        # 3. 生成HTML报告
        report = self.generate_html_report(plan)
        return report

# 步骤执行
class StepExecutor:
    def execute(self, step: WorkflowStep):
        if step.tool == 'sql':
            return self.execute_sql(step)
        elif step.tool == 'code':
            return self.execute_code(step)  # 使用Sandbox
        elif step.tool == 'report':
            return self.execute_report(step)

# 代码沙箱
class CodeSandbox:
    def execute(self, code: str, context: dict) -> dict:
        # 安全的代码执行环境
        # 支持numpy, pandas, matplotlib等
        pass
```

**前端实现**：
```typescript
// src/views/DeepAnalysisPage.vue
// 显示Todo列表和实时执行进度
// SSE监听后端进度更新
```

**数据存储**：
```
backend/data/deep_agent_sessions/
├── {session_id}/
│   ├── analysis_plan.json       # 分析计划
│   ├── step_results/
│   │   ├── step_1.json          # 步骤1结果
│   │   ├── step_2.json
│   │   └── ...
│   └── report.html              # 最终报告
```

---

### 4.4 收藏功能（优先级：P2）

**收藏内容**：
- SQL查询（保存SQL和参数）
- 报表查询（保存报表链接和参数）
- DeepAgent分析（保存分析计划）

**核心功能**：
1. **收藏保存** - 固化查询操作
2. **快速查询** - 点击收藏直接执行，修改日期等参数
3. **收藏管理** - 分类、搜索、编辑、删除

**后端实现**：
```
- backend/models/favorite.py
- backend/repositories/favorite_repository.py
- backend/services/favorite_service.py
- backend/api/favorite_routes.py
```

**前端实现**：
```
- src/components/FavoriteBar.vue
- src/views/FavoriteManagementPage.vue
- src/stores/favoriteStore.ts
```

**数据库表结构**：
```sql
CREATE TABLE favorites (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255),
    title VARCHAR(255),
    type ENUM('sql', 'report', 'deep_analysis'),
    content JSON,              -- 保存SQL、报表链接、分析计划
    parameters JSON,           -- 可变参数定义（日期范围、维度等）
    tags VARCHAR(255),         -- 标签，用于分类
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**JSON Content示例**：
```json
{
  "type": "sql",
  "query": "SELECT ... WHERE date >= ? AND region = ?",
  "parameters": [
    {"name": "start_date", "type": "date", "description": "开始日期"},
    {"name": "region", "type": "string", "description": "地区"}
  ],
  "description": "区域销售统计"
}
```

---

### 4.5 数据导出与分享（优先级：P2）

**功能描述**：
支持多种格式导出和分享链接，提升数据协作能力。

**核心功能**：
1. **多格式导出** - CSV、Excel、PDF、Parquet
2. **分享链接** - 生成临时或永久分享链接
3. **权限控制** - 设置分享链接的访问权限和有效期
4. **批量导出** - 支持多个查询结果打包导出

**后端实现**：
```python
class DataExporter:
    def export(self, result: QueryResult, format: str) -> bytes:
        if format == 'csv':
            return to_csv(result)
        elif format == 'excel':
            return to_excel(result)
        elif format == 'pdf':
            return to_pdf_report(result)
        elif format == 'parquet':
            return to_parquet(result)

class SharingManager:
    def create_share_link(self, query_result: str, expires_in: int = 7*24*3600):
        # 创建临时分享链接
        share_id = generate_id()
        self.store_shared_result(share_id, query_result, expires_in)
        return f"https://taosha.example.com/shared/{share_id}"

    def revoke_share(self, share_id: str):
        # 撤销分享
        pass
```

**前端功能**：
- 导出按钮（CSV、Excel、PDF）
- 分享按钮，生成可复制的链接
- 分享设置（过期时间、权限）

**数据库表结构**：
```sql
CREATE TABLE shared_results (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255),
    share_token VARCHAR(255) UNIQUE,
    title VARCHAR(255),
    result_data JSON,
    access_count INTEGER DEFAULT 0,
    max_access INTEGER,
    expires_at TIMESTAMP,
    created_at TIMESTAMP
);
```

---

### 4.6 定时报表任务（优先级：P2）

**功能描述**：
支持用户创建定时报表任务，自动执行查询并发送结果。

**核心功能**：
1. **任务调度** - 支持Cron表达式定义执行时间
2. **查询执行** - 按计划自动执行SQL查询或报表调用
3. **结果推送** - 通过邮件、Webhook等方式发送结果
4. **任务监控** - 监控任务执行状态和结果

**后端实现**：
```python
class ScheduledTaskService:
    def create_task(self, task: ScheduledTask) -> str:
        # 创建定时任务
        task_id = generate_id()
        self.scheduler.add_job(
            func=self.execute_scheduled_query,
            trigger=CronTrigger.from_crontab(task.cron_expression),
            args=[task_id],
            id=task_id
        )
        return task_id

    def execute_scheduled_query(self, task_id: str):
        # 执行定时查询
        task = self.get_task(task_id)
        result = self.query_engine.execute(task.query)

        # 发送结果
        self.send_result(task, result)

class NotificationService:
    def send_result(self, task: ScheduledTask, result: QueryResult):
        if task.notification_type == 'email':
            self.send_email(task.recipient, result)
        elif task.notification_type == 'webhook':
            self.send_webhook(task.webhook_url, result)
```

**前端实现**：
```
- src/components/tasks/ScheduledTaskForm.vue
- src/views/TaskManagementPage.vue
- src/stores/taskStore.ts
```

**数据库表结构**：
```sql
CREATE TABLE scheduled_tasks (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255),
    title VARCHAR(255),
    type ENUM('sql', 'report', 'deep_analysis'),
    query_content JSON,
    cron_expression VARCHAR(100),
    notification_type ENUM('email', 'webhook', 'in_app'),
    recipient_info JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE task_executions (
    id UUID PRIMARY KEY,
    task_id UUID,
    status ENUM('running', 'completed', 'failed'),
    result_data JSON,
    error_message TEXT,
    execution_time INTEGER,
    created_at TIMESTAMP
);
```
