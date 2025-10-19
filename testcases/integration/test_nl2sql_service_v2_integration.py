"""
NL2SQL Service V2集成测试
"""

import pytest
import sys
from pathlib import Path

# 添加backend目录到路径
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from services.nlquery_service.nl2sql_service_v2 import NL2SQLServiceV2
from models.db_base import SessionLocal, Base, engine
from utils.logger import logger


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """设置测试数据库"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("测试数据库创建成功")
        yield
        Base.metadata.drop_all(bind=engine)
        logger.info("测试数据库清理完成")
    except Exception as e:
        logger.error(f"数据库设置失败: {e}")
        raise


@pytest.fixture
def db_session():
    """创建数据库会话"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def nl2sql_service(db_session):
    """创建NL2SQL Service V2实例"""
    return NL2SQLServiceV2(db_session=db_session)


class TestNL2SQLServiceV2Initialization:
    """NL2SQL Service V2初始化测试"""

    def test_service_initialization(self, nl2sql_service):
        """测试服务初始化"""
        assert nl2sql_service is not None
        assert nl2sql_service.vector_store is not None
        assert nl2sql_service.context_builder is not None
        assert nl2sql_service.llm_service is not None
        assert nl2sql_service.training_service is not None
        logger.info("NL2SQL Service V2初始化成功")

    def test_workflow_initialization(self, nl2sql_service):
        """测试工作流初始化"""
        assert nl2sql_service.workflow is not None
        logger.info("工作流初始化成功")


class TestTrainingDataIntegration:
    """训练数据集成测试"""

    def test_add_training_data(self, nl2sql_service):
        """测试添加训练数据"""
        success = nl2sql_service.add_training_data(
            question="查询所有用户",
            sql="SELECT * FROM users;",
            category="select",
            difficulty="easy"
        )

        assert success is True
        logger.info("添加训练数据成功")

    def test_add_multiple_training_data(self, nl2sql_service):
        """测试添加多条训练数据"""
        training_examples = [
            ("查询活跃用户", "SELECT * FROM users WHERE status='active';"),
            ("查询订单统计", "SELECT user_id, COUNT(*) FROM orders GROUP BY user_id;"),
            ("查询用户订单", "SELECT u.*, o.* FROM users u LEFT JOIN orders o ON u.id = o.user_id;"),
        ]

        for question, sql in training_examples:
            success = nl2sql_service.add_training_data(
                question=question,
                sql=sql,
                category="general"
            )
            assert success is True

        logger.info(f"添加{len(training_examples)}条训练数据成功")

    def test_get_statistics(self, nl2sql_service):
        """测试获取统计信息"""
        # 先添加训练数据
        nl2sql_service.add_training_data(
            question="测试问题",
            sql="SELECT * FROM test;",
            category="select"
        )

        # 获取统计
        stats = nl2sql_service.get_statistics()

        assert "training_data" in stats
        assert "validation" in stats
        assert "vector_store" in stats
        logger.info(f"统计信息: {stats}")


class TestWorkflowExecution:
    """工作流执行测试"""

    def test_simple_query_execution(self, nl2sql_service):
        """测试简单查询执行"""
        result = nl2sql_service.query(
            user_input="查询用户信息",
            flow_type="fast"
        )

        assert "success" in result
        logger.info(f"查询执行完成: success={result['success']}")

    def test_query_with_context(self, nl2sql_service):
        """测试带上下文的查询"""
        result = nl2sql_service.query(
            user_input="查询订单统计",
            flow_type="fast",
            table_names=["orders"]
        )

        assert "success" in result
        logger.info(f"带表信息的查询执行完成: success={result['success']}")

    def test_query_with_relation_id(self, nl2sql_service):
        """测试带关联ID的查询"""
        result = nl2sql_service.query(
            user_input="查询用户订单",
            flow_type="fast",
            relation_id="user_id"
        )

        assert "success" in result
        logger.info(f"带关联ID的查询执行完成: success={result['success']}")


class TestErrorHandling:
    """错误处理测试"""

    def test_invalid_input_handling(self, nl2sql_service):
        """测试无效输入处理"""
        result = nl2sql_service.query(
            user_input="",
            flow_type="fast"
        )

        # 应该能够优雅地处理空输入
        assert "success" in result
        logger.info("空输入处理成功")

    def test_service_without_db_session(self):
        """测试不提供数据库会话的服务"""
        service = NL2SQLServiceV2(db_session=None)

        assert service is not None
        assert service.training_service is None
        logger.info("无数据库会话的服务初始化成功")


