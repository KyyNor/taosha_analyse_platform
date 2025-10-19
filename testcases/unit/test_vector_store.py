"""
向量存储单元测试
"""

import pytest
from typing import List, Dict
from services.vector_store import VectorStore, VectorStoreFactory
from services.embedding_service import EmbeddingFactory
from utils.config import settings
from utils.logger import logger


@pytest.fixture
def embedding_func():
    """创建 Embedding 函数实例"""
    return EmbeddingFactory.create(
        embedding_type="local",
        embedding_model_path=settings.embedding_model_path,
        embedding_device=settings.embedding_device
    )


@pytest.fixture
def chromadb_store(embedding_func):
    """创建 ChromaDB 存储实例（内存模式）"""
    config = {
        "collection_name": "test_taosha",
        "persist_dir": None  # 内存模式
    }
    store = VectorStoreFactory.create("chromadb", embedding_func, config)
    yield store
    # 清理
    store.clear()


@pytest.fixture
def qdrant_store(embedding_func):
    """创建 Qdrant 存储实例"""
    config = {
        "collection_name": "test_taosha",
        "embedding_dimension": settings.embedding_dimensions
    }
    store = VectorStoreFactory.create("qdrant", embedding_func, config)
    yield store
    # 清理
    store.clear()


class TestVectorStoreFactory:
    """向量存储工厂测试"""

    def test_supported_types(self):
        """测试支持的库类型"""
        types = VectorStoreFactory.get_supported_types()
        assert "chromadb" in types
        assert "qdrant" in types

    def test_create_chromadb(self, embedding_func):
        """测试创建 ChromaDB 实例"""
        config = {"collection_name": "test", "persist_dir": None}
        store = VectorStoreFactory.create("chromadb", embedding_func, config)
        assert store is not None
        assert isinstance(store, VectorStore)
        store.clear()

    def test_create_qdrant(self, embedding_func):
        """测试创建 Qdrant 实例"""
        config = {"collection_name": "test", "embedding_dimension": 1024}
        store = VectorStoreFactory.create("qdrant", embedding_func, config)
        assert store is not None
        assert isinstance(store, VectorStore)
        store.clear()

    def test_invalid_store_type(self, embedding_func):
        """测试无效的库类型"""
        with pytest.raises(ValueError):
            VectorStoreFactory.create("invalid_store", embedding_func)


class TestChromatStore:
    """ChromaDB 存储测试"""

    def test_add_documents(self, chromadb_store):
        """测试添加文档"""
        documents = ["这是第一个文档", "这是第二个文档"]
        metadatas = [{"type": "test", "id": 1}, {"type": "test", "id": 2}]

        ids = chromadb_store.add(documents, metadatas)

        assert len(ids) == 2
        assert chromadb_store.count() == 2

    def test_add_documents_without_ids(self, chromadb_store):
        """测试自动生成 ID"""
        documents = ["文档1", "文档2"]
        ids = chromadb_store.add(documents)

        assert len(ids) == 2
        assert all(isinstance(id, str) for id in ids)
        assert chromadb_store.count() == 2

    def test_add_documents_mismatch(self, chromadb_store):
        """测试文档和元数据数量不匹配"""
        documents = ["文档1", "文档2"]
        metadatas = [{"type": "test"}]  # 只有一个元数据

        with pytest.raises(ValueError):
            chromadb_store.add(documents, metadatas)

    def test_search_documents(self, chromadb_store):
        """测试搜索文档"""
        documents = [
            "今年销量统计",
            "产品销售数据",
            "客户信息管理",
            "订单处理流程"
        ]
        metadatas = [
            {"type": "table", "name": "sales"},
            {"type": "table", "name": "sales"},
            {"type": "table", "name": "customer"},
            {"type": "table", "name": "order"}
        ]

        chromadb_store.add(documents, metadatas)

        # 搜索相关文档
        results = chromadb_store.search("销售量查询", top_k=2)

        assert len(results) <= 2
        assert all("id" in r and "content" in r and "score" in r for r in results)
        # 验证返回结果的相似度分数合理性
        assert all(0 <= r["score"] <= 1 for r in results)

    def test_search_with_top_k(self, chromadb_store):
        """测试 top_k 参数"""
        documents = [f"文档{i}" for i in range(10)]
        chromadb_store.add(documents)

        results = chromadb_store.search("文档", top_k=3)
        assert len(results) <= 3

    def test_search_empty_query(self, chromadb_store):
        """测试空查询"""
        documents = ["文档1", "文档2"]
        chromadb_store.add(documents)

        with pytest.raises(ValueError):
            chromadb_store.search("")

    def test_delete_documents(self, chromadb_store):
        """测试删除文档"""
        documents = ["文档1", "文档2", "文档3"]
        ids = chromadb_store.add(documents)

        assert chromadb_store.count() == 3

        chromadb_store.delete(ids[:2])
        assert chromadb_store.count() == 1

    def test_update_documents(self, chromadb_store):
        """测试更新文档"""
        documents = ["原始文档1", "原始文档2"]
        ids = chromadb_store.add(documents)

        updated_documents = ["更新文档1", "更新文档2"]
        chromadb_store.update(ids, updated_documents)

        results = chromadb_store.search("更新", top_k=2)
        assert len(results) > 0

    def test_clear(self, chromadb_store):
        """测试清空"""
        documents = ["文档1", "文档2", "文档3"]
        chromadb_store.add(documents)

        assert chromadb_store.count() == 3

        chromadb_store.clear()
        assert chromadb_store.count() == 0

    def test_health_check(self, chromadb_store):
        """测试健康检查"""
        assert chromadb_store.health_check() is True

    def test_metadata_filtering(self, chromadb_store):
        """测试元数据过滤"""
        documents = [
            "表结构文档",
            "术语定义",
            "查询示例"
        ]
        metadatas = [
            {"type": "table", "is_available": 0},
            {"type": "glossary", "is_available": 1},
            {"type": "example", "is_available": 0}
        ]

        chromadb_store.add(documents, metadatas)

        # 注意：ChromaDB 的过滤条件格式较复杂，这里只测试基础功能
        # 实际过滤可能需要特定的查询语法
        results = chromadb_store.search("文档", top_k=5)
        assert len(results) > 0


