"""
本地Embedding服务 - 基于sentence-transformers和onnxruntime
"""

from typing import List, Optional, Dict, Any
import hashlib
import json
from pathlib import Path

from chromadb import EmbeddingFunction, Documents

from utils.config import settings
from utils.logger import logger


class LocalEmbeddingService:
    """本地Embedding服务实现"""

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
            raise ImportError("请安装sentence-transformers")
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

    def __call__(self, texts: List[str]) -> List[List[float]]:
        """
        计算文本的embedding

        Args:
            texts: 文本列表

        Returns:
            embedding列表
        """
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


class LocalEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    兼容ChromaDB的Embedding函数接口
    使用方法:
    - 单个文本: embedding_function("文本")
    - 批量文本: embedding_function(["文本1", "文本2"])
    """

    def __init__(self, *args: Any, **kwargs: Any):
        self.service = LocalEmbeddingService()

    def __call__(self, input) -> List[List[float]]:
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

        return self.service(texts)

    def get_dimension(self) -> int:
        """获取embedding维度"""
        return self.service.get_dimension()

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.service.is_available()

    def name(self) -> str:
        """
        返回embedding函数的名称
        ChromaDB需要这个方法来识别embedding函数
        """
        return "local_embedding_function"

    def __str__(self) -> str:
        """字符串表示"""
        return f"LocalEmbeddingFunction(model={self.service._model_path})"