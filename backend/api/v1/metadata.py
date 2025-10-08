"""
元数据管理 API 路由
"""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from utils.database import get_db
from utils.exceptions import ValidationException
from schemas.base import DataResponse, PaginatedResponse
from schemas.metadata_schemas import (
    DataThemeCreate, DataThemeUpdate, DataThemeResponse, DataThemeListParams,
    TableCreate, TableUpdate, TableResponse, TableListParams,
    FieldCreate, FieldUpdate, FieldResponse, FieldListParams,
    GlossaryCreate, GlossaryUpdate, GlossaryResponse, GlossaryListParams,
    RelationCreate, RelationUpdate, RelationResponse
)
from services.metadata_service import get_metadata_service

router = APIRouter()


# ========== 数据主题管理 ==========
@router.post("/themes", response_model=DataResponse[DataThemeResponse], summary="创建数据主题")
async def create_theme(
    theme_data: DataThemeCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = 1  # TODO: 从认证中间件获取
):
    """创建数据主题"""
    service = get_metadata_service(db)
    theme = await service.create_theme(theme_data, current_user_id)
    return DataResponse(data=theme)


@router.get("/themes/{theme_id}", response_model=DataResponse[DataThemeResponse], summary="获取数据主题详情")
async def get_theme(
    theme_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取数据主题详情"""
    service = get_metadata_service(db)
    theme = await service.get_theme(theme_id)
    return DataResponse(data=theme)


@router.put("/themes/{theme_id}", response_model=DataResponse[DataThemeResponse], summary="更新数据主题")
async def update_theme(
    theme_id: int,
    theme_data: DataThemeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = 1  # TODO: 从认证中间件获取
):
    """更新数据主题"""
    service = get_metadata_service(db)
    theme = await service.update_theme(theme_id, theme_data, current_user_id)
    return DataResponse(data=theme)


@router.delete("/themes/{theme_id}", response_model=DataResponse[bool], summary="删除数据主题")
async def delete_theme(
    theme_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = 1  # TODO: 从认证中间件获取
):
    """删除数据主题"""
    service = get_metadata_service(db)
    result = await service.delete_theme(theme_id, current_user_id)
    return DataResponse(data=result)


@router.get("/themes", response_model=PaginatedResponse[DataThemeResponse], summary="获取数据主题列表")
async def list_themes(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    keyword: str = Query(None, description="搜索关键词"),
    is_public: bool = Query(None, description="是否公共主题"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    db: AsyncSession = Depends(get_db)
):
    """获取数据主题列表"""
    params = {
        'page': page,
        'size': size,
        'keyword': keyword,
        'is_public': is_public,
        'sort_by': sort_by,
        'sort_order': sort_order
    }
    
    service = get_metadata_service(db)
    result = await service.list_themes(params)
    return PaginatedResponse(data=result)


# ========== 表元数据管理 ==========
@router.post("/tables", response_model=DataResponse[TableResponse], summary="创建表元数据")
async def create_table(
    table_data: TableCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = 1  # TODO: 从认证中间件获取
):
    """创建表元数据"""
    service = get_metadata_service(db)
    table = await service.create_table(table_data, current_user_id)
    return DataResponse(data=table)


@router.get("/tables/{table_id}", response_model=DataResponse[TableResponse], summary="获取表元数据详情")
async def get_table(
    table_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取表元数据详情"""
    service = get_metadata_service(db)
    table = await service.get_table(table_id)
    return DataResponse(data=table)


@router.put("/tables/{table_id}", response_model=DataResponse[TableResponse], summary="更新表元数据")
async def update_table(
    table_id: int,
    table_data: TableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = 1  # TODO: 从认证中间件获取
):
    """更新表元数据"""
    service = get_metadata_service(db)
    table = await service.update_table(table_id, table_data, current_user_id)
    return DataResponse(data=table)


@router.get("/tables", response_model=PaginatedResponse[TableResponse], summary="获取表元数据列表")
async def list_tables(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    keyword: str = Query(None, description="搜索关键词"),
    data_source: str = Query(None, description="数据源"),
    theme_id: int = Query(None, description="主题ID"),
    is_active: bool = Query(None, description="是否启用"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    db: AsyncSession = Depends(get_db)
):
    """获取表元数据列表"""
    params = {
        'page': page,
        'size': size,
        'keyword': keyword,
        'data_source': data_source,
        'theme_id': theme_id,
        'is_active': is_active,
        'sort_by': sort_by,
        'sort_order': sort_order
    }
    
    # TODO: 实现 list_tables 方法
    # service = get_metadata_service(db)
    # result = await service.list_tables(params)
    # return PaginatedResponse(data=result)
    
    # 临时返回空结果
    from schemas.base import PaginatedData
    empty_result = PaginatedData.create([], 0, page, size)
    return PaginatedResponse(data=empty_result)


# ========== 字段元数据管理 ==========
@router.post("/fields", response_model=DataResponse[FieldResponse], summary="创建字段元数据")
async def create_field(
    field_data: FieldCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = 1  # TODO: 从认证中间件获取
):
    """创建字段元数据"""
    service = get_metadata_service(db)
    field = await service.create_field(field_data, current_user_id)
    return DataResponse(data=field)


@router.get("/fields/{field_id}", response_model=DataResponse[FieldResponse], summary="获取字段元数据详情")
async def get_field(
    field_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取字段元数据详情"""
    # TODO: 实现 get_field 方法
    from utils.exceptions import ResourceNotFoundException
    raise ResourceNotFoundException("字段详情接口待实现")


@router.get("/fields", response_model=PaginatedResponse[FieldResponse], summary="获取字段元数据列表")
async def list_fields(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    table_id: int = Query(None, description="表ID"),
    keyword: str = Query(None, description="搜索关键词"),
    field_type: str = Query(None, description="字段类型"),
    is_active: bool = Query(None, description="是否启用"),
    db: AsyncSession = Depends(get_db)
):
    """获取字段元数据列表"""
    # TODO: 实现 list_fields 方法
    from schemas.base import PaginatedData
    empty_result = PaginatedData.create([], 0, page, size)
    return PaginatedResponse(data=empty_result)


# ========== 术语管理 ==========
@router.post("/glossary", response_model=DataResponse[GlossaryResponse], summary="创建术语")
async def create_glossary(
    glossary_data: GlossaryCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = 1  # TODO: 从认证中间件获取
):
    """创建术语"""
    service = get_metadata_service(db)
    glossary = await service.create_glossary(glossary_data, current_user_id)
    return DataResponse(data=glossary)


@router.get("/glossary/{glossary_id}", response_model=DataResponse[GlossaryResponse], summary="获取术语详情")
async def get_glossary(
    glossary_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取术语详情"""
    # TODO: 实现 get_glossary 方法
    from utils.exceptions import ResourceNotFoundException
    raise ResourceNotFoundException("术语详情接口待实现")


@router.get("/glossary", response_model=PaginatedResponse[GlossaryResponse], summary="获取术语列表")
async def list_glossary(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    keyword: str = Query(None, description="搜索关键词"),
    term_type: str = Query(None, description="术语类型"),
    category: str = Query(None, description="术语分类"),
    db: AsyncSession = Depends(get_db)
):
    """获取术语列表"""
    # TODO: 实现 list_glossary 方法
    from schemas.base import PaginatedData
    empty_result = PaginatedData.create([], 0, page, size)
    return PaginatedResponse(data=empty_result)


# ========== 数据同步和导入 ==========
@router.post("/sync/tables", response_model=DataResponse[dict], summary="同步表结构")
async def sync_tables(
    data_source: str = Query(..., description="数据源名称"),
    schema_name: str = Query(None, description="模式名称"),
    db: AsyncSession = Depends(get_db),
    current_user_id: int = 1  # TODO: 从认证中间件获取
):
    """从数据源同步表结构"""
    # TODO: 实现表结构同步功能
    return DataResponse(data={"message": "表结构同步功能待实现", "data_source": data_source})


@router.post("/import/metadata", response_model=DataResponse[dict], summary="导入元数据")
async def import_metadata(
    # file: UploadFile = File(..., description="元数据文件"),
    db: AsyncSession = Depends(get_db),
    current_user_id: int = 1  # TODO: 从认证中间件获取
):
    """从文件导入元数据"""
    # TODO: 实现元数据导入功能
    return DataResponse(data={"message": "元数据导入功能待实现"})


@router.get("/export/metadata", summary="导出元数据")
async def export_metadata(
    format: str = Query("json", regex="^(json|excel|csv)$", description="导出格式"),
    theme_ids: str = Query(None, description="主题ID列表，逗号分隔"),
    db: AsyncSession = Depends(get_db)
):
    """导出元数据"""
    # TODO: 实现元数据导出功能
    return {"message": "元数据导出功能待实现", "format": format}