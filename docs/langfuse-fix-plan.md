# LangFuse userId和sessionId配置修复方案

## 问题现状

当前LangFuse集成中存在以下问题：
- ❌ Sessions记录缺失：会话信息没有在LangFuse中正确记录
- ❌ Users信息缺失：用户标识没有正确传递和显示
- ❌ Tracing数据不完整：输入数据缺失，多次对话只显示第一次
- ❌ 配置的userId和sessionId没有生效

## 核心问题分析

基于代码分析，发现配置没有生效的根本原因：

### 1. CallbackHandler初始化不完整
**位置**: `backend/services/tracking_service/observability_service.py:31`

**问题**:
```python
# 当前代码
_tracing_handler = CallbackHandler()  # 没有传递用户和会话信息
```

**影响**: 即使后续在metadata中设置了这些信息，Langfuse也无法自动识别

### 2. 元数据传递机制不正确
**位置**: `backend/services/agents/agent_service.py:109-112`

**问题**:
```python
# 当前代码
config = RunnableConfig(
    recursion_limit=10,
    callbacks=callbacks,
    metadata={
        "session_id": session_id,
        "user_id": "api_user"  # 硬编码，且CallbackHandler无法获取
    }
)
```

**影响**: metadata设置在RunnableConfig中，但CallbackHandler本身未配置这些元数据

### 3. @observe装饰器配置问题
**位置**: `backend/services/agents/agent_service.py:70`

**问题**:
```python
# 当前代码
@observe(name="agent_chat_stream", capture_input=False)
```

**影响**:
- `capture_input=False` 导致输入数据不完整
- 缺少对session和user信息的显式捕获

### 4. Session ID生成机制不稳定
**位置**: `backend/services/agents/agent_service.py:137-151`

**问题**:
- 每次对话可能生成新的session_id
- 缺乏持久化的会话管理
- 无法保证同一会话的连续性

## 修复方案

### 第一阶段：修复CallbackHandler初始化

**目标**: 让CallbackHandler能够动态获取用户和会话信息

**修改文件**: `backend/services/tracking_service/observability_service.py`

```python
# 修改前
_tracing_handler = CallbackHandler()

# 修改后
def get_tracing_handler():
    """获取带用户会话信息的追踪处理器"""
    return CallbackHandler(
        session_id=lambda: getattr(globals(), 'current_session_id', None),
        user_id=lambda: getattr(globals(), 'current_user_id', None)
    )

# 在initialize_observability函数中
if langfuse.auth_check():
    logger.info("Langfuse client is authenticated and ready!")
    _tracing_handler = get_tracing_handler()
```

### 第二阶段：增强Agent服务的元数据传递

**目标**: 确保用户和会话信息正确传递到Langfuse

**修改文件**: `backend/services/agents/agent_service.py`

```python
# 修改@observe装饰器配置
@observe(
    name="agent_chat_stream",
    capture_input=True,  # 改为True
    capture_output=True  # 新增
)
async def chat_stream(
    self,
    message: str,
    conversation_history: list = None,
    user_id: str = None  # 新增用户ID参数
):
    # 生成或获取session_id
    session_id = self._extract_or_create_session_id(conversation_history)
    user_id = user_id or "api_user"

    # 设置全局变量供CallbackHandler使用
    globals()['current_session_id'] = session_id
    globals()['current_user_id'] = user_id

    # 构建消息列表
    messages = self._build_messages(message, conversation_history)

    # 准备callbacks
    callbacks = [self.tracing_handler] if self.tracing_handler else []

    # 修改RunnableConfig
    async for chunk in self.agent.astream(
        {"messages": messages},
        config=RunnableConfig(
            recursion_limit=10,
            callbacks=callbacks,
            metadata={
                "session_id": session_id,
                "user_id": user_id,
                "langfuse_session_id": session_id,  # 明确指定langfuse session id
                "langfuse_user_id": user_id         # 明确指定langfuse user id
            }
        )
    ):
        yield chunk
```

### 第三阶段：增强API层的用户信息传递

**目标**: 支持从前端传递用户ID到后端

**修改文件**: `backend/api/agents_routes.py`

```python
# 修改请求模型
class ChatRequest(BaseModel):
    message: str
    conversation_history: list = []
    user_id: str = None  # 新增用户ID字段

# 修改聊天端点
@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Agent聊天流式响应"""
    try:
        # 传递用户ID到Agent服务
        async for chunk in agent_service.chat_stream(
            message=request.message,
            conversation_history=request.conversation_history,
            user_id=request.user_id  # 新增参数
        ):
            yield chunk
    except Exception as e:
        logger.error(f"Agent chat stream error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
```

### 第四阶段：优化Session ID生成机制

**目标**: 创建更稳定的Session ID生成策略

