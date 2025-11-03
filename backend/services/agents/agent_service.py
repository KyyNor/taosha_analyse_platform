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

from services.llm_service.base_llm_service import BaseLLMService
from utils.logger import logger


class AgentService:
    """Agent服务类"""

    def __init__(self):
        """初始化Agent服务"""
        self.llm_service = BaseLLMService()
        self.agent = None
        self._initialize_agent()

    def _initialize_agent(self):
        """初始化Agent"""
        try:
            # 创建ReAct Agent，暂时不使用工具
            self.agent = create_agent(
                model=self.llm_service.client,
                tools=[],  # 暂时不使用工具
                system_prompt="你是一个智能助手，专门帮助用户进行数据分析和问答。请用简洁、准确的方式回答用户的问题。"
            )
            logger.info("Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise

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

            logger.info(f"Processing agent request with {len(messages)} messages")

            # 使用stream方法获取流式响应
            async for chunk in self.agent.astream(
                {"messages": messages},
                config=RunnableConfig(recursion_limit=10)
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

            logger.info("Agent streaming completed successfully")

        except Exception as e:
            logger.error(f"Error in agent streaming: {e}")
            yield f"[ERROR] Agent服务出现错误: {str(e)}"


# 全局Agent服务实例
agent_service = AgentService()