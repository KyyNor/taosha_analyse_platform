# DB-GPT 智能体实现深度洞察

> 探索日期: 2026-03-16
> 探索目标: 深入理解 DB-GPT 的智能体架构、Prompt 设计、工具系统和记忆机制

## 📊 项目概览

DB-GPT 是一个 AI 原生数据应用开发框架，拥有 **1122+ Python 文件**，核心包含六大能力：

1. **Text2SQL** - 自然语言转 SQL
2. **RAG (检索增强生成)** - 知识库问答
3. **Multi-Agent** - 多智能体协作
4. **DataSources** - 统一数据源管理
5. **Knowledge** - 知识库管理
6. **Visualization** - 数据可视化

**核心架构**:
```
packages/dbgpt-core/src/dbgpt/agent/
├── core/
│   ├── base_agent.py      # 48KB - 核心基类
│   ├── role.py            # 角色定义
│   ├── profile/           # Profile配置（Prompt模板）
│   ├── action/            # 动作系统
│   ├── memory/            # 记忆系统
│   └── plan/              # 规划系统
├── resource/              # 资源管理
│   ├── tool/              # 工具系统
│   ├── database.py        # 数据库资源
│   └── knowledge.py       # 知识库资源
└── expand/                # 扩展Agent
```

---

## 1. 📝 Prompt 设计机制

### 1.1 基于 Profile 的 Prompt 模板

DB-GPT 使用 **Jinja2 模板** 构建 Prompt，支持中英文双语：

**核心系统 Prompt 模板** (`profile/base.py`):

```jinja2
你是一个 {{ role }}, {% if name %}名字叫 {{ name }}.{% endif %}
你的目标是 {% if is_retry_chat %}{{ retry_goal }}{% else %}{{ goal }}{% endif %}.

请一步一步思考完根据下面给出的已知信息和用户问题完成目标，同时请严格遵守下面"重要提醒"中的约束和规范。

【重要约束】
- 严禁在任务计划中直接调用任何 resource 中的 tool，即使它们在资源列表中被列出。
- 所有 tool 的调用必须通过 ToolExpert agent 实现。
- ToolExpert 的职责是统一管理、代理所有工具的调用，Planner 只应向 ToolExpert 发出工具的使用意图。

{% if resource_prompt %}
已知资源信息：
{{ resource_prompt }}
{% endif %}
{% if expand_prompt %}
{{ expand_prompt }}
{% endif %}

*** 重要提醒 ***
请用简体中文进行回答.
当前时间是:{{now_time}}

{% if is_retry_chat %}
{% if retry_constraints %}
{% for retry_constraint in retry_constraints %}
{{ loop.index }}. {{ retry_constraint }}
{% endfor %}
{% endif %}
{% else %}
{% if constraints %}
{% for constraint in constraints %}
{{ loop.index }}. {{ constraint }}
{% endfor %}
{% endif %}
{% endif %}

{% if examples %}
你也可以参考如下对话示例:
{{ examples }}
{% endif %}

{% if out_schema %} {{ out_schema }} {% endif %}
```

**设计亮点**:
- ✅ **条件渲染**: 支持 `is_retry_chat`、`resource_prompt` 等动态内容
- ✅ **循环渲染**: 支持约束列表、示例列表的迭代
- ✅ **多语言**: 内置中英文模板
- ✅ **结构化输出**: 支持 `out_schema` 定义 JSON Schema
- ✅ **时间感知**: 包含当前时间，提升时间相关问题的准确性

### 1.2 Text2SQL Prompt 示例

**数据库对话 Prompt** (`scene/chat_db/auto_execute/prompt.py`):

```python
_DEFAULT_TEMPLATE_ZH = """
请根据用户选择的数据库和该库的部分可用表结构定义来回答用户问题.
数据库名:
    {db_name}
表结构定义:
    {table_info}

约束:
    1. 请根据用户问题理解用户意图，使用给出表结构定义创建一个语法正确的{dialect} sql
    2. 除非用户在问题中指定了他希望获得的具体数据行数，否则始终将查询限制为最多 {top_k} 个结果。
    3. 只能使用表结构信息中提供的表来生成 sql，如果无法根据提供的表结构中生成 sql，请说："提供的表结构信息不足以生成 sql 查询。" 禁止随意捏造信息。
    4. 请注意生成SQL时不要弄错表和列的关系
    5. 请检查SQL的正确性，并保证正确的情况下优化查询性能
    6. 请从如下给出的展示方式种选择最优的一种用以进行数据渲染，将类型名称放入返回要求格式的name参数值中，如果找不到最合适的则使用'Table'作为展示方式，可用数据展示方式如下: {display_type}

用户问题:
    {user_input}

请一步步思考并按照以下JSON格式回复：
{response}
确保返回正确的json并且可以被Python json.loads方法解析.
"""

RESPONSE_FORMAT_SIMPLE = {
    "thoughts": "thoughts summary to say to user",
    "direct_response": "If the context is sufficient to answer user, reply directly without sql",
    "sql": "SQL Query to run",
    "display_type": "Data display method",
}
```

