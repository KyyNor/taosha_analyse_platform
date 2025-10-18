"""
元数据服务单元测试

测试元数据服务、术语表服务、提示词模板服务等核心功能
"""

import pytest
import json
from sqlalchemy.orm import Session

from services.metadata_service.metadata_service import (
    MetadataService, GlossaryService, PromptTemplateService,
    RelationFieldConfigService, DataThemeService
)


class TestMetadataService:
    """元数据表管理测试"""

    @pytest.fixture
    def metadata_service(self, db_session):
        """创建元数据服务实例"""
        return MetadataService(db_session)

    def test_add_table(self, metadata_service):
        """测试添加表元数据"""
        result = metadata_service.add_table("users", "用户表", 0)

        assert result is not None
        assert result["name"] == "users"
        assert result["comment"] == "用户表"
        assert result["is_available"] == 0
        assert "id" in result
        assert "created_at" in result

    def test_get_tables(self, metadata_service):
        """测试获取所有表"""
        # 添加测试数据
        metadata_service.add_table("table1", "表1", 0)
        metadata_service.add_table("table2", "表2", 0)

        tables = metadata_service.get_tables()

        assert len(tables) >= 2
        table_names = [t["name"] for t in tables]
        assert "table1" in table_names
        assert "table2" in table_names

    def test_get_table_info(self, metadata_service):
        """测试获取指定表信息"""
        metadata_service.add_table("test_table", "测试表", 0)

        table_info = metadata_service.get_table_info("test_table")

        assert table_info is not None
        assert table_info["name"] == "test_table"
        assert table_info["comment"] == "测试表"

    def test_get_table_info_not_found(self, metadata_service):
        """测试获取不存在的表"""
        result = metadata_service.get_table_info("non_existent_table")

        assert result is None

    def test_update_table(self, metadata_service):
        """测试更新表元数据"""
        # 添加表
        table = metadata_service.add_table("test_table", "原始名称", 0)
        table_id = table["id"]

        # 更新表
        success = metadata_service.update_table_by_id(table_id, "更新后的名称", 1)

        assert success is True

        # 验证更新
        updated_table = metadata_service.get_table_info("test_table")
        assert updated_table["comment"] == "更新后的名称"
        assert updated_table["is_available"] == 1

    def test_delete_table(self, metadata_service):
        """测试删除表元数据"""
        # 添加表
        table = metadata_service.add_table("to_delete", "待删除表", 0)
        table_id = table["id"]

        # 删除表
        success = metadata_service.delete_table_by_id(table_id)

        assert success is True

        # 验证删除
        result = metadata_service.get_table_info("to_delete")
        assert result is None

    def test_get_available_tables(self, metadata_service):
        """测试获取可用表"""
        metadata_service.add_table("available1", "可用表1", 0)
        metadata_service.add_table("available2", "可用表2", 0)
        metadata_service.add_table("unavailable", "不可用表", 1)

        available_tables = metadata_service.get_available_tables()

        available_names = [t["name"] for t in available_tables]
        assert "available1" in available_names
        assert "available2" in available_names
        assert "unavailable" not in available_names

    def test_add_column(self, metadata_service):
        """测试添加列元数据"""
        # 先添加表
        table = metadata_service.add_table("users", "用户表", 0)
        table_id = table["id"]

        # 添加列
        column = metadata_service.add_column_by_id(
            table_id, "user_id", "INTEGER", "用户ID", 0, "标识字段"
        )

        assert column is not None
        assert column["name"] == "user_id"
        assert column["type"] == "INTEGER"
        assert column["comment"] == "用户ID"
        assert column["business_type"] == "标识字段"

    def test_add_multiple_columns(self, metadata_service):
        """测试添加多个列"""
        table = metadata_service.add_table("users", "用户表", 0)
        table_id = table["id"]

        # 添加多个列
        metadata_service.add_column_by_id(table_id, "id", "INTEGER")
        metadata_service.add_column_by_id(table_id, "name", "VARCHAR")
        metadata_service.add_column_by_id(table_id, "email", "VARCHAR")

        # 验证表的列信息
        table_info = metadata_service.get_table_info("users")
        assert len(table_info["columns"]) == 3

    def test_update_column(self, metadata_service):
        """测试更新列元数据"""
        table = metadata_service.add_table("users", "用户表", 0)
        table_id = table["id"]

        column = metadata_service.add_column_by_id(table_id, "age", "INTEGER")
        column_id = column["id"]

        # 更新列
        success = metadata_service.update_column_by_id(
            column_id, column_type="VARCHAR", comment="用户年龄"
        )

        assert success is True

    def test_delete_column(self, metadata_service):
        """测试删除列元数据"""
        table = metadata_service.add_table("users", "用户表", 0)
        table_id = table["id"]

        column = metadata_service.add_column_by_id(table_id, "temp_col", "VARCHAR")
        column_id = column["id"]

        # 删除列
        success = metadata_service.delete_column_by_id(column_id)

        assert success is True

        # 验证删除
        table_info = metadata_service.get_table_info("users")
        col_names = [c["name"] for c in table_info["columns"]]
        assert "temp_col" not in col_names


