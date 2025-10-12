# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

淘沙分析平台 (Taosha Analysis Platform) - 一个基于AI的自然语言转SQL分析平台，支持自然语言查询转换为SQL并执行分析。

## Architecture

### Backend (Python/FastAPI)
- **Query Engine**: 抽象查询引擎层，支持DuckDB和Spark SQL
- **NL2SQL Service**: 基于LangGraph和Vanna的自然语言转SQL服务，支持本地Embedding
- **Metadata Service**: 管理数据库元数据、业务术语表和字段关联配置
- **Operation Tracking**: 操作追踪系统，记录查询过程和执行日志，支持任务状态缓存
- **API Layer**: FastAPI REST API，提供查询和表信息接口
- **服务架构优化**: 模块化组织服务代码，分为query_engine、nlquery_service、metadata_service、tracking_service、vanna_service

### Frontend (Vue3/TypeScript)
- **Vue 3 + TypeScript**: 现代前端框架，使用Composition API
- **Pinia**: 状态管理
- **Vue Router**: 路由管理
- **Axios**: HTTP客户端，支持请求拦截和响应处理
- **ECharts**: 数据可视化（替代Plotly.js）
- **Socket.io-client**: WebSocket客户端，支持实时进度更新
- **Tailwind CSS + DaisyUI**: UI组件库
- **@vueuse/core**: Vue组合式工具库

## Common Commands

### Backend Development

```bash
# 进入后端目录
cd backend

# 安装依赖
uv sync

# 启动开发服务器 (推荐使用uv run)
uv run python main.py

# 或者使用uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 代码检查
npm run lint
npm run type-check
```

### Database Operations

```bash
# 使用DuckDB数据库
# 数据库文件位置: backend/database/taosha.duckdb

# 查看数据库表结构
python -c "from services.query_engine import get_query_engine; print(get_query_engine().get_tables())"

# 元数据数据库（SQLite）
# 数据库文件位置: backend/database/metadata.db
```

## Key Components

### Query Engine (`backend/services/query_engine/`)

- `base.py`: 抽象基类定义
- `duckdb_service.py`: DuckDB实现
- `spark_service.py`: Spark SQL实现

### NL2SQL Service (`backend/services/nlquery_service/`)

- `nl2sql_service.py`: 基于LangGraph的自然语言转SQL服务
- `async_query_service.py`: 异步查询服务，支持WebSocket进度推送
- 支持两种流程类型：`fast`（先验证后生成）和`thorough`（先生成后验证）

### Vanna Service (`backend/services/vanna_service/`)

- `taosha_vanna_service.py`: Vanna服务实现，支持自定义Embedding
- `local_embedding_service.py`: 本地Embedding模型支持（Qwen3-Embedding-0.6B）

### Tracking Service (`backend/services/tracking_service/`)

- `operation_tracking.py`: 操作追踪服务，支持任务状态缓存和TTL管理
- 使用cachetools进行内存缓存优化

### Metadata Service (`backend/services/metadata_service/`)

- `metadata_service.py`: 元数据管理服务

### API Routes (`backend/api/`)

- `nlquey_routes.py`: 主要查询API，支持异步查询和进度追踪
- `metadata_routes.py`: 元数据管理API
- `user_routes.py`: 用户相关API
- `endpoint_models.py`: 统一的API数据模型

### Configuration (`backend/utils/config.py`)

- 使用Pydantic Settings进行配置管理
- 支持YAML配置文件和环境变量
- 配置项包括数据库路径、OpenAI API、Embedding配置等

### Frontend Components

- `QueryForm.vue`: 查询表单组件，支持示例填充和查询模式切换
- `QueryProgress.vue`: 查询进度展示组件，支持实时进度更新
- `QueryResultsTable.vue`: 查询结果表格组件
- `SidebarPanel.vue`: 侧边栏面板，包含查询历史和收藏功能
- `FloatingBall.vue`: 悬浮球交互组件

## Data Flow

1.  **用户输入** → **前端界面** → **API调用**
2.  **API** → **异步查询服务** → **LangGraph工作流**
3.  **工作流步骤**:
    - 检查Vanna训练状态
    - 验证输入清晰度（根据流程类型）
    - 生成SQL查询
    - 执行SQL查询
    - 解释SQL含义
    - 分析自然语言差异
