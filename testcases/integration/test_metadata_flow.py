"""
元数据管理流程集成测试

测试完整的元数据管理工作流：
1. 元数据管理流程：添加表 → 配置字段 → 验证关联
2. 术语表流程：添加术语 → 查询术语 → 验证效果
"""

import pytest
import json
from sqlalchemy.orm import Session

from services.metadata_service.metadata_service import (
    MetadataService, GlossaryService, PromptTemplateService,
    RelationFieldConfigService
)


class TestMetadataManagementFlow:
    """元数据管理完整流程测试"""

    @pytest.fixture
    def services(self, db_session):
        """创建所需的服务实例"""
        return {
            "metadata": MetadataService(db_session),
            "glossary": GlossaryService(db_session),
            "relation": RelationFieldConfigService(db_session),
            "prompt": PromptTemplateService(db_session)
        }

    def test_complete_metadata_workflow(self, services):
        """
        测试完整的元数据管理工作流：
        1. 创建表
        2. 为表添加字段
        3. 创建字段关联配置
        4. 验证表和字段的关联
        """
        metadata_svc = services["metadata"]
        relation_svc = services["relation"]

        # 1. 创建表
        user_table = metadata_svc.add_table("users", "用户表", 0)
        assert user_table is not None
        user_table_id = user_table["id"]

        # 2. 添加字段关联配置
        dept_relation = relation_svc.add_relation_config(
            "用户", "部门关联", "用户与部门的多对一关系"
        )
        assert dept_relation is not None
        relation_id = dept_relation["id"]

        # 3. 为表添加字段
        id_col = metadata_svc.add_column_by_id(
            user_table_id, "id", "INTEGER", "用户ID", 0, "标识字段"
        )
        assert id_col is not None

        name_col = metadata_svc.add_column_by_id(
            user_table_id, "name", "VARCHAR", "用户名", 0, "基本字段"
        )
        assert name_col is not None

        dept_col = metadata_svc.add_column_by_id(
            user_table_id, "dept_id", "INTEGER", "部门ID", 0, "关联字段",
            relation_config_id=relation_id
        )
        assert dept_col is not None

        # 4. 验证表和字段的关联
        table_info = metadata_svc.get_table_info("users")
        assert len(table_info["columns"]) == 3

        # 验证字段属性
        dept_id_col = next((c for c in table_info["columns"] if c["name"] == "dept_id"), None)
        assert dept_id_col is not None
        assert dept_id_col["business_type"] == "关联字段"
        assert dept_id_col["relation_config_id"] == relation_id

    def test_metadata_ddl_generation(self, services):
        """
        测试根据元数据生成DDL语句
        """
        metadata_svc = services["metadata"]

        # 创建表和字段
        table = metadata_svc.add_table("products", "产品表", 0)
        table_id = table["id"]

        metadata_svc.add_column_by_id(table_id, "product_id", "INTEGER", "产品ID")
        metadata_svc.add_column_by_id(table_id, "product_name", "VARCHAR", "产品名称")
        metadata_svc.add_column_by_id(table_id, "price", "DECIMAL", "价格")

        # 生成DDL
        ddl_statements = metadata_svc.get_ddl_statements()

        assert len(ddl_statements) > 0
        # 验证DDL包含表名和字段
        ddl_text = "\n".join(ddl_statements)
        assert "products" in ddl_text
        assert "product_id" in ddl_text
        assert "product_name" in ddl_text

    def test_available_tables_filtering(self, services):
        """
        测试可用性过滤：
        1. 创建可用和不可用的表
        2. 验证过滤功能
        """
        metadata_svc = services["metadata"]

        # 创建表
        metadata_svc.add_table("available_table", "可用表", 0)
        metadata_svc.add_table("unavailable_table", "不可用表", 1)
        metadata_svc.add_table("another_available", "另一个可用表", 0)

        # 过滤可用表
        available = metadata_svc.get_available_tables()

        available_names = [t["name"] for t in available]
        assert "available_table" in available_names
        assert "another_available" in available_names
        assert "unavailable_table" not in available_names

    def test_column_update_workflow(self, services):
        """
        测试列的更新工作流：
        1. 创建列
        2. 修改列的属性
        3. 验证修改结果
        """
        metadata_svc = services["metadata"]

        # 创建表和列
        table = metadata_svc.add_table("test_table", "测试表", 0)
        table_id = table["id"]

        column = metadata_svc.add_column_by_id(
            table_id, "age", "INTEGER", "原始注释", 0, "原始业务类型"
        )
        column_id = column["id"]

        # 更新列
        success = metadata_svc.update_column_by_id(
            column_id,
            column_type="VARCHAR",
            comment="更新后的注释",
            business_type="更新后的业务类型",
            is_available=1
        )
        assert success is True

    def test_table_and_column_cascade_deletion(self, services):
        """
        测试表的级联删除：
        1. 创建表和多个字段
        2. 删除表
        3. 验证关联的字段也被删除
        """
        metadata_svc = services["metadata"]

        # 创建表和字段
        table = metadata_svc.add_table("to_delete", "待删除表", 0)
        table_id = table["id"]

        metadata_svc.add_column_by_id(table_id, "col1", "INTEGER")
        metadata_svc.add_column_by_id(table_id, "col2", "VARCHAR")

        # 验证字段存在
        table_info = metadata_svc.get_table_info("to_delete")
        assert len(table_info["columns"]) == 2

        # 删除表
        success = metadata_svc.delete_table_by_id(table_id)
        assert success is True

        # 验证表被删除
        result = metadata_svc.get_table_info("to_delete")
        assert result is None