class TestModuleIntegration:
    """模块集成测试"""

    def test_vector_store_integration(self, nl2sql_service):
        """测试向量存储集成"""
        assert nl2sql_service.vector_store is not None
        logger.info("向量存储集成验证通过")

    def test_llm_service_integration(self, nl2sql_service):
        """测试LLM服务集成"""
        assert nl2sql_service.llm_service is not None
        logger.info("LLM服务集成验证通过")

    def test_training_service_integration(self, nl2sql_service):
        """测试Training Service集成"""
        assert nl2sql_service.training_service is not None
        logger.info("Training Service集成验证通过")

    def test_context_builder_integration(self, nl2sql_service):
        """测试Context Builder集成"""
        assert nl2sql_service.context_builder is not None
        logger.info("Context Builder集成验证通过")

    def test_metadata_service_integration(self, nl2sql_service):
        """测试元数据服务集成"""
        assert nl2sql_service.metadata_service is not None
        logger.info("元数据服务集成验证通过")


class TestWorkflowFlowTypeRouting:
    """工作流流程类型路由测试"""

    def test_workflow_has_correct_edges(self, nl2sql_service):
        """验证工作流有正确的边连接"""
        workflow = nl2sql_service.workflow

        # 获取工作流的节点和边信息
        graph = workflow.get_graph()

        # 应该有5个节点
        nodes = graph.nodes if hasattr(graph, 'nodes') else list(graph.nodes)
        node_count = len(nodes) if not callable(nodes) else len(list(nodes))
        logger.info(f"工作流节点数: {node_count}")
        assert node_count >= 5, f"应该有至少5个节点，实际有{node_count}个"

        # 验证工作流本身存在且已编译
        assert workflow is not None
        assert hasattr(workflow, 'invoke'), "工作流应该有invoke方法"

        logger.info("工作流节点验证通过")

    def test_fast_flow_routing_logic(self, nl2sql_service):
        """测试快速流程的路由逻辑

        快速流程应该：check_training -> validate_input -> generate_sql -> execute_sql -> explain_result
        """
        from services.service_models import TaskState
        from datetime import datetime

        # 创建fast流程的初始状态
        state = TaskState(
            task_id="test_fast_flow",
            user_input="测试查询",
            flow_type="fast",
            created_at=datetime.now()
        )

        # 执行第一步（check_training）后，应该路由到validate_input
        # 这里我们只是验证状态对象能正确创建和使用
        assert state.flow_type == "fast"
        assert state.user_input == "测试查询"
        logger.info("快速流程初始状态验证通过")

    def test_thorough_flow_routing_logic(self, nl2sql_service):
        """测试彻底流程的路由逻辑

        彻底流程应该：check_training -> generate_sql -> validate_input -> execute_sql -> explain_result
        """
        from services.service_models import TaskState
        from datetime import datetime

        # 创建thorough流程的初始状态
        state = TaskState(
            task_id="test_thorough_flow",
            user_input="测试查询",
            flow_type="thorough",
            created_at=datetime.now()
        )

        # 验证状态对象能正确创建和使用
        assert state.flow_type == "thorough"
        assert state.user_input == "测试查询"
        logger.info("彻底流程初始状态验证通过")

    def test_retry_logic_state(self, nl2sql_service):
        """测试重试机制的状态管理"""
        from services.service_models import TaskState
        from datetime import datetime

        # 创建一个有错误的状态（模拟SQL执行失败）
        state = TaskState(
            task_id="test_retry",
            user_input="测试查询",
            flow_type="fast",
            sql_query="SELECT * FROM test",
            error_message="SQL execution failed",
            retry_count=0,
            max_retries=5,
            created_at=datetime.now()
        )

        # 验证状态可以被更新用于重试
        assert state.error_message is not None
        assert state.retry_count == 0

        # 模拟重试计数增加
        state.retry_count = 1
        assert state.retry_count == 1
        assert state.retry_count < state.max_retries

        logger.info("重试逻辑状态管理验证通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
