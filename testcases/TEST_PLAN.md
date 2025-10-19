# 淘沙分析平台 - 后端测试计划（完整版）

## 概述

本测试计划全面覆盖后端的核心功能和关键流程，包含单元测试、集成测试和API测试三个层级，确保代码质量和系统稳定性。

## 测试框架结构

```
testcases/
├── pytest.ini                    # pytest配置文件
├── conftest.py                    # 全局fixtures和配置
├── run_tests.bat                  # Windows测试启动脚本
├── run_tests.sh                   # Linux/Mac测试启动脚本
├── TEST_PLAN.md                   # 本文档
├── unit/                          # 单元测试
│   ├── test_query_engine.py      # 查询引擎服务测试
│   ├── test_metadata_service.py   # 元数据服务测试
│   └── test_repositories.py      # 数据持久化层测试
├── integration/                   # 集成测试
│   ├── test_metadata_flow.py     # 元数据管理流程测试
│   └── test_nl2sql_flow.py       # NL2SQL完整流程测试
└── api/                          # API测试
    └── test_routes.py            # API接口测试
```

### 1. 单元测试 (Unit Tests)

#### 1.1 查询引擎 (`test_query_engine.py`) - 15个测试用例
- **DuckDBService测试**:
  - 服务初始化和连接管理
  - SQL查询执行和结果返回
  - 获取数据库表列表和表结构
  - 异常处理（SQL语法错误、连接失败）
  - 复杂查询（JOIN、聚合函数）
  - 数据插入和查询
- **QueryEngineFactory测试**:
  - 创建不同类型的查询引擎
  - 服务类型验证
  - 大小写不敏感处理

#### 1.2 元数据服务 (`test_metadata_service.py`) - 39个测试用例
- **MetadataService** (9个):
  - 表的增删改查操作
  - 可用性过滤
  - DDL语句生成
  - 表信息获取
- **GlossaryService** (10个):
  - 术语表的增删改查
  - 三种类型术语支持（概念/SQL问答/字典转换）
  - 术语搜索和类型过滤
- **PromptTemplateService** (6个):
  - 提示词模板管理
  - 模板验证（占位符匹配）
  - 模板更新和删除
- **RelationFieldConfigService** (4个):
  - 关联配置的CRUD操作
- **DataThemeService** (10个):
  - 数据主题管理
  - 通用主题唯一性约束
  - 主题与表的关联

#### 1.3 数据持久化层 (`test_repositories.py`) - 25个测试用例
- **BaseRepository** (10个):
  - 通用CRUD操作
  - 条件查询和过滤
  - 数据库错误处理
- **GlossaryTermRepository** (6个):
  - 术语的专用查询方法
  - 搜索和相似查找
- **MetadataTableRepository** (4个):
  - 元数据表的专用操作
  - 关联列信息获取
- **其他Repository** (5个):
  - PromptTemplateRepository
  - RelationFieldConfigRepository

### 2. 集成测试 (Integration Tests)

#### 2.1 NL2SQL完整流程 (`test_nl2sql_flow.py`) - 15个测试用例
- **工作流测试**:
  - 快速流程（fast）：先验证后生成SQL
  - 彻底流程（thorough）：先生成SQL后验证
  - 完整查询流程：输入 → SQL生成 → 验证 → 执行 → 返回结果
- **集成功能测试**:
  - 术语表和元数据的协作
  - 提示词模板集成
  - 任务状态追踪
- **错误处理测试**:
  - SQL验证失败处理
  - SQL执行错误处理
  - 重试机制验证
  - 输入清晰度验证
- **复杂场景测试**:
  - 复杂查询工作流
  - 多表JOIN查询
  - 聚合查询和分组

#### 2.2 元数据管理流程 (`test_metadata_flow.py`) - 8个测试用例
- **完整工作流**:
  - 创建表 → 添加字段 → 配置关联 → 验证结果
  - DDL语句生成和验证
  - 可用性过滤功能
- **协作测试**:
  - 术语表与元数据协作
  - 多个术语类型的协作效果
- **数据管理测试**:
  - 列的更新工作流
  - 表和字段的级联删除

#### 2.3 异步查询服务集成 (`test_nl2sql_flow.py`) - 3个测试用例
- **异步功能测试**:
  - 异步查询提交
  - 工作流步骤验证
  - 任务状态追踪集成

### 3. API测试 (API Tests)

#### 3.1 自然语言查询API (`test_routes.py`) - 12个测试用例
- **查询接口测试**:
  - POST /nlquery/submit - 查询提交
  - GET /nlquery/task/{task_id}/status - 任务状态查询
- **WebSocket测试**:
  - WebSocket连接和状态推送
  - 任务切换和错误处理
  - 连接断开处理
- **参数验证测试**:
  - 查询请求模型验证
  - 无效输入处理
  - 缺少字段验证

