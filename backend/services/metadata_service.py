"""
元数据和术语表管理服务
"""

import json
import sqlite3
import mysql.connector
from pathlib import Path
from loguru import logger
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

from config import settings


class MetadataService:
    """元数据管理服务"""
    
    def __init__(self, db_type: str = "sqlite", db_config: Dict[str, Any] = None):
        self.db_type = db_type
        self.db_config = db_config or self._get_default_db_config()
        self._metadata = None
        self._metadata_hash = None
        self._init_database()
        self._load_metadata()
    
    def _get_default_db_config(self) -> Dict[str, Any]:
        """获取默认数据库配置"""
        if self.db_type == "sqlite":
            return {
                "database": str(settings.database_dir / "metadata.db")
            }
        elif self.db_type == "mysql":
            return {
                "host": "localhost",
                "port": 3306,
                "database": "taosha_metadata",
                "user": "root",
                "password": ""
            }
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_type}")
    
    def _get_connection(self):
        """获取数据库连接"""
        if self.db_type == "sqlite":
            return sqlite3.connect(self.db_config["database"])
        elif self.db_type == "mysql":
            return mysql.connector.connect(**self.db_config)
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_type}")
    
    def _init_database(self):
        """初始化数据库表结构"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if self.db_type == "sqlite":
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS metadata_tables (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        comment TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS metadata_columns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        table_name TEXT NOT NULL,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        comment TEXT,
                        is_primary_key BOOLEAN DEFAULT FALSE,
                        is_nullable BOOLEAN DEFAULT TRUE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (table_name) REFERENCES metadata_tables(name) ON DELETE CASCADE,
                        UNIQUE(table_name, name)
                    )
                """)
            elif self.db_type == "mysql":
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS metadata_tables (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        name VARCHAR(255) UNIQUE NOT NULL,
                        comment TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS metadata_columns (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        table_name VARCHAR(255) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        type VARCHAR(100) NOT NULL,
                        comment TEXT,
                        is_primary_key BOOLEAN DEFAULT FALSE,
                        is_nullable BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (table_name) REFERENCES metadata_tables(name) ON DELETE CASCADE,
                        UNIQUE KEY unique_table_column (table_name, name)
                    )
                """)
            
            conn.commit()
            conn.close()
            logger.info(f"数据库初始化完成: {self.db_type}")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def _load_metadata(self) -> Dict[str, Any]:
        """从数据库加载元数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT name, comment FROM metadata_tables ORDER BY name")
            tables_data = cursor.fetchall()
            
            tables = []
            for table_name, table_comment in tables_data:
                cursor.execute("""
                    SELECT name, type, comment, is_primary_key, is_nullable 
                    FROM metadata_columns 
                    WHERE table_name = ? 
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
            
            conn.close()
            logger.info(f"元数据已从{self.db_type}数据库加载，共{len(tables)}张表")
            
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
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO metadata_tables (name, comment) VALUES (?, ?)",
                (table_name, comment)
            )
            
            conn.commit()
            conn.close()
            logger.info(f"添加表元数据成功: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"添加表元数据失败: {e}")
            return False
    
    def update_table(self, table_name: str, comment: str = "") -> bool:
        """更新表元数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE metadata_tables SET comment = ?, updated_at = ? WHERE name = ?",
                (comment, datetime.now(), table_name)
            )
            
            conn.commit()
            conn.close()
            logger.info(f"更新表元数据成功: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"更新表元数据失败: {e}")
            return False
    
    def delete_table(self, table_name: str) -> bool:
        """删除表元数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM metadata_tables WHERE name = ?", (table_name,))
            
            conn.commit()
            conn.close()
            logger.info(f"删除表元数据成功: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"删除表元数据失败: {e}")
            return False
    
    def add_column(self, table_name: str, column_name: str, column_type: str, 
                   comment: str = "", is_primary_key: bool = False, is_nullable: bool = True) -> bool:
        """添加列元数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO metadata_columns (table_name, name, type, comment, is_primary_key, is_nullable) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (table_name, column_name, column_type, comment, is_primary_key, is_nullable))
            
            conn.commit()
            conn.close()
            logger.info(f"添加列元数据成功: {table_name}.{column_name}")
            return True
            
        except Exception as e:
            logger.error(f"添加列元数据失败: {e}")
            return False
    
    def update_column(self, table_name: str, column_name: str, column_type: str = None,
                     comment: str = None, is_primary_key: bool = None, is_nullable: bool = None) -> bool:
        """更新列元数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if column_type is not None:
                updates.append("type = ?")
                params.append(column_type)
            if comment is not None:
                updates.append("comment = ?")
                params.append(comment)
            if is_primary_key is not None:
                updates.append("is_primary_key = ?")
                params.append(is_primary_key)
            if is_nullable is not None:
                updates.append("is_nullable = ?")
                params.append(is_nullable)
            
            updates.append("updated_at = ?")
            params.append(datetime.now())
            params.extend([table_name, column_name])
            
            cursor.execute(
                f"UPDATE metadata_columns SET {', '.join(updates)} WHERE table_name = ? AND name = ?",
                params
            )
            
            conn.commit()
            conn.close()
            logger.info(f"更新列元数据成功: {table_name}.{column_name}")
            return True
            
        except Exception as e:
            logger.error(f"更新列元数据失败: {e}")
            return False
    
    def delete_column(self, table_name: str, column_name: str) -> bool:
        """删除列元数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM metadata_columns WHERE table_name = ? AND name = ?",
                (table_name, column_name)
            )
            
            conn.commit()
            conn.close()
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
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, comment FROM metadata_tables ORDER BY name")
        tables_data = cursor.fetchall()
        
        tables = []
        for table_name, table_comment in tables_data:
            cursor.execute("""
                SELECT name, type, comment, is_primary_key, is_nullable 
                FROM metadata_columns 
                WHERE table_name = ? 
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
        
        conn.close()
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
    
    def __init__(self, db_type: str = "sqlite", db_config: Dict[str, Any] = None):
        self.db_type = db_type
        self.db_config = db_config or self._get_default_db_config()
        self._glossary = None
        self._glossary_hash = None
        self._init_database()
        self._load_glossary()
    
    def _get_default_db_config(self) -> Dict[str, Any]:
        """获取默认数据库配置"""
        if self.db_type == "sqlite":
            return {
                "database": str(settings.database_dir / "metadata.db")
            }
        elif self.db_type == "mysql":
            return {
                "host": "localhost",
                "port": 3306,
                "database": "taosha_metadata",
                "user": "root",
                "password": ""
            }
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_type}")
    
    def _get_connection(self):
        """获取数据库连接"""
        if self.db_type == "sqlite":
            return sqlite3.connect(self.db_config["database"])
        elif self.db_type == "mysql":
            return mysql.connector.connect(**self.db_config)
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_type}")
    
    def _init_database(self):
        """初始化数据库表结构"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if self.db_type == "sqlite":
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS glossary_terms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        term TEXT UNIQUE NOT NULL,
                        definition TEXT,
                        sql_expression TEXT,
                        category TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS glossary_aliases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        term_id INTEGER NOT NULL,
                        alias TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (term_id) REFERENCES glossary_terms(id) ON DELETE CASCADE,
                        UNIQUE(alias)
                    )
                """)
            elif self.db_type == "mysql":
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS glossary_terms (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        term VARCHAR(255) UNIQUE NOT NULL,
                        definition TEXT,
                        sql_expression TEXT,
                        category VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS glossary_aliases (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        term_id INT NOT NULL,
                        alias VARCHAR(255) NOT NULL UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (term_id) REFERENCES glossary_terms(id) ON DELETE CASCADE
                    )
                """)
            
            conn.commit()
            conn.close()
            logger.info(f"术语表数据库初始化完成: {self.db_type}")
            
        except Exception as e:
            logger.error(f"术语表数据库初始化失败: {e}")
            raise
    
    def _load_glossary(self) -> Dict[str, Any]:
        """从数据库加载术语表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, term, definition, sql_expression, category 
                FROM glossary_terms 
                ORDER BY term
            """)
            terms_data = cursor.fetchall()
            
            terms = []
            for term_id, term, definition, sql_expr, category in terms_data:
                cursor.execute(
                    "SELECT alias FROM glossary_aliases WHERE term_id = ?",
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
            
            conn.close()
            logger.info(f"术语表已从{self.db_type}数据库加载，共{len(terms)}个术语")
            
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
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO glossary_terms (term, definition, sql_expression, category) 
                VALUES (?, ?, ?, ?)
            """, (term, definition, sql_expression, category))
            
            term_id = cursor.lastrowid
            
            if aliases:
                for alias in aliases:
                    cursor.execute(
                        "INSERT INTO glossary_aliases (term_id, alias) VALUES (?, ?)",
                        (term_id, alias)
                    )
            
            conn.commit()
            conn.close()
            logger.info(f"添加术语成功: {term}")
            return True
            
        except Exception as e:
            logger.error(f"添加术语失败: {e}")
            return False
    
    def update_term(self, term_id: int, term: str = None, definition: str = None, 
                   sql_expression: str = None, category: str = None) -> bool:
        """更新术语"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if term is not None:
                updates.append("term = ?")
                params.append(term)
            if definition is not None:
                updates.append("definition = ?")
                params.append(definition)
            if sql_expression is not None:
                updates.append("sql_expression = ?")
                params.append(sql_expression)
            if category is not None:
                updates.append("category = ?")
                params.append(category)
            
            updates.append("updated_at = ?")
            params.append(datetime.now())
            params.append(term_id)
            
            cursor.execute(
                f"UPDATE glossary_terms SET {', '.join(updates)} WHERE id = ?",
                params
            )
            
            conn.commit()
            conn.close()
            logger.info(f"更新术语成功: ID {term_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新术语失败: {e}")
            return False
    
    def delete_term(self, term_id: int) -> bool:
        """删除术语"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM glossary_terms WHERE id = ?", (term_id,))
            
            conn.commit()
            conn.close()
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
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, term, definition, sql_expression, category 
            FROM glossary_terms 
            ORDER BY term
        """)
        terms_data = cursor.fetchall()
        
        terms = []
        for term_id, term, definition, sql_expr, category in terms_data:
            cursor.execute(
                "SELECT alias FROM glossary_aliases WHERE term_id = ?",
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
        
        conn.close()
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
        _metadata_service = MetadataService(db_type=\"sqlite\")
    return _metadata_service

def get_glossary_service() -> GlossaryService:
    """获取术语表服务实例"""
    global _glossary_service
    if _glossary_service is None:
        _glossary_service = GlossaryService(db_type=\"sqlite\")
    return _glossary_service