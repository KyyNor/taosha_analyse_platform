"""
WebSocket路由
"""
import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

from services.websocket.manager import connection_manager, websocket_handler

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

router = APIRouter()


async def get_current_user_from_websocket(
    websocket: WebSocket,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[int]:
    """从WebSocket连接中获取当前用户"""
    # TODO: 实现用户认证逻辑
    # 这里应该验证JWT token并返回用户ID
    # 暂时返回测试用户ID
    return 1


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None
):
    """WebSocket端点"""
    connection_id = str(uuid.uuid4())
    user_id = None
    
    try:
        # TODO: 验证token并获取用户信息
        if token:
            # 简单的token验证逻辑（实际应该解析JWT）
            try:
                user_id = 1  # 暂时使用测试用户ID
            except Exception as e:
                logger.warning(f"Token验证失败: {e}")
        
        # 建立连接
        await connection_manager.connect(websocket, connection_id, user_id)
        
        # 监听消息
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # 处理消息
                await websocket_handler.handle_message(connection_id, message_data)
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                await connection_manager.send_message(connection_id, {
                    "type": "error",
                    "data": {"message": "消息格式错误"}
                })
            
            except Exception as e:
                logger.error(f"处理WebSocket消息时发生错误: {e}")
                await connection_manager.send_message(connection_id, {
                    "type": "error", 
                    "data": {"message": "服务器内部错误"}
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket客户端断开连接: {connection_id}")
    
    except Exception as e:
        logger.error(f"WebSocket连接异常: {connection_id}, 错误: {e}")
    
    finally:
        # 清理连接
        connection_manager.disconnect(connection_id)


@router.get("/ws/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计"""
    return {
        "success": True,
        "data": {
            "total_connections": connection_manager.get_connection_count(),
            "active_tasks": len(connection_manager.task_subscriptions),
            "connected_users": len(connection_manager.user_connections)
        }
    }


@router.post("/ws/broadcast")
async def broadcast_message(message: dict):
    """广播消息（仅供测试使用）"""
    try:
        await connection_manager.broadcast_message({
            "type": "system_message",
            "data": message
        })
        return {"success": True, "message": "消息已广播"}
    except Exception as e:
        logger.error(f"广播消息失败: {e}")
        raise HTTPException(status_code=500, detail="广播消息失败")