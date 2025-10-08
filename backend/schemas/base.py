"""
基础 Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import TypeVar, Generic, List, Optional, Any
from datetime import datetime


class BaseSchema(BaseModel):
    """基础 Schema 类"""
    
    class Config:
        # 允许从 ORM 对象创建
        from_attributes = True
        # 使用枚举值而不是枚举名称
        use_enum_values = True
        # 允许任意类型
        arbitrary_types_allowed = True
        # JSON 编码器配置
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class BaseResponse(BaseModel):
    """基础响应模型"""
    code: int = Field(default=0, description="响应代码，0表示成功")
    message: str = Field(default="success", description="响应消息")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="响应时间")


T = TypeVar('T')


class DataResponse(BaseResponse, Generic[T]):
    """带数据的响应模型"""
    data: Optional[T] = Field(default=None, description="响应数据")


class PaginatedResponse(BaseResponse, Generic[T]):
    """分页响应模型"""
    data: "PaginatedData[T]" = Field(description="分页数据")


class PaginatedData(BaseModel, Generic[T]):
    """分页数据模型"""
    items: List[T] = Field(description="数据列表")
    total: int = Field(description="总数量")
    page: int = Field(description="当前页码")
    size: int = Field(description="每页大小")
    pages: int = Field(description="总页数")
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, size: int) -> "PaginatedData[T]":
        """创建分页数据"""
        pages = (total + size - 1) // size if size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages
        )


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码，从1开始")
    size: int = Field(default=20, ge=1, le=100, description="每页大小，最大100")
    
    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.size


class SortParams(BaseModel):
    """排序参数"""
    sort_by: Optional[str] = Field(default=None, description="排序字段")
    sort_order: Optional[str] = Field(default="asc", regex="^(asc|desc)$", description="排序方向")


class SearchParams(BaseModel):
    """搜索参数"""
    keyword: Optional[str] = Field(default=None, description="搜索关键词")
    filters: Optional[dict] = Field(default=None, description="过滤条件")


class BaseListParams(PaginationParams, SortParams, SearchParams):
    """基础列表查询参数"""
    pass


class BaseAuditSchema(BaseSchema):
    """基础审计字段 Schema"""
    created_at: Optional[datetime] = Field(description="创建时间")
    updated_at: Optional[datetime] = Field(description="更新时间")
    created_by: Optional[int] = Field(description="创建人ID")
    updated_by: Optional[int] = Field(description="更新人ID")


class BaseCreateSchema(BaseSchema):
    """基础创建 Schema"""
    pass


class BaseUpdateSchema(BaseSchema):
    """基础更新 Schema"""
    pass


class BaseResponseSchema(BaseAuditSchema):
    """基础响应 Schema"""
    id: int = Field(description="主键ID")


# 导出类型
__all__ = [
    "BaseSchema",
    "BaseResponse", 
    "DataResponse",
    "PaginatedResponse",
    "PaginatedData",
    "PaginationParams",
    "SortParams", 
    "SearchParams",
    "BaseListParams",
    "BaseAuditSchema",
    "BaseCreateSchema",
    "BaseUpdateSchema", 
    "BaseResponseSchema",
]