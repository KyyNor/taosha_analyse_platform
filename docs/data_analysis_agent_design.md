# 数据分析Agent系统 - 概要设计文档

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

## 3. 功能详细设计

### 3.1 数据分析工具集（优先级：P0）

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

**技术方案**：
```
后端：
- backend/services/tools/
  ├── spark_tool.py           # Spark查询
  ├── mysql_tool.py           # MySQL查询
  ├── report_tool.py          # 报表查询（Playwright）
  └── retrieval_tool.py       # 信息检索
```

---

### 3.2 多模态信息检索（优先级：P0）

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

**实现思路**：
```
后端：
- backend/services/retrieval_service/
  ├── text_processor.py       # 分词、同义词扩展
  ├── full_text_search.py     # 全文检索
  ├── vector_search.py        # 向量检索
  └── reranker.py             # 智能重排
```

---

### 3.3 报表元数据配置管理（优先级：P0）

**元数据包含**：
- 报表名称、链接、类型（汇总表/明细表）
- 报表说明、适用场景、参数定义
- 字段映射（报表字段 → 数据库字段）
- 访问权限、更新频率

**功能需求**：
1. **配置页面** - CRUD操作，支持批量导入
2. **知识库训练** - 报表信息加入向量库用于检索
3. **参数管理** - 支持动态参数定义（日期、维度、指标）

**实现思路**：
```
后端：
- 扩展现有 metadata_service
  ├── report_repository.py    # 报表CRUD
  ├── report_metadata_sync.py # 报表信息同步到向量库

前端：
- src/components/metadata/ReportConfigForm.vue      # 报表配置表单
- src/components/metadata/ReportImportModal.vue     # 批量导入
- src/views/MetadataReportPage.vue                  # 报表管理页面
```

---

### 3.4 Generative UI - 动态可视化组件（优先级：P1）

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

### 3.5 会话管理与历史记录（优先级：P0）

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

**实现思路**：
```
后端：
- backend/models/conversation.py        # 会话ORM模型
- backend/repositories/conversation_repository.py
- backend/services/conversation_service.py
- backend/api/conversation_routes.py   # /api/conversations

前端：
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

### 3.6 意图识别与路由决策（优先级：P0）

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

### 3.7 DeepAgent工作流（优先级：P1）

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

**实现思路**：

**后端**：
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

**前端**：
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

### 3.8 收藏功能（优先级：P2）

**收藏内容**：
- SQL查询（保存SQL和参数）
- 报表查询（保存报表链接和参数）
- DeepAgent分析（保存分析计划）

**核心功能**：
1. **收藏保存** - 固化查询操作
2. **快速查询** - 点击收藏直接执行，修改日期等参数
3. **收藏管理** - 分类、搜索、编辑、删除

**实现思路**：
```
后端：
- backend/models/favorite.py
- backend/repositories/favorite_repository.py
- backend/services/favorite_service.py
- backend/api/favorite_routes.py

前端：
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

## 4. 后端架构设计

### 4.1 服务架构（按优先级）

