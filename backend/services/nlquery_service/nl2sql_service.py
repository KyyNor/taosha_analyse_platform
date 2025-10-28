"""
增强的NL2SQL服务 - 集成Vector Store、Context Builder、LLM Service、Training Service
使用新的模块化架构替代Vanna
"""

import json
import traceback
import re
from datetime import datetime
from typing import Optional, Dict, Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from services.vector_store import NLQueryContextBuilder
from services.llm_service import NLQueryLLMService
from services.metadata_service.metadata_service import (
    get_metadata_service, get_prompt_template_service
)
from services.query_engine import get_query_engine
from services.service_models import BaseNodeLog, TaskState, TaskStateHelper
from services.tracking_service.observability_service import get_tracing_handler
from services.vector_store.qdrant_vector_store import qdrant_vector_store

from utils.logger import logger
from utils.progress_decorator import track_node_progress

from sqlalchemy.orm import Session


# 全局NL2SQLService实例缓存
_nl2sql_service_instance = None


def get_nl2sql_service(db_session: Optional[Session] = None) -> 'NL2SQLService':
    """获取NL2SQLService实例（单例模式）

    Args:
        db_session: 数据库会话（可选，用于Training Service）

    Returns:
        NL2SQLService实例
    """
    global _nl2sql_service_instance
    if _nl2sql_service_instance is None:
        _nl2sql_service_instance = NL2SQLService(db_session=db_session)
    return _nl2sql_service_instance


