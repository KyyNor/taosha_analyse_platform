# DeepAgents Middleware 实施计划

## 一、LangChain 内置 Middleware 清单

| Middleware | 功能描述 | 适用场景 |
|------------|---------|---------|
| **SummarizationMiddleware** | 对话历史自动摘要，防止上下文溢出 | 长对话、多轮分析 |
| **PIIMiddleware** | PII 检测和脱敏（邮箱、手机、信用卡等） | 涉及敏感数据的分析 |
| **HumanInTheLoopMiddleware** | 敏感操作人工审核 | 需要审批的高风险操作 |
| **TodoListMiddleware** | 任务规划和进度追踪 | 复杂多步骤任务 |
| **FilesystemMiddleware** | 文件系统读写工具 | 需要持久化存储的任务 |
| **SubAgentMiddleware** | 子智能体调度和协作 | 多智能体协作场景 |
| **FilesystemClaudeMemoryMiddleware** | 基于文件系统的记忆持久化 | 跨会话记忆保持 |
| **StateClaudeTextEditorMiddleware** | 状态内文件编辑 | 代码生成和修改 |
| **FilesystemClaudeTextEditorMiddleware** | 磁盘文件编辑 | 实际文件操作 |

---

## 二、各 Agent Middleware 配置方案

### 2.1 AgentService (普通对话智能体)

**文件**: `backend/services/agents/agent_service.py`

**当前配置**:
```python
middleware=[
    SummarizationMiddleware(model, max_tokens_before_summary=50000, messages_to_keep=20),
    PIIMiddleware("credit_card", strategy="mask", apply_to_output=True),
    TodoListMiddleware(),
]
```

**建议增加**:

| Middleware | 理由 | 优先级 |
|------------|------|--------|
| ✅ 保留 SummarizationMiddleware | 长对话需要自动摘要 | - |
| ✅ 保留 PIIMiddleware | 保护敏感信息 | - |
| ✅ 保留 TodoListMiddleware | 任务追踪对用户可见 | - |
| ➕ 增加 **RetryMiddleware** (自定义) | 工具调用失败自动重试 | 中 |
| ➕ 增加 **LoggingMiddleware** (自定义) | 详细日志记录便于调试 | 低 |

---

### 2.2 DataAnalyserAgent (数据分析智能体)

**文件**: `backend/services/agents/deepagents/data_analyser_agent.py`

**当前配置** (DeepAgent 自动包含):
```python
# DeepAgent 自动包含: TodoListMiddleware, FilesystemMiddleware, SubAgentMiddleware
middleware=[]  # 空，使用默认
```

**建议增加**:

| Middleware | 理由 | 优先级 |
|------------|------|--------|
| ✅ 保留 TodoListMiddleware | DeepAgent 核心，任务规划必需 | - |
| ✅ 保留 FilesystemMiddleware | 文件读写核心功能 | - |
| ➖ 移除 SubAgentMiddleware | 当前不需要子智能体 | - |
| ➕ 增加 **SummarizationMiddleware** | 长分析过程防止上下文溢出 | 高 |
| ➕ 增加 **ProgressMiddleware** (自定义) | 实时汇报分析进度 | 中 |
| ➕ 增加 **CodeValidationMiddleware** (自定义) | 代码执行前语法检查 | 中 |

**建议配置**:
```python
self.agent = create_deep_agent(
    model=self.llm_service.client,
    tools=tools,
    system_prompt=DATA_ANALYSIS_SYSTEM_PROMPT,
    backend=FilesystemBackend(root_dir=str(self.output_dir), virtual_mode=True),
    middleware=[
        SummarizationMiddleware(
            model=self.llm_service.client,
            trigger={"tokens": 30000},
            keep={"messages": 15},
        ),
        # ProgressMiddleware(callback=self._on_progress),  # 自定义
    ],
)
```

---

### 2.3 QuestionProposerAgent (问题提出智能体)

**文件**: `backend/services/agents/deepagents/question_proposer_agent.py`

**当前配置**:
```python
middleware=[]  # 无
```

**建议配置**:

| Middleware | 理由 | 优先级 |
|------------|------|--------|
| ➕ 增加 **SummarizationMiddleware** | 历史记录可能很长 | 中 |
| ➕ 增加 **OutputValidationMiddleware** (自定义) | 确保输出符合 JSON 格式 | 高 |

