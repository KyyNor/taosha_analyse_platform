"""
异步查询服务V2集成测试
"""

import pytest
import asyncio
import sys
from pathlib import Path

# 添加backend目录到路径
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from services.nlquery_service.async_query_service import AsyncQueryService, get_async_query_service
from services.tracking_service.operation_tracking import OperationTracker
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
async def tracker(db_session):
    """创建操作追踪器"""
    return OperationTracker(db_session)


class TestAsyncQueryServiceV2:
    """异步查询服务V2测试"""

    def test_async_query_service_v2_initialization(self):
        """测试AsyncQueryService V2初始化"""
        service = AsyncQueryService(use_v2=True)
        
        assert service is not None
        assert service.use_v2 is True
        assert service.nl2sql_service is not None
        logger.info("AsyncQueryService V2初始化成功")

    def test_async_query_service_use_v1(self):
        """测试AsyncQueryService使用旧架构"""
        service = AsyncQueryService(use_v2=False)
        
        assert service is not None
        assert service.use_v2 is False
        assert service.nl2sql_service is not None
        logger.info("AsyncQueryService V1初始化成功")

    @pytest.mark.asyncio
    async def test_submit_query_with_v2(self, tracker):
        """测试使用V2架构提交查询"""
        service = AsyncQueryService(use_v2=True)
        
        # 提交查询任务
        task_id = await service.submit_query(
            user_input="查询所有用户",
            operator="test_user",
            flow_type="fast",
            tracker=tracker
        )
        
        assert task_id is not None
        logger.info(f"查询任务提交成功，任务ID: {task_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