**关键策略**:
- 🎯 **Schema 检索**: 使用 DBSummaryClient 进行表结构检索
- 🎯 **结果限制**: 默认限制返回 `{top_k}` 条结果
- 🎯 **方言感知**: 支持多种 SQL 方言 (MySQL/PostgreSQL/DuckDB)
- 🎯 **可视化选择**: 自动选择最优的展示方式 (Table/Chart/等)
- 🎯 **JSON 格式**: 强制要求结构化输出，便于解析

### 1.3 动态配置系统 (DynConfig)

```python
from dbgpt.util.configure import DynConfig

profile: ProfileConfig = ProfileConfig(
    name=DynConfig(
        "Planner",
        category="agent",
        key="dbgpt_agent_plan_planner_agent_profile_name",
    ),
    role=DynConfig(
        "Planner",
        category="agent",
        key="dbgpt_agent_plan_planner_agent_profile_role",
    ),
    goal=DynConfig(
        "理解每个智能体及其能力，使用提供的资源，通过协调智能体来解决用户问题。",
        category="agent",
        key="dbgpt_agent_plan_planner_agent_profile_goal",
    ),
    constraints=DynConfig([
        "每一步都应该向解决用户目标前进。",
        "注意依赖关系和逻辑。",
        "每一步必须是独立可完成的目标。",
        # ... 更多约束
    ]),
)
```

**优势**:
- ✅ **运行时配置**: 通过配置文件动态修改 Prompt
- ✅ **分类管理**: 按 category 和 key 组织配置
- ✅ **版本控制**: 配置变更可追踪

---

## 2. 🛠️ 基础工具/能力系统

### 2.1 工具定义方式

#### 方式 1: 使用 `@tool` 装饰器（推荐）

```python
from dbgpt.agent.resource.tool import tool

@tool(description="添加两个数字")
def add(a: int, b: int) -> int:
    """添加两个数字。"""
    return a + b

# 工具自动绑定到函数
assert add._tool.name == "add"
assert add._tool.description == "添加两个数字"
assert add(1, 2) == 3  # 正常调用
```

**优势**:
- ✅ **极简语法**: 一个装饰器完成工具注册
- ✅ **类型推断**: 自动从函数签名推断参数类型
- ✅ **文档即描述**: 使用函数 docstring 作为工具描述
- ✅ **兼容性好**: 不影响原有函数调用

#### 方式 2: 使用 BaseTool 子类

```python
from dbgpt.agent.resource.tool import BaseTool, ToolParameter

class TestBaseTool(BaseTool):
    @property
    def name(self):
        return "test_tool"

    @property
    def description(self):
        return "This is a test tool."

    @property
    def args(self):
        return {
            "param1": ToolParameter(
                name="param1",
                type="string",
                description="第一个参数",
                required=True
            )
        }

    def execute(self, *args, **kwargs):
        return "executed"

    async def async_execute(self, *args, **kwargs):
        return "async executed"
```

**优势**:
- ✅ **完全控制**: 精确控制每个工具属性
- ✅ **复杂逻辑**: 适合实现复杂工具
- ✅ **异步支持**: 同时支持同步和异步执行

#### 方式 3: 使用 FunctionTool 包装

```python
from dbgpt.agent.resource.tool import FunctionTool

def two_sum(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

ft = FunctionTool(
    name="sample",
    func=two_sum,
    args={
        "a": ToolParameter(type="integer", name="a", description="The first number."),
        "b": ToolParameter(type="integer", name="b", description="The second number."),
    }
)
ft.execute(1, 2)  # 返回 3
```

### 2.2 复杂类型工具示例

```python
from typing import List, Dict, Optional
from typing_extensions import Annotated, Doc

@tool
def complex_func(
    a: int,
    b: Annotated[int, Doc("第二个数字")],
    c: Annotated[str, Doc("第三个字符串")],
    d: List[int],
    e: Annotated[Dict[str, int], Doc("整数字典")],
    f: Optional[float] = None,
    g: str | None = None,
) -> int:
    """复杂函数示例。"""
    return a + b + len(c) + sum(d) + sum(e.values()) + (f or 0) + (len(g) if g else 0)

# 自动解析类型和描述
ft = complex_func._tool
assert ft.args.keys() == {"a", "b", "c", "d", "e", "f", "g"}
assert ft.args["a"].type == "integer"
assert ft.args["e"].type == "object"
```

**支持类型映射**:
| Python 类型 | 工具参数类型 |
|------------|-------------|
| `int` | `integer` |
| `str` | `string` |
| `float` | `number` |
| `bool` | `boolean` |
| `List[T]` | `array` |
| `Dict[str, T]` | `object` |
| `Optional[T]` | `T` (required=False) |
| `Annotated[T, Doc("...")]` | `T` (自定义描述) |

### 2.3 工具资源打包

```python
from dbgpt.agent.resource.tool import ToolPack

# 将多个工具打包成一个资源
tool_pack = ToolPack([
    search_tool,
    db_query_tool,
    visualization_tool
], name="数据分析工具包")

# Agent 绑定资源
agent.bind(tool_pack)
```

