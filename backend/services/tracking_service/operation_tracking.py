"""
操作追踪服务 - 简化版本，支持缓存和状态管理
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from cachetools import TTLCache
from utils.logger import logger
from utils.db_utils import get_database_manager
from services.service_models import TaskState, BaseNodeLog


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

    def __init__(self):
        self.db_manager = get_database_manager()
        self.cache = TaskCache()

    async def get_task_status(self, task_id: str) -> Optional[TaskState]:
        """获取任务状态（只从内存缓存获取）"""
        # 只查缓存，不查数据库
        cached_state = await self.cache.get(task_id)
        if cached_state:
            return cached_state

        # 缓存未命中，直接返回None
        logger.debug(f"任务 {task_id} 在缓存中未找到")
        return None

    async def update_task_progress(self, task_id: str, progress: int,
                                 step_name: str, current_log: BaseNodeLog = None,
                                 error: str = None, final_status: str = None,
                                 execution_result: list[dict] = None, sql_query: str = None):
        """更新任务进度（更新缓存，异步写数据库）"""
        # 获取或创建任务状态
        state = await self.cache.get(task_id)
        if not state:
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
        logger.debug(f"更新任务 {task_id} 进度: {progress}%, 步骤: {step_name}")

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

        # 更新缓存
        logger.info(f"{task_id} 更新任务进度，更新缓存")
        self.cache.set(task_id, state)
        logger.info(f"{task_id} 更新任务进度，更新缓存结束")

        # 写入数据库
        await self._write_to_db(state)

    def create_task(self, state: TaskState):
        """创建新任务"""

        # 更新缓存
        logger.info(f"{state.task_id} 新建任务，更新缓存")
        self.cache.set(state.task_id, state)
        logger.info(f"{state.task_id} 新建任务，更新缓存结束")

        self._write_session_to_db(state.task_id, state.operator)

    async def _write_to_db(self, state: TaskState):
        """异步写入任务状态到数据库"""
        try:
            logger.debug(f"开始写入任务 {state.task_id} 到数据库，状态: {state.status}")

            # 更新会话状态 - 使用UPSERT方式
            self.db_manager.execute_query("""
                INSERT OR REPLACE INTO nlquery_sessions
                (task_id, user_input, operator, flow_type, status, current_step,
                 progress, created_at, completed_at, sql_query, execution_result,
                 clear_check_details, is_clear, error_message, retry_count, max_retries)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                state.task_id,
                state.user_input,
                state.operator,
                state.flow_type,
                state.status,
                state.current_step,
                state.progress,
                state.created_at.strftime('%Y-%m-%d %H:%M:%S') if state.created_at else datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                state.completed_at.strftime('%Y-%m-%d %H:%M:%S') if state.completed_at else None,
                state.sql_query,
                json.dumps(state.execution_result) if state.execution_result else None,
                json.dumps(state.clear_check_details) if state.clear_check_details else None,
                int(state.is_clear),
                state.error_message,
                state.retry_count,
                state.max_retries
            ))
            logger.debug(f"已更新会话状态，任务ID: {state.task_id}")

            # 写入步骤日志（只写入最新的一条）
            if state.logs:
                logger.debug(f"任务 {state.task_id} 有 {len(state.logs)} 条日志")
                latest_log = state.current_step_log

                if latest_log is None:
                    logger.warning(f"任务 {state.task_id} current_step_log 返回 None，使用最后一条日志")
                    if state.logs:
                        latest_log = state.logs[-1]
                    else:
                        logger.error(f"任务 {state.task_id} 日志列表为空，无法写入步骤日志")
                        return

                logger.debug(f"准备写入步骤日志: step={latest_log.step}, success={latest_log.success}")

                self.db_manager.execute_query("""
                    INSERT INTO nlquery_steps
                    (task_id, step, input_data, prompt, model_output, success, error,
                     start_time, end_time, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    state.task_id,
                    latest_log.step,
                    latest_log.input_data,
                    latest_log.prompt if hasattr(latest_log, 'prompt') else "",
                    latest_log.model_output,
                    int(latest_log.success),
                    latest_log.error,
                    latest_log.start_time.strftime('%Y-%m-%d %H:%M:%S') if latest_log.start_time else None,
                    latest_log.end_time.strftime('%Y-%m-%d %H:%M:%S') if latest_log.end_time else None,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
                logger.debug(f"已写入步骤日志，任务ID: {state.task_id}")
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
            self.db_manager.execute_query("""
                INSERT OR IGNORE INTO nlquery_sessions
                (task_id, user_input, operator, flow_type, status, current_step,
                 progress, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                "",  # user_input 将在后续更新
                operator,
                "fast",  # 默认flow_type
                "running",  # 默认status
                "初始化",  # 默认current_step
                0,  # 默认progress
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        except Exception as e:
            logger.error(f"创建会话记录失败: {e}")


    async def get_query_history(self, page: int = 1, page_size: int = 20,
                                status: str = None, operator: str = "api_user"):
        """获取查询历史记录"""
        try:
            # 构建查询条件
            where_conditions = ["operator = ?"]
            params = [operator]

            if status:
                where_conditions.append("status = ?")
                params.append(status)

            where_clause = " AND ".join(where_conditions)

            # 查询总数
            count_query = f"SELECT COUNT(*) as total FROM nlquery_sessions WHERE {where_clause}"
            count_result = self.db_manager.execute_query(count_query, params, fetch="one", return_dict=False)
            total = count_result[0] if count_result else 0

            # 查询分页数据
            offset = (page - 1) * page_size
            query = f"""
                SELECT
                    task_id as id,
                    user_input as query,
                    status,
                    created_at as createdAt,
                    completed_at as completedAt,
                    error_message as errorMessage,
                    operator
                FROM nlquery_sessions
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([page_size, offset])

            results = self.db_manager.execute_query(query, params, fetch="all")
            
            logger.info(f"操作人：{operator} 返回总条数：{total} 是否获取到分页结果：{results is None}")

            # 处理数据格式
            history_items = []
            for result in results:
                # 计算耗时
                duration = None
                if result.get('createdAt') and result.get('completedAt'):
                    try:
                        start = datetime.fromisoformat(result['createdAt'].replace('Z', '+00:00'))
                        end = datetime.fromisoformat(result['completedAt'].replace('Z', '+00:00'))
                        duration = int((end - start).total_seconds() * 1000)
                    except:
                        pass

                item = {
                    'id': result['id'],
                    'query': result['query'] or '',
                    'status': result['status'],
                    'createdAt': result['createdAt'],
                    'completedAt': result['completedAt'],
                    'duration': duration,
                    'generatedSql': '',
                    'errorMessage': result['errorMessage'],
                    'executionResult': [],
                    'operator': result['operator']
                }
                history_items.append(item)

            # 构建分页信息
            pagination = {
                'page': page,
                'pageSize': page_size,
                'total': total,
                'totalPages': (total + page_size - 1) // page_size
            }

            return {
                'success': True,
                'data': history_items,
                'pagination': pagination
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
        """获取单个任务的详细信息"""
        try:
            # 先查缓存
            cached_state = await self.cache.get(task_id)
            if cached_state:
                return {
                    'success': True,
                    'data': cached_state.model_dump()
                }

            # 从数据库查询
            query = """
                SELECT
                    task_id as id,
                    user_input as query,
                    status,
                    created_at as createdAt,
                    completed_at as completedAt,
                    error_message as errorMessage,
                    operator,
                    sql_query,
                    execution_result,
                    flow_type,
                    current_step,
                    progress,
                    is_clear,
                    retry_count,
                    max_retries
                FROM nlquery_sessions
                WHERE task_id = ?
            """
            results = self.db_manager.execute_query(query, [task_id], fetch="all")

            if not results:
                return {
                    'success': False,
                    'error': f'任务 {task_id} 不存在'
                }

            result = results[0]

            # 计算耗时
            duration = None
            if result.get('createdAt') and result.get('completedAt'):
                try:
                    start = datetime.fromisoformat(result['createdAt'].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(result['completedAt'].replace('Z', '+00:00'))
                    duration = int((end - start).total_seconds() * 1000)
                except:
                    pass

            # 获取步骤详情
            steps_query = """
                SELECT step, input_data, prompt, model_output, success, error,
                       start_time, end_time, created_at
                FROM nlquery_steps
                WHERE task_id = ?
                ORDER BY created_at
            """
            steps = self.db_manager.execute_query(steps_query, [task_id], fetch="all")

            # 从sessions中获取SQL和执行结果
            sql_query = result.get('sql_query')
            execution_result_str = result.get('execution_result')
            execution_result = None
            if execution_result_str:
                try:
                    execution_result = json.loads(execution_result_str) if isinstance(execution_result_str, str) else execution_result_str
                except:
                    execution_result = None

            detail_data = {
                'id': result['id'],
                'query': result['query'] or '',
                'status': result['status'],
                'createdAt': result['createdAt'],
                'completedAt': result['completedAt'],
                'duration': duration,
                'generatedSql': sql_query or '',
                'errorMessage': result['errorMessage'],
                'executionResult': execution_result or [],
                'operator': result['operator'],
                'flowType': result.get('flow_type', 'fast'),
                'currentStep': result.get('current_step', ''),
                'progress': result.get('progress', 0),
                'isClear': bool(result.get('is_clear', 0)),
                'retryCount': result.get('retry_count', 0),
                'maxRetries': result.get('max_retries', 5),
                'steps': steps
            }

            return {
                'success': True,
                'data': detail_data
            }

        except Exception as e:
            logger.error(f"获取任务详情失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# 全局追踪器实例
tracker = OperationTracker()