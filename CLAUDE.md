# CLAUDE.md

本文档为 Claude Code（claude.ai/code）在此仓库中工作时提供指导。

## 项目概览

**淘沙分析平台** 是一个 AI 驱动的商业智能平台，可将自然语言查询转换为 SQL，并提供基于智能体的对话能力和工具集成。

- **后端**：FastAPI 服务，支持自然语言转 SQL、智能体对话和元数据管理
- **前端**：Next.js React 应用，具有实时流式 UI
- **最新提交**：`009e414`（docs: 将 CLAUDE.md 重写为中文）

## 开发命令

### 后端

**设置和安装**
```bash
# 使用 uv 安装依赖（Python 3.11+）
uv sync
```

**运行后端**
```bash
# 启动开发服务器（端口 50020）
./sbackend.sh
# 使用特定工作进程运行（多工作进程设置）
uvicorn backend.main:app --host 0.0.0.0 --port 50020 --workers 4
```

**代码质量**
```bash
# 运行 lint/类型检查（如果配置了）
uv run ruff check backend/
uv run mypy backend/
```

### 前端

**设置和安装**
```bash
cd frontend
npm install
```

**运行前端**
```bash
# 开发服务器（端口 3000）
npm run dev

# 或使用 shell 脚本
../sfrontend.sh

# 生产构建
npm run build
npm start

# 代码检查
npm run lint
```

### 全栈开发

```bash
# 终端 1：后端
./sbackend.sh

# 终端 2：前端
./sfrontend.sh

# 后端 API：http://localhost:50020
# 前端 UI：http://localhost:3000
```

## 架构概览

### 后端架构（`/backend`）

**核心层级：**

1. **API 层** (`/backend/api/`)
   - `nlquery_routes.py` - 自然语言查询端点（异步任务提交、进度轮询、澄清）
   - `agents_routes.py` - 智能体对话，支持流式 SSE
   - `metadata_routes.py` - 表/列元数据 CRUD
   - `user_routes.py` - 用户管理（最小化）
   - **基础路径**：`/api/taosha/v1`

2. **服务层** (`/backend/services/`)
   - **智能体服务** (`agents/agent_service.py`)
     - LangChain ReAct 智能体，具有工具调用能力
     - 内存检查点用于会话管理
     - 工具：FineReport 集成、日期辅助、天气 API 等
     - 中间件：摘要生成、PII 屏蔽、待办列表追踪
     - 输出：服务器发送事件（SSE）流

   - **自然语言查询服务** (`nlquery_service/`)
     - `nl2sql_service.py` - LangGraph 工作流（意图→模式→SQL 生成→执行）
     - `async_query_service.py` - 后台任务管理，支持进度追踪
     - 多轮澄清支持

   - **向量存储** (`vector_store/`)
     - Qdrant 后端用于嵌入
     - 通过相似度搜索进行 RAG 上下文检索
     - 从模式元数据训练向量

   - **大语言模型服务** (`llm_service/`)
     - 支持 OpenAI、Qwen（通过 Dashscope）、LocalAI
     - 通过设置可配置
     - 自然语言查询特定提示

   - **查询引擎** (`query_engine/`)
     - 工厂模式支持 DuckDB（进程内）、Spark SQL（JDBC）、EmptyQueryEngine
     - 通过 `config.yaml` 可配置

   - **元数据服务** (`metadata_service/`)
     - SQLAlchemy 模型用于表、列、术语表、主题、关系
     - 模式缓存和同步

3. **数据库层** (`/backend/database`, `/backend/models`)
   - ORM：SQLAlchemy 2.0
   - 数据库：SQLite（开发）、MySQL（生产）
   - 模型：元数据、主题、术语表、追踪、训练记录
   - 连接池通过 `db_base.py`

4. **基础设施**
   - **配置** (`utils/config.py`) - 基于 YAML 的设置，使用 Pydantic 验证
   - **日志** (`utils/logger.py`) - 通过 Loguru 的结构化日志
   - **可观测性** - Langfuse 追踪集成

**关键启动流程：**
```
加载 YAML 配置 → 验证设置 → 初始化数据库 → 获取启动锁（多工作进程同步）
→ 初始化查询引擎 → 初始化 Playwright → 训练向量（异步）→ 同步元数据
→ 初始化 Langfuse → 启动 Uvicorn
```

