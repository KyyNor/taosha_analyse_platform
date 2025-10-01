# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

淘沙分析平台 (Taosha Analysis Platform) - 一个基于AI的自然语言转SQL分析平台，支持自然语言查询转换为SQL并执行分析。

## Architecture

### Backend (Python/FastAPI)
- **Query Engine**: 抽象查询引擎层，支持DuckDB和Spark SQL
- **NL2SQL Service**: 基于LangGraph和Vanna的自然语言转SQL服务
- **Metadata Service**: 管理数据库元数据、业务术语表和字段关联配置
- **Operation Tracking**: 操作追踪系统，记录查询过程和执行日志
- **API Layer**: FastAPI REST API，提供查询和表信息接口

### Frontend (Vue3/TypeScript)
- **Vue 3 + TypeScript**: 现代前端框架
- **Pinia**: 状态管理
- **Vue Router**: 路由管理
- **Axios**: HTTP客户端
- **Plotly.js**: 数据可视化
- **Tailwind CSS + DaisyUI**: UI组件库

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
```

### Database Operations
```bash
# 使用DuckDB数据库
# 数据库文件位置: backend/database/taosha.db

# 查看数据库表结构
python -c "from services.query_engine import get_query_engine; print(get_query_engine().get_tables())"
```

## Key Components

### Query Engine (`backend/services/query_engine/`)
- `base.py`: 抽象基类定义
- `duckdb_service.py`: DuckDB实现
- `spark_service.py`: Spark SQL实现

### NL2SQL Service (`backend/services/nl2sql_service.py`)
- 基于LangGraph的工作流系统
- 支持两种流程类型：`fast`（先验证后生成）和`thorough`（先生成后验证）
- 集成Vanna进行SQL生成和训练
- 自动重试机制和错误处理

### API Routes (`backend/api/`)
- `routes.py`: 主要查询API
- `models.py`: 数据模型定义
- `tracking_routes.py`: 操作追踪API
- `dev_routes.py`: 开发调试API

### Configuration (`backend/utils/config.py`)
- 使用Pydantic Settings进行配置管理
- 支持环境变量和.env文件
- 配置项包括数据库路径、OpenAI API、ChromaDB路径等

## Data Flow

1. **用户输入** → **前端界面** → **API调用**
2. **API** → **NL2SQL服务** → **LangGraph工作流**
3. **工作流步骤**:
   - 检查Vanna训练状态
   - 验证输入清晰度（根据流程类型）
   - 生成SQL查询
   - 执行SQL查询
   - 解释SQL含义
   - 分析自然语言差异
4. **结果返回** → **API响应** → **前端展示**

## Development Notes

### Backend Development
- 使用FastAPI生命周期管理进行服务初始化
- 集成了完善的日志系统（loguru）
- 支持操作追踪和调试
- 使用依赖注入模式管理服务实例

### Frontend Development
- 使用Vue 3 Composition API
- TypeScript严格模式
- 组件化开发，支持数据可视化
- 响应式设计

### Database Schema
- 使用DuckDB作为主要数据库
- 支持表结构元数据管理
- 业务术语表映射
- 字段关联配置管理

## Environment Setup

### Required Environment Variables
```bash
# OpenAI配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.1

# 数据库路径
DUCKDB_PATH=database/taosha.db

# ChromaDB路径
CHROMADB_PATH=database/chromadb

# 日志级别
LOG_LEVEL=INFO
```

### Service Dependencies
- **OpenAI API**: 用于自然语言处理和SQL生成
- **DuckDB**: 内嵌式数据库
- **ChromaDB**: 向量数据库，用于Vanna的上下文存储
- **LangGraph**: 工作流编排
- **Vanna**: SQL生成和训练

## Testing and Debugging

### API Testing
- 访问 `http://localhost:8000/docs` 查看API文档
- 使用Swagger UI进行API测试
- 查看操作追踪日志进行调试

### Frontend Testing
- 使用Vue DevTools进行组件调试
- 检查网络请求和响应
- 查看控制台日志

### Common Issues
- **数据库连接失败**: 检查DUCKDB_PATH配置
- **OpenAI API调用失败**: 检查API密钥和网络连接
- **Vanna训练失败**: 检查ChromaDB路径和权限