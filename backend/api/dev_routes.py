"""
开发环境API路由 - 元数据管理
"""

from typing import List, Optional
from loguru import logger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import get_metadata_service, get_glossary_service, get_relation_field_config_service


# 创建路由器
router = APIRouter(prefix="/dev", tags=["开发工具"])


# 数据模型
class TableMetadataRequest(BaseModel):
    name: str
    comment: str = ""
    is_available: int = 0


class TableMetadataUpdate(BaseModel):
    comment: Optional[str] = None
    is_available: Optional[int] = None


class ColumnMetadataRequest(BaseModel):
    table_name: str
    name: str
    type: str
    comment: str = ""
    is_available: int = 0
    business_type: str = ""
    relation_id: str = ""


class ColumnMetadataUpdate(BaseModel):
    type: Optional[str] = None
    comment: Optional[str] = None
    is_available: Optional[int] = None
    business_type: Optional[str] = None
    relation_id: Optional[str] = None


class GlossaryTermRequest(BaseModel):
    term: str
    definition: str = ""
    sql_expression: str = ""
    category: str = ""
    aliases: List[str] = []


class GlossaryTermUpdate(BaseModel):
    term: Optional[str] = None
    definition: Optional[str] = None
    sql_expression: Optional[str] = None
    category: Optional[str] = None


class RelationFieldConfigRequest(BaseModel):
    relation_family: str
    relation_subfamily: str
    relation_desc: str = ""


class RelationFieldConfigUpdate(BaseModel):
    relation_family: Optional[str] = None
    relation_subfamily: Optional[str] = None
    relation_desc: Optional[str] = None


# 表元数据管理
@router.get("/metadata/tables")
async def get_all_table_metadata():
    """获取所有表元数据"""
    try:
        metadata_service = get_metadata_service()
        tables = metadata_service.get_tables()
        return {"success": True, "data": tables}
    except Exception as e:
        logger.error(f"获取表元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metadata/tables")
async def add_table_metadata(request: TableMetadataRequest):
    """添加表元数据"""
    try:
        metadata_service = get_metadata_service()
        success = metadata_service.add_table(request.name, request.comment, request.is_available)
        if success:
            # 重新加载元数据
            metadata_service.reload_if_changed()
            return {"success": True, "message": f"表元数据已添加: {request.name}"}
        else:
            raise HTTPException(status_code=400, detail="添加表元数据失败")
    except Exception as e:
        logger.error(f"添加表元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/metadata/tables/{table_name}")
async def update_table_metadata(table_name: str, request: TableMetadataUpdate):
    """更新表元数据"""
    try:
        metadata_service = get_metadata_service()
        success = metadata_service.update_table(table_name, request.comment, request.is_available)
        if success:
            # 重新加载元数据
            metadata_service.reload_if_changed()
            return {"success": True, "message": f"表元数据已更新: {table_name}"}
        else:
            raise HTTPException(status_code=400, detail="更新表元数据失败")
    except Exception as e:
        logger.error(f"更新表元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/metadata/tables/{table_name}")
