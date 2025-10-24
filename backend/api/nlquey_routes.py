"""
API路由定义
"""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session

from fastapi.encoders import jsonable_encoder

from api.endpoint_models import QueryRequest, ClarificationInput
from models.db_base import get_db
from services.service_models import TaskState, BaseNodeLog
from services.nlquery_service.async_query_service import get_async_query_service
from services.tracking_service.operation_tracking import OperationTracker
from services.tracking_service.tracker_cache import tracker_cache
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
    retry_cnt = 0
    running = True

    try:
        while running:
            # 接收客户端消息（任务ID）
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                if data.strip():
                    current_task_id = data.strip()
                    current_task_id = current_task_id.replace('"', '')
                    logger.info(f"WebSocket客户端切换到任务: {current_task_id}")
            except asyncio.TimeoutError:
                # 超时继续执行，继续推送当前任务状态
                pass
            except WebSocketDisconnect:
                break

            # 如果有当前任务，推送状态
            if current_task_id:
                # WebSocket直接从全局缓存读取状态，不需要数据库会话
                cached_state = tracker_cache.get_task_state(current_task_id)

                if cached_state:
                    # 将字典转换为TaskState对象
                    task_result = TaskState(**cached_state)

                    if task_result:
                        # 构建响应数据（使用统一的状态格式）
                        response = {
                            "code": 0,
                            "data": task_result,
                            "error_msg": ""
                        }

                        await websocket.send_json(jsonable_encoder(response))

                        # 检查任务是否完成
                        if task_result.status in ["success", "failed"]:
                            logger.info(f"任务 {current_task_id} 已完成，状态: {task_result.status}")
                            # 任务完成后，清空当前任务，但保持连接等待新任务
                            current_task_id = None
                else:
                    # 任务不存在
                    await websocket.send_json({
                        "code": 404,
                        "data": None,
                        "error_msg": f"第{retry_cnt + 1}次尝试：任务 {current_task_id} 不存在"
                    })
                    if retry_cnt < 10:
                        retry_cnt = retry_cnt + 1
                    else:
                        current_task_id = None
                        retry_cnt = 0

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
        except Exception as send_error:
            logger.error(f"发送错误消息失败: {send_error}")
            pass

@router.post("/submit")
async def process_natural_language_query(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    异步处理自然语言查询

    接收自然语言输入，返回任务ID，查询在后台异步执行
    """
    try:
        logger.info(f"接收查询请求: {request.query}，执行流程：{request.flow_type}")

        # 创建带数据库会话的OperationTracker实例
        tracker = OperationTracker(db)

        # 获取异步查询服务
        async_query_service = get_async_query_service()

        # 提交异步任务
        operator = "api_user"  # 实际应用中应该从认证信息中获取
        task_id = await async_query_service.submit_query(
            user_input=request.query,
            operator=operator,
            flow_type=request.flow_type,
            max_retries=request.max_retries,
            tracker=tracker,  # 传递tracker实例
            selected_theme_id=request.selected_theme_id,  # 传递选中的主题ID
            selected_table_ids=request.selected_table_ids  # 传递选中的表ID列表
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


@router.get("/history")
async def get_query_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    status: str = Query(None, description="状态过滤"),
    db: Session = Depends(get_db)
):
    """
    获取查询历史记录
    返回TaskState对象列表
    """
    try:
        logger.info(f"获取查询历史请求: page={page}, page_size={page_size}, status={status}")

        # 创建新的tracker实例，传入db
        request_tracker = OperationTracker(db)

        # 调用追踪服务获取历史记录
        result = await request_tracker.get_query_history(
            page=page,
            page_size=page_size,
            status=status,
            operator="api_user"  # 暂时写死
        )

        return result

    except Exception as e:
        error_message = f"获取查询历史失败: {str(e)}"
        logger.error(error_message, exc_info=True)
        return {
            "success": False,
            "data": [],
            "pagination": {'page': page, 'pageSize': page_size, 'total': 0, 'totalPages': 0},
            "error": error_message
        }


@router.get("/history/{task_id}")
async def get_query_detail(task_id: str, db: Session = Depends(get_db)):
    """
    获取查询详情
    返回List[BaseNodeLog]对象列表
    """
    try:
        logger.info(f"获取查询详情请求: task_id={task_id}")

        # 创建新的tracker实例，传入db
        request_tracker = OperationTracker(db)

        # 调用追踪服务获取详情
        result = await request_tracker.get_task_detail(task_id)

        return result

    except Exception as e:
        error_message = f"获取查询详情失败: {str(e)}"
        logger.error(error_message, exc_info=True)
        return {
            "success": False,
            "data": None,
            "error": error_message
        }


@router.post("/clarification/{task_id}")
async def submit_clarification(
    task_id: str,
    add_input: ClarificationInput,
    db: Session = Depends(get_db)
):
    """提交用户澄清输入 - 异步处理"""
    try:
        logger.info(f"接收澄清输入: task_id={task_id}, clarification={add_input.clarification_input[:50]}...")
                       
        # 获取异步查询服务
        from services.nlquery_service.async_query_service import get_async_query_service
        async_query_service = get_async_query_service()
        tracker = OperationTracker(db)
        
        # 创建后台异步任务恢复工作流执行
        task = asyncio.create_task(
            async_query_service.resume_workflow(task_id, add_input.clarification_input, tracker)
        )
        
        # 添加到后台任务集合
        _background_tasks = getattr(async_query_service, '_background_tasks', set())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        
        logger.info(f"澄清任务已提交到后台执行: task_id={task_id}")
        
        # 立即返回响应
        return {
            "success": True,
            "message": "澄清已接收，正在后台继续处理...",
            "task_id": task_id
        }
        
    except Exception as e:
        error_message = f"提交澄清失败: {str(e)}"
        logger.error(error_message, exc_info=True)
        return {
            "success": False,
            "error": error_message
        }

