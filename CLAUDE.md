# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Taosha Analysis Platform** is an AI-powered BI platform that converts natural language queries to SQL and provides agent-based conversation capabilities with tool integration.

- **Backend**: FastAPI service for NL→SQL conversion, agent chat, and metadata management
- **Frontend**: Next.js React application with real-time streaming UI

## 开发命令

### 后端

**设置和安装**
```bash
# 使用 uv 安装依赖（Python 3.11+）
uv sync

# 或使用 pip
pip install -r requirements-lock.txt
```

**运行后端**
```bash
# 启动开发服务器（端口 50020）
./sbackend.sh
# 或手动运行：
uv run uvicorn backend.main:app --host 0.0.0.0 --port 50020 --reload

# 使用特定工作进程运行（多工作进程设置）
uvicorn backend.main:app --host 0.0.0.0 --port 50020 --workers 4
```

**代码质量**
```bash
# 运行 lint/类型检查（如果配置了）
uv run ruff check backend/
uv run mypy backend/
```

### 前端

**设置和安装**
```bash
cd frontend
npm install
```

**运行前端**
```bash
# 开发服务器（端口 3000）
npm run dev

# 或使用 shell 脚本
../sfrontend.sh

# 生产构建
npm run build
npm start

# 代码检查
npm run lint
```

**构建和测试**
```bash
# Next.js 生产部署构建
npm run build

# 类型检查
npm run type-check
```

### 全栈开发

```bash
# 终端 1：后端
./sbackend.sh

# 终端 2：前端
./sfrontend.sh

# 后端 API：http://localhost:50020
# 前端 UI：http://localhost:3000
```

## 架构概览

### 后端架构（`/backend`）

**核心层级：**

1. **API 层** (`/backend/api/`)
   - `nlquery_routes.py` - 自然语言查询端点（异步任务提交、进度轮询、澄清）
   - `agents_routes.py` - 智能体对话，支持流式 SSE
   - `metadata_routes.py` - 表/列元数据 CRUD
   - `user_routes.py` - 用户管理（最小化）
   - **基础路径**：`/api/taosha/v1`

2. **服务层** (`/backend/services/`)
   - **智能体服务** (`agents/agent_service.py`)
     - LangChain ReAct 智能体，具有工具调用能力
     - 内存检查点用于会话管理
     - 工具：FineReport 集成、日期辅助、天气 API 等
     - 中间件：摘要生成、PII 屏蔽、待办列表追踪
     - 输出：服务器发送事件（SSE）流

   - **自然语言查询服务** (`nlquery_service/`)
     - `nl2sql_service.py` - LangGraph 工作流（意图→模式→SQL 生成→执行）
     - `async_query_service.py` - 后台任务管理，支持进度追踪
     - 多轮澄清支持

   - **向量存储** (`vector_store/`)
     - Qdrant 后端用于嵌入
     - 通过相似度搜索进行 RAG 上下文检索
     - 从模式元数据训练向量

   - **大语言模型服务** (`llm_service/`)
     - 支持 OpenAI、Qwen（通过 Dashscope）、LocalAI
     - 通过设置可配置
     - 自然语言查询特定提示

   - **查询引擎** (`query_engine/`)
     - 工厂模式支持 DuckDB（进程内）、Spark SQL（JDBC）、EmptyQueryEngine
     - 通过 `config.yaml` 可配置

   - **元数据服务** (`metadata_service/`)
     - SQLAlchemy 模型用于表、列、术语表、主题、关系
     - 模式缓存和同步

3. **数据库层** (`/backend/database`, `/backend/models`)
   - ORM：SQLAlchemy 2.0
   - 数据库：SQLite（开发）、MySQL（生产）
   - 模型：元数据、主题、术语表、追踪、训练记录
   - 连接池通过 `db_base.py`

4. **基础设施**
   - **配置** (`utils/config.py`) - 基于 YAML 的设置，使用 Pydantic 验证
   - **日志** (`utils/logger.py`) - 通过 Loguru 的结构化日志
   - **可观测性** - Langfuse 追踪集成