### 2.4 工具 Prompt 生成

```python
async def get_prompt(self, *, lang: str = "en", prompt_type: str = "default"):
    """自动生成工具 Prompt"""
    prompt_template = (
        "{name}: 调用此工具与 {name} API进行交互。{name} API 有什么用？"
        "{description} 参数：{parameters}"
    )

    parameters = []
    for key, value in self.args.items():
        parameters.append({
            "name": key,
            "type": value.type,
            "description": value.description,
            "required": value.required,
        })

    return template.format(
        name=self.name,
        description=self.description,
        parameters=json.dumps(parameters, ensure_ascii=False)
    )
```

**生成示例**:
```
sql_query: 调用此工具与 sql_query API进行交互。sql_query API 有什么用？
执行 SQL 查询并返回结果。参数：[
  {"name": "sql", "type": "string", "description": "SQL 查询语句", "required": true},
  {"name": "db_name", "type": "string", "description": "数据库名称", "required": true}
]
```

---

## 3. 🧠 记忆系统设计

### 3.1 三层记忆架构

```
短期记忆 (ShortTermMemory)
    ↓ (滑动窗口满 + 重要性阈值)
长期记忆 (LongTermMemory)
    ↓ (持久化存储)
GPTs 风格记忆 (GptsMemory)
```

**设计理念**:
- 🎯 **分层存储**: 根据记忆的新鲜度和重要性分层
- 🎯 **自动流转**: 短期记忆自动转移到长期记忆
- 🎯 **智能检索**: 结合向量相似度、时间衰减、重要性评分

### 3.2 记忆片段 (MemoryFragment)

```python
class AgentMemoryFragment(MemoryFragment):
    def __init__(
        self,
        observation: str,           # 观察内容
        embeddings: List[float],    # 向量嵌入
        memory_id: int,             # 记忆ID（雪花ID）
        importance: float,          # 重要性分数 (1-10)
        last_accessed_time: datetime,  # 最后访问时间
        is_insight: bool,           # 是否为洞察
    ):
        pass
```

**记忆元数据**:
```python
metadata = {
    "buffer_idx": int,              # 短期记忆索引
    "last_accessed_at": datetime,   # 最后访问时间
    "session_id": str,              # 会话ID
    "importance": float,            # 重要性分数
}
```

### 3.3 短期记忆 (ShortTermMemory)

**特点**:
- 基于 **滑动窗口**（默认 10 条）
- 支持 **向量增强**（相似度 > 0.7 的记忆会被增强）
- 自动转移到长期记忆

```python
class EnhancedShortTermMemory(ShortTermMemory[T]):
    def __init__(
        self,
        embeddings: Embeddings,
        executor: Executor,
        buffer_size: int = 10,
        enhance_similarity_threshold: float = 0.7,
        enhance_threshold: int = 3,
    ):
        """
        Args:
            buffer_size: 滑动窗口大小
            enhance_similarity_threshold: 相似度阈值
            enhance_threshold: 增强计数阈值
        """
        pass

    async def write(self, memory_fragment: T):
        """写入记忆"""
        # 1. 计算当前记忆的向量嵌入
        embeddings = await self._embeddings.embed_documents([memory_fragment.observation])
        memory_fragment.update_embeddings(embeddings[0])

        # 2. 遍历短期记忆，计算相似度
        for idx, old_embedding in enumerate(self.short_embeddings):
            similarity = cosine_similarity(old_embedding, embeddings[0])

            # 3. Sigmoid 概率变换
            sigmoid_prob = sigmoid_function(similarity)

            # 4. 如果相似度高，增强旧记忆
            if sigmoid_prob >= self.enhance_similarity_threshold:
                if random.random() < sigmoid_prob:
                    self.enhance_cnt[idx] += 1
                    self.enhance_memories[idx].append(memory_fragment)

        # 5. 转移到长期记忆
        await self.transfer_to_long_term(memory_fragment)
```

**记忆增强机制**:
```
新记忆: "用户查询了最近7天的交易数据"
  ↓
与旧记忆相似度: 0.85 (超过阈值 0.7)
  ↓
旧记忆增强: "用户喜欢查询交易趋势数据" (enhance_cnt++)
  ↓
增强次数: 4 次 (超过阈值 3)
  ↓
触发洞察提取: "用户偏好分析交易趋势"
```

### 3.4 长期记忆 (LongTermMemory)

**特点**:
- 基于 **向量存储**（Qdrant）
- 支持 **时间加权检索** (`TimeWeightedEmbeddingRetriever`)
- 自动 **遗忘和合并** 机制

```python
class LongTermRetriever(TimeWeightedEmbeddingRetriever):
    def _retrieve(self, query: str, filters: MetadataFilters) -> List[Chunk]:
        """
        综合分数 = 向量相似度 × 时间衰减 × 重要性
        """
        # 1. 向量相似度检索
        vector_results = await self._vector_store.search(query)

        # 2. 计算时间衰减
        time_diff = now - memory.last_accessed_time
        time_weight = 1.0 / (1.0 + time_diff.days * 0.1)

        # 3. 计算综合分数
        combined_score = (
            vector_score * 0.7 +
            time_weight * 0.2 +
            importance * 0.1
        )

        # 4. 跳过标记为遗忘或合并的记忆
        if doc.content.find("[FORGET]") == -1:
            results.append(doc)

        return sorted(results, key=combined_score, reverse=True)
```

