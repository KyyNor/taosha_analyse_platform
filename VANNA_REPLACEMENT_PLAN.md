# Vanna 替换方案 - 完整设计文档

**创建时间**: 2024-10-19
**状态**: 规划中
**目标完成时间**: 15 个工作日

---

## 📋 项目概述

### 问题背景

当前项目使用 Vanna 作为 NL2SQL 的核心引擎，主要问题：

1. **向量检索无法控制** - 黑盒操作，无法实现混合检索、关联ID过滤等复杂检索策略
2. **向量库耦合紧密** - 难以从 ChromaDB 迁移到 Qdrant
3. **SQL 生成过程不透明** - 无法细粒度调整提示词
4. **错误学习能力不足** - SQL 生成失败后无法自动改进
5. **代码复杂度高** - 不必要的抽象导致维护成本高

### 解决方案

采用**精简化 + 分层解耦**策略，直接替换 Vanna，获得完整的控制权：

- ✅ 向量库抽象层：支持 ChromaDB 和 Qdrant 一键切换
- ✅ 业务级检索服务：4 个预定义的检索方法，满足各种场景
- ✅ 统一的 LLM 服务：基础层 + 业务层，提示词显式可控
- ✅ 简化的训练管理：根据 `source_type + source_id + update_time` 自动增量更新
- ✅ 完整的数据持久化：支持备份、恢复、失败 SQL 记录

---

## 📐 最终架构设计

### 目录结构

```
backend/services/
├── nlquery_service/
│   └── nl2sql_service.py           # 主工作流（改动最小）
│
├── vector_store/                   # 新增：向量存储抽象层 + 业务检索
│   ├── __init__.py
│   ├── base.py                     # VectorStore 抽象基类
│   ├── chromadb_store.py           # ChromaDB 实现
│   ├── qdrant_store.py             # Qdrant 实现
│   ├── vector_store_factory.py     # 工厂模式支持切换
│   └── nlquery_context_builder.py  # 业务级检索（4个方法）
│
├── embedding_service/              # 保留现有结构（不动）
│   ├── __init__.py
│   ├── base.py
│   ├── local_embedding.py
│   ├── api_embedding.py
│   └── embedding_factory.py
│
├── llm_service/                    # 新增：统一的LLM调用服务
│   ├── __init__.py
│   ├── base_llm_service.py         # 基础服务：原始LLM调用
│   ├── nlquery_llm_service.py      # 业务服务：NL2SQL相关调用
│   └── prompt_template_renderer.py # 移动现有的提示词渲染
│
├── training_service/               # 新增：训练管理服务
│   ├── __init__.py
│   ├── trainer.py                  # 训练管理（核心逻辑）
│   └── training_data_repo.py       # 数据持久化层
│
└── vanna_service/                  # 保留（过渡期）
    └── ...
```

---

## 🔧 核心模块设计

### 1. Vector Store 抽象层

**文件**: `backend/services/vector_store/base.py`

```python
from abc import ABC, abstractmethod
from typing import List, Dict

class VectorStore(ABC):
    """向量存储抽象基类"""

    @abstractmethod
    def add(self, documents: List[str],
            metadatas: List[Dict] = None,
            ids: List[str] = None) -> List[str]:
        """添加文档到向量库，返回向量ID列表"""
        pass

    @abstractmethod
    def search(self, query: str,
               top_k: int = 5,
               filters: Dict = None) -> List[Dict]:
        """搜索相似文档
        返回: [{"id": "...", "content": "...", "score": 0.95, "metadata": {...}}]
        """
        pass

    @abstractmethod
    def delete(self, ids: List[str]):
        """删除文档"""
        pass

    @abstractmethod
    def update(self, ids: List[str],
               documents: List[str],
               metadatas: List[Dict] = None):
        """更新文档"""
        pass

    @abstractmethod
    def clear(self):
        """清空所有数据"""
        pass
```

**实现类**:
- `chromadb_store.py`: 基于 ChromaDB 的实现
- `qdrant_store.py`: 基于 Qdrant 的实现
- `vector_store_factory.py`: 工厂模式，支持一键切换

