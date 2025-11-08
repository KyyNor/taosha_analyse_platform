# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指导。

## 项目概述

**淘沙分析平台** - 一个基于AI的自然语言转SQL分析平台，支持将自然语言查询转换为SQL、执行查询，并通过语义搜索进行数据分析。

## 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- `uv` 包管理器
- `npm` 或 `pnpm`

### 开发命令

```bash
# 后端：安装依赖并启动
uv sync
cd backend && uv run python main.py

# 前端：安装依赖并启动
cd frontend && npm install && npm run dev

# 运行测试
uv run pytest -q

# 类型检查
cd frontend && npm run type-check
```

### 常用URL
- 前端应用：http://localhost:5173
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs
- Phoenix追踪：http://localhost:7788

## 系统架构

### 后端组件（Python/FastAPI）

**入口**：`backend/main.py` - FastAPI应用，包含生命周期管理

**核心服务**（`backend/services/`）：
- **query_engine/**：查询引擎，支持DuckDB/Spark SQL
- **nlquery_service/**：基于LangGraph的NL2SQL服务，5节点工作流（知识库检查 → 上下文检索 → SQL生成 → SQL验证 → 结果解释）
- **llm_service/**：LLM交互服务（SQL生成、验证、解释）
- **vector_store/**：基于Qdrant的语义搜索，使用Qwen3嵌入模型，支持本地和远程部署
- **metadata_service/**：元数据管理（数据库模式、业务术语、关系、主题），支持术语表基础字段定义和元数据同步
- **tracking_service/**：操作追踪，支持TTL缓存

**数据访问层**（`backend/repositories/`）：
- `base_repository.py`：通用SQLAlchemy ORM CRUD操作
- `training_repository.py`、`tracking_repository.py`、`metadata_repository.py` 等

**数据库**：
- DuckDB（`database/taosha.duckdb`）：主要查询执行引擎
- SQLite/MySQL（`database/metadata.db`）：元数据存储（主题、术语表、关系、训练数据）
- Qdrant（支持本地/远程部署）：向量嵌入存储，替代ChromaDB提供更好的性能和企业级特性

**API路由**（`backend/api/`）：
- `nlquey_routes.py`：查询执行，支持HTTP长轮询实时进度更新
- `metadata_routes.py`：元数据CRUD操作
- `endpoint_models.py`：请求/响应模型定义

### 前端（Vue 3 + TypeScript）

**结构**：
- `src/components/`：功能组件（查询、布局、公共组件）
- `src/services/api/`：HTTP客户端和API服务层
- `src/stores/`：Pinia状态管理
- `src/views/`：页面组件
- `src/utils/`：工具函数（格式化、时间处理、SQL高亮）
- `src/types/`：TypeScript接口定义

**技术栈**：Vite、Pinia、Axios、ECharts、Tailwind CSS + DaisyUI

**核心功能**：HTTP长轮询实时进度更新、SQL语法高亮、元数据管理UI、结果数据可视化、响应式设计

## 开发工作流

### 后端开发

```bash
# 启动开发服务器（自动重载）
cd backend && uv run python main.py

# 或使用uvicorn
cd backend && uv run uvicorn main:app --reload

# 运行测试
uv run pytest -q

# 运行特定测试文件
uv run pytest backend/tests/test_routes.py -q

# 按关键字运行测试
uv run pytest -k tracking

# 类型检查
cd backend && python -m mypy services/
```

**代码风格**：
- PEP 8规范，4空格缩进，必须有类型注解
- 命名规范：`snake_case`（函数/变量）、`PascalCase`（类）、`UPPER_SNAKE_CASE`（常量）
- 使用 `loguru` 日志库，避免 `print()`

**开发模式**：
- 依赖注入：服务构造函数中进行依赖注入
- Repository模式：使用SQLAlchemy ORM进行数据访问
- 数据库会话：通过 `get_db_session()` 上下文管理器获取会话
- 异步编程：使用async/await处理查询和WebSocket
- LangGraph工作流：支持条件路由的工作流编排

### 前端开发

```bash
cd frontend

# 启动开发服务器
npm run dev

# 生产构建
npm run build

# 类型检查和代码检查
npm run type-check
npm run lint
```

**代码风格**：
- 使用 `<script setup lang="ts">` 语法
- 组件：`PascalCase`（如 `QueryForm.vue`）
- 组合函数：`camelCase`（如 `useQueryStore.ts`）
- 启用严格的TypeScript模式

## 测试

**位置**：`testcases/` 目录（包含单元测试、集成测试、API测试）

```bash
# 运行所有测试
uv run pytest -q

# 运行单个文件
uv run pytest testcases/unit/test_metadata_service.py -q

# 按标记运行
uv run pytest -m "not slow" -q

# 生成覆盖率报告
uv run pytest --cov=backend --cov-report=html
```

**测试框架**：pytest，包含mock和数据库设置的fixture
**覆盖率目标**：核心逻辑85%+、服务层80%+、Repository层80%+、API层75%+

## 配置与环境

### 后端配置（`backend/config/config.yaml`）

YAML配置文件，支持环境变量覆盖（前缀：`TAOSHA_`）

**主要配置项**：
- `app`：应用名称、版本、调试模式
- `query_engine`：DuckDB/Spark选择
- `taosha_db`：SQLite/MySQL元数据数据库
- `openai`：API密钥、模型、温度参数
- `embedding`：本地/远程嵌入配置
- `vector_store`：Qdrant向量存储（支持本地和远程部署）
- `tracing`：Phoenix/LangFuse追踪配置
- `logging`：日志级别、轮转、保留策略

### 环境变量

```bash
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=kimi-k2-0905-preview
TAOSHA_LOG_LEVEL=INFO
```

### 数据库查询

```bash
# 查看DuckDB表
python -c "from services.query_engine import get_query_engine; print(get_query_engine().get_tables())"

# SQLite表
sqlite3 backend/database/metadata.db ".tables"
```

## 常见任务

### 添加新的API端点

1. 在 `backend/api/endpoint_models.py` 中添加模型定义
2. 在相应服务中实现业务逻辑
3. 在 `backend/api/*_routes.py` 中添加路由处理器
4. 如果是新路由，在 `backend/main.py` 中注册
5. 在 `testcases/api/test_routes.py` 中添加测试

### 添加前端组件

1. 在 `src/components/` 中创建 `.vue` 文件，使用 `<script setup lang="ts">`
2. 定义props/emits并使用TypeScript接口
3. 如需共享逻辑，创建组合函数
4. 在父组件中导入使用
5. 确保类型安全且符合严格模式

### 添加数据库模式

1. 在 `backend/models/` 中创建模型
2. 在 `backend/repositories/` 中创建repository
3. 添加CRUD方法
4. 更新 `backend/models/db_base.py` 进行会话管理

## 调试

**后端**：
- 日志：`backend/logs/app.log`、`error.log`
- API文档：`http://localhost:8000/docs`
- 启用调试：在config.yaml中设置 `debug: true`
- 调试器：`python -m pdb backend/main.py`

**前端**：
- Vue DevTools浏览器扩展
- 检查Console和Network选项卡
- 检查WebSocket消息
- 在TypeScript源代码中设置断点

**追踪**：
- Phoenix（如果启用）：`http://localhost:7788`
- 显示LangGraph执行和LLM调用

## 项目结构

```
backend/
├── main.py                      # FastAPI应用
├── api/                         # 路由和模型
├── services/                    # 业务逻辑
│   ├── query_engine/            # DuckDB/Spark
│   ├── nlquery_service/         # NL2SQL
│   ├── llm_service/             # LLM调用
│   ├── vector_store/            # Qdrant向量存储
│   ├── metadata_service/        # 元数据管理
│   └── tracking_service/        # 操作追踪
├── repositories/                # 数据访问层
├── models/                      # ORM模型
├── config/
│   └── config.yaml
├── utils/
│   ├── config.py                # 配置管理
│   ├── logger.py                # 日志配置
│   └── progress_decorator.py    # 进度装饰器
└── database/
    ├── taosha.duckdb
    ├── metadata.db
    └── qdrant/              # Qdrant向量存储数据

frontend/
├── src/
│   ├── components/              # Vue组件
│   ├── services/api/            # API客户端
│   ├── stores/                  # Pinia状态管理
│   ├── views/                   # 页面组件
│   ├── utils/                   # 工具函数
│   └── types/                   # TypeScript接口
├── vite.config.ts
├── tsconfig.json
└── package.json

testcases/
├── unit/                        # 单元测试
├── integration/                 # 集成测试
└── api/                         # HTTP测试
```

## Git提交规范

**提交信息格式**：`[scope]: 描述`
- 作用域：`backend`、`frontend`、`docs`、`infra`、`test`
- 风格：使用祈使语气（"添加"、"修复"、"重构"），不用过去式
- 语言：中文或英文均可

**提交前检查**：
- 后端：`uv run pytest -q`
- 前端：`npm run lint && npm run type-check`
- 不要提交 `.env` 文件或凭据

## 重要说明

### 核心功能特性

### 人在循环（Human-in-the-Loop）
- **功能描述**：支持查询过程中的用户交互和澄清
- **实现细节**：
  - 在查询执行过程中遇到歧义时，系统会主动向用户请求澄清
  - 支持多选澄清选项和自定义文字输入
  - 异步处理澄清请求，避免阻塞查询流程
  - 完整的实时进度更新
- **技术实现**：
  - 后端：扩展了 `async_query_service.py` 支持澄清状态管理
  - 前端：优化 `QueryProgress.vue` 组件，支持澄清交互界面
  - 新增 `BaseNodeLog` 类型用于追踪查询步骤

### 元数据同步功能
- **功能描述**：自动同步外部数据库的元数据信息
- **配置支持**：
  - 支持MySQL、PostgreSQL、SQLite等多种数据源
  - 可配置同步策略（全量/增量）
  - 支持定时同步和手动触发
- **技术实现**：
  - 新增 `metadata_sync_service.py` 处理同步逻辑
  - 配置文件支持多数据源连接配置
  - 自动识别表结构、字段类型和关系信息

### 术语表基础字段功能
- **功能描述**：为术语表添加基础字段支持，增强元数据管理能力
- **新增字段**：
  - 数据类型定义
  - 字段长度限制
  - 默认值设置
  - 验证规则配置
- **技术实现**：
  - 扩展 `glossary_models.py` 数据模型
  - 更新 `metadata_service.py` 业务逻辑
  - 前端界面增加字段编辑功能

### 单进程部署方案
- **功能描述**：通过FastAPI同时提供前端和后端服务
- **实现方案**：
  - FastAPI挂载前端静态文件到根路径
  - API接口迁移到 `/api/taosha/v1/` 路径
  - 支持SPA路由（404自动回退到index.html）
- **部署优势**：
  - 一键启动完整应用
  - 简化部署流程
  - 支持内网离线环境

### 前端离线字体支持
- **功能描述**：配置离线本地字体，支持内网部署
- **字体选择**：
  - 思源黑体CN（中文字体，覆盖99%+常用简体中文）
  - Cascadia Code（代码字体，专业显示）
- **技术优势**：
  - 完全离线，无需CDN依赖
  - 支持Windows和国产Linux系统
  - 现代科技感，提升用户体验
  - 字体文件优化（woff2格式，异步加载）

### 性能优化
- 向量数据库训练在应用启动时异步执行
- 查询结果使用TTLCache缓存
- 使用HTTP长轮询实现实时更新（兼容企业内网环境）
- DuckDB高效处理大规模数据集
- Qdrant向量存储提供高性能语义搜索

### 安全考虑
- 开发环境CORS开放；生产环境需限制来源
- 不要提交.env文件或凭据
- 在API层验证用户输入
- 使用SQLAlchemy ORM防止SQL注入
- 生产环境考虑添加速率限制

### UI/UX优化
- **样式改进**：
  - 添加卡片边框样式，提升视觉层次感
  - 使用OKLch色彩空间优化主题配色
  - 降低色彩饱和度，提供更柔和的视觉效果
  - 改善深色模式对比度
- **交互优化**：
  - 修复弹窗步骤日志显示问题
  - 优化澄清功能界面，支持自动收起
  - 完善TypeScript类型安全

### 淘沙Agent智能对话功能
- **功能描述**：基于LangChain ReAct Agent的智能对话助手，提供自然语言问答服务
- **核心特性**：
  - 实时流式对话响应（Server-Sent Events）
  - 现代化聊天界面，支持多轮对话
  - 集成现有LLM服务，无需额外配置
  - 完整的TypeScript类型安全
- **技术实现**：
  - 后端：`backend/services/agents/agent_service.py` - LangChain Agent核心服务
  - 后端：`backend/api/agents_routes.py` - 流式API接口，支持SSE
  - 前端：`frontend/src/views/AgentPage.vue` - 聊天页面组件
  - 前端：`frontend/src/stores/agentStore.ts` - Pinia状态管理
  - 前端：`frontend/src/services/api/agentService.ts` - API服务封装
- **架构优势**：
  - 复用现有LLM服务和配置管理
  - 使用Fetch + ReadableStream处理流式数据
  - 统一的API配置和错误处理机制
  - 响应式设计，适配多种屏幕尺寸

### 代码质量提升
- **类型安全**：
  - 修复所有TypeScript编译错误
  - 删除未使用的变量和导入
  - 添加完整的类型定义文件
- **依赖管理**：
  - 稳定版本依赖，减少升级风险
  - 清理冗余依赖包

### 已知限制
- 开发环境使用SQLite；生产环境应使用MySQL
- 训练数据索引目前在内存中；考虑使用持久化嵌入缓存
- 暂不支持多租户

## 参考资源

- FastAPI：https://fastapi.tiangolo.com/
- LangGraph：https://langchain-ai.github.io/langgraph/
- Vue 3：https://vuejs.org/
- SQLAlchemy：https://docs.sqlalchemy.org/
- ChromaDB：https://docs.trychroma.com/
- DuckDB：https://duckdb.org/docs/

## 故障排除

**后端无法启动**：
- 检查 `.env` 文件是否存在且包含必需的变量
- 验证Python版本：`python --version`
- 清理缓存：`rm -rf backend/__pycache__ .pytest_cache`
- 重新安装：`uv sync --refresh`

**前端开发服务器无法启动**：
- 验证Node版本：`node --version`
- 清理缓存：`rm -rf frontend/node_modules && npm install`
- 检查5173端口是否被占用

**数据库连接问题**：
- 验证 `config.yaml` 中的数据库路径
- 检查文件权限
- SQLite：`sqlite3 backend/database/metadata.db ".tables"`

**LLM API调用失败**：
- 验证API密钥正确且有额度
- 检查网络连接
- 检查API速率限制
- 启用调试日志：`TAOSHA_LOG_LEVEL=DEBUG`

**向量存储错误**：
- 检查ChromaDB目录是否存在且可写
- 验证嵌入模型路径正确
- 检查推理时是否有足够的内存
- 查看LangChain/OpenInference日志

**Agent服务问题**：
- **端口错误**：确保前端请求发送到正确的后端端口（8000），而非前端开发端口（3000）
- **API配置**：使用 `buildApiUrl()` 确保包含完整的API前缀 `/api/taosha/v1`
- **流式响应**：Fetch + ReadableStream处理SSE，避免直接使用Axios（不支持流式响应）
- **类型错误**：注意 `AxiosResponse` 与原生 `Response` 的区别，特别是在处理流式数据时
- **依赖导入**：Agent服务避免导入 `services` 模块（会触发向量存储初始化），直接导入需要的组件

## Documentation Last Update
上次更新时commit: c8c3ec1 - feat: 添加淘沙Agent智能对话功能
- 文档搜索用context7，其他搜索用tavily