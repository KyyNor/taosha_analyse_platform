# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

**淘沙分析平台** 是一个 AI 驱动的商业智能平台，主要包含两大核心模块：

1. **智能体对话系统** - 基于 LangChain/LangGraph 的对话式 AI 分析助手
2. **FraudHunter 猎诈风控系统** - 企业级实时风控反诈平台

**技术栈：**
- **后端**: FastAPI + LangChain + LangGraph + SQLAlchemy 2.0 + DuckDB/Spark
- **前端**: Next.js 14 (App Router) + React 18 + Tailwind CSS + Radix UI + Vercel AI SDK
- **数据库**: MySQL (元数据) + DuckDB (OLAP) + Qdrant (向量存储)
- **消息队列**: Kafka (实时数据消费)
- **任务调度**: APScheduler (定时任务) + DeepAgents (异步任务执行)

## 开发命令

### 环境准备

```bash
# 后端依赖管理（使用 uv）
uv sync

# 前端依赖管理
cd frontend && npm install
```

### 启动服务

```bash
# 启动后端 (端口 50020)
./sbackend.sh
# 或手动启动: cd backend && uv run uvicorn main:app --workers=2 --port=50020

# 启动前端 (端口 50011)
./sfrontend.sh
# 或手动启动: cd frontend && npm run dev
```

### 其他常用命令

```bash
# 前端构建
npm run build

# 前端代码检查
npm run lint

# 图表组件打包
npm run build:charts

# 生成测试Token
python scripts/generate_token.py --user-id "test001" --user-name "测试用户" --branch-no "DEPT001" --branch-name "技术部" --role-id-list "淘沙管理员" --expire-hours 24
```

## 核心架构

### 后端架构

**启动流程** (`backend/main.py`):
```
启动锁保护 (.startup_lock)
→ Playwright浏览器初始化 (每个worker)
→ 查询引擎初始化 (每个worker)
→ 可观测服务初始化 (每个worker)
→ 数据库表创建和页面同步 (每个worker)
→ 统一调度服务启动 (仅一个worker)
→ DeepAgents任务执行器启动 (每个worker)
→ 实时数据消费者启动 (仅一个worker，可选)
```

**关键设计：**
- **多worker同步**: 使用 `.startup_lock` 文件锁确保系统服务只初始化一次
- **统一调度服务**: 基于 APScheduler 的定时任务管理
  - 离线宽表同步 (`offline_wide_table_sync`)
  - 实时指标生成 (`generate_realtime_wide_table_job`)
  - 元数据同步 (`metadata_sync`)
  - FineReport报表同步 (`fine_report_sync`)
  - 向量数据库训练 (`vector_training`)
  - 实时数据清理 (`realtime_data_cleanup`)
  - Parquet文件清理 (`parquet_file_cleanup`)
- **数据库会话管理**: 使用依赖注入 `db: Session = Depends(get_db)` 或上下文管理器 `with get_db_session() as db`

