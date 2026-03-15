"""
Agent服务
基于LangChain ReAct Agent的对话问答服务
"""
from typing import AsyncGenerator, AsyncIterable, Dict, Any, List, Optional
import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
import json
import uuid
import hashlib
from datetime import datetime, timedelta

from langchain_core.tools import StructuredTool
from langchain.agents.middleware import SummarizationMiddleware, PIIMiddleware, TodoListMiddleware
from services.agents.middleware import SessionNamingMiddleware
from langfuse import observe, propagate_attributes

from services.llm_service.base_llm_service import BaseLLMService
from services.tracking_service.observability_service import get_langfuse_client, get_tracing_handler
from services.agents.tools.common_tools import get_hotboard, get_programmer_story, get_date_range
from services.agents.tools.fine_report_tools import get_report_sample, batch_filter_report_and_get_data
from services.agents.tools.chart_tool import create_chart
from services.agents.tools.comparison_tool import create_comparison
from services.agents.tools.table_tool import create_table
from services.agents.tools.sql_query_tool import execute_sql_query
from services.agents.tools.table_info_tool import get_table_sample_data, get_table_statistics, get_column_statistics
from services.agents.tools.schema_linking_tool import schema_linking_retrieve
from services.agents.tools.knowledge_base_tool import knowledge_base_retrieve  # 新的知识库检索工具
from services.agents.tools.qdrant_vector_store_tool import search_knowledge_base  # 已废弃
from services.agents.tools.common_tools import add, subtract, divide, multiply
from services.agents.json_encoder import to_serializable
from utils.logger import logger

from repositories.chat_repository import ChatRepository


class AgentService:
    """Agent服务类"""

    def __init__(self):
        """初始化Agent服务"""
        self.llm_service = BaseLLMService()
        self.tracing_handler = get_tracing_handler()
        self.agent = None
        self.chat_repo = ChatRepository()

        # agent初始化移至 lifespan

    def _initialize_agent(self, checkpointer):
        """初始化Agent"""
        try:
            tools = [
                # get_report_sample,
                # batch_filter_report_and_get_data,
                get_hotboard,
                # get_programmer_story,
                get_date_range,
                create_chart,
                create_comparison,
                create_table,
                # execute_sql_query,
                # get_table_sample_data,      # 获取表样例数据
                # get_table_statistics,       # 获取表统计信息
                # get_column_statistics,      # 获取字段统计信息
                # add,
                # subtract,
                # divide,
                # multiply,
                # search_knowledge_base,      # 已废弃，拆分为两个专用工具
                schema_linking_retrieve,      # 表结构检索工具（向量+LLM两阶段筛选）
                knowledge_base_retrieve,      # 知识库检索工具（术语/关联/报表）
            ]
            _agent = create_agent(
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
                    TodoListMiddleware(),
                    SessionNamingMiddleware(),  # 添加会话自动命名中间件
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
            return _agent
        except Exception as e:
            logger.error(f"Agent初始化失败: {e}")
            raise

    async def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """从Checkpoint获取会话历史"""
        if not self.agent:
            return []
            
        try:
            config = {"configurable": {"thread_id": session_id}}
            # 使用 aget_state 获取状态 (LangGraph Checkpointer interface)
            # 注意: agent 是 CompiledGraph, 它有 aget_state 方法
            state_snapshot = await self.agent.aget_state(config)
            
            if state_snapshot and state_snapshot.values:
                messages = state_snapshot.values.get("messages", [])
                return self._format_messages(messages)
            return []
        except Exception as e:
            logger.error(f"获取会话历史失败: {e}")
            return []

    def _format_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """格式化消息列表"""
        formatted = []
        for msg in messages:
            role = "unknown"
            if isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            elif isinstance(msg, ToolMessage):
                role = "tool"
            elif msg.type == "system":
                role = "system"
            
            # 尝试提取元数据
            meta_info = msg.additional_kwargs if hasattr(msg, "additional_kwargs") else {}
            
            formatted.append({
                "id": str(getattr(msg, "id", uuid.uuid4())),
                "role": role,
                "content": str(msg.content),
                "type": "text", 
                "created_at": datetime.now(), 
                "meta_info": meta_info
            })
        return formatted

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
            from services.agents.db_checkpoint_saver import get_checkpoint_saver_context
            
            async with get_checkpoint_saver_context() as checkpointer:
                agent = self._initialize_agent(checkpointer)
                async for event in agent.astream_events(
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

                        # Checkpoint handles persistence automatically
                        
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
    async def chat_stream(self, message: str, session_id: str, user_id: str, trace_id: str = None, db: Session = None) -> AsyncGenerator[dict, None]:
        """
        流式对话接口
        """
        try:
            # 1. 确保会话存在
            repo = ChatRepository(db) if db else self.chat_repo
            session, is_new_session = repo.create_session(user_id=user_id, session_id=session_id)
            
            # 2. 创建队列
            queue = asyncio.Queue()

            # 3. 启动后台任务 (Producer)
            # 注意：不await task，让它在后台运行
            asyncio.create_task(self._run_agent_background(message, session_id, queue, trace_id))

            # 4. 消费队列 (Consumer)
            while True:
                event = await queue.get()
                logger.info(event)
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