### 前端架构（`/frontend`）

**技术栈**：Next.js 14、TypeScript、Tailwind CSS、Radix UI、Vercel AI SDK

**项目布局**：
```
app/(main)/
├── agent/page.tsx           # 智能体对话界面
├── nlquery/page.tsx         # 自然语言查询提交与结果
├── history/page.tsx         # 查询历史
├── favorites/page.tsx       # 保存的查询
├── settings/page.tsx        # 应用设置
└── metadata/                # 元数据管理（表、术语表、主题等）

components/
├── agent/                   # 智能体 UI 组件
├── query/                   # 查询表单和结果
├── generative_ui/          # GenUI 支持
└── ui/                     # Radix UI + 自定义组件

lib/
├── state/                  # React Context（智能体、查询、应用、主题）
├── services/               # API 服务调用（agentService、queryService 等）
└── api.ts                 # Axios 配置和 API 基础 URL
```

**状态管理**：
- React Context API：智能体消息、查询任务、主题、全局应用状态
- 服务器发送事件（SSE）：实时智能体流
- 轮询：异步自然语言查询任务进度

**API 集成**：
- 基础 URL：`/api/taosha/v1`（通过 Next.js 重写代理到 `http://localhost:50020`）
- 流式端点：`POST /agents/chat/stream`（服务器发送事件）
- 异步查询：`POST /nlquery/submit` + 轮询 `GET /nlquery/progress/{task_id}`

### 数据流

**智能体对话流：**
```
前端输入 → agentService.chatStream() [SSE]
→ FastAPI：agents_routes.chat_stream_endpoint()
→ LangChain Agent.astream_events()
→ 工具调用 + LLM 生成
→ 流事件（text、tool_call、tool_result）
→ 前端实时渲染
```

**自然语言查询流：**
```
前端输入 → queryService.submitQuery() [异步任务]
→ FastAPI：submit_query() 生成 task_id
→ 后台：LangGraph 工作流（意图→模式→SQL→执行）
→ 前端轮询：progress/{task_id}
→ 完成时检索结果
```

## 前端设计风格与开发规范

### UI设计系统

**设计语言：**
- **现代扁平化设计**：简洁的界面，减少视觉噪音，专注内容展示
- **明暗双主题支持**：基于CSS变量的完整主题切换系统
- **响应式优先**：移动端优先的设计理念，断点768px
- **无障碍性友好**：语义化HTML和ARIA属性支持

**颜色体系：**
```css
/* 主要颜色 - HSL格式 */
--primary: 222.2 47.4% 11.2%     /* 深蓝灰 - 主要文本和重要操作 */
--secondary: 210 40% 96.1%        /* 浅灰 - 次要信息和背景 */
--accent: 210 40% 96.1%           /* 强调色 - 链接和高亮 */
--destructive: 0 84.2% 60.2%      /* 红色 - 错误和删除操作 */
--muted: 210 40% 96.1%            /* 静默色 - 禁用状态 */
```

**设计Tokens：**
- **间距系统**：基于rem单位，常用值 `space-y-2/4/6`, `p-4/6/8`
- **圆角规范**：`rounded-sm`(0.125rem), `rounded-md`(0.375rem), `rounded-lg`(0.5rem)
- **阴影层级**：`shadow-sm`(轻微), `shadow`(标准), `shadow-md`(较深)
- **字体大小**：从 `text-xs`(0.75rem) 到 `text-2xl`(1.5rem) 的完整尺寸

### 组件架构模式

**分层架构：**
```
components/
├── ui/                    # 基础层 - Radix UI无头组件封装
├── common/               # 通用层 - 跨业务通用组件
├── agent/               # 业务层 - 智能体相关组件
├── query/               # 业务层 - 查询相关组件
└── generative_ui/       # 创新层 - 生成式UI组件
```

**组件设计原则：**
1. **单一职责**：每个组件专注一个功能领域
2. **组合优于继承**：通过组合小组件构建复杂功能
3. **Props接口化**：明确的输入输出定义
4. **类型安全**：完整的TypeScript类型支持

