"""
向量存储工厂类 - 支持一键切换向量库
"""

from typing import Dict, Any, Optional
from services.vector_store.base import VectorStore
from services.vector_store.chromadb_store import ChromaDBStore
from services.vector_store.qdrant_store import QdrantStore
from utils.logger import logger


class VectorStoreFactory:
    """向量存储工厂类

    支持工厂模式，可以通过配置一键切换不同的向量库实现
    """

    # 支持的向量库类型
    SUPPORTED_STORES = {
        "chromadb": ChromaDBStore,
        "qdrant": QdrantStore
    }

    @staticmethod
    def create(store_type: str,
               embedding_func,
               config: Dict[str, Any] = None) -> VectorStore:
        """创建向量存储实例

        Args:
            store_type: 向量库类型 ("chromadb" 或 "qdrant")
            embedding_func: Embedding 函数实例
            config: 配置字典，包含库特定的参数

        Returns:
            VectorStore 实例

        Raises:
            ValueError: 不支持的库类型或配置无效时抛出

        Examples:
            # ChromaDB 持久化模式
            config = {
                "persist_dir": "./database/chromadb",
                "collection_name": "taosha_knowledge"
            }
            store = VectorStoreFactory.create("chromadb", embedding_func, config)

            # Qdrant 内存模式
            config = {
                "collection_name": "taosha_knowledge",
                "embedding_dimension": 1024
            }
            store = VectorStoreFactory.create("qdrant", embedding_func, config)
        """
        store_type = store_type.lower()

        if store_type not in VectorStoreFactory.SUPPORTED_STORES:
            raise ValueError(
                f"不支持的向量库类型: {store_type}，"
                f"支持的类型: {list(VectorStoreFactory.SUPPORTED_STORES.keys())}"
            )

        if config is None:
            config = {}

        try:
            store_class = VectorStoreFactory.SUPPORTED_STORES[store_type]

            if store_type == "chromadb":
                return VectorStoreFactory._create_chromadb(
                    store_class,
                    embedding_func,
                    config
                )
            elif store_type == "qdrant":
                return VectorStoreFactory._create_qdrant(
                    store_class,
                    embedding_func,
                    config
                )

        except Exception as e:
            logger.error(f"创建向量存储实例失败: {e}")
            raise RuntimeError(f"向量存储创建失败: {e}")

    @staticmethod
    def _create_chromadb(store_class,
                         embedding_func,
                         config: Dict[str, Any]) -> ChromaDBStore:
        """创建 ChromaDB 实例

        Args:
            store_class: ChromaDBStore 类
            embedding_func: Embedding 函数
            config: 配置字典
                - collection_name (str): 集合名称，默认 "taosha_knowledge"
                - persist_dir (str): 持久化目录，如果为None则使用内存模式

        Returns:
            ChromaDBStore 实例
        """
        collection_name = config.get("collection_name", "taosha_knowledge")
        persist_dir = config.get("persist_dir")  # None 表示内存模式

        logger.info(
            f"创建 ChromaDB 实例: "
            f"collection_name={collection_name}, "
            f"persist_dir={persist_dir or '内存模式'}"
        )

        return store_class(
            embedding_func=embedding_func,
            collection_name=collection_name,
            persist_dir=persist_dir
        )

    @staticmethod
    def _create_qdrant(store_class,
                       embedding_func,
                       config: Dict[str, Any]) -> QdrantStore:
        """创建 Qdrant 实例

        Args:
            store_class: QdrantStore 类
            embedding_func: Embedding 函数
            config: 配置字典
                - collection_name (str): 集合名称，默认 "taosha_knowledge"
                - embedding_dimension (int): Embedding 维度，默认 1024

        Returns:
            QdrantStore 实例
        """
        collection_name = config.get("collection_name", "taosha_knowledge")
        embedding_dimension = config.get("embedding_dimension", 1024)

        logger.info(
            f"创建 Qdrant 实例 (内存模式): "
            f"collection_name={collection_name}, "
            f"embedding_dimension={embedding_dimension}"
        )

        return store_class(
            embedding_func=embedding_func,
            collection_name=collection_name,
            embedding_dimension=embedding_dimension
        )

    @staticmethod
    def get_supported_types() -> list:
        """获取支持的向量库类型列表

        Returns:
            支持的向量库类型列表
        """
        return list(VectorStoreFactory.SUPPORTED_STORES.keys())
