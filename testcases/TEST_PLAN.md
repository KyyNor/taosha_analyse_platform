# 淘沙分析平台 - 后端测试计划（精简版）

## 概述

本测试计划涵盖后端的核心功能和关键流程，采用精简设计以降低维护成本。

## 测试范围

### 1. 单元测试 (Unit Tests)

#### 1.1 查询引擎 (`test_query_engine.py`)
- SQL查询执行和结果返回
- 获取数据库表列表
- 获取表结构信息
- 异常处理（SQL错误、连接失败）

#### 1.2 元数据服务 (`test_metadata_service.py`)
- 表元数据的增删改查
- 字段元数据的增删改查
- 术语表的增删改查（3种类型：概念/SQL问答/字典转换）
- 提示词模板的增删改查
- 关联配置的增删改查

#### 1.3 数据持久化层 (`test_repositories.py`)
- GlossaryTermRepository基础CRUD
- RelationRepository基础CRUD
- MetadataRepository基础CRUD
- 条件查询功能

### 2. 集成测试 (Integration Tests)

#### 2.1 NL2SQL流程 (`test_nl2sql_flow.py`)
- 完整查询流程：输入 → SQL生成 → 验证 → 执行 → 返回结果
- 快速流程(fast)和彻底流程(thorough)
- 异常恢复和重试机制

#### 2.2 元数据管理流程 (`test_metadata_flow.py`)
- 添加表 → 配置字段 → 验证关联 → 查询一致性

#### 2.3 术语表流程 (`test_glossary_flow.py`)
- 添加术语 → 使用术语 → 验证效果

### 3. API测试 (API Tests)

#### 3.1 查询接口 (`test_routes.py`)
- POST /nlquery/generate - 查询生成
- WebSocket /nlquery/ws/task_process - 实时进度推送
- GET /metadata/tables - 元数据查询
- 参数验证和错误响应

## 测试数据

- **测试数据库**：使用内存SQLite和临时DuckDB
- **Mock数据**：预定义的查询语句、表结构、元数据
- **外部API Mock**：OpenAI API、Embedding服务

## 测试工具

```
pytest              # 测试框架
pytest-asyncio      # 异步测试支持
pytest-cov          # 覆盖率分析
pytest-mock         # Mock支持
```

## 执行命令

```bash
# 运行所有测试
pytest testcases/ -v

# 运行特定类型测试
pytest testcases/unit/ -v
pytest testcases/integration/ -v
pytest testcases/api/ -v

# 运行并生成覆盖率报告
pytest testcases/ -v --cov=backend --cov-report=html

# 运行特定测试
pytest testcases/unit/test_metadata_service.py -v
```

## 覆盖率目标

- 核心业务逻辑：≥85%
- 服务层代码：≥80%

## 维护指南

1. **新功能**：添加相应的测试用例
2. **Bug修复**：补充回归测试
3. **API变更**：更新API测试用例
4. **定期检查**：每月检查测试覆盖率和失败用例

