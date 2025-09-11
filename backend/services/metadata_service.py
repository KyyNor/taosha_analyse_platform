"""
元数据和术语表管理服务
"""

import json
from pathlib import Path
from loguru import logger
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

from config import settings


class MetadataService:
    """元数据管理服务"""
    
    def __init__(self, metadata_file: str = None):
        self.metadata_file = metadata_file or settings.metadata_file
        self._metadata = None
        self._metadata_hash = None
        self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """加载元数据"""
        try:
            if Path(self.metadata_file).exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self._metadata = json.loads(content)
                    self._metadata_hash = hashlib.md5(content.encode()).hexdigest()
                    logger.info(f"Metadata loaded from {self.metadata_file}")
            else:
                logger.warning(f"Metadata file not found: {self.metadata_file}")
                self._metadata = {"tables": []}
                self._metadata_hash = None
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
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
    
    def has_changed(self) -> bool:
        """检查元数据是否已变化"""
        if not Path(self.metadata_file).exists():
            return self._metadata_hash is not None
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                content = f.read()
                current_hash = hashlib.md5(content.encode()).hexdigest()
                return current_hash != self._metadata_hash
        except Exception as e:
            logger.error(f"Failed to check metadata changes: {e}")
            return True
    
    def reload_if_changed(self) -> bool:
        """如果有变化则重新加载元数据"""
        if self.has_changed():
            self._load_metadata()
            logger.info("Metadata reloaded due to changes")
            return True
        return False

class GlossaryService:
    """术语表管理服务"""
    
    def __init__(self, glossary_file: str = None):
        self.glossary_file = glossary_file or settings.glossary_file
        self._glossary = None
        self._glossary_hash = None
        self._load_glossary()
    
    def _load_glossary(self) -> Dict[str, Any]:
        """加载术语表"""
        try:
            if Path(self.glossary_file).exists():
                with open(self.glossary_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self._glossary = json.loads(content)
                    self._glossary_hash = hashlib.md5(content.encode()).hexdigest()
                    logger.info(f"Glossary loaded from {self.glossary_file}")
            else:
                logger.warning(f"Glossary file not found: {self.glossary_file}")
                self._glossary = {"terms": []}
                self._glossary_hash = None
        except Exception as e:
            logger.error(f"Failed to load glossary: {e}")
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
    
    def has_changed(self) -> bool:
        """检查术语表是否已变化"""
        if not Path(self.glossary_file).exists():
            return self._glossary_hash is not None
        
        try:
            with open(self.glossary_file, 'r', encoding='utf-8') as f:
                content = f.read()
                current_hash = hashlib.md5(content.encode()).hexdigest()
                return current_hash != self._glossary_hash
        except Exception as e:
            logger.error(f"Failed to check glossary changes: {e}")
            return True
    
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