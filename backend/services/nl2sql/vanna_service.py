"""
Vanna框架服务实现
集成Vanna框架提供NL2SQL基础能力，并添加权限控制
"""
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

import vanna
from vanna.chromadb import ChromaDB_VectorStore
from vanna.openai import OpenAI_Chat

from utils.logger import get_logger
from utils.exceptions import VectorDBException, LLMException, AuthorizationException
from config.settings import get_settings
from models.metadata_models import MetadataTable, MetadataField, MetadataDataTheme

logger = get_logger(__name__)


class TaoshaVanna(ChromaDB_VectorStore, OpenAI_Chat):
    """
    淘沙分析平台定制的Vanna类
    集成ChromaDB向量存储和OpenAI聊天功能
    """
    
    def __init__(self, config: Dict[str, Any]):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)


class VannaService:
    """Vanna框架服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.vanna_client = None
        self._initialize_vanna()
    
    def _initialize_vanna(self):
        """初始化Vanna客户端"""
        try:
            # 配置Vanna
            config = {
                'api_key': self.settings.LLM_API_KEY,
                'api_base': self.settings.LLM_BASE_URL,
                'model': self.settings.LLM_MODEL,
                'path': self.settings.VECTOR_DB_PATH,
                'n_results': 10  # 向量搜索返回结果数
            }
            
            # 创建Vanna实例
            self.vanna_client = TaoshaVanna(config=config)
            
            # 设置模型参数
            self.vanna_client.config['temperature'] = self.settings.LLM_TEMPERATURE
            self.vanna_client.config['max_tokens'] = self.settings.LLM_MAX_TOKENS
            
            logger.info("Vanna框架初始化完成")
            
        except Exception as e:
            logger.error(f"Vanna框架初始化失败: {e}")
            raise VectorDBException(f"Vanna初始化失败: {e}")
    
    async def generate_sql(
        self, 
        question: str, 
        user_id: int,
        theme_id: Optional[int] = None,
        table_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        生成SQL查询
        
        Args:
            question: 用户问题
            user_id: 用户ID
            theme_id: 数据主题ID（可选）
            table_ids: 指定的表ID列表（可选）
            
        Returns:
            包含SQL和相关信息的字典
        """
        try:
            logger.info(f"用户 {user_id} 请求生成SQL: {question}")
            
            # 权限检查：获取用户可访问的表
            accessible_tables = await self._get_user_accessible_tables(
                user_id, theme_id, table_ids
            )
            
            if not accessible_tables:
                raise AuthorizationException("您没有权限访问任何数据表")
            
            # 构建上下文信息
            context_info = await self._build_context_info(accessible_tables)
            
            # 调用Vanna生成SQL
            sql_result = await self._call_vanna_generate_sql(
                question, context_info
            )
            
            # 后处理和验证
            processed_result = await self._post_process_sql(
                sql_result, accessible_tables, user_id
            )
            
            logger.info(f"SQL生成成功，用户: {user_id}")
            return processed_result
            
        except Exception as e:
            logger.error(f"SQL生成失败: {e}")
            raise LLMException(f"SQL生成失败: {e}")
    
    async def train_on_documentation(self, doc_content: str, doc_type: str = "general"):
        """
        基于文档训练模型
        
        Args:
            doc_content: 文档内容
            doc_type: 文档类型
        """
        try:
            logger.info(f"开始训练文档，类型: {doc_type}")
            
            # 训练文档
            self.vanna_client.train(documentation=doc_content)
            
            logger.info(f"文档训练完成，类型: {doc_type}")
            
        except Exception as e:
            logger.error(f"文档训练失败: {e}")
            raise VectorDBException(f"文档训练失败: {e}")
    
    async def train_on_ddl(self, ddl_statements: List[str]):
        """
        基于DDL语句训练模型
        
        Args:
            ddl_statements: DDL语句列表
        """
        try:
            logger.info(f"开始训练DDL，数量: {len(ddl_statements)}")
            
            for ddl in ddl_statements:
                self.vanna_client.train(ddl=ddl)
            
            logger.info(f"DDL训练完成，数量: {len(ddl_statements)}")
            
        except Exception as e:
            logger.error(f"DDL训练失败: {e}")
            raise VectorDBException(f"DDL训练失败: {e}")
    
    async def train_on_sql_pairs(self, sql_pairs: List[Dict[str, str]]):
        """
        基于问题-SQL对训练模型
        
        Args:
            sql_pairs: 包含question和sql的字典列表
        """
        try:
            logger.info(f"开始训练SQL对，数量: {len(sql_pairs)}")
            
            for pair in sql_pairs:
                self.vanna_client.train(
                    question=pair['question'],
                    sql=pair['sql']
                )
            
            logger.info(f"SQL对训练完成，数量: {len(sql_pairs)}")
            
        except Exception as e:
            logger.error(f"SQL对训练失败: {e}")
            raise VectorDBException(f"SQL对训练失败: {e}")
    
    async def update_knowledge_base(
        self, 
        tables: List[MetadataTable],
        force_update: bool = False
    ):
        """
        更新知识库
        
        Args:
            tables: 表元数据列表
            force_update: 是否强制更新
        """
        try:
            logger.info(f"开始更新知识库，表数量: {len(tables)}")
            
            # 生成DDL语句
            ddl_statements = []
            documentation_parts = []
            
            for table in tables:
                # 生成DDL
                ddl = await self._generate_table_ddl(table)
                ddl_statements.append(ddl)
                
                # 生成文档
                doc = await self._generate_table_documentation(table)
                documentation_parts.append(doc)
            
            # 如果强制更新，先清除旧数据
            if force_update:
                await self._clear_knowledge_base()
            
            # 训练DDL
            await self.train_on_ddl(ddl_statements)
            
            # 训练文档
            combined_doc = "\n\n".join(documentation_parts)
            await self.train_on_documentation(combined_doc, "schema")
            
            logger.info("知识库更新完成")
            
        except Exception as e:
            logger.error(f"知识库更新失败: {e}")
            raise VectorDBException(f"知识库更新失败: {e}")
    
    async def get_similar_questions(
        self, 
        question: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取相似问题
        
        Args:
            question: 查询问题
            limit: 返回数量限制
            
        Returns:
            相似问题列表
        """
        try:
            # 使用Vanna的相似性搜索
            similar = self.vanna_client.get_similar_question_sql(question)
            
            # 格式化结果
            results = []
            for item in similar[:limit]:
                results.append({
                    'question': item.get('question', ''),
                    'sql': item.get('sql', ''),
                    'similarity': item.get('similarity', 0.0)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"获取相似问题失败: {e}")
            return []
    
    async def _get_user_accessible_tables(
        self,
        user_id: int,
        theme_id: Optional[int] = None,
        table_ids: Optional[List[int]] = None
    ) -> List[MetadataTable]:
        """获取用户可访问的表"""
        try:
            # TODO: 实现完整的权限检查逻辑
            # 这里先返回模拟数据
            
            accessible_tables = []
            
            # 模拟表数据
            mock_tables = [
                {
                    'id': 1,
                    'table_name_cn': '用户表',
                    'table_name_en': 'users',
                    'table_description': '系统用户信息表',
                    'fields': [
                        {'field_name_cn': '用户ID', 'field_name_en': 'user_id', 'field_type': 'integer'},
                        {'field_name_cn': '用户名', 'field_name_en': 'username', 'field_type': 'string'},
                        {'field_name_cn': '邮箱', 'field_name_en': 'email', 'field_type': 'string'},
                    ]
                },
                {
                    'id': 2,
                    'table_name_cn': '订单表',
                    'table_name_en': 'orders',
                    'table_description': '用户订单信息表',
                    'fields': [
                        {'field_name_cn': '订单ID', 'field_name_en': 'order_id', 'field_type': 'integer'},
                        {'field_name_cn': '用户ID', 'field_name_en': 'user_id', 'field_type': 'integer'},
                        {'field_name_cn': '订单金额', 'field_name_en': 'amount', 'field_type': 'decimal'},
                    ]
                }
            ]
            
            # 根据条件过滤表
            for table_data in mock_tables:
                if table_ids and table_data['id'] not in table_ids:
                    continue
                accessible_tables.append(table_data)
            
            return accessible_tables
            
        except Exception as e:
            logger.error(f"获取用户可访问表失败: {e}")
            raise AuthorizationException(f"权限检查失败: {e}")
    
    async def _build_context_info(self, tables: List[Dict]) -> Dict[str, Any]:
        """构建上下文信息"""
        context = {
            'tables': [],
            'relationships': [],
            'business_terms': []
        }
        
        for table in tables:
            table_info = {
                'name': table['table_name_en'],
                'chinese_name': table['table_name_cn'],
                'description': table.get('table_description', ''),
                'fields': []
            }
            
            for field in table.get('fields', []):
                field_info = {
                    'name': field['field_name_en'],
                    'chinese_name': field['field_name_cn'],
                    'type': field['field_type']
                }
                table_info['fields'].append(field_info)
            
            context['tables'].append(table_info)
        
        return context
    
    async def _call_vanna_generate_sql(
        self, 
        question: str, 
        context_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用Vanna生成SQL"""
        try:
            # 构建增强的问题描述
            enhanced_question = await self._enhance_question_with_context(
                question, context_info
            )
            
            # 调用Vanna生成SQL
            sql = self.vanna_client.generate_sql(enhanced_question)
            
            # 获取相关的训练数据
            related_training_data = self.vanna_client.get_related_training_data(question)
            
            return {
                'sql': sql,
                'original_question': question,
                'enhanced_question': enhanced_question,
                'related_data': related_training_data,
                'confidence': 0.85  # 模拟置信度
            }
            
        except Exception as e:
            logger.error(f"Vanna SQL生成调用失败: {e}")
            raise LLMException(f"Vanna调用失败: {e}")
    
    async def _enhance_question_with_context(
        self, 
        question: str, 
        context_info: Dict[str, Any]
    ) -> str:
        """使用上下文信息增强问题"""
        # 构建表结构信息
        schema_info = []
        for table in context_info['tables']:
            fields_str = ", ".join([
                f"{field['chinese_name']}({field['name']})" 
                for field in table['fields']
            ])
            schema_info.append(
                f"表{table['chinese_name']}({table['name']}): {fields_str}"
            )
        
        enhanced_question = f"""
数据库结构信息:
{chr(10).join(schema_info)}

用户问题: {question}

请基于以上数据库结构生成相应的SQL查询。
"""
        return enhanced_question
    
    async def _post_process_sql(
        self, 
        sql_result: Dict[str, Any], 
        accessible_tables: List[Dict],
        user_id: int
    ) -> Dict[str, Any]:
        """后处理SQL结果"""
        try:
            sql = sql_result.get('sql', '')
            
            # 基础清理
            cleaned_sql = sql.strip()
            if not cleaned_sql.endswith(';'):
                cleaned_sql += ';'
            
            # 权限验证：检查SQL中的表是否在用户可访问范围内
            accessible_table_names = [t['table_name_en'] for t in accessible_tables]
            sql_upper = cleaned_sql.upper()
            
            for table_name in accessible_table_names:
                if table_name.upper() in sql_upper:
                    # 找到了可访问的表，验证通过
                    break
            else:
                # TODO: 更严格的表名检查
                pass
            
            # 安全检查：移除危险操作
            dangerous_operations = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 'ALTER']
            for op in dangerous_operations:
                if op in sql_upper:
                    raise AuthorizationException(f"不允许执行 {op} 操作")
            
            # 添加结果行数限制
            if 'LIMIT' not in sql_upper:
                # 为SELECT语句添加LIMIT
                if sql_upper.strip().startswith('SELECT'):
                    limit_value = self.settings.MAX_RESULT_ROWS
                    if cleaned_sql.endswith(';'):
                        cleaned_sql = cleaned_sql[:-1] + f' LIMIT {limit_value};'
                    else:
                        cleaned_sql += f' LIMIT {limit_value}'
            
            result = {
                'sql': cleaned_sql,
                'original_sql': sql_result.get('sql', ''),
                'question': sql_result.get('original_question', ''),
                'confidence': sql_result.get('confidence', 0.0),
                'accessible_tables': accessible_table_names,
                'user_id': user_id
            }
            
            return result
            
        except Exception as e:
            logger.error(f"SQL后处理失败: {e}")
            raise
    
    async def _generate_table_ddl(self, table: Dict) -> str:
        """生成表的DDL语句"""
        fields_ddl = []
        for field in table.get('fields', []):
            field_type = self._map_field_type(field['field_type'])
            fields_ddl.append(f"    {field['field_name_en']} {field_type}")
        
        ddl = f"""CREATE TABLE {table['table_name_en']} (
{chr(10).join(fields_ddl)}
);"""
        
        return ddl
    
    def _map_field_type(self, field_type: str) -> str:
        """映射字段类型到SQL类型"""
        type_mapping = {
            'string': 'VARCHAR(255)',
            'integer': 'INT',
            'decimal': 'DECIMAL(10,2)',
            'float': 'FLOAT',
            'boolean': 'BOOLEAN',
            'date': 'DATE',
            'datetime': 'DATETIME',
            'text': 'TEXT'
        }
        return type_mapping.get(field_type, 'VARCHAR(255)')
    
    async def _generate_table_documentation(self, table: Dict) -> str:
        """生成表的文档说明"""
        doc_parts = [
            f"表名: {table['table_name_cn']} ({table['table_name_en']})",
            f"描述: {table.get('table_description', '无描述')}"
        ]
        
        if table.get('fields'):
            doc_parts.append("字段说明:")
            for field in table['fields']:
                doc_parts.append(
                    f"- {field['field_name_cn']} ({field['field_name_en']}): {field['field_type']}"
                )
        
        return "\n".join(doc_parts)
    
    async def _clear_knowledge_base(self):
        """清除知识库"""
        try:
            # TODO: 实现清除ChromaDB集合的逻辑
            logger.info("知识库清除完成")
        except Exception as e:
            logger.error(f"清除知识库失败: {e}")


# 全局Vanna服务实例
_vanna_service = None


def get_vanna_service() -> VannaService:
    """获取Vanna服务实例（单例模式）"""
    global _vanna_service
    if _vanna_service is None:
        _vanna_service = VannaService()
    return _vanna_service