class TestGlossaryManagementFlow:
    """术语表管理完整流程测试"""

    @pytest.fixture
    def services(self, db_session):
        """创建所需的服务实例"""
        return {
            "glossary": GlossaryService(db_session),
            "metadata": MetadataService(db_session)
        }

    def test_concept_glossary_workflow(self, services):
        """
        测试概念术语工作流：
        1. 添加概念术语
        2. 查询概念术语
        3. 更新概念术语
        """
        glossary_svc = services["glossary"]

        # 1. 添加概念术语
        content = {
            "explanation": "用户是指使用系统的人员",
            "examples": ["张三", "李四", "王五"]
        }
        success = glossary_svc.add_term("用户", "concept", content, "admin")
        assert success is True

        # 2. 查询概念术语
        term = glossary_svc.find_term("用户")
        assert term is not None
        assert term["type"] == "concept"
        assert term["creator"] == "admin"

        # 3. 更新概念术语
        new_content = {
            "explanation": "用户是指使用系统的合法人员",
            "examples": ["张三", "李四"]
        }
        success = glossary_svc.update_term(term["id"], content=new_content)
        assert success is True

        # 验证更新
        updated_term = glossary_svc.find_term("用户")
        assert updated_term["content"]["explanation"] == "用户是指使用系统的合法人员"

    def test_sql_qa_glossary_workflow(self, services):
        """
        测试SQL问答术语工作流：
        1. 添加多个SQL问答术语
        2. 按类型查询
        3. 验证内容
        """
        glossary_svc = services["glossary"]

        # 添加SQL问答术语
        qa_terms = [
            {
                "name": "查询所有用户",
                "content": {
                    "question": "如何查询系统中所有用户？",
                    "sql": "SELECT * FROM users;",
                    "description": "返回用户表的所有记录"
                }
            },
            {
                "name": "查询活跃用户",
                "content": {
                    "question": "如何查询活跃用户？",
                    "sql": "SELECT * FROM users WHERE status = 'active';",
                    "description": "返回状态为活跃的用户"
                }
            }
        ]

        for term_info in qa_terms:
            success = glossary_svc.add_term(
                term_info["name"],
                "sql_qa",
                term_info["content"],
                "admin"
            )
            assert success is True

        # 按类型查询
        sql_qa_terms = glossary_svc.get_terms_by_type("sql_qa")
        assert len(sql_qa_terms) >= 2

        # 验证内容
        query_all = glossary_svc.find_term("查询所有用户")
        assert query_all is not None
        assert "SELECT * FROM users" in query_all["content"]["sql"]

    def test_dictionary_mapping_glossary_workflow(self, services):
        """
        测试字典转换术语工作流：
        1. 添加多个字典转换术语
        2. 查询和使用
        """
        glossary_svc = services["glossary"]

        # 添加字典转换术语
        mappings = {
            "gender_mapping": {
                "content": {
                    "mappings": {
                        "男": "M",
                        "女": "F",
                        "其他": "O"
                    }
                }
            },
            "status_mapping": {
                "content": {
                    "mappings": {
                        "活跃": "ACTIVE",
                        "休眠": "INACTIVE",
                        "禁用": "DISABLED"
                    }
                }
            }
        }

        for term_name, term_data in mappings.items():
            success = glossary_svc.add_term(
                term_name,
                "dict_mapping",
                term_data["content"],
                "admin"
            )
            assert success is True

        # 查询字典转换术语
        gender = glossary_svc.find_term("gender_mapping")
        assert gender is not None
        assert gender["content"]["mappings"]["男"] == "M"

        # 按类型查询
        dict_terms = glossary_svc.get_terms_by_type("dict_mapping")
        assert len(dict_terms) >= 2

    def test_glossary_and_metadata_integration(self, services):
        """
        测试术语表与元数据的协作：
        1. 创建表和字段
        2. 添加相关的术语
        3. 验证关联效果
        """
        metadata_svc = services["metadata"]
        glossary_svc = services["glossary"]

        # 创建表
        table = metadata_svc.add_table("employees", "员工表", 0)

        # 添加相关的术语
        glossary_svc.add_term(
            "员工",
            "concept",
            {"explanation": "员工是指公司正式员工"},
            "admin"
        )

        glossary_svc.add_term(
            "查询所有员工",
            "sql_qa",
            {"question": "如何查询所有员工？", "sql": "SELECT * FROM employees;"},
            "admin"
        )

        glossary_svc.add_term(
            "部门代码映射",
            "dict_mapping",
            {"mappings": {"IT": "001", "HR": "002"}},
            "admin"
        )

        # 验证术语和元数据
        assert metadata_svc.get_table_info("employees") is not None
        assert glossary_svc.find_term("员工") is not None
        assert glossary_svc.find_term("查询所有员工") is not None


