# DB-GPT 架构深度解析：Action vs Resource vs Tool

## 1️⃣ 核心概念对比

### Action（动作）
**定义**：Agent 可以执行的**动作逻辑**
**抽象层级**：业务逻辑
**依赖**：需要 Resource 才能执行

```python
class Action(ABC, Generic[T]):
    """Base Action class for defining agent actions."""
    
    def __init__(self, language: str = "en"):
        self.resource: Optional[Resource] = None
    
    def init_resource(self, resource: Optional[Resource]):
        """初始化资源"""
        self.resource = resource
    
    @abstractmethod
    async def run(
        self,
        ai_message: str,
        resource: Optional[AgentResource] = None,
        rely_action_out: Optional[ActionOutput] = None,
    ) -> ActionOutput:
        """执行动作"""
        pass
```

**示例**：
```python
class SqlQueryAction(Action):
    """SQL 查询动作"""
    
    @property
    def resource_need(self):
        return ResourceType.DB  # 需要数据库资源
    
    async def run(self, ai_message, resource, rely_action_out):
        # 解析 LLM 输出的 SQL
        sql = self._extract_sql(ai_message)
        
        # 使用 Resource 执行查询
        result = await resource.execute(sql)
        
        return ActionOutput(
            content=f"查询成功，返回 {len(result)} 条记录",
            is_exe_success=True,
            action="sql_query",
            observations=str(result)
        )
```

### Resource（资源）
**定义**：Agent 可以使用的**资源**
**抽象层级**：基础设施
**类型**：Database, Knowledge, Tool, Plugin, 等

```python
class Resource(ABC, Generic[P]):
    """Resource for the agent."""
    
    @classmethod
    @abstractmethod
    def type(cls) -> ResourceType:
        """返回资源类型"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """返回资源名称"""
        pass
    
    async def preload_resource(self):
        """预加载资源"""
        pass
```

**示例**：
```python
class DatabaseResource(Resource):
    """数据库资源"""
    
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.connector = None
    
    @classmethod
    def type(cls):
        return ResourceType.DB
    
    @property
    def name(self):
        return self.db_name
    
    async def preload_resource(self):
        """预加载数据库连接"""
        self.connector = await create_connector(self.db_name)
    
    async def execute(self, sql: str):
        """执行 SQL"""
        return await self.connector.query(sql)
```

### Tool（工具）
**定义**：一种特殊的 Resource，封装**可执行函数**
**抽象层级**：函数调用
**特点**：可以被包装成 Action

```python
class BaseTool(Resource[ToolResourceParameters]):
    """Base class for a tool."""
    
    @classmethod
    def type(cls) -> ResourceType:
        return ResourceType.Tool
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @property
    @abstractmethod
    def args(self) -> Dict[str, ToolParameter]:
        """参数定义"""
        pass
    
    def execute(self, *args, **kwargs):
        """同步执行"""
        pass
    
    async def async_execute(self, *args, **kwargs):
        """异步执行"""
        pass
```

**示例**：
```python
@tool(description="执行 SQL 查询")
def sql_query_tool(sql: str, db_name: str) -> str:
    """执行 SQL 查询并返回结果"""
    connector = get_connector(db_name)
    result = connector.query(sql)
    return json.dumps(result)

# Tool 是 Resource 的一种
assert isinstance(sql_query_tool._tool, Resource)
assert sql_query_tool._tool.type() == ResourceType.Tool
```

---

## 2️⃣ 三者关系图

```
┌─────────────────────────────────────────────────┐
│              ConversableAgent                   │
│  - profile: ProfileConfig                       │
│  - actions: List[Action]                        │
│  - resource: Resource                           │
│  - memory: AgentMemory                          │
└─────────────────────────────────────────────────┘
                      │
                      ├─ actions → [Action1, Action2, Action3]
                      │               │
                      │               └─ 需要依赖 resource
                      │
                      └─ resource → ResourcePack
                                      │
                                      ├─ DatabaseResource
                                      ├─ KnowledgeResource
                                      └─ ToolPack (包含多个 Tool)
```

---

## 3️⃣ 执行流程详解

### 完整流程

