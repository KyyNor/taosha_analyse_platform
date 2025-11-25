这里是基于方案1（预置组件 + JSON流式传输）的详细实现步骤。此方案不强依赖 Vercel AI SDK 的 Node.js 协议，而是使用通用的 NDJSON（换行符分隔的 JSON）流，兼容性最强。

**前提：**
1.  后端已安装：`langchain`, `langchain-openai`, `fastapi`, `uvicorn`, `pydantic`。
2.  前端已安装：`react`, `lucide-react` (可选图标库)。

---

1. 后端：定义数据结构与工具

在后端代码中声明 UI 组件所需的数据结构，并将其封装为 LangChain 的 Tool。

`backend/tools.py`

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# 1. 定义组件的数据模型（Props）
class WeatherCardProps(BaseModel):
    location: str = Field(description="城市名称，例如 北京、上海")
    temperature: int = Field(description="当前气温，摄氏度")
    condition: str = Field(description="天气状况，例如 晴朗、多云、雷阵雨")
    humidity: str = Field(description="湿度，例如 45%")

# 2. 定义工具
# 注意：作为 Generative UI，甚至不需要在这个函数里写真实的查询逻辑，
# 目前只需要利用大模型的参数生成能力。
@tool("weather_card_tool", args_schema=WeatherCardProps)
def weather_card_tool(location: str, temperature: int, condition: str, humidity: str):
    """
    当用户询问天气时调用此工具。
    返回结构化数据以在前端渲染卡片。
    """
    # 在实际业务中，这里可以留空或者返回简单回执，
    # 重点在于前端拦截到这个工具调用请求。
    return "Weather card generated."
```

2. 后端：构建 Agent 与流式 API 接口

在 FastAPI 中处理 LangChain 的事件流，将文本块和工具调用块分开包装。

`backend/server.py`

```python
import json
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from tools import weather_card_tool

app = FastAPI()

# 初始化 Agent
tools = [weather_card_tool]
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个助手。如果用户问天气，请务必调用 weather_card_tool。"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    async def generate_stream():
        # 监听 LangChain 事件
        async for event in agent_executor.astream_events(
            {"input": request.message}, version="v1"
        ):
            kind = event["event"]
            
            # 1. 处理文本流 (Streaming Text)
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield json.dumps({"type": "text", "content": content}) + "\n"

            # 2. 处理工具调用 (Generative UI Trigger)
            # 监听 'on_tool_start' 事件获取完整的工具参数
            elif kind == "on_tool_start":
                tool_name = event["name"]
                # 过滤掉可能存在的内部工具，只处理 UI 工具
                if tool_name == "weather_card_tool":
                    tool_input = event["data"].get("input")
                    yield json.dumps({
                        "type": "ui",
                        "component": "weather-card", # 前端组件标识
                        "props": tool_input
                    }) + "\n"

    return StreamingResponse(generate_stream(), media_type="application/x-ndjson")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

3. 前端：封装 WeatherCard 组件

创建一个纯展示组件，接收后端生成的 Props。

`frontend/components/WeatherCard.tsx`

```tsx
import React from 'react';

interface WeatherCardProps {
  location: string;
  temperature: number;
  condition: string;
  humidity: string;
}

export const WeatherCard: React.FC<WeatherCardProps> = ({ 
  location, temperature, condition, humidity 
}) => {
  return (
    <div className="my-4 p-6 max-w-sm bg-white rounded-xl shadow-lg border border-gray-100">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-bold text-gray-800">{location}</h3>
        <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
          {condition}
        </span>
      </div>
      <div className="flex items-end space-x-2">
        <span className="text-5xl font-bold text-gray-900">{temperature}°</span>
        <span className="text-gray-500 mb-1">C</span>
      </div>
      <div className="mt-4 pt-4 border-t border-gray-100 text-sm text-gray-500">
        湿度: {humidity}
      </div>
    </div>
  );
};
```

4. 前端：实现流式请求页面

在页面中解析 NDJSON 流，并根据类型动态渲染组件。

`frontend/app/page.tsx`

```tsx
"use client";
import { useState } from 'react';
import { WeatherCard } from '../components/WeatherCard';

// 消息类型定义
type Message = {
  role: 'user' | 'assistant';
  content: string;
  ui?: {
    component: string;
    props: any;
  };
};

export default function ChatPage() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input }),
      });

      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      // 初始化一条空的助手消息
      let currentMsg: Message = { role: 'assistant', content: '' };
      setMessages(prev => [...prev, currentMsg]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // 解析流数据
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n').filter(line => line.trim() !== '');

        for (const line of lines) {
          try {
            const data = JSON.parse(line);

            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];

              if (data.type === 'text') {
                // 追加文本
                lastMsg.content += data.content;
              } else if (data.type === 'ui') {
                // 注入 UI 数据
                lastMsg.ui = {
                  component: data.component,
                  props: data.props
                };
              }
              return newMessages;
            });
          } catch (e) {
            console.error("JSON Parse Error", e);
          }
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4 h-screen flex flex-col">
      <div className="flex-1 overflow-y-auto space-y-6 pb-4">
        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] ${msg.role === 'user' ? 'bg-blue-500 text-white p-3 rounded-lg' : 'w-full'}`}>
              
              {/* 1. 文字内容渲染 */}
              {msg.content && (
                <div className={`markdown-body ${msg.role === 'assistant' ? 'text-gray-800' : ''}`}>
                  {msg.content}
                </div>
              )}

              {/* 2. 组件动态渲染 (Generative UI) */}
              {msg.ui?.component === 'weather-card' && (
                <div className="mt-2 animate-fade-in">
                  <WeatherCard {...msg.ui.props} />
                </div>
              )}
              
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-2 pt-4 border-t border-gray-200">
        <input
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !isLoading && sendMessage()}
          placeholder="输入：北京现在的天气..."
          disabled={isLoading}
        />
        <button
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          onClick={sendMessage}
          disabled={isLoading}
        >
          发送
        </button>
      </div>
    </div>
  );
}
```