**状态管理策略：**
```typescript
// 全局状态 - React Context
- AppState: 应用全局状态（侧边栏、主题等）
- ThemeState: 主题切换状态
- AgentState: 智能体会话和消息状态
- QueryState: 查询任务状态

// 本地状态 - useState/useReducer
- 组件内部UI状态
- 表单数据状态
- 临时计算状态
```

### 页面布局规范

**布局模式：**
- **双栏布局**：智能体页面使用可折叠侧边栏 + 主内容区
- **单栏布局**：查询页面使用全宽内容布局
- **弹性网格**：基于Flexbox的自适应布局系统

**响应式策略：**
```typescript
// 移动端检测
const MOBILE_BREAKPOINT = 768
const isMobile = useIsMobile()

// 响应式组件
if (isMobile) {
  return <SheetModal />  // 移动端抽屉式
} else {
  return <Sidebar />     // 桌面端固定侧边栏
}
```

**侧边栏设计：**
- **宽度规范**：桌面端 `w-64`，移动端全屏抽屉
- **状态持久化**：使用Cookie记忆展开/折叠状态
- **过渡动画**：平滑的展开/折叠动画效果

### 交互设计模式

**加载状态：**
- **骨架屏**：数据加载时的占位符
- **进度指示器**：长时操作的任务进度显示
- **按钮状态**：`loading` 状态的禁用和视觉反馈

**反馈机制：**
- **Toast通知**：操作结果的轻量级反馈
- **错误边界**：组件级错误捕获和处理
- **确认对话框**：破坏性操作的二次确认

**表单交互：**
- **实时验证**：基于Pydantic模型的即时验证
- **自动保存**：表单数据的本地存储
- **键盘导航**：完整的键盘操作支持

## 后端API架构风格与开发规范

### FastAPI代码风格

**路由定义模式：**
```python
# 模块化路由组织
router = APIRouter(prefix="/nlquery", tags=["自然语言查询"])

# RESTful端点设计
@router.post("/submit")                    # 创建资源
@router.get("/progress/{task_id}")        # 获取状态
@router.post("/clarification/{task_id}")  # 提交澄清
@router.get("/history")                   # 获取历史
```

**依赖注入规范：**
```python
# 标准数据库会话注入
async def endpoint_handler(
    request: RequestModel,
    db: Session = Depends(get_db),                    # 数据库会话
    current_user: User = Depends(get_current_user)    # 用户认证
):
    pass

# 服务层注入
async def complex_handler(
    request: ComplexRequest,
    db: Session = Depends(get_db),
    query_service: QueryService = Depends(get_query_service),
    vector_store: VectorStore = Depends(get_vector_store)
):
    pass
```

**Pydantic模型设计：**
```python
class QueryRequest(BaseModel):
    """自然语言查询请求模型"""
    query: str = Field(
        ...,
        description="自然语言查询内容",
        min_length=1,
        max_length=2000
    )
    flow_type: Literal["fast", "thorough"] = Field(
        "fast",
        description="查询流程类型"
    )
    max_retries: int = Field(
        2,
        description="最大重试次数",
        ge=0,
        le=5
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "查看最近一个月的销售额趋势",
                "flow_type": "fast",
                "max_retries": 2
            }
        }
```

### 服务层架构模式

**目录组织结构：**
```
services/
├── agents/                    # 智能体服务
│   ├── agent_service.py      # 核心智能体服务
│   ├── tools/               # 智能体工具集
│   │   ├── common_tools.py   # 通用工具
│   │   ├── fine_report_tools.py # 报表工具
│   │   └── weather_tools.py  # 天气工具
│   └── middleware.py        # 智能体中间件
├── nlquery_service/          # 自然语言查询服务
│   ├── nl2sql_service.py     # NL2SQL核心逻辑
│   ├── async_query_service.py # 异步任务管理
│   └── clarification_service.py # 澄清服务
├── metadata_service/         # 元数据服务
├── query_engine/            # 查询引擎
├── vector_store/            # 向量存储
├── llm_service/             # 大语言模型服务
└── tracking_service/        # 追踪服务
```

**业务逻辑分离原则：**
1. **API层**：仅负责HTTP请求响应处理，不包含业务逻辑
2. **服务层**：封装核心业务逻辑，提供高级API
3. **数据层**：负责数据持久化和检索
4. **工具层**：提供可复用的通用功能

