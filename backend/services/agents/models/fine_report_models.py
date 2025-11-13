"""
FineReport工具Pydantic模型定义
用于参数验证和类型安全
"""

from typing import Dict, Literal, Union
from pydantic import BaseModel, Field


class ConditionalLocator(BaseModel):
    """
    条件查找定位器模型
    用于在Excel中根据条件查找数据
    """
    find_column: str = Field(
        ...,
        description="查找列的Excel列名（如A、B、AA等）",
        pattern=r'^[A-Z]+$'
    )
    find_value: str = Field(
        ...,
        description="查找值。如果是static类型则为实际值，如果是dynamic类型则为控件名称"
    )
    find_value_type: Literal["static", "dynamic"] = Field(
        default="static",
        description="查找值类型：static为静态值，dynamic为控件引用"
    )
    return_column: str = Field(
        ...,
        description="返回列的Excel列名（如A、B、AA等）",
        pattern=r'^[A-Z]+$'
    )

    class Config:
        """Pydantic配置"""
        extra = "forbid"  # 禁止额外字段
        use_enum_values = True


class ExcelLocatorDict(BaseModel):
    """
    Excel数据定位器字典
    支持多个数据字段的定位配置
    """
    __root__: Dict[str, ConditionalLocator]

    def get_dict(self) -> Dict[str, ConditionalLocator]:
        """获取字典格式数据"""
        return self.__root__

    class Config:
        """Pydantic配置"""
        extra = "forbid"
        use_enum_values = True


class ControlOperation(BaseModel):
    """
    控件操作模型
    定义对FineReport控件的操作
    """
    type: str = Field(
        default="text",
        description="控件类型，通常为text"
    )
    name: str = Field(
        ...,
        description="控件名称"
    )
    value: Union[str, list] = Field(
        ...,
        description="控件值，可以是单个值或值的数组"
    )

    class Config:
        """Pydantic配置"""
        extra = "forbid"
        use_enum_values = True


class FilterReportRequest(BaseModel):
    """
    批量过滤报表并获取数据的请求模型
    """
    report_url: str = Field(
        ...,
        description="FineReport报表的完整URL"
    )
    control_operations: list = Field(
        ...,
        description="控件操作列表"
    )
    return_locators: Union[ExcelLocatorDict, Dict] = Field(
        default=None,
        description="返回数据定位器字典"
    )

    class Config:
        """Pydantic配置"""
        extra = "forbid"
        use_enum_values = True


# Excel列名验证函数
def validate_excel_column(column: str) -> bool:
    """
    验证Excel列名格式是否正确

    Args:
        column: Excel列名（如A、B、AA等）

    Returns:
        bool: 是否为有效的Excel列名
    """
    if not column or not column.isalpha() or not column.isupper():
        return False
    return True