```python
self.agent = create_agent(
    model=self.llm_service.client,
    tools=tools,
    system_prompt=QUESTION_PROPOSER_PROMPT,
    middleware=[
        SummarizationMiddleware(
            model=self.llm_service.client,
            trigger={"tokens": 20000},
            keep={"messages": 10},
        ),
    ],
)
```

---

### 2.4 ScorerAgent (评分智能体)

**文件**: `backend/services/agents/deepagents/scorer_agent.py`

**当前配置**:
```python
middleware=[]  # 无
```

**建议配置**:

| Middleware | 理由 | 优先级 |
|------------|------|--------|
| ➕ 增加 **SummarizationMiddleware** | 分析报告可能很长 | 高 |
| ➕ 增加 **OutputValidationMiddleware** (自定义) | 确保评分格式正确 | 高 |
| ➕ 增加 **ConsistencyMiddleware** (自定义) | 确保评分标准一致 | 中 |

```python
self.agent = create_agent(
    model=self.llm_service.client,
    tools=tools,
    system_prompt=SCORER_PROMPT,
    middleware=[
        SummarizationMiddleware(
            model=self.llm_service.client,
            trigger={"tokens": 25000},
            keep={"messages": 10},
        ),
    ],
)
```

---

## 三、自定义 Middleware 开发计划

### 3.1 RetryMiddleware (重试中间件)

**功能**: 工具调用失败时自动重试

**文件**: `backend/services/agents/deepagents/middleware/retry.py`

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable
from utils.logger import logger

