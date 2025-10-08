"""
简化的元数据管理 API 路由
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, List

from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


# 模拟数据
MOCK_THEMES = [
    {
        "id": 1,
        "theme_name": "销售数据",
        "theme_description": "销售相关的数据主题",
        "is_public": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    },
    {
        "id": 2,
        "theme_name": "用户数据", 
        "theme_description": "用户相关的数据主题",
        "is_public": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
]

MOCK_TABLES = [
    {
        "id": 1,
        "theme_id": 1,
        "table_name_en": "sales_orders",
        "table_name_cn": "销售订单表",
        "table_description": "存储销售订单信息",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    },
    {
        "id": 2,
        "theme_id": 2,
        "table_name_en": "users",
        "table_name_cn": "用户表",
        "table_description": "存储用户基本信息",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    },
    {
        "id": 3,
        "theme_id": 1,
        "table_name_en": "products", 
        "table_name_cn": "产品表",
        "table_description": "存储产品基本信息",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
]

MOCK_FIELDS = [
    {
        "id": 1,
        "table_id": 1,
        "field_name": "order_id",
        "field_alias": "订单ID",
        "field_description": "唯一标识订单的ID",
        "data_type": "int",
        "is_primary_key": True,
        "is_nullable": False,
        "default_value": None,
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    },
    {
        "id": 2,
        "table_id": 1,
        "field_name": "customer_name",
        "field_alias": "客户姓名",
        "field_description": "购买客户的姓名",
        "data_type": "varchar",
        "is_primary_key": False,
        "is_nullable": False,
        "default_value": None,
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
]

MOCK_GLOSSARY = [
    {
        "id": 1,
        "term_name": "客户",
        "term_description": "购买我们产品或服务的个人或组织",
        "category": "业务术语",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    },
    {
        "id": 2,
        "term_name": "订单",
        "term_description": "客户购买商品或服务的记录",
        "category": "业务术语",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
]


def create_paginated_response(items: List[Dict], page: int, size: int):
    """创建分页响应"""
    total = len(items)
    start = (page - 1) * size
    end = start + size
    page_items = items[start:end]
    
    return {
        "items": page_items,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if size > 0 else 0
    }


# ========== 数据主题管理 ==========
@router.get("/themes")
async def list_themes(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    keyword: str = Query(None, description="搜索关键词"),
    is_active: bool = Query(None, description="是否启用")
):
    """获取数据主题列表"""
    try:
        filtered_themes = MOCK_THEMES
        
        # 关键词过滤
        if keyword:
            filtered_themes = [
                theme for theme in filtered_themes
                if keyword.lower() in theme['theme_name'].lower() or 
                   keyword.lower() in (theme.get('theme_description', '') or '').lower()
            ]
        
        # 状态过滤
        if is_active is not None:
            filtered_themes = [
                theme for theme in filtered_themes
                if theme['is_active'] == is_active
            ]
        
        result = create_paginated_response(filtered_themes, page, size)
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"获取数据主题列表失败: {e}")
        return {
            "code": 500,
            "message": "获取失败",
            "data": None
        }


@router.get("/themes/{theme_id}")
async def get_theme(theme_id: int):
    """获取数据主题详情"""
    try:
        theme = next((t for t in MOCK_THEMES if t['id'] == theme_id), None)
        
        if not theme:
            return {
                "code": 404,
                "message": "数据主题不存在",
                "data": None
            }
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": theme
        }
        
    except Exception as e:
        logger.error(f"获取数据主题详情失败: {e}")
        return {
            "code": 500,
            "message": "获取失败",
            "data": None
        }


# ========== 表元数据管理 ==========
@router.get("/tables")
async def list_tables(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    theme_id: int = Query(None, description="主题ID"),
    keyword: str = Query(None, description="搜索关键词"),
    is_active: bool = Query(None, description="是否启用")
):
    """获取表元数据列表"""
    try:
        filtered_tables = MOCK_TABLES
        
        # 主题过滤
        if theme_id:
            filtered_tables = [
                table for table in filtered_tables
                if table['theme_id'] == theme_id
            ]
        
        # 关键词过滤
        if keyword:
            filtered_tables = [
                table for table in filtered_tables
                if keyword.lower() in table['table_name_en'].lower() or 
                   keyword.lower() in table['table_name_cn'].lower()
            ]
        
        # 状态过滤
        if is_active is not None:
            filtered_tables = [
                table for table in filtered_tables
                if table['is_active'] == is_active
            ]
        
        result = create_paginated_response(filtered_tables, page, size)
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"获取表元数据列表失败: {e}")
        return {
            "code": 500,
            "message": "获取失败",
            "data": None
        }


@router.get("/tables/{table_id}")
async def get_table(table_id: int):
    """获取表元数据详情"""
    try:
        table = next((t for t in MOCK_TABLES if t['id'] == table_id), None)
        
        if not table:
            return {
                "code": 404,
                "message": "表不存在",
                "data": None
            }
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": table
        }
        
    except Exception as e:
        logger.error(f"获取表元数据详情失败: {e}")
        return {
            "code": 500,
            "message": "获取失败",
            "data": None
        }


# ========== 字段元数据管理 ==========
@router.get("/fields")
async def list_fields(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    table_id: int = Query(None, description="表ID"),
    keyword: str = Query(None, description="搜索关键词"),
    is_active: bool = Query(None, description="是否启用")
):
    """获取字段元数据列表"""
    try:
        filtered_fields = MOCK_FIELDS
        
        # 表过滤
        if table_id:
            filtered_fields = [
                field for field in filtered_fields
                if field['table_id'] == table_id
            ]
        
        # 关键词过滤
        if keyword:
            filtered_fields = [
                field for field in filtered_fields
                if keyword.lower() in field['field_name'].lower() or 
                   keyword.lower() in field['field_alias'].lower()
            ]
        
        # 状态过滤
        if is_active is not None:
            filtered_fields = [
                field for field in filtered_fields
                if field['is_active'] == is_active
            ]
        
        result = create_paginated_response(filtered_fields, page, size)
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"获取字段元数据列表失败: {e}")
        return {
            "code": 500,
            "message": "获取失败",
            "data": None
        }


@router.get("/fields/{field_id}")
async def get_field(field_id: int):
    """获取字段元数据详情"""
    try:
        field = next((f for f in MOCK_FIELDS if f['id'] == field_id), None)
        
        if not field:
            return {
                "code": 404,
                "message": "字段不存在",
                "data": None
            }
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": field
        }
        
    except Exception as e:
        logger.error(f"获取字段元数据详情失败: {e}")
        return {
            "code": 500,
            "message": "获取失败",
            "data": None
        }


# ========== 术语管理 ==========
@router.get("/glossary")
async def list_glossary(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    keyword: str = Query(None, description="搜索关键词"),
    category: str = Query(None, description="术语分类"),
    is_active: bool = Query(None, description="是否启用")
):
    """获取术语列表"""
    try:
        filtered_glossary = MOCK_GLOSSARY
        
        # 分类过滤
        if category:
            filtered_glossary = [
                term for term in filtered_glossary
                if term.get('category') == category
            ]
        
        # 关键词过滤
        if keyword:
            filtered_glossary = [
                term for term in filtered_glossary
                if keyword.lower() in term['term_name'].lower() or 
                   keyword.lower() in term['term_description'].lower()
            ]
        
        # 状态过滤
        if is_active is not None:
            filtered_glossary = [
                term for term in filtered_glossary
                if term['is_active'] == is_active
            ]
        
        result = create_paginated_response(filtered_glossary, page, size)
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"获取术语列表失败: {e}")
        return {
            "code": 500,
            "message": "获取失败",
            "data": None
        }


@router.get("/glossary/{glossary_id}")
async def get_glossary_term(glossary_id: int):
    """获取术语详情"""
    try:
        term = next((g for g in MOCK_GLOSSARY if g['id'] == glossary_id), None)
        
        if not term:
            return {
                "code": 404,
                "message": "术语不存在",
                "data": None
            }
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": term
        }
        
    except Exception as e:
        logger.error(f"获取术语详情失败: {e}")
        return {
            "code": 500,
            "message": "获取失败",
            "data": None
        }


# ========== 元数据统计 ==========
@router.get("/stats")
async def get_metadata_stats():
    """获取元数据统计"""
    try:
        stats = {
            "theme_count": len(MOCK_THEMES),
            "table_count": len(MOCK_TABLES),
            "field_count": len(MOCK_FIELDS),
            "glossary_count": len(MOCK_GLOSSARY)
        }
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"获取元数据统计失败: {e}")
        return {
            "code": 500,
            "message": "获取失败",
            "data": None
        }


# ========== 元数据搜索 ==========
@router.get("/search")
async def search_metadata(keyword: str = Query(..., description="搜索关键词")):
    """搜索元数据"""
    try:
        if not keyword:
            return {
                "code": 400,
                "message": "请提供搜索关键词",
                "data": None
            }
        
        keyword_lower = keyword.lower()
        
        # 搜索主题
        matching_themes = [
            theme for theme in MOCK_THEMES
            if keyword_lower in theme['theme_name'].lower() or 
               keyword_lower in (theme.get('theme_description', '') or '').lower()
        ]
        
        # 搜索表
        matching_tables = [
            table for table in MOCK_TABLES
            if keyword_lower in table['table_name_en'].lower() or 
               keyword_lower in table['table_name_cn'].lower()
        ]
        
        # 搜索字段
        matching_fields = [
            field for field in MOCK_FIELDS
            if keyword_lower in field['field_name'].lower() or 
               keyword_lower in field['field_alias'].lower()
        ]
        
        # 搜索术语
        matching_glossary = [
            term for term in MOCK_GLOSSARY
            if keyword_lower in term['term_name'].lower() or 
               keyword_lower in term['term_description'].lower()
        ]
        
        result = {
            "themes": matching_themes,
            "tables": matching_tables,
            "fields": matching_fields,
            "glossary": matching_glossary
        }
        
        return {
            "code": 0,
            "message": "搜索成功",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"搜索元数据失败: {e}")
        return {
            "code": 500,
            "message": "搜索失败",
            "data": None
        }