4.  **实时进度推送** → **WebSocket** → **前端进度更新**
5.  **结果返回** → **API响应** → **前端展示**

## Development Notes

### Backend Development

- 使用FastAPI生命周期管理进行服务初始化
- 集成了完善的日志系统（loguru）
- 支持操作追踪和调试，使用TTLCache进行任务状态缓存
- 模块化服务架构，便于维护和扩展
- 支持本地Embedding模型，减少对外部API的依赖

### Frontend Development

- 使用Vue 3 Composition API和TypeScript严格模式
- 组件化开发，支持数据可视化和实时进度更新
- 响应式设计，支持移动端适配
- 使用Pinia进行状态管理，支持查询历史和收藏功能
- 完整的错误处理和用户友好的提示系统

### Database Schema

- **DuckDB**: 主要业务数据库，用于SQL查询执行
- **SQLite**: 元数据数据库，存储表结构、业务术语和操作日志
- 支持表结构元数据管理
- 业务术语表映射
- 字段关联配置管理
- 操作日志记录和任务状态追踪

## Environment Setup

### Configuration File (`backend/config/config.yaml`)

主要配置项包括：
- 应用信息（名称、版本、调试模式）
- 查询引擎配置（DuckDB/Spark选择）
- 元数据数据库配置（SQLite/MySQL）
- OpenAI API配置
- Embedding配置（支持本地模型）
- 日志配置

### Required Environment Variables

```bash
# OpenAI配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=kimi-k2-0905-preview
OPENAI_TEMPERATURE=0.1

# Embedding配置（可选）
EMBEDDING_API_KEY=your_embedding_api_key
EMBEDDING_BASE_URL=https://api.openai.com/v1

# 日志级别
TAOSHA_LOG_LEVEL=INFO
```

### Service Dependencies

- **OpenAI API**: 用于自然语言处理和SQL生成
- **DuckDB**: 内嵌式数据库
- **SQLite**: 元数据数据库
- **ChromaDB**: 向量数据库，用于Vanna的上下文存储
- **LangGraph**: 工作流编排
- **Vanna**: SQL生成和训练
- **本地Embedding**: Qwen3-Embedding-0.6B模型支持

## Testing and Debugging

### API Testing

- 访问 `http://localhost:8000/docs` 查看API文档
- 使用Swagger UI进行API测试
- 查看操作追踪日志进行调试
- 支持实时WebSocket进度监控

### Frontend Testing

- 使用Vue DevTools进行组件调试
- 检查网络请求和响应
- 查看控制台日志
- 使用浏览器开发工具监控WebSocket连接

### Common Issues

- **数据库连接失败**: 检查配置文件中的数据库路径
- **OpenAI API调用失败**: 检查API密钥、基础URL和网络连接
- **本地Embedding加载失败**: 检查模型路径和设备配置
- **WebSocket连接问题**: 检查前后端WebSocket配置
- **任务状态缓存问题**: 检查TTLCache配置和内存使用情况

## New Features Since 88ebe2925ff8db667dafde3ee46c6e95d4a08ff3

### Backend Enhancements

- ✅ 模块化服务架构重构
- ✅ 任务状态缓存系统（TTLCache）
- ✅ 本地Embedding模型支持
- ✅ 异步查询服务优化
- ✅ 统一的TaskState和BaseNodeLog模型
- ✅ 操作追踪系统简化
- ✅ 元数据数据库结构优化
- ✅ 配置管理统一化

### Frontend Enhancements

- ✅ 完整的前端项目重构
- ✅ 移除登录验证功能，简化使用流程
- ✅ 实时进度展示系统
- ✅ 查询历史和收藏功能
- ✅ 悬浮球侧边栏交互
- ✅ 响应式布局优化
- ✅ 日志详情弹框功能
- ✅ API配置和服务代码优化
- ✅ TypeScript类型系统完善

### UI/UX Improvements

- ✅ 横向三列布局的查询表单
- ✅ SQL代码显示区域的主题自适应
- ✅ 查询进度可视化效果
- ✅ 用户和时间信息展示
- ✅ 导航层级结构优化

### Technical Debt Reduction

- ✅ 代码结构模块化重组
- ✅ 依赖注入模式应用
- ✅ 配置系统标准化
- ✅ 错误处理机制完善
- ✅ 日志系统统一化