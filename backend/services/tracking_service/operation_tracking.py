"""
操作追踪服务 - SQLAlchemy Repository版本
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from cachetools import TTLCache
from sqlalchemy.orm import Session
from utils.logger import logger
from repositories import (
    NlQuerySessionRepository, NlQueryStepRepository, UserFeedbackRepository
)
from services.service_models import TaskState, BaseNodeLog
from .tracker_cache import tracker_cache


class TaskCache:
    """任务状态缓存管理 - 使用 cachetools"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 24 * 3600):
        self._cache = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        logger.info(f"任务缓存初始化完成: max_size={max_size}, ttl={ttl_seconds}秒")

    async def get(self, task_id: str) -> Optional[TaskState]:
        """获取缓存中的任务状态"""
        try:
            state = self._cache.get(task_id)
            return state
        except Exception as e:
            logger.error(f"从缓存获取任务状态失败: {e}")
            return None

    def set(self, task_id: str, state: TaskState):
        """设置任务状态到缓存"""
        try:
            self._cache[task_id] = state
        except Exception as e:
            logger.error(f"设置任务状态到缓存失败: {e}")

    async def remove(self, task_id: str):
        """从缓存中删除任务"""
        try:
            self._cache.pop(task_id, None)
        except Exception as e:
            logger.error(f"从缓存删除任务失败: {e}")

    def clear(self):
        """清空缓存"""
        try:
            self._cache.clear()
            logger.info("任务缓存已清空")
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")

    def info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        try:
            return {
                "maxsize": self._cache.maxsize,
                "currsize": len(self._cache),
                "ttl": getattr(self._cache, 'ttl', 'N/A')
            }
        except Exception as e:
            logger.error(f"获取缓存信息失败: {e}")
            return {}


