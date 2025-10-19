"""
Repository层数据持久化单元测试

测试BaseRepository基类和具体Repository实现的功能
"""

import pytest
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import patch

from repositories.base_repository import BaseRepository
from repositories.glossary_repository import GlossaryTermRepository, PromptTemplateRepository
from repositories.metadata_repository import MetadataTableRepository, MetadataColumnRepository
from repositories.relation_repository import RelationFieldConfigRepository

from models.glossary_models import GlossaryTerm, PromptTemplate
from models.metadata_models import MetadataTable, MetadataColumn
from models.relation_models import RelationFieldConfig


class MockModel:
    """用于测试的Mock模型类"""

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', None)
        self.name = kwargs.get('name', None)
        self.type = kwargs.get('type', None)
        self.content = kwargs.get('content', None)

        # 模拟SQLAlchemy属性
        self.__table__ = type('Table', (), {'name': 'mock_table'})()

    def __repr__(self):
        return f"<MockModel(id={self.id}, name='{self.name}')>"


class TestBaseRepository:
    """BaseRepository基类测试"""

    def test_base_repository_init(self, db_session):
        """测试Repository初始化"""
        repo = BaseRepository(MockModel, db_session)
        assert repo.model_class == MockModel
        assert repo.db == db_session

    def test_create_record(self, db_session):
        """测试创建记录"""
        repo = BaseRepository(MockModel, db_session)

        # 创建记录
        instance = repo.create(name="测试记录", type="test", content="测试内容")

        assert instance is not None
        assert instance.name == "测试记录"
        assert instance.type == "test"
        assert instance.content == "测试内容"
        assert instance.id is not None  # 应该有自动生成的ID

    def test_create_record_with_partial_data(self, db_session):
        """测试创建部分数据的记录"""
        repo = BaseRepository(MockModel, db_session)

        instance = repo.create(name="部分记录")

        assert instance.name == "部分记录"
        assert instance.type is None  # 未提供的字段应该为None

    def test_get_by_id_success(self, db_session):
        """测试根据ID获取记录"""
        repo = BaseRepository(MockModel, db_session)

        # 创建记录
        created = repo.create(name="查找测试", type="test")

        # 根据ID查找
        found = repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.name == "查找测试"

    def test_get_by_id_not_found(self, db_session):
        """测试查找不存在的记录"""
        repo = BaseRepository(MockModel, db_session)

        found = repo.get_by_id(999999)  # 不存在的ID

        assert found is None

    def test_get_all_records(self, db_session):
        """测试获取所有记录"""
        repo = BaseRepository(MockModel, db_session)

        # 创建多条记录
        repo.create(name="记录1", type="A")
        repo.create(name="记录2", type="B")
        repo.create(name="记录3", type="A")

        # 获取所有记录
        all_records = repo.get_all()

        assert len(all_records) >= 3
        names = [r.name for r in all_records]
        assert "记录1" in names
        assert "记录2" in names
        assert "记录3" in names

    def test_get_all_with_filters(self, db_session):
        """测试带过滤条件获取记录"""
        repo = BaseRepository(MockModel, db_session)

        # 创建不同类型的记录
        repo.create(name="记录1", type="A")
        repo.create(name="记录2", type="B")
        repo.create(name="记录3", type="A")

        # 按类型过滤
        type_a_records = repo.get_all(type="A")
        type_b_records = repo.get_all(type="B")

        assert len(type_a_records) == 2
        assert len(type_b_records) == 1
        assert all(r.type == "A" for r in type_a_records)
        assert all(r.type == "B" for r in type_b_records)

    def test_update_record(self, db_session):
        """测试更新记录"""
        repo = BaseRepository(MockModel, db_session)

        # 创建记录
        instance = repo.create(name="原始名称", type="A")

        # 更新记录
        success = repo.update(instance.id, name="更新名称", type="B")

        assert success is True

        # 验证更新
        updated = repo.get_by_id(instance.id)
        assert updated.name == "更新名称"
        assert updated.type == "B"

    def test_update_nonexistent_record(self, db_session):
        """测试更新不存在的记录"""
        repo = BaseRepository(MockModel, db_session)

        success = repo.update(999999, name="新名称")  # 不存在的ID

        assert success is False

    def test_delete_record(self, db_session):
        """测试删除记录"""
        repo = BaseRepository(MockModel, db_session)

        # 创建记录
        instance = repo.create(name="待删除", type="test")

        # 删除记录
        success = repo.delete(instance.id)

        assert success is True

        # 验证删除
        deleted = repo.get_by_id(instance.id)
        assert deleted is None

    def test_delete_nonexistent_record(self, db_session):
        """测试删除不存在的记录"""
        repo = BaseRepository(MockModel, db_session)

        success = repo.delete(999999)  # 不存在的ID

        assert success is False

    def test_create_database_error(self, db_session):
        """测试创建记录时的数据库错误"""
        repo = BaseRepository(MockModel, db_session)

        # 模拟数据库错误
        with patch.object(db_session, 'add', side_effect=SQLAlchemyError("数据库错误")):
            with pytest.raises(SQLAlchemyError):
                repo.create(name="错误测试")


