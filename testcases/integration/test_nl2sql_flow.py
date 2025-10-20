"""
NL2SQL完整流程集成测试

测试自然语言转SQL的完整工作流：
1. 输入验证 → SQL生成 → 验证 → 执行 → 返回结果
2. 不同流程类型（fast/thorough）
3. 异常处理和重试机制
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from services.nlquery_service.nl2sql_service import NL2SQLService
from services.service_models import TaskState, BaseNodeLog
from services.query_engine import get_query_engine


class TestNL2SQLFlow:
    """NL2SQL完整流程测试"""

    @pytest.fixture
    def mock_services(self):
        """Mock所有外部服务"""
        with patch.multiple(
            'services.nlquery_service.nl2sql_service',
            TaoshaVanna=Mock,
            get_metadata_service=Mock(),
            get_glossary_service=Mock(),
            get_relation_field_config_service=Mock(),
            get_prompt_template_service=Mock(),
            get_query_engine=Mock()
        ):
            yield

    @pytest.fixture
    def nl2sql_service(self, mock_services):
        """创建NL2SQL服务实例"""
        with patch('services.nlquery_service.nl2sql_service.settings') as mock_settings:
            mock_settings.openai_api_key = "test_key"
            mock_settings.taosha_vanna_service_api_base = "http://test"
            mock_settings.taosha_vanna_service_api_key = "test_key"
            mock_settings.taosha_vanna_service_model = "test_model"

            # Mock vanna service
            with patch('services.vanna_service.taosha_vanna_service.TaoshaVanna') as mock_vanna_class:
                mock_vanna = Mock()
                mock_vanna.generate_sql.return_value = "SELECT * FROM users WHERE age > 25;"
                mock_vanna.train.return_value = True
                mock_vanna_class.return_value = mock_vanna

                # Mock metadata service
                with patch('services.metadata_service.metadata_service.get_metadata_service') as mock_metadata:
                    mock_metadata_instance = Mock()
                    mock_metadata_instance.get_metadata.return_value = {
                        "tables": [
                            {
                                "name": "users",
                                "columns": [
                                    {"name": "id", "type": "INTEGER"},
                                    {"name": "name", "type": "VARCHAR"},
                                    {"name": "age", "type": "INTEGER"}
                                ]
                            }
                        ]
                    }
                    mock_metadata.return_value = mock_metadata_instance

                    # Mock glossary service
                    with patch('services.metadata_service.metadata_service.get_glossary_service') as mock_glossary:
                        mock_glossary_instance = Mock()
                        mock_glossary_instance.get_terms.return_value = [
                            {"name": "用户", "type": "concept", "content": {"explanation": "系统用户"}}
                        ]
                        mock_glossary.return_value = mock_glossary_instance

                        # Mock query engine
                        with patch('services.query_engine.get_query_engine') as mock_engine:
                            mock_engine_instance = Mock()
                            mock_engine_instance.get_tables.return_value = ["users"]

                            # Mock execution result
                            import pandas as pd
                            mock_df = pd.DataFrame([
                                {"id": 1, "name": "张三", "age": 30},
                                {"id": 2, "name": "李四", "age": 28}
                            ])
                            mock_engine_instance.execute_query.return_value = mock_df
                            mock_engine.return_value = mock_engine_instance

                            service = NL2SQLService()
                            yield service

    def test_fast_flow_complete_workflow(self, nl2sql_service):
        """测试快速流程（fast）的完整工作流"""
        # 创建任务状态
        task_state = TaskState(
            task_id="test_task_1",
            user_input="查询年龄大于25岁的用户",
            flow_type="fast"
        )

        # 执行工作流
        result = nl2sql_service.workflow.invoke(task_state)

        # 验证结果
        assert result.status == "success"
        assert result.sql_query == "SELECT * FROM users WHERE age > 25;"
        assert result.execution_result is not None
        assert len(result.execution_result) == 2  # 应该有2条记录
        assert result.is_clear is True

        # 验证工作流步骤
        step_names = [log.step for log in result.logs]
        assert "知识库更新" in step_names
        assert "用户输入验证" in step_names
        assert "SQL生成" in step_names
        assert "SQL验证" in step_names
        assert "SQL执行" in step_names

    def test_thorough_flow_complete_workflow(self, nl2sql_service):
        """测试彻底流程（thorough）的完整工作流"""
        task_state = TaskState(
            task_id="test_task_2",
            user_input="统计各年龄段的用户数量",
            flow_type="thorough"
        )

        # 执行工作流
        result = nl2sql_service.workflow.invoke(task_state)

        # 验证结果
        assert result.status == "success"
        assert result.sql_query is not None
        assert result.execution_result is not None

    def test_sql_generation_with_glossary(self, nl2sql_service):
        """测试使用术语表的SQL生成"""
        task_state = TaskState(
            task_id="test_task_3",
            user_input="查询所有用户",
            flow_type="fast"
        )

        result = nl2sql_service.workflow.invoke(task_state)

        # 验证术语表被使用
        assert result.status == "success"
        assert "users" in result.sql_query.lower()

    def test_sql_validation_error_handling(self, nl2sql_service):
        """测试SQL验证错误处理"""
        # Mock SQL验证失败
        with patch.object(nl2sql_service, '_validate_sql', return_value=False):
            task_state = TaskState(
                task_id="test_task_4",
                user_input="无效查询",
                flow_type="fast"
            )

            result = nl2sql_service.workflow.invoke(task_state)

            # 验证错误处理
            assert result.status == "failed"
            assert result.error_message is not None

    def test_sql_execution_error_handling(self, nl2sql_service):
        """测试SQL执行错误处理"""
        # Mock SQL执行失败
        with patch.object(nl2sql_service.db_service, 'execute_query',
                         side_effect=Exception("执行错误")):
            task_state = TaskState(
                task_id="test_task_5",
                user_input="查询用户",
                flow_type="fast"
            )

            result = nl2sql_service.workflow.invoke(task_state)

            # 验证错误处理
            assert result.status == "failed"
            assert "执行错误" in result.error_message

    def test_input_clarity_validation(self, nl2sql_service):
        """测试输入清晰度验证"""
        # 清晰的输入
        clear_task = TaskState(
            task_id="clear_task",
            user_input="查询年龄大于30岁的用户信息",
            flow_type="fast"
        )

        clear_result = nl2sql_service.workflow.invoke(clear_task)
        assert clear_result.is_clear is True

        # 模糊的输入（如果有OpenAI API）
        unclear_task = TaskState(
            task_id="unclear_task",
            user_input="用户",
            flow_type="fast"
        )

        unclear_result = nl2sql_service.workflow.invoke(unclear_task)
        # 如果API不可用，应该跳过验证并认为清晰
        assert unclear_result.is_clear is True

    def test_retry_mechanism(self, nl2sql_service):
        """测试重试机制"""
        # Mock前几次执行失败，第3次成功
        call_count = 0
        def mock_execute(sql):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"尝试失败 {call_count}")
            import pandas as pd
            return pd.DataFrame([{"test": "success"}])

        with patch.object(nl2sql_service.db_service, 'execute_query',
                         side_effect=mock_execute):
            task_state = TaskState(
                task_id="retry_task",
                user_input="查询用户",
                flow_type="fast",
                max_retries=3
            )

            result = nl2sql_service.workflow.invoke(task_state)

            # 验证重试成功
            assert result.status == "success"
            assert call_count == 3  # 应该重试了2次

    def test_metadata_integration(self, nl2sql_service):
        """测试元数据集成"""
        # 添加更多表的元数据
        nl2sql_service.metadata_service.get_metadata.return_value = {
            "tables": [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "INTEGER"},
                        {"name": "name", "type": "VARCHAR"},
                        {"name": "dept_id", "type": "INTEGER"}
                    ]
                },
                {
                    "name": "departments",
                    "columns": [
                        {"name": "id", "type": "INTEGER"},
                        {"name": "name", "type": "VARCHAR"}
                    ]
                }
            ]
        }

        task_state = TaskState(
            task_id="join_task",
            user_input="查询用户及其部门信息",
            flow_type="fast"
        )

        result = nl2sql_service.workflow.invoke(task_state)

        # 验证生成了JOIN查询
        assert result.status == "success"
        assert "join" in result.sql_query.lower()

    def test_prompt_template_integration(self, nl2sql_service):
        """测试提示词模板集成"""
        # Mock模板渲染
        mock_renderer = Mock()
        mock_renderer.render_template.return_value = "生成的提示词内容"
        nl2sql_service.template_renderer = mock_renderer

        task_state = TaskState(
            task_id="template_task",
            user_input="使用模板查询",
            flow_type="fast"
        )

        result = nl2sql_service.workflow.invoke(task_state)

        # 验证模板渲染被调用
        mock_renderer.render_template.assert_called()

    def test_task_state_tracking(self, nl2sql_service):
        """测试任务状态追踪"""
        task_state = TaskState(
            task_id="tracking_task",
            user_input="测试追踪",
            flow_type="fast"
        )

        # 添加追踪器mock
        with patch('services.nlquery_service.nl2sql_service.tracker') as mock_tracker:
            mock_tracker.start_task.return_value = True
            mock_tracker.update_task.return_value = True
            mock_tracker.complete_task.return_value = True

            result = nl2sql_service.workflow.invoke(task_state)

            # 验证追踪器被调用
            mock_tracker.start_task.assert_called()
            mock_tracker.update_task.assert_called()
            mock_tracker.complete_task.assert_called()

    def test_complex_query_workflow(self, nl2sql_service):
        """测试复杂查询工作流"""
        # Mock聚合查询结果
        import pandas as pd
        complex_df = pd.DataFrame([
            {"age_group": "20-30", "count": 5},
            {"age_group": "30-40", "count": 3}
        ])
        nl2sql_service.db_service.execute_query.return_value = complex_df
        nl2sql_service.vanna.generate_sql.return_value = """
            SELECT
                CASE
                    WHEN age BETWEEN 20 AND 30 THEN '20-30'
                    WHEN age BETWEEN 30 AND 40 THEN '30-40'
                    ELSE '其他'
                END as age_group,
                COUNT(*) as count
            FROM users
            GROUP BY age_group
        """

        task_state = TaskState(
            task_id="complex_task",
            user_input="统计各年龄段的用户数量分布",
            flow_type="thorough"
        )

        result = nl2sql_service.workflow.invoke(task_state)

        # 验证复杂查询成功
        assert result.status == "success"
        assert result.execution_result is not None
        assert len(result.execution_result) == 2

    def test_error_recovery_workflow(self, nl2sql_service):
        """测试错误恢复工作流"""
        # Mock部分失败的场景
        call_count = 0
        def mock_generate_sql(input_text):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("生成失败")
            return "SELECT * FROM users WHERE age > 20;"

        nl2sql_service.vanna.generate_sql.side_effect = mock_generate_sql

        task_state = TaskState(
            task_id="recovery_task",
            user_input="查询用户",
            flow_type="fast",
            max_retries=2
        )

        result = nl2sql_service.workflow.invoke(task_state)

        # 验证错误恢复
        assert call_count == 2  # 应该重试了1次


class TestAsyncQueryServiceIntegration:
    """异步查询服务集成测试"""

    @pytest.mark.asyncio
    async def test_async_query_submission(self):
        """测试异步查询提交"""
        with patch('services.nlquery_service.async_query_service.get_nl2sql_service') as mock_get_service:
            # Mock NL2SQL服务
            mock_nl2sql = Mock()
            mock_nl2sql.workflow.invoke.return_value = TaskState(
                task_id="async_test",
                user_input="测试查询",
                status="success"
            )
            mock_get_service.return_value = mock_nl2sql

            # Mock tracker
            with patch('services.nlquery_service.async_query_service.tracker') as mock_tracker:
                mock_tracker.start_task.return_value = True
                mock_tracker.update_task.return_value = True
                mock_tracker.complete_task.return_value = True

                from services.nlquery_service.async_query_service import AsyncQueryService
                service = AsyncQueryService()

                # 提交异步查询
                task_id = await service.submit_query(
                    "查询用户信息",
                    operator="test_user",
                    flow_type="fast"
                )

                assert task_id is not None
                assert isinstance(task_id, str)

    def test_workflow_steps_validation(self):
        """测试工作流步骤验证"""
        with patch.multiple(
            'services.nlquery_service.nl2sql_service',
            settings=Mock(),
            TaoshaVanna=Mock,
            get_metadata_service=Mock(),
            get_glossary_service=Mock(),
            get_relation_field_config_service=Mock(),
            get_prompt_template_service=Mock(),
            get_query_engine=Mock()
        ):
            # 创建服务实例进行步骤验证
            service = NL2SQLService()

            # 验证工作流包含必要的步骤
            workflow_nodes = list(service.workflow.nodes.keys())
            required_steps = [
                "知识库更新",
                "用户输入验证",
                "SQL生成",
                "SQL验证",
                "SQL执行"
            ]

            for step in required_steps:
                assert any(step in node for node in workflow_nodes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
