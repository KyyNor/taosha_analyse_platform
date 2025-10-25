"""
统一的Embedding服务 - 支持本地模型和在线模型
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import hashlib
import json
from pathlib import Path

from chromadb import EmbeddingFunction, Documents
from openai import OpenAI

from utils.config import settings
from utils.logger import logger


class BaseEmbeddingService(ABC):
    """Embedding服务抽象基类"""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """计算多个文本的embedding"""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """计算单个文本的embedding"""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """获取embedding维度"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查服务是否可用"""
        pass


class LocalEmbeddingService(BaseEmbeddingService):
    """本地Embedding服务实现 - 基于sentence-transformers"""

    def __init__(self):
        self._model = None
        self._cache = {}
        self._cache_max_size = settings.embedding_cache_size
        self._model_path = settings.embedding_model_path
        self._device = settings.embedding_device

        logger.info(f"本地Embedding服务初始化，模型路径: {self._model_path}, 设备: {self._device}")

    def _load_model(self):
        """懒加载模型"""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"开始加载本地模型: {self._model_path}")
            self._model = SentenceTransformer(
                self._model_path,
                device=self._device
            )

            # 测试模型
            test_embedding = self._model.encode(["测试"])
            logger.info(f"模型加载成功，embedding维度: {len(test_embedding[0])}")

        except ImportError:
            raise ImportError("请安装sentence-transformers: pip install sentence-transformers")
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise RuntimeError(f"无法加载本地模型 {self._model_path}: {e}")

    def _get_cache_key(self, texts: List[str]) -> str:
        """生成缓存键"""
        content = json.dumps(texts, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _update_cache(self, key: str, value: List[List[float]]):
        """更新缓存"""
        if len(self._cache) >= self._cache_max_size:
            # 删除最旧的缓存项（简单的LRU实现）
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[key] = value

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """计算多个文本的embedding"""
        if not texts:
            return []

        # 检查缓存
        cache_key = self._get_cache_key(texts)
        if cache_key in self._cache:
            logger.debug(f"从缓存获取embedding，文本数量: {len(texts)}")
            return self._cache[cache_key]

        # 确保模型已加载
        if self._model is None:
            self._load_model()

        try:
            # 计算embedding
            logger.debug(f"计算embedding，文本数量: {len(texts)}")
            embeddings = self._model.encode(
                texts,
                batch_size=32,
                normalize_embeddings=True,
                convert_to_numpy=True
            )

            # 转换为列表格式
            result = embeddings.tolist()

            # 更新缓存
            self._update_cache(cache_key, result)

            logger.debug(f"embedding计算完成，维度: {len(result[0]) if result else 0}")
            return result

        except Exception as e:
            logger.error(f"embedding计算失败: {e}")
            raise RuntimeError(f"embedding计算失败: {e}")

    def embed_query(self, text: str) -> List[float]:
        """计算单个文本的embedding"""
        if not text:
            return []

        result = self.embed_documents([text])
        return result[0] if result else []

    def get_dimension(self) -> int:
        """获取embedding维度"""
        if self._model is None:
            self._load_model()

        test_embedding = self._model.encode(["测试"])
        return len(test_embedding[0])

    def is_available(self) -> bool:
        """检查服务是否可用"""
        try:
            if self._model is None:
                self._load_model()
            return True
        except Exception as e:
            logger.warning(f"本地embedding服务不可用: {e}")
            return False


class RemoteEmbeddingService(BaseEmbeddingService):
    """远程Embedding服务实现 - 支持OpenAI兼容接口"""

    def __init__(self):
        self.api_key = settings.embedding_api_key
        self.base_url = settings.embedding_base_url
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions
        self.client = None

        if not self.api_key:
            raise ValueError("远程embedding服务需要配置api_key")

        if not self.base_url:
            raise ValueError("远程embedding服务需要配置base_url")

        logger.info(f"远程Embedding服务初始化，API: {self.base_url}, 模型: {self.model}")

    def _get_client(self) -> OpenAI:
        """获取OpenAI客户端"""
        if self.client is None:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        return self.client

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """计算多个文本的embedding"""
        if not texts:
            return []

        try:
            client = self._get_client()

            # 分批处理，避免超出API限制
            batch_size = 100
            all_embeddings = []

            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]

                response = client.embeddings.create(
                    model=self.model,
                    input=batch_texts,
                    encoding_format="float"
                )

                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                logger.debug(f"批处理embedding计算完成，批次大小: {len(batch_texts)}")

            logger.debug(f"远程embedding计算完成，文本数量: {len(texts)}，维度: {len(all_embeddings[0]) if all_embeddings else 0}")
            return all_embeddings

        except Exception as e:
            logger.error(f"远程embedding计算失败: {e}")
            raise RuntimeError(f"远程embedding计算失败: {e}")

    def embed_query(self, text: str) -> List[float]:
        """计算单个文本的embedding"""
        if not text:
            return []

        result = self.embed_documents([text])
        return result[0] if result else []

    def get_dimension(self) -> int:
        """获取embedding维度"""
        # 尝试通过API获取维度，如果失败则返回配置值
        try:
            test_embedding = self.embed_query("测试")
            return len(test_embedding)
        except Exception:
            return self.dimensions

    def is_available(self) -> bool:
        """检查服务是否可用"""
        try:
            # 尝试计算一个简单的embedding
            self.embed_query("测试")
            return True
        except Exception as e:
            logger.warning(f"远程embedding服务不可用: {e}")
            return False