async def delete_table_metadata(table_name: str):
    """删除表元数据"""
    try:
        metadata_service = get_metadata_service()
        success = metadata_service.delete_table(table_name)
        if success:
            # 重新加载元数据
            metadata_service.reload_if_changed()
            return {"success": True, "message": f"表元数据已删除: {table_name}"}
        else:
            raise HTTPException(status_code=400, detail="删除表元数据失败")
    except Exception as e:
        logger.error(f"删除表元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 列元数据管理
@router.post("/metadata/columns")
async def add_column_metadata(request: ColumnMetadataRequest):
    """添加列元数据"""
    try:
        metadata_service = get_metadata_service()
        success = metadata_service.add_column(
            request.table_name, 
            request.name, 
            request.type,
            request.comment,
            request.is_available,
            request.business_type,
            request.relation_id
        )
        if success:
            # 重新加载元数据
            metadata_service.reload_if_changed()
            return {"success": True, "message": f"列元数据已添加: {request.table_name}.{request.name}"}
        else:
            raise HTTPException(status_code=400, detail="添加列元数据失败")
    except Exception as e:
        logger.error(f"添加列元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/metadata/columns/{table_name}/{column_name}")
async def update_column_metadata(table_name: str, column_name: str, request: ColumnMetadataUpdate):
    """更新列元数据"""
    try:
        metadata_service = get_metadata_service()
        success = metadata_service.update_column(
            table_name,
            column_name,
            request.type,
            request.comment,
            request.is_available,
            request.business_type,
            request.relation_id
        )
        if success:
            # 重新加载元数据
            metadata_service.reload_if_changed()
            return {"success": True, "message": f"列元数据已更新: {table_name}.{column_name}"}
        else:
            raise HTTPException(status_code=400, detail="更新列元数据失败")
    except Exception as e:
        logger.error(f"更新列元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/metadata/columns/{table_name}/{column_name}")
async def delete_column_metadata(table_name: str, column_name: str):
    """删除列元数据"""
    try:
        metadata_service = get_metadata_service()
        success = metadata_service.delete_column(table_name, column_name)
        if success:
            # 重新加载元数据
            metadata_service.reload_if_changed()
            return {"success": True, "message": f"列元数据已删除: {table_name}.{column_name}"}
        else:
            raise HTTPException(status_code=400, detail="删除列元数据失败")
    except Exception as e:
        logger.error(f"删除列元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 术语表管理
@router.get("/glossary/terms")
async def get_all_terms():
    """获取所有术语"""
    try:
        glossary_service = get_glossary_service()
        terms = glossary_service.get_terms()
        return {"success": True, "data": terms}
    except Exception as e:
        logger.error(f"获取术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/glossary/terms")
async def add_term(request: GlossaryTermRequest):
    """添加术语"""
    try:
        glossary_service = get_glossary_service()
        success = glossary_service.add_term(
            request.term,
            request.definition,
            request.sql_expression,
            request.category,
            request.aliases
        )
        if success:
            # 重新加载术语表
            glossary_service.reload_if_changed()
            return {"success": True, "message": f"术语已添加: {request.term}"}
        else:
            raise HTTPException(status_code=400, detail="添加术语失败")
    except Exception as e:
        logger.error(f"添加术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/glossary/terms/{term_id}")
async def update_term(term_id: int, request: GlossaryTermUpdate):
    """更新术语"""
    try:
        glossary_service = get_glossary_service()
        success = glossary_service.update_term(
            term_id,
            request.term,
            request.definition,
            request.sql_expression,
            request.category
        )
        if success:
            # 重新加载术语表
            glossary_service.reload_if_changed()
            return {"success": True, "message": f"术语已更新: ID {term_id}"}
        else:
            raise HTTPException(status_code=400, detail="更新术语失败")
    except Exception as e:
        logger.error(f"更新术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/glossary/terms/{term_id}")
async def delete_term(term_id: int):
    """删除术语"""
    try:
        glossary_service = get_glossary_service()
        success = glossary_service.delete_term(term_id)
        if success:
            # 重新加载术语表
            glossary_service.reload_if_changed()
            return {"success": True, "message": f"术语已删除: ID {term_id}"}
        else:
            raise HTTPException(status_code=400, detail="删除术语失败")
    except Exception as e:
        logger.error(f"删除术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/glossary/search")
async def search_term(query: str):
    """搜索术语"""
    try:
        glossary_service = get_glossary_service()
        term = glossary_service.find_term(query)
        if term:
            return {"success": True, "data": term}
        else:
            return {"success": False, "message": "未找到匹配的术语"}
    except Exception as e:
        logger.error(f"搜索术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 数据库同步工具
@router.post("/metadata/sync-from-database")
async def sync_metadata_from_database():
    """从实际数据库同步元数据结构"""
    try:
        from services import get_database_service
        
        db_service = get_database_service()
        metadata_service = get_metadata_service()
        
        # 获取数据库中的表
        table_names = db_service.get_tables()
        synced_tables = []
        
        for table_name in table_names:
            # 检查表是否已存在元数据
            existing_table = metadata_service.get_table_info(table_name)
            if not existing_table:
                # 添加表元数据
                metadata_service.add_table(table_name, f"自动从数据库同步的表: {table_name}")
            
            # 获取表结构
            schema = db_service.get_table_schema(table_name)
            columns = schema.get('columns', [])
            
            for column in columns:
                try:
                    metadata_service.add_column(
                        table_name,
                        column['name'],
                        column['type'],
                        f"自动从数据库同步的列: {column['name']}",
                        0,  # 默认可用
                        column['type'],  # 业务类型默认与存储类型相同
                        ""  # 无关联ID
                    )
                except Exception:
                    # 列可能已存在，忽略错误
                    pass
            
            synced_tables.append(table_name)
        
        # 重新加载元数据
        metadata_service.reload_if_changed()
        
        return {
            "success": True, 
            "message": f"已同步 {len(synced_tables)} 张表的元数据",
            "synced_tables": synced_tables
        }
        
    except Exception as e:
        logger.error(f"同步元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 关联字段配置管理
@router.get("/relation-configs")
async def get_all_relation_configs():
    """获取所有关联字段配置"""
    try:
        relation_service = get_relation_field_config_service()
        configs = relation_service.get_all_relation_configs()
        return {"success": True, "data": configs}
    except Exception as e:
        logger.error(f"获取关联字段配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relation-configs")
async def add_relation_config(request: RelationFieldConfigRequest):
    """添加关联字段配置"""
    try:
        relation_service = get_relation_field_config_service()
        success = relation_service.add_relation_config(
            request.relation_family,
            request.relation_subfamily,
            request.relation_desc
        )
        if success:
            relation_id = f"{request.relation_family}|{request.relation_subfamily}"
            return {"success": True, "message": f"关联字段配置已添加: {relation_id}"}
        else:
            raise HTTPException(status_code=400, detail="添加关联字段配置失败")
    except Exception as e:
        logger.error(f"添加关联字段配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/relation-configs/{relation_id}")
async def update_relation_config(relation_id: str, request: RelationFieldConfigUpdate):
    """更新关联字段配置"""
    try:
        relation_service = get_relation_field_config_service()
        success = relation_service.update_relation_config(
            relation_id,
            request.relation_family,
            request.relation_subfamily,
            request.relation_desc
        )
        if success:
            return {"success": True, "message": f"关联字段配置已更新: {relation_id}"}
        else:
            raise HTTPException(status_code=400, detail="更新关联字段配置失败")
    except Exception as e:
        logger.error(f"更新关联字段配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relation-configs/{relation_id}")
async def delete_relation_config(relation_id: str):
    """删除关联字段配置"""
    try:
        relation_service = get_relation_field_config_service()
        success = relation_service.delete_relation_config(relation_id)
        if success:
            return {"success": True, "message": f"关联字段配置已删除: {relation_id}"}
        else:
            raise HTTPException(status_code=400, detail="删除关联字段配置失败")
    except Exception as e:
        logger.error(f"删除关联字段配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relation-configs/ids")
async def get_relation_ids():
    """获取所有关联ID列表"""
    try:
        relation_service = get_relation_field_config_service()
        relation_ids = relation_service.get_relation_ids()
        return {"success": True, "data": relation_ids}
    except Exception as e:
        logger.error(f"获取关联ID列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))