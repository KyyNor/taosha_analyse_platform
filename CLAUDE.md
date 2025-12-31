# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

**淘沙分析平台** 是一个 AI 驱动的商业智能平台，主要包含两大核心模块：

1. **智能体对话系统** - 基于 LangChain/LangGraph 的对话式 AI 分析助手
2. **FraudHunter 猎诈风控系统** - 企业级实时风控反诈平台

**技术栈：**
- **后端**: FastAPI + LangChain + LangGraph + SQLAlchemy 2.0 + DuckDB/Spark
- **前端**: Next.js 14 + React 18 + Tailwind CSS + Radix UI + Vercel AI SDK
- **数据库**: MySQL (元数据) + DuckDB (OLAP) + Qdrant (向量存储)

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
```

## 核心架构

### 后端架构

**启动流程** (`backend/main.py`):
```
启动锁保护 → PySpark初始化 → Playwright浏览器初始化
→ 查询引擎初始化 → 可观测服务初始化 → 统一调度服务启动
→ DeepAgents任务执行器启动 → Agent服务启动
```

**关键设计：**
- **多worker同步**: 使用 `.startup_lock` 文件锁确保系统服务只初始化一次
- **统一调度服务**: 基于 APScheduler 的定时任务管理（离线宽表同步、实时指标生成、元数据同步等）
- **数据库会话管理**: 使用依赖注入 `db: Session = Depends(get_db)`，自动提交/回滚

**目录结构：**
```
backend/
├── api/                    # API路由层
│   ├── agents_routes.py           # 智能体对话
│   ├── deepagents_routes.py       # DeepAgents任务执行
│   ├── metadata_routes.py         # 元数据管理
│   └── fraudhunter/               # 猎诈系统API
│       ├── indicator_routes.py           # 指标定义
│       ├── indicator_task_routes.py     # 指标任务
│       ├── model_routes.py             # 风控模型（规则引擎）
│       ├── wide_table_routes.py        # 宽表版本
│       └── alert_control_record_routes.py  # 告警记录
├── services/               # 业务逻辑层
│   ├── agents/             # 智能体服务 (agent_service.py)
│   ├── fraudhunter/        # 猎诈业务服务
│   │   ├── indicator_service/     # 指标管理
│   │   ├── model_service/         # 风控模型和规则引擎
│   │   └── wide_table_service/    # 宽表同步
│   ├── query_engine/       # 查询引擎 (DuckDB/Spark)
│   ├── llm_service/        # LLM服务抽象
│   ├── metadata_service/   # 元数据管理
│   ├── scheduler/          # 统一调度服务
│   └── vector_store/       # Qdrant向量存储
├── models/                 # SQLAlchemy ORM模型
│   ├── db_base.py               # 数据库连接和会话管理
│   └── fraudhunter/             # 猎诈数据模型
├── repositories/           # 数据访问层
└── utils/                  # 工具类
    ├── config.py                # YAML配置管理
    └── logger.py                # Loguru日志
```

### FraudHunter 核心业务逻辑

**四层架构：**
```
指标层 → 宽表层 → 模型层 → 告警层
```

1. **指标层** (`indicator_service/`)
   - 指标定义：支持多种数据类型 (integer/float/string/date/enum/boolean)
   - 指标任务：SQL生成、版本管理、上线发布

2. **宽表层** (`wide_table_service/`)
   - **双版本机制**：离线宽表 (T+1 Parquet) + 实时宽表 (Kafka增量)
   - 版本管理：版本号、版本哈希、快照追踪
   - 智能降级：实时宽表异常时自动降级到离线宽表

3. **模型层** (`model_service/`)
   - **规则引擎** (`rule_engine.py`): 可视化规则配置转SQL
     - 支持多层嵌套规则组 (AND/OR逻辑)
     - 支持值表达式: 常量值、指标引用、时间函数、数学函数
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
├── app/(main)/             # 页面路由
│   ├── agent/                   # 智能体对话界面
│   ├── deepagents/              # DeepAgents任务界面
│   ├── metadata/                # 元数据管理
│   └── fraudhunter/             # 猎诈系统页面
├── components/             # React组件
│   ├── ui/                      # Radix UI基础组件
│   ├── agent/                   # 智能体组件
│   └── fraudhunter/             # 猎诈业务组件
│       └── RuleBuilder.tsx      # 可视化规则构建器
└── lib/                    # 工具和服务
    ├── api.ts                   # Axios配置
    ├── services/                # API服务调用
    └── state/                   # React Context状态管理
```

**API集成：**
- 基础路径: `/api/taosha/v1` (通过 Next.js 重写代理到后端 50020)
- 流式端点: `POST /agents/chat/stream` (服务器发送事件 SSE)
- API客户端配置: `frontend/lib/api.ts`

## 配置管理

**后端配置** (`backend/utils/config.py`):
- 基于 YAML (`backend/config/config.yaml`) + 环境变量 + Pydantic Settings
- 关键配置项：
  - `app.workers`: Uvicorn工作进程数
  - `database.type`: mysql
  - `query_engine.service_type`: duckdb/spark
  - `llm.provider`: openai/qwen/localai
  - `fraudhunter_realtime_data_enabled`: 实时数据服务开关

**前端环境变量** (`.env.local`):
```
NEXT_PUBLIC_API_BASE=/api/taosha/v1
```

## 重要实现细节

### 多Worker环境启动锁

位于 `backend/main.py:_acquire_startup_lock()`，使用文件锁确保在多worker环境下只有一个进程执行：
- 向量数据库训练
- 元数据同步
- 统一调度服务启动
- 实时数据消费者启动

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

规则引擎位于 `backend/services/fraudhunter/model_service/rule_engine.py`，负责：
- 将可视化规则配置编译为SQL WHERE子句
- 支持DuckDB的 `list_filter` 语法进行批量模型匹配
- 生成Spark SQL用于离线计算

### 流式架构

- **后端**: 使用 SSE (Server-Sent Events) 进行实时token流
- **前端**: 使用 Vercel AI SDK 的 `useChat` hook 解析SSE事件
- 事件类型: `text`, `tool_call`, `tool_result`

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
| Next.js 14 | 前端框架 |
| Vercel AI SDK | 流式AI UI |
| Tailwind CSS | 样式系统 |
| Radix UI | 无头UI组件库 |

## 常见任务

### 添加新的Agent工具

1. 在 `backend/services/agents/tools/` 创建工具函数
2. 在 `agent_service.py` 的工具列表中注册
3. 工具通过 LangChain 工具调用机制自动可用

### 修改FraudHunter规则

1. 前端使用 `RuleBuilder.tsx` 可视化配置
2. 后端 `rule_engine.py` 生成SQL
3. 回测验证: 调用模型回测API
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
