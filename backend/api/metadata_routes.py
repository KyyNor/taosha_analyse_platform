"""
开发环境API路由 - 元数据管理
"""

from typing import List, Optional

from api.endpoint_models import TableMetadataRequest, TableMetadataUpdate, ColumnMetadataRequest, ColumnMetadataUpdate, \
    GlossaryTermRequest, GlossaryTermUpdate, RelationFieldConfigRequest, RelationFieldConfigUpdate, \
    PromptTemplateRequest, PromptTemplateUpdate
from utils.logger import logger, get_logger, LoggerMixin
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import get_metadata_service, get_glossary_service, get_relation_field_config_service, get_prompt_template_service


# 创建路由器
router = APIRouter(prefix="/metadata")


# 表元数据管理
@router.get("/tables")
async def get_all_table_metadata():
    """获取所有表元数据"""
    try:
        metadata_service = get_metadata_service()
        tables = metadata_service.get_tables()
        return {"success": True, "data": tables}
    except Exception as e:
        logger.error(f"获取表元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tables")
async def add_table_metadata(request: TableMetadataRequest):
    """添加表元数据"""
    try:
        metadata_service = get_metadata_service()
        success = metadata_service.add_table(request.name, request.comment, request.is_available)
        if success:
            # 重新加载元数据
            return {"success": True, "message": f"表元数据已添加: {request.name}"}
        else:
            raise HTTPException(status_code=400, detail="添加表元数据失败")
    except Exception as e:
        logger.error(f"添加表元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tables/{table_name}")
async def update_table_metadata(table_name: str, request: TableMetadataUpdate):
    """更新表元数据"""
    try:
        metadata_service = get_metadata_service()
        success = metadata_service.update_table(table_name, request.comment, request.is_available)
        if success:
            # 重新加载元数据
            return {"success": True, "message": f"表元数据已更新: {table_name}"}
        else:
            raise HTTPException(status_code=400, detail="更新表元数据失败")
    except Exception as e:
        logger.error(f"更新表元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tables/{table_name}")
async def delete_table_metadata(table_name: str):
    """删除表元数据"""
    try:
        metadata_service = get_metadata_service()
        success = metadata_service.delete_table(table_name)
        if success:
            # 重新加载元数据
            return {"success": True, "message": f"表元数据已删除: {table_name}"}
        else:
            raise HTTPException(status_code=400, detail="删除表元数据失败")
    except Exception as e:
        logger.error(f"删除表元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 列元数据管理
@router.post("/columns")
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
            return {"success": True, "message": f"列元数据已添加: {request.table_name}.{request.name}"}
        else:
            raise HTTPException(status_code=400, detail="添加列元数据失败")
    except Exception as e:
        logger.error(f"添加列元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/columns/{table_name}/{column_name}")
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
            return {"success": True, "message": f"列元数据已更新: {table_name}.{column_name}"}
        else:
            raise HTTPException(status_code=400, detail="更新列元数据失败")
    except Exception as e:
        logger.error(f"更新列元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/columns/{table_name}/{column_name}")
async def delete_column_metadata(table_name: str, column_name: str):
    """删除列元数据"""
    try:
        metadata_service = get_metadata_service()
        success = metadata_service.delete_column(table_name, column_name)
        if success:
            # 重新加载元数据
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
            request.name,
            request.type,
            request.content,
            request.creator
        )
        if success:
            return {"success": True, "message": f"术语已添加: {request.name}"}
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
            request.name,
            request.type,
            request.content
        )
        if success:
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
            return {"success": True, "message": f"术语已删除: ID {term_id}"}
        else:
            raise HTTPException(status_code=400, detail="删除术语失败")
    except Exception as e:
        logger.error(f"删除术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/glossary/terms/type/{term_type}")
async def get_terms_by_type(term_type: str):
    """根据类型获取术语"""
    try:
        glossary_service = get_glossary_service()
        terms = glossary_service.get_terms_by_type(term_type)
        return {"success": True, "data": terms}
    except Exception as e:
        logger.error(f"获取术语失败: {e}")
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


# 提示词模板管理
@router.get("/prompt-templates")
async def get_all_prompt_templates():
    """获取所有提示词模板"""
    try:
        template_service = get_prompt_template_service()
        templates = template_service.get_templates()
        return {"success": True, "data": templates}
    except Exception as e:
        logger.error(f"获取提示词模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prompt-templates")
async def add_prompt_template(request: PromptTemplateRequest):
    """添加提示词模板"""
    try:
        template_service = get_prompt_template_service()
        success = template_service.add_template(
            request.name,
            request.fields,
            request.template
        )
        if success:
            return {"success": True, "message": f"提示词模板已添加: {request.name}"}
        else:
            raise HTTPException(status_code=400, detail="添加提示词模板失败")
    except Exception as e:
        logger.error(f"添加提示词模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/prompt-templates/{template_id}")
async def update_prompt_template(template_id: int, request: PromptTemplateUpdate):
    """更新提示词模板"""
    try:
        template_service = get_prompt_template_service()
        success = template_service.update_template(
            template_id,
            request.name,
            request.template
        )
        if success:
            return {"success": True, "message": f"提示词模板已更新: ID {template_id}"}
        else:
            raise HTTPException(status_code=400, detail="更新提示词模板失败")
    except Exception as e:
        logger.error(f"更新提示词模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/prompt-templates/{template_id}")
async def delete_prompt_template(template_id: int):
    """删除提示词模板"""
    try:
        template_service = get_prompt_template_service()
        success = template_service.delete_template(template_id)
        if success:
            return {"success": True, "message": f"提示词模板已删除: ID {template_id}"}
        else:
            raise HTTPException(status_code=400, detail="删除提示词模板失败")
    except Exception as e:
        logger.error(f"删除提示词模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))