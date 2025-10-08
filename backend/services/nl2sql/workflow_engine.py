"""
LangGraph工作流引擎实现
基于LangGraph的NL2SQL查询处理工作流
"""
import asyncio
import uuid
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import HumanMessage, AIMessage

from utils.logger import get_logger
from utils.exceptions import NLQueryException, LLMException
from config.settings import get_settings
from models.nlquery_models import TaskStatusEnum, NodeStatusEnum, NodeTypeEnum
from services.websocket.manager import connection_manager

logger = get_logger(__name__)


class WorkflowState(TypedDict):
    """工作流状态定义"""
    # 基础信息
    task_id: str
    user_id: int
    user_question: str
    selected_theme_id: Optional[int]
    selected_table_ids: Optional[List[int]]
    
    # 执行状态
    current_step: str
    progress_percentage: int
    error_message: Optional[str]
    error_code: Optional[str]
    
    # SQL相关
    generated_sql: Optional[str]
    final_sql: Optional[str]
    sql_validation_result: Optional[Dict[str, Any]]
    
    # 执行结果
    execution_result: Optional[Dict[str, Any]]
    result_row_count: Optional[int]
    result_columns: Optional[List[str]]
    result_data: Optional[List[List[Any]]]
    
    # LLM相关
    llm_messages: List[Dict[str, str]]
    llm_tokens_used: int
    
    # 节点执行记录
    node_execution_log: List[Dict[str, Any]]
    
    # 重试控制
    retry_count: int
    max_retries: int


