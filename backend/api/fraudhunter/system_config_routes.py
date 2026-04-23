"""
系统配置API路由

提供系统热配置的CRUD和Excel解析功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import io
from urllib.parse import quote
from datetime import datetime

from models.db_base import get_db
from schemas.fraudhunter.system_config import (
    SystemConfigCreate,
    SystemConfigUpdate,
    SystemConfigResponse,
    SystemConfigListResponse,
    ExcelParseResponse,
)
from services.fraudhunter.system_config_service import SystemConfigManager
from services.fraudhunter.province_card_bin_service import ProvinceCardBinExistsError, ProvinceCardBinService
from api.endpoint_models import ProvinceCardBinRequest
from utils.logger import logger


router = APIRouter(prefix="/system-config", tags=["系统配置"])


# ==============================================================================
# 省市卡BIN维表管理（放在最前，避免被 /{config_id} 通配路由兜住）
# ==============================================================================

def _get_cardbin_svc(db: Session) -> ProvinceCardBinService:
    return ProvinceCardBinService(db)


@router.get("/province-card-bins")
async def list_province_card_bins(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """分页查询省市卡BIN（支持模糊搜索）"""
    try:
        svc = _get_cardbin_svc(db)
        result = svc.list_paginated(page=page, page_size=page_size, search=search)
        return result
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/province-card-bins/{card_bin}")
async def get_province_card_bin(card_bin: str, db: Session = Depends(get_db)):
    """根据 card_bin 精确查询一条"""
    try:
        svc = _get_cardbin_svc(db)
        row = svc.get_by_card_bin(card_bin)
        if not row:
            raise HTTPException(status_code=404, detail=f"未找到 card_bin: {card_bin}")
        return row
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询省市卡BIN失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/province-card-bins", status_code=201)
async def create_province_card_bin(req: ProvinceCardBinRequest, db: Session = Depends(get_db)):
    """新增一条卡BIN记录，同时同步至 PostgreSQL"""
    if not req.card_bin:
        raise HTTPException(status_code=400, detail="card_bin 不能为空")
    try:
        svc = _get_cardbin_svc(db)
        return svc.create(
            card_bin=req.card_bin,
            bank_name=req.bank_name or "",
            province=req.province or "",
            city=req.city or "",
        )
    except ProvinceCardBinExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"新增省市卡BIN失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/province-card-bins/{card_bin}")
async def update_province_card_bin(card_bin: str, req: ProvinceCardBinRequest, db: Session = Depends(get_db)):
    """更新卡BIN记录，同时同步至 PostgreSQL"""
    try:
        svc = _get_cardbin_svc(db)
        new_card_bin = req.card_bin if req.card_bin is not None else card_bin
        updated = svc.update(
            old_card_bin=card_bin,
            card_bin=new_card_bin,
            bank_name=req.bank_name or "",
            province=req.province or "",
            city=req.city or "",
        )
        if updated:
            updated_row = svc.get_by_card_bin(new_card_bin)
            return updated_row
        raise HTTPException(status_code=404, detail=f"未找到 card_bin: {card_bin}")
    except ProvinceCardBinExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新省市卡BIN失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/province-card-bins/{card_bin}", status_code=200)
async def delete_province_card_bin(card_bin: str, db: Session = Depends(get_db)):
    """删除卡BIN记录，连带删除 PG 中的同一笔"""
    try:
        svc = _get_cardbin_svc(db)
        ok = svc.delete(card_bin)
        if ok:
            return {"success": True, "message": f"已删除: {card_bin}"}
        raise HTTPException(status_code=404, detail=f"未找到 card_bin: {card_bin}")
    except Exception as e:
        logger.error(f"删除省市卡BIN失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get(
    "/{config_id}/export-json-list",
    summary="导出配置(JSON列表)为Excel"
)
async def export_json_list_as_excel(
    config_id: int,
    db: Session = Depends(get_db)
):
    """导出 json_list 类型配置的值为 Excel，直接输出 json_list.value。"""
    try:
        manager = SystemConfigManager(db)
        file_content = manager.export_json_list_as_excel(config_id)

        cfg = manager.get_config(config_id)
        config_key = cfg.config_key if cfg else str(config_id)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{config_key}_{ts}.xlsx"
        encoded = quote(filename)

        logger.info(f"导出配置JSON列表: config_id={config_id}, size={len(file_content)} bytes")

        return StreamingResponse(
            io.BytesIO(file_content),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}; filename*=UTF-8''{encoded}"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出配置JSON列表失败: {e}", exc_info=True)
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


