"""
开发环境API路由 - 元数据管理
"""

from typing import List, Optional
from loguru import logger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import get_metadata_service, get_glossary_service


# 创建路由器
router = APIRouter(prefix="/dev", tags=["开发工具"])


# 数据模型
class TableMetadataRequest(BaseModel):
    name: str
    comment: str = ""


class TableMetadataUpdate(BaseModel):
    comment: str = ""


class ColumnMetadataRequest(BaseModel):
    table_name: str
    name: str
    type: str
    comment: str = ""
    is_primary_key: bool = False
    is_nullable: bool = True


class ColumnMetadataUpdate(BaseModel):
    type: Optional[str] = None
    comment: Optional[str] = None
    is_primary_key: Optional[bool] = None
    is_nullable: Optional[bool] = None


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
        success = metadata_service.add_table(request.name, request.comment)
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
        success = metadata_service.update_table(table_name, request.comment)
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
            request.is_primary_key,
            request.is_nullable
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
            request.is_primary_key,
            request.is_nullable
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
                        False,  # 假设非主键
                        column.get('nullable', True)
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