"""
查询处理器
整合工作流引擎和Vanna服务，提供统一的查询处理接口
"""
import uuid
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from .workflow_engine import WorkflowEngine, WorkflowState
from .vanna_service import get_vanna_service
from utils.logger import get_logger
from utils.exceptions import NLQueryException, ValidationException
from models.nlquery_models import TaskStatusEnum

logger = get_logger(__name__)


class QueryProcessor:
    """查询处理器"""
    
    def __init__(self):
        self.workflow_engine = WorkflowEngine()
        self.vanna_service = get_vanna_service()
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
    
    async def submit_query(
        self,
        user_question: str,
        user_id: int,
        selected_theme_id: Optional[int] = None,
        selected_table_ids: Optional[List[int]] = None,
        query_type: str = "natural_language"
    ) -> Dict[str, Any]:
        """
        提交查询请求
        
        Args:
            user_question: 用户问题
            user_id: 用户ID
            selected_theme_id: 选择的数据主题ID
            selected_table_ids: 选择的表ID列表
            query_type: 查询类型
            
        Returns:
            查询任务信息
        """
        try:
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 验证输入
            await self._validate_query_input(
                user_question, user_id, selected_theme_id, selected_table_ids
            )
            
            # 创建初始状态
            initial_state = WorkflowState(
                task_id=task_id,
                user_id=user_id,
                user_question=user_question,
                selected_theme_id=selected_theme_id,
                selected_table_ids=selected_table_ids,
                current_step="",
                progress_percentage=0,
                error_message=None,
                error_code=None,
                generated_sql=None,
                final_sql=None,
                sql_validation_result=None,
                execution_result=None,
                result_row_count=None,
                result_columns=None,
                result_data=None,
                llm_messages=[],
                llm_tokens_used=0,
                node_execution_log=[],
                retry_count=0,
                max_retries=3
            )
            
            # 记录任务
            task_info = {
                "task_id": task_id,
                "user_id": user_id,
                "user_question": user_question,
                "query_type": query_type,
                "status": TaskStatusEnum.PENDING.value,
                "created_at": datetime.now(),
                "state": initial_state
            }
            
            self.active_tasks[task_id] = task_info
            
            # 异步执行工作流
            asyncio.create_task(self._execute_query_workflow(task_id, initial_state))
            
            logger.info(f"查询任务已提交，任务ID: {task_id}")
            
            return {
                "task_id": task_id,
                "status": TaskStatusEnum.PENDING.value,
                "message": "查询任务已提交，正在处理中..."
            }
            
        except Exception as e:
            logger.error(f"提交查询失败: {e}")
            raise NLQueryException(f"提交查询失败: {e}")
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        try:
            if task_id not in self.active_tasks:
                # TODO: 从数据库查询历史任务
                raise NLQueryException(f"任务 {task_id} 不存在")
            
            task_info = self.active_tasks[task_id]
            state = task_info["state"]
            
            return {
                "task_id": task_id,
                "status": task_info["status"],
                "current_step": state.get("current_step", ""),
                "progress_percentage": state.get("progress_percentage", 0),
                "error_message": state.get("error_message"),
                "error_code": state.get("error_code"),
                "created_at": task_info["created_at"].isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            raise NLQueryException(f"获取任务状态失败: {e}")
    
    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务结果信息
        """
        try:
            if task_id not in self.active_tasks:
                raise NLQueryException(f"任务 {task_id} 不存在")
            
            task_info = self.active_tasks[task_id]
            state = task_info["state"]
            
            # 检查任务是否完成
            if task_info["status"] not in [TaskStatusEnum.SUCCESS.value, TaskStatusEnum.FAILED.value]:
                return {
                    "task_id": task_id,
                    "status": task_info["status"],
                    "message": "任务尚未完成"
                }
            
            result = {
                "task_id": task_id,
                "status": task_info["status"],
                "user_question": state.get("user_question"),
                "generated_sql": state.get("generated_sql"),
                "final_sql": state.get("final_sql"),
                "execution_result": state.get("execution_result"),
                "result_row_count": state.get("result_row_count", 0),
                "result_columns": state.get("result_columns", []),
                "result_data": state.get("result_data", []),
                "error_message": state.get("error_message"),
                "llm_tokens_used": state.get("llm_tokens_used", 0),
                "node_execution_log": state.get("node_execution_log", [])
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            raise NLQueryException(f"获取任务结果失败: {e}")
    
    async def cancel_task(self, task_id: str, user_id: int) -> Dict[str, Any]:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            取消结果
        """
        try:
            if task_id not in self.active_tasks:
                raise NLQueryException(f"任务 {task_id} 不存在")
            
            task_info = self.active_tasks[task_id]
            
            # 验证用户权限
            if task_info["user_id"] != user_id:
                raise NLQueryException("无权限取消此任务")
            
            # 更新任务状态
            task_info["status"] = TaskStatusEnum.CANCELLED.value
            task_info["state"]["current_step"] = "任务已取消"
            task_info["state"]["error_message"] = "用户取消了任务"
            
            logger.info(f"任务已取消: {task_id}")
            
            return {
                "task_id": task_id,
                "status": TaskStatusEnum.CANCELLED.value,
                "message": "任务已取消"
            }
            
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            raise NLQueryException(f"取消任务失败: {e}")
    
    async def get_query_suggestions(
        self, 
        partial_question: str, 
        user_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取查询建议
        
        Args:
            partial_question: 部分问题文本
            user_id: 用户ID
            limit: 返回数量限制
            
        Returns:
            查询建议列表
        """
        try:
            # 使用Vanna服务获取相似问题
            similar_questions = await self.vanna_service.get_similar_questions(
                partial_question, limit
            )
            
            # TODO: 基于用户历史查询提供个性化建议
            
            suggestions = []
            for item in similar_questions:
                suggestions.append({
                    "question": item["question"],
                    "similarity": item["similarity"],
                    "category": "历史查询"  # 可以根据实际情况分类
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"获取查询建议失败: {e}")
            return []
    
    async def _validate_query_input(
        self,
        user_question: str,
        user_id: int,
        selected_theme_id: Optional[int],
        selected_table_ids: Optional[List[int]]
    ):
        """验证查询输入"""
        if not user_question or not user_question.strip():
            raise ValidationException("用户问题不能为空")
        
        if len(user_question) > 1000:
            raise ValidationException("问题描述过长，请控制在1000字符以内")
        
        if not user_id or user_id <= 0:
            raise ValidationException("无效的用户ID")
        
        # TODO: 验证主题和表的存在性及权限
    
    async def _execute_query_workflow(self, task_id: str, initial_state: WorkflowState):
        """执行查询工作流"""
        try:
            logger.info(f"开始执行查询工作流: {task_id}")
            
            # 更新任务状态
            self.active_tasks[task_id]["status"] = TaskStatusEnum.RUNNING.value
            
            # 集成Vanna服务到工作流状态
            initial_state["vanna_service"] = self.vanna_service
            
            # 执行工作流
            final_state = await self.workflow_engine.execute_workflow(initial_state)
            
            # 判断执行结果
            if final_state.get("error_message"):
                self.active_tasks[task_id]["status"] = TaskStatusEnum.FAILED.value
                logger.error(f"查询工作流执行失败: {task_id}, 错误: {final_state['error_message']}")
            else:
                self.active_tasks[task_id]["status"] = TaskStatusEnum.SUCCESS.value
                logger.info(f"查询工作流执行成功: {task_id}")
            
            # 更新最终状态
            self.active_tasks[task_id]["state"] = final_state
            
            # TODO: 将结果保存到数据库
            await self._save_task_result(task_id, final_state)
            
        except Exception as e:
            logger.error(f"查询工作流执行异常: {task_id}, 错误: {e}")
            
            # 更新错误状态
            self.active_tasks[task_id]["status"] = TaskStatusEnum.FAILED.value
            self.active_tasks[task_id]["state"]["error_message"] = str(e)
            self.active_tasks[task_id]["state"]["current_step"] = "执行失败"
            
    async def _save_task_result(self, task_id: str, final_state: WorkflowState):
        """保存任务结果到数据库"""
        try:
            # TODO: 实现保存到数据库的逻辑
            logger.info(f"任务结果已保存: {task_id}")
        except Exception as e:
            logger.error(f"保存任务结果失败: {task_id}, 错误: {e}")
    
    def get_active_tasks_count(self) -> int:
        """获取活跃任务数量"""
        return len([
            task for task in self.active_tasks.values()
            if task["status"] in [TaskStatusEnum.PENDING.value, TaskStatusEnum.RUNNING.value]
        ])
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """清理完成的任务"""
        try:
            current_time = datetime.now()
            tasks_to_remove = []
            
            for task_id, task_info in self.active_tasks.items():
                # 计算任务年龄
                task_age = current_time - task_info["created_at"]
                
                # 如果任务完成且超过指定时间，标记为删除
                if (task_info["status"] in [
                    TaskStatusEnum.SUCCESS.value, 
                    TaskStatusEnum.FAILED.value, 
                    TaskStatusEnum.CANCELLED.value
                ] and task_age.total_seconds() > max_age_hours * 3600):
                    tasks_to_remove.append(task_id)
            
            # 删除过期任务
            for task_id in tasks_to_remove:
                del self.active_tasks[task_id]
                logger.info(f"清理过期任务: {task_id}")
            
            if tasks_to_remove:
                logger.info(f"清理了 {len(tasks_to_remove)} 个过期任务")
                
        except Exception as e:
            logger.error(f"清理任务失败: {e}")


# 全局查询处理器实例
_query_processor = None


def get_query_processor() -> QueryProcessor:
    """获取查询处理器实例（单例模式）"""
    global _query_processor
    if _query_processor is None:
        _query_processor = QueryProcessor()
    return _query_processor