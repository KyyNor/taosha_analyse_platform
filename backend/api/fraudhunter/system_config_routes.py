"""
系统配置API路由

提供系统热配置的CRUD和Excel解析功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional

from models.db_base import get_db
from schemas.fraudhunter.system_config import (
    SystemConfigCreate,
    SystemConfigUpdate,
    SystemConfigResponse,
    SystemConfigListResponse,
    ExcelParseResponse,
)
from services.fraudhunter.system_config_service import SystemConfigManager
from utils.logger import logger


router = APIRouter(prefix="/system-config", tags=["系统配置"])


@router.get(
    "",
    response_model=SystemConfigListResponse,
    summary="获取系统配置列表"
)
async def list_system_configs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词（配置键或描述）"),
    category: Optional[str] = Query(None, description="分类筛选: sql_variable/system_param"),
    db: Session = Depends(get_db)
):
    """
    获取系统配置列表，支持分页和搜索

    查询参数:
    - page: 页码（默认1）
    - page_size: 每页数量（默认20）
    - search: 搜索关键词，匹配配置键或描述
    - category: 分类筛选，可选 sql_variable 或 system_param

    返回:
    - items: 配置列表
    - total: 总数
    - page: 当前页码
    - page_size: 每页数量
    """
    try:
        # 验证分类参数
        if category and category not in ['sql_variable', 'system_param']:
            raise HTTPException(
                status_code=400,
                detail=f"无效的分类: {category}，支持的分类: sql_variable, system_param"
            )

        manager = SystemConfigManager(db)
        items, total = manager.list_configs(
            page=page,
            page_size=page_size,
            search=search,
            category=category
        )

        # 转换 sql_in_convert 为布尔值
        result_items = []
        for item in items:
            item_dict = {
                'id': item.id,
                'config_category': item.config_category,
                'config_key': item.config_key,
                'config_desc': item.config_desc,
                'config_type': item.config_type,
                'config_value': item.config_value,
                'sql_in_convert': bool(item.sql_in_convert),
                'sort_order': item.sort_order,
                'created_at': item.created_at,
                'updated_at': item.updated_at
            }
            result_items.append(item_dict)

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': result_items
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取系统配置列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{config_id}",
    response_model=SystemConfigResponse,
    summary="获取系统配置详情"
)
async def get_system_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定ID的系统配置详情

    参数:
    - config_id: 配置ID
    """
    try:
        manager = SystemConfigManager(db)
        config = manager.get_config(config_id)

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"配置不存在: {config_id}"
            )

        return {
            'id': config.id,
            'config_category': config.config_category,
            'config_key': config.config_key,
            'config_desc': config.config_desc,
            'config_type': config.config_type,
            'config_value': config.config_value,
            'sql_in_convert': bool(config.sql_in_convert),
            'sort_order': config.sort_order,
            'created_at': config.created_at,
            'updated_at': config.updated_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取系统配置详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "",
    response_model=SystemConfigResponse,
    summary="创建系统配置"
)
async def create_system_config(
    data: SystemConfigCreate,
    db: Session = Depends(get_db)
):
    """
    创建新的系统配置

    请求体:
    - config_category: 配置分类（sql_variable/system_param）
    - config_key: 配置键（唯一）
    - config_desc: 配置描述
    - config_type: 值类型（string/list/json_list）
    - config_value: 配置值，格式为 {"value": ...}
    - sql_in_convert: 列表是否转换为SQL IN格式（仅对list类型有效）
    - sort_order: 排序顺序
    """
    try:
        manager = SystemConfigManager(db)
        config = manager.create_config(data)

        return {
            'id': config.id,
            'config_category': config.config_category,
            'config_key': config.config_key,
            'config_desc': config.config_desc,
            'config_type': config.config_type,
            'config_value': config.config_value,
            'sql_in_convert': bool(config.sql_in_convert),
            'sort_order': config.sort_order,
            'created_at': config.created_at,
            'updated_at': config.updated_at
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建系统配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{config_id}",
    response_model=SystemConfigResponse,
    summary="更新系统配置"
)
async def update_system_config(
    config_id: int,
    data: SystemConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    更新指定ID的系统配置

    参数:
    - config_id: 配置ID

    请求体:
    - 同创建接口
    """
    try:
        manager = SystemConfigManager(db)
        config = manager.update_config(config_id, data)

        return {
            'id': config.id,
            'config_category': config.config_category,
            'config_key': config.config_key,
            'config_desc': config.config_desc,
            'config_type': config.config_type,
            'config_value': config.config_value,
            'sql_in_convert': bool(config.sql_in_convert),
            'sort_order': config.sort_order,
            'created_at': config.created_at,
            'updated_at': config.updated_at
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新系统配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/parse-excel",
    response_model=ExcelParseResponse,
    summary="解析Excel文件"
)
async def parse_excel(
    file: UploadFile = File(..., description="Excel文件"),
    db: Session = Depends(get_db)
):
    """
    解析Excel文件，返回预览数据

    用于前端导入配置值时的预览功能。

    请求:
    - file: Excel文件（.xlsx/.xls）

    返回:
    - columns: 列名列表
    - data: 数据行列表
    - row_count: 数据行数
    """
    try:
        # 验证文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="未提供文件名")

        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="仅支持Excel文件格式（.xlsx/.xls）"
            )

        # 读取文件内容
        content = await file.read()

        # 解析Excel
        manager = SystemConfigManager(db)
        result = manager.parse_excel(content)

        logger.info(f"解析Excel成功: {file.filename}, {result['row_count']} 行")

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解析Excel失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
