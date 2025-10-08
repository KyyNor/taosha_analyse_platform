# 淘沙分析平台 - 项目总览

## 🎯 项目概述

淘沙分析平台是一个基于自然语言的企业级数据分析平台，旨在让业务用户通过自然语言查询数据，无需掌握SQL技能就能进行复杂的数据分析。

### 核心价值
- **降低数据分析门槛**：用自然语言代替SQL，让业务用户直接参与数据分析
- **提升分析效率**：AI驱动的智能查询，快速生成准确的SQL语句
- **保证数据安全**：企业级权限控制，确保数据访问的安全性
- **增强分析体验**：实时交互、可视化展示、历史管理等完整功能

## 🏗️ 系统架构

### 整体架构图
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端应用      │    │   后端API       │    │   数据存储      │
│  Vue3 + TS     │◄──►│  FastAPI       │◄──►│  MySQL/SQLite   │
│  DaisyUI       │    │  + LangGraph    │    │  ChromaDB       │
│  WebSocket     │    │  + Vanna        │    │  DuckDB         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 技术栈详解

#### 前端技术栈
- **Vue3 + Composition API**: 现代化的前端框架，提供响应式数据绑定
- **TypeScript**: 类型安全，提高代码质量和开发效率
- **DaisyUI + Tailwind CSS**: 美观的UI组件库和原子化CSS框架
- **Pinia**: 轻量级状态管理，替代Vuex
- **Axios**: HTTP客户端，处理API请求
- **WebSocket**: 实时通信，支持查询进度推送

#### 后端技术栈
- **FastAPI**: 高性能异步Web框架，自动生成API文档
- **SQLAlchemy**: 现代化的Python ORM，支持异步操作
- **LangGraph**: AI工作流编排框架，处理复杂的NL2SQL流程
- **Vanna**: 专业的NL2SQL框架，提供基础的语言模型能力
- **ChromaDB**: 向量数据库，用于语义检索和相似SQL查找
- **JWT**: 无状态的身份认证机制

#### 数据层技术栈
- **MySQL**: 生产环境主数据库，存储业务数据
- **SQLite**: 开发环境数据库，便于快速开始
- **DuckDB**: 高性能分析引擎，处理复杂查询
- **ChromaDB**: 向量存储，支持语义检索

## 🎨 功能模块详解

### 1. 智能查询模块
**核心功能**: 将自然语言转换为SQL并执行

**技术实现**:
- 基于LangGraph的多步骤工作流
- 结合Vanna框架的NL2SQL能力
- ChromaDB向量检索相似查询
- 实时进度推送和状态管理

**关键文件**:
- `backend/services/nl2sql/workflow_engine.py` - 工作流引擎
- `backend/services/nl2sql/vanna_service.py` - Vanna框架封装
- `frontend/src/views/Query.vue` - 查询界面
- `frontend/src/stores/query.ts` - 查询状态管理

### 2. 元数据管理模块
**核心功能**: 管理数据表、字段、术语和主题

**技术实现**:
- RESTful API设计
- 层次化的数据组织结构
- 细粒度的权限控制
- 响应式的前端界面

**关键文件**:
- `backend/models/metadata_models.py` - 数据模型
- `backend/api/v1/metadata.py` - API接口
- `frontend/src/views/metadata/` - 前端界面

### 3. 权限管理模块
**核心功能**: RBAC权限模型，用户、角色、权限管理

**技术实现**:
- 基于JWT的无状态认证
- RBAC角色权限模型
- 中间件权限验证
- 细粒度权限控制

**关键文件**:
- `backend/utils/permissions.py` - 权限中间件
- `backend/api/v1/users.py` - 用户管理API
- `backend/api/v1/roles.py` - 角色管理API
- `backend/scripts/init_permissions.py` - 权限初始化

### 4. 实时通信模块
**核心功能**: WebSocket实时通信，查询进度推送

**技术实现**:
- WebSocket连接管理
- 任务订阅机制
- 自动重连和心跳
- 事件驱动的消息处理

**关键文件**:
- `backend/services/websocket/manager.py` - WebSocket管理器
- `frontend/src/services/websocket.ts` - 前端WebSocket服务

## 📊 数据库设计

### 核心表结构

#### 用户权限相关
- `users` - 用户基本信息
- `roles` - 角色定义
- `permissions` - 权限定义
- `user_roles` - 用户角色关联
- `role_permissions` - 角色权限关联