---

### 2. NLQuery Context Builder（业务检索层）

**文件**: `backend/services/vector_store/nlquery_context_builder.py`

核心方法（4个业务场景）：

#### 方法1: `retrieve_by_semantic_search()`
纯向量检索，根据语义相似度查找相关表和字段

**参数**:
- `user_input: str` - 用户输入
- `top_k: int = 10` - 返回结果数量

**返回**: 格式化的提示词上下文

**使用场景**: 一般性的自然语言查询

#### 方法2: `retrieve_by_relation_id()`
关联ID优先检索，先按关联ID过滤，再向量检索

**参数**:
- `relation_id: str` - 关联ID（如"cust_id"）
- `user_input: str` - 用户输入
- `top_k: int = 10`

**返回**: 格式化的上下文（关联字段优先）

**使用场景**: 用户提到特定关联概念的查询

#### 方法3: `retrieve_by_table_first()`
表优先检索，先返回指定表的完整结构，再向量检索补充

**参数**:
- `table_names: List[str]` - 指定的表名
- `user_input: str` - 用户输入
- `top_k: int = 10`

**返回**: 格式化的上下文（表结构在前）

**使用场景**: 用户明确指定了表名的查询

#### 方法4: `retrieve_hybrid()`
混合检索，组合使用关联ID、表优先、向量检索

**参数**:
- `user_input: str` - 用户输入
- `relation_id: str = None` - 可选的关联ID
- `table_names: List[str] = None` - 可选的表名
- `top_k: int = 10`

**返回**: 格式化的上下文

**使用场景**: 复杂查询，需要多个条件组合

---

### 3. LLM Service（统一的大模型服务）

#### 基础服务: `base_llm_service.py`

```python
class BaseLLMService:
    """基础LLM服务 - 提供原始调用能力"""

    def __init__(self, llm_client, config):
        self.client = llm_client  # OpenAI兼容客户端
        self.config = config  # model, temperature等

    def call(self,
            messages: List[Dict[str, str]],
            temperature: float = None,
            max_tokens: int = None) -> str:
        """调用LLM，返回文本响应"""
        pass

    def call_with_json_mode(self,
                           messages: List[Dict[str, str]]) -> Dict:
        """调用LLM的JSON模式，返回解析后的JSON"""
        pass
```

#### 业务服务: `nlquery_llm_service.py`

```python
class NLQueryLLMService:
    """NL2SQL专用的LLM服务"""

    def __init__(self, base_llm_service: BaseLLMService,
                 template_renderer: PromptTemplateRenderer):
        self.llm = base_llm_service
        self.template_renderer = template_renderer

    # ========== SQL 生成 ==========
    def generate_sql(self, user_input: str, context: str,
                    template_name: str = "sql_generation") -> str:
        """生成SQL查询语句"""
        pass

    # ========== SQL 重试 ==========
    def retry_sql_generation(self, user_input: str, context: str,
                            previous_sql: str, error_message: str) -> str:
        """基于错误信息重新生成SQL"""
        pass

    # ========== 输入验证 ==========
    def validate_input_clarity(self, user_input: str, context: str,
                              sql_query: str = None,
                              flow_type: str = "fast") -> Dict:
        """验证用户输入的清晰度，返回JSON格式结果"""
        pass
```

**关键特点**:
- 基础层只做调用，业务层处理提示词
- 所有调用显式传入提示词，便于调试
- 返回结构化结果（字符串或JSON）

---

### 4. Training Service（训练管理）

#### Trainer: `trainer.py`

