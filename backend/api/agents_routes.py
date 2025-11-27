"""
Agent API路由
提供基于LangChain ReAct Agent的对话问答功能
"""
import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langfuse import propagate_attributes

from services.agents.agent_service import agent_service
from services.tracking_service.observability_service import get_langfuse_client
from utils.logger import logger


router = APIRouter(prefix="/agents")


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    content: str
    status: str = "success"
    session_id: Optional[str] = None


@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest) -> StreamingResponse:
    """
    流式聊天接口

    支持生成式UI功能和动态组件渲染，直接输出LangChain原生事件格式

    事件类型：
    - text: 文本token流
    - tool_call: 工具调用（开始/参数更新）
    - tool_result: 工具执行结果
    - error: 错误信息

    Args:
        request: 聊天请求

    Returns:
        StreamingResponse: 原生LangChain格式的流式响应
    """
    async def generate_stream():
        """生成原生LangChain事件格式的流式响应"""
        try:
            # 处理默认值
            user_id = request.user_id or "api_user"
            session_id = request.session_id or str(uuid.uuid4())

            logger.info(f"收到流式聊天请求: {request.message[:100]}..., user_id: {user_id}, session_id: {session_id}")

            langfuse_client = get_langfuse_client()

            with langfuse_client.start_as_current_span(name="api_chat_stream") as span:
                with propagate_attributes(user_id=user_id, session_id=session_id):
                    span.update_trace(
                        user_id=user_id,
                        session_id=session_id,
                        input=request.message
                    )

                    # 直接使用agent_service的chat_stream方法
                    event_count = 0
                    async for event in agent_service.chat_stream(
                        message=request.message,
                        session_id=session_id,
                        user_id=user_id,
                    ):
                        event_count += 1
                        logger.debug(f"发送SSE事件 #{event_count}: {event.get('event', 'unknown')}")

                        # 直接输出原生事件格式
                        sse_message = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                        yield sse_message
                        await asyncio.sleep(0)  # 立即刷新缓冲区

                    span.update(output={"events_sent": event_count})

            logger.info(f"流式聊天完成, session_id: {session_id}, 共发送{event_count}个事件")

        except Exception as e:
            logger.error(f"流式聊天错误: {e}")
            error_event = {
                "event": "error",
                "data": {
                    "error": str(e)
                }
            }
            error_message = f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
            yield error_message
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