class TestGlossaryTermRepository:
    """GlossaryTermRepository测试"""

    def test_glossary_repository_init(self, db_session):
        """测试术语表Repository初始化"""
        repo = GlossaryTermRepository(db_session)
        assert repo.model_class == GlossaryTerm
        assert repo.db == db_session

    def test_create_glossary_term(self, db_session):
        """测试创建术语"""
        repo = GlossaryTermRepository(db_session)

        term = repo.create(
            name="用户",
            type="concept",
            content='{"explanation": "使用系统的人员"}',
            creator="admin"
        )

        assert term.name == "用户"
        assert term.type == "concept"
        assert term.content == '{"explanation": "使用系统的人员"}'
        assert term.creator == "admin"

    def test_get_by_name(self, db_session):
        """测试根据名称获取术语"""
        repo = GlossaryTermRepository(db_session)

        # 创建术语
        repo.create(name="数据库", type="concept", content='{"text": "定义"}')

        # 查找术语
        term = repo.get_by_name("数据库")

        assert term is not None
        assert term.name == "数据库"

    def test_get_by_name_not_found(self, db_session):
        """测试查找不存在的术语"""
        repo = GlossaryTermRepository(db_session)

        term = repo.get_by_name("不存在的术语")

        assert term is None

    def test_get_by_type(self, db_session):
        """测试根据类型获取术语"""
        repo = GlossaryTermRepository(db_session)

        # 创建不同类型的术语
        repo.create(name="概念1", type="concept", content='{"text": "定义1"}')
        repo.create(name="问答1", type="sql_qa", content='{"question": "问题"}')
        repo.create(name="概念2", type="concept", content='{"text": "定义2"}')

        # 获取概念类术语
        concept_terms = repo.get_by_type("concept")

        assert len(concept_terms) == 2
        assert all(t.type == "concept" for t in concept_terms)

    def test_get_by_creator(self, db_session):
        """测试根据创建者获取术语"""
        repo = GlossaryTermRepository(db_session)

        # 创建不同创建者的术语
        repo.create(name="术语1", type="concept", content='{"text": "定义1"}', creator="admin")
        repo.create(name="术语2", type="concept", content='{"text": "定义2"}', creator="user1")
        repo.create(name="术语3", type="concept", content='{"text": "定义3"}', creator="admin")

        # 获取admin创建的术语
        admin_terms = repo.get_by_creator("admin")

        assert len(admin_terms) == 2
        assert all(t.creator == "admin" for t in admin_terms)

    def test_search_terms(self, db_session):
        """测试搜索术语"""
        repo = GlossaryTermRepository(db_session)

        # 创建术语
        repo.create(name="数据库", type="concept", content='{"explanation": "存储数据的系统"}')
        repo.create(name="用户", type="concept", content='{"explanation": "使用系统的人员"}')
        repo.create(name="查询", type="sql_qa", content='{"question": "如何查询数据库"}')

        # 搜索包含"数据"的术语
        results = repo.search_terms("数据")

        assert len(results) >= 1  # 至少找到数据库术语

    def test_find_similar_terms(self, db_session):
        """测试查找相似术语"""
        repo = GlossaryTermRepository(db_session)

        # 创建相关术语
        repo.create(name="用户管理", type="concept", content='{"text": "定义1"}')
        repo.create(name="用户权限", type="concept", content='{"text": "定义2"}')
        repo.create(name="用户设置", type="concept", content='{"text": "定义3"}')
        repo.create(name="数据库管理", type="concept", content='{"text": "定义4"}')

        # 查找包含"用户"的术语
        similar_terms = repo.find_similar_terms("用户", limit=3)

        assert len(similar_terms) >= 3
        assert all("用户" in term.name for term in similar_terms)

    def test_search_terms_limit(self, db_session):
        """测试搜索术语限制数量"""
        repo = GlossaryTermRepository(db_session)

        # 创建多个匹配的术语
        for i in range(5):
            repo.create(name=f"测试{i}", type="concept", content='{"text": "定义"}')

        # 搜索并限制结果
        results = repo.find_similar_terms("测试", limit=2)

        assert len(results) == 2