class OperationTracker:
    """简化的操作追踪器"""

    def __init__(self, db: Session):
        """
        初始化操作追踪器

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        # 立即初始化所有repository
        self.session_repo = NlQuerySessionRepository(db)
        self.step_repo = NlQueryStepRepository(db)
        self.feedback_repo = UserFeedbackRepository(db)
        # 使用全局缓存实例
        self.cache = tracker_cache

    async def get_task_status(self, task_id: str) -> Optional[TaskState]:
        """获取任务状态（只从内存缓存获取）"""
        # 只查缓存，不查数据库
        cached_state_dict = self.cache.get_task_state(task_id)
        if cached_state_dict:
            # 将字典转换为TaskState对象
            return TaskState(**cached_state_dict)

        # 缓存未命中，直接返回None
        logger.debug(f"任务 {task_id} 在缓存中未找到")
        return None

    async def update_task_progress(self, task_id: str, progress: int,
                                 step_name: str, current_log: BaseNodeLog = None,
                                 error: str = None, final_status: str = None,
                                 execution_result: list[dict] = None, sql_query: str = None,
                                 write_step_log: bool = True):
        """更新任务进度（更新缓存，异步写数据库）"""
        # 获取或创建任务状态
        cached_state_dict = self.cache.get_task_state(task_id)
        if cached_state_dict:
            state = TaskState(**cached_state_dict)
        else:
            logger.info("未从缓存中获取到任务进度")
            state = TaskState(
                task_id=task_id,
                user_input="",
                status="running",
                current_step=step_name,
                progress=progress,
                created_at=datetime.now()
            )

        # 更新状态
        state.progress = progress
        state.current_step = step_name
        state.current_step_name = step_name
        state.progress = progress
        logger.info(f"更新任务 {task_id} 进度: {progress}%, 步骤: {step_name}")

        if current_log:
            state.logs.append(current_log)
            # 设置当前步骤日志为最新的日志
            state.current_step_log = current_log

        if error:
            state.error_message = error
            state.status = "failed"
            state.completed_at = datetime.now()
        elif final_status:
            state.status = final_status
            if final_status in ("success", "completed"):
                state.completed_at = datetime.now()
                state.progress = 100

        if execution_result:
            state.execution_result = execution_result

        if sql_query:
            state.sql_query = sql_query

        # 更新缓存 - 将TaskState对象转换为字典
        logger.info(f"{task_id} 更新任务进度，更新缓存")
        state_dict = {
            'task_id': state.task_id,
            'user_input': state.user_input,
            'operator': state.operator,
            'flow_type': state.flow_type,
            'status': state.status,
            'current_step': state.current_step,
            'progress': state.progress,
            'created_at': state.created_at,
            'completed_at': state.completed_at,
            'logs': state.logs,
            'error_message': state.error_message,
            'execution_result': state.execution_result,
            'sql_query': state.sql_query,
            'clear_check_details': state.clear_check_details,
            'is_clear': state.is_clear,
            'retry_count': state.retry_count,
            'max_retries': state.max_retries
        }
        self.cache.set_task_state(task_id, state_dict)
        logger.info(f"{task_id} 更新任务进度，更新缓存结束")
        logger.info(state)

        # 写入数据库
        await self._write_to_db(state, write_step_log)

    def create_task(self, state: TaskState):
        """创建新任务"""

        # 更新缓存 - 将TaskState对象转换为字典
        logger.info(f"{state.task_id} 新建任务，更新缓存")
        state_dict = {
            'task_id': state.task_id,
            'user_input': state.user_input,
            'operator': state.operator,
            'flow_type': state.flow_type,
            'status': state.status,
            'current_step': state.current_step,
            'progress': state.progress,
            'created_at': state.created_at,
            'completed_at': state.completed_at,
            'logs': state.logs,
            'error_message': state.error_message,
            'execution_result': state.execution_result,
            'sql_query': state.sql_query,
            'clear_check_details': state.clear_check_details,
            'is_clear': state.is_clear,
            'retry_count': state.retry_count,
            'max_retries': state.max_retries
        }
        self.cache.set_task_state(state.task_id, state_dict)
        logger.info(f"{state.task_id} 新建任务，更新缓存结束")

        self._write_session_to_db(state.task_id, state.operator)

    async def _write_to_db(self, state: TaskState, write_step_log: bool = True):
        """异步写入任务状态到数据库"""
        try:
            logger.debug(f"开始写入任务 {state.task_id} 到数据库，状态: {state.status}")

            # 更新或创建会话状态
            session_data = {
                'task_id': state.task_id,
                'user_input': state.user_input,
                'operator': state.operator,
                'flow_type': state.flow_type,
                'status': state.status,
                'current_step': state.current_step,
                'progress': state.progress,
                'created_at': state.created_at,
                'completed_at': state.completed_at,
                'sql_query': state.sql_query,
                'execution_result': json.dumps(state.execution_result) if state.execution_result else None,
                'clear_check_details': json.dumps(state.clear_check_details) if state.clear_check_details else None,
                'is_clear': int(state.is_clear),
                'error_message': state.error_message,
                'retry_count': state.retry_count,
                'max_retries': state.max_retries
            }

            # 检查会话是否存在
            existing_session = self.session_repo.get_by_task_id(state.task_id)
            if existing_session:
                # 更新现有会话（使用task_id而不是id）
                # 从session_data中移除task_id，避免重复传递
                update_data = {k: v for k, v in session_data.items() if k != 'task_id'}
                self.session_repo.update_by_task_id(state.task_id, **update_data)
            else:
                # 创建新会话
                self.session_repo.create(**session_data)

            logger.debug(f"已更新会话状态，任务ID: {state.task_id}")

            # 写入步骤日志（只写入最新的一条，且根据 write_step_log 参数决定）
            if state.logs and write_step_log:
                logger.debug(f"任务 {state.task_id} 有 {len(state.logs)} 条日志，准备写入步骤日志")
                latest_log = state.current_step_log

                if latest_log is None:
                    logger.warning(f"任务 {state.task_id} current_step_log 返回 None，使用最后一条日志")
                    if state.logs:
                        latest_log = state.logs[-1]
                    else:
                        logger.error(f"任务 {state.task_id} 日志列表为空，无法写入步骤日志")
                        return

                logger.debug(f"准备写入步骤日志: step={latest_log.step}, success={latest_log.success}")

                step_data = {
                    'task_id': state.task_id,
                    'step': latest_log.step,
                    'input_data': latest_log.input_data,
                    'prompt': latest_log.prompt if hasattr(latest_log, 'prompt') else "",
                    'model_output': latest_log.model_output,
                    'success': int(latest_log.success),
                    'error': latest_log.error,
                    'start_time': latest_log.start_time,
                    'end_time': latest_log.end_time,
                    'created_at': datetime.now()
                }

                self.step_repo.create(**step_data)
                logger.debug(f"已写入步骤日志，任务ID: {state.task_id}")
            else:
                if not write_step_log:
                    logger.debug(f"任务 {state.task_id} 根据设置不写入步骤日志")
                else:
                    logger.debug(f"任务 {state.task_id} 没有日志需要写入")

            logger.debug(f"任务 {state.task_id} 状态已写入数据库")

        except Exception as e:
            logger.error(f"写入任务 {state.task_id} 到数据库失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    async def _write_session_to_db(self, task_id: str, operator: str = None):
        """异步写入会话记录到数据库"""
        try:
            session_data = {
                'task_id': task_id,
                'user_input': "",  # user_input 将在后续更新
                'operator': operator,
                'flow_type': "fast",  # 默认flow_type
                'status': "running",  # 默认status
                'current_step': "初始化",  # 默认current_step
                'progress': 0,  # 默认progress
                'created_at': datetime.now()
            }

            self.session_repo.create(**session_data)
        except Exception as e:
            logger.error(f"创建会话记录失败: {e}")

    async def get_query_history(self, page: int = 1, page_size: int = 20,
                                status: str = None, operator: str = "api_user"):
        """获取查询历史记录"""
        try:
            # 使用Repository的分页方法
            result = self.session_repo.get_paginated_by_operator(
                operator=operator,
                page=page,
                page_size=page_size,
                status=status
            )

            # 转换为TaskState对象
            history_items = []
            for session in result['items']:
                try:
                    # 处理执行结果
                    execution_result = None
                    if session.execution_result:
                        try:
                            execution_result = json.loads(session.execution_result) if isinstance(session.execution_result, str) else session.execution_result
                        except:
                            execution_result = []

                    # 创建TaskState对象
                    task_state = TaskState(
                        task_id=session.task_id,
                        user_input=session.user_input or '',
                        operator=session.operator,
                        flow_type=session.flow_type or 'fast',
                        status=session.status,
                        current_step=session.current_step or '',
                        progress=session.progress or 0,
                        created_at=session.created_at,
                        completed_at=session.completed_at,
                        sql_query=session.sql_query or '',
                        execution_result=execution_result,
                        clear_check_details={},
                        is_clear=bool(session.is_clear or 0),
                        error_message=session.error_message,
                        retry_count=session.retry_count or 0,
                        max_retries=session.max_retries or 5,
                        logs=[],
                        current_step_log=None,
                        current_step_name=''
                    )
                    history_items.append(task_state)
                except Exception as e:
                    logger.error(f"转换TaskState对象失败: {e}, session: {session}")
                    # 如果转换失败，创建一个默认的TaskState
                    task_state = TaskState(
                        task_id=session.task_id,
                        user_input=session.user_input or '',
                        operator=session.operator,
                        status='error',
                        error_message=f"数据转换失败: {str(e)}"
                    )
                    history_items.append(task_state)

            return {
                'success': True,
                'data': history_items,
                'pagination': {
                    'page': result['page'],
                    'pageSize': result['page_size'],
                    'total': result['total'],
                    'totalPages': result['total_pages']
                }
            }

        except Exception as e:
            logger.error(f"获取查询历史失败: {e}")
            return {
                'success': False,
                'data': [],
                'pagination': {'page': page, 'pageSize': page_size, 'total': 0, 'totalPages': 0},
                'error': str(e)
            }

    async def get_task_detail(self, task_id: str):
        """获取单个任务的步骤详情"""
        try:
            # 获取步骤日志
            steps = self.step_repo.get_by_task_id(task_id)

            # 转换为BaseNodeLog对象
            log_list = []
            for step in steps:
                try:
                    node_log = BaseNodeLog(
                        step=step.step,
                        input_data=step.input_data or '',
                        prompt=step.prompt or '',
                        model_output=step.model_output or '',
                        success=bool(step.success),
                        error=step.error,
                        start_time=step.start_time,
                        end_time=step.end_time
                    )
                    log_list.append(node_log)
                except Exception as e:
                    logger.error(f"转换步骤日志失败: {e}, step: {step}")

            return {
                'success': True,
                'data': log_list
            }

        except Exception as e:
            logger.error(f"获取任务详情失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# 注意：不再使用全局tracker实例，改为依赖注入模式
# tracker = OperationTracker()  # 已移除，请使用依赖注入