class TestGlossaryService:
    """术语表服务测试"""

    @pytest.fixture
    def glossary_service(self, db_session):
        """创建术语表服务实例"""
        return GlossaryService(db_session)

    def test_add_concept_term(self, glossary_service):
        """测试添加概念解释术语"""
        content = {
            "explanation": "用户是指使用系统的人员",
            "examples": ["张三", "李四"]
        }

        success = glossary_service.add_term(
            "用户", "concept", content, "admin"
        )

        assert success is True

        # 验证术语
        terms = glossary_service.get_terms()
        term_names = [t["name"] for t in terms]
        assert "用户" in term_names

    def test_add_sql_qa_term(self, glossary_service):
        """测试添加SQL问答术语"""
        content = {
            "question": "如何查询所有用户？",
            "sql": "SELECT * FROM users;"
        }

        success = glossary_service.add_term(
            "查询所有用户", "sql_qa", content, "admin"
        )

        assert success is True

    def test_add_dict_mapping_term(self, glossary_service):
        """测试添加字典转换术语"""
        content = {
            "mappings": {
                "男": "M",
                "女": "F"
            }
        }

        success = glossary_service.add_term(
            "性别转换", "dict_mapping", content, "admin"
        )

        assert success is True

    def test_get_terms(self, glossary_service):
        """测试获取所有术语"""
        glossary_service.add_term("术语1", "concept", {"text": "定义1"}, "admin")
        glossary_service.add_term("术语2", "sql_qa", {"question": "问题"}, "admin")

        terms = glossary_service.get_terms()

        assert len(terms) >= 2

    def test_find_term(self, glossary_service):
        """测试查找术语"""
        glossary_service.add_term("用户", "concept", {"explanation": "定义"}, "admin")

        term = glossary_service.find_term("用户")

        assert term is not None
        assert term["name"] == "用户"
        assert term["type"] == "concept"

    def test_find_term_not_found(self, glossary_service):
        """测试查找不存在的术语"""
        result = glossary_service.find_term("不存在的术语")

        assert result is None

    def test_get_terms_by_type(self, glossary_service):
        """测试按类型获取术语"""
        glossary_service.add_term("概念1", "concept", {"text": "定义"}, "admin")
        glossary_service.add_term("概念2", "concept", {"text": "定义"}, "admin")
        glossary_service.add_term("问答1", "sql_qa", {"question": "问题"}, "admin")

        concept_terms = glossary_service.get_terms_by_type("concept")

        assert len(concept_terms) == 2
        assert all(t["type"] == "concept" for t in concept_terms)

    def test_update_term(self, glossary_service):
        """测试更新术语"""
        glossary_service.add_term("原名称", "concept", {"text": "定义"}, "admin")

        # 获取术语ID
        term = glossary_service.find_term("原名称")
        term_id = term["id"]

        # 更新术语
        success = glossary_service.update_term(
            term_id, name="新名称", content={"text": "新定义"}
        )

        assert success is True

    def test_delete_term(self, glossary_service):
        """测试删除术语"""
        glossary_service.add_term("待删除", "concept", {"text": "定义"}, "admin")

        term = glossary_service.find_term("待删除")
        term_id = term["id"]

        # 删除术语
        success = glossary_service.delete_term(term_id)

        assert success is True

        # 验证删除
        result = glossary_service.find_term("待删除")
        assert result is None


