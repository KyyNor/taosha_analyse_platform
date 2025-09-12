"""
元数据和术语表管理服务
"""

import json
from loguru import logger
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

from config import settings
from utils.database_connection import get_database_manager


class MetadataService:
    """元数据管理服务"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self._metadata = None
        self._metadata_hash = None
        self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """从数据库加载元数据"""
        try:
            with self.db_manager.get_metadata_connection() as (conn, db_type):
                cursor = conn.cursor()
                
                cursor.execute("SELECT name, comment FROM metadata_tables ORDER BY name")
                tables_data = cursor.fetchall()
                
                tables = []
                for table_name, table_comment in tables_data:
                    placeholder = self.db_manager.get_sql_placeholder(db_type)
                    cursor.execute(f"""
                        SELECT name, type, comment, is_primary_key, is_nullable 
                        FROM metadata_columns 
                        WHERE table_name = {placeholder} 
                        ORDER BY name
                    """, (table_name,))
                    columns_data = cursor.fetchall()
                    
                    columns = []
                    for col_name, col_type, col_comment, is_pk, is_nullable in columns_data:
                        columns.append({
                            "name": col_name,
                            "type": col_type,
                            "comment": col_comment or "",
                            "is_primary_key": bool(is_pk),
                            "is_nullable": bool(is_nullable)
                        })
                    
                    tables.append({
                        "name": table_name,
                        "comment": table_comment or "",
                        "columns": columns
                    })
                
                self._metadata = {"tables": tables}
                content_str = json.dumps(self._metadata, sort_keys=True, ensure_ascii=False)
                self._metadata_hash = hashlib.md5(content_str.encode()).hexdigest()
                
                logger.info(f"元数据已从{db_type}数据库加载，共{len(tables)}张表")
                
        except Exception as e:
            logger.error(f"从数据库加载元数据失败: {e}")
            self._metadata = {"tables": []}
            self._metadata_hash = None
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取元数据"""
        return self._metadata or {"tables": []}
    
    def get_tables(self) -> List[Dict[str, Any]]:
        """获取所有表信息"""
        return self.get_metadata().get("tables", [])
    
    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取指定表的信息"""
        for table in self.get_tables():
            if table.get("name") == table_name:
                return table
        return None
    
    def get_ddl_statements(self) -> List[str]:
        """生成建表语句"""
        ddl_statements = []
        
        for table in self.get_tables():
            table_name = table.get("name")
            columns = table.get("columns", [])
            
            if not table_name or not columns:
                continue
            
            # 构建建表语句
            column_definitions = []
            for col in columns:
                col_def = f"{col['name']} {col['type']}"
                if col.get('is_primary_key'):
                    col_def += " PRIMARY KEY"
                column_definitions.append(col_def)
            
            ddl = f"CREATE TABLE {table_name} (\n  " + ",\n  ".join(column_definitions) + "\n)"
            ddl_statements.append(ddl)
        
        return ddl_statements
    
    def add_table(self, table_name: str, comment: str = "") -> bool:
        """添加表元数据"""
        try:
            with self.db_manager.get_metadata_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                cursor.execute(
                    f"INSERT INTO metadata_tables (name, comment) VALUES ({placeholder}, {placeholder})",
                    (table_name, comment)
                )
                
            logger.info(f"添加表元数据成功: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"添加表元数据失败: {e}")
            return False
    
    def update_table(self, table_name: str, comment: str = "") -> bool:
        """更新表元数据"""
        try:
            with self.db_manager.get_metadata_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                cursor.execute(
                    f"UPDATE metadata_tables SET comment = {placeholder}, updated_at = {placeholder} WHERE name = {placeholder}",
                    (comment, datetime.now(), table_name)
                )
                
            logger.info(f"更新表元数据成功: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"更新表元数据失败: {e}")
            return False
    
    def delete_table(self, table_name: str) -> bool:
        """删除表元数据"""
        try:
            with self.db_manager.get_metadata_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                cursor.execute(f"DELETE FROM metadata_tables WHERE name = {placeholder}", (table_name,))
                
            logger.info(f"删除表元数据成功: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"删除表元数据失败: {e}")
            return False
    
    def add_column(self, table_name: str, column_name: str, column_type: str, 
                   comment: str = "", is_primary_key: bool = False, is_nullable: bool = True) -> bool:
        """添加列元数据"""
        try:
            with self.db_manager.get_metadata_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                cursor.execute(f"""
                    INSERT INTO metadata_columns (table_name, name, type, comment, is_primary_key, is_nullable) 
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                """, (table_name, column_name, column_type, comment, is_primary_key, is_nullable))
                
            logger.info(f"添加列元数据成功: {table_name}.{column_name}")
            return True
            
        except Exception as e:
            logger.error(f"添加列元数据失败: {e}")
            return False
    
    def update_column(self, table_name: str, column_name: str, column_type: str = None,
                     comment: str = None, is_primary_key: bool = None, is_nullable: bool = None) -> bool:
        """更新列元数据"""
        try:
            with self.db_manager.get_metadata_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                updates = []
                params = []
                
                if column_type is not None:
                    updates.append(f"type = {placeholder}")
                    params.append(column_type)
                if comment is not None:
                    updates.append(f"comment = {placeholder}")
                    params.append(comment)
                if is_primary_key is not None:
                    updates.append(f"is_primary_key = {placeholder}")
                    params.append(is_primary_key)
                if is_nullable is not None:
                    updates.append(f"is_nullable = {placeholder}")
                    params.append(is_nullable)
                
                updates.append(f"updated_at = {placeholder}")
                params.append(datetime.now())
                params.extend([table_name, column_name])
                
                cursor.execute(
                    f"UPDATE metadata_columns SET {', '.join(updates)} WHERE table_name = {placeholder} AND name = {placeholder}",
                    params
                )
                
            logger.info(f"更新列元数据成功: {table_name}.{column_name}")
            return True
            
        except Exception as e:
            logger.error(f"更新列元数据失败: {e}")
            return False
    
    def delete_column(self, table_name: str, column_name: str) -> bool:
        """删除列元数据"""
        try:
            with self.db_manager.get_metadata_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                cursor.execute(
                    f"DELETE FROM metadata_columns WHERE table_name = {placeholder} AND name = {placeholder}",
                    (table_name, column_name)
                )
                
            logger.info(f"删除列元数据成功: {table_name}.{column_name}")
            return True
            
        except Exception as e:
            logger.error(f"删除列元数据失败: {e}")
            return False
    
    def has_changed(self) -> bool:
        """检查元数据是否已变化"""
        try:
            current_metadata = self._load_metadata_from_db()
            current_content = json.dumps(current_metadata, sort_keys=True, ensure_ascii=False)
            current_hash = hashlib.md5(current_content.encode()).hexdigest()
            return current_hash != self._metadata_hash
        except Exception as e:
            logger.error(f"检查元数据变化失败: {e}")
            return True
    
    def _load_metadata_from_db(self) -> Dict[str, Any]:
        """从数据库加载元数据（不更新实例状态）"""
        with self.db_manager.get_metadata_connection() as (conn, db_type):
            cursor = conn.cursor()
            
            cursor.execute("SELECT name, comment FROM metadata_tables ORDER BY name")
            tables_data = cursor.fetchall()
            
            tables = []
            for table_name, table_comment in tables_data:
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                cursor.execute(f"""
                    SELECT name, type, comment, is_primary_key, is_nullable 
                    FROM metadata_columns 
                    WHERE table_name = {placeholder} 
                    ORDER BY name
                """, (table_name,))
                columns_data = cursor.fetchall()
                
                columns = []
                for col_name, col_type, col_comment, is_pk, is_nullable in columns_data:
                    columns.append({
                        "name": col_name,
                        "type": col_type,
                        "comment": col_comment or "",
                        "is_primary_key": bool(is_pk),
                        "is_nullable": bool(is_nullable)
                    })
                
                tables.append({
                    "name": table_name,
                    "comment": table_comment or "",
                    "columns": columns
                })
            
            return {"tables": tables}
    
    def reload_if_changed(self) -> bool:
        """如果有变化则重新加载元数据"""
        if self.has_changed():
            self._load_metadata()
            logger.info("Metadata reloaded due to changes")
            return True
        return False

class GlossaryService:
    """术语表管理服务"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self._glossary = None
        self._glossary_hash = None
        self._load_glossary()
    
    def _load_glossary(self) -> Dict[str, Any]:
        """从数据库加载术语表"""
        try:
            with self.db_manager.get_metadata_connection() as (conn, db_type):
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, term, definition, sql_expression, category 
                    FROM glossary_terms 
                    ORDER BY term
                """)
                terms_data = cursor.fetchall()
                
                terms = []
                for term_id, term, definition, sql_expr, category in terms_data:
                    placeholder = self.db_manager.get_sql_placeholder(db_type)
                    cursor.execute(
                        f"SELECT alias FROM glossary_aliases WHERE term_id = {placeholder}",
                        (term_id,)
                    )
                    aliases_data = cursor.fetchall()
                    aliases = [alias[0] for alias in aliases_data]
                    
                    terms.append({
                        "term": term,
                        "definition": definition or "",
                        "sql_expression": sql_expr or "",
                        "category": category or "",
                        "aliases": aliases
                    })
                
                self._glossary = {"terms": terms}
                content_str = json.dumps(self._glossary, sort_keys=True, ensure_ascii=False)
                self._glossary_hash = hashlib.md5(content_str.encode()).hexdigest()
                
                logger.info(f"术语表已从{db_type}数据库加载，共{len(terms)}个术语")
                
        except Exception as e:
            logger.error(f"从数据库加载术语表失败: {e}")
            self._glossary = {"terms": []}
            self._glossary_hash = None
    
    def get_glossary(self) -> Dict[str, Any]:
        """获取术语表"""
        return self._glossary or {"terms": []}
    
    def get_terms(self) -> List[Dict[str, Any]]:
        """获取所有术语"""
        return self.get_glossary().get("terms", [])
    
    def find_term(self, query: str) -> Optional[Dict[str, Any]]:
        """根据查询找到匹配的术语"""
        query_lower = query.lower()
        
        for term in self.get_terms():
            # 检查术语名称
            if term.get("term", "").lower() == query_lower:
                return term
            
            # 检查别名
            aliases = term.get("aliases", [])
            for alias in aliases:
                if alias.lower() == query_lower:
                    return term
        
        return None
    
    def get_term_mappings(self) -> Dict[str, str]:
        """获取术语到SQL表达式的映射"""
        mappings = {}
        
        for term in self.get_terms():
            term_name = term.get("term")
            sql_expr = term.get("sql_expression")
            
            if term_name and sql_expr:
                mappings[term_name.lower()] = sql_expr
                
                # 添加别名映射
                for alias in term.get("aliases", []):
                    mappings[alias.lower()] = sql_expr
        
        return mappings
    
    def add_term(self, term: str, definition: str = "", sql_expression: str = "", 
                 category: str = "", aliases: List[str] = None) -> bool:
        """添加术语"""
        try:
            with self.db_manager.get_metadata_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                cursor.execute(f"""
                    INSERT INTO glossary_terms (term, definition, sql_expression, category) 
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                """, (term, definition, sql_expression, category))
                
                term_id = cursor.lastrowid
                
                if aliases:
                    for alias in aliases:
                        cursor.execute(
                            f"INSERT INTO glossary_aliases (term_id, alias) VALUES ({placeholder}, {placeholder})",
                            (term_id, alias)
                        )
                
            logger.info(f"添加术语成功: {term}")
            return True
            
        except Exception as e:
            logger.error(f"添加术语失败: {e}")
            return False
    
    def update_term(self, term_id: int, term: str = None, definition: str = None, 
                   sql_expression: str = None, category: str = None) -> bool:
        """更新术语"""
        try:
            with self.db_manager.get_metadata_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                updates = []
                params = []
                
                if term is not None:
                    updates.append(f"term = {placeholder}")
                    params.append(term)
                if definition is not None:
                    updates.append(f"definition = {placeholder}")
                    params.append(definition)
                if sql_expression is not None:
                    updates.append(f"sql_expression = {placeholder}")
                    params.append(sql_expression)
                if category is not None:
                    updates.append(f"category = {placeholder}")
                    params.append(category)
                
                updates.append(f"updated_at = {placeholder}")
                params.append(datetime.now())
                params.append(term_id)
                
                cursor.execute(
                    f"UPDATE glossary_terms SET {', '.join(updates)} WHERE id = {placeholder}",
                    params
                )
                
            logger.info(f"更新术语成功: ID {term_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新术语失败: {e}")
            return False
    
    def delete_term(self, term_id: int) -> bool:
        """删除术语"""
        try:
            with self.db_manager.get_metadata_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                cursor.execute(f"DELETE FROM glossary_terms WHERE id = {placeholder}", (term_id,))
                
            logger.info(f"删除术语成功: ID {term_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除术语失败: {e}")
            return False
    
    def has_changed(self) -> bool:
        """检查术语表是否已变化"""
        try:
            current_glossary = self._load_glossary_from_db()
            current_content = json.dumps(current_glossary, sort_keys=True, ensure_ascii=False)
            current_hash = hashlib.md5(current_content.encode()).hexdigest()
            return current_hash != self._glossary_hash
        except Exception as e:
            logger.error(f"检查术语表变化失败: {e}")
            return True
    
    def _load_glossary_from_db(self) -> Dict[str, Any]:
        """从数据库加载术语表（不更新实例状态）"""
        with self.db_manager.get_metadata_connection() as (conn, db_type):
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, term, definition, sql_expression, category 
                FROM glossary_terms 
                ORDER BY term
            """)
            terms_data = cursor.fetchall()
            
            terms = []
            for term_id, term, definition, sql_expr, category in terms_data:
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                cursor.execute(
                    f"SELECT alias FROM glossary_aliases WHERE term_id = {placeholder}",
                    (term_id,)
                )
                aliases_data = cursor.fetchall()
                aliases = [alias[0] for alias in aliases_data]
                
                terms.append({
                    "term": term,
                    "definition": definition or "",
                    "sql_expression": sql_expr or "",
                    "category": category or "",
                    "aliases": aliases
                })
            
            return {"terms": terms}
    
    def reload_if_changed(self) -> bool:
        """如果有变化则重新加载术语表"""
        if self.has_changed():
            self._load_glossary()
            logger.info("Glossary reloaded due to changes")
            return True
        return False

# 全局服务实例
_metadata_service: Optional[MetadataService] = None
_glossary_service: Optional[GlossaryService] = None

def get_metadata_service() -> MetadataService:
    """获取元数据服务实例"""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = MetadataService()
    return _metadata_service

def get_glossary_service() -> GlossaryService:
    """获取术语表服务实例"""
    global _glossary_service
    if _glossary_service is None:
        _glossary_service = GlossaryService()
    return _glossary_service