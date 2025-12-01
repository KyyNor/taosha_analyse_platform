"""
Agent API路由
提供基于LangChain ReAct Agent的对话问答功能
"""
import json
import uuid
import time
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langfuse import propagate_attributes

from services.agents.agent_service import agent_service
from backend.repositories.chat_repository import ChatRepository
from services.tracking_service.observability_service import get_langfuse_client
from utils.logger import logger


router = APIRouter(prefix="/agents")
chat_repo = ChatRepository()

# --- 请求/响应模型 ---

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    trace_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    content: str
    status: str = "success"
    session_id: Optional[str] = None

class SessionResponse(BaseModel):
    """会话列表项响应"""
    id: str
    title: Optional[str]
    updated_at: str

class MessageResponse(BaseModel):
    """消息历史项响应"""
    id: str
    role: str
    content: str
    type: str
    created_at: str
    meta_info: Optional[Dict] = None

# --- 聊天接口 ---

@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest) -> StreamingResponse:
    """
    流式聊天接口

    支持生成式UI功能和动态组件渲染，直接输出LangChain原生事件格式
    自动持久化会话和消息。

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
            trace_id = request.trace_id or f"trace_{int(time.time())}_{uuid.uuid4().hex[:8]}"

            logger.info(f"收到流式聊天请求: {request.message[:100]}..., user_id: {user_id}, session_id: {session_id}, trace_id: {trace_id}")

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
                        trace_id=trace_id
                    ):
                        event_count += 1
                        logger.debug(f"发送SSE事件 #{event_count}: {event.get('event', 'unknown')}, trace_id: {trace_id}")

                        # 直接输出原生事件格式
                        sse_message = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                        yield sse_message
                        await asyncio.sleep(0)  # 立即刷新缓冲区

                    span.update(output={"events_sent": event_count})

            logger.info(f"流式聊天完成, session_id: {session_id}, trace_id: {trace_id}, 共发送{event_count}个事件")

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

# --- 历史记录接口 ---

@router.get("/history")
async def get_history(user_id: str = Query(..., description="用户ID"), limit: int = 20) -> List[SessionResponse]:
    """获取用户的会话列表"""
    sessions = chat_repo.get_user_sessions(user_id, limit)
    return [
        SessionResponse(
            id=s.id,
            title=s.title,
            updated_at=s.updated_at.isoformat() if s.updated_at else ""
        ) for s in sessions
    ]

@router.get("/history/{session_id}")
async def get_session_messages(session_id: str) -> List[MessageResponse]:
    """获取指定会话的消息历史"""
    messages = chat_repo.get_session_history(session_id)
    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content or "",
            type=m.type,
            created_at=m.created_at.isoformat() if m.created_at else "",
            meta_info=m.meta_info
        ) for m in messages
    ]

@router.delete("/history/{session_id}")
async def delete_session(session_id: str, user_id: str = Query(..., description="用户ID")):
    """删除会话"""
    success = chat_repo.delete_session(session_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or permission denied")
    return {"status": "success", "message": "Session deleted"}

@router.put("/history/{session_id}/title")
async def update_session_title(session_id: str, title: str = Query(..., description="新标题")):
    """更新会话标题"""
    chat_repo.update_session_title(session_id, title)
    return {"status": "success", "message": "Title updated"}


# --- 健康检查 ---

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    健康检查接口
    """
    try:
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
