"""
DeepAgents 任务执行服务

提供基于数据库队列的任务管理和执行功能：
- 支持多 worker 环境（使用数据库锁保证并发安全）
- 子进程执行任务（便于超时强杀）
- 20分钟超时控制
- 状态追踪和结果保存
"""

import os
import time
import signal
import multiprocessing
from datetime import datetime
from threading import Thread, Lock, Event
from typing import Optional, Dict, Any

from utils.logger import logger


# 任务超时时间（秒）
TASK_TIMEOUT_SECONDS = 20 * 60  # 20分钟

# 轮询间隔（秒）
POLL_INTERVAL_SECONDS = 5


def _run_analysis_task(session_id: str, question: str, result_queue: multiprocessing.Queue):
    """在子进程中执行分析任务

    Args:
        session_id: 会话ID
        question: 分析问题
        result_queue: 结果队列
    """
    try:
        # 在子进程中导入，避免主进程的依赖问题
        from services.agents.deepagents.data_analyser_agent import DataAnalyserAgent

        # 创建并运行分析
        analyser = DataAnalyserAgent(session_id=session_id)
        analyser.create_agent()
        result = analyser.run_analysis(question)

        # 如果成功，运行评分
        if result.get("success"):
            try:
                from services.agents.deepagents.scorer_agent import ScorerAgent
                scorer = ScorerAgent()
                score_result = scorer.evaluate_and_save(session_id)
                result["score_result"] = score_result
            except Exception as e:
                logger.warning(f"评分失败: {e}")
                result["score_error"] = str(e)

        result_queue.put(result)

    except Exception as e:
        logger.error(f"分析任务执行失败: {e}", exc_info=True)
        result_queue.put({
            "success": False,
            "session_id": session_id,
            "error": str(e)
        })