### 数据访问层模式

**SQLAlchemy 2.0 ORM设计：**
```python
class MetadataTable(Base):
    """元数据表模型"""
    __tablename__ = "metadata_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 关系定义
    columns: Mapped[list["MetadataColumn"]] = relationship(
        "MetadataColumn",
        back_populates="table",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<MetadataTable(id={self.id}, name='{self.name}')>"
```

**数据库会话管理：**
```python
# 依赖注入模式 - 推荐使用
def get_db() -> Generator[Session, None, None]:
    """FastAPI依赖注入的数据库会话管理"""
    db = SessionLocal()
    try:
        yield db
        db.commit()  # 请求成功时自动提交
    except Exception:
        db.rollback()  # 异常时回滚
        raise
    finally:
        db.close()

# 上下文管理器模式 - 用于后台任务
@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """上下文管理器模式的数据库会话"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

**Repository模式实现：**
```python
class BaseRepository(Generic[T]):
    """基础仓储类"""
    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model

    def get(self, id: int) -> Optional[T]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, obj_data: dict) -> T:
        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

class MetadataTableRepository(BaseRepository[MetadataTable]):
    """元数据表仓储"""
    def __init__(self, db: Session):
        super().__init__(db, MetadataTable)

    def get_by_name(self, name: str) -> Optional[MetadataTable]:
        return self.db.query(MetadataTable).filter(
            MetadataTable.name == name
        ).first()
