"""
Agent服务
基于LangChain ReAct Agent的对话问答服务
"""
import asyncio
from typing import AsyncGenerator, Dict, Any
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
import json
import uuid
import hashlib

from langchain_core.tools import StructuredTool
from langchain.agents.middleware import SummarizationMiddleware, PIIMiddleware, TodoListMiddleware
import langfuse
from langfuse import observe

from services.llm_service.base_llm_service import BaseLLMService
from services.tracking_service.observability_service import get_tracing_handler
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

    @observe(name="agent_chat_stream", capture_input=False)
    async def chat_stream(self, message: str, conversation_history: list = None) -> AsyncGenerator[str, None]:
        """
        流式对话接口

        Args:
            message: 用户消息
            conversation_history: 对话历史列表

        Yields:
            str: 流式响应的token
        """
        try:
            # 生成或提取session_id
            session_id = self._extract_or_create_session_id(conversation_history)

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

            # 使用stream方法获取流式响应，配置CallbackHandler
            callbacks = [self.tracing_handler] if self.tracing_handler else []
            async for chunk in self.agent.astream(
                {"messages": messages},
                config=RunnableConfig(
                    recursion_limit=10,
                    callbacks=callbacks,
                    metadata={
                        "session_id": session_id,
                        "user_id": "api_user"  # todo 临时写死，后续改为从token解析
                    }
                )
            ):
                # 解析chunk并提取内容
                if isinstance(chunk, dict):
                    # 检查是否包含agent或model的输出
                    for key, value in chunk.items():
                        if key in ["agent", "model"] and isinstance(value, dict):
                            if "messages" in value:
                                for msg in value["messages"]:
                                    if hasattr(msg, "content") and msg.content:
                                        # 流式返回内容
                                        if isinstance(msg.content, str):
                                            for char in msg.content:
                                                yield char
                                                await asyncio.sleep(0.01)  # 控制流式速度
                                        elif isinstance(msg.content, list):
                                            # 处理多模态内容
                                            for content in msg.content:
                                                if hasattr(content, "text") and content.text:
                                                    for char in content.text:
                                                        yield char
                                                        await asyncio.sleep(0.01)

                        elif isinstance(value, str):
                            # 直接返回字符串内容
                            for char in value:
                                yield char
                                await asyncio.sleep(0.01)

            logger.info(f"Agent流式响应完成，session_id: {session_id}")

        except Exception as e:
            logger.error(f"Agent流式响应错误: {e}")
            yield f"[错误] Agent服务出现错误: {str(e)}"

    def _extract_or_create_session_id(self, conversation_history: list = None) -> str:
        """
        从对话历史中提取session_id，没有则创建新的

        Args:
            conversation_history: 对话历史列表

        Returns:
            str: session_id
        """
        if conversation_history:
            # 从对话历史中提取session_id，寻找最后一条assistant消息
            for msg in reversed(conversation_history):
                if msg.get("role") == "assistant" and msg.get("content"):
                    # 使用内容的hash作为稳定的session_id
                    content_hash = hashlib.md5(msg.get("content", "").encode()).hexdigest()[:8]
                    logger.debug(f"从历史消息中提取session_id: {content_hash}")
                    return content_hash

        # 没有历史记录则创建新的session_id
        new_session_id = str(uuid.uuid4())[:8]
        logger.debug(f"创建新的session_id: {new_session_id}")
        return new_session_id


# 全局Agent服务实例
agent_service = AgentService()