class WorkflowEngine:
    """LangGraph工作流引擎"""
    
    def __init__(self):
        self.settings = get_settings()
        self.graph = None
        self._build_workflow()
    
    def _build_workflow(self):
        """构建工作流图"""
        workflow = StateGraph(WorkflowState)
        
        # 添加节点
        workflow.add_node("validate_input", self._validate_input_node)
        workflow.add_node("generate_sql", self._generate_sql_node)
        workflow.add_node("validate_sql", self._validate_sql_node)
        workflow.add_node("execute_sql", self._execute_sql_node)
        workflow.add_node("process_result", self._process_result_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        # 设置入口点
        workflow.set_entry_point("validate_input")
        
        # 定义边（流程控制）
        workflow.add_edge("validate_input", "generate_sql")
        
        # SQL生成后的条件分支
        workflow.add_conditional_edges(
            "generate_sql",
            self._should_validate_sql,
            {
                "validate": "validate_sql",
                "error": "handle_error",
                "execute": "execute_sql"
            }
        )
        
        # SQL验证后的条件分支
        workflow.add_conditional_edges(
            "validate_sql",
            self._should_execute_sql,
            {
                "execute": "execute_sql",
                "regenerate": "generate_sql",
                "error": "handle_error"
            }
        )
        
        # SQL执行后的条件分支
        workflow.add_conditional_edges(
            "execute_sql",
            self._should_process_result,
            {
                "process": "process_result",
                "retry": "generate_sql",
                "error": "handle_error"
            }
        )
        
        # 结果处理和错误处理都结束流程
        workflow.add_edge("process_result", END)
        workflow.add_edge("handle_error", END)
        
        # 编译图
        self.graph = workflow.compile()
        logger.info("LangGraph工作流图构建完成")
    
    async def execute_workflow(self, initial_state: WorkflowState) -> WorkflowState:
        """执行工作流"""
        try:
            logger.info(f"开始执行工作流，任务ID: {initial_state['task_id']}")
            
            # 初始化状态
            initial_state.update({
                "current_step": "开始处理",
                "progress_percentage": 0,
                "llm_messages": [],
                "llm_tokens_used": 0,
                "node_execution_log": [],
                "retry_count": 0,
                "max_retries": self.settings.MAX_RETRY_COUNT
            })
            
            # 发送初始通知
            await self._notify_progress(initial_state)
            
            # 执行工作流
            final_state = await self._run_workflow(initial_state)
            
            # 发送完成通知
            await self._notify_completion(final_state)
            
            logger.info(f"工作流执行完成，任务ID: {final_state['task_id']}")
            return final_state
            
        except Exception as e:
            logger.error(f"工作流执行失败: {e}", exc_info=True)
            initial_state.update({
                "current_step": "执行失败",
                "progress_percentage": 0,
                "error_message": str(e),
                "error_code": "WORKFLOW_ERROR"
            })
            
            # 发送错误通知
            await self._notify_error(initial_state)
            
            return initial_state
    
    async def _run_workflow(self, state: WorkflowState) -> WorkflowState:
        """运行工作流（异步适配）"""
        # 由于LangGraph可能不完全支持异步，这里做适配处理
        try:
            # 同步执行图
            result = self.graph.invoke(state)
            return result
        except Exception as e:
            logger.error(f"工作流图执行失败: {e}")
            raise NLQueryException(f"工作流执行失败: {e}")
    
    # ========== WebSocket通知方法 ==========
    
    async def _notify_progress(self, state: WorkflowState):
        """发送进度通知"""
        try:
            await connection_manager.notify_query_progress(
                state["task_id"],
                {
                    "current_step": state.get("current_step", ""),
                    "progress_percentage": state.get("progress_percentage", 0) / 100.0,
                    "generated_sql": state.get("generated_sql"),
                    "sql_confidence": state.get("sql_validation_result", {}).get("confidence"),
                    "logs": self._format_logs(state)
                }
            )
        except Exception as e:
            logger.warning(f"发送进度通知失败: {e}")
    
    async def _notify_completion(self, state: WorkflowState):
        """发送完成通知"""
        try:
            await connection_manager.notify_query_completed(
                state["task_id"],
                {
                    "generated_sql": state.get("generated_sql"),
                    "result": {
                        "columns": state.get("result_columns", []),
                        "rows": state.get("result_data", []),
                        "total_count": state.get("result_row_count"),
                        "execution_time_ms": state.get("execution_result", {}).get("execution_time_ms")
                    },
                    "final_step": state.get("current_step"),
                    "total_tokens": state.get("llm_tokens_used", 0)
                }
            )
        except Exception as e:
            logger.warning(f"发送完成通知失败: {e}")
    
    async def _notify_error(self, state: WorkflowState):
        """发送错误通知"""
        try:
            await connection_manager.notify_query_error(
                state["task_id"],
                {
                    "error_message": state.get("error_message", ""),
                    "error_code": state.get("error_code", ""),
                    "failed_step": state.get("current_step", ""),
                    "logs": self._format_logs(state)
                }
            )
        except Exception as e:
            logger.warning(f"发送错误通知失败: {e}")
    
    def _format_logs(self, state: WorkflowState) -> List[Dict[str, Any]]:
        """格式化日志信息"""
        logs = []
        for log_entry in state.get("node_execution_log", []):
            logs.append({
                "timestamp": log_entry.get("timestamp"),
                "level": log_entry.get("status", "INFO").upper(),
                "message": f"{log_entry.get('node_name', '')}: {log_entry.get('message', '')}"
            })
        return logs
    
    # ========== 工作流节点实现 ==========
    
    async def _validate_input_node(self, state: WorkflowState) -> WorkflowState:
        """输入验证节点"""
        try:
            self._log_node_start(state, NodeTypeEnum.SQL_GENERATION, "输入验证")
            
            # 验证用户问题
            if not state.get("user_question", "").strip():
                raise NLQueryException("用户问题不能为空")
            
            # 验证用户ID
            if not state.get("user_id"):
                raise NLQueryException("用户ID不能为空")
            
            # 验证主题选择（如果有）
            if state.get("selected_theme_id"):
                # TODO: 验证主题是否存在且用户有权限访问
                pass
            
            state.update({
                "current_step": "输入验证完成",
                "progress_percentage": 10
            })
            
            # 发送进度通知
            await self._notify_progress(state)
            
            self._log_node_success(state, "输入验证", "输入验证通过")
            return state
            
        except Exception as e:
            return self._log_node_error(state, "输入验证", str(e))
    
    async def _generate_sql_node(self, state: WorkflowState) -> WorkflowState:
        """SQL生成节点"""
        try:
            self._log_node_start(state, NodeTypeEnum.SQL_GENERATION, "SQL生成")
            
            # 构建提示词
            prompt = await self._build_sql_prompt(state)
            
            # 调用LLM生成SQL
            generated_sql = await self._call_llm_for_sql(prompt, state)
            
            # 清理和格式化SQL
            final_sql = self._clean_sql(generated_sql)
            
            state.update({
                "generated_sql": generated_sql,
                "final_sql": final_sql,
                "current_step": "SQL生成完成",
                "progress_percentage": 40
            })
            
            self._log_node_success(state, "SQL生成", f"生成SQL: {final_sql[:100]}...")
            return state
            
        except Exception as e:
            return self._log_node_error(state, "SQL生成", str(e))
    
    async def _validate_sql_node(self, state: WorkflowState) -> WorkflowState:
        """SQL验证节点"""
        try:
            self._log_node_start(state, NodeTypeEnum.SQL_VALIDATION, "SQL验证")
            
            sql = state.get("final_sql")
            if not sql:
                raise NLQueryException("没有SQL需要验证")
            
            # 基础SQL语法检查
            validation_result = await self._validate_sql_syntax(sql)
            
            # 安全性检查
            security_result = await self._validate_sql_security(sql)
            
            # 权限检查
            permission_result = await self._validate_sql_permissions(sql, state)
            
            # 合并验证结果
            combined_result = {
                "syntax_valid": validation_result["valid"],
                "security_valid": security_result["valid"],
                "permission_valid": permission_result["valid"],
                "errors": validation_result.get("errors", []) + 
                         security_result.get("errors", []) + 
                         permission_result.get("errors", [])
            }
            
            state.update({
                "sql_validation_result": combined_result,
                "current_step": "SQL验证完成",
                "progress_percentage": 60
            })
            
            if combined_result["syntax_valid"] and combined_result["security_valid"] and combined_result["permission_valid"]:
                self._log_node_success(state, "SQL验证", "SQL验证通过")
            else:
                self._log_node_error(state, "SQL验证", f"SQL验证失败: {combined_result['errors']}")
            
            return state
            
        except Exception as e:
            return self._log_node_error(state, "SQL验证", str(e))
    
    async def _execute_sql_node(self, state: WorkflowState) -> WorkflowState:
        """SQL执行节点"""
        try:
            self._log_node_start(state, NodeTypeEnum.SQL_EXECUTION, "SQL执行")
            
            sql = state.get("final_sql")
            if not sql:
                raise NLQueryException("没有SQL需要执行")
            
            # 执行SQL查询
            from utils.database import query_engine_manager
            result = await query_engine_manager.execute_query(sql)
            
            # 处理结果
            state.update({
                "execution_result": result,
                "result_row_count": result.get("row_count", 0),
                "result_columns": result.get("columns", []),
                "result_data": result.get("rows", [])[:100],  # 只保存前100行
                "current_step": "SQL执行完成",
                "progress_percentage": 80
            })
            
            self._log_node_success(state, "SQL执行", f"查询成功，返回 {result.get('row_count', 0)} 行数据")
            return state
            
        except Exception as e:
            return self._log_node_error(state, "SQL执行", str(e))
    
    async def _process_result_node(self, state: WorkflowState) -> WorkflowState:
        """结果处理节点"""
        try:
            self._log_node_start(state, NodeTypeEnum.RESULT_PROCESSING, "结果处理")
            
            # 数据后处理（如脱敏、格式化等）
            processed_data = await self._post_process_data(
                state.get("result_data", []),
                state.get("result_columns", []),
                state
            )
            
            # 更新状态
            state.update({
                "result_data": processed_data,
                "current_step": "处理完成",
                "progress_percentage": 100
            })
            
            self._log_node_success(state, "结果处理", "结果处理完成")
            return state
            
        except Exception as e:
            return self._log_node_error(state, "结果处理", str(e))
    
    async def _handle_error_node(self, state: WorkflowState) -> WorkflowState:
        """错误处理节点"""
        try:
            self._log_node_start(state, NodeTypeEnum.ERROR_HANDLING, "错误处理")
            
            error_message = state.get("error_message", "未知错误")
            
            # 错误分类和处理建议
            error_suggestions = self._get_error_suggestions(error_message)
            
            state.update({
                "current_step": "错误处理完成",
                "progress_percentage": 0,
                "error_suggestions": error_suggestions
            })
            
            self._log_node_success(state, "错误处理", f"错误处理完成: {error_message}")
            return state
            
        except Exception as e:
            logger.error(f"错误处理节点失败: {e}")
            state.update({
                "error_message": f"错误处理失败: {e}",
                "current_step": "错误处理失败"
            })
            return state
    
    # ========== 条件判断函数 ==========
    
    def _should_validate_sql(self, state: WorkflowState) -> str:
        """判断是否需要验证SQL"""
        if state.get("error_message"):
            return "error"
        if state.get("final_sql"):
            return "validate"
        return "error"
    
    def _should_execute_sql(self, state: WorkflowState) -> str:
        """判断是否应该执行SQL"""
        validation_result = state.get("sql_validation_result", {})
        
        if state.get("error_message"):
            return "error"
        
        if (validation_result.get("syntax_valid") and 
            validation_result.get("security_valid") and 
            validation_result.get("permission_valid")):
            return "execute"
        
        # 如果验证失败且重试次数未超限，重新生成SQL
        if state.get("retry_count", 0) < state.get("max_retries", 3):
            state["retry_count"] = state.get("retry_count", 0) + 1
            return "regenerate"
        
        return "error"
    
    def _should_process_result(self, state: WorkflowState) -> str:
        """判断是否应该处理结果"""
        if state.get("error_message"):
            return "error"
        if state.get("execution_result"):
            return "process"
        
        # 如果执行失败且重试次数未超限，重试
        if state.get("retry_count", 0) < state.get("max_retries", 3):
            state["retry_count"] = state.get("retry_count", 0) + 1
            return "retry"
        
        return "error"
    
    # ========== 辅助方法 ==========
    
    def _log_node_start(self, state: WorkflowState, node_type: NodeTypeEnum, node_name: str):
        """记录节点开始执行"""
        log_entry = {
            "node_name": node_name,
            "node_type": node_type.value,
            "status": NodeStatusEnum.RUNNING.value,
            "start_time": datetime.now().isoformat(),
            "input_data": {}
        }
        
        if "node_execution_log" not in state:
            state["node_execution_log"] = []
        state["node_execution_log"].append(log_entry)
        
        logger.info(f"节点开始执行: {node_name}")
    
    def _log_node_success(self, state: WorkflowState, node_name: str, message: str):
        """记录节点执行成功"""
        if state.get("node_execution_log"):
            last_log = state["node_execution_log"][-1]
            if last_log["node_name"] == node_name:
                last_log.update({
                    "status": NodeStatusEnum.SUCCESS.value,
                    "end_time": datetime.now().isoformat(),
                    "output_message": message
                })
        
        logger.info(f"节点执行成功: {node_name} - {message}")
    
    def _log_node_error(self, state: WorkflowState, node_name: str, error_message: str) -> WorkflowState:
        """记录节点执行错误"""
        if state.get("node_execution_log"):
            last_log = state["node_execution_log"][-1]
            if last_log["node_name"] == node_name:
                last_log.update({
                    "status": NodeStatusEnum.FAILED.value,
                    "end_time": datetime.now().isoformat(),
                    "error_message": error_message
                })
        
        state.update({
            "error_message": error_message,
            "error_code": "NODE_ERROR"
        })
        
        logger.error(f"节点执行失败: {node_name} - {error_message}")
        return state
    
    async def _build_sql_prompt(self, state: WorkflowState) -> str:
        """构建SQL生成提示词"""
        # TODO: 实现完整的提示词构建逻辑
        user_question = state["user_question"]
        
        prompt = f"""
请根据用户问题生成相应的SQL查询语句。

用户问题: {user_question}

要求:
1. 生成的SQL必须是标准的SQL语法
2. 只返回SQL语句，不要其他解释
3. 确保SQL的安全性，避免注入攻击
4. 优化查询性能

SQL:
"""
        return prompt
    
    async def _call_llm_for_sql(self, prompt: str, state: WorkflowState) -> str:
        """调用LLM生成SQL"""
        try:
            # TODO: 实现实际的LLM调用逻辑
            # 这里先返回模拟的SQL
            await asyncio.sleep(1)  # 模拟LLM调用延迟
            
            # 模拟SQL生成
            if "用户" in state["user_question"]:
                mock_sql = "SELECT * FROM users LIMIT 10;"
            elif "订单" in state["user_question"]:
                mock_sql = "SELECT * FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) LIMIT 10;"
            else:
                mock_sql = "SELECT 1 as result;"
            
            # 更新token使用量
            state["llm_tokens_used"] = state.get("llm_tokens_used", 0) + 150
            
            return mock_sql
            
        except Exception as e:
            raise LLMException(f"LLM调用失败: {e}")
    
    def _clean_sql(self, sql: str) -> str:
        """清理和格式化SQL"""
        if not sql:
            return ""
        
        # 移除多余的空白字符
        sql = sql.strip()
        
        # 确保以分号结尾
        if not sql.endswith(';'):
            sql += ';'
        
        return sql
    
    async def _validate_sql_syntax(self, sql: str) -> Dict[str, Any]:
        """验证SQL语法"""
        try:
            # 基础语法检查
            if not sql or not sql.strip():
                return {"valid": False, "errors": ["SQL不能为空"]}
            
            # 检查危险关键词
            dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE"]
            sql_upper = sql.upper()
            
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    return {"valid": False, "errors": [f"不允许使用 {keyword} 操作"]}
            
            return {"valid": True, "errors": []}
            
        except Exception as e:
            return {"valid": False, "errors": [f"语法验证失败: {e}"]}
    
    async def _validate_sql_security(self, sql: str) -> Dict[str, Any]:
        """验证SQL安全性"""
        try:
            # 检查SQL注入模式
            injection_patterns = ["--", "/*", "*/", ";--", "' OR '1'='1"]
            
            for pattern in injection_patterns:
                if pattern in sql:
                    return {"valid": False, "errors": [f"检测到潜在的SQL注入风险: {pattern}"]}
            
            return {"valid": True, "errors": []}
            
        except Exception as e:
            return {"valid": False, "errors": [f"安全验证失败: {e}"]}
    
    async def _validate_sql_permissions(self, sql: str, state: WorkflowState) -> Dict[str, Any]:
        """验证SQL权限"""
        try:
            # TODO: 实现完整的权限验证逻辑
            # 这里先简单验证
            
            user_id = state.get("user_id")
            if not user_id:
                return {"valid": False, "errors": ["用户ID缺失"]}
            
            return {"valid": True, "errors": []}
            
        except Exception as e:
            return {"valid": False, "errors": [f"权限验证失败: {e}"]}
    
    async def _post_process_data(self, data: List[List[Any]], columns: List[str], state: WorkflowState) -> List[List[Any]]:
        """数据后处理"""
        try:
            # TODO: 实现数据脱敏、格式化等处理
            processed_data = data
            
            # 限制返回行数
            max_rows = self.settings.MAX_RESULT_ROWS
            if len(processed_data) > max_rows:
                processed_data = processed_data[:max_rows]
                logger.info(f"结果数据已截断至 {max_rows} 行")
            
            return processed_data
            
        except Exception as e:
            logger.error(f"数据后处理失败: {e}")
            return data
    
    def _get_error_suggestions(self, error_message: str) -> List[str]:
        """获取错误处理建议"""
        suggestions = []
        
        if "语法" in error_message:
            suggestions.append("请检查您的问题描述是否清晰明确")
            suggestions.append("尝试使用更简单的表达方式")
        
        if "权限" in error_message:
            suggestions.append("您可能没有访问相关数据的权限")
            suggestions.append("请联系管理员获取必要的权限")
        
        if "超时" in error_message:
            suggestions.append("查询可能涉及大量数据，请尝试缩小查询范围")
            suggestions.append("添加时间范围或其他过滤条件")
        
        if not suggestions:
            suggestions.append("请尝试重新描述您的查询需求")
            suggestions.append("或联系技术支持获取帮助")
        
        return suggestions