```python
class Trainer:
    """训练管理器 - 根据 source_type + source_id + update_time 判断增量更新"""

    def train(self,
             source_type: str,      # table, glossary, relation, sql_qa
             source_id: str,        # 表ID、术语ID等
             documents: List[str],
             metadatas: List[Dict],
             update_time: datetime = None):
        """通用训练方法

        逻辑:
        1. 检查是否已训练过 source_type + source_id
        2. 如果没有 → 直接添加
        3. 如果有 → 比较 update_time
           - 新数据更新 → 删除旧数据，添加新数据
           - 新数据更旧 → 跳过（幂等性保证）
        """
        pass

    def record_failed_sql(self,
                         user_input: str,
                         generated_sql: str,
                         error_message: str,
                         corrected_sql: str = None):
        """记录失败的SQL用于后续学习"""
        pass

    def get_stats(self) -> Dict:
        """获取训练统计信息"""
        pass

    def export_data(self) -> Dict:
        """导出所有训练数据（备份/迁移用）"""
        pass

    def import_data(self, data: Dict):
        """导入训练数据（恢复/迁移用）"""
        pass

    def clear_failed_records(self, older_than: datetime):
        """清理过期的失败记录"""
        pass
```

#### TrainingDataRepository: `training_data_repo.py`

```python
class TrainingDataRepository:
    """训练数据仓库 - 数据持久化层"""

    def save_training_record(self, record: Dict) -> str:
        """保存训练记录"""
        pass

    def get_training_record(self, source_type: str, source_id: str) -> Dict:
        """获取已有的训练记录"""
        pass

    def update_training_record(self, record: Dict):
        """更新训练记录"""
        pass

    def save_failed_sql_record(self, record: Dict):
        """保存失败的SQL记录"""
        pass

    def get_failed_sql_records(self, limit: int = 100) -> List[Dict]:
        """获取失败的SQL记录"""
        pass

    def get_stats(self) -> Dict:
        """获取统计信息"""
        pass

    def export_all(self) -> Dict:
        """导出所有训练数据"""
        pass

    def import_all(self, data: Dict):
        """导入训练数据"""
        pass

    def delete_failed_records_before(self, datetime):
        """删除过期的失败记录"""
        pass
```

---

## 🗄️ 数据库设计

### 表1: training_records（训练记录表）

**用途**: 记录向量库中的所有训练数据及其来源

**字段定义**:

```sql
CREATE TABLE training_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type VARCHAR(50) NOT NULL,        -- 数据来源类型: table, glossary, relation, sql_qa
    source_id VARCHAR(255) NOT NULL,         -- 来源ID: table_id, term_id, relation_id等
    vector_ids TEXT,                         -- JSON数组，向量库中的ID列表
    documents_count INTEGER,                 -- 训练文档数量
    embedding_model VARCHAR(255),            -- 使用的Embedding模型名称
    update_time DATETIME,                    -- 数据最后修改时间（用于判断增量更新）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    modified_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_type, source_id)           -- 同一来源的记录唯一
);

CREATE INDEX idx_training_records_source ON training_records(source_type, source_id);
CREATE INDEX idx_training_records_created ON training_records(created_at);
```

**SQLAlchemy 模型**:

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class TrainingRecord(Base):
    """训练记录表"""
    __tablename__ = 'training_records'

    id = Column(Integer, primary_key=True)
    source_type = Column(String(50), nullable=False)
    source_id = Column(String(255), nullable=False)
    vector_ids = Column(Text)                             # JSON array
    documents_count = Column(Integer)
    embedding_model = Column(String(255))
    update_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    modified_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('source_type', 'source_id', name='uq_training_source'),
        Index('idx_training_source', 'source_type', 'source_id'),
        Index('idx_training_created', 'created_at'),
    )
```

**使用场景**:
- 记录"什么时间"训练了"什么内容"
- 判断是否需要增量更新（比较 update_time）
- 支持向量库迁移时的数据导出/导入
- 版本追踪和审计

---

### 表2: failed_sql_records（失败 SQL 记录表）

**用途**: 记录SQL生成失败的案例，用于后续改进提示词

**字段定义**:

```sql
CREATE TABLE failed_sql_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_input TEXT NOT NULL,                -- 用户原始输入
    generated_sql TEXT NOT NULL,             -- 生成失败的SQL
    error_message TEXT,                      -- 执行时的错误信息
    corrected_sql TEXT,                      -- 纠正后的SQL（可选）
    is_fixed BOOLEAN DEFAULT 0,              -- 是否已纠正
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_failed_sql_created ON failed_sql_records(created_at);
CREATE INDEX idx_failed_sql_fixed ON failed_sql_records(is_fixed);
```

**SQLAlchemy 模型**:

```python
from sqlalchemy import Column, Integer, Text, DateTime, Boolean, Index