**记忆标记**:
- `[FORGET]`: 标记为遗忘，不再检索
- `[MERGE]`: 标记为合并，合并到其他记忆

### 3.5 GPTs 风格记忆 (GptsMemory)

**特点**:
- 持久化存储（数据库）
- 跨会话记忆共享
- 支持记忆恢复

```python
class GptsMemory:
    async def get_agent_history_memory(self, conv_id: str, role: str):
        """获取Agent的历史记忆"""
        action_outputs = await self.db.get_action_outputs(conv_id, role)

        # 恢复记忆片段
        fragments = []
        for action_output in action_outputs:
            fragment = AgentMemoryFragment.build_from(
                observation=action_output.memory_fragments["memory"],
                importance=action_output.memory_fragments.get("importance"),
                memory_id=action_output.memory_fragments.get("id"),
            )
            fragments.append(fragment)

        return fragments
```

### 3.6 记忆重要性评分

**LLM 评分器** (`memory/llm.py`):

```python
class LLMImportanceScorer:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def score(self, memory_fragment: MemoryFragment) -> float:
        """使用LLM评估记忆重要性，分数1-10"""
        prompt = f"""
        请评估以下记忆片段的重要性（1-10分）：
        {memory_fragment.observation}

        评分标准：
        - 10分：关键信息，必须记住（如用户偏好、核心需求）
        - 5分：有用信息，可以记住（如一般性问题）
        - 1分：无关信息，可以遗忘（如闲聊）

        请只返回数字分数。
        """
        response = await self.llm_client.generate(prompt)
        return float(response.strip())
```

**评分示例**:
| 记忆内容 | 重要性分数 | 原因 |
|---------|-----------|------|
| "用户想要分析交易欺诈趋势" | 10.0 | 核心需求，必须记住 |
| "用户问了当前时间" | 2.0 | 临时信息，可以遗忘 |
| "用户偏好使用图表展示" | 7.0 | 用户偏好，有用信息 |
| "用户说了声谢谢" | 1.0 | 礼貌性对话，无关信息 |

### 3.7 记忆洞察提取

```python
class LLMInsightExtractor:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def extract(self, memory_fragments: List[MemoryFragment]) -> str:
        """从记忆片段中提取高阶洞察"""
        memories_text = "\n".join([
            f"- {frag.observation}" for frag in memory_fragments
        ])

        prompt = f"""
        从以下记忆片段中提取关键洞察和模式：
        {memories_text}

        请总结：
        1. 用户偏好
        2. 常见问题
        3. 行为模式
        4. 潜在需求

        请以结构化的方式返回洞察。
        """
        return await self.llm_client.generate(prompt)
```

**洞察示例**:
```
输入记忆：
- 用户查询了最近7天的交易数据
- 用户要求生成趋势图表
- 用户偏好使用柱状图展示
- 用户关注欺诈率指标

输出洞察：
1. 用户偏好：喜欢可视化数据，特别是趋势图表
2. 常见问题：关注交易数据和欺诈率
3. 行为模式：定期查看最近7天的数据
4. 潜在需求：可能需要自动化报表生成功能
```

### 3.8 记忆写入模板

```jinja2
{% if question %}问题: {{ question }} {% endif %}
{% if thought %}思考答案: {{ thought }} {% endif %}
{% if action %}行动结果: {{ action }} {% endif %}
{% if observation %}观察: {{ observation }} {% endif %}
```

**写入示例**:
```
问题: 查询最近7天的交易总额
思考答案: 我需要使用 SQL 查询工具来获取数据
行动结果: sql_query
观察: 查询成功，总额为 1,234,567 元
```

---

## 4. 🎯 规划系统

### 4.1 规划 Agent (PlannerAgent)

**角色定义**:

```python
PlannerAgent(
    profile=ProfileConfig(
        name="Planner",
        role="Planner",
        goal="理解每个智能体及其能力，使用提供的资源，通过协调智能体来解决用户问题。",
        constraints=[
            "每一步都应该向解决用户目标前进。",
            "注意依赖关系和逻辑。",
            "每一步必须是独立可完成的目标。",
            "只使用上面提到的智能体。",
            "根据实际需要分配资源。",
            "每一步应该只使用一种资源。",
            "合并连续的依赖步骤。",
        ],
        examples="""
user: 帮我构建一个销售报告，总结关键指标和趋势
assistants: [
    {
        "serial_number": "1",
        "agent": "DataScientist",
        "content": "按 product_category 分组检索总销售额、平均销售额和交易数量。",
    },
    {
        "serial_number": "2",
        "agent": "DataAnalyst",
        "content": "分析检索到的销售数据，识别关键趋势和模式。",
    },
    {
        "serial_number": "3",
        "agent": "ReportWriter",
        "content": "根据分析结果生成销售报告，包括图表和关键见解。",
    }
]
"""
    )
)
```

