"""
元数据和术语表管理服务
"""

import json
from utils.logger import logger
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

from utils.config import settings
from utils.db_utils import get_database_manager


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
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                
                cursor.execute("SELECT id, name, comment, is_available, created_at, updated_at FROM metadata_tables ORDER BY name")
                tables_data = cursor.fetchall()

                tables = []
                for table_id, table_name, table_comment, is_available, created_at, updated_at in tables_data:
                    placeholder = self.db_manager.get_sql_placeholder(db_type)
                    cursor.execute(f"""
                        SELECT name, type, comment, is_available, business_type, relation_id 
                        FROM metadata_columns 
                        WHERE table_name = {placeholder} 
                        ORDER BY name
                    """, (table_name,))
                    columns_data = cursor.fetchall()
                    
                    columns = []
                    for col_name, col_type, col_comment, col_is_available, business_type, relation_id in columns_data:
                        columns.append({
                            "name": col_name,
                            "type": col_type,
                            "comment": col_comment or "",
                            "is_available": int(col_is_available or 0),
                            "business_type": business_type or "",
                            "relation_id": relation_id or ""
                        })
                    
                    tables.append({
                        "id": table_id,
                        "name": table_name,
                        "comment": table_comment or "",
                        "is_available": int(is_available or 0),
                        "created_at": created_at or "",
                        "updated_at": updated_at or "",
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
    
    def add_table(self, table_name: str, comment: str = "", is_available: int = 0) -> bool:
        """添加表元数据"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                cursor.execute(
                    f"INSERT INTO metadata_tables (name, comment, is_available) VALUES ({placeholder}, {placeholder}, {placeholder})",
                    (table_name, comment, is_available)
                )
                
            logger.info(f"添加表元数据成功: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"添加表元数据失败: {e}")
            return False
    
    def update_table(self, table_name: str, comment: str = None, is_available: int = None) -> bool:
        """更新表元数据"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                updates = []
                params = []
                
                if comment is not None:
                    updates.append(f"comment = {placeholder}")
                    params.append(comment)
                if is_available is not None:
                    updates.append(f"is_available = {placeholder}")
                    params.append(is_available)
                
                updates.append(f"updated_at = {placeholder}")
                params.append(datetime.now())
                params.append(table_name)
                
                cursor.execute(
                    f"UPDATE metadata_tables SET {', '.join(updates)} WHERE name = {placeholder}",
                    params
                )
                
            logger.info(f"更新表元数据成功: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"更新表元数据失败: {e}")
            return False
    
    def delete_table(self, table_name: str) -> bool:
        """删除表元数据"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                cursor.execute(f"DELETE FROM metadata_tables WHERE name = {placeholder}", (table_name,))
                
            logger.info(f"删除表元数据成功: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"删除表元数据失败: {e}")
            return False
    
    def add_column(self, table_name: str, column_name: str, column_type: str, 
                   comment: str = "", is_available: int = 0, business_type: str = "", relation_id: str = "") -> bool:
        """添加列元数据"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                cursor.execute(f"""
                    INSERT INTO metadata_columns (table_name, name, type, comment, is_available, business_type, relation_id) 
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                """, (table_name, column_name, column_type, comment, is_available, business_type, relation_id))
                
            logger.info(f"添加列元数据成功: {table_name}.{column_name}")
            return True
            
        except Exception as e:
            logger.error(f"添加列元数据失败: {e}")
            return False
    
    def update_column(self, table_name: str, column_name: str, column_type: str = None,
                     comment: str = None, is_available: int = None, business_type: str = None, relation_id: str = None) -> bool:
        """更新列元数据"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
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
                if is_available is not None:
                    updates.append(f"is_available = {placeholder}")
                    params.append(is_available)
                if business_type is not None:
                    updates.append(f"business_type = {placeholder}")
                    params.append(business_type)
                if relation_id is not None:
                    updates.append(f"relation_id = {placeholder}")
                    params.append(relation_id)
                
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
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
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
    
    def _load_metadata_from_db(self) -> Dict[str, Any]:
        """从数据库加载元数据（不更新实例状态）"""
        with self.db_manager.get_taosha_db_connection() as (conn, db_type):
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, name, comment, is_available, created_at, updated_at FROM metadata_tables ORDER BY name")
            tables_data = cursor.fetchall()

            tables = []
            for table_id, table_name, table_comment, is_available, created_at, updated_at in tables_data:
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                cursor.execute(f"""
                    SELECT name, type, comment, is_available, business_type, relation_id 
                    FROM metadata_columns 
                    WHERE table_name = {placeholder} 
                    ORDER BY name
                """, (table_name,))
                columns_data = cursor.fetchall()
                
                columns = []
                for col_name, col_type, col_comment, col_is_available, business_type, relation_id in columns_data:
                    columns.append({
                        "name": col_name,
                        "type": col_type,
                        "comment": col_comment or "",
                        "is_available": int(col_is_available or 0),
                        "business_type": business_type or "",
                        "relation_id": relation_id or ""
                    })
                
                tables.append({
                    "id": table_id,
                    "name": table_name,
                    "comment": table_comment or "",
                    "is_available": int(is_available or 0),
                    "created_at": created_at or "",
                    "updated_at": updated_at or "",
                    "columns": columns
                })
            
            return {"tables": tables}
    
    def get_available_tables(self) -> List[Dict[str, Any]]:
        """获取所有可用的表信息（is_available = 0）"""
        all_tables = self.get_tables()
        return [table for table in all_tables if table.get('is_available', 0) == 0]

class RelationFieldConfigService:
    """关联字段配置管理服务"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
    
    def get_all_relation_configs(self) -> List[Dict[str, Any]]:
        """获取所有关联字段配置"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT relation_id, relation_family, relation_subfamily, relation_desc
                    FROM relation_field_config 
                    ORDER BY relation_family, relation_subfamily
                """)
                configs_data = cursor.fetchall()
                
                configs = []
                for relation_id, family, subfamily, desc in configs_data:
                    configs.append({
                        "relation_id": relation_id,
                        "relation_family": family,
                        "relation_subfamily": subfamily,
                        "relation_desc": desc or ""
                    })
                
                return configs
                
        except Exception as e:
            logger.error(f"获取关联字段配置失败: {e}")
            return []
    
    def add_relation_config(self, family: str, subfamily: str, desc: str = "") -> bool:
        """添加关联字段配置"""
        try:
            relation_id = f"{family}|{subfamily}"
            
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                cursor.execute(f"""
                    INSERT INTO relation_field_config (relation_id, relation_family, relation_subfamily, relation_desc) 
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                """, (relation_id, family, subfamily, desc))
                
            logger.info(f"添加关联字段配置成功: {relation_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加关联字段配置失败: {e}")
            return False
    
    def update_relation_config(self, relation_id: str, family: str = None, subfamily: str = None, desc: str = None) -> bool:
        """更新关联字段配置"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                updates = []
                params = []
                
                # 如果family或subfamily有变化，需要更新relation_id
                new_relation_id = relation_id
                if family is not None or subfamily is not None:
                    # 获取当前的family和subfamily
                    cursor.execute(
                        f"SELECT relation_family, relation_subfamily FROM relation_field_config WHERE relation_id = {placeholder}",
                        (relation_id,)
                    )
                    result = cursor.fetchone()
                    if result:
                        current_family, current_subfamily = result
                        new_family = family if family is not None else current_family
                        new_subfamily = subfamily if subfamily is not None else current_subfamily
                        new_relation_id = f"{new_family}|{new_subfamily}"
                        
                        updates.append(f"relation_id = {placeholder}")
                        params.append(new_relation_id)
                        
                        if family is not None:
                            updates.append(f"relation_family = {placeholder}")
                            params.append(family)
                        if subfamily is not None:
                            updates.append(f"relation_subfamily = {placeholder}")
                            params.append(subfamily)
                
                if desc is not None:
                    updates.append(f"relation_desc = {placeholder}")
                    params.append(desc)
                
                if updates:
                    params.append(relation_id)
                    cursor.execute(
                        f"UPDATE relation_field_config SET {', '.join(updates)} WHERE relation_id = {placeholder}",
                        params
                    )
                
            logger.info(f"更新关联字段配置成功: {relation_id} -> {new_relation_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新关联字段配置失败: {e}")
            return False
    
    def delete_relation_config(self, relation_id: str) -> bool:
        """删除关联字段配置"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                cursor.execute(f"DELETE FROM relation_field_config WHERE relation_id = {placeholder}", (relation_id,))
                
            logger.info(f"删除关联字段配置成功: {relation_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除关联字段配置失败: {e}")
            return False
    
    def get_relation_ids(self) -> List[str]:
        """获取所有关联ID列表"""
        configs = self.get_all_relation_configs()
        return [config['relation_id'] for config in configs]

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
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT id, name, type, content, creator, created_at, updated_at
                    FROM glossary_terms
                    ORDER BY name
                """)
                terms_data = cursor.fetchall()

                terms = []
                for term_id, name, term_type, content, creator, created_at, updated_at in terms_data:
                    # 解析 JSON content
                    try:
                        content_data = json.loads(content) if content else {}
                    except json.JSONDecodeError:
                        content_data = {}
                        logger.warning(f"术语 {name} 的 content 字段不是有效的 JSON 格式")

                    terms.append({
                        "id": term_id,
                        "name": name,
                        "type": term_type,
                        "content": content_data,
                        "creator": creator or "",
                        "created_at": created_at if created_at else "",
                        "updated_at": updated_at if updated_at else ""
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
            if term.get("name", "").lower() == query_lower:
                return term

        return None
    
    def get_terms_by_type(self, term_type: str) -> List[Dict[str, Any]]:
        """根据类型获取术语"""
        return [term for term in self.get_terms() if term.get("type") == term_type]
    
    def add_term(self, name: str, term_type: str, content: Dict[str, Any], creator: str) -> bool:
        """添加术语"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)

                # 将 content 转换为 JSON 字符串
                content_json = json.dumps(content, ensure_ascii=False)

                cursor.execute(f"""
                    INSERT INTO glossary_terms (name, type, content, creator)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                """, (name, term_type, content_json, creator))

            logger.info(f"添加术语成功: {name}")
            # 重新加载术语表
            self._load_glossary()
            return True

        except Exception as e:
            logger.error(f"添加术语失败: {e}")
            return False
    
    def update_term(self, term_id: int, name: str = None, term_type: str = None,
                   content: Dict[str, Any] = None) -> bool:
        """更新术语"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                updates = []
                params = []
                
                if name is not None:
                    updates.append(f"name = {placeholder}")
                    params.append(name)
                if term_type is not None:
                    updates.append(f"type = {placeholder}")
                    params.append(term_type)
                if content is not None:
                    updates.append(f"content = {placeholder}")
                    content_json = json.dumps(content, ensure_ascii=False)
                    params.append(content_json)
                
                updates.append(f"updated_at = {placeholder}")
                params.append(datetime.now())
                params.append(term_id)
                
                cursor.execute(
                    f"UPDATE glossary_terms SET {', '.join(updates)} WHERE id = {placeholder}",
                    params
                )
                
            logger.info(f"更新术语成功: ID {term_id}")
            # 重新加载术语表
            self._load_glossary()
            return True
            
        except Exception as e:
            logger.error(f"更新术语失败: {e}")
            return False
    
    def delete_term(self, term_id: int) -> bool:
        """删除术语"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)
                
                cursor.execute(f"DELETE FROM glossary_terms WHERE id = {placeholder}", (term_id,))
                
            logger.info(f"删除术语成功: ID {term_id}")
            # 重新加载术语表
            self._load_glossary()
            return True
            
        except Exception as e:
            logger.error(f"删除术语失败: {e}")
            return False
    
    def _load_glossary_from_db(self) -> Dict[str, Any]:
        """从数据库加载术语表（不更新实例状态）"""
        with self.db_manager.get_taosha_db_connection() as (conn, db_type):
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, name, type, content, creator, created_at, updated_at
                FROM glossary_terms
                ORDER BY name
            """)
            terms_data = cursor.fetchall()

            terms = []
            for term_id, name, term_type, content, creator, created_at, updated_at in terms_data:
                # 解析 JSON content
                try:
                    content_data = json.loads(content) if content else {}
                except json.JSONDecodeError:
                    content_data = {}
                    logger.warning(f"术语 {name} 的 content 字段不是有效的 JSON 格式")

                terms.append({
                    "id": term_id,
                    "name": name,
                    "type": term_type,
                    "content": content_data,
                    "creator": creator or "",
                    "created_at": created_at if created_at else "",
                    "updated_at": updated_at if updated_at else ""
                })

            return {"terms": terms}


class PromptTemplateService:
    """提示词模板管理服务"""

    def __init__(self):
        self.db_manager = get_database_manager()
        self._templates = None
        self._templates_hash = None
        self._load_templates()

    def _load_templates(self) -> Dict[str, Any]:
        """从数据库加载提示词模板"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT id, name, fields, template, created_at, updated_at
                    FROM prompt_templates
                    ORDER BY name
                """)
                templates_data = cursor.fetchall()

                templates = []
                for template_id, name, fields, template, created_at, updated_at in templates_data:
                    # 解析 JSON fields
                    try:
                        fields_data = json.loads(fields) if fields else []
                    except json.JSONDecodeError:
                        fields_data = []
                        logger.warning(f"提示词模板 {name} 的 fields 字段不是有效的 JSON 格式")

                    templates.append({
                        "id": template_id,
                        "name": name,
                        "fields": fields_data,
                        "template": template or "",
                        "created_at": created_at if created_at else "",
                        "updated_at": updated_at if updated_at else ""
                    })

                self._templates = {"templates": templates}
                content_str = json.dumps(self._templates, sort_keys=True, ensure_ascii=False)
                self._templates_hash = hashlib.md5(content_str.encode()).hexdigest()

                logger.info(f"提示词模板已从{db_type}数据库加载，共{len(templates)}个模板")

        except Exception as e:
            logger.error(f"从数据库加载提示词模板失败: {e}")
            self._templates = {"templates": []}
            self._templates_hash = None

    def get_templates(self) -> List[Dict[str, Any]]:
        """获取所有提示词模板"""
        return self.get_templates_data().get("templates", [])

    def get_templates_data(self) -> Dict[str, Any]:
        """获取提示词模板数据"""
        return self._templates or {"templates": []}

    def get_template_by_id(self, template_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取提示词模板"""
        for template in self.get_templates():
            if template.get("id") == template_id:
                return template
        return None

    def get_template_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取提示词模板"""
        for template in self.get_templates():
            if template.get("name") == name:
                return template
        return None

    def validate_template(self, fields: List[str], template: str) -> List[str]:
        """验证模板中的占位符是否与字段匹配"""
        import re

        # 找出模板中的所有占位符 {field_name}
        placeholders = set(re.findall(r'\{(\w+)\}', template))

        # 找出字段列表中的字段
        field_set = set(fields)

        errors = []

        # 检查是否有模板中的占位符不在字段列表中
        missing_fields = placeholders - field_set
        if missing_fields:
            errors.append(f"模板中使用了不存在的字段: {', '.join(missing_fields)}")

        # 检查是否有字段列表中的字段未在模板中使用
        unused_fields = field_set - placeholders
        if unused_fields:
            errors.append(f"字段列表中有未使用的字段: {', '.join(unused_fields)}")

        return errors

    def add_template(self, name: str, fields: List[str], template: str) -> bool:
        """添加提示词模板"""
        try:
            # 验证模板
            errors = self.validate_template(fields, template)
            if errors:
                for error in errors:
                    logger.error(f"模板验证失败: {error}")
                return False

            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)

                # 将 fields 转换为 JSON 字符串
                fields_json = json.dumps(fields, ensure_ascii=False)

                cursor.execute(f"""
                    INSERT INTO prompt_templates (name, fields, template)
                    VALUES ({placeholder}, {placeholder}, {placeholder})
                """, (name, fields_json, template))

            logger.info(f"添加提示词模板成功: {name}")
            # 重新加载模板
            self._load_templates()
            return True

        except Exception as e:
            logger.error(f"添加提示词模板失败: {e}")
            return False

    def update_template(self, template_id: int, name: str = None, template: str = None) -> bool:
        """更新提示词模板"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)

                # 获取当前模板信息
                current_template = self.get_template_by_id(template_id)
                if not current_template:
                    logger.error(f"模板不存在: ID {template_id}")
                    return False

                updates = []
                params = []

                if name is not None:
                    updates.append(f"name = {placeholder}")
                    params.append(name)

                if template is not None:
                    # 验证模板（使用当前的字段列表）
                    errors = self.validate_template(current_template.get("fields", []), template)
                    if errors:
                        for error in errors:
                            logger.error(f"模板验证失败: {error}")
                        return False

                    updates.append(f"template = {placeholder}")
                    params.append(template)

                if updates:
                    updates.append(f"updated_at = {placeholder}")
                    params.append(datetime.now())
                    params.append(template_id)

                    cursor.execute(
                        f"UPDATE prompt_templates SET {', '.join(updates)} WHERE id = {placeholder}",
                        params
                    )

            logger.info(f"更新提示词模板成功: ID {template_id}")
            # 重新加载模板
            self._load_templates()
            return True

        except Exception as e:
            logger.error(f"更新提示词模板失败: {e}")
            return False

    def delete_template(self, template_id: int) -> bool:
        """删除提示词模板"""
        try:
            with self.db_manager.get_taosha_db_connection() as (conn, db_type):
                cursor = conn.cursor()
                placeholder = self.db_manager.get_sql_placeholder(db_type)

                cursor.execute(f"DELETE FROM prompt_templates WHERE id = {placeholder}", (template_id,))

            logger.info(f"删除提示词模板成功: ID {template_id}")
            # 重新加载模板
            self._load_templates()
            return True

        except Exception as e:
            logger.error(f"删除提示词模板失败: {e}")
            return False


# 全局服务实例
_metadata_service: Optional[MetadataService] = None
_glossary_service: Optional[GlossaryService] = None
_relation_field_config_service: Optional[RelationFieldConfigService] = None
_prompt_template_service: Optional[PromptTemplateService] = None

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

def get_relation_field_config_service() -> RelationFieldConfigService:
    """获取关联字段配置服务实例"""
    global _relation_field_config_service
    if _relation_field_config_service is None:
        _relation_field_config_service = RelationFieldConfigService()
    return _relation_field_config_service

def get_prompt_template_service() -> PromptTemplateService:
    """获取提示词模板服务实例"""
    global _prompt_template_service
    if _prompt_template_service is None:
        _prompt_template_service = PromptTemplateService()
    return _prompt_template_service