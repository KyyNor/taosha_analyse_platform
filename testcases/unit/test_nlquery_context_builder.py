"""
NLQuery Context Builder 测试
"""

import pytest
import sys
from pathlib import Path

# 添加 backend 目录到路径
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from services.vector_store import NLQueryContextBuilder, VectorStoreFactory
from utils.logger import logger


class MockEmbeddingFunction:
    """模拟 Embedding 函数"""

    def embed_documents(self, documents: list) -> list:
        """返回模拟的 embedding"""
        import random
        return [[random.random() for _ in range(5)] for _ in documents]

    def embed_query(self, query: str) -> list:
        """返回模拟的 query embedding"""
        import random
        return [random.random() for _ in range(5)]

    def name(self) -> str:
        """返回 embedding 函数名称"""
        return "mock_embedding_function"


class MockMetadataService:
    """模拟元数据服务"""

    def get_available_tables(self):
        """返回可用表列表"""
        return [
            {
                "id": "1",
                "name": "order_table",
                "comment": "订单表",
                "columns": [
                    {
                        "name": "order_id",
                        "type": "int",
                        "business_type": "int",
                        "comment": "订单ID",
                        "relation_id": "order_id",
                        "is_available": 0
                    },
                    {
                        "name": "cust_no",
                        "type": "varchar",
                        "business_type": "varchar",
                        "comment": "客户编号",
                        "relation_id": "cust_id",
                        "is_available": 0
                    },
                    {
                        "name": "amount",
                        "type": "decimal",
                        "business_type": "decimal",
                        "comment": "订单金额",
                        "relation_id": "",
                        "is_available": 0
                    }
                ]
            },
            {
                "id": "2",
                "name": "customer_table",
                "comment": "客户表",
                "columns": [
                    {
                        "name": "cust_no",
                        "type": "varchar",
                        "business_type": "varchar",
                        "comment": "客户编号",
                        "relation_id": "cust_id",
                        "is_available": 0
                    },
                    {
                        "name": "cust_name",
                        "type": "varchar",
                        "business_type": "varchar",
                        "comment": "客户名称",
                        "relation_id": "",
                        "is_available": 0
                    }
                ]
            }
        ]

    def get_table_by_name(self, table_name: str):
        """获取指定表"""
        tables = self.get_available_tables()
        for table in tables:
            if table.get("name") == table_name:
                return table
        return None


class MockGlossaryService:
    """模拟术语服务"""

    def get_terms(self):
        """返回术语列表"""
        return [
            {
                "id": "1",
                "name": "销量",
                "type": "concept",
                "content": {"content": "产品的销售数量"}
            }
        ]


class MockRelationConfigService:
    """模拟关联配置服务"""

    def get_all_relation_configs(self):
        """返回所有关联配置"""
        return [
            {
                "relation_id": "cust_id",
                "relation_family": "customer",
                "relation_subfamily": "id",
                "relation_desc": "客户编号"
            }
        ]


@pytest.fixture
def vector_store():
    """创建向量存储实例"""
    embedding_func = MockEmbeddingFunction()
    config = {"collection_name": "test_context", "embedding_dimension": 5}
    store = VectorStoreFactory.create("qdrant", embedding_func, config)

    # 预加载一些测试数据
    documents = [
        "表名：order_table\n描述：订单表\n字段信息：\n  - order_id：订单ID\n  - cust_no：客户编号\n  - amount：订单金额",
        "表名：customer_table\n描述：客户表\n字段信息：\n  - cust_no：客户编号\n  - cust_name：客户名称",
        "术语：销量 - 产品的销售数量",
        "术语：客户编号 - 唯一标识客户的编号"
    ]
    metadatas = [
        {"type": "table", "table_name": "order_table"},
        {"type": "table", "table_name": "customer_table"},
        {"type": "glossary", "term_name": "销量"},
        {"type": "glossary", "term_name": "客户编号"}
    ]

    store.add(documents, metadatas)
    yield store
    store.clear()


@pytest.fixture
def context_builder(vector_store):
    """创建上下文构建器"""
    embedding_func = MockEmbeddingFunction()
    metadata_service = MockMetadataService()
    glossary_service = MockGlossaryService()
    relation_config_service = MockRelationConfigService()

    builder = NLQueryContextBuilder(
        vector_store=vector_store,
        embedding_func=embedding_func,
        metadata_service=metadata_service,
        glossary_service=glossary_service,
        relation_config_service=relation_config_service
    )

    return builder