**目录结构：**
```
backend/
├── api/                    # API路由层
│   ├── agents_routes.py           # 智能体对话
│   ├── deepagents_routes.py       # DeepAgents任务执行
│   ├── metadata_routes.py         # 元数据管理
│   ├── entity_routes.py           # 实体管理
│   ├── permission_routes.py       # 权限管理
│   ├── user_routes.py             # 用户管理
│   └── fraudhunter/               # 猎诈系统API
│       ├── indicator_routes.py           # 指标定义
│       ├── indicator_task_routes.py     # 指标任务
│       ├── indicator_query_routes.py     # 指标查询
│       ├── model_routes.py             # 风控模型（规则引擎）
│       ├── wide_table_routes.py        # 宽表版本
│       ├── alert_control_record_routes.py  # 告警记录
│       ├── system_config_routes.py       # 系统配置
│       └── dry_run_task_routes.py        # 任务干运行
├── services/               # 业务逻辑层
│   ├── agents/             # 智能体服务
│   │   ├── agent_service.py         # LangChain Agent主服务
│   │   ├── deepagents/              # DeepAgents多智能体编排
│   │   │   ├── deepagents_runner.py      # 任务执行器
│   │   │   ├── multi_agent_pipeline.py    # 多智能体流水线
│   │   │   ├── question_proposer_agent.py # 问题提出智能体
│   │   │   ├── data_analyser_agent.py     # 数据分析智能体
│   │   │   └── scorer_agent.py            # 评分智能体
│   │   ├── tools/                   # LangChain工具集
│   │   │   ├── sql_tool.py              # SQL查询工具
│   │   │   ├── table_tool.py            # 表格数据工具
│   │   │   ├── chart_tool.py            # 图表生成工具
│   │   │   └── fine_report_tools.py      # FineReport集成工具
│   │   └── db_checkpoint_saver.py    # 聊天历史检查点存储
│   ├── fraudhunter/        # 猎诈业务服务
│   │   ├── indicator_service/       # 指标管理
│   │   │   ├── indicator_manager.py         # 指标CRUD
│   │   │   ├── indicator_task_manager.py    # 指标任务管理
│   │   │   ├── sql_validator.py            # SQL验证器
│   │   │   └── indicator_query_service.py  # 指标查询服务
│   │   ├── model_service/           # 风控模型和规则引擎
│   │   │   ├── rule_engine.py             # 规则引擎 v2.1.0
│   │   │   ├── model_executor.py          # 模型执行器
│   │   │   ├── realtime_consumer.py       # Kafka实时数据消费
│   │   │   ├── duckdb_analyze_pool.py     # DuckDB分析池
│   │   │   └── risk_control_model_manager.py
│   │   ├── wide_table_service/      # 宽表同步
│   │   │   ├── sync_service.py            # 宽表同步服务
│   │   │   └── version_manager.py         # 版本管理器
│   │   ├── dry_run_task_service/    # 任务验证服务
│   │   └── system_config_service.py # 系统配置管理
│   ├── query_engine/       # 查询引擎抽象
│   │   ├── base.py                  # 查询引擎基类
│   │   ├── duckdb_service.py        # DuckDB实现
│   │   ├── spark_service.py         # Spark实现
│   │   └── empty_engine_service.py  # 降级实现
│   ├── llm_service/        # LLM服务抽象
│   ├── metadata_service/   # 元数据管理
│   ├── scheduler/          # 统一调度服务
│   │   ├── scheduler_service.py     # APScheduler封装
│   │   └── jobs/                    # 定时任务实现
│   ├── vector_store/       # Qdrant向量存储
│   ├── tracking_service/   # 可观测性服务 (Langfuse)
│   └── token_service.py    # JWT Token服务
├── models/                 # SQLAlchemy ORM模型
│   ├── db_base.py               # 数据库连接和会话管理
│   ├── agent_chat_models.py     # Agent聊天历史
│   ├── metadata_models.py       # 元数据模型
│   ├── permission_models.py     # 权限角色模型
│   └── fraudhunter/             # 猎诈数据模型
│       ├── indicator.py              # 指标定义和任务
│       ├── wide_table.py             # 宽表版本和快照
│       ├── risk_control_model.py     # 风控模型和规则
│       ├── dry_run_task.py           # 任务验证模型
│       └── model_execution_tracking.py
├── repositories/           # 数据访问层
├── middleware/             # 中间件
│   └── auth_middleware.py       # 认证中间件
├── schemas/                # Pydantic验证模型
├── utils/                  # 工具类
│   ├── config.py                # YAML配置管理
│   └── logger.py                # Loguru日志
└── config/                 # 配置文件
    ├── config.yaml              # 主配置文件
    └── pages.yaml               # 页面配置
```

### FraudHunter 核心业务逻辑

**四层架构：**
```
指标层 (Indicator) → 宽表层 (Wide Table) → 模型层 (Model) → 告警层 (Alert)
```

