# Vanna imports
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from vanna.chromadb import ChromaDB_VectorStore
from vanna.openai import OpenAI_Chat
from openai import OpenAI

from pathlib import Path

from utils.config import settings
from utils.logger import logger
from services.local_embedding_service import LocalEmbeddingFunction

class TaoshaVanna(ChromaDB_VectorStore, OpenAI_Chat):
    """自定义Vanna实现"""

    def __init__(self, config=None):
        # 初始化ChromaDB
        chroma_path = settings.chromadb_path
        Path(chroma_path).mkdir(parents=True, exist_ok=True)

        # 创建embedding函数配置
        chroma_config = {
            'path': chroma_path,
            'client': 'persistent',
        }

        # 根据配置类型选择embedding服务
        embedding_func = None

        if settings.embedding_type == "local":
            # 使用本地embedding模型
            if settings.embedding_model_path:
                try:
                    logger.info(f"使用本地embedding模型: {settings.embedding_model_path}")
                    embedding_func = LocalEmbeddingFunction()
                    logger.info("本地embedding服务初始化成功")
                except Exception as e:
                    logger.warning(f"本地embedding服务初始化失败: {e}")
                    embedding_func = None
            else:
                logger.warning("配置了本地模式但未指定模型路径")

        elif settings.embedding_type == "remote":
            # 使用远程embedding API
            if settings.embedding_api_key:
                try:
                    logger.info("使用远程embedding API")
                    embedding_func = OpenAIEmbeddingFunction(
                        api_key=settings.embedding_api_key,
                        model_name=settings.embedding_model,
                        api_base=settings.embedding_base_url,
                        dimensions=settings.embedding_dimensions
                    )
                    logger.info("远程embedding服务初始化成功")
                except Exception as e:
                    logger.warning(f"远程embedding服务初始化失败: {e}")
                    embedding_func = None
            else:
                logger.warning("配置了远程模式但未指定API密钥")

        else:
            logger.warning(f"未知的embedding类型: {settings.embedding_type}")

        # 设置embedding函数
        if embedding_func:
            chroma_config['embedding_function'] = embedding_func
        else:
            logger.warning("未配置有效的embedding服务，ChromaDB将使用默认embedding")

        ChromaDB_VectorStore.__init__(self, config=chroma_config)

        # 创建 OpenAI 客户端配置
        openai_config = {
            'model': settings.openai_model,
            'temperature': settings.openai_temperature,
            'api_key': settings.openai_api_key
        }

        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

        OpenAI_Chat.__init__(self, client=client, config=openai_config)

        self.training_hash = None
        logger.info("TaoshaVanna初始化完成")