class FailedSQLRecord(Base):
    """失败SQL记录表"""
    __tablename__ = 'failed_sql_records'

    id = Column(Integer, primary_key=True)
    user_input = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=False)
    error_message = Column(Text)
    corrected_sql = Column(Text)
    is_fixed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_failed_sql_created', 'created_at'),
        Index('idx_failed_sql_fixed', 'is_fixed'),
    )
```

**使用场景**:
- 自动记录SQL生成失败的案例
- 可视化展示哪些类型的错误最常见
- 用于改进提示词模板
- 支持错误反馈和学习循环

---

## 🔄 工作流集成方式

### 现有工作流改动最小化

```python
# nl2sql_service.py
class NL2SQLService:
    def __init__(self):
        # 向量库 + Embedding
        self.embedding = EmbeddingFactory.create(...)
        self.vector_store = VectorStoreFactory.create(..., embedding=self.embedding)

        # 上下文构建器
        self.context_builder = NLQueryContextBuilder(
            vector_store=self.vector_store,
            embedding_func=self.embedding,
            metadata_service=get_metadata_service(),
            glossary_service=get_glossary_service(),
            relation_config_service=get_relation_field_config_service()
        )

        # LLM 服务
        self.base_llm = BaseLLMService(llm_client, config)
        self.nlquery_llm = NLQueryLLMService(self.base_llm, template_renderer)

        # 训练服务
        self.trainer = Trainer(self.vector_store, TrainingDataRepository(db))

        # 构建工作流
        self.workflow = self._build_workflow()

    def _train_vanna(self):
        """替代 vanna.train() - 使用 trainer.train()"""
        # 训练表结构
        for table in available_tables:
            self.trainer.train(
                source_type="table",
                source_id=table['id'],
                documents=[...],
                metadatas=[...],
                update_time=table.get('updated_at')
            )
        # 训练术语表
        for term in terms:
            self.trainer.train(
                source_type="glossary",
                source_id=term['id'],
                documents=[...],
                metadatas=[...],
                update_time=term.get('updated_at')
            )

    def _build_workflow(self):
        """构建 LangGraph 工作流"""

        @track_node_progress("生成查询语句")
        def generate_sql(state: TaskState) -> TaskState:
            # 1. 构建上下文（选择合适的检索策略）
            context = self.context_builder.retrieve_by_semantic_search(
                state.user_input,
                top_k=10
            )

            # 2. 调用 LLM 生成 SQL
            sql = self.nlquery_llm.generate_sql(
                user_input=state.user_input,
                context=context
            )

            state.sql_query = sql
            return state

        @track_node_progress("执行查询语句")
        def execute_sql(state: TaskState) -> TaskState:
            try:
                result = self.db_service.execute_query(state.sql_query)
                state.execution_result = result.to_dict(orient="records")
            except Exception as e:
                state.error_message = str(e)
                # 自动记录失败的 SQL
                self.trainer.record_failed_sql(
                    user_input=state.user_input,
                    generated_sql=state.sql_query,
                    error_message=str(e)
                )
                state.retry_count = getattr(state, 'retry_count', 0) + 1

            return state

        # ... 工作流构建代码 ...
