"""
元数据和术语表管理服务 - SQLAlchemy Repository版本
"""

import json
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from repositories import (
    MetadataTableRepository, MetadataColumnRepository,
    GlossaryTermRepository, PromptTemplateRepository,
    RelationFieldConfigRepository, DataThemeRepository,
    ThemeTableRelationRepository
)
from utils.logger import logger


class MetadataService:
    """元数据管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.table_repo = MetadataTableRepository(db)
        self.column_repo = MetadataColumnRepository(db)

    def _build_metadata_dict(self, is_available: str, include_fields: bool, table_name_filter: str) -> Dict[str, Any]:
        """从数据库动态构建元数据字典"""
        try:
            tables_with_columns = self.table_repo.get_filter_tables_with_columns(is_available, include_fields, table_name_filter)

            tables = []
            for table in tables_with_columns:
                # 在访问属性之前先获取所有需要的值，避免会话问题
                table_id = table.id
                table_name = table.name
                table_comment = table.comment or ""
                table_is_available = int(table.is_available or 0)
                table_created_at = table.created_at
                table_updated_at = table.updated_at

                # 获取列信息
                columns_list = []
                if hasattr(table, 'columns') and table.columns:
                    for column in table.columns:
                        if column is not None:
                            column_dict = {
                                "id": column.id,
                                "name": column.name,
                                "type": column.type,
                                "comment": column.comment or "",
                                "remark": column.remark or "",
                                "is_available": int(column.is_available or 0),
                                "business_type": column.business_type or "",
                                "relation_config_id": column.relation_config_id or ""
                            }
                            columns_list.append(column_dict)

                # 转换为字典格式
                table_remark = table.remark or ""
                table_dict = {
                    "id": table_id,
                    "name": table_name,
                    "comment": table_comment,
                    "remark": table_remark,
                    "is_available": table_is_available,
                    "created_at": table_created_at,
                    "updated_at": table_updated_at,
                    "columns": columns_list
                }

                tables.append(table_dict)

            logger.debug(f"元数据已从数据库加载，共{len(tables)}张表")
            return {"tables": tables}

        except Exception as e:
            logger.error(f"从数据库加载元数据失败: {e}")
            return {"tables": []}


    def get_tables(self, is_available: Optional[str] = None,include_fields: Optional[bool] = True,table_name_filter: Optional[str] = None,) -> List[Dict[str, Any]]:
        """获取所有表信息"""
        return self._build_metadata_dict(
            is_available=is_available,
            include_fields=include_fields,
            table_name_filter=table_name_filter
        ).get("tables", [])

    def get_table_by_id(self, table_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取单个表信息（不包含字段列表）"""
        try:
            table = self.table_repo.get_with_columns(table_id)
            if not table:
                logger.warning(f"表不存在: ID {table_id}")
                return None

            # 转换为字典格式，只返回表信息
            table_dict = {
                "id": table.id,
                "name": table.name,
                "comment": table.comment or "",
                "remark": table.remark or "",
                "is_available": int(table.is_available or 0),
                "created_at": table.created_at,
                "updated_at": table.updated_at
            }

            logger.info(f"获取表信息成功: ID {table_id}")
            return table_dict

        except Exception as e:
            logger.error(f"获取表信息失败: {e}")
            raise

    def add_table(self, table_name: str, comment: str = "", remark: str = "", is_available: int = 0) -> Optional[Dict[str, Any]]:
        """添加表元数据"""
        try:
            table = self.table_repo.create(
                name=table_name,
                comment=comment,
                remark=remark,
                is_available=is_available
            )

            # 转换为字典格式返回
            table_dict = {
                "id": table.id,
                "name": table.name,
                "comment": table.comment or "",
                "remark": table.remark or "",
                "is_available": int(table.is_available or 0),
                "created_at": table.created_at,
                "updated_at": table.updated_at,
                "columns": []
            }

            logger.info(f"添加表元数据成功: {table_name}")
            return table_dict

        except Exception as e:
            logger.error(f"添加表元数据失败: {e}")
            return None

    # 已废弃: 使用 update_table_by_id(table_id, comment, is_available) 替代

    def update_table_by_id(self, table_id: int, comment: str = None, remark: str = None, is_available: int = None) -> bool:
        """更新表元数据（按ID）"""
        try:
            # 准备更新数据
            update_data = {}
            if comment is not None:
                update_data['comment'] = comment
            if remark is not None:
                update_data['remark'] = remark
            if is_available is not None:
                update_data['is_available'] = is_available

            if update_data:
                self.table_repo.update(table_id, **update_data)

            logger.info(f"更新表元数据成功: ID {table_id}")
            return True

        except Exception as e:
            logger.error(f"更新表元数据失败: {e}")
            return False


    def delete_table_by_id(self, table_id: int) -> bool:
        """删除表元数据（按ID）"""
        try:
            self.table_repo.delete(table_id)

            logger.info(f"删除表元数据成功: ID {table_id}")
            return True

        except Exception as e:
            logger.error(f"删除表元数据失败: {e}")
            return False

    def add_column_by_id(self, table_id: int, column_name: str, column_type: str,
                          comment: str = "", remark: str = "", is_available: int = 0, business_type: str = "", relation_config_id: int = None) -> Optional[Dict[str, Any]]:
        """添加列元数据（按表ID）"""
        try:
            # 检查表是否存在
            table = self.table_repo.get_by_id(table_id)
            if not table:
                logger.error(f"表不存在: ID {table_id}")
                return None

            # 查找关联配置（如果有relation_config_id）
            if relation_config_id:
                relation_config_repo = RelationFieldConfigRepository(self.db)
                relation_config = relation_config_repo.get_by_id(relation_config_id)
                if not relation_config:
                    logger.warning(f"关联配置不存在: ID {relation_config_id}")
                    relation_config_id = None

            column = self.column_repo.create(
                table_id=table_id,
                name=column_name,
                type=column_type,
                comment=comment,
                remark=remark,
                is_available=is_available,
                business_type=business_type,
                relation_config_id=relation_config_id
            )

            # 转换为字典格式返回
            column_dict = {
                "id": column.id,
                "table_id": column.table_id,
                "name": column.name,
                "type": column.type,
                "comment": column.comment or "",
                "remark": column.remark or "",
                "is_available": int(column.is_available or 0),
                "business_type": column.business_type or "",
                "relation_config_id": column.relation_config_id
            }

            logger.info(f"添加列元数据成功: 表ID {table_id}.{column_name}")
            return column_dict

        except Exception as e:
            logger.error(f"添加列元数据失败: {e}")
            return None

    def add_column(self, table_name: str, column_name: str, column_type: str,
                   comment: str = "", is_available: int = 0, business_type: str = "", relation_config_id: int = None) -> bool:
        """添加列元数据（向后兼容，按表名）"""
        try:
            # 先找到表记录
            table = self.table_repo.get_by_name(table_name)
            if not table:
                logger.error(f"表不存在: {table_name}")
                return False

            result = self.add_column_by_id(
                table.id, column_name, column_type, comment,
                is_available, business_type, relation_config_id
            )
            return result is not True

        except Exception as e:
            logger.error(f"添加列元数据失败: {e}")
            return False

    # 已废弃: 使用 update_column_by_table_id(table_id, column_name, ...) 替代

    def update_column_by_table_id(self, table_id: int, column_name: str, column_type: str = None,
                                  comment: str = None, remark: str = None, is_available: int = None, business_type: str = None,
                                  relation_config_id: int = None) -> bool:
        """更新列元数据（按表ID）"""
        try:
            # 找到列记录
            column = self.column_repo.get_by_table_and_name(table_id, column_name)
            if not column:
                logger.error(f"列不存在: 表ID {table_id}.{column_name}")
                return False

            # 准备更新数据
            update_data = {}
            if column_type is not None:
                update_data['type'] = column_type
            if comment is not None:
                update_data['comment'] = comment
            if remark is not None:
                update_data['remark'] = remark
            if is_available is not None:
                update_data['is_available'] = is_available
            if business_type is not None:
                update_data['business_type'] = business_type
            if relation_config_id is not None:
                update_data['relation_config_id'] = relation_config_id

            if update_data:
                self.column_repo.update(column.id, **update_data)

            logger.info(f"更新列元数据成功: 表ID {table_id}.{column_name}")
            return True

        except Exception as e:
            logger.error(f"更新列元数据失败: {e}")
            return False

    def update_column_by_id(self, column_id: int, name: str = None, column_type: str = None,
                           comment: str = None, remark: str = None, is_available: int = None, business_type: str = None,
                           relation_config_id: int = None) -> bool:
        """更新列元数据（按列ID）"""
        try:
            # 准备更新数据
            update_data = {}
            if name is not None:
                update_data['name'] = name
            if column_type is not None:
                update_data['type'] = column_type
            if comment is not None:
                update_data['comment'] = comment
            if remark is not None:
                update_data['remark'] = remark
            if is_available is not None:
                update_data['is_available'] = is_available
            if business_type is not None:
                update_data['business_type'] = business_type
            if relation_config_id is not None:
                update_data['relation_config_id'] = relation_config_id

            if update_data:
                self.column_repo.update(column_id, **update_data)

            logger.info(f"更新列元数据成功: ID {column_id}")
            return True

        except Exception as e:
            logger.error(f"更新列元数据失败: {e}")
            return False

    def delete_column_by_id(self, column_id: int) -> bool:
        """删除列元数据（按列ID）"""
        try:
            self.column_repo.delete(column_id)

            logger.info(f"删除列元数据成功: ID {column_id}")
            return True

        except Exception as e:
            logger.error(f"删除列元数据失败: {e}")
            return False

    # 已废弃: 使用 delete_column_by_table_id(table_id, column_name) 替代

    def get_columns_by_table_id(self, table_id: int) -> List[Dict[str, Any]]:
        """根据表ID获取所有字段"""
        try:
            columns = self.column_repo.get_by_table_id(table_id)

            # 转换为字典格式
            columns_list = []
            for column in columns:
                columns_list.append({
                    "id": column.id,
                    "table_id": column.table_id,
                    "name": column.name,
                    "type": column.type,
                    "comment": column.comment or "",
                    "remark": column.remark or "",
                    "is_available": int(column.is_available or 0),
                    "business_type": column.business_type or "",
                    "relation_config_id": column.relation_config_id
                })

            return columns_list
        except Exception as e:
            logger.error(f"获取表字段失败: {e}")
            raise

    def delete_column_by_table_id(self, table_id: int, column_name: str) -> bool:
        """删除列元数据（按表ID）"""
        try:
            # 找到列记录
            column = self.column_repo.get_by_table_and_name(table_id, column_name)
            if not column:
                logger.error(f"列不存在: 表ID {table_id}.{column_name}")
                return False

            self.column_repo.delete(column.id)

            logger.info(f"删除列元数据成功: 表ID {table_id}.{column_name}")
            return True

        except Exception as e:
            logger.error(f"删除列元数据失败: {e}")
            return False

    def batch_update_table_and_columns(self, table: Dict[str, Any], columns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量更新表和字段元数据"""
        try:
            success_count = 0
            error_count = 0
            errors = []

            # 开始事务
            with self.db.begin():
                # 处理表更新
                if table:
                    try:
                        table_id = table.get('id')
                        if not table_id:
                            error_count += 1
                            errors.append({
                                'type': 'table',
                                'data': table,
                                'error': '表ID不能为空'
                            })
                            # 跳过表更新，继续处理字段
                        else:
                            # 准备更新数据
                            update_data = {}
                            if 'name' in table:
                                update_data['name'] = table['name']
                            if 'comment' in table:
                                update_data['comment'] = table['comment']
                            if 'remark' in table:
                                update_data['remark'] = table['remark']
                            if 'is_available' in table:
                                update_data['is_available'] = table['is_available']

                            # 执行更新
                            if update_data:
                                self.table_repo.update_without_commit(table_id, **update_data)
                                success_count += 1
                                logger.debug(f"更新表成功: ID {table_id}")
                            else:
                                logger.debug(f"表无更新数据: ID {table_id}")
                                success_count += 1

                    except Exception as e:
                        error_count += 1
                        errors.append({
                            'type': 'table',
                            'id': table.get('id'),
                            'error': str(e)
                        })
                        logger.error(f"更新表失败: ID {table.get('id')}, 错误: {e}")

                # 处理字段更新
                for column_data in columns:
                    try:
                        column_id = column_data.get('id')
                        if not column_id:
                            error_count += 1
                            errors.append({
                                'type': 'column',
                                'data': column_data,
                                'error': '字段ID不能为空'
                            })
                            continue

                        # 准备更新数据
                        update_data = {}
                        if 'name' in column_data:
                            update_data['name'] = column_data['name']
                        if 'type' in column_data:
                            update_data['type'] = column_data['type']
                        if 'comment' in column_data:
                            update_data['comment'] = column_data['comment']
                        if 'remark' in column_data:
                            update_data['remark'] = column_data['remark']
                        if 'is_available' in column_data:
                            update_data['is_available'] = column_data['is_available']
                        if 'business_type' in column_data:
                            update_data['business_type'] = column_data['business_type']
                        if 'relation_config_id' in column_data:
                            update_data['relation_config_id'] = column_data['relation_config_id']

                        # 执行更新
                        if update_data:
                            self.column_repo.update_without_commit(column_id, **update_data)
                            success_count += 1
                            logger.debug(f"更新字段成功: ID {column_id}")
                        else:
                            logger.debug(f"字段无更新数据: ID {column_id}")
                            success_count += 1

                    except Exception as e:
                        error_count += 1
                        errors.append({
                            'type': 'column',
                            'id': column_data.get('id'),
                            'error': str(e)
                        })
                        logger.error(f"更新字段失败: ID {column_data.get('id')}, 错误: {e}")

            result = {
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors
            }

            logger.info(f"批量更新完成: 成功 {success_count}, 失败 {error_count}")
            return result

        except Exception as e:
            logger.error(f"批量更新元数据失败: {e}")
            raise


class RelationFieldConfigService:
    """关联字段配置管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = RelationFieldConfigRepository(db)

    def get_relation_config_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取关联字段配置"""
        try:
            config = self.repo.get_by_id(config_id)
            if config:
                return {
                    "id": config.id,
                    "relation_id": f"{config.relation_family}|{config.relation_subfamily}",  # 拼接的关联ID，用于前端显示
                    "relation_family": config.relation_family,
                    "relation_subfamily": config.relation_subfamily,
                    "relation_desc": config.relation_desc or ""
                }
            return None
        except Exception as e:
            logger.error(f"获取关联字段配置失败: {e}")
            return None

    def get_all_relation_configs(self) -> List[Dict[str, Any]]:
        """获取所有关联字段配置"""
        try:
            configs = self.repo.get_all()
            return [
                {
                    "id": config.id,
                    "relation_id": f"{config.relation_family}|{config.relation_subfamily}",  # 拼接的关联ID，用于前端显示
                    "relation_family": config.relation_family,
                    "relation_subfamily": config.relation_subfamily,
                    "relation_desc": config.relation_desc or ""
                }
                for config in configs
            ]
        except Exception as e:
            logger.error(f"获取关联字段配置失败: {e}")
            return []

    def add_relation_config(self, family: str, subfamily: str, desc: str = "") -> Optional[Dict[str, Any]]:
        """添加关联字段配置"""
        try:
            config = self.repo.create(
                relation_family=family,
                relation_subfamily=subfamily,
                relation_desc=desc
            )

            # 转换为字典格式返回
            config_dict = {
                "id": config.id,
                "relation_id": f"{config.relation_family}|{config.relation_subfamily}",  # 拼接的关联ID，用于前端显示
                "relation_family": config.relation_family,
                "relation_subfamily": config.relation_subfamily,
                "relation_desc": config.relation_desc or ""
            }

            logger.info(f"添加关联字段配置成功: {family}|{subfamily}")
            return config_dict

        except Exception as e:
            logger.error(f"添加关联字段配置失败: {e}")
            return None

    def update_relation_config(self, config_id: int, family: str = None, subfamily: str = None, desc: str = None) -> bool:
        """更新关联字段配置"""
        try:
            # 准备更新数据
            update_data = {}
            if family is not None:
                update_data['relation_family'] = family
            if subfamily is not None:
                update_data['relation_subfamily'] = subfamily
            if desc is not None:
                update_data['relation_desc'] = desc

            if update_data:
                self.repo.update(config_id, **update_data)

            logger.info(f"更新关联字段配置成功: ID {config_id}")
            return True

        except Exception as e:
            logger.error(f"更新关联字段配置失败: {e}")
            return False

    def delete_relation_config(self, config_id: int) -> bool:
        """删除关联字段配置"""
        try:
            self.repo.delete(config_id)
            logger.info(f"删除关联字段配置成功: ID {config_id}")
            return True

        except Exception as e:
            logger.error(f"删除关联字段配置失败: {e}")
            return False


class GlossaryService:
    """术语表管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = GlossaryTermRepository(db)

    def _build_glossary_dict(self) -> Dict[str, Any]:
        """从数据库动态构建术语表字典"""
        try:
            terms = self.repo.get_all()

            terms_list = []
            for term in terms:
                # 解析 JSON content
                try:
                    content_data = json.loads(term.content) if term.content else {}
                except json.JSONDecodeError:
                    content_data = {}
                    logger.warning(f"术语 {term.name} 的 content 字段不是有效的 JSON 格式")

                terms_list.append({
                    "id": term.id,
                    "name": term.name,
                    "type": term.type,
                    "content": content_data,
                    "creator": term.creator or "",
                    "is_basic": term.is_basic or False,  # 添加 is_basic 字段
                    "created_at": term.created_at,
                    "updated_at": term.updated_at
                })

            logger.debug(f"术语表已从数据库加载，共{len(terms_list)}个术语")
            return {"terms": terms_list}

        except Exception as e:
            logger.error(f"从数据库加载术语表失败: {e}")
            return {"terms": []}

    def get_glossary(self) -> Dict[str, Any]:
        """获取术语表（直接从数据库查询）"""
        return self._build_glossary_dict()

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

    def add_term(self, name: str, term_type: str, content: Dict[str, Any], creator: str, is_basic: bool = False) -> bool:
        """添加术语"""
        try:
            # 将 content 转换为 JSON 字符串
            content_json = json.dumps(content, ensure_ascii=False)

            self.repo.create(
                name=name,
                type=term_type,
                content=content_json,
                creator=creator,
                is_basic=is_basic
            )

            logger.info(f"添加术语成功: {name}, 基础术语: {is_basic}")
            return True

        except Exception as e:
            logger.error(f"添加术语失败: {e}")
            return False

    def update_term(self, term_id: int, name: str = None, term_type: str = None,
                   content: Dict[str, Any] = None, is_basic: bool = None) -> bool:
        """更新术语"""
        try:
            # 准备更新数据
            update_data = {}
            if name is not None:
                update_data['name'] = name
            if term_type is not None:
                update_data['type'] = term_type
            if content is not None:
                content_json = json.dumps(content, ensure_ascii=False)
                update_data['content'] = content_json
            if is_basic is not None:
                update_data['is_basic'] = is_basic

            if update_data:
                self.repo.update(term_id, **update_data)

            logger.info(f"更新术语成功: ID {term_id}")
            return True

        except Exception as e:
            logger.error(f"更新术语失败: {e}")
            return False

    def delete_term(self, term_id: int) -> bool:
        """删除术语"""
        try:
            self.repo.delete(term_id)

            logger.info(f"删除术语成功: ID {term_id}")
            return True

        except Exception as e:
            logger.error(f"删除术语失败: {e}")
            return False

    def get_basic_terms(self) -> List[Dict[str, Any]]:
        """获取所有基础术语"""
        try:
            terms = self.repo.get_basic_terms()
            return [self._term_to_dict(term) for term in terms]
        except Exception as e:
            logger.error(f"获取基础术语失败: {e}")
            return []

    def get_non_basic_terms(self) -> List[Dict[str, Any]]:
        """获取所有非基础术语"""
        try:
            terms = self.repo.get_non_basic_terms()
            return [self._term_to_dict(term) for term in terms]
        except Exception as e:
            logger.error(f"获取非基础术语失败: {e}")
            return []

    def _term_to_dict(self, term) -> Dict[str, Any]:
        """将术语对象转换为字典"""
        try:
            content_data = json.loads(term.content) if term.content else {}
        except json.JSONDecodeError:
            content_data = {}
            logger.warning(f"术语 {term.name} 的 content 字段不是有效的 JSON 格式")
        
        return {
            "id": term.id,
            "name": term.name,
            "type": term.type,
            "content": content_data,
            "creator": term.creator or "",
            "is_basic": term.is_basic or False,
            "created_at": term.created_at,
            "updated_at": term.updated_at
        }


class PromptTemplateService:
    """提示词模板管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = PromptTemplateRepository(db)

    def _build_templates_dict(self) -> Dict[str, Any]:
        """从数据库动态构建提示词模板字典"""
        try:
            templates = self.repo.get_all()

            templates_list = []
            for template in templates:
                # 解析 JSON fields
                try:
                    fields_data = json.loads(template.fields) if template.fields else []
                except json.JSONDecodeError:
                    fields_data = []
                    logger.warning(f"提示词模板 {template.name} 的 fields 字段不是有效的 JSON 格式")

                templates_list.append({
                    "id": template.id,
                    "name": template.name,
                    "fields": fields_data,
                    "template": template.template or "",
                    "created_at": template.created_at,
                    "updated_at": template.updated_at
                })

            logger.debug(f"提示词模板已从数据库加载，共{len(templates_list)}个模板")
            return {"templates": templates_list}

        except Exception as e:
            logger.error(f"从数据库加载提示词模板失败: {e}")
            return {"templates": []}

    def get_templates(self) -> List[Dict[str, Any]]:
        """获取所有提示词模板"""
        return self.get_templates_data().get("templates", [])

    def get_templates_data(self) -> Dict[str, Any]:
        """获取提示词模板数据（直接从数据库查询）"""
        return self._build_templates_dict()

    def get_template_by_id(self, template_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取提示词模板"""
        for template in self.get_templates():
            if template.get("id") == template_id:
                return template
        return None

    def get_template_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取提示词模板"""
        template = self.repo.get_by_name(name)
        if template:
            return self.get_template_by_id(template.id)
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

            # 将 fields 转换为 JSON 字符串
            fields_json = json.dumps(fields, ensure_ascii=False)

            self.repo.create(
                name=name,
                fields=fields_json,
                template=template
            )

            logger.info(f"添加提示词模板成功: {name}")
            return True

        except Exception as e:
            logger.error(f"添加提示词模板失败: {e}")
            return False

    def update_template(self, template_id: int, name: str = None, template: str = None) -> bool:
        """更新提示词模板"""
        try:
            # 获取当前模板信息
            current_template = self.get_template_by_id(template_id)
            if not current_template:
                logger.error(f"模板不存在: ID {template_id}")
                return False

            # 准备更新数据
            update_data = {}
            if name is not None:
                update_data['name'] = name

            if template is not None:
                # 验证模板（使用当前的字段列表）
                errors = self.validate_template(current_template.get("fields", []), template)
                if errors:
                    for error in errors:
                        logger.error(f"模板验证失败: {error}")
                    return False

                update_data['template'] = template

            if update_data:
                self.repo.update(template_id, **update_data)

            logger.info(f"更新提示词模板成功: ID {template_id}")
            return True

        except Exception as e:
            logger.error(f"更新提示词模板失败: {e}")
            return False

    def delete_template(self, template_id: int) -> bool:
        """删除提示词模板"""
        try:
            self.repo.delete(template_id)

            logger.info(f"删除提示词模板成功: ID {template_id}")
            return True

        except Exception as e:
            logger.error(f"删除提示词模板失败: {e}")
            return False


class DataThemeService:
    """数据主题管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.theme_repo = DataThemeRepository(db)
        self.relation_repo = ThemeTableRelationRepository(db)
        self.table_repo = MetadataTableRepository(db)

    def get_all_themes(self) -> List[Dict[str, Any]]:
        """获取所有数据主题"""
        try:
            themes = self.theme_repo.get_all()
            return [
                {
                    "id": theme.id,
                    "theme_name": theme.theme_name,
                    "theme_description": theme.theme_description or "",
                    "theme_type": theme.theme_type,
                    "department": theme.department or "",
                    "created_at": theme.created_at,
                    "updated_at": theme.updated_at
                }
                for theme in themes
            ]
        except Exception as e:
            logger.error(f"获取数据主题失败: {e}")
            return []

    def get_theme_by_id(self, theme_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取数据主题"""
        try:
            theme = self.theme_repo.get_by_id(theme_id)
            if theme:
                return {
                    "id": theme.id,
                    "theme_name": theme.theme_name,
                    "theme_description": theme.theme_description or "",
                    "theme_type": theme.theme_type,
                    "department": theme.department or "",
                    "created_at": theme.created_at,
                    "updated_at": theme.updated_at
                }
            return None
        except Exception as e:
            logger.error(f"获取数据主题失败: {e}")
            return None

    def get_theme_by_name(self, theme_name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取数据主题"""
        try:
            theme = self.theme_repo.get_by_name(theme_name)
            if theme:
                return self.get_theme_by_id(theme.id)
            return None
        except Exception as e:
            logger.error(f"获取数据主题失败: {e}")
            return None

    def add_theme(self, theme_name: str, theme_description: str = "", theme_type: str = "normal", department: str = "") -> Optional[Dict[str, Any]]:
        """添加数据主题"""
        try:
            # 检查通用主题唯一性
            if theme_type == "public":
                existing_public = self.get_public_theme()
                if existing_public:
                    logger.error("通用主题已存在，只能创建一个")
                    return None

            theme = self.theme_repo.create(
                theme_name=theme_name,
                theme_description=theme_description,
                theme_type=theme_type,
                department=department
            )

            # 转换为字典格式返回
            theme_dict = {
                "id": theme.id,
                "theme_name": theme.theme_name,
                "theme_description": theme.theme_description or "",
                "theme_type": theme.theme_type,
                "department": theme.department or "",
                "created_at": theme.created_at,
                "updated_at": theme.updated_at
            }

            logger.info(f"添加数据主题成功: {theme_name}")
            return theme_dict

        except Exception as e:
            logger.error(f"添加数据主题失败: {e}")
            return None

    def update_theme(self, theme_id: int, theme_name: str = None, theme_description: str = None,
                     theme_type: str = None, department: str = None) -> bool:
        """更新数据主题"""
        try:
            # 获取当前主题信息
            current_theme = self.get_theme_by_id(theme_id)
            if not current_theme:
                logger.error(f"主题不存在: ID {theme_id}")
                return False

            # 检查通用主题唯一性
            if theme_type == "public" and current_theme.get("theme_type") != "public":
                existing_public = self.get_public_theme()
                if existing_public and existing_public.get("id") != theme_id:
                    logger.error("通用主题已存在，只能创建一个")
                    return False

            # 准备更新数据
            update_data = {}
            if theme_name is not None:
                update_data['theme_name'] = theme_name
            if theme_description is not None:
                update_data['theme_description'] = theme_description
            if theme_type is not None:
                update_data['theme_type'] = theme_type
            if department is not None:
                update_data['department'] = department

            if update_data:
                self.theme_repo.update(theme_id, **update_data)

            logger.info(f"更新数据主题成功: ID {theme_id}")
            return True

        except Exception as e:
            logger.error(f"更新数据主题失败: {e}")
            return False

    def delete_theme(self, theme_id: int) -> bool:
        """删除数据主题"""
        try:
            self.theme_repo.delete(theme_id)
            logger.info(f"删除数据主题成功: ID {theme_id}")
            return True

        except Exception as e:
            logger.error(f"删除数据主题失败: {e}")
            return False

    def get_public_theme(self) -> Optional[Dict[str, Any]]:
        """获取通用主题"""
        try:
            theme = self.theme_repo.get_public_theme()
            if theme:
                return self.get_theme_by_id(theme.id)
            return None
        except Exception as e:
            logger.error(f"获取通用主题失败: {e}")
            return None

    def get_theme_tables(self, theme_id: int) -> List[Dict[str, Any]]:
        """获取主题下的表"""
        try:
            relations = self.relation_repo.get_by_theme_id(theme_id)

            tables = []
            for relation in relations:
                table = self.table_repo.get_by_id(relation.table_id)
                if table:
                    tables.append({
                        "id": table.id,
                        "name": table.name,
                        "comment": table.comment or "",
                        "is_available": int(table.is_available or 0),
                        "created_at": table.created_at,
                        "updated_at": table.updated_at
                    })

            return tables
        except Exception as e:
            logger.error(f"获取主题表失败: {e}")
            return []

    def add_table_to_theme(self, theme_id: int, table_id: int) -> bool:
        """添加表到主题"""
        try:
            # 检查表是否存在
            table = self.table_repo.get_by_id(table_id)
            if not table:
                logger.error(f"表不存在: ID {table_id}")
                return False

            # 检查关联是否已存在
            existing_relation = self.relation_repo.get_relation(theme_id, table_id)
            if existing_relation:
                logger.info(f"表已存在于主题中: 主题{theme_id}, 表{table_id}")
                return True

            self.relation_repo.add_table_to_theme(theme_id, table_id)
            logger.info(f"添加表到主题成功: 主题{theme_id}, 表{table_id}")
            return True

        except Exception as e:
            logger.error(f"添加表到主题失败: {e}")
            return False

    def remove_table_from_theme(self, theme_id: int, table_id: int) -> bool:
        """从主题中移除表"""
        try:
            success = self.relation_repo.remove_table_from_theme(theme_id, table_id)
            if success:
                logger.info(f"从主题中移除表成功: 主题{theme_id}, 表{table_id}")
            return success

        except Exception as e:
            logger.error(f"从主题中移除表失败: {e}")
            return False


# 全局服务实例
_metadata_service: Optional[MetadataService] = None
_glossary_service: Optional[GlossaryService] = None
_relation_field_config_service: Optional[RelationFieldConfigService] = None
_prompt_template_service: Optional[PromptTemplateService] = None
_data_theme_service: Optional[DataThemeService] = None

def get_metadata_service(db: Optional[Session] = None) -> MetadataService:
    """获取元数据服务实例"""
    if db:
        # 如果提供了db，直接返回新实例
        return MetadataService(db)
    global _metadata_service
    if _metadata_service is None:
        from models.db_base import SessionLocal
        _metadata_service = MetadataService(SessionLocal())
    return _metadata_service

def get_glossary_service(db: Optional[Session] = None) -> GlossaryService:
    """获取术语表服务实例"""
    if db:
        # 如果提供了db，直接返回新实例
        return GlossaryService(db)
    global _glossary_service
    if _glossary_service is None:
        from models.db_base import SessionLocal
        _glossary_service = GlossaryService(SessionLocal())
    return _glossary_service

def get_relation_field_config_service(db: Optional[Session] = None) -> RelationFieldConfigService:
    """获取关联字段配置服务实例"""
    if db:
        # 如果提供了db，直接返回新实例
        return RelationFieldConfigService(db)
    global _relation_field_config_service
    if _relation_field_config_service is None:
        from models.db_base import SessionLocal
        _relation_field_config_service = RelationFieldConfigService(SessionLocal())
    return _relation_field_config_service

def get_prompt_template_service(db: Optional[Session] = None) -> PromptTemplateService:
    """获取提示词模板服务实例"""
    if db:
        # 如果提供了db，直接返回新实例
        return PromptTemplateService(db)
    global _prompt_template_service
    if _prompt_template_service is None:
        from models.db_base import SessionLocal
        _prompt_template_service = PromptTemplateService(SessionLocal())
    return _prompt_template_service

def get_data_theme_service(db: Optional[Session] = None) -> DataThemeService:
    """获取数据主题服务实例"""
    if db:
        # 如果提供了db，直接返回新实例
        return DataThemeService(db)
    global _data_theme_service
    if _data_theme_service is None:
        from models.db_base import SessionLocal
        _data_theme_service = DataThemeService(SessionLocal())
    return _data_theme_service