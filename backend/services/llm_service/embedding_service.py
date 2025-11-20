"""
Embedding服务 - 基于LocalAI的文本嵌入服务
"""

from typing import List
from langchain_openai import OpenAIEmbeddings
from utils.logger import logger
from utils.config import settings


class EmbeddingService:
    """基于LocalAI的文本嵌入服务

    使用LangChain的OpenAIEmbeddings连接LocalAI服务
    """

    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        """初始化Embedding服务

        Args:
            base_url: LocalAI服务的基础URL
            api_key: API密钥（LocalAI通常不需要）
            model: 使用的嵌入模型名称
        """
        self.base_url = base_url or settings.embedding_base_url
        self.api_key = api_key or settings.embedding_api_key or "not-needed"
        self.model = model or settings.embedding_model

        if not self.base_url:
            raise ValueError("Embedding base URL is required")

        try:
            logger.info(f"初始化LocalAI Embedding服务: {self.base_url}")

            # 初始化LangChain OpenAIEmbeddings客户端
            self.client = OpenAIEmbeddings(
                model=self.model,
                openai_api_base=self.base_url,
                openai_api_key=self.api_key,
                chunk_size=1000,
                max_retries=3,
                request_timeout=60,
                tiktoken_enabled=False  # LocalAI模型通常不需要tiktoken
            )

            logger.info(f"LocalAI Embedding服务初始化完成，模型: {self.model}")

        except Exception as e:
            logger.error(f"LocalAI Embedding服务初始化失败: {e}")
            raise RuntimeError(f"Embedding服务初始化失败: {e}")

    def embed_query(self, text: str) -> List[float]:
        """为单个查询文本生成嵌入向量

        Args:
            text: 查询文本

        Returns:
            嵌入向量列表
        """
        try:
            return self.client.embed_query(text)
        except Exception as e:
            logger.error(f"生成查询嵌入失败: {e}")
            raise RuntimeError(f"生成查询嵌入失败: {e}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """为多个文档文本生成嵌入向量

        Args:
            texts: 文档文本列表

        Returns:
            嵌入向量列表的列表
        """
        if not texts:
            return []

        try:
            return self.client.embed_documents(texts)
        except Exception as e:
            logger.error(f"生成文档嵌入失败: {e}")
            raise RuntimeError(f"生成文档嵌入失败: {e}")

    def health_check(self) -> bool:
        """检查LocalAI服务健康状态

        Returns:
            服务是否健康
        """
        try:
            # 尝试生成一个简单的嵌入向量来测试连接
            test_embedding = self.client.embed_query("test")
            return len(test_embedding) > 0
        except Exception as e:
            logger.error(f"Embedding服务健康检查失败: {e}")
            return False

    @property
    def embedding_dimension(self) -> int:
        """获取嵌入向量维度

        Returns:
            嵌入向量维度
        """
        try:
            # 生成一个测试嵌入来获取维度
            test_embedding = self.client.embed_query("test")
            return len(test_embedding)
        except Exception as e:
            logger.error(f"获取嵌入维度失败: {e}")
            # 从配置中获取默认维度
            return getattr(settings, 'embedding_dimensions', 1024)


# 全局缓存实例
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """获取全局Embedding服务实例

    Returns:
        EmbeddingService实例
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service