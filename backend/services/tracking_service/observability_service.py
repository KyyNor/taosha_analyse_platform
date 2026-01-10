"""
可观测性服务 - 管理外部追踪平台集成
支持 Langfuse
"""

from utils.config import settings
from utils.logger import logger

# 全局追踪处理器实例
_tracing_handler = None
_langfuse_client = None

def initialize_observability():
    """根据配置初始化追踪处理器"""
    global _tracing_handler
    global _langfuse_client

    if settings.tracing_type == "langfuse":
        try:
            from langfuse import get_client
            from langfuse.langchain import CallbackHandler
            import os

            os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
            os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
            os.environ["LANGFUSE_HOST"] = settings.langfuse_host
            _langfuse_client = get_client()

            # Verify connection
            if _langfuse_client.auth_check():
                logger.info("Langfuse client is authenticated and ready!")
                _tracing_handler = CallbackHandler()
            else:
                logger.error("Langfuse authentication failed. Please check your credentials and host.")
                _tracing_handler = None

        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")
            _tracing_handler = None
    else:
        logger.info(f"Tracing disabled or unknown type: {settings.tracing_type}")
        _tracing_handler = None


def get_tracing_handler():
    """获取追踪处理器

    Returns:
        追踪处理器实例，如果未初始化或禁用则返回 None
    """
    return _tracing_handler


def get_langfuse_client():
    return _langfuse_client