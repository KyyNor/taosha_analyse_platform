"""
向量存储基础测试 - 不依赖外部服务
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# 添加 backend 目录到路径
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from services.vector_store import VectorStore, VectorStoreFactory
from utils.logger import logger


class MockEmbeddingFunction:
    """模拟 Embedding 函数"""

    def embed_documents(self, documents: list) -> list:
        """返回模拟的 embedding"""
        # 返回随机的 embedding（维度为 5）
        import random
        return [[random.random() for _ in range(5)] for _ in documents]

    def embed_query(self, query: str) -> list:
        """返回模拟的 query embedding"""
        import random
        return [random.random() for _ in range(5)]

    def name(self) -> str:
        """返回 embedding 函数名称（ChromaDB 需要）"""
        return "mock_embedding_function"


class TestVectorStoreFactory:
    """向量存储工厂测试"""

    def test_supported_types(self):
        """测试支持的库类型"""
        types = VectorStoreFactory.get_supported_types()
        assert "chromadb" in types
        assert "qdrant" in types
        logger.info(f"支持的向量库类型: {types}")

    def test_create_chromadb(self):
        """测试创建 ChromaDB 实例"""
        embedding_func = MockEmbeddingFunction()
        config = {"collection_name": "test", "persist_dir": None}
        store = VectorStoreFactory.create("chromadb", embedding_func, config)
        assert store is not None
        assert isinstance(store, VectorStore)
        logger.info("ChromaDB 实例创建成功")
        store.clear()

    def test_create_qdrant(self):
        """测试创建 Qdrant 实例"""
        embedding_func = MockEmbeddingFunction()
        config = {"collection_name": "test", "embedding_dimension": 5}
        store = VectorStoreFactory.create("qdrant", embedding_func, config)
        assert store is not None
        assert isinstance(store, VectorStore)
        logger.info("Qdrant 实例创建成功")
        store.clear()

    def test_invalid_store_type(self):
        """测试无效的库类型"""
        embedding_func = MockEmbeddingFunction()
        with pytest.raises(ValueError) as exc_info:
            VectorStoreFactory.create("invalid_store", embedding_func)
        assert "不支持的向量库类型" in str(exc_info.value)
        logger.info("无效库类型异常处理正确")


class TestChromatStoreBasic:
    """ChromaDB 存储基础测试"""

    def test_add_and_count(self):
        """测试添加文档和计数"""
        embedding_func = MockEmbeddingFunction()
        config = {"collection_name": "test_add", "persist_dir": None}
        store = VectorStoreFactory.create("chromadb", embedding_func, config)

        try:
            documents = ["这是第一个文档", "这是第二个文档"]
            ids = store.add(documents)

            assert len(ids) == 2
            assert store.count() == 2
            logger.info("ChromaDB 添加和计数功能正常")
        finally:
            store.clear()

    def test_search_basic(self):
        """测试基础搜索"""
        embedding_func = MockEmbeddingFunction()
        config = {"collection_name": "test_search", "persist_dir": None}
        store = VectorStoreFactory.create("chromadb", embedding_func, config)

        try:
            documents = ["销售数据", "客户信息", "订单管理"]
            store.add(documents)

            results = store.search("销售", top_k=2)

            assert isinstance(results, list)
            assert len(results) <= 2
            assert all("id" in r and "content" in r and "score" in r for r in results)
            logger.info("ChromaDB 搜索功能正常")
        finally:
            store.clear()

    def test_delete_documents(self):
        """测试删除文档"""
        embedding_func = MockEmbeddingFunction()
        config = {"collection_name": "test_delete", "persist_dir": None}
        store = VectorStoreFactory.create("chromadb", embedding_func, config)

        try:
            documents = ["文档1", "文档2", "文档3"]
            ids = store.add(documents)
            assert store.count() == 3

            store.delete(ids[:2])
            assert store.count() == 1
            logger.info("ChromaDB 删除功能正常")
        finally:
            store.clear()

    def test_health_check(self):
        """测试健康检查"""
        embedding_func = MockEmbeddingFunction()
        config = {"collection_name": "test_health", "persist_dir": None}
        store = VectorStoreFactory.create("chromadb", embedding_func, config)

        try:
            assert store.health_check() is True
            logger.info("ChromaDB 健康检查正常")
        finally:
            store.clear()


class TestQdrantStoreBasic:
    """Qdrant 存储基础测试"""

    def test_add_and_count(self):
        """测试添加文档和计数"""
        embedding_func = MockEmbeddingFunction()
        config = {"collection_name": "test_add_q", "embedding_dimension": 5}
        store = VectorStoreFactory.create("qdrant", embedding_func, config)

        try:
            documents = ["这是第一个文档", "这是第二个文档"]
            ids = store.add(documents)

            assert len(ids) == 2
            assert store.count() == 2
            logger.info("Qdrant 添加和计数功能正常")
        finally:
            store.clear()

    def test_search_basic(self):
        """测试基础搜索"""
        embedding_func = MockEmbeddingFunction()
        config = {"collection_name": "test_search_q", "embedding_dimension": 5}
        store = VectorStoreFactory.create("qdrant", embedding_func, config)

        try:
            documents = ["销售数据", "客户信息", "订单管理"]
            store.add(documents)

            results = store.search("销售", top_k=2)

            assert isinstance(results, list)
            assert len(results) <= 2
            assert all("id" in r and "content" in r and "score" in r for r in results)
            logger.info("Qdrant 搜索功能正常")
        finally:
            store.clear()

    def test_delete_documents(self):
        """测试删除文档"""
        embedding_func = MockEmbeddingFunction()
        config = {"collection_name": "test_delete_q", "embedding_dimension": 5}
        store = VectorStoreFactory.create("qdrant", embedding_func, config)

        try:
            documents = ["文档1", "文档2", "文档3"]
            ids = store.add(documents)
            assert store.count() == 3

            store.delete(ids[:2])
            assert store.count() == 1
            logger.info("Qdrant 删除功能正常")
        finally:
            store.clear()

    def test_health_check(self):
        """测试健康检查"""
        embedding_func = MockEmbeddingFunction()
        config = {"collection_name": "test_health_q", "embedding_dimension": 5}
        store = VectorStoreFactory.create("qdrant", embedding_func, config)

        try:
            assert store.health_check() is True
            logger.info("Qdrant 健康检查正常")
        finally:
            store.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
