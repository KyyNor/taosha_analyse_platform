"""
自定义异常类模块
"""
from typing import Optional, Any
from datetime import datetime
from fastapi import HTTPException


class TaoshaException(Exception):
    """淘沙平台基础异常类"""
    
    def __init__(
        self,
        message: str,
        error_code: int = 500000,
        status_code: int = 500,
        details: Optional[Any] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details
        self.timestamp = datetime.now()
        super().__init__(self.message)


class ValidationException(TaoshaException):
    """参数验证异常"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code=400001,
            status_code=400,
            details=details
        )


class AuthenticationException(TaoshaException):
    """认证异常"""
    
    def __init__(self, message: str = "认证失败", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code=401001,
            status_code=401,
            details=details
        )


class AuthorizationException(TaoshaException):
    """授权异常"""
    
    def __init__(self, message: str = "权限不足", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code=403001,
            status_code=403,
            details=details
        )


class ResourceNotFoundException(TaoshaException):
    """资源未找到异常"""
    
    def __init__(self, message: str = "资源未找到", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code=404001,
            status_code=404,
            details=details
        )


class DatabaseException(TaoshaException):
    """数据库异常"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=f"数据库错误: {message}",
            error_code=500001,
            status_code=500,
            details=details
        )


class QueryEngineException(TaoshaException):
    """查询引擎异常"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=f"查询引擎错误: {message}",
            error_code=500002,
            status_code=500,
            details=details
        )


class LLMException(TaoshaException):
    """大语言模型异常"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=f"LLM服务错误: {message}",
            error_code=500003,
            status_code=500,
            details=details
        )


class VectorDBException(TaoshaException):
    """向量数据库异常"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=f"向量数据库错误: {message}",
            error_code=500004,
            status_code=500,
            details=details
        )


class NLQueryException(TaoshaException):
    """自然语言查询异常"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=f"查询处理错误: {message}",
            error_code=500005,
            status_code=500,
            details=details
        )


class ConfigurationException(TaoshaException):
    """配置异常"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=f"配置错误: {message}",
            error_code=500006,
            status_code=500,
            details=details
        )


class BusinessLogicException(TaoshaException):
    """业务逻辑异常"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code=400002,
            status_code=400,
            details=details
        )


class RateLimitException(TaoshaException):
    """请求频率限制异常"""
    
    def __init__(self, message: str = "请求过于频繁", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code=429001,
            status_code=429,
            details=details
        )


class ExternalServiceException(TaoshaException):
    """外部服务异常"""
    
    def __init__(self, service_name: str, message: str, details: Optional[Any] = None):
        super().__init__(
            message=f"外部服务 {service_name} 错误: {message}",
            error_code=502001,
            status_code=502,
            details=details
        )


# 异常代码映射
EXCEPTION_CODE_MAP = {
    400001: "参数验证失败",
    400002: "业务逻辑错误",
    401001: "认证失败",
    403001: "权限不足",
    404001: "资源未找到",
    429001: "请求频率限制",
    500000: "服务器内部错误",
    500001: "数据库错误",
    500002: "查询引擎错误",
    500003: "LLM服务错误",
    500004: "向量数据库错误",
    500005: "查询处理错误",
    500006: "配置错误",
    502001: "外部服务错误",
}


def get_error_message(error_code: int) -> str:
    """根据错误代码获取错误消息"""
    return EXCEPTION_CODE_MAP.get(error_code, "未知错误")