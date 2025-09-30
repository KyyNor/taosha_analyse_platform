"""
淘沙分析平台 - 日志工具类
基于loguru的统一日志管理
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from utils.config import get_config


class LoggerManager:
    """日志管理器"""

    def __init__(self):
        self.config = get_config()
        self._initialized = False
        self._setup_logger()

    def _setup_logger(self):
        """设置loguru日志配置"""
        if self._initialized:
            return

        # 移除默认处理器
        logger.remove()

        # 获取日志配置
        log_level = self.config.get('logging.level', 'INFO')
        log_rotation = self.config.get('logging.rotation', '10 MB')
        log_retention = self.config.get('logging.retention', '7 days')
        log_compression = self.config.get('logging.compression', 'gz')

        # 控制台输出
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
            colorize=True,
            backtrace=True,
            diagnose=True
        )

        # 文件输出
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        logger.add(
            log_dir / "app.log",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=log_rotation,
            retention=log_retention,
            compression=log_compression,
            encoding="utf-8",
            backtrace=True,
            diagnose=True
        )

        # 错误日志单独文件
        logger.add(
            log_dir / "error.log",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=log_rotation,
            retention=log_retention,
            compression=log_compression,
            encoding="utf-8",
            backtrace=True,
            diagnose=True
        )

        self._initialized = True

    def get_logger(self, name: Optional[str] = None):
        """获取日志记录器"""
        if name:
            return logger.bind(name=name)
        return logger

    def set_level(self, level: str):
        """设置日志级别"""
        logger.remove()
        self._setup_logger()

    def add_file_handler(self, file_path: str, level: str = "INFO", **kwargs):
        """添加文件处理器"""
        logger.add(
            file_path,
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            encoding="utf-8",
            **kwargs
        )


# 全局日志管理器实例
_logger_manager = LoggerManager()


def get_logger(name: Optional[str] = None):
    """获取日志记录器"""
    return _logger_manager.get_logger(name)


def set_log_level(level: str):
    """设置日志级别"""
    _logger_manager.set_level(level)


def add_log_file(file_path: str, level: str = "INFO", **kwargs):
    """添加日志文件"""
    _logger_manager.add_file_handler(file_path, level, **kwargs)


# 便捷的日志函数
def debug(message: str, **kwargs):
    """调试日志"""
    get_logger().debug(message, **kwargs)


def info(message: str, **kwargs):
    """信息日志"""
    get_logger().info(message, **kwargs)


def warning(message: str, **kwargs):
    """警告日志"""
    get_logger().warning(message, **kwargs)


def error(message: str, **kwargs):
    """错误日志"""
    get_logger().error(message, **kwargs)


def critical(message: str, **kwargs):
    """严重错误日志"""
    get_logger().critical(message, **kwargs)


def exception(message: str, **kwargs):
    """异常日志（包含堆栈跟踪）"""
    get_logger().exception(message, **kwargs)


# 向后兼容的logger实例
logger = get_logger()


class LoggerMixin:
    """日志混入类，为其他类提供日志功能"""

    @property
    def logger(self):
        """获取类专属日志记录器"""
        return get_logger(self.__class__.__name__)


def log_function_call(func):
    """函数调用日志装饰器"""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_logger = get_logger(func.__module__)
        func_logger.debug(f"调用函数 {func.__name__}，参数: args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            func_logger.debug(f"函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            func_logger.error(f"函数 {func.__name__} 执行失败: {e}")
            raise

    return wrapper


def log_method_call(method):
    """方法调用日志装饰器"""
    import functools

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        method_logger = get_logger(self.__class__.__name__)
        method_logger.debug(f"调用方法 {self.__class__.__name__}.{method.__name__}，参数: args={args}, kwargs={kwargs}")
        try:
            result = method(self, *args, **kwargs)
            method_logger.debug(f"方法 {self.__class__.__name__}.{method.__name__} 执行成功")
            return result
        except Exception as e:
            method_logger.error(f"方法 {self.__class__.__name__}.{method.__name__} 执行失败: {e}")
            raise

    return wrapper


# 性能日志装饰器
def log_performance(func):
    """性能日志装饰器"""
    import functools
    import time

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func_logger = get_logger(func.__module__)

        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            func_logger.info(f"函数 {func.__name__} 执行时间: {execution_time:.3f}秒")
            return result
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            func_logger.error(f"函数 {func.__name__} 执行失败，耗时: {execution_time:.3f}秒，错误: {e}")
            raise

    return wrapper