class EmbeddingServiceFactory:
    """Embedding服务工厂类"""

    @staticmethod
    def create_from_config() -> BaseEmbeddingService:
        """根据配置创建Embedding服务"""
        embedding_type = settings.embedding_type.lower()

        if embedding_type == "local":
            if not settings.embedding_model_path:
                raise ValueError("本地embedding服务需要配置model_path")
            return LocalEmbeddingService()

        elif embedding_type == "remote":
            return RemoteEmbeddingService()

        else:
            raise ValueError(f"不支持的embedding类型: {embedding_type}，支持的类型: local, remote")


class ChromaEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    兼容ChromaDB的Embedding函数接口
    适配ChromaDB的EmbeddingFunction接口要求
    """

    def __init__(self, service: BaseEmbeddingService):
        self.service = service

    def __call__(self, input: Documents) -> List[List[float]]:
        """
        处理输入数据，支持单个文本或文本列表

        Args:
            input: 单个文本或文本列表

        Returns:
            embedding列表
        """
        # 统一处理为列表格式
        if isinstance(input, str):
            texts = [input]
        elif isinstance(input, list):
            texts = input
        else:
            raise ValueError(f"不支持的输入类型: {type(input)}")

        return self.service.embed_documents(texts)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """ChromaDB接口兼容方法"""
        return self.service.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """ChromaDB接口兼容方法"""
        return self.service.embed_query(text)

    def name(self) -> str:
        """返回embedding函数的名称"""
        service_type = "local" if isinstance(self.service, LocalEmbeddingService) else "remote"
        return f"chroma_embedding_function_{service_type}"

    def __str__(self) -> str:
        """字符串表示"""
        service_type = "local" if isinstance(self.service, LocalEmbeddingService) else "remote"
        return f"ChromaEmbeddingFunction(service_type={service_type})"


def get_embedding_service() -> BaseEmbeddingService:
    """获取全局Embedding服务实例"""
    return EmbeddingServiceFactory.create_from_config()


def get_chroma_embedding_function() -> EmbeddingFunction:
    """获取ChromaDB兼容的Embedding函数实例"""
    service = get_embedding_service()
    return ChromaEmbeddingFunction(service)


class QdrantEmbeddingFunction:
    """
    适配Qdrant的Embedding函数接口
    复用现有的embedding服务，提供Qdrant兼容的接口
    """

    def __init__(self, service: BaseEmbeddingService):
        self.service = service

    def encode(self, texts: List[str]) -> List[List[float]]:
        """
        计算文本的embedding向量
        
        Args:
            texts: 文本列表
            
        Returns:
            embedding向量列表
        """
        return self.service.embed_documents(texts)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """计算多个文本的embedding"""
        return self.service.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """计算单个文本的embedding"""
        return self.service.embed_query(text)

    def get_dimension(self) -> int:
        """获取embedding维度"""
        return self.service.get_dimension()

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.service.is_available()

    def name(self) -> str:
        """返回embedding函数的名称"""
        service_type = "local" if isinstance(self.service, LocalEmbeddingService) else "remote"
        return f"qdrant_embedding_function_{service_type}"

    def __str__(self) -> str:
        """字符串表示"""
        service_type = "local" if isinstance(self.service, LocalEmbeddingService) else "remote"
        return f"QdrantEmbeddingFunction(service_type={service_type})"


def get_qdrant_embedding_function() -> QdrantEmbeddingFunction:
    """获取Qdrant兼容的Embedding函数实例"""
    service = get_embedding_service()
    return QdrantEmbeddingFunction(service)