| 优先级 | 服务模块 | 功能 | 依赖 |
|------|--------|------|------|
| **P0** | agent_service | Agent编排和工作流 | LangGraph, LLM |
| **P0** | intent_classifier | 意图识别 | LLM, retrieval_service |
| **P0** | retrieval_service | 多模态检索 | Qdrant, DuckDB FTS |
| **P0** | conversation_service | 会话管理 | DB |
| **P0** | tools/* | 数据分析工具集 | query_engine, report_tool |
| **P1** | deep_agent_service | 多步骤分析工作流 | agent_service, sandbox |
| **P1** | report_config_service | 报表配置管理 | metadata_service |
| **P1** | code_sandbox | 代码执行沙箱 | RestrictedPython |
| **P2** | favorite_service | 收藏管理 | conversation_service |

### 4.2 API路由设计

```
/api/taosha/v1/
├── /agent
│   ├── POST /chat              # 发送查询
│   ├── GET /chat/{conv_id}     # 获取对话
│   └── POST /chat/{msg_id}/clarify  # 澄清
│
├── /conversations
│   ├── GET /                   # 列出会话
│   ├── GET /{id}               # 获取会话
│   ├── DELETE /{id}            # 删除会话
│   └── POST /{id}/archive      # 归档
│
├── /metadata/reports
│   ├── GET /                   # 列表
│   ├── POST /                  # 创建
│   ├── PUT /{id}               # 更新
│   ├── DELETE /{id}            # 删除
│   └── POST /import            # 批量导入
│
├── /favorites
│   ├── GET /                   # 列表
│   ├── POST /                  # 创建
│   ├── PUT /{id}               # 更新
│   ├── DELETE /{id}            # 删除
│   └── POST /{id}/execute      # 执行收藏
│
└── /deep-analysis
    ├── POST /analyze           # 启动分析
    ├── GET /{session_id}       # 获取进度
    └── GET /{session_id}/report # 获取报告
```

### 4.3 关键工作流设计

**普通Agent查询工作流**：
```python
@router.post("/agent/chat")
async def agent_chat(request: ChatRequest):
    # 1. 意图识别
    intent = intent_classifier.classify(request.query)

    # 2. 路由决策
    if intent == DetailedTableQuery:
        result = find_report_link(request.query)
    else:
        # 3. 检索候选
        candidates = retrieval_service.search(request.query)

        # 4. Agent执行
        result = agent_service.execute(
            request.query,
            candidates,
            tools=[sql_tool, report_tool, retrieval_tool]
        )

    # 5. 保存会话
    save_conversation(request.session_id, result)

    # 6. 返回结果
    return format_response(result)
```

**DeepAgent工作流**：
```python
@router.post("/deep-analysis/analyze")
async def deep_analyze(request: AnalysisRequest):
    # 1. 分析问题，生成计划
    plan = deep_agent.analyze_and_plan(request.query)
    session_id = create_session()
    save_plan(session_id, plan)

    # 2. 后台执行
    asyncio.create_task(
        execute_analysis_in_background(session_id, plan)
    )

    # 3. 立即返回
    return {"session_id": session_id, "plan": plan}

async def execute_analysis_in_background(session_id, plan):
    for step in plan.steps:
        result = execute_step(step)
        save_step_result(session_id, step.id, result)

        # 推送进度到前端
        notify_progress(session_id, step.id, result.status)

    # 生成报告
    report = generate_html_report(session_id, plan)
    save_report(session_id, report)
```

---

## 5. 前端架构设计

### 5.1 页面结构（按优先级）

| 优先级 | 页面 | 功能 | 依赖组件 |
|------|------|------|--------|
| **P0** | ConversationPage | 主聊天界面 | ChatInput, MessageList, GenerativeUI |
| **P0** | HistoryPage | 会话历史管理 | ConversationList, ConversationSearch |
| **P1** | MetadataReportPage | 报表配置管理 | ReportConfigForm, ReportTable |
| **P1** | DeepAnalysisPage | 分析进度展示 | TodoList, StepProgress, ReportViewer |
| **P2** | FavoriteManagementPage | 收藏管理 | FavoriteList, FavoriteForm |

### 5.2 核心组件

```
src/components/
├── chat/
│   ├── ChatInput.vue              # 输入框
│   ├── MessageList.vue            # 消息列表
│   ├── ClarificationDialog.vue    # 澄清对话
│   └── StreamingMessage.vue       # 流式消息
│
├── charts/
│   ├── LineChart.vue              # 折线图
│   ├── BarChart.vue               # 柱状图
│   ├── PieChart.vue               # 饼图
│   ├── TreeChart.vue              # 树图
│   └── ComparisonTable.vue        # 对比表
│
├── workflow/
│   ├── TodoList.vue               # 任务清单
│   ├── StepProgress.vue           # 步骤进度
│   └── CodeBlockViewer.vue        # 代码查看
│
├── metadata/
│   ├── ReportConfigForm.vue       # 报表配置表单
│   ├── ReportImportModal.vue      # 批量导入
│   └── ReportTable.vue            # 报表列表
│
└── favorites/
    ├── FavoriteBar.vue            # 快捷栏
    ├── FavoriteList.vue           # 列表
    └── FavoriteForm.vue           # 编辑表单
```

### 5.3 状态管理（Pinia）

```typescript
// src/stores/
├── agentStore.ts                  # Agent状态
├── conversationStore.ts           # 会话状态
├── metadataStore.ts               # 元数据状态
├── deepAnalysisStore.ts           # 分析状态
└── favoriteStore.ts               # 收藏状态
```

### 5.4 API服务层

```typescript
// src/services/api/
├── agentService.ts                # Agent API
├── conversationService.ts         # 会话 API
├── metadataService.ts             # 元数据 API
├── deepAnalysisService.ts         # 分析 API
└── favoriteService.ts             # 收藏 API
```

---

## 6. 实现优先级与时间轴

### Phase 1: 基础Agent框架（2-3周）
**优先级：P0**

- [ ] 扩展Agent服务支持工具调用
- [ ] 实现意图识别
- [ ] 会话管理基础功能
- [ ] 基础聊天页面

**交付**：能处理简单SQL查询和报表查询

---

### Phase 2: 信息检索与报表配置（1-2周）
**优先级：P0**

- [ ] 多模态信息检索服务
- [ ] 报表元数据配置页面
- [ ] 检索集成到Agent
- [ ] 历史记录页面

**交付**：支持从元数据检索和报表管理

---

### Phase 3: Generative UI（1-2周）
**优先级：P1**

- [ ] 组件库实现（饼图、折线图、柱状图、树图、表格）
- [ ] Agent决策图表类型的逻辑
- [ ] 前端集成可视化组件

**交付**：查询结果自动可视化

---

### Phase 4: DeepAgent工作流（2-3周）
**优先级：P1**

- [ ] 工作流编排引擎
- [ ] 代码Sandbox实现
- [ ] 步骤执行和结果持久化
- [ ] HTML报告生成
- [ ] 前端进度展示（Todo列表）

**交付**：支持多步骤复杂分析

---

### Phase 5: 收藏与优化（1周）
**优先级：P2**

- [ ] 收藏功能实现
- [ ] 性能优化
- [ ] 完整测试

**交付**：用户可收藏和快速查询

---

## 7. 技术栈与依赖

### 后端
- **框架**：FastAPI, LangGraph
- **LLM**：OpenAI/Kimi
- **向量库**：Qdrant
- **查询引擎**：Spark SQL, MySQL, DuckDB
- **检索**：DuckDB FTS, Qdrant
- **代码执行**：RestrictedPython, IPython
- **自动化**：Playwright

### 前端
- **框架**：Vue 3 + TypeScript
- **状态管理**：Pinia
- **图表库**：ECharts, AntV G2
- **通信**：Axios, EventSource (SSE)
- **UI组件**：DaisyUI

---

## 8. 数据安全与权限考虑

1. **权限控制** - API层验证用户权限，限制数据库访问范围
2. **代码沙箱** - 使用RestrictedPython限制代码执行权限
3. **查询审计** - 记录所有查询和执行结果
4. **敏感信息处理** - 日志脱敏，不保存完整SQL中的敏感字段值

---

## 9. 关键技术细节

### 会话实时更新
- **前端**：SSE (Server-Sent Events) 监听 `/api/agent/chat/{conv_id}/stream`
- **后端**：Agent执行过程中实时推送进度和结果

### 后台查询不中断
- 查询执行用独立异步任务，不阻塞API响应
- 前端可关闭页面，通过历史页面查看执行结果

### 代码Sandbox
```python
# 使用RestrictedPython + IPython的内核
# 安全的命名空间：numpy, pandas, matplotlib
# 禁止：os.system, open(), import等危险操作
```

---

## 10. 后续扩展方向

1. **查询成本估算** - 执行前评估查询复杂度
2. **字段级血缘追踪** - 记录数据转换过程
3. **查询建议引擎** - 基于历史提供优化建议
4. **批量任务队列** - 支持用户提交多个任务后台执行
5. **数据导出增强** - 支持多格式导出（CSV、Excel、PDF）
6. **行级安全（RLS）** - 多租户和权限管理

---

## 11. 风险和缓解方案

| 风险 | 影响 | 缓解方案 |
|-----|------|--------|
| LLM API调用成本高 | 经济成本 | 缓存热查询，使用本地模型fallback |
| 复杂查询生成SQL错误 | 数据准确性 | 加强验证工具，人工审核 |
| 代码沙箱的安全漏洞 | 系统安全 | 使用RestrictedPython, 白名单库 |
| 并发查询性能下降 | 用户体验 | Spark集群化，查询结果缓存 |
| 历史记录数据量爆炸 | 存储成本 | 定时归档，数据压缩 |

---

## 附录：核心数据结构

```typescript
// 查询请求
interface AgentQuery {
  conversation_id: string
  query: string
  context?: Record<string, any>
}

// Agent响应
interface AgentResponse {
  message: string
  result_type: 'sql' | 'report' | 'chart' | 'code' | 'analysis'
  data?: any
  visualization?: ChartConfig
  tools_used?: ToolCall[]
  execution_time: number
}

// 图表配置
interface ChartConfig {
  type: 'line' | 'bar' | 'pie' | 'tree' | 'table'
  title: string
  data: any[]
  options?: any  // ECharts options
}

// 工作流计划
interface AgentExecutionPlan {
  id: string
  title: string
  steps: WorkflowStep[]
  estimated_duration: number
}

interface WorkflowStep {
  id: string
  title: string
  description: string
  tool: 'sql' | 'code' | 'report' | 'retrieval'
  input: any
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: any
  execution_time?: number
}
```

