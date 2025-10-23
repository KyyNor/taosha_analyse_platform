"""
可观测性服务 - 管理外部追踪平台集成
支持 Langfuse 和 Phoenix 等追踪平台
"""

from utils.config import settings
from utils.logger import logger

# 全局追踪处理器实例
_tracing_handler = None


def initialize_observability():
    """根据配置初始化追踪处理器"""
    global _tracing_handler

    if settings.tracing_type == "langfuse":
        try:
            from langfuse import get_client
            from langfuse.langchain import CallbackHandler
            import os

            os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
            os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
            os.environ["LANGFUSE_HOST"] = settings.langfuse_host
            langfuse = get_client()

            # Verify connection
            if langfuse.auth_check():
                logger.info("Langfuse client is authenticated and ready!")
                _tracing_handler = CallbackHandler()
            else:
                logger.error("Langfuse authentication failed. Please check your credentials and host.")
                _tracing_handler = None

        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")
            _tracing_handler = None

    elif settings.tracing_type == "phoenix":
        try:
            import phoenix as px
            # 启动本地服务器（内嵌在 Python 进程中）
            import os
            os.environ["PHOENIX_WORKING_DIR"] = settings.phoenix_work_dir
            os.environ["PHOENIX_HOST"] = '0.0.0.0'
            os.environ["PHOENIX_PORT"] = settings.phoenix_port
            session = px.launch_app(use_temp_dir=False)
            # 自动追踪 LangChain/LangGraph
            from phoenix.otel import register
            from openinference.instrumentation.langchain import LangChainInstrumentor

            tracer_provider = register()
            LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

            # Phoenix 使用自动instrumentation，不需要返回handler
            _tracing_handler = None
            logger.info("Phoenix observability initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Phoenix: {e}")
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
