"""
Agent服务
基于LangChain ReAct Agent的对话问答服务
"""
from typing import AsyncGenerator, AsyncIterable, Dict, Any
import asyncio
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
import json
import uuid
import hashlib
from datetime import datetime, timedelta

from langchain_core.tools import StructuredTool
from langchain.agents.middleware import SummarizationMiddleware, PIIMiddleware, TodoListMiddleware
from langfuse import observe, propagate_attributes

from services.llm_service.base_llm_service import BaseLLMService
from services.tracking_service.observability_service import get_langfuse_client, get_tracing_handler
from services.agents.common_tools import get_hotboard, get_programmer_story, get_date_range
from services.agents.fine_report_tools import get_report_sample, batch_filter_report_and_get_data
from services.agents.weather_tool import get_weather
from services.agents.chart_tool import create_chart
from services.agents.metrics_tool import get_metrics
from services.agents.json_encoder import to_serializable
from utils.logger import logger

from backend.repositories.chat_repository import ChatRepository
from backend.services.agents.db_checkpoint_saver import DatabaseCheckpointSaver


class AgentService:
    """Agent服务类"""

    def __init__(self):
        """初始化Agent服务"""
        self.llm_service = BaseLLMService()
        self.tracing_handler = get_tracing_handler()
        self.agent = None
        self.chat_repo = ChatRepository()

        self._initialize_agent()

    def _initialize_agent(self):
        """初始化Agent"""
        try:
            # 使用数据库持久化
            checkpointer = DatabaseCheckpointSaver()

            tools = [
                # get_report_sample, 
                # batch_filter_report_and_get_data, 
                # get_hotboard, 
                # get_programmer_story, 
                get_date_range, 
                get_weather, 
                create_chart, 
                get_metrics, 
            ]
            self.agent = create_agent(
                model=self.llm_service.client,
                tools=tools,
                system_prompt="""你是一个智能助手，使用提供的工具来帮助用户回答问题。""",
                checkpointer=checkpointer,
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

    async def _run_agent_background(self, message: str, session_id: str, queue: asyncio.Queue, trace_id: str):
        """后台运行Agent任务，并将事件推送到队列，同时保存历史记录"""
        try:
            logger.info(f"Agent后台任务开始, session_id: {session_id}")
            
            # 推送开始事件
            await queue.put({
                "event": "start",
                "data": {
                    "session_id": session_id,
                    "trace_id": trace_id
                }
            })

            callbacks = [self.tracing_handler] if self.tracing_handler else []
            current_tool_call = None
            
            async for event in self.agent.astream_events(
                {"messages": [HumanMessage(content=message)]},
                config=RunnableConfig(
                    recursion_limit=100,
                    callbacks=callbacks,
                    configurable={"thread_id": session_id}
                )
            ):
                event_type = event.get("event", "")
                data = event.get("data", {})

                # 1. 处理 LLM 流式输出 (Token)
                if event_type == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    # 文本 Token
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        await queue.put({
                            "event": "text",
                            "data": {
                                "content": chunk.content,
                                "type": "token"
                            }
                        })
                    
                    # 工具调用 Chunk
                    if chunk and hasattr(chunk, "tool_call_chunks"):
                        for tool_chunk in chunk.tool_call_chunks:
                            if tool_chunk:
                                if tool_chunk.get("name"):
                                    current_tool_call = {
                                        "id": tool_chunk.get("id", ""),
                                        "name": tool_chunk.get("name", ""),
                                        "args": tool_chunk.get("args", "")
                                    }
                                    await queue.put({
                                        "event": "tool_call",
                                        "data": {
                                            "id": current_tool_call["id"],
                                            "name": current_tool_call["name"],
                                            "args": current_tool_call["args"],
                                            "status": "pending",
                                            "type": "start"
                                        }
                                    })
                                elif current_tool_call:
                                    if tool_chunk.get("args"):
                                        current_tool_call["args"] += tool_chunk["args"]
                                        await queue.put({
                                            "event": "tool_call",
                                            "data": {
                                                "id": current_tool_call["id"],
                                                "args": current_tool_call["args"],
                                                "type": "args_update"
                                            }
                                        })

                # 2. 处理 LLM 完整输出 (保存到 DB)
                elif event_type == "on_chat_model_end":
                    output = data.get("output")
                    if output and isinstance(output, AIMessage):
                        content = output.content
                        # 只有当内容不为空时才保存 (避免纯工具调用的中间状态)
                        if content:
                            self.chat_repo.add_message(
                                session_id=session_id,
                                role="assistant",
                                content=str(content),
                                msg_type="text"
                            )
                
                # 3. 处理工具执行完成
                elif event_type == "on_tool_end":
                    output = data.get("output")
                    
                    # 格式化输出
                    content_obj = None
                    tool_name = current_tool_call.get("name", "unknown") if current_tool_call else "unknown"
                    tool_call_id = current_tool_call.get("id", "") if current_tool_call else ""

                    if hasattr(output, 'update'): # Command
                        command_info = output.update
                        todos_dict = command_info.get("todos", "")
                        if todos_dict:
                            content_obj = todos_dict
                            tool_name = "todo_list_tool"
                    elif hasattr(output, 'content'): # ToolMessage
                        content = output.content
                        if isinstance(content, dict):
                            content_obj = content
                        else:
                            try:
                                content_obj = json.loads(content)
                            except Exception:
                                content_obj = str(content)
                        tool_name = getattr(output, 'name', tool_name)
                    else:
                        content_obj = str(output)

                    # 发送事件到前端
                    await queue.put({
                        "event": "tool_result",
                        "data": {
                            "id": tool_call_id,
                            "name": tool_name,
                            "result": {
                                "type": "tool_message",
                                "content": content_obj,
                                "tool_call_id": tool_call_id,
                                "name": tool_name
                            },
                            "status": "completed"
                        }
                    })

                    # 保存工具结果到 DB
                    self.chat_repo.add_message(
                        session_id=session_id,
                        role="tool",
                        content=json.dumps(content_obj, ensure_ascii=False) if not isinstance(content_obj, str) else content_obj,
                        msg_type="json" if isinstance(content_obj, (dict, list)) else "text",
                        meta_info={"tool_name": tool_name, "tool_call_id": tool_call_id}
                    )
                    
                    current_tool_call = None

                elif event_type == "on_tool_error":
                    error = data.get("error", "Unknown error")
                    if current_tool_call:
                        await queue.put({
                            "event": "tool_result",
                            "data": {
                                "id": current_tool_call.get("id", ""),
                                "name": current_tool_call.get("name", "unknown"),
                                "result": str(error),
                                "status": "failed"
                            }
                        })
                        current_tool_call = None

            # 任务完成
            await queue.put(None)
            logger.info(f"Agent后台任务完成, session_id: {session_id}")

        except Exception as e:
            logger.error(f"Agent后台任务出错: {e}")
            await queue.put({
                "event": "error",
                "data": {"error": str(e), "trace_id": trace_id}
            })
            await queue.put(None)

    @observe(name="agent_chat_stream")
    async def chat_stream(self, message: str, session_id: str, user_id: str, trace_id: str = None) -> AsyncGenerator[dict, None]:
        """
        流式对话接口
        """
        try:
            # 1. 确保会话存在
            self.chat_repo.create_session(user_id=user_id, session_id=session_id)
            
            # 2. 保存用户消息
            self.chat_repo.add_message(session_id, "user", message)

            # 3. 创建队列
            queue = asyncio.Queue()

            # 4. 启动后台任务 (Producer)
            # 注意：不await task，让它在后台运行
            asyncio.create_task(self._run_agent_background(message, session_id, queue, trace_id))

            # 5. 消费队列 (Consumer)
            while True:
                event = await queue.get()
                if event is None: # 结束信号
                    break
                yield event
                
        except Exception as e:
            logger.error(f"Agent流式响应错误: {e}")
            yield {
                "event": "error",
                "data": {
                    "error": str(e),
                    "trace_id": trace_id
                }
            }

    def _process_chunk(self, chunk: Dict[str, Any], trace_id: str = None) -> Dict[str, Any]:
        """处理事件块，添加 trace_id"""
        if isinstance(chunk.get('data'), dict) and trace_id:
            chunk['data']['trace_id'] = trace_id
        return chunk

# 全局Agent服务实例
agent_service = AgentService()