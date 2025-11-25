# 使用 useChat 对接 FastAPI 驱动的 LangChain Agent

将 Vercel AI SDK 的 `useChat` 钩子与 FastAPI + LangChain Agent 对接，核心在于**FastAPI 端实现符合 useChat 协议的流式 API**。useChat 默认期望一个接收 POST 请求的 `/api/chat` 端点，请求体包含消息数组，响应为 Server-Sent Events (SSE) 格式的流式数据。

---

## 一、FastAPI 后端实现

### 1. 安装依赖

```bash
pip install fastapi uvicorn langchain langchain-openai pydantic
```

### 2. 创建支持流式的 LangChain Agent

关键是为 Agent 启用 `astream_events()` 或 `astream_log()` 方法，并正确格式化 SSE 输出。

```python
# main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import json
import asyncio
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

app = FastAPI(title="LangChain Agent API")

# 定义消息模型（匹配 useChat 格式）
class Message(BaseModel):
    role: str
    content: str

class ChatPayload(BaseModel):
    messages: List[Message]

# 定义工具（示例）
@tool
def get_weather(location: str) -> str:
    """获取指定城市的天气信息"""
    return f"{location} 今天晴朗，25°C"

# 创建 LangChain Agent
def create_agent():
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,
        streaming=True,  # 关键：启用流式
    )
    
    system_prompt = """你是一个 helpful 助手。你可以使用工具来回答问题。
    如果有工具调用，请严格按照工具要求执行。"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    tools = [get_weather]
    
    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )
    
    return agent_executor

agent_executor = create_agent()

# 转换消息格式为 LangChain 格式
def convert_messages(messages: List[Message]):
    """将 useChat 格式转换为 LangChain 格式"""
    from langchain.schema import HumanMessage, AIMessage, SystemMessage
    
    langchain_messages = []
    for msg in messages:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))
        elif msg.role == "system":
            langchain_messages.append(SystemMessage(content=msg.content))
    return langchain_messages

# 流式响应生成器
async def generate_stream(payload: ChatPayload):
    """生成 SSE 格式的流式响应"""
    try:
        # 准备输入
        input_text = payload.messages[-1].content
        chat_history = convert_messages(payload.messages[:-1])
        
        # 调用 Agent 的流式方法
        async for event in agent_executor.astream_events(
            {
                "input": input_text,
                "chat_history": chat_history
            },
            version="v1"
        ):
            event_type = event["event"]
            
            # 处理 LLM 生成的文本
            if event_type == "on_llm_stream":
                if event["data"].get("chunk"):
                    content = event["data"]["chunk"].content
                    if content:
                        yield f"data: {json.dumps({'type': 'text', 'content': content})}\n\n"
            
            # 处理工具调用
            elif event_type == "on_tool_start":
                tool_input = event["data"].get("input")
                tool_name = event["name"]
                yield f"data: {json.dumps({'type': 'tool-call', 'toolName': tool_name, 'args': tool_input})}\n\n"
            
            # 处理工具结果
            elif event_type == "on_tool_end":
                result = event["data"].get("output")
                tool_name = event["name"]
                yield f"data: {json.dumps({'type': 'tool-result', 'toolName': tool_name, 'result': result})}\n\n"
        
        # 结束标记
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

# 聊天端点
@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload):
    """接收 useChat 的请求并返回流式响应"""
    return StreamingResponse(
        generate_stream(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

# 健康检查
@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3. 处理工具调用

当 Agent 调用工具时，useChat 需要 `maxSteps` 参数来支持多轮交互：

```python
# 在 generate_stream 中增加工具结果处理逻辑
elif event_type == "on_tool_end":
    result = event["data"].get("output")
    tool_name = event["name"]
    # 发送工具结果给客户端
    yield f"data: {json.dumps({
        'type': 'tool-result', 
        'toolName': tool_name, 
        'result': result
    })}\n\n"
```

---

## 二、前端 Next.js + useChat 配置

### 1. 配置 useChat 指向 FastAPI

```tsx
'use client';
import { useChat } from '@ai-sdk/react';

export default function ChatPage() {
  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
  } = useChat({
    api: 'http://localhost:8000/api/chat',  // 指向 FastAPI 端点
    maxSteps: 3,  // 允许多轮工具调用，关键！
    onToolCall: async ({ toolCall }) => {
      // 可选：自定义工具执行逻辑
      console.log('Tool called:', toolCall);
    },
    onResponse: (response) => {
      console.log('Response received:', response);
    },
    onError: (error) => {
      console.error('Chat error:', error);
    },
  });

  return (
    <div className="flex flex-col h-screen">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.map((message) => (
          <div key={message.id} className="mb-4">
            <strong className="capitalize">{message.role}:</strong>
            <div className="mt-1">
              {message.parts?.map((part, index) => {
                if (part.type === 'text') {
                  return <p key={index} className="whitespace-pre-wrap">{part.text}</p>;
                }
                if (part.type === 'tool-call') {
                  return (
                    <div key={index} className="bg-blue-50 p-2 rounded">
                      🛠️ 调用工具: {part.toolName}
                      <pre className="text-xs mt-1">{JSON.stringify(part.args, null, 2)}</pre>
                    </div>
                  );
                }
                if (part.type === 'tool-result') {
                  return (
                    <div key={index} className="bg-green-50 p-2 rounded">
                      ✅ 工具结果: {part.toolName}
                      <pre className="text-xs mt-1">{JSON.stringify(part.result, null, 2)}</pre>
                    </div>
                  );
                }
                return null;
              })}
            </div>
          </div>
        ))}
      </div>

      {/* 错误显示 */}
      {error && (
        <div className="bg-red-50 text-red-700 p-2 m-4 rounded">
          错误: {error.message}
        </div>
      )}

      {/* 输入表单 */}
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={handleInputChange}
            placeholder="输入消息..."
            disabled={isLoading}
            className="flex-1 p-2 border rounded"
          />
          <button 
            type="submit" 
            disabled={isLoading}
            className="px-4 py-2 bg-blue-500 text-white rounded disabled:bg-gray-300"
          >
            {isLoading ? '发送中...' : '发送'}
          </button>
        </div>
      </form>
    </div>
  );
}
```

### 2. 处理跨域问题（CORS）

在 FastAPI 中配置 CORS 中间件：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js 默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
```

---

## 三、数据格式协议详解

### useChat → FastAPI 请求格式

```json
{
  "messages": [
    { "role": "user", "content": "北京天气怎么样？" },
    { "role": "assistant", "content": "我来帮您查询" },
    { "role": "user", "content": "谢谢" }
  ]
}
```

### FastAPI → useChat 响应格式（SSE）

```
data: {"type": "text", "content": "我来帮您查询北京的天气"}
data: {"type": "tool-call", "toolName": "get_weather", "args": {"location": "北京"}}
data: {"type": "tool-result", "toolName": "get_weather", "result": "北京今天晴朗，25°C"}
data: {"type": "text", "content": "北京今天晴朗，温度25°C，非常适合外出！"}
data: {"type": "done"}
```