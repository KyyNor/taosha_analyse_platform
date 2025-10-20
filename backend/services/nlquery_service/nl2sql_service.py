"""
增强的NL2SQL服务 - 集成Vector Store、Context Builder、LLM Service、Training Service
使用新的模块化架构替代Vanna
"""

import json
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from openai import OpenAI

from langgraph.graph import StateGraph, END

from services.vector_store import VectorStoreFactory, NLQueryContextBuilder
from services.llm_service import NLQueryLLMService
from services.training_service import TrainingService
from services.metadata_service.metadata_service import (
    get_metadata_service, get_prompt_template_service
)
from services.tracking_service.operation_tracking import OperationTracker
from services.query_engine import get_query_engine
from services.service_models import BaseNodeLog, TaskState, TaskStateHelper

from utils.config import settings
from utils.logger import logger
from utils.progress_decorator import track_node_progress

from sqlalchemy.orm import Session


# 全局NL2SQLServiceV2实例缓存
_nl2sql_service_instance = None


def get_nl2sql_service(db_session: Optional[Session] = None) -> 'NL2SQLService':
    """获取NL2SQLServiceV2实例（单例模式）

    Args:
        db_session: 数据库会话（可选，用于Training Service）

    Returns:
        NL2SQLServiceV2实例
    """
    global _nl2sql_service_instance
    if _nl2sql_service_instance is None:
        _nl2sql_service_instance = NL2SQLService(db_session=db_session)
    return _nl2sql_service_instance


