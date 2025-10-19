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

- `metadata_service.py`: 元数据管理服务，支持术语表、关联配置和提示词模板管理

### Prompt Template Renderer (`backend/services/`)

- `prompt_template_renderer.py`: 提示词模板渲染服务，支持模板化提示词生成和占位符替换

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

- `QueryForm.vue`: 查询表单组件，支持示例填充、查询模式切换和表选择优化
- `QueryProgress.vue`: 查询进度展示组件，支持实时进度更新和耗时显示
- `QueryResultsTable.vue`: 查询结果表格组件，支持数据可视化和交互优化
- `SidebarPanel.vue`: 侧边栏面板，包含查询历史和收藏功能
- `FloatingBall.vue`: 悬浮球交互组件
- `LogDetailModal.vue`: 日志详情弹窗组件，支持SQL语法高亮和执行步骤展示

### Metadata Management Components

- `GlossaryPage.vue`: 术语表管理页面，支持概念解释、SQL问答和字典转换三种类型
- `RelationsPage.vue`: 关联配置管理页面，支持关系家族和子家族配置
- `PromptTemplatesPage.vue`: 提示词模板管理页面，支持字段验证和模板预览
- `TablesPage.vue`: 数据表管理页面，支持字段配置和关联ID选择

### Frontend Utility Libraries

- `duration.ts`: 时间和耗时计算工具函数
  - `calculateDuration()`: 计算两个时间点之间的耗时
  - `formatDuration()`: 格式化耗时显示（ms/s/min）
  - `formatTime()`: 格式化时间显示为本地化字符串
- `formatText.ts`: 智能文本格式化工具
  - `formatText()`: 智能格式化各种文本内容（JSON、多行文本等）
  - `formatJson()`: JSON内容格式化，确保正确缩进和换行
  - `isJson()`: 判断文本是否为JSON格式
- `prism.ts`: SQL语法高亮工具
  - `highlightSql()`: SQL代码语法高亮
  - `applyPrismTheme()`: 动态应用Prism主题（支持深色/浅色主题）

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
- 集成Prism.js进行SQL语法高亮显示
- 智能文本格式化和时间处理工具函数

### Database Schema

- **DuckDB**: 主要业务数据库，用于SQL查询执行
- **SQLite**: 元数据数据库，存储表结构、业务术语、关联配置和提示词模板
- 支持表结构元数据管理
- 业务术语表管理（概念解释、SQL问答、字典转换三种类型）
- 字段关联配置管理（关系家族和子家族）
- 提示词模板管理（支持占位符验证和模板渲染）
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
- **SQL语法高亮显示问题**: 检查Prism.js主题配置和CDN连接

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
- ✅ **提示词模板渲染服务**：新增模板化提示词生成和占位符替换功能
- ✅ **术语表管理重构**：支持概念解释、SQL问答、字典转换三种类型
- ✅ **关联配置管理**：实现完整的关系家族和子家族配置功能，支持拼接ID显示
- ✅ **表选择组件优化**：修复数据绑定问题，优化UI展示格式
- ✅ **OperationTracker依赖注入重构**：新增TrackerCache全局缓存管理器，解决数据库写入失败问题
- ✅ **数据库连接管理统一化**：实现Session依赖注入，每个请求获得独立Session，避免并发问题
- ✅ **数据主题管理功能**：完整实现主题和表关联管理，支持一般主题和通用主题两种类型
- ✅ **时间时区问题修复**：统一使用本地时间，解决UTC时差8小时问题
- ✅ **Repository模式数据访问层**：完成SQLAlchemy ORM架构重构，实现标准化数据访问接口
- ✅ **LLM Service模块化**：新增BaseLLMService和NLQueryLLMService，解耦LLM功能逻辑
- ✅ **Training Service完整实现**：支持训练数据管理、会话管理、验证结果记录等核心功能
- ✅ **NL2SQLServiceV2增强**：集成Vector Store、Context Builder、LLM Service、Training Service的完整工作流
- ✅ **LangGraph工作流架构**：5节点工作流（知识库检查、上下文检索、SQL生成、SQL验证、结果解释）
- ✅ **VectorStoreFactory延迟加载**：实现字符串模块路径和动态导入，解决依赖冲突问题
- ✅ **OpenAI客户端管理**：动态创建和配置OpenAI客户端，支持自定义API端点和模型配置