**规划策略**:
1. **任务分解**: 将复杂任务分解为可执行的子任务
2. **依赖分析**: 分析任务间的依赖关系
3. **资源分配**: 为每个任务分配合适的 Agent 和资源
4. **并行优化**: 识别可并行执行的任务

### 4.2 团队自动规划 (TeamAutoPlan)

```python
class TeamAutoPlan:
    async def plan(
        self,
        context: AgentContext,
        agents: List[ConversableAgent],
        question: str,
    ) -> List[PlanAction]:
        """自动生成任务计划"""
        # 1. 构建 Planner Prompt
        prompt = self._build_planner_prompt(agents, question)

        # 2. 调用 LLM 生成计划
        plan_json = await self.llm_client.generate(prompt)

        # 3. 解析计划
        plan_actions = self._parse_plan(plan_json)

        # 4. 验证计划
        validated_actions = self._validate_plan(plan_actions, agents)

        return validated_actions
```

**计划示例**:
```json
{
  "plan": [
    {
      "step": 1,
      "agent": "DataScientist",
      "content": "查询最近7天的交易数据，按日期分组",
      "depends_on": []
    },
    {
      "step": 2,
      "agent": "DataAnalyst",
      "content": "分析交易数据，识别异常模式和趋势",
      "depends_on": [1]
    },
    {
      "step": 3,
      "agent": "DataVisualizer",
      "content": "生成交易趋势图表和异常点标注",
      "depends_on": [2]
    }
  ]
}
```

---

## 5. 📊 资源管理系统

### 5.1 资源类型

```python
class ResourceType(str, Enum):
    Database = "database"      # 数据库资源
    Knowledge = "knowledge"    # 知识库资源
    Tool = "tool"             # 工具资源
    Http = "http"             # HTTP API 资源
    Service = "service"       # 服务资源
```

### 5.2 资源加载和依赖检查

```python
class Resource:
    async def preload_resource(self):
        """预加载资源，启动时检查依赖"""
        for sub_resource in self.sub_resources:
            await sub_resource.preload_resource()

    def get_resource_by_type(self, resource_type: ResourceType):
        """按类型获取资源"""
        for resource in self.sub_resources:
            if resource.type() == resource_type:
                return resource
        return None
```

**预加载流程**:
```python
async def build(self, is_retry_chat: bool = False):
    """构建 Agent"""
    # 1. 预加载资源
    await self.preload_resource()

    # 2. 检查 Agent 可用性
    self.check_available()

    # 3. 初始化资源加载器
    for action in self.actions:
        action.init_resource(self.resource)

    # 4. 初始化 LLM
    if not self.is_human:
        self.llm_client = AIWrapper(llm_client=self.llm_config.llm_client)

        # 5. 初始化记忆
        memory_session = f"{conv_id}_{self.role}_{self.name}"
        self.memory.initialize(
            self.name,
            self.llm_config.llm_client,
            importance_scorer=self.memory_importance_scorer,
            insight_extractor=self.memory_insight_extractor,
            session_id=memory_session,
        )

    return self
```

### 5.3 Agent 绑定资源

```python
agent = ConversableAgent(
    profile=profile_config,
    memory=AgentMemory(),
)

# 绑定 LLM
agent.bind(llm_config)

# 绑定资源
agent.bind(resource_pack)

# 绑定工具
agent.bind(DatabaseQueryTool)
agent.bind(VisualizationTool)

# 绑定上下文
agent.bind(agent_context)
```

**bind 方法支持**:
- `LLMConfig`: LLM 配置
- `AgentContext`: Agent 上下文
- `Resource`: 资源包
- `AgentMemory`: 记忆系统
- `ProfileConfig`: Profile 配置
- `Action`: 动作类
- `Type[Action]`: 动作类类型

---

## 6. 🔄 完整工作流程

```python
# 1. 创建 Agent
agent = ConversableAgent(
    profile=ProfileConfig(
        name="DataAnalyst",
        role="数据分析专家",
        goal="帮助用户分析数据并提供洞察",
        constraints=[
            "使用提供的数据库资源",
            "生成清晰的SQL查询",
            "提供可视化结果"
        ]
    ),
    memory=AgentMemory(),
)

# 2. 绑定资源
agent.bind(llm_config)
agent.bind(database_resource)
agent.bind(ToolPack([
    SqlQueryTool,
    ChartTool,
]))

# 3. 初始化 Agent
await agent.build()

# 4. 运行 Agent
async def run_agent():
    question = "查询最近7天的交易总额并生成趋势图"

    # 4.1 读取相关记忆
    memories = await agent.read_memories(question)

    # 4.2 构建 Prompt
    prompt = await agent.build_prompt(
        question=question,
        most_recent_memories=memories,
        resource_vars={"db_name": "taosha_db"}
    )

    # 4.3 调用 LLM
    response = await agent.llm_client.generate(prompt)

    # 4.4 解析 Action
    action = SqlQueryTool.parse_action(response)

    # 4.5 执行 Action
    output = await action.run(response, resource=database_resource)

    # 4.6 写入记忆
    await agent.write_memories(
        question=question,
        ai_message=response,
        action_output=output
    )

    return output

# 5. 获取结果
result = await run_agent()
```