class TestNLQueryContextBuilder:
    """NLQuery Context Builder 测试"""

    def test_semantic_search(self, context_builder):
        """测试纯向量检索"""
        user_input = "订单信息查询"
        context = context_builder.retrieve_by_semantic_search(user_input, top_k=2)

        assert context is not None
        assert isinstance(context, str)
        assert len(context) > 0
        logger.info(f"纯向量检索成功: {len(context)} 字符")

    def test_semantic_search_returns_formatted_context(self, context_builder):
        """测试纯向量检索返回格式化的上下文"""
        user_input = "销售数据"
        context = context_builder.retrieve_by_semantic_search(user_input)

        # 验证返回的是格式化的文本
        assert isinstance(context, str)
        assert len(context) > 0
        logger.info("上下文格式验证通过")

    def test_relation_id_search(self, context_builder):
        """测试关联ID优先检索"""
        context = context_builder.retrieve_by_relation_id(
            relation_id="cust_id",
            user_input="客户查询",
            top_k=2
        )

        assert context is not None
        assert isinstance(context, str)
        assert len(context) > 0
        logger.info("关联ID优先检索成功")

    def test_table_first_search(self, context_builder):
        """测试表优先检索"""
        context = context_builder.retrieve_by_table_first(
            table_names=["order_table"],
            user_input="订单金额",
            top_k=2
        )

        assert context is not None
        assert isinstance(context, str)
        assert "order_table" in context  # 应该包含表信息
        logger.info("表优先检索成功")

    def test_table_first_search_multiple_tables(self, context_builder):
        """测试表优先检索多张表"""
        context = context_builder.retrieve_by_table_first(
            table_names=["order_table", "customer_table"],
            user_input="客户订单",
            top_k=2
        )

        assert context is not None
        assert "order_table" in context
        assert "customer_table" in context
        logger.info("多表优先检索成功")

    def test_hybrid_search(self, context_builder):
        """测试混合检索"""
        context = context_builder.retrieve_hybrid(
            user_input="最近订单",
            relation_id="cust_id",
            table_names=["order_table"],
            top_k=2
        )

        assert context is not None
        assert isinstance(context, str)
        assert len(context) > 0
        logger.info("混合检索成功")

    def test_hybrid_search_without_relation_id(self, context_builder):
        """测试混合检索（不指定关联ID）"""
        context = context_builder.retrieve_hybrid(
            user_input="最近订单",
            table_names=["order_table"],
            top_k=2
        )

        assert context is not None
        assert isinstance(context, str)
        logger.info("混合检索（无关联ID）成功")

    def test_hybrid_search_without_tables(self, context_builder):
        """测试混合检索（不指定表）"""
        context = context_builder.retrieve_hybrid(
            user_input="最近订单",
            relation_id="cust_id",
            top_k=2
        )

        assert context is not None
        assert isinstance(context, str)
        logger.info("混合检索（无表）成功")

    def test_get_fields_by_relation_id(self, context_builder):
        """测试根据关联ID获取字段"""
        fields = context_builder._get_fields_by_relation_id("cust_id")

        assert isinstance(fields, list)
        assert len(fields) > 0

        # 验证找到的字段
        table_names = {f["table_name"] for f in fields}
        assert "order_table" in table_names or "customer_table" in table_names
        logger.info(f"找到 {len(fields)} 个关联字段")

    def test_get_fields_by_relation_id_not_found(self, context_builder):
        """测试查找不存在的关联ID"""
        fields = context_builder._get_fields_by_relation_id("nonexistent_id")

        assert isinstance(fields, list)
        assert len(fields) == 0
        logger.info("不存在的关联ID返回空列表")

    def test_context_contains_useful_info(self, context_builder):
        """测试上下文包含有用的信息"""
        context = context_builder.retrieve_by_semantic_search("订单查询")

        # 上下文应该包含某些关键词
        assert len(context) > 0
        # 验证上下文中有结构化的信息
        assert "表" in context or "字段" in context or "术语" in context or "信息" in context
        logger.info("上下文包含有用信息验证通过")

    def test_large_top_k(self, context_builder):
        """测试大的 top_k 值"""
        context = context_builder.retrieve_by_semantic_search("查询", top_k=50)

        assert context is not None
        assert isinstance(context, str)
        logger.info("大 top_k 值检索成功")

    def test_small_top_k(self, context_builder):
        """测试小的 top_k 值"""
        context = context_builder.retrieve_by_semantic_search("查询", top_k=1)

        assert context is not None
        assert isinstance(context, str)
        logger.info("小 top_k 值检索成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
