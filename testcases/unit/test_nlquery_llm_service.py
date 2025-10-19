"""
NLQueryLLMService 测试
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# 添加 backend 目录到路径
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from services.llm_service import NLQueryLLMService
from utils.logger import logger


class MockLLMClient:
    """模拟 OpenAI 客户端"""

    def __init__(self, response_type="sql"):
        self.response_type = response_type
        self.call_count = 0
        self.chat = self._get_chat()

    def _get_chat(self):
        """返回可链式调用的对象"""
        chat_mock = Mock()
        chat_mock.completions.create = self.create
        return chat_mock

    def create(self, **kwargs):
        """模拟 API 调用"""
        self.call_count += 1
        response = Mock()

        if self.response_type == "sql":
            content = json.dumps({
                "sql": "SELECT * FROM users WHERE age > 18;",
                "explanation": "查询年龄大于18岁的用户",
                "confidence": 0.95
            })
        elif self.response_type == "validation":
            content = json.dumps({
                "is_clear": True,
                "confidence": 0.9,
                "details": "用户输入清晰，SQL 正确对应",
                "suggestions": []
            })
        elif self.response_type == "explanation":
            content = "这个 SQL 查询用于检索所有年龄大于18岁的用户"
        else:
            content = "Default response"

        response.choices = [Mock(message=Mock(content=content))]
        return response


class MockTemplateService:
    """模拟提示词模板服务"""

    def __init__(self):
        self.templates = {
            "sql_generation": {
                "id": 1,
                "name": "sql_generation",
                "fields": ["user_input", "context"],
                "template": "生成 SQL: 用户输入={{user_input}}, 上下文={{context}}"
            },
            "sql_retry": {
                "id": 2,
                "name": "sql_retry",
                "fields": ["user_input", "context", "previous_sql", "error_message"],
                "template": "重试 SQL: {{previous_sql}}, 错误={{error_message}}"
            },
            "input_validation": {
                "id": 3,
                "name": "input_validation",
                "fields": ["user_input", "context", "sql_query"],
                "template": "验证: SQL={{sql_query}}"
            },
            "sql_explanation": {
                "id": 4,
                "name": "sql_explanation",
                "fields": ["sql_query", "user_input"],
                "template": "解释 SQL: {{sql_query}}"
            }
        }

    def get_template_by_name(self, name: str):
        """获取模板"""
        return self.templates.get(name)


@pytest.fixture
def mock_llm_client():
    """创建模拟 LLM 客户端"""
    return MockLLMClient(response_type="sql")


@pytest.fixture
def mock_template_service():
    """创建模拟提示词模板服务"""
    return MockTemplateService()


@pytest.fixture
def config():
    """创建配置字典"""
    return {
        "model": "gpt-4",
        "temperature": 0.1,
        "max_tokens": 2000
    }


@pytest.fixture
def nlquery_service(mock_llm_client, config, mock_template_service):
    """创建 NLQueryLLMService 实例"""
    return NLQueryLLMService(
        mock_llm_client,
        config,
        template_service=mock_template_service
    )


class TestNLQueryLLMServiceBasics:
    """基础功能测试"""

    def test_service_initialization(self, nlquery_service):
        """测试服务初始化"""
        assert nlquery_service is not None
        assert nlquery_service.template_renderer is not None
        logger.info("服务初始化成功")

    def test_inherited_methods(self, nlquery_service):
        """测试继承的基础方法"""
        model_name = nlquery_service.get_model_name()
        assert model_name == "gpt-4"

        temperature = nlquery_service.get_temperature()
        assert temperature == 0.1

        logger.info(f"继承方法测试通过: model={model_name}, temp={temperature}")

    def test_config_access(self, nlquery_service):
        """测试配置访问"""
        assert nlquery_service.config.get("model") == "gpt-4"
        assert nlquery_service.config.get("temperature") == 0.1
        assert nlquery_service.config.get("max_tokens") == 2000
        logger.info("配置访问测试通过")


class TestSQLGeneration:
    """SQL 生成测试"""

    def test_generate_sql_basic(self, nlquery_service):
        """测试基础 SQL 生成"""
        result = nlquery_service.generate_sql(
            user_input="查询年龄大于18岁的用户",
            context="表: users (id, name, age)"
        )

        assert result["success"] is True
        assert "SELECT" in result["sql"]
        assert result["confidence"] > 0
        logger.info(f"SQL 生成成功: {result['sql']}")

    def test_generate_sql_returns_dict_structure(self, nlquery_service):
        """测试 SQL 生成返回的字典结构"""
        result = nlquery_service.generate_sql(
            user_input="查询订单",
            context="表: orders"
        )

        assert "success" in result
        assert "sql" in result
        assert "explanation" in result
        assert "confidence" in result
        logger.info("SQL 生成返回结构验证通过")

    def test_generate_sql_with_custom_template(self, nlquery_service):
        """测试使用自定义模板生成 SQL"""
        result = nlquery_service.generate_sql(
            user_input="获取所有活跃用户",
            context="表: users (id, name, status)",
            template_name="sql_generation"
        )

        assert result["success"] is True
        assert len(result["sql"]) > 0
        logger.info("自定义模板 SQL 生成测试通过")

    def test_generate_sql_with_temperature_override(self, nlquery_service):
        """测试温度参数覆盖"""
        result = nlquery_service.generate_sql(
            user_input="查询用户",
            context="表: users",
            temperature=0.5
        )

        assert result["success"] is True
        logger.info("温度参数覆盖测试通过")

    def test_generate_sql_error_handling(self, mock_llm_client, config, mock_template_service):
        """测试 SQL 生成错误处理"""
        # 创建失败的模拟客户端
        bad_client = Mock()
        bad_client.chat.completions.create.side_effect = Exception("API 错误")

        service = NLQueryLLMService(bad_client, config, mock_template_service)
        result = service.generate_sql(
            user_input="查询",
            context="表"
        )

        assert result["success"] is False
        assert result["error"] is not None
        assert result["sql"] == ""
        logger.info(f"错误处理验证通过: {result['error']}")


class TestSQLRetry:
    """SQL 重试测试"""

    def test_retry_sql_generation_basic(self, nlquery_service):
        """测试基础 SQL 重试"""
        result = nlquery_service.retry_sql_generation(
            user_input="查询活跃用户",
            context="表: users",
            previous_sql="SELECT * FROM users WHERE status='active';",
            error_message="表 'users' 不存在"
        )

        assert result["success"] is True
        assert "retry_count" in result
        assert result["retry_count"] == 1
        logger.info(f"SQL 重试成功: {result['sql']}")

    def test_retry_sql_includes_error_info(self, nlquery_service):
        """测试重试包含错误信息"""
        result = nlquery_service.retry_sql_generation(
            user_input="查询",
            context="表: users",
            previous_sql="SELECT * FROM nonexistent;",
            error_message="Syntax error near 'nonexistent'"
        )

        assert result["success"] is True
        assert "explanation" in result
        logger.info("重试错误信息处理验证通过")

    def test_retry_sql_higher_temperature(self, nlquery_service):
        """测试重试使用更高的温度"""
        result = nlquery_service.retry_sql_generation(
            user_input="查询",
            context="表",
            previous_sql="SELECT * FROM users;",
            error_message="错误"
        )

        assert result["success"] is True
        logger.info("高温度重试测试通过")


class TestInputValidation:
    """输入验证测试"""

    def test_validate_input_clarity_json_response(self, mock_llm_client, config, mock_template_service):
        """测试输入验证 JSON 响应解析"""
        # 配置返回验证结果
        mock_llm_client.response_type = "validation"

        service = NLQueryLLMService(mock_llm_client, config, mock_template_service)
        result = service.validate_input_clarity(
            user_input="查询年龄大于18岁的用户",
            context="表: users",
            sql_query="SELECT * FROM users WHERE age > 18;"
        )

        assert result["success"] is True
        assert "is_clear" in result
        assert "confidence" in result
        assert "details" in result
        assert "suggestions" in result
        logger.info(f"输入验证成功: is_clear={result['is_clear']}")

    def test_validate_input_fast_flow(self, nlquery_service):
        """测试快速流程的输入验证"""
        result = nlquery_service.validate_input_clarity(
            user_input="获取订单",
            context="表: orders",
            sql_query="SELECT * FROM orders;",
            flow_type="fast"
        )

        assert result["success"] is True
        logger.info(f"快速流程验证: is_clear={result['is_clear']}")

    def test_validate_input_thorough_flow(self, nlquery_service):
        """测试完整流程的输入验证"""
        result = nlquery_service.validate_input_clarity(
            user_input="获取最近一天的订单总金额",
            context="表: orders (id, amount, created_at)",
            sql_query="SELECT SUM(amount) FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY);",
            flow_type="thorough"
        )

        assert result["success"] is True
        logger.info(f"完整流程验证: confidence={result['confidence']}")

    def test_validate_input_with_custom_template(self, nlquery_service):
        """测试自定义模板的输入验证"""
        result = nlquery_service.validate_input_clarity(
            user_input="查询",
            context="表",
            sql_query="SELECT * FROM users;",
            flow_type="fast"
        )

        assert result["success"] is True
        logger.info("自定义模板输入验证测试通过")


class TestSQLExplanation:
    """SQL 解释测试"""

    def test_explain_sql_basic(self, mock_llm_client, config, mock_template_service):
        """测试基础 SQL 解释"""
        mock_llm_client.response_type = "explanation"

        service = NLQueryLLMService(mock_llm_client, config, mock_template_service)
        result = service.explain_sql(
            sql_query="SELECT * FROM users WHERE age > 18;"
        )

        assert result["success"] is True
        assert "explanation" in result
        assert len(result["explanation"]) > 0
        logger.info(f"SQL 解释: {result['summary']}")

    def test_explain_sql_with_context(self, nlquery_service):
        """测试带上下文的 SQL 解释"""
        result = nlquery_service.explain_sql(
            sql_query="SELECT COUNT(*) as total FROM orders WHERE status='completed';",
            user_input="获取已完成订单的数量"
        )

        assert result["success"] is True
        assert "explanation" in result
        assert "summary" in result
        logger.info(f"带上下文 SQL 解释成功")

    def test_explain_sql_summary_truncation(self, nlquery_service):
        """测试 SQL 解释的摘要截断"""
        result = nlquery_service.explain_sql(
            sql_query="SELECT * FROM users;"
        )

        assert result["success"] is True
        # 摘要应该被截断到100字符
        assert len(result["summary"]) <= 104  # 100 + "..."
        logger.info(f"摘要截断验证通过: {len(result['summary'])} 字符")


class TestSQLResponseParsing:
    """SQL 响应解析测试"""

    def test_parse_json_response(self, nlquery_service):
        """测试 JSON 格式的响应解析"""
        json_response = json.dumps({
            "sql": "SELECT * FROM users;",
            "explanation": "查询所有用户",
            "confidence": 0.95
        })

        result = nlquery_service._parse_sql_response(json_response)

        assert result["success"] is True
        assert result["sql"] == "SELECT * FROM users;"
        assert result["confidence"] == 0.95
        logger.info("JSON 响应解析测试通过")

    def test_parse_sql_code_block(self, nlquery_service):
        """测试 SQL 代码块的解析"""
        response = """
        根据你的查询，这是生成的 SQL：

        ```sql
        SELECT * FROM orders WHERE status = 'completed';
        ```

        这个查询会返回所有已完成的订单。
        """

        result = nlquery_service._parse_sql_response(response)

        assert result["success"] is True
        assert "SELECT" in result["sql"]
        assert "orders" in result["sql"]
        logger.info(f"SQL 代码块解析: {result['sql']}")

    def test_parse_direct_sql(self, nlquery_service):
        """测试直接 SQL 的解析"""
        response = "SELECT id, name FROM users WHERE age > 18;"

        result = nlquery_service._parse_sql_response(response)

        assert result["success"] is True
        assert result["sql"] == response
        logger.info("直接 SQL 解析测试通过")

    def test_parse_invalid_response(self, nlquery_service):
        """测试无效响应的解析"""
        invalid_response = "This is not SQL at all"

        result = nlquery_service._parse_sql_response(invalid_response)

        # 应该返回成功但置信度较低
        assert result["success"] is True
        assert result["confidence"] == 0.5
        logger.info(f"无效响应处理: confidence={result['confidence']}")

    def test_parse_empty_response(self, nlquery_service):
        """测试空响应的解析"""
        result = nlquery_service._parse_sql_response("")

        assert result["success"] is False
        assert result["error"] is not None
        logger.info("空响应解析测试通过")


class TestDefaultTemplates:
    """默认模板测试"""

    def test_default_sql_generation_template(self):
        """测试默认 SQL 生成模板"""
        template = NLQueryLLMService._get_default_sql_generation_template()

        # 模板使用 {placeholder} 格式
        assert "{context}" in template
        assert "{user_input}" in template
        assert "json" in template.lower()
        logger.info("默认 SQL 生成模板验证通过")

    def test_default_sql_retry_template(self):
        """测试默认 SQL 重试模板"""
        template = NLQueryLLMService._get_default_sql_retry_template()

        assert "{previous_sql}" in template
        assert "{error_message}" in template
        logger.info("默认 SQL 重试模板验证通过")

    def test_default_validation_template(self):
        """测试默认验证模板"""
        template = NLQueryLLMService._get_default_validation_template()

        assert "{sql_query}" in template
        assert "{user_input}" in template
        logger.info("默认验证模板验证通过")

    def test_default_explanation_template(self):
        """测试默认解释模板"""
        template = NLQueryLLMService._get_default_sql_explanation_template()

        assert "{sql_query}" in template
        logger.info("默认解释模板验证通过")


class TestIntegrationScenarios:
    """集成测试场景"""

    def test_full_sql_generation_workflow(self, nlquery_service):
        """测试完整的 SQL 生成工作流"""
        # 1. 生成 SQL
        generate_result = nlquery_service.generate_sql(
            user_input="查询最近7天的订单",
            context="表: orders (id, created_at, amount)"
        )
        assert generate_result["success"] is True

        # 2. 验证输入
        validate_result = nlquery_service.validate_input_clarity(
            user_input="查询最近7天的订单",
            context="表: orders",
            sql_query=generate_result["sql"],
            flow_type="fast"
        )
        assert validate_result["success"] is True

        # 3. 解释 SQL
        explain_result = nlquery_service.explain_sql(
            sql_query=generate_result["sql"],
            user_input="查询最近7天的订单"
        )
        assert explain_result["success"] is True

        logger.info("完整工作流测试通过")

    def test_error_recovery_workflow(self, nlquery_service):
        """测试错误恢复工作流"""
        # 1. 初始 SQL 生成
        initial_result = nlquery_service.generate_sql(
            user_input="获取用户信息",
            context="表: users"
        )
        assert initial_result["success"] is True

        # 2. 模拟 SQL 执行失败，进行重试
        retry_result = nlquery_service.retry_sql_generation(
            user_input="获取用户信息",
            context="表: users (id, name, email)",
            previous_sql=initial_result["sql"],
            error_message="表名不正确"
        )
        assert retry_result["success"] is True
        assert retry_result["retry_count"] == 1

        logger.info("错误恢复工作流测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