---

## 7. 🎨 与淘沙分析平台的对比

| 特性 | DB-GPT | 淘沙分析平台 | 建议 |
|------|--------|-------------|------|
| **Prompt 系统** | Jinja2 模板 + DynConfig | LangChain PromptTemplate | ✅ 已足够完善 |
| **工具系统** | @tool 装饰器 + BaseTool | LangChain @tool | ✅ 已足够完善 |
| **记忆系统** | 三层架构（短期/长期/GPTs） | SQLAlchemy 持久化 | ⚠️ 可借鉴三层架构 |
| **规划系统** | PlannerAgent + TeamAutoPlan | DeepAgents 编排 | ⚠️ 可借鉴 Planner 思想 |
| **资源管理** | Resource + ResourcePack | 无统一管理 | ⭐ 建议引入 |
| **依赖检查** | 启动时预加载和检查 | 手动管理 | ⭐ 建议引入 |
| **重要性评分** | LLM 自动评分 | 无 | ⭐ 建议引入 |
| **洞察提取** | LLM 自动提取 | 无 | ⭐ 建议引入 |

---

## 8. 💡 核心借鉴点

### ⭐ 立即可以借鉴的

#### 1. 资源预加载机制

**当前问题**:
- 淘沙的查询引擎、元数据等资源分散在各处
- 启动时没有统一的依赖检查
- 资源未就绪时难以排查问题

**借鉴方案**:
```python
# backend/services/agents/resource_manager.py

from dbgpt.agent.resource import Resource, ResourcePack

class TaoshaResourceManager(Resource):
    """淘沙资源管理器"""

    async def preload_resource(self):
        """预加载所有资源"""
        # 1. 预加载查询引擎
        query_engine = QueryEngineService()
        await query_engine.initialize()

        # 2. 预加载元数据
        metadata = MetadataService()
        await metadata.load_all_tables()

        # 3. 预加载向量存储
        vector_store = QdrantVectorStore()
        await vector_store.check_connection()

        # 4. 检查依赖
        self._check_dependencies()

    def _check_dependencies(self):
        """检查依赖是否满足"""
        if not query_engine.is_ready():
            raise RuntimeError("查询引擎未就绪")
        if not metadata.is_ready():
            raise RuntimeError("元数据未加载")
        # ...
```

**使用方式**:
```python
# backend/main.py

resource_manager = TaoshaResourceManager()
await resource_manager.preload_resource()

agent.bind(resource_manager)
```

#### 2. 记忆重要性评分

**当前问题**:
- 所有对话历史都平等对待
- 无法区分重要信息和无关信息
- 长对话后上下文噪声大

**借鉴方案**:
```python
# backend/services/agents/memory_scorer.py

from dbgpt.agent.memory.llm import LLMImportanceScorer

class TaoshaMemoryScorer(LLMImportanceScorer):
    """淘沙记忆重要性评分器"""

    async def score(self, memory_fragment: MemoryFragment) -> float:
        """评估记忆重要性"""
        observation = memory_fragment.observation

        # 关键词检测（快速评分）
        if self._contains_key_words(observation):
            return 9.0

        # LLM 评分（精确评分）
        prompt = f"""
        请评估以下对话内容的重要性（1-10分）：
        {observation}

        评分标准：
        - 10分：用户核心需求、关键业务逻辑
        - 7分：用户偏好、常用功能
        - 4分：一般性问题、操作确认
        - 1分：闲聊、礼貌性对话

        只返回数字分数。
        """
        response = await self.llm_client.generate(prompt)
        return float(response.strip())

    def _contains_key_words(self, text: str) -> bool:
        """关键词检测"""
        keywords = ["欺诈", "风控", "规则", "模型", "指标", "查询"]
        return any(kw in text for kw in keywords)
```

#### 3. 短期记忆增强

**当前问题**:
- 相似问题反复查询
- 无法识别用户意图模式
- 上下文理解不连贯

