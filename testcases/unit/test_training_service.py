"""
训练服务单元测试
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# 添加 backend 目录到路径
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from services.training_service import TrainingService
from models.training_models import (
    TrainingData, TrainingSession, TrainingMetrics, SQLValidationResult
)
from models.db_base import SessionLocal, create_tables, drop_tables, Base, engine
from utils.logger import logger


# 数据库设置 - 使用内存SQLite进行测试
@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """设置测试数据库"""
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("测试数据库创建成功")
        yield
        # 清理表
        Base.metadata.drop_all(bind=engine)
        logger.info("测试数据库清理完成")
    except Exception as e:
        logger.error(f"测试数据库设置失败: {e}")
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
def training_service(db_session):
    """创建训练服务实例"""
    return TrainingService(db_session)


class TestTrainingDataManagement:
    """训练数据管理测试"""

    def test_add_training_data(self, training_service):
        """测试添加训练数据"""
        result = training_service.add_training_data(
            question="查询年龄大于18岁的用户",
            sql="SELECT * FROM users WHERE age > 18;",
            category="select",
            difficulty="easy",
            tags="basic,user",
            source="manual"
        )

        assert result is not None
        assert result["question"] == "查询年龄大于18岁的用户"
        assert result["category"] == "select"
        logger.info(f"添加训练数据成功: ID={result['id']}")

    def test_batch_import_training_data(self, training_service):
        """测试批量导入训练数据"""
        data_list = [
            {
                "question": "查询所有用户",
                "sql": "SELECT * FROM users;",
                "category": "select",
                "difficulty": "easy"
            },
            {
                "question": "查询用户订单统计",
                "sql": "SELECT user_id, COUNT(*) as order_count FROM orders GROUP BY user_id;",
                "category": "aggregate",
                "difficulty": "medium"
            },
            {
                "question": "查询用户和订单信息",
                "sql": "SELECT u.*, o.* FROM users u LEFT JOIN orders o ON u.id = o.user_id;",
                "category": "join",
                "difficulty": "hard"
            }
        ]

        result = training_service.batch_import_training_data(data_list)

        assert result["total"] == 3
        assert result["success"] == 3
        assert result["failed"] == 0
        logger.info(f"批量导入成功: {result}")

    def test_batch_import_with_errors(self, training_service):
        """测试批量导入包含错误的数据"""
        data_list = [
            {
                "question": "查询用户",
                "sql": "SELECT * FROM users;"
            },
            {
                "question": "",  # 空问题
                "sql": "SELECT * FROM orders;"
            },
            {
                "question": "查询订单",
                "sql": ""  # 空SQL
            }
        ]

        result = training_service.batch_import_training_data(data_list)

        assert result["total"] == 3
        assert result["success"] == 1
        assert result["failed"] == 2
        logger.info(f"包含错误的导入测试通过: {result}")

    def test_get_training_data(self, training_service):
        """测试获取训练数据"""
        # 先添加数据
        add_result = training_service.add_training_data(
            question="测试问题",
            sql="SELECT * FROM test;",
            category="test"
        )

        # 再获取数据
        get_result = training_service.get_training_data(add_result["id"])

        assert get_result is not None
        assert get_result["question"] == "测试问题"
        assert get_result["sql"] == "SELECT * FROM test;"
        logger.info("获取训练数据成功")

    def test_update_training_data(self, training_service):
        """测试更新训练数据"""
        # 添加数据
        add_result = training_service.add_training_data(
            question="原始问题",
            sql="SELECT * FROM users;"
        )

        # 更新数据
        success = training_service.update_training_data(
            add_result["id"],
            difficulty="hard",
            quality_score=0.8
        )

        assert success is True

        # 验证更新
        updated = training_service.get_training_data(add_result["id"])
        assert updated["difficulty"] == "hard"
        assert updated["quality_score"] == 0.8
        logger.info("更新训练数据成功")

    def test_delete_training_data(self, training_service, db_session):
        """测试删除训练数据"""
        # 添加数据
        add_result = training_service.add_training_data(
            question="待删除问题",
            sql="SELECT * FROM users;"
        )

        # 删除数据
        success = training_service.delete_training_data(add_result["id"])
        assert success is True

        # 清除会话缓存，确保重新查询
        db_session.expunge_all()

        # 验证删除
        deleted = training_service.get_training_data(add_result["id"])
        assert deleted is None
        logger.info("删除训练数据成功")

    def test_verify_training_data(self, training_service):
        """测试验证训练数据"""
        # 添加数据
        add_result = training_service.add_training_data(
            question="验证问题",
            sql="SELECT * FROM users;"
        )

        # 验证数据
        success = training_service.verify_training_data(
            add_result["id"],
            notes="通过验证"
        )

        assert success is True

        # 验证状态
        verified = training_service.get_training_data(add_result["id"])
        assert verified["is_verified"] is True
        logger.info("验证训练数据成功")

    def test_search_training_data(self, training_service):
        """测试搜索训练数据"""
        # 添加多条数据
        training_service.add_training_data(
            question="查询用户信息",
            sql="SELECT * FROM users;"
        )
        training_service.add_training_data(
            question="查询订单信息",
            sql="SELECT * FROM orders;"
        )
        training_service.add_training_data(
            question="用户订单总计",
            sql="SELECT COUNT(*) FROM orders WHERE user_id = 1;"
        )

        # 搜索包含"用户"的数据
        results = training_service.search_training_data("用户", limit=10)

        assert len(results) >= 2
        logger.info(f"搜索结果: {len(results)} 条")

    def test_get_training_data_statistics(self, training_service):
        """测试获取训练数据统计"""
        # 添加多条数据
        training_service.add_training_data(
            question="问题1",
            sql="SELECT * FROM users;",
            category="select",
            difficulty="easy"
        )
        training_service.add_training_data(
            question="问题2",
            sql="SELECT COUNT(*) FROM orders;",
            category="aggregate",
            difficulty="medium"
        )

        # 获取统计
        stats = training_service.get_training_data_statistics()

        assert stats["total"] >= 2
        assert "categories" in stats
        assert "average_quality" in stats
        logger.info(f"训练数据统计: {stats}")


class TestTrainingSessionManagement:
    """训练会话管理测试"""

    def test_create_training_session(self, training_service):
        """测试创建训练会话"""
        result = training_service.create_training_session(
            session_name="测试训练会话",
            session_type="manual",
            notes="这是一个测试会话"
        )

        assert result is not None
        assert result["name"] == "测试训练会话"
        assert result["status"] == "pending"
        logger.info(f"创建训练会话成功: ID={result['id']}")

    def test_start_training_session(self, training_service):
        """测试启动训练会话"""
        # 创建会话
        create_result = training_service.create_training_session(
            session_name="启动测试"
        )

        # 启动会话
        success = training_service.start_training_session(create_result["id"])
        assert success is True

        # 验证状态
        session_info = training_service.get_training_session(create_result["id"])
        assert session_info["status"] == "running"
        logger.info("启动训练会话成功")

    def test_complete_training_session(self, training_service):
        """测试完成训练会话"""
        # 创建并启动会话
        create_result = training_service.create_training_session(
            session_name="完成测试"
        )
        training_service.start_training_session(create_result["id"])

        # 完成会话
        success = training_service.complete_training_session(
            create_result["id"],
            success_rate=0.95,
            avg_confidence=0.92,
            training_time=12.5
        )

        assert success is True

        # 验证结果
        session_info = training_service.get_training_session(create_result["id"])
        assert session_info["status"] == "completed"
        assert session_info["success_rate"] == 0.95
        logger.info("完成训练会话成功")

    def test_get_training_session(self, training_service):
        """测试获取训练会话信息"""
        # 创建会话
        create_result = training_service.create_training_session(
            session_name="获取测试"
        )

        # 获取会话信息
        session_info = training_service.get_training_session(create_result["id"])

        assert session_info is not None
        assert session_info["id"] == create_result["id"]
        assert "created_at" in session_info
        logger.info("获取训练会话成功")

    def test_get_recent_training_sessions(self, training_service):
        """测试获取最近的训练会话"""
        # 创建多个会话
        for i in range(3):
            training_service.create_training_session(
                session_name=f"最近会话 {i+1}"
            )

        # 获取最近的会话
        sessions = training_service.get_recent_training_sessions(days=7, limit=10)

        assert len(sessions) >= 3
        logger.info(f"获取最近会话: {len(sessions)} 个")


class TestValidationResultManagement:
    """SQL验证结果管理测试"""

    def test_record_validation_result(self, training_service):
        """测试记录验证结果"""
        result = training_service.record_validation_result(
            training_data_id=None,
            original_sql="SELECT * FROM users;",
            executed_sql="SELECT * FROM users;",
            is_valid=True,
            validation_message="SQL有效",
            execution_time_ms=123.45,
            row_count=5,
            execution_status="success"
        )

        assert result is not None
        assert result["is_valid"] is True
        assert result["execution_time_ms"] == 123.45
        logger.info(f"记录验证结果成功: ID={result['id']}")

    def test_get_validation_statistics(self, training_service):
        """测试获取验证统计"""
        # 记录多个验证结果
        training_service.record_validation_result(
            training_data_id=None,
            original_sql="SELECT * FROM users;",
            executed_sql="SELECT * FROM users;",
            is_valid=True,
            execution_status="success"
        )
        training_service.record_validation_result(
            training_data_id=None,
            original_sql="SELECT * FROM invalid;",
            executed_sql="SELECT * FROM invalid;",
            is_valid=False,
            error_message="表不存在",
            execution_status="error"
        )

        # 获取统计
        stats = training_service.get_validation_statistics()

        assert "total" in stats
        assert "valid" in stats
        assert "invalid" in stats
        logger.info(f"验证统计: {stats}")

    def test_get_failed_validations(self, training_service):
        """测试获取失败的验证"""
        # 记录失败的验证结果
        training_service.record_validation_result(
            training_data_id=None,
            original_sql="SELECT * FROM nonexistent;",
            executed_sql="SELECT * FROM nonexistent;",
            is_valid=False,
            error_message="表不存在",
            execution_status="error"
        )

        # 获取失败的验证
        failed = training_service.get_failed_validations(limit=10)

        assert len(failed) >= 1
        logger.info(f"获取失败验证: {len(failed)} 条")


class TestIntegrationScenarios:
    """集成测试场景"""

    def test_complete_training_workflow(self, training_service):
        """测试完整的训练工作流"""
        # 1. 添加训练数据
        training_data = training_service.add_training_data(
            question="查询活跃用户",
            sql="SELECT * FROM users WHERE status = 'active';",
            category="select",
            difficulty="medium"
        )
        assert training_data is not None

        # 2. 创建训练会话
        session = training_service.create_training_session(
            session_name="完整工作流测试"
        )
        assert session is not None

        # 3. 启动会话
        success = training_service.start_training_session(session["id"])
        assert success is True

        # 4. 记录验证结果
        validation = training_service.record_validation_result(
            training_data_id=training_data["id"],
            original_sql=training_data["sql"],
            executed_sql=training_data["sql"],
            is_valid=True,
            execution_time_ms=45.5,
            row_count=10
        )
        assert validation is not None

        # 5. 完成会话
        success = training_service.complete_training_session(
            session["id"],
            success_rate=1.0,
            avg_confidence=0.95,
            training_time=10.0
        )
        assert success is True

        logger.info("完整工作流测试通过")

    def test_batch_training_workflow(self, training_service):
        """测试批量训练工作流"""
        # 1. 批量导入训练数据
        data_list = [
            {
                "question": f"查询问题{i}",
                "sql": f"SELECT * FROM table{i};",
                "category": "select",
                "difficulty": "easy"
            }
            for i in range(5)
        ]

        import_result = training_service.batch_import_training_data(data_list)
        assert import_result["success"] == 5

        # 2. 获取统计信息
        stats = training_service.get_training_data_statistics()
        assert stats["total"] >= 5

        logger.info("批量训练工作流测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
