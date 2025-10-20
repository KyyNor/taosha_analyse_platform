"""
向量存储工厂类 - 支持一键切换向量库，提供全局唯一实例
"""

from typing import Dict, Any, Optional

from services.llm_service.embedding_service import get_chroma_embedding_function
from services.vector_store.base import VectorStore
from utils.logger import logger
from utils.config import settings


class VectorStoreFactory:
    """向量存储工厂类

    支持工厂模式，可以通过配置一键切换不同的向量库实现
    使用延迟导入避免依赖问题
    提供全局唯一实例管理
    """

    # 支持的向量库类型
    SUPPORTED_STORES = {
        "chromadb": "services.vector_store.chromadb_store:ChromaDBStore",
        "qdrant": "services.vector_store.qdrant_store:QdrantStore"
    }

    # 全局实例
    _vector_store: Optional[VectorStore] = None
    _initialized: bool = False

    @staticmethod
    def _load_class(module_path: str):
        """动态加载类

        Args:
            module_path: 模块路径 (格式: "module.path:ClassName")

        Returns:
            加载的类
        """
        module_name, class_name = module_path.split(":")
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)

    @staticmethod
    def create(store_type: str,
               config: Dict[str, Any] = None) -> VectorStore:
        """创建向量存储实例

        Args:
            store_type: 向量库类型 ("chromadb" 或 "qdrant")
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
            # 使用延迟加载获取类
            module_path = VectorStoreFactory.SUPPORTED_STORES[store_type]
            store_class = VectorStoreFactory._load_class(module_path)

            if store_type == "chromadb":
                # 创建 embedding 函数
                embedding_function = get_chroma_embedding_function()

                return VectorStoreFactory._create_chromadb(
                    store_class,
                    embedding_function,
                    config
                )
            elif store_type == "qdrant":
                embedding_func = None
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
                         config: Dict[str, Any]) -> VectorStore:
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
                       config: Dict[str, Any]) -> VectorStore:
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

    # 全局实例管理方法
    @classmethod
    def get_vector_store(cls) -> VectorStore:
        """获取全局 VectorStore 实例

        如果实例未初始化，会根据配置文件自动初始化

        Returns:
            VectorStore 全局实例
        """
        if cls._vector_store is None or not cls._initialized:
            cls._initialize_from_config()
        return cls._vector_store

    @classmethod
    def _initialize_from_config(cls):
        """根据配置文件初始化全局 VectorStore 实例

        Raises:
            RuntimeError: 初始化失败时抛出
        """
        try:
            logger.info("开始初始化全局 VectorStore 实例")

            # 获取向量存储配置
            # 先尝试从 settings 读取，如果没有则从 config.yaml 读取
            store_type = getattr(settings, 'vector_store_type', 'chromadb')
            collection_name = getattr(settings, 'vector_store_collection_name', 'taosha_knowledge')
            persist_dir = getattr(settings, 'vector_store_persist_dir', './database/chromadb')

            # 如果 settings 中没有，尝试从配置文件读取
            if not hasattr(settings, 'vector_store_type'):
                try:
                    from utils.config import get_config
                    config = get_config()
                    vector_store_config = config.get('vector_store', {})
                    store_type = vector_store_config.get('store_type', 'chromadb')
                    collection_name = vector_store_config.get('collection_name', 'taosha_knowledge')
                    persist_dir = vector_store_config.get('persist_dir', './database/chromadb')
                except Exception as e:
                    logger.warning(f"从配置文件读取向量存储配置失败，使用默认值: {e}")

            # 构建配置字典
            config = {
                "collection_name": collection_name,
                "persist_dir": persist_dir
            }

            # 创建 VectorStore 实例
            cls._vector_store = cls.create(store_type, config)
            cls._initialized = True

            logger.info(f"全局 VectorStore 实例初始化成功: store_type={store_type}, collection_name={collection_name}")

        except Exception as e:
            logger.error(f"初始化全局 VectorStore 实例失败: {e}")
            raise RuntimeError(f"全局 VectorStore 初始化失败: {e}")

    @classmethod
    def reset(cls):
        """重置全局实例（主要用于测试）"""
        cls._vector_store = None
        cls._initialized = False
        logger.info("全局 VectorStore 实例已重置")


def get_vector_store() -> VectorStore:
    """获取全局 VectorStore 实例的便捷函数

    Returns:
        VectorStore 全局实例
    """
    return VectorStoreFactory.get_vector_store()