class DeepAgentsTaskExecutor:
    """DeepAgents 任务执行器

    基于数据库队列的任务执行器，支持多 worker 环境。
    每个 worker 进程创建一个实例，独立轮询数据库领取任务。
    """

    def __init__(self):
        self._running = False
        self._worker_thread: Optional[Thread] = None
        self._current_process: Optional[multiprocessing.Process] = None
        self._current_session_id: Optional[str] = None
        self._stop_event = Event()
        self._lock = Lock()

        logger.info("DeepAgentsTaskExecutor 初始化完成")

    def start(self):
        """启动任务执行器"""
        if self._running:
            logger.warning("任务执行器已在运行中")
            return

        self._running = True
        self._stop_event.clear()
        self._worker_thread = Thread(target=self._poll_and_execute, daemon=True)
        self._worker_thread.start()
        logger.info("DeepAgents 任务执行器已启动")

    def stop(self):
        """停止任务执行器"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        # 终止当前运行的任务
        with self._lock:
            if self._current_process and self._current_process.is_alive():
                logger.warning(f"正在终止当前任务: {self._current_session_id}")
                self._current_process.terminate()
                self._current_process.join(timeout=5)
                if self._current_process.is_alive():
                    self._current_process.kill()

                # 更新任务状态为失败
                if self._current_session_id:
                    self._update_session_status(
                        self._current_session_id,
                        "failed",
                        llm_output="任务被强制终止（服务停止）"
                    )

        if self._worker_thread:
            self._worker_thread.join(timeout=10)

        logger.info("DeepAgents 任务执行器已停止")

    def _poll_and_execute(self):
        """轮询数据库并执行任务"""
        logger.info("开始轮询任务队列...")

        while self._running and not self._stop_event.is_set():
            try:
                # 尝试领取并执行任务
                self._claim_and_execute_task()
            except Exception as e:
                logger.error(f"任务轮询异常: {e}", exc_info=True)

            # 等待下一次轮询
            self._stop_event.wait(timeout=POLL_INTERVAL_SECONDS)

    def _claim_and_execute_task(self):
        """尝试从数据库领取并执行一个任务"""
        from models.db_base import get_db_session
        from models.deepagents.analysis_tracking_models import AnalysisSession
        from sqlalchemy import asc

        session_data = None

        try:
            with get_db_session() as db:
                # 使用 FOR UPDATE SKIP LOCKED 确保并发安全
                # 这样多个 worker 可以同时查询，但只有一个能领取到任务
                session = db.query(AnalysisSession).filter(
                    AnalysisSession.status == "pending"
                ).order_by(
                    asc(AnalysisSession.created_at)
                ).with_for_update(skip_locked=True).first()

                if not session:
                    return  # 无待处理任务

                # 标记为执行中
                session.status = "running"
                session.start_time = datetime.now()
                db.commit()

                # 保存任务信息
                session_data = {
                    "session_id": session.session_id,
                    "question": session.question
                }

                logger.info(f"领取到任务: {session.session_id}")

        except Exception as e:
            logger.error(f"领取任务失败: {e}", exc_info=True)
            return

        if session_data:
            # 在子进程中执行任务
            self._execute_task(session_data["session_id"], session_data["question"])

    def _execute_task(self, session_id: str, question: str):
        """执行单个任务

        Args:
            session_id: 会话ID
            question: 分析问题
        """
        with self._lock:
            self._current_session_id = session_id

        result_queue = multiprocessing.Queue()

        try:
            # 创建子进程执行任务
            self._current_process = multiprocessing.Process(
                target=_run_analysis_task,
                args=(session_id, question, result_queue)
            )
            self._current_process.start()

            # 等待任务完成或超时
            self._current_process.join(timeout=TASK_TIMEOUT_SECONDS)

            if self._current_process.is_alive():
                # 超时，强制终止
                logger.warning(f"任务超时，强制终止: {session_id}")
                self._current_process.terminate()
                self._current_process.join(timeout=5)
                if self._current_process.is_alive():
                    self._current_process.kill()
                    self._current_process.join(timeout=2)

                self._update_session_status(
                    session_id,
                    "failed",
                    llm_output="任务执行超时（超过20分钟），已强制终止"
                )
            else:
                # 正常完成，获取结果
                if not result_queue.empty():
                    result = result_queue.get_nowait()
                    self._save_task_result(session_id, result)
                else:
                    # 进程结束但没有结果（可能是异常退出）
                    exit_code = self._current_process.exitcode
                    self._update_session_status(
                        session_id,
                        "failed",
                        llm_output=f"任务异常退出，退出码: {exit_code}"
                    )

        except Exception as e:
            logger.error(f"执行任务失败: {e}", exc_info=True)
            self._update_session_status(
                session_id,
                "failed",
                llm_output=f"任务执行异常: {str(e)}"
            )

        finally:
            with self._lock:
                self._current_process = None
                self._current_session_id = None

    def _save_task_result(self, session_id: str, result: Dict[str, Any]):
        """保存任务结果到数据库

        Args:
            session_id: 会话ID
            result: 任务结果
        """
        try:
            from models.db_base import get_db_session
            from models.deepagents.analysis_tracking_models import AnalysisSession

            with get_db_session() as db:
                session = db.query(AnalysisSession).filter(
                    AnalysisSession.session_id == session_id
                ).first()

                if not session:
                    logger.error(f"会话不存在: {session_id}")
                    return

                # 更新状态
                session.status = "completed" if result.get("success") else "failed"
                session.end_time = datetime.now()

                if session.start_time:
                    session.duration_seconds = (session.end_time - session.start_time).total_seconds()

                # 保存结果
                if result.get("report_path"):
                    session.report_path = result.get("report_path")
                if result.get("report_content"):
                    session.report_content = result.get("report_content")
                if result.get("llm_output"):
                    session.llm_output = result.get("llm_output")
                elif result.get("error"):
                    session.llm_output = f"错误: {result.get('error')}"

                db.commit()
                logger.info(f"任务结果已保存: {session_id}, 状态: {session.status}")

        except Exception as e:
            logger.error(f"保存任务结果失败: {e}", exc_info=True)

    def _update_session_status(
        self,
        session_id: str,
        status: str,
        llm_output: Optional[str] = None
    ):
        """更新会话状态

        Args:
            session_id: 会话ID
            status: 新状态
            llm_output: LLM输出内容
        """
        try:
            from models.db_base import get_db_session
            from models.deepagents.analysis_tracking_models import AnalysisSession

            with get_db_session() as db:
                session = db.query(AnalysisSession).filter(
                    AnalysisSession.session_id == session_id
                ).first()

                if session:
                    session.status = status
                    session.end_time = datetime.now()
                    if session.start_time:
                        session.duration_seconds = (session.end_time - session.start_time).total_seconds()
                    if llm_output:
                        session.llm_output = llm_output
                    db.commit()
                    logger.info(f"会话状态已更新: {session_id} -> {status}")

        except Exception as e:
            logger.error(f"更新会话状态失败: {e}", exc_info=True)

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态

        Returns:
            队列状态信息
        """
        try:
            from models.db_base import get_db_session
            from models.deepagents.analysis_tracking_models import AnalysisSession

            with get_db_session() as db:
                pending_count = db.query(AnalysisSession).filter(
                    AnalysisSession.status == "pending"
                ).count()

                running_count = db.query(AnalysisSession).filter(
                    AnalysisSession.status == "running"
                ).count()

                return {
                    "is_running": self._running,
                    "queue_size": pending_count,
                    "running_count": running_count,
                    "current_task": {
                        "session_id": self._current_session_id
                    } if self._current_session_id else None
                }

        except Exception as e:
            logger.error(f"获取队列状态失败: {e}")
            return {
                "is_running": self._running,
                "queue_size": 0,
                "running_count": 0,
                "current_task": None,
                "error": str(e)
            }


# 全局实例（每个 worker 进程一个）
_task_executor: Optional[DeepAgentsTaskExecutor] = None
_executor_lock = Lock()


def get_task_executor() -> DeepAgentsTaskExecutor:
    """获取任务执行器实例（单例）

    Returns:
        DeepAgentsTaskExecutor 实例
    """
    global _task_executor

    if _task_executor is None:
        with _executor_lock:
            if _task_executor is None:
                _task_executor = DeepAgentsTaskExecutor()

    return _task_executor
