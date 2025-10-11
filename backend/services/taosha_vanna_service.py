# Vanna imports
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from vanna.chromadb import ChromaDB_VectorStore
from vanna.openai import OpenAI_Chat

from pathlib import Path

from utils.config import settings
from utils.logger import logger

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

        # 如果配置了embedding API，则使用自定义embedding函数
        if settings.embedding_api_key:
            embedding_func = OpenAIEmbeddingFunction(
                api_key=settings.embedding_api_key,
                model_name=settings.embedding_model,
                api_base=settings.embedding_base_url,
                dimensions=settings.embedding_dimensions
            )
            chroma_config['embedding_function'] = embedding_func

        ChromaDB_VectorStore.__init__(self, config=chroma_config)

        # 创建 OpenAI 客户端配置
        openai_config = {
            'model': settings.openai_model,
            'temperature': settings.openai_temperature,
        }
        client = None

        # 只有当 API key 存在时才设置
        if settings.openai_api_key:
            openai_config['api_key'] = settings.openai_api_key

        # 如果有自定义 base_url，需要传递 OpenAI 客户端实例
        if settings.openai_base_url:
            try:
                from openai import OpenAI
                client = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url
                )
            except ImportError:
                logger.warning("OpenAI包不可用，使用默认配置")

        OpenAI_Chat.__init__(self, client=client, config=openai_config)

        self.training_hash = None
        logger.info("TaoshaVanna初始化完成")