```

---

## 📋 实施任务清单

### 阶段 1: Vector Store 抽象层（3 天）

- [ ] **Task 1.1**: 创建 `vector_store/base.py` - VectorStore 抽象基类
  - 定义 add, search, delete, update, clear 方法
  - 编写单元测试

- [ ] **Task 1.2**: 创建 `vector_store/chromadb_store.py` - ChromaDB 实现
  - 复用现有 LocalEmbeddingFunction
  - 支持元数据过滤
  - 编写集成测试

- [ ] **Task 1.3**: 创建 `vector_store/qdrant_store.py` - Qdrant 实现
  - 支持内存和网络两种模式
  - 同步元数据过滤逻辑
  - 编写集成测试

- [ ] **Task 1.4**: 创建 `vector_store/vector_store_factory.py` - 工厂模式
  - 支持配置切换
  - 参数验证和错误处理

### 阶段 2: NLQuery Context Builder（2 天）

- [ ] **Task 2.1**: 创建 `vector_store/nlquery_context_builder.py`
  - 实现 `retrieve_by_semantic_search()` 方法
  - 实现 `retrieve_by_relation_id()` 方法
  - 实现 `retrieve_by_table_first()` 方法
  - 实现 `retrieve_hybrid()` 方法
  - 编写详细测试用例

### 阶段 3: LLM Service（2 天）

- [ ] **Task 3.1**: 创建 `llm_service/base_llm_service.py`
  - 实现 `call()` 基础调用
  - 实现 `call_with_json_mode()` JSON模式
  - 错误处理和重试逻辑

- [ ] **Task 3.2**: 创建 `llm_service/nlquery_llm_service.py`
  - 实现 `generate_sql()` 方法
  - 实现 `retry_sql_generation()` 方法
  - 实现 `validate_input_clarity()` 方法
  - 编写测试用例

- [ ] **Task 3.3**: 移动 `prompt_template_renderer.py` 到 `llm_service/`
  - 检查是否可用 LangChain 内置功能替代
  - 调整导入路径

### 阶段 4: Training Service（2.5 天）

- [ ] **Task 4.1**: 创建数据库模型和建表脚本
  - 定义 `TrainingRecord` SQLAlchemy 模型
  - 定义 `FailedSQLRecord` SQLAlchemy 模型
  - 编写迁移脚本（Alembic）

- [ ] **Task 4.2**: 创建 `training_service/training_data_repo.py`
  - 实现所有 CRUD 操作
  - 支持导出/导入功能
  - 编写数据库测试

- [ ] **Task 4.3**: 创建 `training_service/trainer.py`
  - 实现增量更新逻辑
  - 实现失败SQL记录
  - 编写单元测试

### 阶段 5: NL2SQL Service 重构（2 天）

- [ ] **Task 5.1**: 替换 Vanna 实例化
  - 移除 `TaoshaVanna` 导入
  - 添加各个新服务的初始化

- [ ] **Task 5.2**: 更新 `_train_vanna()` 方法
  - 改用 `trainer.train()`
  - 保留原有的训练逻辑

- [ ] **Task 5.3**: 更新工作流节点
  - 替换 `vanna.generate_sql()` 调用
  - 替换 `vanna.submit_prompt()` 调用
  - 集成错误记录

### 阶段 6: 测试与验证（2.5 天）

- [ ] **Task 6.1**: 单元测试
  - VectorStore 各实现类
  - ContextBuilder 各方法
  - LLMService 各方法
  - Trainer 和 Repository

- [ ] **Task 6.2**: 集成测试
  - 向量库检索 + 上下文构建端到端
  - LLM 调用 + SQL 生成端到端
  - 训练数据记录和查询

- [ ] **Task 6.3**: 工作流端到端测试
  - 现有 117 个测试是否仍可通过
  - 性能基准测试

- [ ] **Task 6.4**: 向量库迁移测试
  - ChromaDB → Qdrant 数据导出/导入验证

### 阶段 7: 配置和文档（0.5 天）

- [ ] **Task 7.1**: 更新配置文件
  - `config.yaml` - 添加向量库选择配置
  - `pyproject.toml` - 添加新依赖（qdrant-client, rank-bm25等）

- [ ] **Task 7.2**: 更新文档
  - 更新 `CLAUDE.md` 文件
  - 添加新模块的使用说明
  - 添加向量库迁移指南

---

## ⏱️ 工作量估计

| 阶段 | 任务 | 工作量 | 风险 |
|------|------|--------|------|
| 1 | Vector Store 抽象层 | 3天 | 低 |
| 2 | NLQuery Context Builder | 2天 | 低 |
| 3 | LLM Service | 2天 | 低 |
| 4 | Training Service | 2.5天 | 中 |
| 5 | NL2SQL 重构 | 2天 | 中 |
| 6 | 测试验证 | 2.5天 | 中 |
| 7 | 配置文档 | 0.5天 | 低 |
| **总计** | **14项子任务** | **15天** | - |

**可并行进行**:
- 阶段 1 和阶段 3 可以并行（预计缩短至 10-12 天）
- 各个任务内部子任务可以并行实施

---

## 🚀 关键改进对比

| 方面 | Vanna | 新方案 | 改进度 |
|------|-------|--------|--------|
| 向量检索控制力 | ❌ 完全黑盒 | ✅ 4种策略可选 | ⭐⭐⭐⭐⭐ |
| 向量库灵活性 | ❌ 仅支持 ChromaDB | ✅ 支持多库切换 | ⭐⭐⭐⭐ |
| SQL 生成透明度 | ❌ 内部调用不可见 | ✅ 提示词显式可控 | ⭐⭐⭐⭐⭐ |
| 错误学习能力 | ❌ 无 | ✅ 自动记录和跟踪 | ⭐⭐⭐⭐ |
| 数据持久化 | ❌ 仅在向量库中 | ✅ 完整的 CRUD 接口 | ⭐⭐⭐⭐ |
| 代码复杂度 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 维护成本 | 高 | 低 | ⭐⭐⭐⭐ |

---

## ✅ 验收标准

### 功能验收

- [ ] Vector Store 抽象层完全可用，支持 ChromaDB 和 Qdrant 无缝切换
- [ ] Context Builder 提供 4 种检索方法，结果符合预期
- [ ] LLM Service 正确调用大模型，返回结构化结果
- [ ] Training Service 支持增量更新和失败SQL记录
- [ ] NL2SQL 工作流可正常运行，执行结果与 Vanna 时期一致

### 性能验收

- [ ] 向量检索延迟 ≤ 200ms（top_k=10）
- [ ] 单条 SQL 生成延迟 ≤ 3s（受LLM API限制）
- [ ] 训练数据记录无性能负影响

### 测试验收

- [ ] 现有 117 个测试全部通过
- [ ] 新增测试覆盖率 ≥ 80%
- [ ] 向量库迁移测试通过

### 文档验收

- [ ] `CLAUDE.md` 更新完整
- [ ] 各模块 API 文档完整
- [ ] 迁移指南清晰可执行

---

## 📝 后续优化方向

1. **混合检索增强**
   - 集成 BM25 算法，支持向量+关键词融合
   - 实现检索结果重排（cross-encoder）

2. **智能提示词生成**
   - 基于失败SQL记录自动优化提示词
   - 支持A/B测试不同的提示词版本

3. **多向量库并行**
   - 支持向量在多个库中同时存储（冷热备份）
   - 支持跨库查询

4. **训练数据版本管理**
   - Git 式的训练数据版本控制
   - 支持快速回滚到历史版本

5. **可视化调试工具**
   - Web UI 展示向量检索过程
   - 失败SQL可视化分析

---

## 📞 相关文件

- **本规划文档**: `D:\code\taosha_analyse_platform\VANNA_REPLACEMENT_PLAN.md`
- **现有 Vanna 实现**: `backend/services/vanna_service/`
- **现有 NL2SQL 工作流**: `backend/services/nlquery_service/nl2sql_service.py`
- **配置文件**: `backend/config/config.yaml`
- **项目说明**: `CLAUDE.md`

---

## 🎯 下一步行动

1. ✅ 本规划文档已完成，提交 Git
2. ⏳ 按阶段顺序实施，每个阶段完成后提交 Git
3. ⏳ 定期同步进度和遇到的问题
4. ⏳ 最终进行完整的集成测试和文档更新

