"""
自然语言转SQL服务 - LangGraph + Vanna 实现
"""

import hashlib
from loguru import logger
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import chromadb
from pathlib import Path

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

# Vanna imports
from vanna.base import VannaBase
from vanna.openai import OpenAI_Chat
from vanna.chromadb import ChromaDB_VectorStore

# Local imports
from config import settings
from services.database_service import get_database_service
from services.metadata_service import get_metadata_service, get_glossary_service


# 状态定义
class GraphState(TypedDict):
    """LangGraph状态定义"""
    user_input: str
    processed_input: str
    is_clear: bool
    sql_query: str
    execution_result: Optional[pd.DataFrame]
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
            'model': settings.openai_model
        }
        
        # 只有当 API key 存在时才设置
        if settings.openai_api_key:
            openai_config['api_key'] = settings.openai_api_key
            
        # 如果有自定义 base_url，需要传递 OpenAI 客户端实例
        if settings.openai_base_url:
            try:
                from openai import OpenAI
                client = OpenAI(
                    api_key=settings.openai_api_key or "dummy",
                    base_url=settings.openai_base_url
                )
                openai_config['client'] = client
            except ImportError:
                logger.warning("OpenAI package not available, using default configuration")
        
        OpenAI_Chat.__init__(self, config=openai_config)
        
        self.training_hash = None
        logger.info("TaoshaVanna initialized")
    
    def submit_prompt(self, prompt: str) -> str:
        """重写submit_prompt方法，直接调用OpenAI API"""
        try:
            if not settings.openai_api_key:
                logger.warning("OpenAI API key not configured")
                return "抱歉，AI服务未配置，无法处理您的请求。"
            
            from openai import OpenAI
            
            # 创建OpenAI客户端
            client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url
            )
            
            # 调用API
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            result = response.choices[0].message.content
            logger.debug(f"OpenAI API response: {result[:100]}...")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return f"API调用失败: {str(e)}"
    
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
        
        logger.debug(f"[{step}] Input: {input_data}")
        logger.debug(f"[{step}] Prompt: {prompt[:200]}..." if len(prompt) > 200 else f"[{step}] Prompt: {prompt}")
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
        self.db_service = get_database_service()
        
        # 构建LangGraph工作流
        self.workflow = self._build_workflow()
        
        logger.info("NL2SQL Service initialized")
    
    def _build_workflow(self) -> StateGraph:
        """构建LangGraph工作流"""
        
        def check_training_needed(state: GraphState) -> GraphState:
            """检查是否需要重新训练Vanna"""
            logs = state.get('logs', [])
            
            # 检查元数据和术语表是否有变化
            metadata_changed = self.metadata_service.reload_if_changed()
            glossary_changed = self.glossary_service.reload_if_changed()
            
            if metadata_changed or glossary_changed or not self.vanna.training_hash:
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
            """验证输入是否清晰"""
            user_input = state['user_input']
            logs = state.get('logs', [])
            
            # 检查API配置
            if not settings.openai_api_key:
                logger.warning("OpenAI API key not configured, skipping input validation")
                state['is_clear'] = True
                state['processed_input'] = user_input
                state['logs'] = logs
                return state
            
            # 构建验证提示词
            validation_prompt = f"""
请判断以下用户查询是否足够清晰，可以转换为SQL查询：

用户查询: {user_input}

可用的表结构:
{self._get_table_info_text()}

可用的术语:
{self._get_glossary_text()}

请回答"是"或"否"，并说明原因。如果不够清晰，请说明需要什么额外信息。
"""
            
            try:
                response = self.vanna.submit_prompt(validation_prompt)
                
                # 确保response是字符串
                if not isinstance(response, str):
                    logger.warning(f"Unexpected response type: {type(response)}, content: {response}")
                    response = str(response) if response else ""
                
                is_clear = response.lower().startswith('是') if response else True
                
                log_entry = self.vanna.log_interaction(
                    step="input_validation",
                    input_data=user_input,
                    prompt=validation_prompt,
                    model_output=response,
                    success=True
                )
                logs.append(log_entry)
                
                state['is_clear'] = is_clear
                state['processed_input'] = response
                state['logs'] = logs
                
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"Input validation failed with traceback:\n{error_traceback}")
                
                log_entry = self.vanna.log_interaction(
                    step="input_validation",
                    input_data=user_input,
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
            """生成SQL查询"""
            user_input = state['user_input']
            logs = state.get('logs', [])
            
            try:
                # 使用Vanna生成SQL
                sql_query = self.vanna.generate_sql(user_input)
                
                log_entry = self.vanna.log_interaction(
                    step="sql_generation",
                    input_data=user_input,
                    prompt="vanna.generate_sql",
                    model_output=sql_query,
                    success=True
                )
                logs.append(log_entry)
                
                state['sql_query'] = sql_query
                state['logs'] = logs
                
            except Exception as e:
                log_entry = self.vanna.log_interaction(
                    step="sql_generation",
                    input_data=user_input,
                    prompt="vanna.generate_sql",
                    model_output="",
                    success=False,
                    error=str(e)
                )
                logs.append(log_entry)
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
        
        def retry_with_error_feedback(state: GraphState) -> GraphState:
            """使用错误反馈重新生成SQL"""
            user_input = state['user_input']
            error_message = state.get('error_message', '')
            previous_sql = state.get('sql_query', '')
            logs = state.get('logs', [])
            
            # 构建包含错误信息的提示词
            retry_prompt = f"""
之前的SQL查询执行失败，请根据错误信息重新生成SQL：

原始用户查询: {user_input}
之前生成的SQL: {previous_sql}
错误信息: {error_message}

表结构信息:
{self._get_table_info_text()}

术语表:
{self._get_glossary_text()}

请生成一个新的SQL查询，避免之前的错误：
"""
            
            try:
                response = self.vanna.submit_prompt(retry_prompt)
                # 提取SQL（简单实现，实际可能需要更复杂的解析）
                sql_query = self._extract_sql_from_response(response)
                
                log_entry = self.vanna.log_interaction(
                    step="sql_retry",
                    input_data=f"{user_input} | Error: {error_message}",
                    prompt=retry_prompt,
                    model_output=response,
                    success=True
                )
                logs.append(log_entry)
                
                state['sql_query'] = sql_query
                state['error_message'] = None  # 清除错误信息
                state['logs'] = logs
                
            except Exception as e:
                log_entry = self.vanna.log_interaction(
                    step="sql_retry",
                    input_data=f"{user_input} | Error: {error_message}",
                    prompt=retry_prompt,
                    model_output="",
                    success=False,
                    error=str(e)
                )
                logs.append(log_entry)
                state['error_message'] = f"重试失败: {str(e)}"
                state['logs'] = logs
            
            return state
        
        # 构建工作流图
        workflow = StateGraph(GraphState)
        
        # 添加节点
        workflow.add_node("check_training", check_training_needed)
        workflow.add_node("validate_input", validate_input_clarity)
        workflow.add_node("generate_sql", generate_sql)
        workflow.add_node("execute_sql", execute_sql)
        workflow.add_node("retry_sql", retry_with_error_feedback)
        
        # 添加边
        workflow.set_entry_point("check_training")
        workflow.add_edge("check_training", "validate_input")
        
        # 条件边
        workflow.add_conditional_edges(
            "validate_input",
            lambda state: "generate_sql" if state.get('is_clear') else END
        )
        
        workflow.add_edge("generate_sql", "execute_sql")
        
        workflow.add_conditional_edges(
            "execute_sql",
            should_retry,
            {
                "success": END,
                "failed": END,
                "retry": "retry_sql"
            }
        )
        
        workflow.add_edge("retry_sql", "execute_sql")
        
        return workflow.compile()
    
    def _train_vanna(self):
        """训练Vanna模型"""
        logger.info("Training Vanna with metadata and glossary...")
        
        # 训练DDL语句
        ddl_statements = self.metadata_service.get_ddl_statements()
        for ddl in ddl_statements:
            self.vanna.train(ddl=ddl)
        
        # 训练术语表映射
        terms = self.glossary_service.get_terms()
        for term in terms:
            if term.get('sql_expression'):
                question = f"什么是{term.get('term')}"
                sql = f"SELECT {term.get('sql_expression')} AS {term.get('term')}"
                self.vanna.train(question=question, sql=sql)
        
        # 生成训练hash
        metadata_str = str(self.metadata_service.get_metadata())
        glossary_str = str(self.glossary_service.get_glossary())
        combined_str = metadata_str + glossary_str
        self.vanna.training_hash = hashlib.md5(combined_str.encode()).hexdigest()
        
        logger.info("Vanna training completed")
    
    def _get_table_info_text(self) -> str:
        """获取表信息的文本描述"""
        tables = self.metadata_service.get_tables()
        info_lines = []
        
        for table in tables:
            table_name = table.get('name', '')
            table_comment = table.get('comment', '')
            info_lines.append(f"表 {table_name}: {table_comment}")
            
            columns = table.get('columns', [])
            for col in columns:
                col_info = f"  - {col.get('name')} ({col.get('type')}): {col.get('comment', '')}"
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
    
    def process_query(self, user_input: str, max_retries: int = 2) -> Dict[str, Any]:
        """处理用户查询"""
        initial_state = GraphState(
            user_input=user_input,
            processed_input="",
            is_clear=False,
            sql_query="",
            execution_result=None,
            error_message=None,
            retry_count=0,
            max_retries=max_retries,
            logs=[]
        )
        
        # 执行工作流
        final_state = self.workflow.invoke(initial_state)
        
        # 准备返回结果
        result = {
            'user_input': user_input,
            'is_clear': final_state.get('is_clear', False),
            'sql_query': final_state.get('sql_query', ''),
            'success': final_state.get('execution_result') is not None,
            'data': final_state.get('execution_result'),
            'error': final_state.get('error_message'),
            'retry_count': final_state.get('retry_count', 0),
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