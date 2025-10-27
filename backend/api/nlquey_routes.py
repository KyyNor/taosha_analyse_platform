"""
API路由定义
"""
import asyncio
import time
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Query, Depends
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

@router.get("/progress/{task_id}")
async def get_task_progress(
    task_id: str,
    last_update_time: Optional[str] = Query(None, description="上次更新时间戳（ISO格式）"),
    timeout: int = Query(30, ge=1, le=60, description="服务端最大等待时间（秒）"),
    db: Session = Depends(get_db)
):
    """
    长轮询获取任务进度

    - 如果有新更新则立即返回最新状态
    - 否则等待最多timeout秒后返回当前状态
    - 返回complete=True表示任务已完成（成功或失败）

    Args:
        task_id: 任务ID
        last_update_time: 上次更新的时间戳（ISO格式），用于增量查询
        timeout: 服务端阻塞等待的最大时间（秒）

    Returns:
        {
            "code": 0 或错误码,
            "data": {
                "task_id": "...",
                "status": "running|success|failed|cancelled",
                "progress": 0-100,
                "current_step": "当前步骤名称",
                "complete": true|false,
                "update_time": "ISO时间戳",
                "logs": [...],
                ...其他字段
            },
            "error_msg": ""
        }
    """
    try:
        # 检查任务是否存在
        task_state = tracker_cache.get_task_state(task_id)
        if not task_state:
            return {
                "code": 404,
                "data": None,
                "error_msg": f"任务 {task_id} 不存在"
            }

        # 获取初始状态的更新时间
        current_state = task_state.copy()
        current_update_time = current_state.get('update_time', datetime.now().isoformat())

        # 如果没有上次更新时间，或有新更新，则直接返回
        if not last_update_time or current_update_time > last_update_time:
            return {
                "code": 0,
                "data": {
                    **current_state,
                    "update_time": current_update_time,
                    "complete": current_state.get('status') in ['success', 'failed']
                },
                "error_msg": ""
            }

        # 等待更新（最多timeout秒）
        start_time = time.time()
        poll_interval = 0.5  # 每500ms检查一次

        while time.time() - start_time < timeout:
            await asyncio.sleep(poll_interval)

            # 重新检查状态
            task_state = tracker_cache.get_task_state(task_id)
            if task_state:
                new_update_time = task_state.get('update_time', datetime.now().isoformat())
                if new_update_time > last_update_time:
                    return {
                        "code": 0,
                        "data": {
                            **task_state,
                            "update_time": new_update_time,
                            "complete": task_state.get('status') in ['success', 'failed']
                        },
                        "error_msg": ""
                    }

        # 超时时返回当前状态（可能无新更新）
        task_state = tracker_cache.get_task_state(task_id)
        if task_state:
            current_update_time = task_state.get('update_time', datetime.now().isoformat())
            return {
                "code": 0,
                "data": {
                    **task_state,
                    "update_time": current_update_time,
                    "complete": task_state.get('status') in ['success', 'failed']
                },
                "error_msg": ""
            }
        else:
            return {
                "code": 404,
                "data": None,
                "error_msg": f"任务 {task_id} 不存在"
            }

    except Exception as e:
        logger.error(f"获取任务进度失败: {e}", exc_info=True)
        return {
            "code": 500,
            "data": None,
            "error_msg": f"服务器错误: {str(e)}"
        }

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
        
        # 恢复工作流执行
        await async_query_service.resume_workflow(task_id, add_input.clarification_input, tracker)
        
        logger.info(f"工作流已恢复: task_id={task_id}")

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