**借鉴方案**:
```python
# backend/services/agents/enhanced_memory.py

from dbgpt.agent.memory.short_term import EnhancedShortTermMemory

class TaoshaShortTermMemory(EnhancedShortTermMemory):
    """淘沙短期记忆"""

    async def write(self, memory_fragment: T):
        """写入记忆"""
        # 1. 计算向量嵌入
        embeddings = await self._embeddings.embed_documents([
            memory_fragment.observation
        ])
        memory_fragment.update_embeddings(embeddings[0])

        # 2. 相似度检测和增强
        async with self._lock:
            for idx, old_embedding in enumerate(self.short_embeddings):
                similarity = cosine_similarity(old_embedding, embeddings[0])

                if similarity >= 0.8:  # 高相似度
                    self.enhance_cnt[idx] += 1
                    self.enhance_memories[idx].append(memory_fragment)

                    # 触发洞察提取
                    if self.enhance_cnt[idx] >= 3:
                        insight = await self._extract_insight(
                            self.enhance_memories[idx]
                        )
                        logger.info(f"提取洞察: {insight}")

        # 3. 转移到长期记忆
        await self.transfer_to_long_term(memory_fragment)

    async def _extract_insight(self, memories: List[T]) -> str:
        """提取洞察"""
        memories_text = "\n".join([m.observation for m in memories])
        prompt = f"""
        从以下对话历史中提取用户偏好和模式：
        {memories_text}

        请总结：
        1. 用户关注什么数据？
        2. 用户偏好什么展示方式？
        3. 用户有哪些常用操作？
        """
        return await self.llm_client.generate(prompt)
```

#### 4. Profile 配置系统

**当前问题**:
- Prompt 硬编码在代码中
- 修改 Prompt 需要重启服务
- 难以 A/B 测试不同 Prompt

**借鉴方案**:
```python
# backend/services/agents/profile_config.py

from dbgpt.util.configure import DynConfig
from dbgpt.agent.profile import ProfileConfig

class TaoshaAgentProfiles:
    """淘沙 Agent Profile 配置"""

    DATA_ANALYST = ProfileConfig(
        name=DynConfig(
            "数据分析师",
            category="agent",
            key="taosha_agent_data_analyst_name",
        ),
        role=DynConfig(
            "DataAnalyst",
            category="agent",
            key="taosha_agent_data_analyst_role",
        ),
        goal=DynConfig(
            "帮助用户分析数据、生成 SQL 查询、提供可视化建议",
            category="agent",
            key="taosha_agent_data_analyst_goal",
        ),
        constraints=DynConfig([
            "只使用淘沙数据库中存在的表",
            "SQL 查询必须限制返回结果数量（默认 100 条）",
            "优先使用索引列进行查询",
            "避免使用子查询，优先使用 JOIN",
        ], category="agent"),
        examples=DynConfig("""
用户: 查询最近7天的欺诈交易数量
助手: SELECT DATE(transaction_time) as date, COUNT(*) as fraud_count
     FROM fraud_transactions
     WHERE transaction_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
     GROUP BY DATE(transaction_time)
     ORDER BY date;

用户: 这个查询太慢了
助手: 建议在 transaction_time 列上创建索引以提升查询性能。
        """, category="agent"),
    )

    FRAUD_EXPERT = ProfileConfig(
        name="风控专家",
        role="FraudExpert",
        goal="帮助用户配置风控规则、分析欺诈模式、优化模型",
        constraints=[
            "遵循淘沙风控规则引擎语法",
            "规则必须包含明确的阈值和条件",
            "避免过度拟合历史数据",
        ],
    )
```

**使用方式**:
```python
# backend/config/agent_config.yaml

agent:
  data_analyst:
    name: "高级数据分析师"
    goal: "提供深入的数据洞察和优化建议"

  fraud_expert:
    name: "资深风控专家"
    constraints:
      - "规则必须经过回测验证"
      - "关注误报率和漏报率的平衡"
```

### ⭐⭐ 近期可以规划的

#### 5. PlannerAgent 模式

**应用场景**:
- 复杂数据分析任务（如生成完整报表）
- 多 Agent 协作（如数据分析 + 可视化 + 报告生成）
- 长流程任务（如风控模型开发流程）

**实现方案**:
```python
# backend/services/agents/planner_agent.py

from dbgpt.agent.plan import PlannerAgent

class TaoshaPlannerAgent(PlannerAgent):
    """淘沙规划 Agent"""

    def __init__(self):
        super().__init__(
            profile=ProfileConfig(
                name="TaskPlanner",
                role="任务规划专家",
                goal="将复杂任务分解为可执行的子任务，并协调多个 Agent 完成",
                constraints=[
                    "每个子任务必须是独立可完成的",
                    "明确子任务间的依赖关系",
                    "合理分配 Agent 和资源",
                ],
            ),
            agents=[
                DataAnalystAgent(),
                FraudExpertAgent(),
                VisualizerAgent(),
                ReportWriterAgent(),
            ]
        )

    async def plan_report_task(self, user_question: str):
        """规划报表生成任务"""
        prompt = f"""
        用户需求: {user_question}

        可用 Agent:
        - DataAnalyst: 数据查询和分析
        - FraudExpert: 风控规则和模型
        - Visualizer: 数据可视化
        - ReportWriter: 报告生成

        请生成任务计划，每个任务包含：
        1. 执行顺序
        2. 负责 Agent
        3. 具体内容
        4. 依赖关系
        5. 所需资源
        """

        plan_json = await self.llm_client.generate(prompt)
        return self._parse_plan(plan_json)
```

#### 6. 时间加权检索

**应用场景**:
- 长期对话历史检索
- 跨会话记忆检索
- 用户偏好学习