1. **指标层** (`indicator_service/`)
   - 指标定义：支持多种数据类型 (integer/float/string/date/enum/boolean)
   - 指标任务：SQL生成、版本管理、上线发布、数据预览

2. **宽表层** (`wide_table_service/`)
   - **双版本机制**：离线宽表 (T+1 Parquet) + 实时宽表 (Kafka增量)
   - 版本管理：版本号、版本哈希、快照追踪
   - 智能降级：实时宽表异常时自动降级到离线宽表

3. **模型层** (`model_service/`)
   - **规则引擎 v2.1.0** (`rule_engine.py`): 可视化规则配置转SQL
     - 支持多层嵌套规则组 (AND/OR逻辑)
     - 支持值表达式: 常量值、指标引用、时间函数、数学函数
     - DuckDB `list_filter` 批量匹配
     - Spark SQL 离线计算
   - **回测系统**: 历史数据验证、结果导出
   - **实时任务**: Kafka消费、DuckDB加工、模型匹配、告警生成

4. **告警层** (`alert_control_record_routes.py`)
   - 命中记录生成、告警管控追踪、Excel导出

**实时处理链路：**
```
Kafka Canal数据 → RealtimeDataConsumer (DuckDB加工)
→ 定时任务 (generate_realtime_wide_table_job)
→ 实时指标计算 + LEFT JOIN离线宽表 → 规则引擎匹配 → 告警生成
```

### 前端架构

**目录结构：**
```
frontend/
├── app/                    # Next.js App Router
│   ├── layout.tsx               # 根布局
│   ├── (main)/                  # 路由组 - 主应用内容
│   │   ├── layout.tsx               # 主布局 (Header)
│   │   ├── info/                   # 登录页
│   │   ├── agent/                  # 智能体对话界面
│   │   ├── deepagents/             # DeepAgents任务界面
│   │   │   ├── page.tsx                # 任务列表
│   │   │   └── [sessionId]/           # 任务详情
│   │   ├── metadata/               # 元数据管理
│   │   │   ├── relations/              # 数据关系
│   │   │   ├── glossary/               # 业务术语
│   │   │   ├── fine-reports/           # FineReport集成
│   │   │   └── prompt-templates/       # 提示词模板
│   │   ├── fraudhunter/            # 猎诈系统页面
│   │   │   ├── indicators/             # 指标管理
│   │   │   ├── indicator-tasks/        # 指标任务
│   │   │   ├── indicator-query/        # 指标查询
│   │   │   ├── risk-control-models/    # 风控模型
│   │   │   ├── wide-table-versions/    # 宽表版本
│   │   │   ├── alert-control-records/  # 告警记录
│   │   │   ├── dry-run/                # 模型测试
│   │   │   └── system-config/          # 系统配置
│   │   └── admin/                  # 管理员页面
│   │       ├── departments/            # 部门管理
│   │       ├── roles/                  # 角色管理
│   │       ├── permissions/            # 权限管理
│   │       └── login-records/          # 登录记录
│   └── not-found.tsx           # 404页面
├── components/             # React组件
│   ├── ui/                      # Radix UI基础组件 (shadcn/ui)
│   ├── agent/                   # 智能体组件
│   │   ├── ChatInput.tsx            # 聊天输入
│   │   ├── ChatMessagesArea.tsx     # 消息展示
│   │   ├── ChatSidebar.tsx          # 会话侧边栏
│   │   ├── GenerativeUIRenderer.tsx # 动态UI渲染
│   │   └── MarkdownBlock.tsx        # Markdown渲染
│   ├── fraudhunter/             # 猎诈业务组件
│   │   └── model/
│   │       ├── RuleBuilder.tsx         # 可视化规则构建器
│   │       ├── ConditionRuleEditor.tsx # 条件规则编辑器
│   │       ├── IndicatorCombobox.tsx   # 指标选择器
│   │       └── RuleImportExport.tsx    # 规则导入导出
│   ├── generative_ui/           # AI工具结果动态UI组件
│   │   ├── Table.tsx                # 数据表格
│   │   ├── BarChart.tsx             # 柱状图
│   │   ├── LineChart.tsx            # 折线图
│   │   ├── PieChart.tsx             # 饼图
│   │   ├── TreemapChart.tsx         # 矩形树图
│   │   ├── TodoList.tsx             # 任务列表
│   │   └── ToolResult.tsx           # 工具结果渲染器
│   └── layout/                  # 布局组件
│       └── Header.tsx              # 主导航头
└── lib/                    # 工具和服务
    ├── api.ts                   # Axios配置 (拦截器、错误处理)
    ├── services/                # API服务层
    │   ├── agentService.ts         # Agent对话API (SSE流式)
    │   ├── deepagentsService.ts    # DeepAgents任务API
    │   ├── fraudhunterService.ts   # FraudHunter API
    │   ├── fraudhunter/            # FraudHunter子模块
    │   └── metadataService.ts      # 元数据API
    ├── state/                   # React Context状态管理
    │   ├── agent.tsx               # Agent状态 (流式、历史)
    │   ├── app.tsx                 # 全局状态
    │   └── theme.tsx               # 主题状态
    └── utils/                   # 工具函数
        ├── formatUtils.ts          # 格式化工具
        └── downloadUtils.ts        # 下载工具
```