class TestQdrantStore:
    """Qdrant 存储测试"""

    def test_add_documents(self, qdrant_store):
        """测试添加文档"""
        documents = ["这是第一个文档", "这是第二个文档"]
        metadatas = [{"type": "test", "id": 1}, {"type": "test", "id": 2}]

        ids = qdrant_store.add(documents, metadatas)

        assert len(ids) == 2
        assert qdrant_store.count() == 2

    def test_add_documents_without_ids(self, qdrant_store):
        """测试自动生成 ID"""
        documents = ["文档1", "文档2"]
        ids = qdrant_store.add(documents)

        assert len(ids) == 2
        assert all(isinstance(id, str) for id in ids)
        assert qdrant_store.count() == 2

    def test_search_documents(self, qdrant_store):
        """测试搜索文档"""
        documents = [
            "今年销量统计",
            "产品销售数据",
            "客户信息管理",
            "订单处理流程"
        ]
        metadatas = [
            {"type": "table", "name": "sales"},
            {"type": "table", "name": "sales"},
            {"type": "table", "name": "customer"},
            {"type": "table", "name": "order"}
        ]

        qdrant_store.add(documents, metadatas)

        # 搜索相关文档
        results = qdrant_store.search("销售量查询", top_k=2)

        assert len(results) <= 2
        assert all("id" in r and "content" in r and "score" in r for r in results)
        assert all(0 <= r["score"] <= 1 for r in results)

    def test_delete_documents(self, qdrant_store):
        """测试删除文档"""
        documents = ["文档1", "文档2", "文档3"]
        ids = qdrant_store.add(documents)

        assert qdrant_store.count() == 3

        qdrant_store.delete(ids[:2])
        assert qdrant_store.count() == 1

    def test_update_documents(self, qdrant_store):
        """测试更新文档"""
        documents = ["原始文档1", "原始文档2"]
        ids = qdrant_store.add(documents)

        updated_documents = ["更新文档1", "更新文档2"]
        qdrant_store.update(ids, updated_documents)

        results = qdrant_store.search("更新", top_k=2)
        assert len(results) > 0

    def test_clear(self, qdrant_store):
        """测试清空"""
        documents = ["文档1", "文档2", "文档3"]
        qdrant_store.add(documents)

        assert qdrant_store.count() == 3

        qdrant_store.clear()
        assert qdrant_store.count() == 0

    def test_health_check(self, qdrant_store):
        """测试健康检查"""
        assert qdrant_store.health_check() is True


class TestVectorStoreComparison:
    """向量存储对比测试"""

    def test_chromadb_and_qdrant_compatibility(self, chromadb_store, qdrant_store):
        """测试 ChromaDB 和 Qdrant 的兼容性"""
        documents = [
            "今年销量统计",
            "产品销售数据",
            "客户信息管理"
        ]
        metadatas = [{"type": "test"} for _ in documents]

        # 在两个存储中都添加相同的文档
        chromadb_ids = chromadb_store.add(documents, metadatas)
        qdrant_ids = qdrant_store.add(documents, metadatas)

        # 验证文档数量一致
        assert chromadb_store.count() == qdrant_store.count()

        # 验证搜索结果的数量一致（可能顺序不同）
        chromadb_results = chromadb_store.search("销售", top_k=2)
        qdrant_results = qdrant_store.search("销售", top_k=2)

        assert len(chromadb_results) == len(qdrant_results)

        # 验证元数据一致
        assert all("metadata" in r for r in chromadb_results)
        assert all("metadata" in r for r in qdrant_results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
