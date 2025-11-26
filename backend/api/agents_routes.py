"""
Agent API路由
提供基于LangChain ReAct Agent的对话问答功能
"""
import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from services.tracking_service.observability_service import get_langfuse_client
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langfuse import propagate_attributes

from services.agents.agent_service import agent_service
from services.agents.json_encoder import LangChainJSONEncoder, serialize_event_data
from services.agents.vercel_bridge import LangChainToVercelBridge
from utils.logger import logger
import time


router = APIRouter(prefix="/agents")


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    conversation_history: list = []


class ChatResponse(BaseModel):
    """聊天响应模型"""
    content: str
    status: str = "success"
    session_id: Optional[str] = None


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    聊天接口（非流式）

    Args:
        request: 聊天请求

    Returns:
        ChatResponse: 聊天响应
    """
    try:
        # 处理默认值
        user_id = request.user_id or "api_user"
        session_id = request.session_id or str(uuid.uuid4())

        logger.info(f"收到聊天请求: {request.message[:100]}..., user_id: {user_id}, session_id: {session_id}")

        # 收集所有流式响应
        response_content = ""
        langfuse_client = get_langfuse_client()

        
        with langfuse_client.start_as_current_span(name="api_chat") as span:
            with propagate_attributes(user_id=user_id, session_id=session_id):
                span.update_trace(
                    user_id=user_id,
                    session_id=session_id,
                    input=request.message
                )
                async for chunk in agent_service.chat_stream(
                    message=request.message,
                    session_id=session_id,
                    user_id=user_id,
                    conversation_history=request.conversation_history
                ):
                    response_content += chunk
                    
                span.update(output={"response": ''.join(response_content)})


        return ChatResponse(content=response_content, session_id=session_id)

    except Exception as e:
        logger.error(f"聊天接口错误: {e}")
        raise HTTPException(status_code=500, detail=f"聊天服务错误: {str(e)}")




@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest) -> StreamingResponse:
    """
    流式聊天接口
    使用Server-Sent Events (SSE) 返回结构化的Agent事件流

    事件类型：
    - start: 流开始，包含session_id
    - text: 文本token响应
    - tool_call: 工具调用事件
    - tool_result: 工具执行结果
    - end: 流结束
    - error: 错误信息

    Args:
        request: 聊天请求

    Returns:
        StreamingResponse: 流式响应
    """
    async def generate_stream():
        """生成流式响应"""
        try:
            # 处理默认值
            user_id = request.user_id or "api_user"
            session_id = request.session_id or str(uuid.uuid4())

            logger.info(f"收到流式聊天请求: {request.message[:100]}..., user_id: {user_id}, session_id: {session_id}")

            # 发送流开始事件
            yield f"data: {json.dumps({'event': 'start', 'data': {'session_id': session_id}}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)  # 强制刷新缓冲区

            langfuse_client = get_langfuse_client()
            full_response = ""
            event_count = 0

            with langfuse_client.start_as_current_span(name="api_chat_stream") as span:
                with propagate_attributes(user_id=user_id, session_id=session_id):
                    span.update_trace(
                        user_id=user_id,
                        session_id=session_id,
                        input=request.message
                    )

                    # 流式发送Agent事件
                    async for event_data in agent_service.chat_stream(
                        message=request.message,
                        session_id=session_id,
                        user_id=user_id,
                        conversation_history=request.conversation_history
                    ):
                        # 直接转发Agent服务返回的事件
                        event_type = event_data.get("event", "unknown")
                        event_count += 1

                        # 仅收集文本响应用于追踪
                        if event_type == "text":
                            content = event_data.get("data", {}).get("content", "")
                            full_response += content

                        # 发送SSE格式的事件，使用自定义编码器处理LangChain对象
                        try:
                            sse_line = f"data: {serialize_event_data(event_data)}\n\n"
                        except Exception as e:
                            logger.warning(f"事件序列化失败: {e}, 使用fallback处理")
                            # Fallback: 尝试用标准编码器，如果还是失败就记录错误信息
                            try:
                                event_data_fallback = {
                                    "event": event_type,
                                    "data": {"error": "failed to serialize event data"}
                                }
                                sse_line = f"data: {json.dumps(event_data_fallback, ensure_ascii=False)}\n\n"
                            except Exception as fallback_error:
                                logger.error(f"事件序列化fallback也失败: {fallback_error}")
                                continue

                        logger.debug(f"发送SSE事件 #{event_count}: {event_type}")
                        yield sse_line
                        await asyncio.sleep(0)  # 立即刷新缓冲区，不阻塞等待

                    span.update(output={"response": full_response})

            # 发送结束事件
            event_count += 1
            yield f"data: {json.dumps({'event': 'end', 'data': {}}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)  # 最后一次刷新

            logger.info(f"流式聊天完成, session_id: {session_id}, 共发送{event_count}个事件")

        except Exception as e:
            logger.error(f"流式聊天错误: {e}")
            error_data = {
                "event": "error",
                "data": {
                    "error": str(e)
                }
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/chat/vercel-stream")
async def chat_vercel_stream_endpoint(request: ChatRequest) -> StreamingResponse:
    """
    Vercel AI SDK兼容的流式聊天接口

    将LangChain Agent的astream_events转换为Vercel AI SDK兼容的SSE流格式
    用于支持生成式UI功能

    事件类型（Vercel格式）：
    - assistant_message_start: 消息开始
    - text_delta: 文本增量
    - tool_call_start: 工具调用开始
    - tool_call_input: 工具输入参数
    - tool_call_result: 工具执行结果
    - tool_call_error: 工具调用错误
    - assistant_message_complete: 消息完成
    - done: 流结束
    - error: 错误信息

    Args:
        request: 聊天请求

    Returns:
        StreamingResponse: Vercel格式的流式响应
    """
    async def generate_vercel_stream():
        """生成Vercel AI SDK兼容的流式响应"""
        try:
            # 处理默认值
            user_id = request.user_id or "api_user"
            session_id = request.session_id or str(uuid.uuid4())

            logger.info(f"收到Vercel格式流式聊天请求: {request.message[:100]}..., user_id: {user_id}, session_id: {session_id}")

            # 创建桥接器实例
            bridge = LangChainToVercelBridge()

            langfuse_client = get_langfuse_client()

            with langfuse_client.start_as_current_span(name="api_chat_vercel_stream") as span:
                with propagate_attributes(user_id=user_id, session_id=session_id):
                    span.update_trace(
                        user_id=user_id,
                        session_id=session_id,
                        input=request.message
                    )

                    # 获取LangChain的原始事件流
                    langchain_stream = agent_service.agent.astream_events(
                        {"messages": request.message},
                    )

                    # 使用桥接器转换为Vercel格式并流式输出
                    event_count = 0
                    async for sse_message in bridge.convert_stream(langchain_stream):
                        event_count += 1
                        logger.debug(f"发送Vercel SSE事件 #{event_count}")
                        yield sse_message
                        await asyncio.sleep(0)  # 立即刷新缓冲区

                    span.update(output={"response": bridge.current_text_buffer})

            logger.info(f"Vercel流式聊天完成, session_id: {session_id}, 共发送{event_count}个事件")

        except Exception as e:
            logger.error(f"Vercel流式聊天错误: {e}")
            error_message = f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
            yield error_message
            await asyncio.sleep(0)

    return StreamingResponse(
        generate_vercel_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "X-Accel-Buffering": "no",
        }
    )


class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = True
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None

class ChatCompletionChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Usage

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    健康检查接口

    Returns:
        Dict: 健康状态
    """
    try:
        # 检查Agent服务状态
        agent_status = "healthy" if agent_service.agent is not None else "unhealthy"

        return {
            "status": "success",
            "service": "agent",
            "agent_status": agent_status,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "error",
            "service": "agent",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        }