"""
开发环境API路由 - 元数据管理
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from api.endpoint_models import TableMetadataRequest, TableMetadataUpdate, ColumnMetadataRequest, ColumnMetadataUpdate, \
    GlossaryTermRequest, GlossaryTermUpdate, RelationFieldConfigRequest, RelationFieldConfigUpdate, \
    PromptTemplateRequest, PromptTemplateUpdate, DataThemeRequest, DataThemeUpdate, ThemeTableRelationRequest, \
    BatchUpdateRequest, BatchUpdateResult, FineReportRequest, FineReportUpdate
from models.db_base import get_db
from services import get_metadata_service, get_glossary_service, get_relation_field_config_service, \
    get_prompt_template_service, get_data_theme_service
from services.metadata_service.fine_report_service import get_fine_report_service
from utils.config import settings
from utils.logger import logger

# 创建路由器
router = APIRouter(prefix="/metadata")


# 表元数据管理
@router.get("/tables")
async def get_all_table_metadata(
        isAvailable: Optional[str] = None,
        fields: Optional[bool] = True,  # 新增参数，默认返回字段
        table_name: Optional[str] = None,  # 新增参数，支持表名搜索
        db: Session = Depends(get_db)
):
    """获取所有表元数据"""
    try:
        metadata_service = get_metadata_service(db)

        tables = metadata_service.get_tables(
            is_available=isAvailable,
            include_fields=fields,
            table_name_filter=table_name
        )

        return {"success": True, "data": tables}
    except Exception as e:
        logger.error(f"获取表元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_id}")
async def get_table_metadata(table_id: int, db: Session = Depends(get_db)):
    """根据ID获取单个表元数据及其所有字段"""
    try:
        metadata_service = get_metadata_service(db)
        table = metadata_service.get_table_by_id(table_id)

        if not table:
            raise HTTPException(status_code=404, detail=f"表不存在: ID {table_id}")

        return {"success": True, "data": table}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tables")
async def add_table_metadata(request: TableMetadataRequest, db: Session = Depends(get_db)):
    """添加表元数据"""
    try:
        metadata_service = get_metadata_service(db)
        created_table = metadata_service.add_table(request.name, request.comment, request.remark, request.is_available)
        if created_table:
            # 返回创建的表对象
            return {
                "success": True,
                "message": f"表元数据已添加: {request.name}",
                "data": created_table
            }
        else:
            raise HTTPException(status_code=400, detail="添加表元数据失败")
    except Exception as e:
        logger.error(f"添加表元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tables/{table_id}")
async def update_table_metadata(table_id: int, request: TableMetadataUpdate, db: Session = Depends(get_db)):
    """更新表元数据"""
    try:
        metadata_service = get_metadata_service(db)
        success = metadata_service.update_table_by_id(table_id, request.comment, request.remark, request.is_available)
        if success:
            # 重新加载元数据
            return {"success": True, "message": f"表元数据已更新: ID {table_id}"}
        else:
            raise HTTPException(status_code=400, detail="更新表元数据失败")
    except Exception as e:
        logger.error(f"更新表元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tables/{table_id}")
async def delete_table_metadata(table_id: int, db: Session = Depends(get_db)):
    """删除表元数据"""
    try:
        metadata_service = get_metadata_service(db)
        success = metadata_service.delete_table_by_id(table_id)
        if success:
            # 重新加载元数据
            return {"success": True, "message": f"表元数据已删除: ID {table_id}"}
        else:
            raise HTTPException(status_code=400, detail="删除表元数据失败")
    except Exception as e:
        logger.error(f"删除表元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/table/batch")
async def batch_update_metadata(request: BatchUpdateRequest, db: Session = Depends(get_db)):
    """批量更新表和字段元数据"""
    try:
        metadata_service = get_metadata_service(db)
        result = metadata_service.batch_update_table_and_columns(
            table=request.table,
            columns=request.columns
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"批量更新元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 列元数据管理
@router.get("/columns")
async def get_columns_by_table(table_id: int, db: Session = Depends(get_db)):
    """根据表ID获取所有字段"""
    try:
        metadata_service = get_metadata_service(db)
        columns = metadata_service.get_columns_by_table_id(table_id)

        # metadata_service 已返回字典列表，直接返回
        return {"success": True, "data": columns}
    except Exception as e:
        logger.error(f"获取字段列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/columns")
async def add_column_metadata(request: ColumnMetadataRequest, db: Session = Depends(get_db)):
    """添加列元数据"""
    try:
        metadata_service = get_metadata_service(db)
        created_column = metadata_service.add_column_by_id(
            request.table_id,
            request.name,
            request.type,
            request.comment,
            request.remark,
            request.is_available,
            request.business_type,
            request.relation_config_id
        )
        if created_column:
            # 重新加载元数据
            return {
                "success": True,
                "message": f"列元数据已添加: 表ID {request.table_id}.{request.name}",
                "data": created_column
            }
        else:
            raise HTTPException(status_code=400, detail="添加列元数据失败")
    except Exception as e:
        logger.error(f"添加列元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/columns/{column_id}")
async def update_column_metadata(column_id: int, request: ColumnMetadataUpdate, db: Session = Depends(get_db)):
    """更新列元数据"""
    try:
        metadata_service = get_metadata_service(db)
        success = metadata_service.update_column_by_id(
            column_id,
            request.name,
            request.type,
            request.comment,
            request.remark,
            request.is_available,
            request.business_type,
            request.relation_config_id
        )
        if success:
            # 重新加载元数据
            return {"success": True, "message": f"列元数据已更新: ID {column_id}"}
        else:
            raise HTTPException(status_code=400, detail="更新列元数据失败")
    except Exception as e:
        logger.error(f"更新列元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/columns/{column_id}")
async def delete_column_metadata(column_id: int, db: Session = Depends(get_db)):
    """删除列元数据"""
    try:
        metadata_service = get_metadata_service(db)
        success = metadata_service.delete_column_by_id(column_id)
        if success:
            # 重新加载元数据
            return {"success": True, "message": f"列元数据已删除: ID {column_id}"}
        else:
            raise HTTPException(status_code=400, detail="删除列元数据失败")
    except Exception as e:
        logger.error(f"删除列元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 术语表管理
@router.get("/glossary/terms")
async def get_all_terms(db: Session = Depends(get_db)):
    """获取所有术语"""
    try:
        glossary_service = get_glossary_service(db)
        terms = glossary_service.get_terms()
        return {"success": True, "data": terms}
    except Exception as e:
        logger.error(f"获取术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/glossary/terms")
async def add_term(request: GlossaryTermRequest, db: Session = Depends(get_db)):
    """添加术语"""
    try:
        creator: str = "api_user"
        glossary_service = get_glossary_service(db)
        term_id = glossary_service.add_term(
            request.name,
            request.type,
            request.content,
            creator,
            request.is_basic  # 传递 is_basic 参数
        )
        if term_id:
            return {
                "success": True,
                "message": f"术语已添加: {request.name}",
                "data": {"id": term_id}
            }
        else:
            raise HTTPException(status_code=400, detail="添加术语失败")
    except Exception as e:
        logger.error(f"添加术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/glossary/terms/{term_id}")
async def update_term(term_id: int, request: GlossaryTermUpdate, db: Session = Depends(get_db)):
    """更新术语"""
    try:
        glossary_service = get_glossary_service(db)
        success = glossary_service.update_term(
            term_id,
            request.name,
            request.type,
            request.content,
            request.is_basic  # 传递 is_basic 参数
        )
        if success:
            return {"success": True, "message": f"术语已更新: ID {term_id}"}
        else:
            raise HTTPException(status_code=400, detail="更新术语失败")
    except Exception as e:
        logger.error(f"更新术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/glossary/terms/{term_id}")
async def delete_term(term_id: int, db: Session = Depends(get_db)):
    """删除术语"""
    try:
        glossary_service = get_glossary_service(db)
        success = glossary_service.delete_term(term_id)
        if success:
            return {"success": True, "message": f"术语已删除: ID {term_id}"}
        else:
            raise HTTPException(status_code=400, detail="删除术语失败")
    except Exception as e:
        logger.error(f"删除术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/glossary/terms/{term_id}")
async def get_term_by_id(term_id: int, db: Session = Depends(get_db)):
    """根据ID获取术语"""
    try:
        glossary_service = get_glossary_service(db)
        term = glossary_service.get_term_by_id(term_id)
        if term:
            return {"success": True, "data": term}
        else:
            raise HTTPException(status_code=404, detail="术语不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/glossary/terms/type/{term_type}")
async def get_terms_by_type(term_type: str, db: Session = Depends(get_db)):
    """根据类型获取术语"""
    try:
        glossary_service = get_glossary_service(db)
        terms = glossary_service.get_terms_by_type(term_type)
        return {"success": True, "data": terms}
    except Exception as e:
        logger.error(f"获取术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/glossary/search")
async def search_term(query: str, db: Session = Depends(get_db)):
    """搜索术语"""
    try:
        glossary_service = get_glossary_service(db)
        term = glossary_service.find_term(query)
        if term:
            return {"success": True, "data": term}
        else:
            return {"success": False, "message": "未找到匹配的术语"}
    except Exception as e:
        logger.error(f"搜索术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/glossary/terms/basic")
async def get_basic_terms(db: Session = Depends(get_db)):
    """获取所有基础术语"""
    try:
        glossary_service = get_glossary_service(db)
        terms = glossary_service.get_basic_terms()
        return {"success": True, "data": terms}
    except Exception as e:
        logger.error(f"获取基础术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/glossary/terms/non-basic")
async def get_non_basic_terms(db: Session = Depends(get_db)):
    """获取所有非基础术语"""
    try:
        glossary_service = get_glossary_service(db)
        terms = glossary_service.get_non_basic_terms()
        return {"success": True, "data": terms}
    except Exception as e:
        logger.error(f"获取非基础术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 关联字段配置管理
@router.get("/relation-configs/{config_id}")
async def get_relation_config_by_id(config_id: int, db: Session = Depends(get_db)):
    """根据ID获取关联字段配置"""
    try:
        relation_service = get_relation_field_config_service(db)
        config = relation_service.get_relation_config_by_id(config_id)
        if config:
            return {"success": True, "data": config}
        else:
            raise HTTPException(status_code=404, detail="关联字段配置不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取关联字段配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relation-configs")
async def get_all_relation_configs(db: Session = Depends(get_db)):
    """获取所有关联字段配置"""
    try:
        relation_service = get_relation_field_config_service(db)
        configs = relation_service.get_all_relation_configs()
        return {"success": True, "data": configs}
    except Exception as e:
        logger.error(f"获取关联字段配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relation-configs")
async def add_relation_config(request: RelationFieldConfigRequest, db: Session = Depends(get_db)):
    """添加关联字段配置"""
    try:
        relation_service = get_relation_field_config_service(db)
        created_config = relation_service.add_relation_config(
            request.relation_family,
            request.relation_subfamily,
            request.relation_desc
        )
        if created_config:
            return {
                "success": True,
                "message": f"关联字段配置已添加: {request.relation_family}|{request.relation_subfamily}",
                "data": created_config
            }
        else:
            raise HTTPException(status_code=400, detail="添加关联字段配置失败")
    except Exception as e:
        logger.error(f"添加关联字段配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/relation-configs/{config_id}")
async def update_relation_config(config_id: int, request: RelationFieldConfigUpdate, db: Session = Depends(get_db)):
    """更新关联字段配置"""
    try:
        relation_service = get_relation_field_config_service(db)
        success = relation_service.update_relation_config(
            config_id,
            request.relation_family,
            request.relation_subfamily,
            request.relation_desc
        )
        if success:
            return {"success": True, "message": f"关联字段配置已更新: ID {config_id}"}
        else:
            raise HTTPException(status_code=400, detail="更新关联字段配置失败")
    except Exception as e:
        logger.error(f"更新关联字段配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relation-configs/{config_id}")
async def delete_relation_config(config_id: int, db: Session = Depends(get_db)):
    """删除关联字段配置"""
    try:
        relation_service = get_relation_field_config_service(db)
        success = relation_service.delete_relation_config(config_id)
        if success:
            return {"success": True, "message": f"关联字段配置已删除: ID {config_id}"}
        else:
            raise HTTPException(status_code=400, detail="删除关联字段配置失败")
    except Exception as e:
        logger.error(f"删除关联字段配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 提示词模板管理
@router.get("/prompt-templates/{template_id}")
async def get_prompt_template_by_id(template_id: int, db: Session = Depends(get_db)):
    """根据ID获取提示词模板"""
    try:
        template_service = get_prompt_template_service(db)
        template = template_service.get_template_by_id(template_id)
        if template:
            return {"success": True, "data": template}
        else:
            raise HTTPException(status_code=404, detail="提示词模板不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取提示词模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompt-templates")
async def get_all_prompt_templates(db: Session = Depends(get_db)):
    """获取所有提示词模板"""
    try:
        template_service = get_prompt_template_service(db)
        templates = template_service.get_templates()
        return {"success": True, "data": templates}
    except Exception as e:
        logger.error(f"获取提示词模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prompt-templates")
async def add_prompt_template(request: PromptTemplateRequest, db: Session = Depends(get_db)):
    """添加提示词模板"""
    try:
        template_service = get_prompt_template_service(db)
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
async def update_prompt_template(template_id: int, request: PromptTemplateUpdate, db: Session = Depends(get_db)):
    """更新提示词模板"""
    try:
        template_service = get_prompt_template_service(db)
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
async def delete_prompt_template(template_id: int, db: Session = Depends(get_db)):
    """删除提示词模板"""
    try:
        template_service = get_prompt_template_service(db)
        success = template_service.delete_template(template_id)
        if success:
            return {"success": True, "message": f"提示词模板已删除: ID {template_id}"}
        else:
            raise HTTPException(status_code=400, detail="删除提示词模板失败")
    except Exception as e:
        logger.error(f"删除提示词模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 数据主题管理
@router.get("/themes")
async def get_all_themes(theme_type: Optional[str] = None, 
                         db: Session = Depends(get_db)):
    """获取所有数据主题"""
    try:
        # todo 只返回非公共表
        theme_service = get_data_theme_service(db)
        themes = theme_service.get_all_themes()
        return {"success": True, "data": themes}
    except Exception as e:
        logger.error(f"获取数据主题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/themes/{theme_id}")
async def get_theme(theme_id: int, db: Session = Depends(get_db)):
    """获取指定数据主题"""
    try:
        theme_service = get_data_theme_service(db)
        theme = theme_service.get_theme_by_id(theme_id)
        if theme:
            return {"success": True, "data": theme}
        else:
            raise HTTPException(status_code=404, detail="数据主题不存在")
    except Exception as e:
        logger.error(f"获取数据主题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/themes")
async def add_theme(request: DataThemeRequest, db: Session = Depends(get_db)):
    """添加数据主题"""
    try:
        theme_service = get_data_theme_service(db)
        created_theme = theme_service.add_theme(
            request.theme_name,
            request.theme_description,
            request.theme_type,
            request.department
        )
        if created_theme:
            return {
                "success": True,
                "message": f"数据主题已添加: {request.theme_name}",
                "data": created_theme
            }
        else:
            raise HTTPException(status_code=400, detail="添加数据主题失败")
    except Exception as e:
        logger.error(f"添加数据主题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/themes/{theme_id}")
async def update_theme(theme_id: int, request: DataThemeUpdate, db: Session = Depends(get_db)):
    """更新数据主题"""
    try:
        theme_service = get_data_theme_service(db)
        success = theme_service.update_theme(
            theme_id,
            request.theme_name,
            request.theme_description,
            request.theme_type,
            request.department
        )
        if success:
            return {"success": True, "message": f"数据主题已更新: ID {theme_id}"}
        else:
            raise HTTPException(status_code=400, detail="更新数据主题失败")
    except Exception as e:
        logger.error(f"更新数据主题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/themes/{theme_id}")
async def delete_theme(theme_id: int, db: Session = Depends(get_db)):
    """删除数据主题"""
    try:
        theme_service = get_data_theme_service(db)
        success = theme_service.delete_theme(theme_id)
        if success:
            return {"success": True, "message": f"数据主题已删除: ID {theme_id}"}
        else:
            raise HTTPException(status_code=400, detail="删除数据主题失败")
    except Exception as e:
        logger.error(f"删除数据主题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/themes/{theme_id}/tables")
async def get_theme_tables(theme_id: int, db: Session = Depends(get_db)):
    """获取主题下的表"""
    try:
        theme_service = get_data_theme_service(db)
        tables = theme_service.get_theme_tables(theme_id)
        return {"success": True, "data": tables}
    except Exception as e:
        logger.error(f"获取主题表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/themes/{theme_id}/tables")
async def add_table_to_theme(theme_id: int, request: ThemeTableRelationRequest, db: Session = Depends(get_db)):
    """添加表到主题"""
    try:
        theme_service = get_data_theme_service(db)
        success = theme_service.add_table_to_theme(theme_id, request.table_id)
        if success:
            return {"success": True, "message": f"表已添加到主题: 主题{theme_id}, 表{request.table_id}"}
        else:
            raise HTTPException(status_code=400, detail="添加表到主题失败")
    except Exception as e:
        logger.error(f"添加表到主题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/themes/{theme_id}/tables/{table_id}")
async def remove_table_from_theme(theme_id: int, table_id: int, db: Session = Depends(get_db)):
    """从主题中移除表"""
    try:
        theme_service = get_data_theme_service(db)
        success = theme_service.remove_table_from_theme(theme_id, table_id)
        if success:
            return {"success": True, "message": f"表已从主题中移除: 主题{theme_id}, 表{table_id}"}
        else:
            raise HTTPException(status_code=400, detail="从主题中移除表失败")
    except Exception as e:
        logger.error(f"从主题中移除表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# FineReport报表元数据管理
@router.get("/fine-reports/designer-urls")
async def get_designer_urls():
    """获取FineReport设计器地址列表"""
    try:
        designer_urls = settings.fine_report_designer_urls
        return {"success": True, "data": designer_urls}
    except Exception as e:
        logger.error(f"获取FineReport设计器地址列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fine-reports")
async def get_all_fine_reports(
    is_available: Optional[int] = None,
    report_type: Optional[str] = None,
    department_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取所有FineReport报表（支持多条件过滤）"""
    try:
        report_service = get_fine_report_service(db)
        reports = report_service.get_all_reports(
            is_available=is_available,
            report_type=report_type,
            department_id=department_id,
            keyword=keyword
        )
        return {"success": True, "data": reports}
    except Exception as e:
        logger.error(f"获取FineReport报表列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fine-reports/{report_id}")
