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
    get_metadata_service, get_glossary_service,
    get_relation_field_config_service, get_prompt_template_service
)
from services.tracking_service.operation_tracking import OperationTracker
from services.query_engine import get_query_engine
from services.service_models import BaseNodeLog, TaskState, TaskStateHelper
from services.prompt_template_renderer import PromptTemplateRenderer

from utils.config import settings
from utils.logger import logger
from utils.progress_decorator import track_node_progress

from sqlalchemy.orm import Session


# 全局NL2SQLServiceV2实例缓存
_nl2sql_service_v2_instance = None


def get_nl2sql_service_v2(db_session: Optional[Session] = None) -> 'NL2SQLServiceV2':
    """获取NL2SQLServiceV2实例（单例模式）

    Args:
        db_session: 数据库会话（可选，用于Training Service）

    Returns:
        NL2SQLServiceV2实例
    """
    global _nl2sql_service_v2_instance
    if _nl2sql_service_v2_instance is None:
        _nl2sql_service_v2_instance = NL2SQLServiceV2(db_session=db_session)
    return _nl2sql_service_v2_instance


class NL2SQLServiceV2:
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

        # 初始化LLM服务
        # 创建OpenAI客户端
        openai_client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

        llm_config = {
            "model": settings.openai_model,
            "temperature": settings.openai_temperature,
            "max_tokens": 2000
        }
        template_service = get_prompt_template_service()
        self.llm_service = NLQueryLLMService(
            openai_client,
            llm_config,
            template_service=template_service
        )

        # 初始化Training Service（如果提供了数据库会话）
        self.training_service = None
        if db_session:
            self.training_service = TrainingService(db_session)

        # 初始化其他服务
        self.metadata_service = get_metadata_service()
        self.glossary_service = get_glossary_service()
        self.relation_config_service = get_relation_field_config_service()
        self.prompt_template_service = get_prompt_template_service()
        self.db_service = get_query_engine()
        self.template_renderer = PromptTemplateRenderer(self.prompt_template_service)

        # 操作追踪器（如果提供了数据库会话）
        self.operation_tracker = None
        if db_session:
            self.operation_tracker = OperationTracker(db_session)

        # 构建工作流
        self.workflow = self._build_workflow()

        logger.info("NL2SQLServiceV2 初始化完成（新的模块化架构）")

    def _build_workflow(self) -> StateGraph:
        """构建LangGraph工作流"""

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

        @track_node_progress("检索上下文")
        def retrieve_context(state: TaskState) -> TaskState:
            """从向量库检索上下文"""
            try:
                user_input = state.user_input
                relation_id = getattr(state, "relation_id", None)
                table_names = getattr(state, "table_names", None)

                # 使用Context Builder检索上下文
                if relation_id and table_names:
                    context = self.context_builder.retrieve_hybrid(
                        user_input=user_input,
                        relation_id=relation_id,
                        table_names=table_names,
                        top_k=5
                    )
                elif relation_id:
                    context = self.context_builder.retrieve_by_relation_id(
                        relation_id=relation_id,
                        user_input=user_input,
                        top_k=5
                    )
                elif table_names:
                    context = self.context_builder.retrieve_by_table_first(
                        table_names=table_names,
                        user_input=user_input,
                        top_k=5
                    )
                else:
                    context = self.context_builder.retrieve_by_semantic_search(
                        user_input=user_input,
                        top_k=10
                    )

                state.context = context
                state.current_step_log = BaseNodeLog(
                    step="检索上下文",
                    input_data=user_input,
                    prompt="",
                    model_output=f"Retrieved context ({len(context)} chars)",
                    success=True
                )
                return state

            except Exception as e:
                logger.error(f"上下文检索失败: {e}")
                state.context = ""
                state.current_step_log = BaseNodeLog(
                    step="检索上下文",
                    input_data=user_input,
                    prompt="",
                    model_output="",
                    success=False,
                    error=str(e)
                )
                return state

        @track_node_progress("生成SQL")
        def generate_sql(state: TaskState) -> TaskState:
            """使用LLM Service生成SQL"""
            try:
                user_input = state.user_input
                context = getattr(state, "context", "")
                error_message = getattr(state, "error_message", None)
                previous_sql = getattr(state, "sql_query", "")

                # 根据是否有错误决定使用生成还是重试
                if error_message and previous_sql:
                    result = self.llm_service.retry_sql_generation(
                        user_input=user_input,
                        context=context,
                        previous_sql=previous_sql,
                        error_message=error_message,
                        temperature=0.3
                    )
                    step_name = "SQL重试生成"
                else:
                    result = self.llm_service.generate_sql(
                        user_input=user_input,
                        context=context,
                        temperature=0.1
                    )
                    step_name = "生成SQL"

                if result["success"]:
                    state.sql_query = result["sql"]
                    state.sql_confidence = result["confidence"]
                    state.error_message = None
                    success = True
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
                    step="生成SQL",
                    input_data=state.user_input,
                    prompt="",
                    model_output="",
                    success=False,
                    error=str(e)
                )
                return state

        @track_node_progress("验证SQL")
        def validate_sql(state: TaskState) -> TaskState:
            """验证生成的SQL"""
            try:
                sql_query = getattr(state, "sql_query", "")
                if not sql_query:
                    state.is_valid_sql = False
                    state.validation_error = "没有生成SQL"
                    return state

                # 尝试执行SQL验证
                try:
                    result = self.db_service.execute(sql_query)
                    state.is_valid_sql = True
                    state.execution_result = result
                    state.validation_error = None

                    # 如果有Training Service，记录成功的验证
                    if self.training_service:
                        self.training_service.record_validation_result(
                            training_data_id=None,
                            original_sql=sql_query,
                            executed_sql=sql_query,
                            is_valid=True,
                            execution_status="success",
                            row_count=len(result) if result else 0
                        )

                except Exception as exec_error:
                    state.is_valid_sql = False
                    state.validation_error = str(exec_error)
                    state.error_message = str(exec_error)

                    # 记录失败的验证
                    if self.training_service:
                        self.training_service.record_validation_result(
                            training_data_id=None,
                            original_sql=sql_query,
                            executed_sql=sql_query,
                            is_valid=False,
                            error_message=str(exec_error),
                            execution_status="error"
                        )

                state.current_step_log = BaseNodeLog(
                    step="验证SQL",
                    input_data=sql_query,
                    prompt="",
                    model_output="Valid" if state.is_valid_sql else state.validation_error,
                    success=state.is_valid_sql
                )
                return state

            except Exception as e:
                logger.error(f"SQL验证失败: {e}")
                state.is_valid_sql = False
                state.validation_error = str(e)
                state.current_step_log = BaseNodeLog(
                    step="验证SQL",
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
                sql_query = getattr(state, "sql_query", "")
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
                    model_output=state.sql_explanation if state.sql_explanation else "无解释",
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

        # 构建工作流图
        workflow = StateGraph(TaskState)

        # 添加节点
        workflow.add_node("check_training", check_training_needed)
        workflow.add_node("retrieve_context", retrieve_context)
        workflow.add_node("generate_sql", generate_sql)
        workflow.add_node("validate_sql", validate_sql)
        workflow.add_node("explain_result", explain_result)

        # 添加边
        workflow.set_entry_point("check_training")
        workflow.add_edge("check_training", "retrieve_context")
        workflow.add_edge("retrieve_context", "generate_sql")
        workflow.add_edge("generate_sql", "validate_sql")
        workflow.add_edge("validate_sql", "explain_result")
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
                user_input=user_input,
                flow_type=flow_type,
                relation_id=relation_id,
                table_names=table_names or [],
                created_at=datetime.now()
            )

            # 执行工作流
            result = self.workflow.invoke(initial_state)

            # 构建返回结果
            return {
                "success": True,
                "user_input": user_input,
                "sql_query": result.sql_query,
                "sql_confidence": result.sql_confidence,
                "execution_result": result.execution_result if result.is_valid_sql else None,
                "is_valid": result.is_valid_sql,
                "explanation": result.sql_explanation,
                "steps": self._extract_steps(result)
            }

        except Exception as e:
            logger.error(f"NL2SQL查询失败: {e}\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "user_input": user_input
            }

    def _extract_steps(self, state: TaskState) -> list:
        """从状态中提取执行步骤"""
        steps = []
        # 这里可以从state的step日志中提取步骤信息
        # 实现细节取决于如何存储步骤日志
        return steps

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

    def process_query(self, user_input: str, task_id: str, max_retries: int = 5,
                     operator: str = "api_user", flow_type: str = "fast",
                     tracker: Optional[Any] = None) -> Dict[str, Any]:
        """兼容旧API的处理查询方法（用于AsyncQueryService）

        Args:
            user_input: 用户输入
            task_id: 任务ID（用于追踪）
            max_retries: 最大重试次数（保留参数以兼容旧API）
            operator: 操作者（保留参数以兼容旧API）
            flow_type: 流程类型
            tracker: 操作追踪器（保留参数以兼容旧API）

        Returns:
            查询结果字典
        """
        try:
            # 直接调用query方法，返回结果
            result = self.query(user_input=user_input, flow_type=flow_type)

            # 如果提供了tracker，记录结果
            if tracker:
                try:
                    # 记录成功的查询结果
                    if result.get("success"):
                        logger.info(f"任务 {task_id} 查询成功: {user_input[:50]}...")
                    else:
                        logger.warning(f"任务 {task_id} 查询失败: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    logger.warning(f"记录任务结果失败: {e}")

            return result

        except Exception as e:
            logger.error(f"处理查询失败: {e}\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "user_input": user_input
            }