**关键启动流程：**
```
加载 YAML 配置 → 验证设置 → 初始化数据库 → 获取启动锁（多工作进程同步）
→ 初始化查询引擎 → 初始化 Playwright → 训练向量（异步）→ 同步元数据
→ 初始化 Langfuse → 启动 Uvicorn
```

### 前端架构（`/frontend`）

**技术栈**：Next.js 14、TypeScript、Tailwind CSS、Radix UI、Vercel AI SDK

**项目布局**：
```
app/(main)/
├── agent/page.tsx           # 智能体对话界面
├── nlquery/page.tsx         # 自然语言查询提交与结果
├── history/page.tsx         # 查询历史
├── favorites/page.tsx       # 保存的查询
├── settings/page.tsx        # 应用设置
└── metadata/                # 元数据管理（表、术语表、主题等）

components/
├── agent/                   # 智能体 UI 组件
├── query/                   # 查询表单和结果
├── generative_ui/          # GenUI 支持
└── ui/                     # Radix UI + 自定义组件

lib/
├── state/                  # React Context（智能体、查询、应用、主题）
├── services/               # API 服务调用（agentService、queryService 等）
└── api.ts                 # Axios 配置和 API 基础 URL
```

**状态管理**：
- React Context API：智能体消息、查询任务、主题、全局应用状态
- 服务器发送事件（SSE）：实时智能体流
- 轮询：异步自然语言查询任务进度

**API 集成**：
- 基础 URL：`/api/taosha/v1`（通过 Next.js 重写代理到 `http://localhost:50020`）
- 流式端点：`POST /agents/chat/stream`（服务器发送事件）
- 异步查询：`POST /nlquery/submit` + 轮询 `GET /nlquery/progress/{task_id}`

### 数据流

**智能体对话流：**
```
前端输入 → agentService.chatStream() [SSE]
→ FastAPI：agents_routes.chat_stream_endpoint()
→ LangChain Agent.astream_events()
→ 工具调用 + LLM 生成
→ 流事件（text、tool_call、tool_result）
→ 前端实时渲染
```

**自然语言查询流：**
```
前端输入 → queryService.submitQuery() [异步任务]
→ FastAPI：submit_query() 生成 task_id
→ 后台：LangGraph 工作流（意图→模式→SQL→执行）
→ 前端轮询：progress/{task_id}
→ 完成时检索结果
```

## 关键技术

| 组件 | 技术 | 用途 |
|------|------|------|
| 后端 Web | FastAPI 0.116 | REST API 框架 |
| 智能体/工作流 | LangChain 1.0、LangGraph 1.0 | LLM 编排和工作流 |
| 数据库 ORM | SQLAlchemy 2.0 | 元数据和追踪持久化 |
| 向量数据库 | Qdrant 客户端 1.7 | 嵌入和 RAG 上下文 |
| 查询引擎 | DuckDB 1.2 | 本地 OLAP 查询 |
| LLM 支持 | OpenAI、Qwen、LocalAI | 语言模型（可配置） |
| 可观测性 | Langfuse 3.9 | 追踪和监控 |
| 前端 | Next.js 14、React 18 | Web UI 框架 |
| 样式 | Tailwind CSS、Radix UI | UI 组件和样式 |
| 流 | Vercel AI SDK 5.0 | 客户端 SSE/流 |
| HTTP | Axios 1.7 | 前端 API 调用 |

## 配置

配置基于 `backend/utils/config.py` 中的 YAML：

**关键设置**：
- `app.workers` - Uvicorn 工作进程数
- `database.type` - sqlite 或 mysql
- `query_engine.type` - duckdb、spark 或 empty
- `llm.provider` - openai、qwen、localai
- `vector_store.type` - qdrant
- `qdrant.url` - 向量数据库连接
- `embeddings.model` - 嵌入模型路径/端点
- `tracing.provider` - langfuse 或 phoenix
- `finereport_base_url` - FineReport 集成

通过环境变量或运行时 YAML 文件加载。

## 常见开发任务

### 添加新的智能体工具

1. 在 `backend/services/agents/tools/` 中创建工具函数（例如 `new_tool.py`）
2. 在 `backend/services/agents/agent_service.py` 的工具列表中注册
3. 传递给智能体构造函数：`tools=[get_report_sample, new_tool, ...]`
4. 工具通过 LangChain 工具调用机制自动可被智能体调用

