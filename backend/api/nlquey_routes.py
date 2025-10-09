"""
API路由定义
"""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime

from api.endpoint_models import QueryRequest
from services.async_query_service import get_async_query_service
from utils.logger import logger

# 创建路由器
router = APIRouter(prefix="/nlquery")

@router.websocket("/ws/task_process")
async def ws_task_process(websocket: WebSocket):
    """
    WebSocket任务状态推送接口
    客户端发送任务ID，服务端每5秒推送一次任务状态
    如果任务完成（成功或失败），则停止推送
    """
    await websocket.accept()
    current_task_id = None
    running = True

    try:
        while running:
            # 接收客户端消息（任务ID）
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                if data.strip():
                    current_task_id = data.strip()
                    logger.info(f"WebSocket客户端切换到任务: {current_task_id}")
            except asyncio.TimeoutError:
                # 超时继续执行，继续推送当前任务状态
                pass
            except WebSocketDisconnect:
                break

            # 如果有当前任务，推送状态
            if current_task_id:
                async_query_service = get_async_query_service()
                task_result = await async_query_service.get_task_result(current_task_id)

                if task_result:
                    # 处理日志格式转换
                    processed_logs = task_result.get("logs", [])

                    # 构建响应数据（使用统一的状态格式）
                    response = {
                        "code": 0,
                        "data": {
                            "task_id": task_result.get("task_id"),
                            "status": task_result.get("status"),
                            "current_step": task_result.get("current_step"),
                            "progress": task_result.get("progress"),
                            "created_at": task_result.get("created_at"),
                            "started_at": task_result.get("started_at"),
                            "completed_at": task_result.get("completed_at"),
                            "user_input": task_result.get("user_input"),
                            "sql_query": task_result.get("sql_query"),
                            "data": task_result.get("data"),
                            "row_count": task_result.get("row_count", 0),
                            "success": task_result.get("success", False),
                            "error": task_result.get("error_message"),
                            "logs": processed_logs
                        },
                        "error_msg": ""
                    }

                    await websocket.send_json(response)

                    # 检查任务是否完成
                    if task_result["status"] in ["success", "failed"]:
                        logger.info(f"任务 {current_task_id} 已完成，状态: {task_result['status']}")
                        # 任务完成后，清空当前任务，但保持连接等待新任务
                        current_task_id = None
                else:
                    # 任务不存在
                    await websocket.send_json({
                        "code": 404,
                        "data": None,
                        "error_msg": f"任务 {current_task_id} 不存在"
                    })
                    current_task_id = None

            # 等待5秒再推送
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        logger.info("WebSocket客户端断开连接")
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "code": 500,
                "data": None,
                "error_msg": f"服务器错误: {str(e)}"
            })
        except:
            pass

@router.post("/submit")
async def process_natural_language_query(request: QueryRequest):
    """
    异步处理自然语言查询

    接收自然语言输入，返回任务ID，查询在后台异步执行
    """
    try:
        logger.info(f"接收查询请求: {request.query}")

        # 获取异步查询服务
        async_query_service = get_async_query_service()

        # 提交异步任务
        operator = "api_user"  # 实际应用中应该从认证信息中获取
        task_id = await async_query_service.submit_query(
            user_input=request.query,
            operator=operator,
            flow_type=request.flow_type,
            max_retries=request.max_retries
        )

        logger.info(f"异步任务已创建: {task_id}")

        # 返回任务ID
        return {
            "success": True,
            "task_id": task_id,
            "message": "查询任务已提交，正在后台处理"
        }

    except Exception as e:
        error_message = f"查询提交失败: {str(e)}"
        logger.error(error_message, exc_info=True)

        # 返回错误响应
        return {
            "success": False,
            "error": error_message
        }

