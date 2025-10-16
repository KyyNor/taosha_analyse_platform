"""
自然语言转SQL服务 - LangGraph + Vanna 实现
"""

import hashlib
import json
import traceback
from datetime import datetime

from typing import Optional

# LangGraph imports
from langgraph.graph import StateGraph, END

from services.metadata_service.metadata_service import get_metadata_service, get_glossary_service, get_relation_field_config_service, get_prompt_template_service
from services.tracking_service.operation_tracking import tracker
from services.query_engine import get_query_engine
from services.service_models import BaseNodeLog, TaskState, TaskStateHelper
from services.vanna_service.taosha_vanna_service import TaoshaVanna
from services.prompt_template_renderer import PromptTemplateRenderer

# Local imports
from utils.config import settings
from utils.logger import logger
from utils.progress_decorator import track_node_progress

class NL2SQLService:
    """自然语言转SQL服务"""
    
    def __init__(self):
        self.vanna = TaoshaVanna()
        self.metadata_service = get_metadata_service()
        self.glossary_service = get_glossary_service()
        self.relation_config_service = get_relation_field_config_service()
        self.prompt_template_service = get_prompt_template_service()
        self.db_service = get_query_engine()

        # 初始化提示词模板渲染器
        self.template_renderer = PromptTemplateRenderer(self.prompt_template_service)

        # 构建统一的LangGraph工作流
        self.workflow = self._build_workflow()

        logger.info("NL2SQL服务初始化完成")
    
    def _build_workflow(self) -> StateGraph:
        """构建统一的LangGraph工作流，支持多种流程类型"""
        
        @track_node_progress("知识库更新")
        def check_training_needed(state: TaskState) -> TaskState:
            """检查是否需要重新训练Vanna"""

            logger.info(state)

            # 需要重新训练
            self._train_vanna()

            state.current_step_log = BaseNodeLog(
                step="知识库更新",
                input_data="metadata/glossary check",
                prompt="",
                model_output="training completed",
                success=True
            )

            return state
        
        @track_node_progress("用户输入验证")
        def validate_input_clarity(state: TaskState) -> TaskState:
            """验证输入是否清晰，支持两种模式：纯输入验证 和 SQL+输入匹配验证"""
            user_input = state.user_input
            step_name = '用户输入验证'
            sql_query = getattr(state, 'sql_query', '')  # 可能存在也可能不存在
            flow_type = getattr(state, 'flow_type', 'fast')

            # 检查API配置
            if not settings.openai_api_key:
                logger.warning("大模型API密钥未配置，跳过输入验证")
                state.is_clear = True
                state.current_step_log = BaseNodeLog(
                    step=step_name,
                    input_data=user_input,
                    prompt="",
                    model_output="",
                    success=False,
                    error="大模型API密钥未配置，跳过输入验证"
                )
                return state

            # 根据是否有SQL选择验证模式和模板
            current_date = datetime.now().strftime("%Y-%m-%d")

            # 准备模板参数
            template_params = {
                "current_date": current_date,
                "user_input": user_input,
                "table_info": self._get_table_info_text(),
                "glossary_info": self._get_glossary_text(),
                "relation_config": self._get_relation_config_text()
            }

            # 根据流程类型选择模板
            if sql_query and flow_type == 'thorough':
                # 深度流程：验证用户输入+SQL匹配度
                template_params["sql_query"] = sql_query
                template_name = "input_validation_thorough"

                # 默认模板（回退用）
                default_template = """请结合生成的SQL查询，判断用户原始查询是否足够清晰，SQL是否准确反映了用户需求。

用户原始查询: {user_input}

生成的SQL查询: {sql_query}

可用的表结构:
{table_info}

可用的术语:
{glossary_info}

字段关联配置:
{relation_config}

请严格按照以下JSON格式返回结果，不要添加任何其他文字：
{
    "is_clear": true/false,
    "reason": "判断的详细原因，结合SQL生成质量来评估",
    "sql_match": true/false,
    "suggestions": ["如果不够清晰，请提供3个具体的可查询示例"]
}

注意：
1. 不仅要评估用户输入的清晰度，还要评估SQL是否准确反映了用户需求
2. 如果SQL很好地满足了用户需求，即使输入不够完美也应该认为is_clear=true
3. 如果SQL与用户需求有偏差，应该给出具体建议"""
            else:
                # 快速流程：只验证用户输入清晰度
                template_name = "input_validation_fast"

                # 默认模板（回退用）
                default_template = """请判断以下用户查询是否足够清晰，可以转换为SQL查询。

当前日期: {current_date}

用户查询: {user_input}

可用的表结构:
{table_info}

可用的术语:
{glossary_info}

字段关联配置:
{relation_config}

请严格按照以下JSON格式返回结果，不要添加任何其他文字：
{
    "is_clear": true/false,
    "reason": "判断的详细原因",
    "suggestions": ["如果不清晰，请提供3个具体的可查询示例，直接使用表中的字段名和具体时间范围，例如：'最近30天手机销量统计'、'2024年1月各地区销售额对比'"]
}

注意：suggestions中应该是完整的、可以直接查询的问题示例，而不是修改建议。基于用户的模糊查询，结合可用的表结构，生成具体可执行的查询示例。"""

            # 使用模板渲染器获取提示词
            try:
                validation_prompt = self.template_renderer.render_template(
                    template_name=template_name,
                    params=template_params,
                    default_template=default_template
                )
                logger.info(f"使用模板 {template_name} 生成验证提示词")
            except Exception as e:
                logger.warning(f"模板渲染失败，使用默认模板: {e}")
                validation_prompt = default_template.format(**template_params)

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
                    is_clear = False
                    clear_check_details = {
                        'is_clear': is_clear,
                        'reason': f"无法解析模型响应为JSON: {str(json_error)}",
                        'suggestions': [],
                        'validation_type': step_name
                    }

                state.is_clear = is_clear
                state.clear_check_details = clear_check_details

                state.current_step_log = BaseNodeLog(
                    step=step_name,
                    input_data=user_input if not sql_query else f"user:{user_input}\nsql:{sql_query}",
                    prompt=validation_prompt,
                    model_output=response,
                    success=True,
                )
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Input validation failed with traceback:\n{error_traceback}")

                state.is_clear = False
                state.error_message = f"输入验证失败: {str(e)}"
                state.current_step_log = BaseNodeLog(
                    step=step_name,
                    input_data=user_input if not sql_query else f"user:{user_input}\nsql:{sql_query}",
                    prompt=validation_prompt,
                    model_output="",
                    success=False,
                    error=f"{str(e)}\nTraceback:\n{error_traceback}"
                )

            return state
        
        @track_node_progress("生成查询语句")
        def generate_sql(state: TaskState) -> TaskState:
            """生成SQL查询（包含错误重试逻辑）"""
            user_input = state.user_input
            error_message = getattr(state, 'error_message', None)
            previous_sql = getattr(state, 'sql_query', '')
            retry_count = getattr(state, 'retry_count', 0)
            
            # 构建输入内容：如果有错误信息，则包含错误反馈
            step_name = "生成查询语句"

            # 这是重试情况，增强输入信息
            current_date = datetime.now().strftime("%Y-%m-%d")

            # 根据是否有错误信息选择模板
            if error_message and previous_sql:
                # 重试情况
                step_name = "sql_retry"
                template_name = "sql_generation_retry"

                # 准备重试模板参数
                template_params = {
                    "user_input": user_input,
                    "current_date": current_date,
                    "previous_sql": previous_sql,
                    "error_message": error_message,
                    "table_info": self._get_table_info_text()
                }

                # 默认重试模板（回退用）
                default_template = """之前的SQL执行失败，请生成一个新的SQL查询。

原始用户查询: {user_input}
当前日期: {current_date}

之前失败的SQL: {previous_sql}
错误信息: {error_message}

可用的表结构:
{table_info}

请基于错误信息生成一个新的SQL查询，避免相同的错误。

重要提示:
1. 字段的存储类型和业务类型可能不同，数值比较时请使用CAST转换为业务类型
2. 关联不同表的字段时，请根据关联配置进行适当转换
3. 所有表都需要使用别名，从t1开始，t1、t2、t3依次递增
4. 所有字段都需要使用完整引用，例如t1.cust_no，不允许只写字段名
5. 特别注意数据类型转换和NULL值处理

请生成标准的SQL查询语句。"""
            else:
                # 正常生成情况
                template_name = "sql_generation"

                # 准备生成模板参数
                template_params = {
                    "current_date": current_date,
                    "user_input": user_input,
                    "error_info": "",
                    "tips": ""
                }

                # 默认生成模板（回退用）
                default_template = """请根据用户的自然语言查询生成对应的SQL语句。

{user_input}
当前日期: {current_date}

{error_info}

重要提示:
1. 字段的存储类型和业务类型可能不同，数值比较时请使用CAST转换为业务类型
2. 关联不同表的字段时，请根据关联配置进行适当转换
3. 所有表都需要使用别名，从t1开始，t1、t2、t3依次递增
4. 所有字段都需要使用完整引用，例如t1.cust_no，不允许只写字段名
{tips}

请生成标准的SQL查询语句。"""

            # 使用模板渲染器获取提示词
            try:
                query_input = self.template_renderer.render_template(
                    template_name=template_name,
                    params=template_params,
                    default_template=default_template
                )
                logger.info(f"使用模板 {template_name} 生成SQL提示词")
            except Exception as e:
                logger.warning(f"模板渲染失败，使用默认模板: {e}")
                query_input = default_template.format(**template_params)

            
            try:
                # 使用Vanna生成SQL（会自动检索向量数据库上下文）
                sql_query = self.vanna.generate_sql(query_input)
                
                state.sql_query = sql_query
                state.error_message = None  # 清除错误信息
                state.current_step_log = BaseNodeLog(
                    step=step_name,
                    input_data=query_input,
                    prompt=query_input,
                    model_output=sql_query,
                    success=True,
                )

            except Exception as e:
                error_traceback = traceback.format_exc()

                if retry_count > 0:
                    state.error_message = f"SQL重试失败: {str(e)}"
                else:
                    state.error_message = f"SQL生成失败: {str(e)}"

                state.current_step_log = BaseNodeLog(
                    step=step_name,
                    input_data=query_input,
                    prompt=query_input,
                    model_output="",
                    success=False,
                    error=f"{str(e)}\nTraceback:\n{error_traceback}"
                )
            
            return state
        
        @track_node_progress("执行查询语句")
        def execute_sql(state: TaskState) -> TaskState:
            """执行SQL查询"""
            sql_query = getattr(state, 'sql_query', '')
            step_name = "执行查询语句"

            if not sql_query:
                state.error_message = "没有可执行的SQL查询"
                return state
            
            try:
                # 执行SQL查询
                result = self.db_service.execute_query(sql_query)

                state.current_step_log = BaseNodeLog(
                    step=step_name,
                    input_data=sql_query,
                    prompt="data_engine.execute_query",
                    model_output=f"返回 {len(result)} 行数据",
                    success=True,
                )
                
                state.execution_result = result.to_dict(orient="records")

            except Exception as e:
                error_traceback = traceback.format_exc()
                # 增加重试计数
                retry_count = getattr(state, 'retry_count', 0) + 1
                state.retry_count = retry_count
                state.error_message = f"SQL执行失败: {str(e)}"
                state.current_step_log = BaseNodeLog(
                    step=step_name,
                    input_data=sql_query,
                    prompt="data_engine.execute_query",
                    model_output="",
                    success=False,
                    error=f"{str(e)}\nTraceback:\n{error_traceback}"
                )
            
            return state

        def should_retry(state: TaskState) -> str:
            """判断是否应该重试"""
            retry_count = getattr(state, 'retry_count', 0)
            max_retries = getattr(state, 'max_retries', 2)
            has_error = getattr(state, 'error_message', None) is not None

            if has_error and retry_count < max_retries:
                return "retry"
            elif getattr(state, 'execution_result', None) is not None:
                return "success"
            else:
                return "failed"
        
        
        # 构建工作流图
        workflow = StateGraph(TaskState)
        
        # 添加节点
        workflow.add_node("check_training", check_training_needed)
        workflow.add_node("validate_input", validate_input_clarity)
        workflow.add_node("generate_sql", generate_sql)
        workflow.add_node("execute_sql", execute_sql)

        # 添加边
        workflow.set_entry_point("check_training")

        # 根据流程类型路由到不同的验证/生成路径
        def route_by_flow_type(state: TaskState) -> str:
            """根据流程类型决定下一步"""
            flow_type = getattr(state, 'flow_type', 'fast')
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
        def route_after_generate_sql(state: TaskState) -> str:
            """生成SQL后的路由逻辑"""
            flow_type = getattr(state, 'flow_type', 'fast')
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
                "success": END,
                "failed": END,
                "retry": "generate_sql"  # 回到generate_sql节点进行重试
            }
        )

        return workflow.compile()
    
    def _train_vanna(self):
        """训练Vanna模型（使用文档描述方式）"""
        logger.info("开始使用可用元数据、词汇表和关系配置训练Vanna模型...")
        
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
            # 只处理概念解释和SQL问答类型的术语
            if term.get('type') in ['concept', 'sql_qa']:
                term_name = term.get('name', '')
                content = term.get('content', {})

                if term.get('type') == 'sql_qa' and content.get('answer'):
                    # SQL问答类型，使用答案作为SQL
                    question = content.get('question', f"什么是{term_name}")
                    sql = content.get('answer', '')
                    self.vanna.train(question=question, sql=sql)
                elif term.get('type') == 'concept' and content.get('content'):
                    # 概念解释类型，将解释内容作为问答对训练
                    question = f"什么是{term_name}"
                    answer = content.get('content', '')
                    self.vanna.train(question=question, sql=f"SELECT '{answer}' AS {term_name}")
        
        # 5. 生成训练hash
        metadata_str = str(self.metadata_service.get_metadata())
        glossary_str = str(self.glossary_service.get_glossary())
        relation_str = str(self.relation_config_service.get_all_relation_configs())
        combined_str = metadata_str + glossary_str + relation_str
        self.vanna.training_hash = hashlib.md5(combined_str.encode()).hexdigest()
        
        logger.info("Vanna模型训练完成")
    
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
            term_name = term.get('name', '')
            term_type = term.get('type', '')
            content = term.get('content', {})

            if term_type == 'concept':
                content_text = content.get('content', '')
                term_line = f"- {term_name} (概念解释): {content_text}"
            elif term_type == 'sql_qa':
                question = content.get('question', '')
                answer = content.get('answer', '')
                term_line = f"- {term_name} (SQL问答): {question} - {answer}"
            elif term_type == 'dict_mapping':
                col_name = content.get('col_name', '')
                dict_map_count = len(content.get('dict_map', []))
                term_line = f"- {term_name} (字典转换): 字段({col_name})，映射项({dict_map_count}个)"
            else:
                term_line = f"- {term_name}: {content}"

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
    
    def process_query(self, user_input: str, task_id, max_retries: int = 5, operator: str = None, flow_type: str = "fast") -> TaskState:
        """
        处理用户查询
        :param flow_type: 流程类型，"fast"=先验证后生成SQL，"thorough"=先生成SQL后验证
        """
        logger.info(f"开始处理查询流程 用户输入：{user_input}，任务ID：{task_id}，操作人：{operator}，流程类型：{flow_type}")
        
        # 创建统一的任务状态
        task_state = TaskStateHelper.create_default(
            task_id=task_id,
            user_input=user_input,
            flow_type=flow_type,
            max_retries=max_retries,
            operator=operator
        )

        tracker.create_task(task_state)

        # 执行工作流（直接使用TaskState）
        final_state = self.workflow.invoke(task_state)

        # 返回统一格式
        return final_state

# 全局服务实例
_nl2sql_service: Optional[NL2SQLService] = None

def get_nl2sql_service() -> NL2SQLService:
    """获取NL2SQL服务实例"""
    global _nl2sql_service
    if _nl2sql_service is None:
        _nl2sql_service = NL2SQLService()
    return _nl2sql_service