class TestPromptTemplateService:
    """提示词模板服务测试"""

    @pytest.fixture
    def prompt_service(self, db_session):
        """创建提示词模板服务实例"""
        return PromptTemplateService(db_session)

    def test_add_template(self, prompt_service):
        """测试添加提示词模板"""
        fields = ["table_name", "column_list"]
        template = "为数据表 {table_name}（包含字段：{column_list}）生成查询SQL"

        success = prompt_service.add_template("查询模板", fields, template)

        assert success is True

    def test_add_template_invalid_placeholders(self, prompt_service):
        """测试添加模板时占位符不匹配"""
        fields = ["name", "email"]
        # 模板中使用了不存在的占位符 {phone}
        template = "用户 {name} 的邮箱是 {phone}"

        success = prompt_service.add_template("无效模板", fields, template)

        # 应该失败，因为占位符不匹配
        assert success is False

    def test_get_templates(self, prompt_service):
        """测试获取所有模板"""
        prompt_service.add_template(
            "模板1", ["field1"], "内容 {field1}"
        )
        prompt_service.add_template(
            "模板2", ["field1"], "内容 {field1}"
        )

        templates = prompt_service.get_templates()

        assert len(templates) >= 2

    def test_get_template_by_name(self, prompt_service):
        """测试按名称获取模板"""
        prompt_service.add_template(
            "测试模板", ["field1"], "内容 {field1}"
        )

        template = prompt_service.get_template_by_name("测试模板")

        assert template is not None
        assert template["name"] == "测试模板"

    def test_update_template(self, prompt_service):
        """测试更新提示词模板"""
        prompt_service.add_template(
            "原模板", ["field1"], "原内容 {field1}"
        )

        template = prompt_service.get_template_by_name("原模板")
        template_id = template["id"]

        # 更新模板名称
        success = prompt_service.update_template(
            template_id, name="新模板"
        )

        assert success is True

    def test_delete_template(self, prompt_service):
        """测试删除提示词模板"""
        prompt_service.add_template(
            "待删除", ["field1"], "内容 {field1}"
        )

        template = prompt_service.get_template_by_name("待删除")
        template_id = template["id"]

        # 删除模板
        success = prompt_service.delete_template(template_id)

        assert success is True

    def test_validate_template(self, prompt_service):
        """测试模板验证"""
        fields = ["name", "age", "email"]
        template = "用户 {name}，{age} 岁，邮箱 {email}"

        errors = prompt_service.validate_template(fields, template)

        # 应该没有错误
        assert len(errors) == 0

    def test_validate_template_missing_fields(self, prompt_service):
        """测试模板中缺少字段验证"""
        fields = ["name", "age"]
        template = "用户 {name}，{age} 岁，邮箱 {email}"

        errors = prompt_service.validate_template(fields, template)

        # 应该有错误：缺少 email 字段
        assert len(errors) > 0


class TestRelationFieldConfigService:
    """关联字段配置服务测试"""

    @pytest.fixture
    def relation_service(self, db_session):
        """创建关联字段配置服务实例"""
        return RelationFieldConfigService(db_session)

    def test_add_relation_config(self, relation_service):
        """测试添加关联配置"""
        result = relation_service.add_relation_config(
            "用户", "部门关联", "用户与部门的关联关系"
        )

        assert result is not None
        assert result["relation_family"] == "用户"
        assert result["relation_subfamily"] == "部门关联"

    def test_get_all_configs(self, relation_service):
        """测试获取所有关联配置"""
        relation_service.add_relation_config("家族1", "子家族1", "描述1")
        relation_service.add_relation_config("家族2", "子家族2", "描述2")

        configs = relation_service.get_all_relation_configs()

        assert len(configs) >= 2

    def test_update_relation_config(self, relation_service):
        """测试更新关联配置"""
        config = relation_service.add_relation_config("原家族", "子家族", "描述")
        config_id = config["id"]

        success = relation_service.update_relation_config(
            config_id, family="新家族"
        )

        assert success is True

    def test_delete_relation_config(self, relation_service):
        """测试删除关联配置"""
        config = relation_service.add_relation_config("家族", "子家族", "描述")
        config_id = config["id"]

        success = relation_service.delete_relation_config(config_id)

        assert success is True


class TestDataThemeService:
    """数据主题服务测试"""

    @pytest.fixture
    def theme_service(self, db_session):
        """创建数据主题服务实例"""
        return DataThemeService(db_session)

    def test_add_theme(self, theme_service):
        """测试添加数据主题"""
        result = theme_service.add_theme(
            "销售主题", "销售相关数据", "normal", "销售部"
        )

        assert result is not None
        assert result["theme_name"] == "销售主题"
        assert result["theme_type"] == "normal"

    def test_get_all_themes(self, theme_service):
        """测试获取所有主题"""
        theme_service.add_theme("主题1", "描述1", "normal")
        theme_service.add_theme("主题2", "描述2", "normal")

        themes = theme_service.get_all_themes()

        assert len(themes) >= 2

    def test_get_theme_by_name(self, theme_service):
        """测试按名称获取主题"""
        theme_service.add_theme("测试主题", "测试描述", "normal")

        theme = theme_service.get_theme_by_name("测试主题")

        assert theme is not None
        assert theme["theme_name"] == "测试主题"

    def test_update_theme(self, theme_service):
        """测试更新主题"""
        theme = theme_service.add_theme("原主题", "原描述", "normal")
        theme_id = theme["id"]

        success = theme_service.update_theme(
            theme_id, theme_name="新主题", theme_description="新描述"
        )

        assert success is True

    def test_delete_theme(self, theme_service):
        """测试删除主题"""
        theme = theme_service.add_theme("待删除", "描述", "normal")
        theme_id = theme["id"]

        success = theme_service.delete_theme(theme_id)

        assert success is True

    def test_add_public_theme(self, theme_service):
        """测试添加通用主题"""
        result = theme_service.add_theme("通用主题", "描述", "public")

        assert result is not None
        assert result["theme_type"] == "public"

    def test_public_theme_uniqueness(self, theme_service):
        """测试通用主题唯一性约束"""
        # 添加第一个通用主题
        theme_service.add_theme("通用1", "描述", "public")

        # 尝试添加第二个通用主题，应该失败
        result = theme_service.add_theme("通用2", "描述", "public")

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