class TestMetadataTableRepository:
    """MetadataTableRepository测试"""

    def test_metadata_table_repository_init(self, db_session):
        """测试元数据表Repository初始化"""
        repo = MetadataTableRepository(db_session)
        assert repo.model_class == MetadataTable
        assert repo.db == db_session

    def test_create_metadata_table(self, db_session):
        """测试创建元数据表"""
        repo = MetadataTableRepository(db_session)

        table = repo.create(
            name="users",
            comment="用户表",
            is_available=0
        )

        assert table.name == "users"
        assert table.comment == "用户表"
        assert table.is_available == 0

    def test_get_by_name(self, db_session):
        """测试根据名称获取元数据表"""
        repo = MetadataTableRepository(db_session)

        # 创建表
        repo.create(name="products", comment="产品表")

        # 查找表
        table = repo.get_by_name("products")

        assert table is not None
        assert table.name == "products"

    def test_get_available_tables(self, db_session):
        """测试获取可用表"""
        repo = MetadataTableRepository(db_session)

        # 创建可用和不可用的表
        repo.create(name="available1", comment="可用表1", is_available=0)
        repo.create(name="available2", comment="可用表2", is_available=0)
        repo.create(name="unavailable", comment="不可用表", is_available=1)

        # 获取可用表
        available_tables = repo.get_available_tables()

        assert len(available_tables) == 2
        assert all(t.is_available == 0 for t in available_tables)

    def test_get_table_with_columns(self, db_session):
        """测试获取表及其列信息"""
        table_repo = MetadataTableRepository(db_session)
        column_repo = MetadataColumnRepository(db_session)

        # 创建表
        table = table_repo.create(name="test_table", comment="测试表")

        # 创建列
        column_repo.create(
            table_id=table.id,
            name="id",
            type="INTEGER",
            comment="主键"
        )

        # 获取表及其列
        table_with_columns = table_repo.get_with_columns()

        # 查找我们创建的表
        our_table = next((t for t in table_with_columns if t.name == "test_table"), None)
        assert our_table is not None
        assert hasattr(our_table, 'columns')


class TestRelationFieldConfigRepository:
    """RelationFieldConfigRepository测试"""

    def test_relation_config_repository_init(self, db_session):
        """测试关联配置Repository初始化"""
        repo = RelationFieldConfigRepository(db_session)
        assert repo.model_class == RelationFieldConfig
        assert repo.db == db_session

    def test_create_relation_config(self, db_session):
        """测试创建关联配置"""
        repo = RelationFieldConfigRepository(db_session)

        config = repo.create(
            relation_family="用户",
            relation_subfamily="部门关联",
            relation_desc="用户与部门的关联关系"
        )

        assert config.relation_family == "用户"
        assert config.relation_subfamily == "部门关联"
        assert config.relation_desc == "用户与部门的关联关系"

    def test_get_relation_config(self, db_session):
        """测试获取关联配置"""
        repo = RelationFieldConfigRepository(db_session)

        # 创建配置
        created = repo.create(
            relation_family="测试",
            relation_subfamily="子测试",
            relation_desc="测试描述"
        )

        # 获取配置
        config = repo.get_by_id(created.id)

        assert config is not None
        assert config.relation_family == "测试"

    def test_find_relations_by_family(self, db_session):
        """测试根据家族查找关联配置"""
        repo = RelationFieldConfigRepository(db_session)

        # 创建不同家族的配置
        repo.create(relation_family="家族1", relation_subfamily="子家族1")
        repo.create(relation_family="家族1", relation_subfamily="子家族2")
        repo.create(relation_family="家族2", relation_subfamily="子家族3")

        # 查找家族1的配置
        family1_configs = repo.get_by_family("家族1")

        assert len(family1_configs) == 2
        assert all(c.relation_family == "家族1" for c in family1_configs)


class TestPromptTemplateRepository:
    """PromptTemplateRepository测试"""

    def test_prompt_template_repository_init(self, db_session):
        """测试提示词模板Repository初始化"""
        repo = PromptTemplateRepository(db_session)
        assert repo.model_class == PromptTemplate
        assert repo.db == db_session

    def test_create_prompt_template(self, db_session):
        """测试创建提示词模板"""
        repo = PromptTemplateRepository(db_session)

        template = repo.create(
            name="查询模板",
            fields='["table_name", "condition"]',
            template="为表 {table_name} 生成查询，条件：{condition}"
        )

        assert template.name == "查询模板"
        assert template.fields == '["table_name", "condition"]'
        assert "{table_name}" in template.template

    def test_get_template_by_name(self, db_session):
        """测试根据名称获取模板"""
        repo = PromptTemplateRepository(db_session)

        # 创建模板
        repo.create(
            name="SQL生成模板",
            fields='["table"]',
            template="为表 {table} 生成SQL"
        )

        # 查找模板
        template = repo.get_by_name("SQL生成模板")

        assert template is not None
        assert template.name == "SQL生成模板"

    def test_template_name_uniqueness(self, db_session):
        """测试模板名称唯一性"""
        repo = PromptTemplateRepository(db_session)

        # 创建第一个模板
        repo.create(
            name="唯一模板",
            fields='["field"]',
            template="内容 {field}"
        )

        # 尝试创建同名模板（应该失败）
        with pytest.raises(Exception):  # SQLAlchemy会抛出IntegrityError
            repo.create(
                name="唯一模板",
                fields='["field2"]',
                template="内容 {field2}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
