"""
模型命中与告警管理器属性测试
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.db_base import Base
from models.fraudhunter.model_execution_tracking import (
    FraudHunterHitRecord,
    FraudHunterAlertControlRecord
)
from models.fraudhunter.risk_control_model import FraudHunterModelDefinition
from services.fraudhunter.model_execution_service.model_hit_alert_manager import (
    ModelHitAlertManager,
    ModelHit
)


# 测试数据库设置
@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def manager(db_session):
    """创建管理器实例"""
    return ModelHitAlertManager(db_session)


# Hypothesis策略定义
account_id_strategy = st.text(min_size=1, max_size=64, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))

model_hit_strategy = st.builds(
    ModelHit,
    model_id=st.integers(min_value=1, max_value=1000),
    model_name=st.text(min_size=1, max_size=128, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')))
)

hit_models_strategy = st.lists(model_hit_strategy, min_size=1, max_size=5)

indicator_data_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    values=st.one_of(
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(max_size=100)
    ),
    min_size=1,
    max_size=10
)

hit_time_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31)
)


class TestModelHitAlertManager:
    """模型命中与告警管理器测试类"""

    @given(
        account_id=account_id_strategy,
        hit_models=hit_models_strategy,
        indicator_data=indicator_data_strategy,
        hit_time=hit_time_strategy
    )
    @settings(max_examples=100)
    def test_property_1_hit_record_creation_completeness(
        self, manager, db_session, account_id, hit_models, indicator_data, hit_time
    ):
        """
        **Feature: model-execution-tracking, Property 1: 命中记录创建完整性**
        **Validates: Requirements 1.1, 1.4**
        
        对于任何模型执行结果，当账号命中模型时，系统应当创建包含所有必需字段
        （账号标识、指标数据、命中模型信息、命中时间）的命中记录
        """
        # 执行创建命中记录
        hit_record = manager.create_hit_record(account_id, hit_models, indicator_data, hit_time)
        
        # 验证记录创建成功
        assert hit_record is not None
        assert hit_record.id is not None
        
        # 验证所有必需字段都存在且正确
        assert hit_record.account_id == account_id
        assert hit_record.hit_time == hit_time
        assert hit_record.indicator_data == indicator_data
        
        # 验证命中模型信息正确存储
        expected_model_ids = [model.model_id for model in hit_models]
        expected_model_names = [model.model_name for model in hit_models]
        
        assert hit_record.hit_model_ids == expected_model_ids
        assert hit_record.hit_model_names == expected_model_names
        
        # 验证审计字段
        assert hit_record.created_at is not None
        assert hit_record.updated_at is not None

    @given(
        account_id=account_id_strategy,
        hit_models=hit_models_strategy.filter(lambda x: len(x) > 1),  # 确保多个模型
        indicator_data=indicator_data_strategy,
        hit_time=hit_time_strategy
    )
    @settings(max_examples=100)
    def test_property_2_multi_model_hit_storage_consistency(
        self, manager, db_session, account_id, hit_models, indicator_data, hit_time
    ):
        """
        **Feature: model-execution-tracking, Property 2: 多模型命中存储一致性**
        **Validates: Requirements 1.2**
        
        对于任何账号同时命中多个模型的情况，系统应当在单条记录中正确存储所有命中模型的ID和名称列表
        """
        # 执行创建命中记录
        hit_record = manager.create_hit_record(account_id, hit_models, indicator_data, hit_time)
        
        # 验证模型数量一致
        assert len(hit_record.hit_model_ids) == len(hit_models)
        assert len(hit_record.hit_model_names) == len(hit_models)
        assert len(hit_record.hit_model_ids) == len(hit_record.hit_model_names)
        
        # 验证模型ID和名称的对应关系
        for i, model in enumerate(hit_models):
            assert hit_record.hit_model_ids[i] == model.model_id
            assert hit_record.hit_model_names[i] == model.model_name
        
        # 验证所有模型信息都被正确存储
        stored_model_ids = set(hit_record.hit_model_ids)
        expected_model_ids = set(model.model_id for model in hit_models)
        assert stored_model_ids == expected_model_ids
        
        stored_model_names = set(hit_record.hit_model_names)
        expected_model_names = set(model.model_name for model in hit_models)
        assert stored_model_names == expected_model_names

    @given(
        account_id=account_id_strategy,
        hit_models=hit_models_strategy,
        indicator_data=indicator_data_strategy,
        base_time=hit_time_strategy,
        repeat_count=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=100)
    def test_property_3_duplicate_hit_record_independence(
        self, manager, db_session, account_id, hit_models, indicator_data, base_time, repeat_count
    ):
        """
        **Feature: model-execution-tracking, Property 3: 重复命中记录独立性**
        **Validates: Requirements 1.3**
        
        对于任何账号在同一天多次命中相同模型的情况，系统应当为每次命中创建独立的记录，
        记录数量等于命中次数
        """
        created_records = []
        
        # 在同一天内创建多次命中记录
        for i in range(repeat_count):
            # 使用相同的日期但不同的时间
            hit_time = base_time.replace(
                hour=(base_time.hour + i) % 24,
                minute=(base_time.minute + i * 10) % 60
            )
            
            hit_record = manager.create_hit_record(account_id, hit_models, indicator_data, hit_time)
            created_records.append(hit_record)
        
        # 提交事务以确保记录被保存
        db_session.commit()
        
        # 验证创建了正确数量的独立记录
        assert len(created_records) == repeat_count
        
        # 验证每条记录都有唯一的ID
        record_ids = [record.id for record in created_records]
        assert len(set(record_ids)) == repeat_count
        
        # 验证所有记录都是同一账号和同一天
        record_date = base_time.date()
        for record in created_records:
            assert record.account_id == account_id
            assert record.hit_time.date() == record_date
            
        # 从数据库查询验证记录确实被独立存储
        db_records = db_session.query(FraudHunterHitRecord).filter(
            FraudHunterHitRecord.account_id == account_id
        ).all()
        
        assert len(db_records) == repeat_count
        
        # 验证每条记录的完整性
        for db_record in db_records:
            assert db_record.account_id == account_id
            assert db_record.indicator_data == indicator_data
            expected_model_ids = [model.model_id for model in hit_models]
            expected_model_names = [model.model_name for model in hit_models]
            assert db_record.hit_model_ids == expected_model_ids
            assert db_record.hit_model_names == expected_model_names


# 测试无效输入的边界情况
class TestModelHitAlertManagerEdgeCases:
    """边界情况测试"""

    def test_create_hit_record_empty_account_id(self, manager):
        """测试空账号ID"""
        with pytest.raises(ValueError, match="账号ID不能为空"):
            manager.create_hit_record("", [ModelHit(1, "test")], {"key": "value"}, datetime.now())

    def test_create_hit_record_empty_models(self, manager):
        """测试空模型列表"""
        with pytest.raises(ValueError, match="命中模型列表不能为空"):
            manager.create_hit_record("test_account", [], {"key": "value"}, datetime.now())

    def test_create_hit_record_empty_indicator_data(self, manager):
        """测试空指标数据"""
        with pytest.raises(ValueError, match="指标数据不能为空"):
            manager.create_hit_record("test_account", [ModelHit(1, "test")], {}, datetime.now())