### 添加新的查询流阶段

1. 在 `backend/services/nlquery_service/nl2sql_service.py` 中添加新节点/函数
2. 通过 `graph.add_node()` 和 `graph.add_edge()` 在 LangGraph 工作流中连接
3. 在节点中更新执行追踪/日志

### 修改 API 端点

- 后端路由在 `/backend/api/`
- 前端服务在 `/frontend/lib/services/`
- API 基础 URL：`NEXT_PUBLIC_API_BASE`（前端环境变量）
- 代理重写在 `frontend/next.config.mjs`

### 更新元数据模式

- `/backend/models/` 中的模型
- 如需使用 Alembic 迁移（目前未使用；模式编辑直接应用）
- 重新同步元数据：调用 `metadata_service.sync_from_source()`

### 调试智能体会话

- 日志：后端中 `loguru` 的结构化日志
- 追踪：查看 Langfuse 仪表板获取完整执行跟踪
- 会话状态：检查点存储每个 `session_id` 的状态
- 前端开发工具：在网络选项卡中检查 SSE 事件

## 重要的实现细节

### 多工作进程同步

后端使用启动锁（`backend/utils/startup_lock.py`）来防止多个 uvicorn 工作进程重复初始化。只有第一个工作进程执行向量训练等昂贵任务。

### 异步任务处理

自然语言查询作为后台任务通过 `asyncio` 任务队列运行。前端使用长轮询（30 秒超时）检查进度。任务状态在 `OperationTracker` 中追踪。

### 会话管理

- **智能体**：每个 `session_id` 的内存检查点（临时的，重启后丢失）
- **查询**：通过 UUID + 数据库日志进行任务追踪

### 向量数据库集成

- 嵌入存储在 Qdrant 中以进行快速相似度搜索
- 用于自然语言转 SQL 的 RAG 上下文检索
- 从启动时的元数据模式训练

### 流式架构

- **智能体**：SSE（服务器发送事件）用于实时令牌流
- **前端**：使用 `text`、`tool_call`、`tool_result` 事件类型解析 SSE 事件流
- Vercel AI SDK 提供解析辅助程序

## 测试

未配置正式测试套件。对于手动测试：
- 后端：使用 FastAPI `/docs`（Swagger UI 在 `http://localhost:50020/docs`）
- 前端：浏览器开发者工具
- 集成：使用 `testcases/` 目录中的示例查询

## 部署

**Docker 就绪**：
- 后端：`uvicorn backend.main:app --host 0.0.0.0 --port 50020`
- 前端：`next start --host 0.0.0.0 --port 3000`
- 环境：使用 `.env` 或容器环境变量

**多工作进程设置**：设置 `uvicorn --workers N` 进行水平扩展

**数据库**：在配置中配置 `database.url` 以支持外部 MySQL

**向量数据库**：将 `qdrant.url` 指向远程 Qdrant 实例

## 文件结构参考

```
/backend
├── main.py                     # FastAPI 应用 + 启动/关闭
├── api/                        # 路由处理器
├── services/                   # 业务逻辑（智能体、nlquery 等）
├── models/                     # SQLAlchemy ORM 模型
├── database/                   # 数据库连接和会话管理
├── utils/                      # 配置、日志、启动锁
└── schemas/                    # Pydantic 请求/响应模型

/frontend
├── app/(main)/                 # 页面路由
├── components/                 # React 组件
├── lib/
│   ├── state/                 # React Context 提供程序
│   ├── services/              # API 服务函数
│   ├── api.ts                 # Axios 实例
│   └── utils/                 # 工具函数
└── public/                    # 静态资源
```

## 未来工作笔记

- 考虑添加正式测试（后端使用 pytest、前端使用 Jest/Vitest）
- 模式迁移（Alembic）目前未使用；考虑为生产环境实施
- 会话持久化：内存智能体检查点在重启后丢失；考虑使用 Redis 进行持久化
- 性能：监控 Langfuse 跟踪以发现查询执行瓶颈
- 向量训练是异步的但对大型模式阻塞；考虑增量更新

- **Latest Commit**: `27ffd0d` (cleanup: 清理历史文件和旧备份)