#### 3.2 元数据管理API (`test_routes.py`) - 12个测试用例
- **表元数据API**:
  - GET /metadata/tables - 获取表列表
  - POST /metadata/tables - 添加表
  - PUT /metadata/tables/{id} - 更新表
  - DELETE /metadata/tables/{id} - 删除表
- **列元数据API**:
  - POST /metadata/columns - 添加列
- **术语表API**:
  - GET /metadata/glossary - 获取术语表
  - POST /metadata/glossary - 添加术语
- **关联配置API**:
  - GET /metadata/relations - 获取关联配置

#### 3.3 API集成测试 (`test_routes.py`) - 5个测试用例
- **集成功能测试**:
  - CORS头设置
  - API版本ing
  - 响应格式一致性
  - 服务器错误处理

## 测试数据和Mock策略

### 测试数据库
- **临时DuckDB**: 每个测试独立数据库，预置样例数据（users、orders、products表）
- **内存SQLite**: 元数据数据库，每个测试用例后自动清理
- **自动清理**: 测试完成后自动删除临时文件

### Mock策略
- **外部API**: OpenAI API、Embedding服务完全Mock
- **Vanna服务**: Mock SQL生成和训练功能
- **异步服务**: Mock异步查询服务
- **查询引擎**: 可选择真实引擎或Mock

### 样例数据
- **查询语句**: 各种复杂度的SQL查询样例
- **元数据**: 完整的表结构和字段信息
- **术语表**: 三种类型的样例术语
- **API请求**: 标准化的测试请求数据

## 测试工具和依赖

### 核心测试框架
```
pytest              # 测试框架
pytest-asyncio      # 异步测试支持
pytest-cov          # 覆盖率分析
pytest-mock         # Mock支持
pytest-timeout      # 超时控制
```

### API测试工具
```
fastapi             # API测试支持
httpx               # 异步HTTP客户端
websockets          # WebSocket测试
```

### 数据库Mock工具
```
duckdb              # 临时数据库
sqlite3             # 内存数据库
sqlalchemy          # ORM测试支持
```

## 执行命令

### 基本执行
```bash
# 运行所有测试
./testcases/run_tests.bat all              # Windows
./testcases/run_tests.sh all               # Linux/Mac

# 运行特定类型测试
./testcases/run_tests.bat unit             # 单元测试
./testcases/run_tests.bat integration      # 集成测试
./testcases/run_tests.bat api              # API测试

# 运行元数据相关测试
./testcases/run_tests.bat metadata
```

### 覆盖率分析
```bash
# 生成覆盖率报告
./testcases/run_tests.bat all --cov

# 查看HTML覆盖率报告
# 打开 htmlcov/index.html
```

### 高级选项
```bash
# 并行执行测试
pytest testcases/ -n auto

# 只运行失败的测试
pytest testcases/ --lf

# 显示最慢的10个测试
pytest testcases/ --duration=10

# 生成Junit格式报告
pytest testcases/ --junitxml=report.xml
```

## 测试统计

### 当前测试覆盖
- **总测试用例**: 117个
- **单元测试**: 79个 (67%)
- **集成测试**: 26个 (22%)
- **API测试**: 12个 (10%)

### 文件分布
- **test_query_engine.py**: 15个测试用例
- **test_metadata_service.py**: 39个测试用例
- **test_repositories.py**: 25个测试用例
- **test_metadata_flow.py**: 8个测试用例
- **test_nl2sql_flow.py**: 18个测试用例
- **test_routes.py**: 12个测试用例

### 覆盖率目标
- **核心业务逻辑**: ≥90%
- **服务层代码**: ≥85%
- **Repository层**: ≥80%
- **API层**: ≥75%

## 维护指南

### 新功能开发
1. **编写测试先行**: 在开发功能前先编写测试用例
2. **TDD流程**: 红绿重构循环
3. **覆盖关键路径**: 确保核心逻辑有测试覆盖

### Bug修复流程
1. **复现Bug**: 编写测试用例复现问题
2. **修复代码**: 修复问题
3. **验证修复**: 确保测试通过
4. **回归测试**: 运行完整测试套件

### API变更管理
1. **更新API测试**: 修改对应的API测试用例
2. **向后兼容**: 确保API变更不破坏现有功能
3. **文档更新**: 同步更新API文档

### 定期维护
1. **每周检查**: 运行完整测试套件，检查失败用例
2. **覆盖率报告**: 定期生成并分析覆盖率报告
3. **性能监控**: 关注测试执行时间，优化慢速测试
4. **依赖更新**: 定期更新测试依赖到最新版本

### CI/CD集成
```yaml
# 示例GitHub Actions配置
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          ./testcases/run_tests.sh all --cov
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

---

**最后更新**: 2025-01-19
**版本**: 1.0
**维护者**: 开发团队

