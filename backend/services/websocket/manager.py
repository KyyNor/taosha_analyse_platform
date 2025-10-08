"""
WebSocket管理器 - 处理实时通信
"""
import json
import asyncio
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃连接: {connection_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # 存储任务订阅: {task_id: set(connection_ids)}
        self.task_subscriptions: Dict[str, Set[str]] = {}
        # 存储用户连接: {user_id: set(connection_ids)}
        self.user_connections: Dict[int, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: Optional[int] = None):
        """接受WebSocket连接"""
        try:
            await websocket.accept()
            self.active_connections[connection_id] = websocket
            
            # 关联用户连接
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(connection_id)
            
            logger.info(f"WebSocket连接已建立: {connection_id}, 用户: {user_id}")
            
            # 发送连接确认消息
            await self.send_message(connection_id, {
                "type": "connection_established",
                "data": {
                    "connection_id": connection_id,
                    "timestamp": datetime.now().isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {connection_id}, 错误: {e}")
            raise
    
    def disconnect(self, connection_id: str):
        """断开WebSocket连接"""
        try:
            # 移除连接
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
            
            # 移除任务订阅
            for task_id, connections in self.task_subscriptions.items():
                connections.discard(connection_id)
            
            # 移除用户连接关联
            for user_id, connections in self.user_connections.items():
                connections.discard(connection_id)
            
            logger.info(f"WebSocket连接已断开: {connection_id}")
            
        except Exception as e:
            logger.error(f"断开WebSocket连接失败: {connection_id}, 错误: {e}")
    
    async def send_message(self, connection_id: str, message: Dict[str, Any]):
        """向指定连接发送消息"""
        if connection_id not in self.active_connections:
            logger.warning(f"连接不存在: {connection_id}")
            return False
        
        try:
            websocket = self.active_connections[connection_id]
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {connection_id}, 错误: {e}")
            # 连接可能已断开，清理连接
            self.disconnect(connection_id)
            return False
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """向所有连接广播消息"""
        if not self.active_connections:
            return
        
        # 并发发送消息
        tasks = []
        for connection_id in list(self.active_connections.keys()):
            tasks.append(self.send_message(connection_id, message))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def send_to_user(self, user_id: int, message: Dict[str, Any]):
        """向指定用户的所有连接发送消息"""
        if user_id not in self.user_connections:
            return
        
        tasks = []
        for connection_id in list(self.user_connections[user_id]):
            tasks.append(self.send_message(connection_id, message))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def subscribe_task(self, connection_id: str, task_id: str):
        """订阅任务更新"""
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        
        self.task_subscriptions[task_id].add(connection_id)
        logger.info(f"连接 {connection_id} 订阅任务 {task_id}")
    
    def unsubscribe_task(self, connection_id: str, task_id: str):
        """取消订阅任务更新"""
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(connection_id)
            logger.info(f"连接 {connection_id} 取消订阅任务 {task_id}")
    
    async def notify_task_update(self, task_id: str, update_data: Dict[str, Any]):
        """通知任务更新"""
        if task_id not in self.task_subscriptions:
            return
        
        message = {
            "type": "task_update",
            "task_id": task_id,
            "data": update_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # 向订阅该任务的所有连接发送更新
        tasks = []
        for connection_id in list(self.task_subscriptions[task_id]):
            tasks.append(self.send_message(connection_id, message))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def notify_query_progress(self, task_id: str, progress_data: Dict[str, Any]):
        """通知查询进度更新"""
        await self.notify_task_update(task_id, {
            "type": "progress_update",
            **progress_data
        })
    
    async def notify_query_completed(self, task_id: str, result_data: Dict[str, Any]):
        """通知查询完成"""
        await self.notify_task_update(task_id, {
            "type": "query_completed",
            **result_data
        })
    
    async def notify_query_error(self, task_id: str, error_data: Dict[str, Any]):
        """通知查询错误"""
        await self.notify_task_update(task_id, {
            "type": "query_error",
            **error_data
        })
    
    def get_connection_count(self) -> int:
        """获取活跃连接数量"""
        return len(self.active_connections)
    
    def get_task_subscription_count(self, task_id: str) -> int:
        """获取任务订阅数量"""
        return len(self.task_subscriptions.get(task_id, set()))


# 全局连接管理器实例
connection_manager = ConnectionManager()


class WebSocketHandler:
    """WebSocket消息处理器"""
    
    def __init__(self, manager: ConnectionManager):
        self.manager = manager
    
    async def handle_message(self, connection_id: str, message_data: Dict[str, Any]):
        """处理客户端消息"""
        try:
            message_type = message_data.get("type")
            data = message_data.get("data", {})
            
            if message_type == "subscribe_task":
                task_id = data.get("task_id")
                if task_id:
                    self.manager.subscribe_task(connection_id, task_id)
                    await self.manager.send_message(connection_id, {
                        "type": "subscription_confirmed",
                        "data": {"task_id": task_id}
                    })
            
            elif message_type == "unsubscribe_task":
                task_id = data.get("task_id")
                if task_id:
                    self.manager.unsubscribe_task(connection_id, task_id)
                    await self.manager.send_message(connection_id, {
                        "type": "unsubscription_confirmed",
                        "data": {"task_id": task_id}
                    })
            
            elif message_type == "ping":
                await self.manager.send_message(connection_id, {
                    "type": "pong",
                    "data": {"timestamp": datetime.now().isoformat()}
                })
            
            else:
                logger.warning(f"未知消息类型: {message_type}")
                await self.manager.send_message(connection_id, {
                    "type": "error",
                    "data": {"message": f"未知消息类型: {message_type}"}
                })
        
        except Exception as e:
            logger.error(f"处理WebSocket消息失败: {connection_id}, 错误: {e}")
            await self.manager.send_message(connection_id, {
                "type": "error",
                "data": {"message": "消息处理失败"}
            })


# 全局消息处理器实例
websocket_handler = WebSocketHandler(connection_manager)