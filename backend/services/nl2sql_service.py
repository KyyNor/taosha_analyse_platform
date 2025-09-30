"""
自然语言转SQL服务 - LangGraph + Vanna 实现
"""

import hashlib
import json
from loguru import logger
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from pathlib import Path

# LangGraph imports
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

# Vanna imports
from vanna.openai import OpenAI_Chat
from vanna.chromadb import ChromaDB_VectorStore

# Local imports
from utils.config import settings
from services.database_service import get_database_service
from services.metadata_service import get_metadata_service, get_glossary_service, get_relation_field_config_service
from services.operation_tracking import track_operation, tracker, OperationStep


# 状态定义
class GraphState(TypedDict):
    """LangGraph状态定义"""
    user_input: str
    flow_type: str  # 新增：流程类型 ("fast" 或 "thorough")
    clear_check_details: Dict[str, Any]
    is_clear: bool
    sql_query: str
    execution_result: Optional[pd.DataFrame]
    sql_explanation: Optional[str]
    nl_diff_analysis: Optional[Dict[str, Any]]
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    logs: List[Dict[str, Any]]

@dataclass
class NL2SQLLog:
    """日志记录结构"""
    step: str
    timestamp: datetime
    input_data: str
    prompt: str
    model_output: str
    success: bool
    error: Optional[str] = None

class TaoshaVanna(ChromaDB_VectorStore, OpenAI_Chat):
    """自定义Vanna实现"""
    
    def __init__(self, config=None):
        # 初始化ChromaDB
        chroma_path = settings.chromadb_path
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        
        ChromaDB_VectorStore.__init__(self, config={'path': chroma_path})
        
        # 创建 OpenAI 客户端配置
        openai_config = {
            'model': settings.openai_model,
            'temperature': settings.openai_temperature,

        }
        client = None
        
        # 只有当 API key 存在时才设置
        if settings.openai_api_key:
            openai_config['api_key'] = settings.openai_api_key
            
        # 如果有自定义 base_url，需要传递 OpenAI 客户端实例
        if settings.openai_base_url:
            try:
                from openai import OpenAI
                client = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url
                )
            except ImportError:
                logger.warning("OpenAI package not available, using default configuration")
        
        OpenAI_Chat.__init__(self, client=client, config=openai_config)
        
        self.training_hash = None
        logger.info("TaoshaVanna initialized")
    
    def log_interaction(self, step: str, input_data: str, prompt: str, 
                       model_output: str, success: bool, error: str = None):
        """记录交互日志"""
        import traceback
        import inspect
        
        # 获取调用者信息
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        caller_file = caller_frame.f_code.co_filename
        caller_line = caller_frame.f_lineno
        caller_function = caller_frame.f_code.co_name
        
        log_entry = {
            'step': step,
            'timestamp': datetime.now().isoformat(),
            'input_data': input_data,
            'prompt': prompt,
            'model_output': model_output,
            'success': success,
            'error': error,
            'caller_info': {
                'file': caller_file,
                'line': caller_line,
                'function': caller_function
            }
        }
        
        # 同时记录到新的追踪系统
        if tracker.current_session:
            operation_step = OperationStep(
                session_id=tracker.current_session,
                step_sequence=0,  # 自动分配
                step_name=step,
                input_data=input_data[:1000],  # 限制长度
                call_method=f"{caller_function}",
                output_data=model_output[:1000],
                error_message=error,
                success=success,
                metadata={'caller_info': log_entry['caller_info']}
            )
            
            # 提取SQL（如果有）
            if 'sql' in step.lower() and model_output:
                from services.operation_tracking import extract_sql_from_text
                operation_step.generated_sql = extract_sql_from_text(model_output)
            
            tracker.log_step(operation_step)
        
        logger.debug(f"[{step}] Input: {input_data}")
        logger.debug(f"[{step}] Prompt: {prompt}...")
        logger.debug(f"[{step}] Output: {model_output}")
        
        if error:
            logger.error(f"[{step}] Error in {caller_function}() at line {caller_line}: {error}")
            # 如果有活跃的异常，打印完整的traceback
            if hasattr(error, '__traceback__'):
                logger.error(f"[{step}] Full traceback:\n{''.join(traceback.format_tb(error.__traceback__))}")
        
        return log_entry