### Frontend Enhancements

- ✅ 完整的前端项目重构
- ✅ 移除登录验证功能，简化使用流程
- ✅ 实时进度展示系统
- ✅ 查询历史和收藏功能
- ✅ 悬浮球侧边栏交互
- ✅ 响应式布局优化
- ✅ 日志详情弹框功能（支持SQL语法高亮和执行步骤展示）
- ✅ API配置和服务代码优化
- ✅ TypeScript类型系统完善
- ✅ 智能文本格式化和时间处理工具函数
- ✅ 查询结果表格数据可视化增强
- ✅ **元数据管理界面重构**：术语表、关联配置、提示词模板三大管理页面
- ✅ **表单组件优化**：关联ID字段改为下拉框选择，提升用户体验
- ✅ **数据展示修复**：解决前端术语表数据显示问题，优化数据绑定逻辑
- ✅ **TypeScript类型安全**：完善接口定义，提升代码类型安全性
- ✅ **数据主题管理界面完善**：实现完整主题管理界面，支持主题信息增删改查和表关联管理
- ✅ **关联配置ID显示优化**：修复关联配置接口，支持拼接ID显示（家族|子家族），同时确保入库使用真实ID

### UI/UX Improvements

- ✅ 横向三列布局的查询表单
- ✅ SQL代码显示区域的主题自适应
- ✅ 查询进度可视化效果
- ✅ 用户和时间信息展示
- ✅ 导航层级结构优化
- ✅ **术语表录入界面美化**：重新设计表单布局，添加主色调边框和内阴影效果
- ✅ **表选择显示优化**：中文名（英文名）格式显示，移除标签展示简化界面

### Testing & Quality Assurance

- ✅ **完整测试框架建立**：新增130+个测试用例，覆盖核心功能
- ✅ **测试目录结构重组**：统一管理到testcases/目录，支持单元测试、集成测试、API测试
- ✅ **查询引擎测试**：DuckDBService完整功能测试，QueryEngineFactory工厂模式测试
- ✅ **Repository层测试**：BaseRepository通用CRUD测试，数据错误处理和事务测试
- ✅ **NL2SQL流程测试**：快速流程和彻底流程测试，异步查询服务集成测试
- ✅ **API接口测试**：自然语言查询API测试，WebSocket实时进度推送测试
- ✅ **中文显示修复**：修复Windows环境下测试中文乱码问题
- ✅ **测试覆盖率提升**：核心业务逻辑85%→90%，服务层80%→85%，Repository层0%→80%，API层0%→75%
- ✅ **LLM Service单元测试**：30个测试覆盖SQL生成、重试、验证、解释等功能
- ✅ **Training Service单元测试**：19个测试覆盖训练数据和会话管理
- ✅ **NL2SQL V2集成测试**：15个测试验证完整工作流和模块集成

### Technical Debt Reduction

- ✅ 代码结构模块化重组
- ✅ 依赖注入模式应用
- ✅ 配置系统标准化
- ✅ 错误处理机制完善
- ✅ 日志系统统一化
- ✅ **API响应处理优化**：修复axios数据重复提取问题，统一API响应格式处理
- ✅ **数据库结构优化**：删除冗余表结构，重新设计术语表和提示词模板表
- ✅ **代码风格统一**：运行ESLint自动修复，统一组件结构和属性顺序
- ✅ **无用代码清理**：移除废弃的按名称查询接口，统一使用ID-based操作
- ✅ **NL2SQLServiceV2工作流架构修复**：
  - 恢复完整的flow_type条件路由逻辑（fast/thorough流程差异执行）
  - 实现SQL执行失败的重试机制（execute_sql → generate_sql）
  - 修复LLM服务方法调用 - 使用validate_input_clarity正确方法
  - 修复TaskState字段类型问题（clear_check_details为字典，添加sql_explanation字段）
  - 添加4个comprehensive工作流流程类型路由测试
  - 全部19个集成测试通过验证

---

## Documentation Last Update
上次更新时commit:2f96839 - 修复NL2SQLServiceV2工作流架构，恢复完整的flow_type逻辑和重试机制