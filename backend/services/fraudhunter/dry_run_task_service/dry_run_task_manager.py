"""
异步任务管理器（Dry Run专用）
"""

import uuid
import asyncio
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from sqlalchemy.orm import Session
from models.fraudhunter.dry_run_task import FraudHunterDryRunExecution
from models.db_base import get_db_session
from utils.logger import logger


class DryRunTaskManager:
    """异步任务管理器"""

    def __init__(self):
        self.running_tasks: Dict[str, asyncio.Task] = {}

    async def submit_task(
        self,
        db: Session,
        task_type: str,
        task_id: int,
        task_func: Callable,
        created_by: str,
        task_name: Optional[str] = None,
        parent_execution_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """提交异步任务

        Args:
            db: 数据库会话
            task_type: 任务类型（indicator/model_backtest等）
            task_id: 任务关联ID
            task_func: 任务执行函数
            created_by: 创建人
            task_name: 任务名称（用于模型回测等场景生成可读性更好的execution_id）
            parent_execution_id: 父任务执行ID（用于批量任务关联子任务）
            **kwargs: 传递给任务函数的参数

        Returns:
            execution_id: 任务执行ID
        """
        # 生成任务ID
        if task_type == 'model_backtest' and task_name:
            # 模型回测使用 task_{模型名称}_{时间戳} 格式
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            execution_id = f"task_{task_name}_{timestamp}"
        elif task_type == 'model_batch_backtest':
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            execution_id = f"task_批量模型回测_{timestamp}_{uuid.uuid4().hex[:8]}"
        else:
            # 其他类型使用 UUID 格式
            execution_id = f"task_{uuid.uuid4()}"

        # 创建任务记录
        task_execution = FraudHunterDryRunExecution(
            task_type=task_type,
            task_id=task_id,
            execution_id=execution_id,
            parent_execution_id=parent_execution_id,
            status='pending',
            created_by=created_by
        )

        db.add(task_execution)
        db.commit()

        # 创建异步任务，将 task_id 也传递给任务函数
        task = asyncio.create_task(
            self._run_task(execution_id, task_func, task_id, **kwargs)
        )
        self.running_tasks[execution_id] = task

        logger.info(f"任务已提交: {execution_id}, 类型: {task_type}")
        return execution_id

    async def _run_task(self, execution_id: str, task_func: Callable, task_id: int, **kwargs) -> None:
        """执行任务

        Args:
            execution_id: 任务执行ID
            task_func: 任务执行函数
            task_id: 任务关联ID
            **kwargs: 传递给任务函数的参数
        """
        with get_db_session() as db:
            try:
                # 更新任务状态为运行中
                task_execution = db.query(FraudHunterDryRunExecution).filter(
                    FraudHunterDryRunExecution.execution_id == execution_id
                ).first()

                if not task_execution:
                    logger.error(f"任务记录不存在: {execution_id}")
                    return

                task_execution.status = 'running'
                task_execution.start_time = datetime.now()
                db.commit()

                logger.info(f"开始执行任务: {execution_id}")

                # 执行任务，传递 task_id 作为参数
                result = await task_func(db, execution_id, task_id, **kwargs)

                # ═══════════════════ 精确定位 MySQL JSON 错误根源 ══════════════════════
                # MySQL JSON 解析器比 Python json 更严格，以下情况会报错：
                #   1. Lone Surrogate: U+D800~UDFFF 的孤立半个代理码点
                #   2. 非法控制字符: 除 \t\n\r 外的 < 0x20 字符
                import json as _json

                SURROGATE_START, SURROGATE_END = 0xD800, 0xDFFF
                LEGAL_CTRL = frozenset({0x09, 0x0A, 0x0D})

                def _scan_lone_surrogate(obj, path=""):
                    """遍历所有字符串叶节点，找第一个 lone surrogate"""
                    if isinstance(obj, str):
                        for i, ch in enumerate(obj):
                            cp = ord(ch)
                            if SURROGATE_START <= cp <= SURROGATE_END:
                                ctx = repr(obj[max(0,i-10):i+12])
                                return (path, hex(cp), ctx)
                    elif isinstance(obj, dict):
                        for k, v in obj.items():
                            found = _scan_lone_surrogate(v, f"{path}.{k}")
                            if found:
                                return found
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            found = _scan_lone_surrogate(item, f"{path}[{i}]")
                            if found:
                                return found
                    return None

                # 先扫 lone surrogate（最常见的问题来源）
                sfx = _scan_lone_surrogate(result)
                if sfx:
                    p, c, ctx = sfx
                    logger.error(f"[DIAG] ❌ LONE SURROGATE → path={p} codepoint={c} ctx={ctx}")
                else:
                    logger.info("[DIAG] ✅ 未发现 lone surrogate")

                # 再扫非法控制字符
                def _scan_bad_ctrl(obj, path=""):
                    violations = []
                    if isinstance(obj, str):
                        for i, ch in enumerate(obj):
                            cp = ord(ch)
                            if cp < 0x20 and cp not in LEGAL_CTRL:
                                ctx = repr(obj[max(0,i-5):i+8])
                                violations.append(f"path={path}[{i}] cp={hex(cp)} ctx={ctx}")
                    elif isinstance(obj, dict):
                        for k, v in obj.items():
                            violations.extend(_scan_bad_ctrl(v, f"{path}.{k}"))
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            violations.extend(_scan_bad_ctrl(item, f"{path}[{i}]"))
                    return violations

                bad_ctrls = _scan_bad_ctrl(result)
                if bad_ctrls:
                    logger.error(f"[DIAG] ❌ ILLEGAL CTRL 共 {len(bad_ctrls)} 处，前5: {bad_ctrls[:5]}")
                else:
                    logger.info("[DIAG] ✅ 无非法控制字符")

                # 针对已知出错位置 177953 做定向检查
                TARGET_POS = 177953
                try:
                    encoded = _json.dumps(result, ensure_ascii=False)
                    total_len = len(encoded)
                    logger.info(f"[DIAG] ✅ json.dumps 正常，总长度={total_len}")

                    # 显示错误位置附近的原始字节
                    chunk_start = max(0, TARGET_POS - 50)
                    chunk_end = min(total_len, TARGET_POS + 100)
                    logger.warning(f"[DIAG] 📍 Position {TARGET_POS} 附近内容:")
                    logger.warning(f"       >>> {repr(encoded[chunk_start:chunk_end])} <<<")
                except Exception as je:
                    raw_str = str(result)
                    logger.error(f"[DIAG] ❌ json.dumps 本身失败: {je}")
                    if len(raw_str) > TARGET_POS:
                        logger.warning(f"[DIAG] 📍 出错位置 {TARGET_POS} 周围原始内容:")
                        logger.warning(f"       >>> {repr(raw_str[TARGET_POS-50:TARGET_POS+100])} <<<")

                # 更新任务状态为成功
                task_execution.status = 'success'
                task_execution.end_time = datetime.now()
                task_execution.result_summary = result
                logger.info(result)
                db.commit()

                logger.info(f"任务执行成功: {execution_id}")

            except Exception as e:
                # 更新任务状态为失败
                task_execution = db.query(FraudHunterDryRunExecution).filter(
                    FraudHunterDryRunExecution.execution_id == execution_id
                ).first()

                if task_execution:
                    task_execution.status = 'failed'
                    task_execution.end_time = datetime.now()
                    task_execution.result_summary = {
                        'error': str(e),
                        'error_type': type(e).__name__
                    }
                    db.commit()

                logger.error(f"任务执行失败: {execution_id}, 错误: {str(e)}", exc_info=True)

            finally:
                # 清理任务记录
                if execution_id in self.running_tasks:
                    del self.running_tasks[execution_id]

    def get_task_progress(self, db: Session, task_id: int) -> Dict[str, Any]:
        """获取任务进度

        Args:
            db: 数据库会话
            task_id: 任务主键ID

        Returns:
            任务进度信息

        Raises:
            ValueError: 如果任务不存在
        """
        task_execution = db.query(FraudHunterDryRunExecution).filter(
            FraudHunterDryRunExecution.id == task_id
        ).first()

        if not task_execution:
            raise ValueError(f"任务不存在: {task_id}")

        # 计算进度（简化版本，实际应该根据任务类型和状态计算）
        progress = 0.0
        if task_execution.status == 'pending':
            progress = 0.0
        elif task_execution.status == 'running':
            progress = 50.0  # 模拟进度
        elif task_execution.status in ['success', 'failed', 'cancelled']:
            progress = 100.0

        # 估算剩余时间（简化版本）
        estimated_remaining_seconds = None
        if task_execution.status == 'running' and task_execution.start_time:
            elapsed = (datetime.now() - task_execution.start_time).total_seconds()
            if progress > 0 and progress < 100:
                estimated_remaining_seconds = int(elapsed * (100 - progress) / progress)

        return {
            'task_id': task_execution.execution_id,
            'task_type': task_execution.task_type,
            'parent_execution_id': task_execution.parent_execution_id,
            'status': task_execution.status,
            'progress': progress,
            'current_step': self._get_current_step(task_execution.status),
            'start_time': task_execution.start_time,
            'end_time': task_execution.end_time,
            'estimated_remaining_seconds': estimated_remaining_seconds
        }

    def get_task_result(self, db: Session, task_id: int) -> Dict[str, Any]:
        """获取任务结果

        Args:
            db: 数据库会话
            task_id: 任务主键ID

        Returns:
            任务结果信息

        Raises:
            ValueError: 如果任务不存在或未完成
        """
        task_execution = db.query(FraudHunterDryRunExecution).filter(
            FraudHunterDryRunExecution.id == task_id
        ).first()

        if not task_execution:
            raise ValueError(f"任务不存在: {task_id}")

        if task_execution.status not in ['success', 'failed']:
            raise ValueError(f"任务尚未完成: {task_id}")

        # 计算执行时长
        duration_seconds = None
        if task_execution.start_time and task_execution.end_time:
            duration_seconds = int((task_execution.end_time - task_execution.start_time).total_seconds())

        return {
            'task_id': task_execution.execution_id,
            'status': task_execution.status,
            'duration_seconds': duration_seconds,
            'result': task_execution.result_summary
        }

    async def cancel_task(self, db: Session, task_id: int) -> bool:
        """取消任务

        Args:
            db: 数据库会话
            task_id: 任务主键ID

        Returns:
            是否成功取消

        Raises:
            ValueError: 如果任务不存在
        """
        task_execution = db.query(FraudHunterDryRunExecution).filter(
            FraudHunterDryRunExecution.id == task_id
        ).first()

        if not task_execution:
            raise ValueError(f"任务不存在: {task_id}")

        # 获取execution_id用于查找运行中的任务
        execution_id = task_execution.execution_id

        # 尝试取消异步任务
        if execution_id in self.running_tasks:
            task = self.running_tasks[execution_id]
            task.cancel()

            # 更新任务状态
            task_execution.status = 'cancelled'
            task_execution.end_time = datetime.now()
            db.commit()

            logger.info(f"任务已取消: {execution_id}")
            return True

        # 如果任务还在pending状态，直接标记为cancelled
        if task_execution.status == 'pending':
            task_execution.status = 'cancelled'
            task_execution.end_time = datetime.now()
            db.commit()
            logger.info(f"任务已取消: {execution_id}")
            return True

        return False

    def list_task_executions(
        self,
        db: Session,
        task_type: Optional[str] = None,
        task_id: Optional[int] = None,
        status: Optional[str] = None,
        parent_execution_id: Optional[str] = None,
        result_summary: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list, int]:
        """查询任务执行历史

        Args:
            db: 数据库会话
            task_type: 任务类型筛选
            task_id: 任务ID筛选
            status: 任务状态筛选
            parent_execution_id: 父任务执行ID筛选
            result_summary: 结果摘要模糊搜索
            page: 页码
            page_size: 每页数量

        Returns:
            (任务列表, 总数)
        """
        from sqlalchemy import cast, Text

        query = db.query(FraudHunterDryRunExecution)

        if task_type:
            query = query.filter(FraudHunterDryRunExecution.task_type == task_type)

        if task_id:
            query = query.filter(FraudHunterDryRunExecution.task_id == task_id)

        if status:
            query = query.filter(FraudHunterDryRunExecution.status == status)

        if parent_execution_id:
            query = query.filter(FraudHunterDryRunExecution.parent_execution_id == parent_execution_id)

        if result_summary:
            # 将JSON字段转换为文本后进行LIKE搜索
            query = query.filter(
                cast(FraudHunterDryRunExecution.result_summary, Text).like(f'%{result_summary}%')
            )

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(FraudHunterDryRunExecution.created_at.desc()).offset(offset).limit(page_size).all()

        return items, total

    def _get_current_step(self, status: str) -> str:
        """根据状态获取当前步骤描述

        Args:
            status: 任务状态

        Returns:
            步骤描述
        """
        step_map = {
            'pending': '等待执行',
            'running': '正在执行',
            'success': '执行成功',
            'failed': '执行失败',
            'cancelled': '已取消'
        }
        return step_map.get(status, '未知状态')


# 全局任务管理器实例
dry_run_task_manager = DryRunTaskManager()
