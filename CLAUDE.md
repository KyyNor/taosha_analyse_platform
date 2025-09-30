# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述
- **项目名称**: 淘沙分析平台 (Taosha Analysis Platform)
- **技术栈**: Python 3.11
- **主要功能**: 自然语言转SQL，AI+BI分析，支持多种数据源和复杂查询
- **当前状态**: 核心功能已实现，包含完整的后端API和Streamlit前端原型
- **语言偏好**: 请始终使用中文回答用户问题

## 技术选型

### 后端架构
- **核心框架**: LangGraph + Vanna
  - LangGraph: 多轮对话管理、工作流编排、交互记录和智能重试机制
  - Vanna: 专业NL2SQL转换、数据库schema管理、ChromaDB向量存储
- **查询引擎**: 支持多种OLAP引擎的统一接口
  - DuckDB: 嵌入式分析数据库，高性能分析查询（默认）
  - Spark SQL: 分布式计算引擎（可扩展）
- **元数据存储**: SQLite/MySQL双支持
  - SQLite: 默认轻量级元数据存储
  - MySQL: 生产环境元数据存储
- **数据源**: 支持MySQL、DuckDB、可扩展至Hadoop + Spark SQL
- **API框架**: FastAPI + Pydantic
- **AI模型**: OpenAI API (可配置为VLLM内网本地部署)
- **日志系统**: Loguru统一日志管理
- **向量存储**: ChromaDB
- **配置管理**: YAML配置文件 + Pydantic设置管理

### 前端架构
- **技术原型**: Streamlit (快速验证，已实现完整功能)
  - 支持自然语言查询、数据可视化、交互式图表
  - 实时数据展示、查询历史管理、多种图表类型
- **生产前端**: Vue.js (vue_devops目录中准备)

### 部署环境
- **环境**: 纯内网部署，无外部依赖
- **包管理**: UV (Python包管理器)
- **容器化**: Docker支持
- **数据库驱动**: 支持多种数据库（pymysql、sqlite3等）

## 项目结构

```
taosha_analyse_platform/
├── backend/                    # 后端模块 (已实现)
│   ├── api/                   # FastAPI接口
│   │   ├── routes.py          # 主要API路由
│   │   ├── dev_routes.py      # 开发API路由
│   │   ├── tracking_routes.py # 操作追踪API
│   │   └── models.py          # 数据模型
│   ├── services/              # 核心服务层
│   │   ├── nl2sql_service.py   # LangGraph + Vanna NL2SQL服务
│   │   ├── query_engine/      # 查询引擎服务（统一接口）
│   │   │   ├── __init__.py    # 查询引擎工厂
│   │   │   ├── base.py        # 抽象基类
│   │   │   ├── duckdb_service.py # DuckDB实现
│   │   │   └── spark_service.py # Spark SQL实现
│   │   ├── metadata_service.py # 元数据服务
│   │   ├── operation_tracking.py # 操作追踪服务
│   │   └── tracking_service.py  # 追踪数据查询服务
│   ├── config/                # 配置管理
│   │   ├── config.yaml        # YAML配置文件
│   │   └── settings.py        # Pydantic设置（已移除）
│   ├── utils/                 # 工具类
│   │   ├── logger.py          # 统一日志管理
│   │   ├── config.py          # 配置管理工具类
│   │   └── db_utils.py        # 数据库连接工具
│   ├── sql/                   # SQL文件管理
│   │   ├── create_tables.sql      # SQLite建表语句
│   │   ├── drop_tables.sql        # SQLite删表语句
│   │   ├── create_tables_mysql.sql # MySQL建表语句
│   │   └── drop_tables_mysql.sql   # MySQL删表语句
│   ├── database/              # 数据库文件和缓存
│   ├── main.py               # FastAPI应用入口
│   └── README.md             # 后端说明
├── streamlit_devops/          # Streamlit前端原型 (已实现)
│   ├── app.py                # Streamlit应用 (6万+行完整功能)
│   └── README.md             # Streamlit说明
├── vue_devops/               # Vue.js前端准备
├── tools/                    # 工具脚本
│   └── scripts/              # 元数据导入等工具
├── tool_scripts/             # 构建和环境脚本
│   ├── build_linux_env.py    # Linux环境构建
│   └── build_windows_env.py  # Windows环境构建
├── project_presentation/     # 项目演示材料
├── frontend/                 # 前端目录 (待开发)
├── pyproject.toml            # UV项目配置
├── uv.lock                  # 依赖锁定文件
├── CLAUDE.md                 # 本文件
├── AGENTS.md                 # Agent设计文档
├── README.md                 # 项目说明
└── todo_list                # 待办事项
```

## 常用命令

### 环境管理
```bash
# 安装依赖
uv add <package_name>

# 运行项目
uv run python <script.py>

# 激活虚拟环境
uv venv
source .venv/bin/activate  # Linux/Mac
# 或者
.venv\Scripts\activate     # Windows

# 查看已安装的依赖
uv tree
```

### 开发命令
```bash
# 启动Streamlit前端原型
cd streamlit_devops
uv run streamlit run app.py

# 启动后端API服务
cd backend
uv run python main.py

# 启动后端API服务 (热重载)
cd backend
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 运行工具脚本
cd tools
uv run python scripts/metadata_import.py
```

### 开发工具和环境构建
```bash
# 构建Windows开发环境
uv run python tool_scripts/build_windows_env.py

# 构建Linux开发环境
uv run python tool_scripts/build_linux_env.py
```