```

### 配置管理与错误处理

**配置管理架构：**
```python
class ConfigManager:
    """配置管理器 - YAML + 环境变量 + Pydantic"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) or Path("config/config.yaml")
        self._config_data = self._load_config()
        self.settings = self._create_settings()

    class Settings(BaseSettings):
        """Pydantic设置模型"""
        # 应用基础配置
        app_name: str = Field(default="淘沙分析平台")
        app_version: str = Field(default="1.0.0")
        debug: bool = Field(default=False)

        # 数据库配置
        database_url: str = Field(...)
        database_pool_size: int = Field(default=5)
        database_max_overflow: int = Field(default=10)

        # 外部服务配置
        openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
        qwen_api_key: Optional[str] = Field(None, env="QWEN_API_KEY")

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
```

**日志记录系统：**
```python
class LoggerManager:
    """基于Loguru的结构化日志管理"""

    def __init__(self):
        self._setup_logger()

    def _setup_logger(self):
        # 移除默认处理器
        logger.remove()

        # 控制台处理器 - 带颜色和格式化
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            colorize=True,
            backtrace=True,
            diagnose=True
        )

        # 文件处理器 - 按级别和日期分割
        logger.add(
            "logs/app_{time:YYYY-MM-DD}.log",
            level="DEBUG",
            rotation="00:00",
            retention="30 days",
            compression="zip",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"
        )

        # 错误文件处理器
        logger.add(
            "logs/error_{time:YYYY-MM-DD}.log",
            level="ERROR",
            rotation="00:00",
            retention="30 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"
        )
```

## 关键技术

| 组件 | 技术 | 用途 |
|------|------|------|
| 后端 Web | FastAPI 0.116 | REST API 框架 |
| 智能体/工作流 | LangChain 1.0、LangGraph 1.0 | LLM 编排和工作流 |
| 数据库 ORM | SQLAlchemy 2.0 | 元数据和追踪持久化 |
| 向量数据库 | Qdrant 客户端 1.7 | 嵌入和 RAG 上下文 |
| 查询引擎 | DuckDB 1.2 | 本地 OLAP 查询 |
| LLM 支持 | OpenAI、Qwen、LocalAI | 语言模型（可配置） |
| 可观测性 | Langfuse 3.9 | 追踪和监控 |
| 前端 | Next.js 14、React 18 | Web UI 框架 |
| 样式 | Tailwind CSS、Radix UI | UI 组件和样式 |
| 流 | Vercel AI SDK 5.0 | 客户端 SSE/流 |
| HTTP | Axios 1.7 | 前端 API 调用 |

## 配置

配置基于 `backend/utils/config.py` 中的 YAML：

**关键设置**：
- `app.workers` - Uvicorn 工作进程数
- `database.type` - sqlite 或 mysql
- `query_engine.type` - duckdb、spark 或 empty
- `llm.provider` - openai、qwen、localai
- `vector_store.type` - qdrant
- `qdrant.url` - 向量数据库连接
- `embeddings.model` - 嵌入模型路径/端点
- `tracing.provider` - langfuse 或 phoenix
- `finereport_base_url` - FineReport 集成

通过环境变量或运行时 YAML 文件加载。

## 常见开发任务

### 添加新的智能体工具

1. 在 `backend/services/agents/tools/` 中创建工具函数（例如 `new_tool.py`）
2. 在 `backend/services/agents/agent_service.py` 的工具列表中注册
3. 传递给智能体构造函数：`tools=[get_report_sample, new_tool, ...]`
4. 工具通过 LangChain 工具调用机制自动可被智能体调用

### 添加新的查询流阶段

1. 在 `backend/services/nlquery_service/nl2sql_service.py` 中添加新节点/函数
2. 通过 `graph.add_node()` 和 `graph.add_edge()` 在 LangGraph 工作流中连接
3. 在节点中更新执行追踪/日志

### 修改 API 端点

- 后端路由在 `/backend/api/`
- 前端服务在 `/frontend/lib/services/`
- API 基础 URL：`NEXT_PUBLIC_API_BASE`（前端环境变量）
- 代理重写在 `frontend/next.config.mjs`

### 更新元数据模式

- `/backend/models/` 中的模型
- 如需使用 Alembic 迁移（目前未使用；模式编辑直接应用）
- 重新同步元数据：调用 `metadata_service.sync_from_source()`

### 调试智能体会话

- 日志：后端中 `loguru` 的结构化日志
- 追踪：查看 Langfuse 仪表板获取完整执行跟踪
- 会话状态：检查点存储每个 `session_id` 的状态
- 前端开发工具：在网络选项卡中检查 SSE 事件

## 重要的实现细节

### 多工作进程同步

后端使用启动锁（`backend/utils/startup_lock.py`）来防止多个 uvicorn 工作进程重复初始化。只有第一个工作进程执行向量训练等昂贵任务。

### 异步任务处理

自然语言查询作为后台任务通过 `asyncio` 任务队列运行。前端使用长轮询（30 秒超时）检查进度。任务状态在 `OperationTracker` 中追踪。

### 会话管理

- **智能体**：每个 `session_id` 的内存检查点（临时的，重启后丢失）
- **查询**：通过 UUID + 数据库日志进行任务追踪

### 向量数据库集成

- 嵌入存储在 Qdrant 中以进行快速相似度搜索
- 用于自然语言转 SQL 的 RAG 上下文检索
- 从启动时的元数据模式训练

### 流式架构

- **智能体**：SSE（服务器发送事件）用于实时令牌流
- **前端**：使用 `text`、`tool_call`、`tool_result` 事件类型解析 SSE 事件流
- Vercel AI SDK 提供解析辅助程序

## 测试

未配置正式测试套件。对于手动测试：
- 后端：使用 FastAPI `/docs`（Swagger UI 在 `http://localhost:50020/docs`）
- 前端：浏览器开发者工具
- 集成：使用 `testcases/` 目录中的示例查询

## 部署

**Docker 就绪**：
- 后端：`uvicorn backend.main:app --host 0.0.0.0 --port 50020`
- 前端：`next start --host 0.0.0.0 --port 3000`
- 环境：使用 `.env` 或容器环境变量

**多工作进程设置**：设置 `uvicorn --workers N` 进行水平扩展

**数据库**：在配置中配置 `database.url` 以支持外部 MySQL

**向量数据库**：将 `qdrant.url` 指向远程 Qdrant 实例

## 文件结构参考

```
/backend
├── main.py                     # FastAPI 应用 + 启动/关闭
├── api/                        # 路由处理器
├── services/                   # 业务逻辑（智能体、nlquery 等）
├── models/                     # SQLAlchemy ORM 模型
├── database/                   # 数据库连接和会话管理
├── utils/                      # 配置、日志、启动锁
└── schemas/                    # Pydantic 请求/响应模型

/frontend
├── app/(main)/                 # 页面路由
├── components/                 # React 组件
├── lib/
│   ├── state/                 # React Context 提供程序
│   ├── services/              # API 服务函数
│   ├── api.ts                 # Axios 实例
│   └── utils/                 # 工具函数
└── public/                    # 静态资源
```

### 新增内容概要

#### 1. 前端设计风格与开发规范

**新增章节**：
- **UI设计系统**：完整的颜色体系、设计Tokens、响应式策略
- **组件架构模式**：分层架构、状态管理策略、组件设计原则
- **页面布局规范**：双栏/单栏布局、移动端适配、侧边栏设计
- **交互设计模式**：加载状态、反馈机制、表单交互

**技术亮点**：
- 明暗双主题的CSS变量系统
- 基于Radix UI的无头组件架构
- React Context + 本地状态的混合状态管理
- 移动端优先的响应式设计（768px断点）

#### 2. 后端API架构风格与开发规范

**新增章节**：
- **FastAPI代码风格**：路由定义、依赖注入、Pydantic模型设计
- **服务层架构模式**：目录组织、业务逻辑分离、服务通信
- **数据访问层模式**：SQLAlchemy 2.0 ORM、会话管理、Repository模式
- **配置管理与错误处理**：YAML配置管理、Loguru日志、异常处理策略

**技术亮点**：
- RESTful API设计规范和模块化路由
- 基于FastAPI的依赖注入系统
- SQLAlchemy 2.0现代ORM特性应用
- 多层异常处理和结构化日志记录

### 功能更新亮点

#### 前端功能增强

**会话管理系统**：
- 聊天会话的CRUD操作和持久化存储
- 智能分组和历史对话时间显示（`4edc191`）
- 移动端优化的侧边栏体验（`5d1b0ed`）

**生成式UI组件**：
- Markdown渲染组件（`7a6f264`）
- 实时任务进度显示的TodoList组件（`c7b46cf`, `4aa2e78`）
- 可折叠的工具结果展示组件（`0976277`）

**设计系统统一**：
- 统一的UI组件阴影效果（`ca9120d`）
- 整体UI设计和交互体验优化（`954cb78`）

#### 后端功能增强

**Agent系统优化**：
- 聊天会话和消息模型完善（`3f63e91`）
- Agent工具调用解析问题修复（`4733669`）
- trace_id管理优化（`4a2c6df`）

**数据分析工具**：
- 新增指标数据获取工具（`e8f1a64`）
- 完善生成式图表功能（`f5827bc`）

### 技术架构演进

#### 前端架构演进
- **状态管理规范化**：明确React Context使用场景和最佳实践
- **组件分层标准化**：UI层、业务层、通用层的清晰划分
- **移动端适配完善**：响应式策略和交互优化

#### 后端架构演进
- **依赖注入标准化**：统一的`db: Session = Depends(get_db)`模式
- **服务层解耦**：清晰的业务逻辑与API层分离
- **配置管理完善**：YAML + 环境变量 + Pydantic的三层配置体系

### 开发规范确立

#### 前端开发规范
1. **设计系统**：基于Tailwind CSS的原子化设计，完整的颜色和间距规范
2. **组件原则**：单一职责、组合优先、类型安全
3. **状态管理**：全局状态用Context，本地状态用hooks
4. **响应式设计**：移动端优先，断点768px

#### 后端开发规范
1. **API设计**：RESTful规范，模块化路由，统一响应格式
2. **依赖注入**：标准化的FastAPI依赖注入模式
3. **数据访问**：SQLAlchemy 2.0 ORM，Repository模式
4. **错误处理**：分层异常处理，结构化日志记录

### 最佳实践总结

#### 代码组织
- **前端**：分层组件架构，明确的职责划分
- **后端**：四层架构（API层、服务层、数据层、工具层）
- **配置**：集中化配置管理，环境变量覆盖

#### 开发流程
- **类型安全**：前端TypeScript，后端Pydantic模型验证
- **错误处理**：全局异常捕获，用户友好的错误信息
- **日志记录**：结构化日志，多级别输出，文件轮转
- **测试策略**：API文档化，前端组件可测试性

这次更新为项目建立了完整的开发规范和设计体系，为后续的功能开发和团队协作提供了清晰的指导。

- **Latest Commit**: `5d1b0ed` (cleanup: 清理历史文件和旧备份)
