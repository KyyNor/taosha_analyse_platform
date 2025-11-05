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
from services.agents.tools import get_hotboard, get_programmer_story
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
            # 创建ReAct Agent，添加热榜和程序员小故事工具
            tools = [get_hotboard, get_programmer_story]
            self.agent = create_agent(
                model=self.llm_service.client,
                tools=tools,
                system_prompt="""你是一个智能助手，使用提供的工具来帮助用户回答问题。"""
            )
            logger.info("Agent初始化成功，已加载热榜和程序员小故事工具")
        except Exception as e:
            logger.error(f"Agent初始化失败: {e}")
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

            logger.info(f"正在处理Agent请求，共{len(messages)}条消息")

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

            logger.info("Agent流式响应完成")

        except Exception as e:
            logger.error(f"Agent流式响应错误: {e}")
            yield f"[错误] Agent服务出现错误: {str(e)}"


# 全局Agent服务实例
agent_service = AgentService()