@wrap_model_call
def retry_middleware(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """工具调用失败自动重试"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return handler(request)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"重试 {attempt + 1}/{max_retries}: {e}")
```

**适用**: AgentService, DataAnalyserAgent

---

### 3.2 ProgressMiddleware (进度中间件)

**功能**: 实时汇报分析进度到外部系统

**文件**: `backend/services/agents/deepagents/middleware/progress.py`

```python
from langchain.agents.middleware import AgentMiddleware, AgentState
from langgraph.runtime import Runtime
from typing import Any, Callable

class ProgressMiddleware(AgentMiddleware):
    """分析进度汇报中间件"""

    def __init__(self, callback: Callable[[str, int], None] = None):
        super().__init__()
        self.callback = callback
        self.step_count = 0

    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        self.step_count += 1
        if self.callback:
            last_msg = state["messages"][-1]
            self.callback(f"Step {self.step_count}", self.step_count)
        return None
```

**适用**: DataAnalyserAgent

---

### 3.3 OutputValidationMiddleware (输出验证中间件)

**功能**: 验证 Agent 输出符合预期的 JSON 格式

**文件**: `backend/services/agents/deepagents/middleware/validation.py`

```python
import json
from langchain.agents.middleware import AgentMiddleware, hook_config, AgentState
from langchain.messages import AIMessage
from langgraph.runtime import Runtime
from typing import Any

class OutputValidationMiddleware(AgentMiddleware):
    """输出格式验证中间件"""

    def __init__(self, required_fields: list[str] = None):
        super().__init__()
        self.required_fields = required_fields or []

    @hook_config(can_jump_to=["end"])
    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        last_msg = state["messages"][-1]

        # 尝试解析 JSON
        try:
            content = last_msg.content
            # 提取 JSON 块
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
                data = json.loads(json_str)
            else:
                data = json.loads(content)

            # 验证必需字段
            missing = [f for f in self.required_fields if f not in data]
            if missing:
                return {
                    "messages": [AIMessage(f"输出缺少必需字段: {missing}，请重新生成")],
                }
        except json.JSONDecodeError:
            # JSON 解析失败，让 Agent 重试
            pass

        return None
```

**适用**: QuestionProposerAgent, ScorerAgent

---

### 3.4 LoggingMiddleware (日志中间件)

**功能**: 详细记录模型调用和工具使用

**文件**: `backend/services/agents/deepagents/middleware/logging.py`

```python
from langchain.agents.middleware import AgentMiddleware, AgentState
from langgraph.runtime import Runtime
from typing import Any
from utils.logger import logger

class LoggingMiddleware(AgentMiddleware):
    """详细日志记录中间件"""

    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        msg_count = len(state.get("messages", []))
        logger.debug(f"[Agent] 调用模型，当前消息数: {msg_count}")
        return None

    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        last_msg = state["messages"][-1]
        content_preview = str(last_msg.content)[:200]
        logger.debug(f"[Agent] 模型返回: {content_preview}...")
        return None
```

**适用**: 所有 Agent (开发调试阶段)

---

## 四、实施步骤

### 阶段 1: 内置 Middleware 配置 (高优先级)

| 任务 | 文件 | 说明 |
|-----|------|-----|
| 为 DataAnalyserAgent 添加 SummarizationMiddleware | data_analyser_agent.py | 防止长分析溢出 |
| 为 QuestionProposerAgent 添加 SummarizationMiddleware | question_proposer_agent.py | 历史记录可能很长 |
| 为 ScorerAgent 添加 SummarizationMiddleware | scorer_agent.py | 分析报告可能很长 |

### 阶段 2: 自定义 Middleware 开发 (中优先级)

| 任务 | 文件 | 说明 |
|-----|------|-----|
| 创建 middleware 目录 | deepagents/middleware/__init__.py | 存放自定义中间件 |
| 实现 RetryMiddleware | deepagents/middleware/retry.py | 工具调用重试 |
| 实现 OutputValidationMiddleware | deepagents/middleware/validation.py | 输出格式验证 |
| 实现 ProgressMiddleware | deepagents/middleware/progress.py | 进度汇报 |

### 阶段 3: 集成测试 (低优先级)

| 任务 | 说明 |
|-----|-----|
| 测试 SummarizationMiddleware 触发条件 | 确保长对话正确摘要 |
| 测试 RetryMiddleware 重试逻辑 | 模拟工具失败场景 |
| 测试 OutputValidationMiddleware | 验证 JSON 格式检查 |

---

## 五、Middleware 配置总结表

| Agent | 内置 Middleware | 自定义 Middleware |
|-------|----------------|------------------|
| **AgentService** | SummarizationMiddleware, PIIMiddleware, TodoListMiddleware | RetryMiddleware, LoggingMiddleware |
| **DataAnalyserAgent** | TodoListMiddleware*, FilesystemMiddleware*, SummarizationMiddleware | ProgressMiddleware |
| **QuestionProposerAgent** | SummarizationMiddleware | OutputValidationMiddleware |
| **ScorerAgent** | SummarizationMiddleware | OutputValidationMiddleware |

*: DeepAgent 自动包含

---

## 六、新增文件清单

```
backend/services/agents/deepagents/
└── middleware/
    ├── __init__.py
    ├── retry.py              # RetryMiddleware
    ├── validation.py         # OutputValidationMiddleware
    ├── progress.py           # ProgressMiddleware
    └── logging.py            # LoggingMiddleware
```

---

## 七、Middleware 使用示例

### 7.1 SummarizationMiddleware 配置示例

```python
from langchain.agents.middleware import SummarizationMiddleware

# 方式1: 基于 token 数触发
SummarizationMiddleware(
    model="gpt-4o-mini",  # 使用便宜的模型做摘要
    trigger={"tokens": 30000},
    keep={"messages": 15},
)

# 方式2: 基于消息数和 token 数联合触发
SummarizationMiddleware(
    model="gpt-4o-mini",
    trigger=[
        {"tokens": 5000, "messages": 3},
        {"tokens": 3000, "messages": 6},
    ],
    keep={"messages": 20},
)

# 方式3: 基于比例触发
SummarizationMiddleware(
    model="gpt-4o-mini",
    trigger={"fraction": 0.8},  # 达到上下文窗口 80% 时触发
    keep={"fraction": 0.3},     # 保留 30% 的消息
)
```

### 7.2 PIIMiddleware 配置示例

```python
from langchain.agents.middleware import PIIMiddleware

# 脱敏邮箱
PIIMiddleware("email", strategy="redact", apply_to_input=True)

# 遮盖信用卡
PIIMiddleware("credit_card", strategy="mask", apply_to_output=True)

# 阻止 API Key（使用自定义正则）
PIIMiddleware(
    "api_key",
    detector=r"sk-[a-zA-Z0-9]{32}",
    strategy="block",
    apply_to_input=True,
)
```

### 7.3 HumanInTheLoopMiddleware 配置示例

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

HumanInTheLoopMiddleware(
    interrupt_on={
        "send_email": {
            "allowed_decisions": ["approve", "edit", "reject"]
        },
        "delete_file": {
            "allowed_decisions": ["approve", "reject"]
        }
    }
)
```

---

**文档创建日期**：2025-12-21
**最后更新**：2025-12-21
