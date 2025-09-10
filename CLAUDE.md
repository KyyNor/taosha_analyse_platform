# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述
- **项目名称**: 淘沙分析平台 (Taosha Analysis Platform)
- **技术栈**: Python 3.11
- **主要功能**: 自然语言转SQL，AI+BI分析
- **语言偏好**: 请始终使用中文回答用户问题

## 技术选型

### 后端架构
- **核心框架**: LangGraph + Vanna
  - LangGraph: 多轮对话管理、工作流编排、交互记录
  - Vanna: 专业NL2SQL转换、数据库schema管理
- **OLAP引擎**: DuckDB + cachetools
  - DuckDB: 嵌入式OLAP数据库，高性能分析查询
  - cachetools: Python内存缓存，支持TTL和LRU策略
- **数据源**: Hadoop + Spark SQL (原始数据)
- **API框架**: FastAPI
- **AI模型**: VLLM (内网本地部署)

### 前端架构
- **技术原型**: Streamlit (快速验证)
- **生产前端**: 待定 (React/Vue/Svelte)

### 部署环境
- **环境**: 纯内网部署，无外部依赖
- **包管理**: UV (Python包管理器)

## 项目结构

```
taosha_analyse_platform/
├── backend/                    # 后端模块 (LangGraph + Vanna)
│   ├── agents/                # LangGraph Agent定义
│   ├── nl2sql/               # Vanna NL2SQL核心
│   ├── database/             # 数据库连接和管理
│   ├── api/                  # FastAPI接口
│   └── config/               # 配置管理
├── frontend/                  # 前端模块 (技术栈待定)
├── devops/                   # 运维和部署
│   ├── streamlit_prototype/  # Streamlit技术原型
│   ├── docker/               # Docker部署配置
│   ├── k8s/                  # Kubernetes配置
│   └── scripts/              # 部署脚本
├── tools/                    # 工具脚本
│   └── scripts/              # 各种工具脚本
├── pyproject.toml            # UV项目配置
└── CLAUDE.md                 # 本文件
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
```

### 开发命令
```bash
# 启动Streamlit原型
cd devops/streamlit_prototype
uv run streamlit run app.py

# 启动后端API (开发完成后)
cd backend
uv run uvicorn api.main:app --reload

# 运行工具脚本
cd tools
uv run python scripts/metadata_import.py
```

### 测试和检查
由于项目处于初始化阶段，具体的测试和代码检查命令将在开发过程中添加：
- `uv run pytest` - 运行测试
- `uv run black .` - 代码格式化
- `uv run flake8` - 代码风格检查

## 核心功能模块

### 1. 多轮对话管理 (LangGraph)
- 维护对话状态和上下文
- 处理用户意图识别和路由
- 记录完整的交互过程

### 2. NL2SQL转换 (Vanna)
- 自然语言理解和SQL生成
- 数据库schema学习和管理
- SQL查询优化和验证

### 3. 轻量级OLAP引擎 (DuckDB + cachetools)
- 嵌入式OLAP数据库，无需额外部署
- 智能内存缓存，支持TTL过期和LRU淘汰
- 从Hadoop加载热点数据到内存进行快速查询
- 预聚合表支持，加速常见分析场景
- 查询性能：秒级响应 vs Spark SQL分钟级

### 4. 数据可视化
- 支持多种图表类型
- 自动根据数据特征选择合适的可视化方式
- 表格、柱状图、折线图、饼图等

### 5. 内网部署支持
- 完全离线运行，无外部API依赖
- 支持企业内部VLLM模型
- 适配企业内部数据库环境
- 零额外组件部署，纯Python包解决方案

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
- 考虑数据安全和SQL注入防护
- 优先使用内网环境兼容的技术方案
- 保持代码的模块化和可扩展性
- OLAP引擎采用零部署方案，避免额外组件依赖

## 快速上手
1. 首先开发Streamlit原型验证核心功能
2. 逐步完善后端LangGraph + Vanna架构  
3. 最后开发生产级前端界面