class TestPromptTemplateFlow:
    """提示词模板工作流测试"""

    @pytest.fixture
    def prompt_service(self, db_session):
        """创建提示词模板服务"""
        return PromptTemplateService(db_session)

    def test_template_creation_and_validation_workflow(self, prompt_service):
        """
        测试模板创建和验证工作流：
        1. 创建带验证的模板
        2. 尝试创建无效模板
        3. 更新模板
        """
        # 1. 创建有效模板
        fields = ["table_name", "columns", "condition"]
        template = "为表 {table_name}（字段：{columns}）生成查询SQL，查询条件：{condition}"

        success = prompt_service.add_template("查询SQL生成", fields, template)
        assert success is True

        # 2. 尝试创建无效模板（占位符不匹配）
        invalid_template = "为表 {table_name} 生成查询，使用 {unknown_field}"
        success = prompt_service.add_template(
            "无效模板", fields, invalid_template
        )
        assert success is False

        # 3. 验证创建的模板
        valid_template = prompt_service.get_template_by_name("查询SQL生成")
        assert valid_template is not None
        assert len(valid_template["fields"]) == 3

    def test_multiple_templates_management(self, prompt_service):
        """
        测试多个模板的管理：
        1. 创建多个不同用途的模板
        2. 查询和检索
        3. 更新和删除
        """
        # 创建不同用途的模板
        templates = [
            {
                "name": "SQL生成模板",
                "fields": ["table", "columns"],
                "template": "根据表 {table} 的字段 {columns} 生成查询"
            },
            {
                "name": "数据解释模板",
                "fields": ["data_name", "metric"],
                "template": "解释 {data_name} 中的 {metric} 含义"
            },
            {
                "name": "异常分析模板",
                "fields": ["metric", "threshold"],
                "template": "分析 {metric} 超过 {threshold} 的原因"
            }
        ]

        # 创建所有模板
        for template_info in templates:
            success = prompt_service.add_template(
                template_info["name"],
                template_info["fields"],
                template_info["template"]
            )
            assert success is True

        # 验证所有模板都存在
        all_templates = prompt_service.get_templates()
        assert len(all_templates) >= 3

        # 验证可以按名称检索
        sql_template = prompt_service.get_template_by_name("SQL生成模板")
        assert sql_template is not None
        assert "表" in sql_template["template"]

        # 更新模板
        template_id = sql_template["id"]
        success = prompt_service.update_template(
            template_id,
            name="更新的SQL生成模板"
        )
        assert success is True

        # 删除模板
        success = prompt_service.delete_template(template_id)
        assert success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