```python
async def generate_reply(self, message: AgentMessage):
    """生成回复的完整流程"""
    
    # 1️⃣ Thinking（思考）- LLM 决定做什么
    llm_reply = await self.thinking(
        thinking_messages=[],
        sender=user_agent,
    )
    # llm_reply: "我需要查询最近7天的交易数据"
    
    # 2️⃣ Review（审查）- 检查 LLM 回复是否合法
    approve, comments = await self.review(llm_reply, self)
    # approve: True
    
    # 3️⃣ Act（执行）- 执行 Action
    action_output = await self.act(
        message=AgentMessage(content=llm_reply),
        sender=user_agent,
    )
    # action_output: ActionOutput(content="查询成功...")
    
    # 4️⃣ Verify（验证）- 验证执行结果
    check_pass, reason = await self.verify(
        message=AgentMessage(content=llm_reply),
        sender=user_agent,
    )
    # check_pass: True
    
    return action_output
```

### Act 方法详解

```python
async def act(self, message: AgentMessage) -> ActionOutput:
    """执行 Action"""
    last_out = None
    
    # 遍历所有 Action（按顺序执行）
    for i, action in enumerate(self.actions):
        # 1. 解析 Action
        real_action = action.parse_action(
            ai_message=message.content,  # LLM 的回复
            default_action=action,
        )
        
        # 2. 执行 Action
        last_out = await real_action.run(
            ai_message=message.content,
            resource=self.resource,  # 传入 Resource
            rely_action_out=last_out,  # 依赖上一个 Action 的输出
        )
    
    return last_out
```

---

## 4️⃣ 与 LangChain/淘沙的对比

### LangChain 架构

```python
# LangChain: Tool 直接绑定到 Agent
agent = Agent(
    tools=[
        search_tool,
        calculator_tool,
    ]
)

# 执行流程
user_input → Agent → LLM 选择 Tool → 执行 Tool → 返回结果
```

### DB-GPT 架构

```python
# DB-GPT: Action + Resource 分离
agent = ConversableAgent(
    actions=[SqlQueryAction(), DataAnalysisAction()],
    resource=ResourcePack([
        DatabaseResource(db_name="taosha_db"),
        ToolPack([search_tool, calculator_tool]),
    ])
)

# 执行流程
user_input → Agent → LLM 思考 → 执行 Action → Action 使用 Resource → 返回结果
```

### 淘沙当前架构

```python
# 淘沙: LangChain @tool
@tool
def sql_query_tool(sql: str) -> str:
    """执行 SQL 查询"""
    return query_engine.run(sql)

agent_service = AgentService(
    tools=[sql_query_tool, chart_tool],
    system_prompt="...",
)

# 执行流程
user_input → AgentService → LLM 选择 Tool → 执行 Tool → 返回结果
```

---

## 5️⃣ 关键问题：是否有意图识别？

### ❌ 不是独立的意图识别步骤

DB-GPT **没有**在任务开始前单独的意图识别步骤。

### ✅ 意图识别集成在 Thinking 阶段

意图识别发生在 **LLM 思考过程中**：

```python
async def thinking(self, messages: List[AgentMessage], sender: Agent):
    """思考阶段 - 包含意图识别"""
    
    # 1. 构建 Prompt
    prompt = await self.build_prompt(
        question=messages[-1].content,
        most_recent_memories=await self.read_memories(),
        resource_vars=self.resource.get_resource_prompt(),
    )
    # Prompt 包含：
    # - 用户问题
    # - 历史记忆
    # - 可用资源
    # - Agent 角色和约束
    
    # 2. LLM 生成回复（包含意图识别）
    llm_reply = await self.llm_client.generate(prompt)
    # LLM 会根据 Prompt 自动识别意图：
    # - 用户想查询数据？→ 生成 SQL
    # - 用户想生成图表？→ 生成图表配置
    # - 用户想分析数据？→ 生成分析思路
    
    return llm_reply
```

### 示例：意图识别过程

**用户问题**："查询最近7天的交易总额"

**Prompt**：
```
你是一个数据库专家，目标是帮助用户查询数据。

可用资源：
- Database: taosha_db（包含交易表）

用户问题：查询最近7天的交易总额

请思考并生成 SQL：
```