class NL2SQLService:
    """自然语言转SQL服务"""
    
    def __init__(self):
        self.vanna = TaoshaVanna()
        self.metadata_service = get_metadata_service()
        self.glossary_service = get_glossary_service()
        self.relation_config_service = get_relation_field_config_service()
        self.db_service = get_database_service()

        # 构建统一的LangGraph工作流
        self.workflow = self._build_workflow()

        logger.info("NL2SQL Service initialized")
    
    def _build_workflow(self) -> StateGraph:
        """构建统一的LangGraph工作流，支持多种流程类型"""
        
        def check_training_needed(state: GraphState) -> GraphState:
            """检查是否需要重新训练Vanna"""
            logs = state.get('logs', [])
            
            # 需要重新训练
            self._train_vanna()
            log_entry = self.vanna.log_interaction(
                step="training_check",
                input_data="metadata/glossary check",
                prompt="",
                model_output="training completed",
                success=True
            )
            logs.append(log_entry)
            
            state['logs'] = logs
            return state
        
        def validate_input_clarity(state: GraphState) -> GraphState:
            """验证输入是否清晰，支持两种模式：纯输入验证 和 SQL+输入匹配验证"""
            user_input = state['user_input']
            sql_query = state.get('sql_query', '')  # 可能存在也可能不存在
            flow_type = state.get('flow_type', 'fast')
            logs = state.get('logs', [])

            # 检查API配置
            if not settings.openai_api_key:
                logger.warning("OpenAI API key not configured, skipping input validation")
                state['is_clear'] = True
                state['processed_input'] = user_input
                state['logs'] = logs
                return state

            # 根据是否有SQL选择验证模式
            if sql_query and flow_type == 'thorough':
                # 深度流程：验证用户输入+SQL匹配度
                current_date = datetime.now().strftime("%Y-%m-%d")
                validation_prompt = f"""
请结合生成的SQL查询，判断用户原始查询是否足够清晰，SQL是否准确反映了用户需求。

用户原始查询: {user_input}

生成的SQL查询: {sql_query}

可用的表结构:
{self._get_table_info_text()}

可用的术语:
{self._get_glossary_text()}

字段关联配置:
{self._get_relation_config_text()}

请严格按照以下JSON格式返回结果，不要添加任何其他文字：
{{
    "is_clear": true/false,
    "reason": "判断的详细原因，结合SQL生成质量来评估",
    "sql_match": true/false,
    "suggestions": ["如果不够清晰，请提供3个具体的可查询示例"]
}}

注意：
1. 不仅要评估用户输入的清晰度，还要评估SQL是否准确反映了用户需求
2. 如果SQL很好地满足了用户需求，即使输入不够完美也应该认为is_clear=true
3. 如果SQL与用户需求有偏差，应该给出具体建议
"""
                step_name = "sql_based_validation"
            else:
                # 快速流程：只验证用户输入清晰度
                current_date = datetime.now().strftime("%Y-%m-%d")
                validation_prompt = f"""
请判断以下用户查询是否足够清晰，可以转换为SQL查询。

当前日期: {current_date}

用户查询: {user_input}

可用的表结构:
{self._get_table_info_text()}

可用的术语:
{self._get_glossary_text()}

字段关联配置:
{self._get_relation_config_text()}

请严格按照以下JSON格式返回结果，不要添加任何其他文字：
{{
    "is_clear": true/false,
    "reason": "判断的详细原因",
    "suggestions": ["如果不清晰，请提供3个具体的可查询示例，直接使用表中的字段名和具体时间范围，例如：'最近30天手机销量统计'、'2024年1月各地区销售额对比'"]
}}

注意：suggestions中应该是完整的、可以直接查询的问题示例，而不是修改建议。基于用户的模糊查询，结合可用的表结构，生成具体可执行的查询示例。
"""
                step_name = "input_validation"
            
            try:
                # 使用正确的消息格式
                messages = [{"role": "user", "content": validation_prompt}]
                response = self.vanna.submit_prompt(messages)
                
                # 确保response是字符串
                if not isinstance(response, str):
                    logger.warning(f"Unexpected response type: {type(response)}, content: {response}")
                    response = str(response) if response else ""
                
                # 解析JSON响应
                try:
                    # 尝试解析JSON
                    validation_result = json.loads(response.strip())
                    is_clear = validation_result.get('is_clear', True)
                    reason = validation_result.get('reason', '')
                    suggestions = validation_result.get('suggestions', [])

                    # 构建更详细的处理输入
                    clear_check_details = {
                        'is_clear': is_clear,
                        'reason': reason,
                        'suggestions': suggestions
                    }

                    # 如果是SQL验证模式，添加额外的字段
                    if sql_query and flow_type == 'thorough':
                        clear_check_details['sql_match'] = validation_result.get('sql_match', True)
                        clear_check_details['validation_type'] = 'sql_based'
                    else:
                        clear_check_details['validation_type'] = 'input_only'

                except json.JSONDecodeError as json_error:
                    clear_check_details = {
                        'is_clear': False,
                        'reason': f"无法解析模型响应为JSON: {str(json_error)}",
                        'suggestions': [],
                        'validation_type': step_name
                    }

                log_entry = self.vanna.log_interaction(
                    step=step_name,
                    input_data=user_input if not sql_query else f"user:{user_input}\nsql:{sql_query}",
                    prompt=validation_prompt,
                    model_output=response,
                    success=True
                )
                logs.append(log_entry)
                
                state['is_clear'] = is_clear
                state['processed_input'] = clear_check_details
                state['clear_check_details'] = clear_check_details
                state['logs'] = logs
                
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"Input validation failed with traceback:\n{error_traceback}")
                
                log_entry = self.vanna.log_interaction(
                    step=step_name,
                    input_data=user_input if not sql_query else f"user:{user_input}\nsql:{sql_query}",
                    prompt=validation_prompt,
                    model_output="",
                    success=False,
                    error=f"{str(e)}\nTraceback:\n{error_traceback}"
                )
                logs.append(log_entry)
                state['is_clear'] = False
                state['error_message'] = f"输入验证失败: {str(e)}"
                state['logs'] = logs
            
            return state
        
        def generate_sql(state: GraphState) -> GraphState:
            """生成SQL查询（包含错误重试逻辑）"""
            user_input = state['user_input']
            logs = state.get('logs', [])
            error_message = state.get('error_message')
            previous_sql = state.get('sql_query', '')
            retry_count = state.get('retry_count', 0)
            
            # 构建输入内容：如果有错误信息，则包含错误反馈
            step_name = "sql_generation"
            
            
            # 这是重试情况，增强输入信息
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            tips = ""
            error_info = ""
            if error_message and previous_sql:
                step_name = "sql_retry"
                error_info = f"之前生成的SQL执行失败，SQL: {previous_sql}，错误信息: {error_message}"
                tips = "请生成一个新的SQL查询，避免之前的错误。"
            
            query_input = f"""原始用户查询: {user_input}
当前日期: {current_date}

{error_info}

重要提示:
1. 字段的存储类型和业务类型可能不同，数值比较时请使用CAST转换为业务类型
2. 关联不同表的字段时，请根据关联配置进行适当转换
3. 所有表都需要使用别名，从t1开始，t1、t2、t3依次递增
4. 所有字段都需要使用完整引用，例如t1.cust_no，不允许只写字段名
{tips}"""

            
            try:
                # 使用Vanna生成SQL（会自动检索向量数据库上下文）
                sql_query = self.vanna.generate_sql(query_input)
                
                log_entry = self.vanna.log_interaction(
                    step=step_name,
                    input_data=query_input,
                    prompt="vanna.generate_sql",
                    model_output=sql_query,
                    success=True
                )
                logs.append(log_entry)
                
                state['sql_query'] = sql_query
                state['error_message'] = None  # 清除错误信息
                state['logs'] = logs
                
            except Exception as e:
                log_entry = self.vanna.log_interaction(
                    step=step_name,
                    input_data=query_input,
                    prompt="vanna.generate_sql",
                    model_output="",
                    success=False,
                    error=str(e)
                )
                logs.append(log_entry)
                
                if retry_count > 0:
                    state['error_message'] = f"SQL重试失败: {str(e)}"
                else:
                    state['error_message'] = f"SQL生成失败: {str(e)}"
                state['logs'] = logs
            
            return state
        
        def execute_sql(state: GraphState) -> GraphState:
            """执行SQL查询"""
            sql_query = state.get('sql_query', '')
            logs = state.get('logs', [])
            
            if not sql_query:
                state['error_message'] = "没有可执行的SQL查询"
                return state
            
            try:
                # 执行SQL查询
                result = self.db_service.execute_query(sql_query)
                
                log_entry = self.vanna.log_interaction(
                    step="sql_execution",
                    input_data=sql_query,
                    prompt="database.execute_query",
                    model_output=f"返回 {len(result)} 行数据",
                    success=True
                )
                logs.append(log_entry)
                
                state['execution_result'] = result
                state['logs'] = logs
                
            except Exception as e:
                log_entry = self.vanna.log_interaction(
                    step="sql_execution",
                    input_data=sql_query,
                    prompt="database.execute_query",
                    model_output="",
                    success=False,
                    error=str(e)
                )
                logs.append(log_entry)
                
                # 增加重试计数
                retry_count = state.get('retry_count', 0) + 1
                state['retry_count'] = retry_count
                state['error_message'] = f"SQL执行失败: {str(e)}"
                state['logs'] = logs
            
            return state

        def explain_sql(state: GraphState) -> GraphState:
            """在SQL执行成功后，用自然语言解释SQL在做什么"""
            logs = state.get('logs', [])
            sql_query = state.get('sql_query', '')

            if not sql_query:
                state['sql_explanation'] = ''
                return state

            if not settings.openai_api_key:
                logger.warning("OpenAI API key not configured, skipping sql explanation")
                state['sql_explanation'] = ''
                return state

            prompt = f"""
请用中文严谨的说明下面的SQL在查询什么（2-4句话），并列出关键点：

SQL：
{sql_query}

要求：
1) 简述查询目标（查询对象、度量、时间/维度限制）
2) 说明主要筛选条件、分组、排序或聚合
3) 给出可能的业务含义或注意事项（如果有）
"""

            try:
                messages = [{"role": "user", "content": prompt}]
                explanation = self.vanna.submit_prompt(messages)
                if not isinstance(explanation, str):
                    explanation = str(explanation) if explanation is not None else ''

                log_entry = self.vanna.log_interaction(
                    step="sql_explanation",
                    input_data=sql_query,
                    prompt=prompt,
                    model_output=explanation,
                    success=True
                )
                logs.append(log_entry)

                state['sql_explanation'] = explanation
                state['logs'] = logs
            except Exception as e:
                log_entry = self.vanna.log_interaction(
                    step="sql_explanation",
                    input_data=sql_query,
                    prompt=prompt,
                    model_output="",
                    success=False,
                    error=str(e)
                )
                logs.append(log_entry)
                state['sql_explanation'] = ''
                state['logs'] = logs

            return state

        def analyze_nl_diff(state: GraphState) -> GraphState:
            """对比用户自然语言与SQL解释，分析差异与固化知识点"""
            logs = state.get('logs', [])
            user_input = state.get('user_input', '')
            sql_explanation = state.get('sql_explanation', '')

            if not settings.openai_api_key:
                logger.warning("OpenAI API key not configured, skipping nl diff analysis")
                state['nl_diff_analysis'] = None
                return state

            prompt = f"""
你将看到两段中文描述：
1) 用户原始需求：\n{user_input}
2) SQL含义解释：\n{sql_explanation}

请分析二者之间的差异与偏差，并判断是否需要沉淀为“固化知识”（便于之后统一口径）。
请务必返回严格JSON（不要额外文字）：
{{
  "is_mismatch": true/false,
  "differences": ["关键差异1", "关键差异2"],
  "suggest_alignment": ["建议如何对齐口径或补充字段"],
  "knowledge_candidates": [
    {{"title": "知识点简短标题", "description": "口径/转换规则/字段映射等"}}
  ]
}}
"""

            try:
                messages = [{"role": "user", "content": prompt}]
                response = self.vanna.submit_prompt(messages)
                if not isinstance(response, str):
                    response = str(response) if response is not None else ''

                parsed: Optional[Dict[str, Any]] = None
                try:
                    parsed = json.loads(response.strip()) if response else None
                except Exception:
                    parsed = None

                log_entry = self.vanna.log_interaction(
                    step="nl_diff_analysis",
                    input_data=f"user:{user_input}\nsql_exp:{sql_explanation}",
                    prompt=prompt,
                    model_output=response,
                    success=True
                )
                logs.append(log_entry)

                state['nl_diff_analysis'] = parsed if parsed is not None else {"raw": response}
                state['logs'] = logs
            except Exception as e:
                log_entry = self.vanna.log_interaction(
                    step="nl_diff_analysis",
                    input_data=f"user:{user_input}\nsql_exp:{sql_explanation}",
                    prompt=prompt,
                    model_output="",
                    success=False,
                    error=str(e)
                )
                logs.append(log_entry)
                state['nl_diff_analysis'] = None
                state['logs'] = logs

            return state
        
        def should_retry(state: GraphState) -> str:
            """判断是否应该重试"""
            retry_count = state.get('retry_count', 0)
            max_retries = state.get('max_retries', 2)
            has_error = state.get('error_message') is not None

            if has_error and retry_count < max_retries:
                return "retry"
            elif state.get('execution_result') is not None:
                return "success"
            else:
                return "failed"
        
        
        # 构建工作流图
        workflow = StateGraph(GraphState)
        
        # 添加节点
        workflow.add_node("check_training", check_training_needed)
        workflow.add_node("validate_input", validate_input_clarity)
        workflow.add_node("generate_sql", generate_sql)
        workflow.add_node("execute_sql", execute_sql)
        workflow.add_node("explain_sql", explain_sql)
        workflow.add_node("analyze_nl_diff", analyze_nl_diff)
        
        # 添加边
        workflow.set_entry_point("check_training")

        # 根据流程类型路由到不同的验证/生成路径
        def route_by_flow_type(state: GraphState) -> str:
            """根据流程类型决定下一步"""
            flow_type = state.get('flow_type', 'fast')
            return flow_type

        workflow.add_conditional_edges(
            "check_training",
            route_by_flow_type,
            {
                "fast": "validate_input",        # 快速流程：先验证后生成
                "thorough": "generate_sql"      # 深度流程：先生成后验证
            }
        )

        # 验证节点的路由逻辑
        def route_after_validation(state: GraphState) -> str:
            """验证后的路由逻辑"""
            if not state.get('is_clear'):
                return "failed"

            flow_type = state.get('flow_type', 'fast')
            sql_query = state.get('sql_query', '')

            if flow_type == 'fast' or not sql_query:
                # 快速流程：验证通过后生成SQL
                # 或者深度流程的第一次验证（此时还没有SQL）
                return "generate_sql"
            else:
                # 深度流程：已经有SQL，验证通过后执行
                return "execute_sql"

        workflow.add_conditional_edges(
            "validate_input",
            route_after_validation,
            {
                "generate_sql": "generate_sql",
                "execute_sql": "execute_sql",
                "failed": END
            }
        )

        # 生成SQL后的路由逻辑
        def route_after_generate_sql(state: GraphState) -> str:
            """生成SQL后的路由逻辑"""
            flow_type = state.get('flow_type', 'fast')
            if flow_type == 'thorough':
                # 深度流程：生成SQL后需要验证
                return "validate_input"
            else:
                # 快速流程：直接执行SQL
                return "execute_sql"

        workflow.add_conditional_edges(
            "generate_sql",
            route_after_generate_sql,
            {
                "validate_input": "validate_input",
                "execute_sql": "execute_sql"
            }
        )

        # 重试逻辑：如果失败且可以重试，回到generate_sql
        workflow.add_conditional_edges(
            "execute_sql",
            should_retry,
            {
                "success": "explain_sql",
                "failed": END,
                "retry": "generate_sql"  # 回到generate_sql节点进行重试
            }
        )

        # 执行成功后解释SQL，并进行自然语言差异分析
        workflow.add_edge("explain_sql", "analyze_nl_diff")
        workflow.add_edge("analyze_nl_diff", END)

        return workflow.compile()
    
    def _train_vanna(self):
        """训练Vanna模型（使用文档描述方式）"""
        logger.info("Training Vanna with available metadata, glossary and relation configs...")
        
        # 1. 训练表结构描述（只使用可用的表和列）
        available_tables = self.metadata_service.get_available_tables()
        for table in available_tables:
            table_name = table.get('name')
            table_comment = table.get('comment', '')
            columns = table.get('columns', [])
            
            # 只包含可用的列
            available_columns = [col for col in columns if col.get('is_available', 0) == 0]
            
            if available_columns:
                # 构建表结构文档
                doc_lines = [f"表名：{table_name}"]
                if table_comment:
                    doc_lines.append(f"表描述：{table_comment}")
                
                doc_lines.append("字段信息：")
                for col in available_columns:
                    storage_type = col.get('type', '')
                    business_type = col.get('business_type', '') or storage_type
                    comment = col.get('comment', '')
                    relation_id = col.get('relation_id', '')
                    
                    col_desc = f"  - {col.get('name')}：存储类型({storage_type})，业务类型({business_type})"
                    if comment:
                        col_desc += f"，描述({comment})"
                    if relation_id:
                        col_desc += f"，关联ID({relation_id})"
                    doc_lines.append(col_desc)
                
                documentation = "\n".join(doc_lines)
                self.vanna.train(documentation=documentation)
        
        # 2. 训练字段类型处理规则
        current_date = datetime.now().strftime("%Y-%m-%d")
        type_handling_doc = f"""
字段类型处理规则：
当前日期: {current_date}

1. 由于历史原因，字段的存储类型和业务类型可能不一致
2. 在进行数值比较、计算、排序等逻辑操作时，必须使用CAST函数将字段转换为业务类型
3. 示例：
   - 如果字段amount存储类型为VARCHAR，业务类型为DECIMAL
   - 比较时应使用：WHERE CAST(amount AS DECIMAL) > 100
   - 排序时应使用：ORDER BY CAST(amount AS DECIMAL) DESC
4. 在生成SQL时，请始终优先考虑业务类型进行类型转换
5. 时间相关查询时，请参考当前日期({current_date})来处理"今天"、"本月"、"最近30天"等时间描述
        """
        self.vanna.train(documentation=type_handling_doc)
        
        # 3. 训练关联配置信息
        relation_configs = self.relation_config_service.get_all_relation_configs()
        if relation_configs:
            relation_doc_lines = ["字段关联配置："]
            relation_doc_lines.append("在多个表中的字段可以相互关联，但存在格式差异，需要根据关联ID进行适当的转换。")
            
            for config in relation_configs:
                relation_id = config.get('relation_id')
                family = config.get('relation_family')
                subfamily = config.get('relation_subfamily')
                desc = config.get('relation_desc', '')
                
                config_desc = f"  - 关联ID: {relation_id} (关联族: {family}, 关联子族: {subfamily})"
                if desc:
                    config_desc += f"\n    关联规则: {desc}"
                relation_doc_lines.append(config_desc)
            
            relation_doc_lines.append("\n关联使用示例：")
            relation_doc_lines.append("- 当需要关联不同表的相同关联族字段时，请根据关联配置中的规则进行字段转换")
            relation_doc_lines.append("- 例如cust_no|17和cust_no|16关联需要left(col_name,16)")
            relation_doc_lines.append("- 例如cust_no|16和cust_no|cn_start关联需要right(col_name,16)")
            
            relation_documentation = "\n".join(relation_doc_lines)
            self.vanna.train(documentation=relation_documentation)
        
        # 4. 训练术语表映射
        terms = self.glossary_service.get_terms()
        for term in terms:
            if term.get('sql_expression'):
                question = f"什么是{term.get('term')}"
                sql = f"SELECT {term.get('sql_expression')} AS {term.get('term')}"
                self.vanna.train(question=question, sql=sql)
        
        # 5. 生成训练hash
        metadata_str = str(self.metadata_service.get_metadata())
        glossary_str = str(self.glossary_service.get_glossary())
        relation_str = str(self.relation_config_service.get_all_relation_configs())
        combined_str = metadata_str + glossary_str + relation_str
        self.vanna.training_hash = hashlib.md5(combined_str.encode()).hexdigest()
        
        logger.info("Vanna training completed")
    
    def _get_table_info_text(self) -> str:
        """获取可用表信息的文本描述（只包含 is_available = 0 的表和列）"""
        tables = self.metadata_service.get_available_tables()  # 只获取可用表
        info_lines = []
        
        for table in tables:
            table_name = table.get('name', '')
            table_comment = table.get('comment', '')
            info_lines.append(f"表 {table_name}: {table_comment}")
            
            columns = table.get('columns', [])
            # 只包含可用的列
            available_columns = [col for col in columns if col.get('is_available', 0) == 0]
            for col in available_columns:
                # 优先使用业务类型，如果没有则使用存储类型
                col_type = col.get('business_type') or col.get('type')
                col_info = f"  - {col.get('name')} ({col_type}): {col.get('comment', '')}"
                if col.get('relation_id'):
                    col_info += f" [关联ID: {col.get('relation_id')}]"
                info_lines.append(col_info)
        
        return "\n".join(info_lines)
    
    def _get_glossary_text(self) -> str:
        """获取术语表的文本描述"""
        terms = self.glossary_service.get_terms()
        term_lines = []
        
        for term in terms:
            term_name = term.get('term', '')
            definition = term.get('definition', '')
            aliases = ", ".join(term.get('aliases', []))
            
            term_line = f"- {term_name}: {definition}"
            if aliases:
                term_line += f" (别名: {aliases})"
            term_lines.append(term_line)
        
        return "\n".join(term_lines)
    
    def _get_relation_config_text(self) -> str:
        """获取关联配置的文本描述"""
        configs = self.relation_config_service.get_all_relation_configs()
        config_lines = []
        
        for config in configs:
            relation_id = config.get('relation_id', '')
            family = config.get('relation_family', '')
            subfamily = config.get('relation_subfamily', '')
            desc = config.get('relation_desc', '')
            
            config_line = f"- {relation_id} (关联族: {family}, 子族: {subfamily})"
            if desc:
                config_line += f": {desc}"
            config_lines.append(config_line)
        
        if not config_lines:
            return "暂无关联配置"
        
        return "\n".join(config_lines)
    
    def _extract_sql_from_response(self, response: str) -> str:
        """从响应中提取SQL语句"""
        # 简单实现：查找SELECT、INSERT、UPDATE、DELETE等关键词
        lines = response.split('\n')
        sql_lines = []
        in_sql_block = False
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH']):
                in_sql_block = True
                sql_lines.append(line)
            elif in_sql_block:
                if line.endswith(';') or line == '':
                    if line.endswith(';'):
                        sql_lines.append(line)
                    break
                else:
                    sql_lines.append(line)
        
        return ' '.join(sql_lines)
    
    def process_query(self, user_input: str, max_retries: int = 5, operator: str = None, flow_type: str = "fast") -> Dict[str, Any]:
        """
        处理用户查询
        :param flow_type: 流程类型，"fast"=先验证后生成SQL，"thorough"=先生成SQL后验证
        """
        # 使用追踪上下文管理器
        with track_operation("nl2sql_query", operator):
            session_id = tracker.current_session

            initial_state = GraphState(
                user_input=user_input,
                flow_type=flow_type,
                processed_input="",
                clear_check_details={},
                is_clear=False,
                sql_query="",
                execution_result=None,
                sql_explanation=None,
                nl_diff_analysis=None,
                error_message=None,
                retry_count=0,
                max_retries=max_retries,
                logs=[]
            )
            
            # 执行工作流
            final_state = self.workflow.invoke(initial_state)
            
            # 准备返回结果
            result = {
                'session_id': session_id,  # 添加session_id到返回结果
                'user_input': user_input,
                'is_clear': final_state.get('is_clear', False),
                'clear_check_details': final_state.get('clear_check_details', {}),
                'sql_query': final_state.get('sql_query', ''),
                'success': final_state.get('execution_result') is not None,
                'data': final_state.get('execution_result'),
                'error': final_state.get('error_message'),
                'retry_count': final_state.get('retry_count', 0),
                'sql_explanation': final_state.get('sql_explanation'),
                'nl_diff_analysis': final_state.get('nl_diff_analysis'),
                'logs': final_state.get('logs', [])
            }
            
            # 如果有数据结果，转换为字典格式
            if result['data'] is not None:
                result['data'] = result['data'].to_dict('records')
                result['row_count'] = len(result['data'])
            
            return result

# 全局服务实例
_nl2sql_service: Optional[NL2SQLService] = None

def get_nl2sql_service() -> NL2SQLService:
    """获取NL2SQL服务实例"""
    global _nl2sql_service
    if _nl2sql_service is None:
        _nl2sql_service = NL2SQLService()
    return _nl2sql_service