async def get_fine_report(report_id: int, db: Session = Depends(get_db)):
    """根据ID获取FineReport报表详情"""
    try:
        report_service = get_fine_report_service(db)
        report = report_service.get_report_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"报表不存在: ID {report_id}")
        return {"success": True, "data": report}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取FineReport报表详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fine-reports")
async def create_fine_report(request: FineReportRequest, db: Session = Depends(get_db)):
    """创建FineReport报表"""
    try:
        report_service = get_fine_report_service(db)
        report = report_service.create_report(request.dict())
        if report:
            return {
                "success": True,
                "message": f"FineReport报表已创建: {request.report_name}",
                "data": report
            }
        else:
            raise HTTPException(status_code=400, detail="创建FineReport报表失败，报表名称可能已存在")
    except Exception as e:
        logger.error(f"创建FineReport报表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/fine-reports/{report_id}")
async def update_fine_report(report_id: int, request: FineReportUpdate, db: Session = Depends(get_db)):
    """更新FineReport报表"""
    try:
        report_service = get_fine_report_service(db)
        # 只包含非None的字段
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供更新数据")

        success = report_service.update_report(report_id, update_data)
        if success:
            return {"success": True, "message": f"FineReport报表已更新: ID {report_id}"}
        else:
            raise HTTPException(status_code=400, detail="更新FineReport报表失败，报表不存在或名称已被使用")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新FineReport报表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/fine-reports/{report_id}")
async def delete_fine_report(report_id: int, db: Session = Depends(get_db)):
    """删除FineReport报表"""
    try:
        report_service = get_fine_report_service(db)
        success = report_service.delete_report(report_id)
        if success:
            return {"success": True, "message": f"FineReport报表已删除: ID {report_id}"}
        else:
            raise HTTPException(status_code=404, detail="报表不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除FineReport报表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))