**实现方案**:
```python
# backend/services/agents/temporal_memory.py

from dbgpt.agent.memory.long_term import LongTermRetriever

class TaoshaTemporalRetriever(LongTermRetriever):
    """淘沙时间加权检索器"""

    def _retrieve(self, query: str, filters: MetadataFilters) -> List[Chunk]:
        """时间加权检索"""
        # 1. 向量相似度检索
        vector_results = self._vector_store.search(query, top_k=20)

        # 2. 计算综合分数
        scored_results = []
        for doc, vector_score in vector_results:
            # 时间衰减（30 天半衰期）
            time_diff = (now - doc.last_accessed_at).days
            time_weight = 0.5 ** (time_diff / 30)

            # 重要性加权
            importance = doc.metadata.get("importance", 5.0)
            importance_weight = importance / 10.0

            # 综合分数
            combined_score = (
                vector_score * 0.6 +
                time_weight * 0.25 +
                importance_weight * 0.15
            )

            scored_results.append((doc, combined_score))

        # 3. 排序返回
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in scored_results[:self._k]]
```

---

## 9. 📚 关键代码路径

### Prompt 模板
- `packages/dbgpt-core/src/dbgpt/agent/core/profile/base.py:27-111`
- `packages/dbgpt-app/src/dbgpt_app/scene/chat_db/auto_execute/prompt.py`

### 工具系统
- `packages/dbgpt-core/src/dbgpt/agent/resource/tool/base.py`
- `packages/dbgpt-core/src/dbgpt/agent/resource/tool/pack.py`

### 记忆系统
- `packages/dbgpt-core/src/dbgpt/agent/core/memory/short_term.py`
- `packages/dbgpt-core/src/dbgpt/agent/core/memory/long_term.py`
- `packages/dbgpt-core/src/dbgpt/agent/core/memory/llm.py`

### 规划系统
- `packages/dbgpt-core/src/dbgpt/agent/core/plan/planner_agent.py`
- `packages/dbgpt-core/src/dbgpt/agent/core/plan/team_auto_plan.py`

---

## 10. 🎯 总结

DB-GPT 的智能体系统具有以下 **核心优势**：

1. **📝 模块化 Prompt**: Jinja2 模板 + DynConfig，支持动态配置
2. **🛠️ 灵活工具系统**: @tool 装饰器 + 多种定义方式
3. **🧠 三层记忆架构**: 短期 → 长期 → GPTs，自动流转
4. **🎯 智能规划**: PlannerAgent 自动任务分解
5. **📊 统一资源管理**: 预加载 + 依赖检查

**对淘沙分析平台的建议**：

| 优先级 | 功能 | 实现难度 | 预期收益 |
|-------|------|---------|---------|
| ⭐⭐⭐ | 资源预加载机制 | 低 | 高 |
| ⭐⭐⭐ | 记忆重要性评分 | 低 | 高 |
| ⭐⭐⭐ | Profile 配置系统 | 低 | 中 |
| ⭐⭐ | 短期记忆增强 | 中 | 高 |
| ⭐⭐ | PlannerAgent | 高 | 中 |
| ⭐ | 时间加权检索 | 中 | 低 |

---

## 附录: 快速参考

### DB-GPT 项目结构

```
DB-GPT/
├── packages/
│   ├── dbgpt-core/          # 核心框架
│   │   └── src/dbgpt/
│   │       ├── agent/       # Agent 框架
│   │       ├── core/        # 核心接口
│   │       ├── rag/         # RAG 框架
│   │       └── datasource/  # 数据源抽象
│   │
│   ├── dbgpt-app/           # 应用层
│   │   └── src/dbgpt_app/
│   │       └── scene/       # 应用场景
│   │           ├── chat_db/         # 数据库对话
│   │           ├── chat_knowledge/  # 知识库对话
│   │           └── chat_dashboard/  # 仪表板对话
│   │
│   ├── dbgpt-ext/           # 扩展模块
│   │   └── src/dbgpt_ext/
│   │       ├── rag/         # RAG 扩展
│   │       │   ├── retriever/
│   │       │   │   ├── bm25.py
│   │       │   │   ├── db_schema.py
│   │       │   │   ├── doc_tree.py
│   │       │   │   └── graph_retriever/
│   │       │   └── summary/
│   │       │       └── rdbms_db_summary.py
│   │       └── datasource/  # 数据源扩展
│   │
│   └── dbgpt-serve/         # 服务层
│       └── src/dbgpt_serve/
│           ├── datasource/  # 数据源服务
│           ├── knowledge/   # 知识库服务
│           └── agent/       # Agent 服务
│
└── pilote/                  # 前端（React）
```

### 关键配置文件

- `config/config.yaml`: 主配置文件
- `config/prompt_config.yaml`: Prompt 配置
- `config/agent_config.yaml`: Agent 配置

### 核心依赖

- **LLM**: OpenAI / Qwen / LocalAI
- **向量存储**: Qdrant
- **数据库**: 支持 MySQL/PostgreSQL/DuckDB
- **前端**: Next.js 14 + React 18

---

**文档版本**: v1.0
**最后更新**: 2026-03-16
**维护者**: Claude Code
