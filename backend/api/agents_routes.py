"""
Agent API路由
提供基于LangChain ReAct Agent的对话问答功能
"""
import json
import uuid
from typing import Dict, Any, Optional
from services.tracking_service.observability_service import get_langfuse_client
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langfuse import propagate_attributes

from services.agents.agent_service import agent_service
from utils.logger import logger


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
    使用Server-Sent Events (SSE) 返回流式响应

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

            # 发送SSE头部，包含session_id
            yield f"data: {json.dumps({'type': 'start', 'content': '', 'session_id': session_id})}\n\n"

            langfuse_client = get_langfuse_client()
            output_collected = [] 
            
            with langfuse_client.start_as_current_span(name="api_chat_stream") as span:
                with propagate_attributes(user_id=user_id, session_id=session_id):
                    span.update_trace(
                        user_id=user_id,
                        session_id=session_id,
                        input=request.message
                    )
                    # 流式发送Agent响应
                    async for chunk in agent_service.chat_stream(
                        message=request.message,
                        session_id=session_id,
                        user_id=user_id,
                        conversation_history=request.conversation_history
                    ):
                        output_collected.append(chunk)
                        # 发送数据块
                        data = {
                            "type": "content",
                            "content": chunk
                        }
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    
                    span.update(output={"response": ''.join(output_collected)})

            # 发送结束标记
            yield f"data: {json.dumps({'type': 'end', 'content': ''})}\n\n"

            logger.info(f"流式聊天完成, session_id: {session_id}")

        except Exception as e:
            logger.error(f"流式聊天错误: {e}")
            error_data = {
                "type": "error",
                "content": f"流式聊天服务错误: {str(e)}"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


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