**LLM 回复**（Thinking 阶段）：
```json
{
  "thoughts": "用户想查询交易总额，需要使用 SUM 函数和 DATE 条件",
  "sql": "SELECT SUM(amount) FROM transactions WHERE transaction_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
}
```

**Act 阶段**：
```python
# SqlQueryAction 解析 LLM 回复
sql = extract_sql(llm_reply)
# SELECT SUM(amount) FROM transactions ...

# 使用 DatabaseResource 执行
result = await self.resource.execute(sql)
# 返回：1234567

# 返回 ActionOutput
return ActionOutput(
    content="查询成功，最近7天交易总额为 1,234,567 元",
    is_exe_success=True,
    observations="1,234,567"
)
```

---

## 6️⃣ 总结对比表

| 特性 | LangChain | DB-GPT | 淘沙 |
|------|-----------|--------|------|
| **工具定义** | @tool 装饰器 | BaseTool 类 | @tool 装饰器 |
| **资源管理** | 无统一管理 | Resource + ResourcePack | 无统一管理 |
| **动作抽象** | Tool = Action | Action + Resource 分离 | Tool = Action |
| **意图识别** | LLM Tool 选择 | LLM Thinking 阶段 | LLM Tool 选择 |
| **资源预加载** | 无 | preload_resource() | 无 |
| **依赖检查** | 运行时错误 | 启动时 check_available() | 运行时错误 |
| **记忆系统** | ConversationBufferMemory | 三层架构（短期/长期/GPTs） | SQLAlchemy 持久化 |

---

## 7️⃣ 对淘沙的建议

### 当前架构（已足够好）

```python
@tool
def sql_query_tool(sql: str) -> str:
    """执行 SQL 查询"""
    return query_engine.run(sql)

@tool
def chart_render_tool(data: str, chart_type: str) -> str:
    """渲染图表"""
    return chart_service.render(data, chart_type)

agent = AgentService(
    tools=[sql_query_tool, chart_render_tool],
)
```

### 建议增强（借鉴 DB-GPT）

#### 1. 引入 Resource 管理

```python
class TaoshaResourceManager:
    """淘沙资源管理器"""
    
    async def preload_resource(self):
        """预加载资源"""
        # 1. 查询引擎
        self.query_engine = QueryEngineService()
        await self.query_engine.initialize()
        
        # 2. 元数据
        self.metadata = MetadataService()
        await self.metadata.load_all_tables()
        
        # 3. 向量存储
        self.vector_store = QdrantVectorStore()
        await self.vector_store.check_connection()
        
        logger.info("资源预加载完成")

# 使用
resource_manager = TaoshaResourceManager()
await resource_manager.preload_resource()
```

#### 2. 分离 Action 和 Resource（可选）

```python
class SqlQueryAction(Action):
    """SQL 查询动作"""
    
    @property
    def resource_need(self):
        return "query_engine"
    
    async def run(self, ai_message, resource, rely_action_out):
        sql = self._extract_sql(ai_message)
        result = await resource.run(sql)
        return ActionOutput(content=str(result))

# 使用
agent = ConversableAgent(
    actions=[SqlQueryAction()],
    resource=TaoshaResourceManager(),
)
```

#### 3. 保留现有 @tool 方式（简单场景）

```python
# 简单场景不需要改动
@tool
def simple_tool(param: str) -> str:
    """简单工具"""
    return do_something(param)
```

---

## 🎯 核心要点

1. **Action** = 业务逻辑（做什么）
2. **Resource** = 基础设施（用什么）
3. **Tool** = 函数封装（怎么用）
4. **意图识别** = LLM Thinking 阶段（不是独立步骤）

DB-GPT 的核心优势是 **Action 和 Resource 分离**，这样：
- ✅ 资源可以复用
- ✅ 依赖关系清晰
- ✅ 启动时检查
- ✅ 易于测试

但对淘沙来说，**当前的 @tool 方式已经足够好**，只需要：
- ⭐ 增加资源管理器（预加载 + 依赖检查）
- ⭐ 保留 @tool 方式（简单场景）
- ⭐ 可选：复杂场景使用 Action + Resource 分离