#### 元数据相关
- `data_themes` - 数据主题
- `data_tables` - 数据表
- `data_fields` - 数据字段
- `business_glossary` - 业务术语

#### 查询相关
- `query_history` - 查询历史
- `query_favorites` - 收藏查询
- `query_tasks` - 查询任务

### 数据关系图
```
users ──────┐
           │
           ├── user_roles ──── roles ──── role_permissions ──── permissions
           │
           └── query_history ──── data_themes ──── data_tables ──── data_fields
```

## 🔄 业务流程

### 1. 用户查询流程
```
用户输入自然语言 → 主题/表选择 → 提交查询 → AI分析 → 生成SQL → 执行查询 → 返回结果
```

### 2. 权限验证流程
```
用户请求 → JWT验证 → 权限检查 → 资源访问 → 返回结果
```

### 3. 数据管理流程
```
元数据录入 → 权限分配 → 主题关联 → 查询使用 → 结果反馈
```

## 🚀 核心特性

### 1. 智能化程度高
- **语义理解**: 基于大语言模型的自然语言理解
- **上下文感知**: 结合元数据和历史查询的上下文分析
- **自动优化**: 查询性能优化和结果缓存

### 2. 企业级特性
- **权限控制**: 细粒度的RBAC权限模型
- **数据安全**: 多层次的数据访问控制
- **审计日志**: 完整的操作日志记录

### 3. 用户体验优秀
- **实时反馈**: WebSocket实时进度推送
- **可视化展示**: 丰富的图表和表格展示
- **历史管理**: 查询历史和收藏功能

### 4. 可扩展性强
- **模块化设计**: 清晰的模块划分和接口定义
- **插件化架构**: 支持查询引擎和AI模型的扩展
- **云原生**: 支持容器化部署和微服务架构

## 📈 性能特点

### 1. 查询性能
- **DuckDB引擎**: 针对分析场景优化的查询引擎
- **并发处理**: 异步架构支持高并发查询
- **结果缓存**: 智能缓存常用查询结果

### 2. 系统性能
- **异步架构**: FastAPI + SQLAlchemy异步支持
- **连接池**: 数据库连接池管理
- **静态资源**: 前端资源CDN加速

### 3. AI性能
- **向量检索**: ChromaDB高效的向量相似度搜索
- **模型优化**: 针对企业场景优化的prompt设计
- **缓存机制**: AI结果缓存减少重复计算

## 🔧 部署和维护

### 开发环境
- 一键启动脚本
- 热重载支持
- 完整的调试信息

### 生产环境
- Docker容器化部署
- Nginx反向代理
- Systemd服务管理
- 自动化备份脚本

### 监控和日志
- 结构化日志输出
- 性能指标监控
- 错误报警机制

## 🎯 使用场景

### 1. 业务分析师
- 快速生成数据报表
- 探索性数据分析
- 业务指标监控

### 2. 数据科学家
- 数据预处理
- 特征工程
- 模型验证

### 3. 管理层
- 业务仪表板
- 决策支持
- 趋势分析

## 🔮 未来规划

### 短期目标 (3-6个月)
- [ ] 支持更多数据库类型 (PostgreSQL, ClickHouse等)
- [ ] 增强图表可视化能力
- [ ] 移动端适配

### 中期目标 (6-12个月)
- [ ] 机器学习模型集成
- [ ] 自动化报表生成
- [ ] 多租户支持

### 长期目标 (1年+)
- [ ] 实时数据流处理
- [ ] 自然语言生成报告
- [ ] 企业级数据治理

## 🤝 贡献指南

### 开发者
1. Fork项目仓库
2. 创建功能分支
3. 遵循代码规范
4. 编写测试用例
5. 提交Pull Request

### 代码规范
- Python: PEP 8
- TypeScript: ESLint + Prettier
- 提交信息: Conventional Commits

### 测试要求
- 单元测试覆盖率 > 80%
- 集成测试覆盖主要业务流程
- 性能测试验证关键指标

---

📞 **联系方式**: 如有问题或建议，请创建Issue或联系开发团队

⭐ **项目地址**: [GitHub Repository](https://github.com/your-org/taosha-analyse-platform)

📚 **文档中心**: [在线文档](https://docs.taosha-platform.com)