**API集成：**
- 基础路径: `/api/taosha/v1` (通过 Next.js 重写代理到后端 50020)
- 前端basePath: `/taosha`
- 流式端点: `POST /agents/chat/stream` (服务器发送事件 SSE)
- Token优先级: URL参数 → Cookie → Header

## 配置管理

**后端配置** (`backend/config/config.yaml`):
- 应用设置: `app.workers`, `app.debug`
- 数据库: `taosha_db.mysql.*`
- 查询引擎: `query_engine.service_type` (duckdb/spark)
- PySpark: `pyspark.*` (大数据处理)
- LLM: `openai.*`, `qwen.*`, `localai.*`
- 向量存储: `qdrant.*`
- 调度: `scheduler.*`
- FraudHunter: `fraudhunter_realtime_data_enabled`, `fraudhunter_wide_table.*`
- Kafka: `kafka.*`

**前端环境变量** (`.env.local`):
```
NEXT_PUBLIC_API_BASE=/api/taosha/v1
```

**前端配置** (`next.config.mjs`):
- basePath: `/taosha`
- API重写: `/api/*` → `http://localhost:50020/api/*`

## 重要实现细节

### 多Worker环境启动锁

位于 `backend/main.py:_acquire_startup_lock()`，使用文件锁 (`.startup_lock`) 确保在多worker环境下只有一个进程执行：
- 向量数据库训练
- 元数据同步
- 统一调度服务启动
- 实时数据消费者启动

锁文件包含 PID 和时间戳，10分钟过期机制。

### 数据库会话管理模式

```python
# FastAPI依赖注入模式（推荐用于API路由）
async def endpoint_handler(
    db: Session = Depends(get_db)  # 自动提交/回滚
):
    pass

# 上下文管理器模式（用于后台任务）
with get_db_session() as db:
    pass  # 自动提交/回滚
```

### 规则引擎SQL生成

规则引擎位于 `backend/services/fraudhunter/model_service/rule_engine.py`，支持：
- **值表达式类型**: 常量值、指标引用、时间函数、数学函数
- **运算符**: 等于、不等于、大于、小于、包含、正则匹配等
- **逻辑运算**: AND/OR 嵌套规则组
- **SQL生成**: DuckDB `list_filter` 批量匹配、Spark SQL 离线计算

### 流式架构

**后端**:
- 使用 SSE (Server-Sent Events) 进行实时token流
- 事件类型: `text`, `tool_call`, `tool_result`
- Agent服务: `agent_service.py`