**修改文件**: `backend/services/agents/agent_service.py`

```python
def _extract_or_create_session_id(self, conversation_history: list = None, request_session_id: str = None) -> str:
    """提取或创建会话ID

    Args:
        conversation_history: 对话历史
        request_session_id: 请求中传递的session_id

    Returns:
        str: 会话ID
    """
    # 优先使用请求中传递的session_id
    if request_session_id:
        return request_session_id

    # 从对话历史中提取稳定的session_id
    if conversation_history and len(conversation_history) >= 2:
        # 寻找第一个用户消息作为会话起点
        for msg in conversation_history:
            if msg.get("role") == "user" and msg.get("content"):
                # 使用用户消息的hash作为稳定的session_id
                content_hash = hashlib.md5(
                    msg.get("content", "").encode()[:100]  # 只取前100字符避免过长
                ).hexdigest()[:12]
                return f"session_{content_hash}"

    # 生成新的session_id，带时间戳增加唯一性
    timestamp = int(time.time())
    random_suffix = str(uuid.uuid4())[:8]
    new_session_id = f"session_{timestamp}_{random_suffix}"
    return new_session_id
```

### 第五阶段：前端集成（可选）

**目标**: 前端支持用户ID和Session ID的传递

**修改文件**: `frontend/src/services/api/agentService.ts`

```typescript
export interface ChatRequest {
  message: string;
  conversation_history: ChatMessage[];
  user_id?: string;  // 新增用户ID
  session_id?: string;  // 新增会话ID（可选）
}

// 修改chatStream方法
export async function* chatStream(request: ChatRequest): AsyncGenerator<any, void, unknown> {
  // 从localStorage获取用户ID
  const userId = request.user_id || localStorage.getItem('agent_user_id') || 'anonymous_user';

  const response = await fetch(`${buildApiUrl()}/agents/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...request,
      user_id: userId,  // 传递用户ID
      // session_id 让后端自动生成更稳定
    }),
  });

  // ... 流式处理逻辑
}
```

## 实施步骤

### 1. 准备工作
- [ ] 备份当前代码
- [ ] 确认Langfuse配置正确
- [ ] 测试当前功能状态

### 2. 后端修改（按顺序执行）
- [ ] 修改 `observability_service.py` 中的CallbackHandler初始化
- [ ] 修改 `agent_service.py` 中的@observe装饰器和chat_stream方法
- [ ] 优化 `agent_service.py` 中的Session ID生成逻辑
- [ ] 修改 `agents_routes.py` 中的API接口

### 3. 前端修改（可选）
- [ ] 修改 `agentService.ts` 支持用户ID传递
- [ ] 修改 `AgentPage.vue` 添加用户ID管理

### 4. 测试验证
- [ ] 单用户对话测试
- [ ] 多用户隔离测试
- [ ] 会话连续性测试
- [ ] Langfuse数据完整性验证

## 预期效果

修复后将实现：

### ✅ LangFuse数据完整性
- **Sessions正确记录**: 每个会话都有独立的session记录
- **Users信息完整**: 不同用户的数据正确分离和显示
- **完整Tracing数据**: input/output完整捕获，多次对话正确追踪

### ✅ 功能增强
- **多用户支持**: 支持不同用户的独立对话和数据隔离
- **会话管理**: 更稳定的会话ID生成和管理机制
- **向后兼容**: 不影响现有API的使用

### ✅ 企业级特性
- **用户级别的数据隔离**: 支持企业多用户环境
- **完整的可观测性**: 详细的使用情况和性能监控
- **会话级别的分析**: 支持会话级别的用户行为分析

## 注意事项

1. **配置检查**: 确保Langfuse环境变量正确设置
2. **渐进部署**: 建议分阶段实施，先验证后端修改
3. **数据备份**: 修改前备份现有的Langfuse数据
4. **监控观察**: 部署后密切观察Langfuse数据记录情况

## 故障排除

### 常见问题

1. **Session仍然缺失**
   - 检查CallbackHandler是否正确初始化
   - 确认全局变量设置是否生效
   - 验证Langfuse连接状态

2. **用户信息仍然缺失**
   - 检查API是否正确传递user_id
   - 确认metadata设置是否完整
   - 验证前端是否正确发送用户标识

3. **数据仍然不完整**
   - 检查@observe装饰器配置
   - 确认capture_input/capture_output设置
   - 验证异常处理是否影响数据记录

## 联系支持

如果在实施过程中遇到问题，可以：
1. 查看Langfuse官方文档
2. 检查项目日志文件
3. 分析Langfuse Dashboard的连接状态
4. 参考本文档的故障排除部分

---

**最后更新**: 2025-11-12
**版本**: 1.0
**适用版本**: LangFuse SDK最新版本, LangChain 1.0+