class NL2SQLService:
    """增强的NL2SQL服务 - 集成新的模块化服务"""

    def __init__(self, db_session: Optional[Session] = None):
        """初始化NL2SQL服务

        Args:
            db_session: 数据库会话（可选，用于Training Service）
        """
        # 使用全局向量存储实例和上下文构建器
        try:
            self.vector_store = qdrant_vector_store
            self.context_builder = NLQueryContextBuilder()
            logger.info("向量存储和上下文构建器初始化成功，使用全局实例")
        except Exception as e:
            logger.error(f"向量存储初始化失败: {e}")
            raise

        template_service = get_prompt_template_service(db_session)
        self.llm_service = NLQueryLLMService(
            template_service=template_service
        )

  
        # 初始化其他服务
        self.metadata_service = get_metadata_service()
        self.db_service = get_query_engine()

        # 构建工作流
        self.workflow = self._build_workflow()

        logger.info("NL2SQLService 初始化完成")

    @staticmethod
    def _is_sql_safe(sql_query: str) -> tuple[bool, str]:
        """检查SQL是否安全 - 防止危险操作

        Args:
            sql_query: SQL查询语句

        Returns:
            (is_safe: bool, reason: str) - 是否安全和原因说明
        """
        if not sql_query or not isinstance(sql_query, str):
            return True, ""

        # 移除SQL注释
        # 移除 /* */ 风格注释
        sql_cleaned = re.sub(r'/\*[\s\S]*?\*/', '', sql_query)
        # 移除 -- 风格注释
        sql_cleaned = re.sub(r'--[^\n]*', '', sql_cleaned)

        # 转换为大写进行比较
        sql_upper = sql_cleaned.upper()

        # 定义危险操作关键词
        dangerous_patterns = [
            r'\bINSERT\b',
            r'\bUPDATE\b',
            r'\bDELETE\b',
            r'\bDROP\b',
            r'\bCREATE\b'
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, sql_upper):
                operation = pattern.strip(r'\b')
                return False, f"SQL包含危险操作: {operation}. 只允许执行SELECT查询。"

        return True, ""

    def _build_workflow(self) -> StateGraph:
        """构建LangGraph工作流（与原nl2sql_service.py逻辑一致）"""

        @track_node_progress("构建查询上下文")
        def build_context(state: TaskState) -> TaskState:
            """构建查询上下文 - 从向量数据库检索相关信息"""
            try:
                user_input = state.user_input
                filtered_vector_ids = getattr(state, 'filtered_vector_ids', None)

                # 使用向量检索构建上下文
                context = self.context_builder.retrieve_by_semantic_search(
                    user_input=user_input,
                    top_k=10,
                    allowed_vector_ids=filtered_vector_ids  # 传递过滤的向量库ID
                )

                state.task_context = context

                state.current_step_log = BaseNodeLog(
                    step="构建查询上下文",
                    input_data=user_input,
                    prompt="",
                    model_output=f"Context built with {len(context)} characters",
                    success=True
                )
                return state

            except Exception as e:
                logger.error(f"构建查询上下文失败: {e}")
                state.task_context = ""
                state.current_step_log = BaseNodeLog(
                    step="构建查询上下文",
                    input_data="",
                    prompt="",
                    model_output="",
                    success=False,
                    error=str(e)
                )
                return state

        @track_node_progress("检查输入清晰度")
        def validate_input(state: TaskState) -> TaskState:
            """验证输入是否清晰，如果不清晰则生成澄清选项"""
            try:
                user_input = state.user_input
                flow_type = getattr(state, 'flow_type', 'fast')
                sql_query = getattr(state, 'sql_query', '')

                # 确定验证类型
                if flow_type == 'thorough' and sql_query:
                    # thorough流程：验证SQL和输入是否匹配
                    step_name = "SQL验证"
                    input_for_validation = f"user:{user_input}\nsql:{sql_query}"
                else:
                    # fast流程或第一次验证：验证输入清晰度
                    step_name = "处理输入"
                    input_for_validation = user_input

                # 使用新的验证方法，支持生成澄清选项
                validation_result = self.llm_service.validate_input_clarity_with_options(
                    input_messages=state.messages,
                    user_input=user_input,
                    context=state.task_context,
                    sql_query=sql_query if sql_query else "",
                    flow_type=flow_type
                )

                state.is_clear = validation_result.get("is_clear", False)
                state.clear_check_details = {
                    "details": validation_result.get("details", ""),
                    "suggestions": validation_result.get("suggestions", []),
                    "confidence": validation_result.get("confidence", 0.0),
                    "clarification_options": validation_result.get("clarification_options", []),
                    "clarification_question": validation_result.get("clarification_question", "")
                }
                
                # 如果输入不清晰且有澄清选项，设置等待用户输入状态
                if not state.is_clear and validation_result.get("clarification_options"):
                    state.waiting_for_user_input = True

                    # 设置返回节点 - 根据您的反馈，thorough流程回到generate_sql
                    if flow_type == 'thorough':
                        state.return_to_node = "generate_sql"
                    else:
                        state.return_to_node = "validate_input"
                    
                    # 更新状态为等待用户输入
                    state.status = "waiting_for_input"
                    
                state.current_step_log = BaseNodeLog(
                    step=step_name,
                    input_data=input_for_validation,
                    prompt="",
                    model_output=f"Clear: {state.is_clear}",
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
                        input_messages=state.messages,
                        previous_sql=previous_sql,
                        error_message=error_message,
                        context=state.task_context,
                    )
                    step_name = "SQL重试生成"
                else:
                    result = self.llm_service.generate_sql(
                        user_input=user_input,
                        input_messages=state.messages,
                        context=state.task_context,
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

        @track_node_progress("SQL安全校验")
        def validate_sql_safety(state: TaskState) -> TaskState:
            """验证SQL的安全性 - 检查是否包含危险操作

            失败时设置error_message，让should_retry函数决定是否重试
            """
            try:
                sql_query = getattr(state, 'sql_query', '')
                if not sql_query:
                    state.error_message = "没有生成SQL"
                    state.current_step_log = BaseNodeLog(
                        step="SQL安全校验",
                        input_data="",
                        prompt="",
                        model_output="",
                        success=False,
                        error="没有生成SQL"
                    )
                    return state

                # 检查SQL安全性
                is_safe, reason = self._is_sql_safe(sql_query)

                if is_safe:
                    state.error_message = None  # 清除之前的错误
                    state.current_step_log = BaseNodeLog(
                        step="SQL安全校验",
                        input_data=sql_query,
                        prompt="",
                        model_output="SQL安全检查通过",
                        success=True
                    )
                else:
                    state.error_message = reason  # 设置错误，让should_retry处理
                    state.current_step_log = BaseNodeLog(
                        step="SQL安全校验",
                        input_data=sql_query,
                        prompt="",
                        model_output="",
                        success=False,
                        error=reason
                    )
                    logger.warning(f"SQL安全检查失败: {reason}")

                return state

            except Exception as e:
                logger.error(f"SQL安全校验失败: {e}")
                state.error_message = str(e)
                state.current_step_log = BaseNodeLog(
                    step="SQL安全校验",
                    input_data="",
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
                    result = self.db_service.execute_query(sql_query)
                    state.execution_result = result
                    state.error_message = None
                    state.current_step_log = BaseNodeLog(
                        step="执行SQL",
                        input_data=sql_query,
                        prompt="",
                        model_output=f"Success: {len(state.execution_result) if state.execution_result else 0} rows",
                        success=True
                    )

                    # 如果有Training Service，记录成功的结果
  
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
                        input_messages=state.messages,
                        sql_query=sql_query,
                        user_input=user_input,
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
            return flow_type  # 统一先构建上下文

        def route_after_validation(state: TaskState) -> str:
            """验证后的路由逻辑"""
            # 如果等待用户输入，暂停工作流
            if getattr(state, 'waiting_for_user_input', False):
                return "wait_for_user_input"
            
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

        def route_after_sql_safety_check(state: TaskState) -> str:
            """SQL安全校验后的路由逻辑"""
            error_message = getattr(state, 'error_message', None)

            if error_message:
                # 安全检查失败 -> 判断是否可以重试
                retry_count = getattr(state, 'retry_count', 0)
                max_retries = getattr(state, 'max_retries', 5)

                if retry_count < max_retries:
                    # 可以重试 -> 增加计数后回到generate_sql
                    state.retry_count = retry_count + 1
                    return "generate_sql"
                else:
                    # 超过重试次数 -> 结束
                    return "end_with_error"

            # 安全检查通过 -> 继续下一步
            flow_type = getattr(state, 'flow_type', 'fast')
            if flow_type == 'fast':
                # fast流程：直接执行
                return "execute_sql"
            else:
                # thorough流程：验证清晰度
                return "validate_input"

        def execute_sql_should_retry(state: TaskState) -> str:
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

        @track_node_progress("等待用户输入")
        def wait_for_user_input(state: TaskState) -> TaskState:
            """等待用户输入的节点 - 使用interrupt机制"""
            # 检查是否有用户澄清输入
            # user_clarification = getattr(state, 'user_clarification', '')
            # if user_clarification:
            #     # 有用户输入，更新用户输入内容并继续
            #     state.user_input = state.user_input + user_clarification
            #     state.waiting_for_user_input = False
            #     state.status = "running"
            #     logger.info(f"收到用户澄清输入: {user_clarification[:50]}...")
            # else:
            #     # 没有用户输入，设置等待状态并中断
            #     state.waiting_for_user_input = True
            #     state.status = "waiting_for_input"
            #     logger.info("等待用户澄清输入...")
                
            #     # 使用LangGraph的interrupt_before机制
            #     from langgraph.graph import interrupt_before
            #     # 这个调用会在节点执行前中断工作流
            #     interrupt_before(["validate_input", "generate_sql"])
            from langgraph.types import Command, interrupt
            interrupt("等待用户输入")
            # state.user_input = state.user_input + "用户澄清：" + interrupt("等待用户输入")
            # state.waiting_for_user_input = False
            # state.status = "running"
            
            return state

        # 创建检查点保存器，用于支持中断和恢复
        checkpoint_saver = MemorySaver()
        
        # 构建工作流图
        workflow = StateGraph(TaskState)

        # 添加节点
        workflow.add_node("build_context", build_context)
        workflow.add_node("validate_input", validate_input)
        workflow.add_node("wait_for_user_input", wait_for_user_input)  # 新增
        workflow.add_node("generate_sql", generate_sql)
        workflow.add_node("validate_sql_safety", validate_sql_safety)
        workflow.add_node("execute_sql", execute_sql)
        workflow.add_node("explain_result", explain_result)

        # 添加边
        workflow.set_entry_point("build_context")

        # build_context -> validate_input
        workflow.add_conditional_edges(
            "build_context",
            route_by_flow_type,
            {
                "fast": "validate_input",
                "thorough": "generate_sql"
            }
        )

        # validate_input的路由
        workflow.add_conditional_edges(
            "validate_input",
            route_after_validation,
            {
                "wait_for_user_input": "wait_for_user_input",  # 新增
                "generate_sql": "generate_sql",
                "execute_sql": "execute_sql",
                "failed": END
            }
        )
        
        # wait_for_user_input 的路由 - 根据return_to_node决定下一步
        def route_after_user_input(state: TaskState) -> str:
            """用户输入后的路由逻辑"""
            return_to_node = getattr(state, 'return_to_node', 'validate_input')
            flow_type = getattr(state, 'flow_type', 'fast')
            
            # 根据流程类型和返回节点决定下一步
            if return_to_node == "generate_sql":
                return "generate_sql"
            elif return_to_node == "validate_input":
                return "validate_input"
            else:
                # 默认根据流程类型决定
                if flow_type == 'fast':
                    return "validate_input"
                else:
                    return "generate_sql"
        
        # 添加wait_for_user_input的路由
        workflow.add_conditional_edges(
            "wait_for_user_input",
            route_after_user_input,
            {
                "validate_input": "validate_input",
                "generate_sql": "generate_sql"
            }
        )

        # generate_sql的路由 - 两种流程都先进行SQL安全校验
        workflow.add_edge("generate_sql", "validate_sql_safety")

        # validate_sql_safety的路由 - SQL安全校验后的分支
        workflow.add_conditional_edges(
            "validate_sql_safety",
            route_after_sql_safety_check,
            {
                "generate_sql": "generate_sql",  # 重试：回到SQL生成
                "end_with_error": END,  # 超过重试次数：结束
                "execute_sql": "execute_sql",  # fast流程：执行SQL
                "validate_input": "validate_input"  # thorough流程：验证清晰度
            }
        )

        # execute_sql的路由（重试逻辑）
        workflow.add_conditional_edges(
            "execute_sql",
            execute_sql_should_retry,
            {
                "retry": "generate_sql",
                "success": "explain_result",
                "failed": "explain_result"
            }
        )

        # explain_result到结束
        workflow.add_edge("explain_result", END)

        # 获取追踪处理器
        tracing_handler = get_tracing_handler()

        # 编译工作流，添加检查点支持
        if tracing_handler is None:
            graph = workflow.compile(checkpointer=checkpoint_saver)
        else:
            graph = workflow.compile(
                checkpointer=checkpoint_saver,
            ).with_config({"callbacks": [tracing_handler]})

        # 绘制流程图依赖外网环境
        # png_bytes = graph.get_graph().draw_mermaid_png()
        # with open("nlquery_graph.png", "wb") as f:
        #     f.write(png_bytes)

        return graph

    def write_db_after_workflow(self, result, tracker, task_id):
        # 更新追踪器 - 同步调用，不需要 await
        # 注意：不在这里写入步骤日志，由上层 async_query_service 在任务结束时一次性写入
        logger.info("流程执行结束，开始更新状态")
        error_msg = getattr(result, 'error_message', None)

        if error_msg:
            tracker.update_task_progress(
                task_id=task_id,
                progress=100,
                step_name="查询失败",
                final_status="failed",
            )
        else:
            tracker.update_task_progress(
                task_id=task_id,
                progress=100,
                step_name="查询完成",
                final_status="success",
            )

    def resume_workflow_with_interrupt(self, task_id: str, clarification_input: str, tracker: Optional[Any] = None) -> Dict[str, Any]:
        """使用interrupt机制恢复工作流执行"""
        try:
            from services.tracking_service.tracker_cache import tracker_cache
            cached_state = tracker_cache.get_task_state(task_id)
            resume_state = TaskState(**cached_state)

            new_input = f"{resume_state.user_input} 用户补充澄清：{clarification_input}"

            resume_state.user_input = new_input
            resume_state.waiting_for_user_input = False
            resume_state.status = "running"

            cached_state.update({
                'user_input': new_input,
                'waiting_for_user_input': False,
                'status': "running"
            })
            
            config = {"configurable": {"thread_id": task_id}}
                
            result = self.workflow.invoke(resume_state, config=config)

            # 将结果转换为TaskState对象（如果是dict）
            if isinstance(result, dict):
                result = TaskState(**result)

            self.write_db_after_workflow(result, tracker, task_id)
            error_msg = getattr(result, 'error_message', None)
            user_input = getattr(result, 'user_input', None)
            
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

    def process_query(self, user_input: str, task_id: str, max_retries: int = 5,
                     operator: str = "api_user", flow_type: str = "fast",
                     tracker: Optional[Any] = None,
                     filtered_vector_ids: Optional[list] = None) -> Dict[str, Any]:
        """兼容旧API的处理查询方法（用于AsyncQueryService）

        Args:
            user_input: 用户输入
            task_id: 任务ID（用于追踪）
            max_retries: 最大重试次数
            operator: 操作者
            flow_type: 流程类型
            tracker: 操作追踪器
            filtered_vector_ids: 可选的向量库ID列表，用于精准过滤检索结果

        Returns:
            查询结果字典
        """
        try:
            logger.info(f"查询流程: 任务ID={task_id}, 用户输入={user_input[:50]}, 流程类型={flow_type}")

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

            # 添加过滤的向量库ID
            task_state.filtered_vector_ids = filtered_vector_ids or []

            tracker.create_task(task_state)

            # 执行工作流，使用线程ID作为检查点ID
            config = {"configurable": {"thread_id": task_id}}
            
            result = self.workflow.invoke(task_state, config=config)

            # 将结果转换为TaskState对象（如果是dict）
            if isinstance(result, dict):
                result = TaskState(**result)

            error_msg = getattr(result, 'error_message', None)

            waiting_for_user_input = getattr(result, 'waiting_for_user_input', False)
            if waiting_for_user_input:
                logger.info(f"查询流程中断，等待用户输入: ---")
                return {
                    "success": False,
                    "user_input": user_input,
                    "is_waiting_for_input": True,
                    "error": "等待用户澄清输入"
                }

            self.write_db_after_workflow(result, tracker, task_id)

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

    def get_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        stats = {}

        # 获取向量库统计
        try:
            count = self.vector_store.count()
            stats["vector_store"] = {"documents": count}
        except:
            stats["vector_store"] = {"documents": 0}

        return stats
