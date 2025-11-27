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
from services.agents.common_tools import get_hotboard, get_programmer_story, get_date_range
from services.agents.fine_report_tools import get_report_sample, batch_filter_report_and_get_data
from services.agents.weather_tool import get_weather
from services.agents.json_encoder import to_serializable
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
            tools = [get_report_sample, batch_filter_report_and_get_data, get_hotboard, get_programmer_story, get_date_range, get_weather]
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
        流式对话接口，使用astream_events获取Agent执行事件

        Args:
            message: 用户消息
            session_id: 会话ID
            user_id: 用户ID
            conversation_history: 对话历史列表

        Yields:
            dict: 结构化的事件数据
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

            # 使用astream_events获取离散的Agent执行事件
            callbacks = [self.tracing_handler] if self.tracing_handler else []
            current_tool_call = None

            async for event in self.agent.astream_events(
                {"messages": messages},
                config=RunnableConfig(
                    recursion_limit=10,
                    callbacks=callbacks
                )
            ):
                event_type = event.get("event", "")
                data = event.get("data", {})

                # 过滤并处理关键事件
                if event_type == "on_chain_start":
                    # 链开始，可选：发送thinking事件
                    pass

                elif event_type == "on_chat_model_stream":
                    # LLM token流
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield {
                            "event": "text",
                            "data": {
                                "content": chunk.content,
                                "type": "token"
                            }
                        }

                    # 处理工具调用chunks
                    if chunk and hasattr(chunk, "tool_call_chunks"):
                        for tool_chunk in chunk.tool_call_chunks:
                            if tool_chunk:
                                # 工具调用开始或继续
                                if tool_chunk.get("name"):
                                    current_tool_call = {
                                        "id": tool_chunk.get("id", ""),
                                        "name": tool_chunk.get("name", ""),
                                        "args": tool_chunk.get("args", "")
                                    }
                                    yield {
                                        "event": "tool_call",
                                        "data": {
                                            "id": current_tool_call["id"],
                                            "name": current_tool_call["name"],
                                            "args": current_tool_call["args"],
                                            "status": "pending",
                                            "type": "start"
                                        }
                                    }
                                elif current_tool_call:
                                    # 参数增量更新
                                    if tool_chunk.get("args"):
                                        current_tool_call["args"] += tool_chunk["args"]
                                        yield {
                                            "event": "tool_call",
                                            "data": {
                                                "id": current_tool_call["id"],
                                                "args": current_tool_call["args"],
                                                "type": "args_update"
                                            }
                                        }

                elif event_type == "on_tool_end":
                    logger.debug(f"工具执行完成事件，data: {data}")
                    # 工具执行完成
                    output = data.get("output")

                    if current_tool_call:
                        # 将输出转换为可序列化的格式
                        
                        content = output.content
                        content_obj = None
                        
                        if isinstance(content, dict):
                            content_obj = content
                        try:
                            content_obj = json.loads(content)
                        except Exception:
                            content_obj = str(content)
                            
                        tool_name = output.name

                        yield {
                            "event": "tool_result",
                            "data": {
                                "id": current_tool_call.get("id", ""),
                                "name": tool_name,
                                "result": {
                                    "type": "tool_message",
                                    "content": content_obj,
                                    "tool_call_id": output.tool_call_id,
                                    "name": output.name
                                },
                                "status": "completed"
                            }
                        }
                        current_tool_call = None

                elif event_type == "on_tool_error":
                    # 工具执行出错
                    error = data.get("error", "Unknown error")

                    if current_tool_call:
                        yield {
                            "event": "tool_result",
                            "data": {
                                "id": current_tool_call.get("id", ""),
                                "name": current_tool_call.get("name", "unknown"),
                                "result": str(error),
                                "status": "failed"
                            }
                        }
                        current_tool_call = None

            logger.info(f"Agent流式响应完成，session_id: {session_id}")

        except Exception as e:
            logger.error(f"Agent流式响应错误: {e}")
            yield {
                "event": "error",
                "data": {
                    "error": str(e)
                }
            }

# 全局Agent服务实例
agent_service = AgentService()