class NL2SQLService:
    """增强的NL2SQL服务 - 集成新的模块化服务"""

    def __init__(self, db_session: Optional[Session] = None):
        """初始化NL2SQL服务V2

        Args:
            db_session: 数据库会话（可选，用于Training Service）
        """
        # 初始化向量存储和上下文构建器
        try:
            # 尝试创建Qdrant向量存储
            self.vector_store = VectorStoreFactory.create("qdrant", None, {})
            self.context_builder = NLQueryContextBuilder(
                vector_store=self.vector_store,
                embedding_func=None
            )
        except Exception as e:
            logger.warning(f"向量存储初始化失败，使用ChromaDB: {e}")
            # 降级到ChromaDB
            self.vector_store = VectorStoreFactory.create("chromadb", None, {})
            self.context_builder = NLQueryContextBuilder(
                vector_store=self.vector_store,
                embedding_func=None
            )

        template_service = get_prompt_template_service(db_session)
        self.llm_service = NLQueryLLMService(
            template_service=template_service
        )

        # 初始化Training Service（如果提供了数据库会话）
        self.training_service = None
        if db_session:
            self.training_service = TrainingService(db_session)

        # 初始化其他服务
        self.metadata_service = get_metadata_service()
        self.db_service = get_query_engine()

        # 构建工作流
        self.workflow = self._build_workflow()

        logger.info("NL2SQLServiceV2 初始化完成（新的模块化架构）")

    def _build_workflow(self) -> StateGraph:
        """构建LangGraph工作流（与原nl2sql_service.py逻辑一致）"""

        @track_node_progress("知识库检查")
        def check_training_needed(state: TaskState) -> TaskState:
            """检查是否需要重新训练模型"""
            try:
                # 检查Training Service是否可用
                if self.training_service:
                    stats = self.training_service.get_training_data_statistics()
                    logger.info(f"训练数据统计: {stats}")
                else:
                    logger.info("Training Service未初始化")

                state.current_step_log = BaseNodeLog(
                    step="知识库检查",
                    input_data="knowledge base check",
                    prompt="",
                    model_output="knowledge base ready",
                    success=True
                )
                return state

            except Exception as e:
                logger.error(f"知识库检查失败: {e}")
                state.current_step_log = BaseNodeLog(
                    step="知识库检查",
                    input_data="",
                    prompt="",
                    model_output="",
                    success=False,
                    error=str(e)
                )
                return state

        @track_node_progress("检查输入清晰度")
        def validate_input(state: TaskState) -> TaskState:
            """验证输入是否清晰（fast流程）或在thorough流程中验证SQL"""
            try:
                user_input = state.user_input
                flow_type = getattr(state, 'flow_type', 'fast')
                sql_query = getattr(state, 'sql_query', '')

                # 确定验证类型
                if flow_type == 'thorough' and sql_query:
                    # thorough流程：验证SQL和输入是否匹配
                    step_name = "SQL验证"
                    input_for_validation = f"user:{user_input}\nsql:{sql_query}"
                    # 构建上下文（从元数据服务获取）
                    context = ""
                    try:
                        tables = self.metadata_service.get_all_tables()
                        context = json.dumps([{"table": t.table_name, "columns": [c.column_name for c in t.columns]}
                                           for t in tables], ensure_ascii=False)
                    except:
                        pass
                else:
                    # fast流程或第一次验证：验证输入清晰度
                    step_name = "处理输入"
                    input_for_validation = user_input
                    context = ""

                # 使用LLM验证（调用正确的方法名）
                validation_result = self.llm_service.validate_input_clarity(
                    user_input=user_input,
                    context=context,
                    sql_query=sql_query if sql_query else "",
                    flow_type=flow_type
                )

                state.is_clear = validation_result.get("is_clear", False)
                state.clear_check_details = {
                    "details": validation_result.get("details", ""),
                    "suggestions": validation_result.get("suggestions", []),
                    "confidence": validation_result.get("confidence", 0.0)
                }
                state.current_step_log = BaseNodeLog(
                    step=step_name,
                    input_data=input_for_validation,
                    prompt="",
                    model_output="Clear" if state.is_clear else "Not clear",
                    success=state.is_clear
                )
                return state

            except Exception as e:
                logger.error(f"输入验证失败: {e}")
                state.is_clear = False
                state.error_message = str(e)
                state.current_step_log = BaseNodeLog(
                    step="检查输入清晰度",
                    input_data="",
                    prompt="",
                    model_output="",
                    success=False,
                    error=str(e)
                )
                return state

        @track_node_progress("生成查询语句")
        def generate_sql(state: TaskState) -> TaskState:
            """使用LLM Service生成SQL"""
            try:
                user_input = state.user_input
                error_message = getattr(state, 'error_message', None)
                previous_sql = getattr(state, 'sql_query', '')
                retry_count = getattr(state, 'retry_count', 0)

                # 根据是否有错误决定使用生成还是重试
                if error_message and previous_sql:
                    result = self.llm_service.retry_sql_generation(
                        user_input=user_input,
                        previous_sql=previous_sql,
                        error_message=error_message,
                        temperature=0.3
                    )
                    step_name = "SQL重试生成"
                else:
                    result = self.llm_service.generate_sql(
                        user_input=user_input,
                        context="",
                        temperature=0.1
                    )
                    step_name = "生成查询语句"

                if result["success"]:
                    state.sql_query = result["sql"]
                    success = True
                    state.error_message = None
                    state.retry_count = 0
                else:
                    state.error_message = result.get("error", "SQL生成失败")
                    success = False

                state.current_step_log = BaseNodeLog(
                    step=step_name,
                    input_data=user_input,
                    prompt="",
                    model_output=state.sql_query if success else state.error_message,
                    success=success
                )
                return state

            except Exception as e:
                logger.error(f"SQL生成失败: {e}")
                state.error_message = str(e)
                state.current_step_log = BaseNodeLog(
                    step="生成查询语句",
                    input_data=state.user_input,
                    prompt="",
                    model_output="",
                    success=False,
                    error=str(e)
                )
                return state

        @track_node_progress("执行SQL")
        def execute_sql(state: TaskState) -> TaskState:
            """执行生成的SQL"""
            try:
                sql_query = getattr(state, 'sql_query', '')
                if not sql_query:
                    state.error_message = "没有生成SQL"
                    state.current_step_log = BaseNodeLog(
                        step="执行SQL",
                        input_data="",
                        prompt="",
                        model_output="",
                        success=False,
                        error="没有生成SQL"
                    )
                    return state

                # 尝试执行SQL
                try:
                    result = self.db_service.execute(sql_query)
                    state.execution_result = result
                    state.error_message = None
                    state.current_step_log = BaseNodeLog(
                        step="执行SQL",
                        input_data=sql_query,
                        prompt="",
                        model_output=f"Success: {len(result) if result else 0} rows",
                        success=True
                    )

                    # 如果有Training Service，记录成功的结果
                    if self.training_service:
                        try:
                            self.training_service.record_validation_result(
                                training_data_id=None,
                                original_sql=sql_query,
                                executed_sql=sql_query,
                                is_valid=True,
                                execution_status="success",
                                row_count=len(result) if result else 0
                            )
                        except Exception as e:
                            logger.warning(f"记录验证结果失败: {e}")

                except Exception as exec_error:
                    state.error_message = str(exec_error)
                    state.current_step_log = BaseNodeLog(
                        step="执行SQL",
                        input_data=sql_query,
                        prompt="",
                        model_output="",
                        success=False,
                        error=str(exec_error)
                    )

                    # 记录失败的验证
                    if self.training_service:
                        try:
                            self.training_service.record_validation_result(
                                training_data_id=None,
                                original_sql=sql_query,
                                executed_sql=sql_query,
                                is_valid=False,
                                error_message=str(exec_error),
                                execution_status="error"
                            )
                        except Exception as e:
                            logger.warning(f"记录失败结果失败: {e}")

                return state

            except Exception as e:
                logger.error(f"执行SQL失败: {e}")
                state.error_message = str(e)
                state.current_step_log = BaseNodeLog(
                    step="执行SQL",
                    input_data="",
                    prompt="",
                    model_output="",
                    success=False,
                    error=str(e)
                )
                return state

        @track_node_progress("解释结果")
        def explain_result(state: TaskState) -> TaskState:
            """解释SQL查询和执行结果"""
            try:
                sql_query = getattr(state, 'sql_query', '')
                user_input = state.user_input

                if sql_query:
                    explanation_result = self.llm_service.explain_sql(
                        sql_query=sql_query,
                        user_input=user_input,
                        temperature=0.2
                    )

                    if explanation_result["success"]:
                        state.sql_explanation = explanation_result["explanation"]
                    else:
                        state.sql_explanation = "无法生成解释"
                else:
                    state.sql_explanation = ""

                state.current_step_log = BaseNodeLog(
                    step="解释结果",
                    input_data=sql_query,
                    prompt="",
                    model_output=state.sql_explanation if getattr(state, 'sql_explanation', '') else "无解释",
                    success=True
                )
                return state

            except Exception as e:
                logger.error(f"解释生成失败: {e}")
                state.sql_explanation = ""
                state.current_step_log = BaseNodeLog(
                    step="解释结果",
                    input_data="",
                    prompt="",
                    model_output="",
                    success=False,
                    error=str(e)
                )
                return state

        # 路由逻辑函数（与原流程一致）
        def route_by_flow_type(state: TaskState) -> str:
            """根据流程类型决定下一步"""
            flow_type = getattr(state, 'flow_type', 'fast')
            return flow_type

        def route_after_validation(state: TaskState) -> str:
            """验证后的路由逻辑"""
            if not getattr(state, 'is_clear', None):
                return "failed"

            flow_type = getattr(state, 'flow_type', 'fast')
            sql_query = getattr(state, 'sql_query', '')

            if flow_type == 'fast' or not sql_query:
                # 快速流程：验证通过后生成SQL
                # 或者深度流程的第一次验证（此时还没有SQL）
                return "generate_sql"
            else:
                # 深度流程：已经有SQL，验证通过后执行
                return "execute_sql"

        def route_after_generate_sql(state: TaskState) -> str:
            """生成SQL后的路由逻辑"""
            flow_type = getattr(state, 'flow_type', 'fast')
            if flow_type == 'thorough':
                # 深度流程：生成SQL后需要验证
                return "validate_input"
            else:
                # 快速流程：直接执行SQL
                return "execute_sql"

        def should_retry(state: TaskState) -> str:
            """重试逻辑：如果失败且可以重试，回到generate_sql"""
            error_message = getattr(state, 'error_message', None)
            retry_count = getattr(state, 'retry_count', 0)
            max_retries = getattr(state, 'max_retries', 5)

            if error_message and retry_count < max_retries:
                state.retry_count = retry_count + 1
                return "retry"
            elif error_message:
                return "failed"
            else:
                return "success"

        # 构建工作流图
        workflow = StateGraph(TaskState)

        # 添加节点
        workflow.add_node("check_training", check_training_needed)
        workflow.add_node("validate_input", validate_input)
        workflow.add_node("generate_sql", generate_sql)
        workflow.add_node("execute_sql", execute_sql)
        workflow.add_node("explain_result", explain_result)

        # 添加边
        workflow.set_entry_point("check_training")

        # check_training根据flow_type路由
        workflow.add_conditional_edges(
            "check_training",
            route_by_flow_type,
            {
                "fast": "validate_input",        # 快速流程：先验证后生成
                "thorough": "generate_sql"      # 深度流程：先生成后验证
            }
        )

        # validate_input的路由
        workflow.add_conditional_edges(
            "validate_input",
            route_after_validation,
            {
                "generate_sql": "generate_sql",
                "execute_sql": "execute_sql",
                "failed": END
            }
        )

        # generate_sql的路由
        workflow.add_conditional_edges(
            "generate_sql",
            route_after_generate_sql,
            {
                "validate_input": "validate_input",
                "execute_sql": "execute_sql"
            }
        )

        # execute_sql的路由（重试逻辑）
        workflow.add_conditional_edges(
            "execute_sql",
            should_retry,
            {
                "retry": "generate_sql",
                "success": "explain_result",
                "failed": "explain_result"
            }
        )

        # explain_result到结束
        workflow.add_edge("explain_result", END)

        return workflow.compile()

    def query(self, user_input: str, flow_type: str = "fast",
              relation_id: Optional[str] = None,
              table_names: Optional[list] = None) -> Dict[str, Any]:
        """执行自然语言查询

        Args:
            user_input: 用户的自然语言查询
            flow_type: 流程类型（fast或thorough）
            relation_id: 可选的关联ID
            table_names: 可选的表名列表

        Returns:
            查询结果字典
        """
        try:
            logger.info(f"执行NL2SQL查询: {user_input[:100]}...")

            # 创建初始状态
            initial_state = TaskState(
                task_id="inline_query",  # 非追踪模式下的任务ID
                user_input=user_input,
                flow_type=flow_type,
                created_at=datetime.now()
            )

            # 执行工作流
            result = self.workflow.invoke(initial_state)

            # 将结果转换为TaskState对象（如果是dict）
            if isinstance(result, dict):
                result = TaskState(**result)

            # 构建返回结果
            error_msg = getattr(result, 'error_message', None)
            return {
                "success": error_msg is None,
                "user_input": user_input,
                "sql_query": getattr(result, 'sql_query', ''),
                "execution_result": getattr(result, 'execution_result', None) if error_msg is None else None,
                "is_valid": error_msg is None,
                "explanation": getattr(result, 'sql_explanation', ''),
                "error": error_msg
            }

        except Exception as e:
            logger.error(f"NL2SQL查询失败: {e}\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "user_input": user_input
            }

    def process_query(self, user_input: str, task_id: str, max_retries: int = 5,
                     operator: str = "api_user", flow_type: str = "fast",
                     tracker: Optional[Any] = None) -> Dict[str, Any]:
        """兼容旧API的处理查询方法（用于AsyncQueryService）

        Args:
            user_input: 用户输入
            task_id: 任务ID（用于追踪）
            max_retries: 最大重试次数
            operator: 操作者
            flow_type: 流程类型
            tracker: 操作追踪器

        Returns:
            查询结果字典
        """
        try:
            logger.info(f"查询流程V2: 任务ID={task_id}, 用户输入={user_input[:50]}, 流程类型={flow_type}")

            if tracker is None:
                raise ValueError("tracker参数是必须的，请通过依赖注入传入OperationTracker实例")

            # 创建统一的任务状态
            task_state = TaskStateHelper.create_default(
                task_id=task_id,
                user_input=user_input,
                flow_type=flow_type,
                max_retries=max_retries,
                operator=operator
            )

            tracker.create_task(task_state)

            # 执行工作流
            result = self.workflow.invoke(task_state)

            # 将结果转换为TaskState对象（如果是dict）
            if isinstance(result, dict):
                result = TaskState(**result)

            # 更新追踪器
            error_msg = getattr(result, 'error_message', None)
            if error_msg:
                tracker.update_task_progress(
                    task_id=task_id,
                    progress=100,
                    step_name="查询失败",
                    error=error_msg,
                    final_status="failed",
                    write_step_log=False
                )
            else:
                tracker.update_task_progress(
                    task_id=task_id,
                    progress=100,
                    step_name="查询完成",
                    final_status="success",
                    write_step_log=False
                )

            return {
                "success": error_msg is None,
                "user_input": user_input,
                "sql_query": getattr(result, 'sql_query', ''),
                "execution_result": getattr(result, 'execution_result', None) if error_msg is None else None,
                "is_valid": error_msg is None,
                "explanation": getattr(result, 'sql_explanation', ''),
                "error": error_msg
            }

        except Exception as e:
            logger.error(f"处理查询失败: {e}\n{traceback.format_exc()}")
            if tracker:
                try:
                    tracker.update_task_progress(
                        task_id=task_id,
                        progress=0,
                        step_name="处理失败",
                        error=str(e),
                        final_status="failed",
                        write_step_log=False
                    )
                except:
                    pass

            return {
                "success": False,
                "error": str(e),
                "user_input": user_input
            }

    def add_training_data(self, question: str, sql: str, **kwargs) -> bool:
        """添加训练数据

        Args:
            question: 自然语言问题
            sql: 对应的SQL
            **kwargs: 其他参数

        Returns:
            是否成功
        """
        if not self.training_service:
            logger.warning("Training Service未初始化")
            return False

        try:
            result = self.training_service.add_training_data(
                question=question,
                sql=sql,
                **kwargs
            )
            return result is not None
        except Exception as e:
            logger.error(f"添加训练数据失败: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        stats = {}

        # 获取训练数据统计
        if self.training_service:
            stats["training_data"] = self.training_service.get_training_data_statistics()
            stats["validation"] = self.training_service.get_validation_statistics()

        # 获取向量库统计
        try:
            count = self.vector_store.count()
            stats["vector_store"] = {"documents": count}
        except:
            stats["vector_store"] = {"documents": 0}

        return stats
