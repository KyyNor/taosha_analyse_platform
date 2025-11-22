"""
Agent服务
基于LangChain ReAct Agent的对话问答服务
"""
from typing import AsyncGenerator, AsyncIterable, Dict, Any
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
import json
import uuid
import hashlib

from langchain_core.tools import StructuredTool
from langchain.agents.middleware import SummarizationMiddleware, PIIMiddleware, TodoListMiddleware
from langfuse import observe, propagate_attributes

from services.llm_service.base_llm_service import BaseLLMService
from services.tracking_service.observability_service import get_langfuse_client, get_tracing_handler
from services.agents.common_tools import get_hotboard, get_programmer_story
from services.agents.fine_report_tools import get_report_sample, batch_filter_report_and_get_data
from utils.logger import logger


class AgentService:
    """Agent服务类"""

    def __init__(self):
        """初始化Agent服务"""
        self.llm_service = BaseLLMService()
        self.tracing_handler = get_tracing_handler()
        self.agent = None
        self._initialize_agent()

    def _initialize_agent(self):
        """初始化Agent"""
        try:
            tools = [get_report_sample, batch_filter_report_and_get_data]
            self.agent = create_agent(
                model=self.llm_service.client,
                tools=tools,
                system_prompt="""你是一个智能助手，使用提供的工具来帮助用户回答问题。""",
                middleware=[
                    SummarizationMiddleware(
                        model=self.llm_service.client,
                        max_tokens_before_summary=50000,
                        messages_to_keep=20,
                        summary_prompt="请你总结以上内容。"
                    ),
                    PIIMiddleware("credit_card", strategy="mask", apply_to_output=True),
                    TodoListMiddleware(),
                    # LLMToolSelectorMiddleware(
                    #     model="gpt-4o-mini",  # Use cheaper model for selection
                    #     max_tools=3,  # Limit to 3 most relevant tools
                    #     always_include=["search"],  # Always include certain tools
                    # ),
                    # ContextEditingMiddleware(
                    #     edits=[
                    #         ClearToolUsesEdit(trigger=1000),  # Clear old tool uses
                    #     ],
                    # ),
                ]
            )
            logger.info("Agent初始化成功")
        except Exception as e:
            logger.error(f"Agent初始化失败: {e}")
            raise

    @observe(name="agent_chat_stream")
    async def chat_stream(self, message: str, session_id: str, user_id: str, conversation_history: list = None) -> AsyncGenerator[dict, None]:
        """
        流式对话接口

        Args:
            message: 用户消息
            conversation_history: 对话历史列表

        Yields:
            str: 流式响应的token
        """
        try:

            # 构建消息历史
            messages = []

            # 添加历史消息
            if conversation_history:
                for msg in conversation_history:
                    if msg.get("role") == "user":
                        messages.append(HumanMessage(content=msg.get("content", "")))
                    elif msg.get("role") == "assistant":
                        messages.append(AIMessage(content=msg.get("content", "")))

            # 添加当前用户消息
            messages.append(HumanMessage(content=message))

            logger.info(f"正在处理Agent请求，共{len(messages)}条消息，session_id: {session_id}")

            # 使用stream_mode="messages"直接获取LLM token流，利用LangChain原生流式
            callbacks = [self.tracing_handler] if self.tracing_handler else []
            async for chunk in self.agent.astream(
                {"messages": messages},
                config=RunnableConfig(
                    recursion_limit=10,
                    callbacks=callbacks
                ),
                stream_mode="messages"  # 直接获取LangChain token
            ):
                # 直接返回LangChain token的content，利用其原生流式控制
                yield chunk

            logger.info(f"Agent流式响应完成，session_id: {session_id}")

        except Exception as e:
            logger.error(f"Agent流式响应错误: {e}")
            # yield f"[错误] Agent服务出现错误: {str(e)}"

    def to_openai_chunk(self, role: str, content: str, finish_reason=None):
        """生成一个符合 OpenAI 格式的 SSE chunk"""
        chunk = {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion.chunk",
            "created": int(uuid.uuid1().time),
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "delta": {} if finish_reason else {"role": role, "content": content},
                    "finish_reason": finish_reason,
                }
            ],
        }
        return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    
    async def agent_stream_to_openai(self, user_input: str) -> AsyncIterable[str]:
        """实时消费 agent.stream() 并转成 OpenAI 格式"""
        # 开始：先推一个 role=assistant
        yield self.to_openai_chunk("assistant", "")

        # 逐条事件解析
        async for event in self.agent.astream({"messages": [("user", user_input)]}):
            # event 结构：{node_name: {messages: [AIMessage, ...]}}
            for node, payload in event.items():
                msg = payload["messages"][-1]
                if hasattr(msg, "content"):
                    yield self.to_openai_chunk("", msg.content)

        # 结束标志
        yield self.to_openai_chunk("", "", finish_reason="stop")
        yield "data: [DONE]\n\n"

# 全局Agent服务实例
agent_service = AgentService()