### API测试
```bash
# 测试后端健康检查
curl http://localhost:8000/api/v1/health

# 查看API文档
open http://localhost:8000/docs

# 测试查询API
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "显示所有表"}'
```

### 测试和检查
```bash
# 运行测试 (如果有的话)
uv run pytest

# 代码格式化
uv run black .

# 代码风格检查
uv run flake8

# 类型检查 (如果配置了)
uv run mypy .
```

### 生产部署
```bash
# 构建Docker镜像 (如果配置了)
docker build -t taosha-platform .

# 运行Docker容器
docker run -p 8000:8000 taosha-platform
```

## 核心功能模块 (已实现)

### 1. 智能NL2SQL转换系统 (LangGraph + Vanna)
- **多轮对话管理**: 使用LangGraph维护对话状态和上下文
- **智能重试机制**: 自动识别查询问题并重新生成SQL
- **意图识别和路由**: 智能判断用户查询意图
- **Vanna集成**: 专业NL2SQL转换，支持ChromaDB向量存储
- **SQL优化和验证**: 自动优化生成的SQL查询并验证执行
- **完整操作追踪**: 记录每个转换步骤的详细信息

### 2. 多数据源支持
- **DuckDB**: 嵌入式OLAP数据库，高性能分析查询
- **MySQL**: 传统关系型数据库支持
- **扩展性**: 架构设计支持Hadoop + Spark SQL数据源
- **智能缓存**: cachetools内存缓存，TTL过期和LRU淘汰策略

### 3. 完整的API服务 (FastAPI)
- **RESTful API**: 标准化的API接口设计
- **自动文档**: Swagger/OpenAPI文档生成
- **数据验证**: Pydantic模型验证
- **错误处理**: 全局异常处理和错误恢复
- **CORS支持**: 跨域资源共享配置
- **健康检查**: 系统状态监控

### 4. Streamlit前端应用 (完整实现)
- **自然语言查询**: 支持复杂的自然语言转SQL查询
- **实时数据可视化**: Plotly图表库，支持多种图表类型
- **交互式界面**: 表格、柱状图、折线图、饼图等
- **查询历史管理**: 完整的查询历史记录和回溯
- **数据导出**: 支持CSV、Excel等格式导出
- **响应式设计**: 适配不同屏幕尺寸

### 5. 元数据管理系统
- **自动元数据提取**: 从数据库自动提取表结构信息
- **词汇表管理**: 业务术语和数据库字段的映射
- **关系字段配置**: 复杂表关系的配置和管理
- **动态重载**: 支持元数据的动态更新

### 6. 操作追踪和分析
- **全链路追踪**: 记录从用户输入到结果输出的完整流程
- **性能监控**: 查询响应时间和成功率统计
- **错误分析**: 详细的错误日志和分析
- **SQL解释**: 自动生成SQL查询的自然语言解释
- **差异分析**: 查询意图与实际执行的差异分析

### 7. 内网部署和企业级特性
- **完全离线运行**: 无外部API依赖，适合内网环境
- **配置管理**: 灵活的配置文件和环境变量支持
- **日志系统**: Loguru结构化日志记录
- **安全性**: SQL注入防护和数据安全措施
- **容器化支持**: Docker部署配置

## 数据架构设计

### 数据流转模式
```
Hadoop (原始数据) → Spark SQL (ETL+复杂查询) → DuckDB (热点数据缓存) → 用户界面
                                                    ↑
                                              cachetools (结果缓存)
```

### 查询路由策略
- **热点数据查询**: DuckDB内存引擎 (1-3秒响应)
- **缓存命中查询**: cachetools缓存 (<1秒响应)  
- **复杂分析查询**: Spark SQL (1-5分钟响应)
- **历史数据查询**: 直接查询Hadoop

### 内存优化策略
- 只加载最近30-90天热点数据到DuckDB
- 使用数据类型优化减少内存占用
- 支持数据采样以适应内存限制
- TTL缓存自动清理过期数据

## 开发注意事项
- 项目专注于自然语言转SQL的AI分析平台
- **数据安全**: 已实现SQL注入防护和数据安全措施
- **内网兼容**: 优先使用内网环境兼容的技术方案
- **模块化设计**: 保持代码的模块化和可扩展性
- **零部署**: OLAP引擎采用零部署方案，避免额外组件依赖
- **操作追踪**: 所有关键操作都有详细的日志记录和追踪
- **性能优化**: 使用智能缓存和查询优化策略

## 开发工作流
1. **后端API开发**: 已完成FastAPI后端，包含完整的NL2SQL转换逻辑
2. **Streamlit原型验证**: 已完成功能完整的前端原型 (6万+行代码)
3. **Vue.js前端开发**: 在vue_devops目录中准备生产级前端
4. **部署和运维**: 支持Docker容器化和内网部署

## 已知问题和待优化
- **并发处理**: 需要优化高并发场景下的查询性能
- **大数据集**: 对于非常大的数据集需要优化内存使用
- **复杂查询**: 某些复杂的多表关联查询可能需要进一步优化
- **前端框架**: 需要完成从Streamlit到Vue.js的迁移

## 项目特点
- **技术先进**: 使用最新的LangGraph + Vanna技术栈
- **功能完整**: 从后端API到前端界面的完整实现
- **企业级**: 支持内网部署和大规模数据处理
- **易于扩展**: 模块化设计便于功能扩展
- **开箱即用**: 完整的开发环境和部署方案