**前端**:
- 使用 Vercel AI SDK 兼容的事件格式
- 状态管理: `lib/state/agent.tsx`
- AbortController 支持请求取消

### DeepAgents多智能体编排

位于 `backend/services/agents/deepagents/`:
- **deepagents_runner.py**: 任务执行器，管理智能体生命周期
- **multi_agent_pipeline.py**: 多智能体流水线编排
- **question_proposer_agent.py**: 问题提出智能体
- **data_analyser_agent.py**: 数据分析智能体
- **scorer_agent.py**: 结果评分智能体

支持Docker执行策略和自定义执行策略。

## 调试技巧

### 后端调试

- **日志**: 使用 Loguru 结构化日志，日志文件位于 `backend/logs/`
- **追踪**: 集成 Langfuse 进行LLM调用追踪
- **API文档**: FastAPI自动生成Swagger UI `http://localhost:50020/docs`

### 前端调试

- **网络面板**: 查看SSE事件流和API请求
- **React DevTools**: 调试组件状态和Context
- **构建错误**: 使用 `npm run lint` 检查代码问题

## 关键技术点

| 技术 | 用途 |
|------|------|
| FastAPI | 后端REST API框架 |
| LangChain/LangGraph | LLM编排和工作流 |
| SQLAlchemy 2.0 | ORM数据库操作 |
| DuckDB | 本地OLAP查询引擎 |
| PySpark | 大数据处理（可选） |
| Qdrant | 向量数据库RAG |
| Playwright | 浏览器自动化（FineReport集成） |
| APScheduler | 定时任务调度 |
| Kafka | 实时数据消费 |
| DeepAgents | 多智能体任务编排 |
| Next.js 14 | 前端框架 (App Router) |
| Vercel AI SDK | 流式AI UI |
| Tailwind CSS | 样式系统 |
| Radix UI | 无头UI组件库 |
| shadcn/ui | UI组件基础 |

## 常见任务

### 添加新的Agent工具

1. 在 `backend/services/agents/tools/` 创建工具函数
2. 继承 LangChain `BaseTool` 或使用 `@tool` 装饰器
3. 在 `agent_service.py` 的工具列表中注册
4. 如需前端UI渲染，在 `frontend/components/generative_ui/` 添加对应组件

### 修改FraudHunter规则

1. 前端使用 `RuleBuilder.tsx` 可视化配置规则
2. 后端 `rule_engine.py` 将规则配置编译为SQL
3. 回测验证: 调用模型回测API测试历史数据
4. 上线发布: 模型状态 → online

### 数据库迁移

- 当前不使用 Alembic
- 直接修改 `models/` 中的模型类
- SQLAlchemy 2.0 支持自动模式更新（开发环境）

### 添加新的定时任务

在 `backend/main.py:_initialize_system_services()` 中注册：
```python
scheduler_service.add_interval_job(
    func=your_job_function,
    seconds=interval,
    job_id='unique_job_id',
    job_name='任务名称'
)
```

### 添加新的DeepAgents智能体

1. 在 `backend/services/agents/deepagents/` 创建智能体类
2. 在 `multi_agent_pipeline.py` 中注册智能体
3. 定义智能体间的依赖关系和数据流
4. 在前端添加对应的任务界面

## PySpark环境配置

使用PySpark前提条件：
1. 新建bdspk用户，bigdata组
2. 拷贝spark目录到执行脚本的机器
3. 添加环境变量到 `~/.bashrc`:
```bash
export SPARK_HOME=/data/spark-3.1.3-bin-hadoop3.2
export HADOOP_CONF_DIR=$SPARK_HOME/conf
export HIVE_CONF_DIR=$SPARK_HOME/conf
export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-*.zip:$PYTHONPATH
```
4. 拷贝jdk8到 `~/jdk8` 目录
5. 注意：主机名不能有下划线
