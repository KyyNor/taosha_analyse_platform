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
from schemas.fraudhunter.alert_control_record import (
    AlertControlFilters,
    PaginationParams
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

    @given(
        account_id=account_id_strategy,
        hit_models=hit_models_strategy,
        indicator_data=indicator_data_strategy,
        hit_time=hit_time_strategy,
        is_send_alert=st.booleans(),
        is_duplicate=st.booleans()
    )
    @settings(max_examples=100)
    def test_property_7_alert_status_setting_correctness(
        self, manager, db_session, account_id, hit_models, indicator_data, hit_time, is_send_alert, is_duplicate
    ):
        """
        **Feature: model-execution-tracking, Property 7: 告警状态设置正确性**
        **Validates: Requirements 2.3**
        
        对于任何告警处理，系统应当根据模型配置和历史记录正确设置alert_status：
        未配置告警的模型为'not_configured'，首次告警为'sent'，重复告警为'duplicate'
        """
        # 为每个模型创建模型定义
        model_definitions = []
        for model in hit_models:
            model_def = FraudHunterModelDefinition(
                id=model.model_id,
                model_code=f"MODEL_{model.model_id}",
                model_name=model.model_name,
                description="Test model",
                is_send_alert_message=is_send_alert,
                is_acct_control=False,
                rule_config={"rules": []},
                status="online"
            )
            db_session.add(model_def)
            model_definitions.append(model_def)
        
        db_session.flush()
        
        # 如果需要模拟重复告警，先创建一条历史记录
        if is_duplicate and is_send_alert:
            # 创建历史命中记录
            historical_hit = manager.create_hit_record(account_id, hit_models, indicator_data, hit_time)
            historical_alerts = manager.hit_record_processor(historical_hit)
            db_session.commit()
        
        # 创建新的命中记录
        hit_record = manager.create_hit_record(account_id, hit_models, indicator_data, hit_time)
        
        # 处理命中记录生成告警管控记录
        alert_control_records = manager.hit_record_processor(hit_record)
        
        # 验证告警状态设置正确性
        for i, record in enumerate(alert_control_records):
            model_def = model_definitions[i]
            
            if not model_def.is_send_alert_message:
                # 未配置告警的模型应该是 not_configured
                assert record.alert_status == 'not_configured'
                assert record.alert_message is None
                assert record.alert_person is None
                assert record.alert_time is None
            elif is_duplicate and is_send_alert:
                # 重复告警应该是 duplicate
                assert record.alert_status == 'duplicate'
                assert record.alert_message is not None
                # 重复告警不设置告警人和告警时间
                assert record.alert_person is None
                assert record.alert_time is None
            else:
                # 首次告警应该是 sent
                assert record.alert_status == 'sent'
                assert record.alert_message is not None
                assert record.alert_person == 'system'
                assert record.alert_time is not None
                
                # 验证告警消息格式
                expected_message = manager._format_alert_message(
                    account_id, hit_time, [model_def.model_name], has_control=model_def.is_acct_control
                )
                assert record.alert_message == expected_message

    @given(
        account_id=account_id_strategy,
        hit_models=hit_models_strategy,
        indicator_data=indicator_data_strategy,
        hit_time=hit_time_strategy,
        is_acct_control=st.booleans(),
        is_duplicate=st.booleans()
    )
    @settings(max_examples=100)
    def test_property_9_control_status_setting_correctness(
        self, manager, db_session, account_id, hit_models, indicator_data, hit_time, is_acct_control, is_duplicate
    ):
        """
        **Feature: model-execution-tracking, Property 9: 管控状态设置正确性**
        **Validates: Requirements 2.5**
        
        对于任何管控处理，系统应当根据模型配置和历史记录正确设置control_status：
        未配置管控的模型为'not_configured'，首次管控为'executed'，重复管控为'duplicate'
        """
        # 为每个模型创建模型定义
        model_definitions = []
        for model in hit_models:
            model_def = FraudHunterModelDefinition(
                id=model.model_id,
                model_code=f"MODEL_{model.model_id}",
                model_name=model.model_name,
                description="Test model",
                is_send_alert_message=False,
                is_acct_control=is_acct_control,
                rule_config={"rules": []},
                status="online"
            )
            db_session.add(model_def)
            model_definitions.append(model_def)
        
        db_session.flush()
        
        # 如果需要模拟重复管控，先创建一条历史记录
        if is_duplicate and is_acct_control:
            # 创建历史命中记录
            historical_hit = manager.create_hit_record(account_id, hit_models, indicator_data, hit_time)
            historical_alerts = manager.hit_record_processor(historical_hit)
            db_session.commit()
        
        # 创建新的命中记录
        hit_record = manager.create_hit_record(account_id, hit_models, indicator_data, hit_time)
        
        # 处理命中记录生成告警管控记录
        alert_control_records = manager.hit_record_processor(hit_record)
        
        # 验证管控状态设置正确性
        for i, record in enumerate(alert_control_records):
            model_def = model_definitions[i]
            
            if not model_def.is_acct_control:
                # 未配置管控的模型应该是 not_configured
                assert record.control_status == 'not_configured'
                assert record.control_time is None
                assert record.control_serial_number is None
            elif is_duplicate and is_acct_control:
                # 重复管控应该是 duplicate
                assert record.control_status == 'duplicate'
                # 重复管控不设置管控时间和流水号
                assert record.control_time is None
                assert record.control_serial_number is None
            else:
                # 首次管控应该是 executed
                assert record.control_status == 'executed'
                assert record.control_time is not None
                assert record.control_serial_number is not None
                
                # 验证管控流水号格式（应该以CTRL开头）
                assert record.control_serial_number.startswith('CTRL')
                assert len(record.control_serial_number) == 18  # CTRL + 14位时间戳

    @given(
        records_data=st.lists(
            st.tuples(
                account_id_strategy,
                hit_models_strategy,
                indicator_data_strategy,
                hit_time_strategy
            ),
            min_size=1,
            max_size=20
        ),
        filters=st.builds(
            AlertControlFilters,
            start_date=st.one_of(st.none(), st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))),
            end_date=st.one_of(st.none(), st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))),
            account_id=st.one_of(st.none(), account_id_strategy),
            model_id=st.one_of(st.none(), st.integers(min_value=1, max_value=1000)),
            alert_status=st.one_of(st.none(), st.sampled_from(['not_configured', 'sent', 'duplicate'])),
            control_status=st.one_of(st.none(), st.sampled_from(['not_configured', 'executed', 'duplicate'])),
            search=st.one_of(st.none(), st.text(min_size=1, max_size=20))
        ),
        pagination=st.builds(
            PaginationParams,
            page=st.integers(min_value=1, max_value=10),
            page_size=st.integers(min_value=1, max_value=50)
        )
    )
    @settings(max_examples=100)
    def test_property_10_query_filter_result_correctness(
        self, manager, db_session, records_data, filters, pagination
    ):
        """
        **Feature: model-execution-tracking, Property 10: 查询筛选结果正确性**
        **Validates: Requirements 3.2, 4.2**
        
        对于任何筛选条件（日期范围、账号、模型），查询结果应当只包含满足所有筛选条件的记录
        """
        # 创建测试数据
        created_records = []
        for account_id, hit_models, indicator_data, hit_time in records_data:
            # 为模型创建定义
            for model in hit_models:
                existing_model = db_session.query(FraudHunterModelDefinition).filter(
                    FraudHunterModelDefinition.id == model.model_id
                ).first()
                
                if not existing_model:
                    model_def = FraudHunterModelDefinition(
                        id=model.model_id,
                        model_code=f"MODEL_{model.model_id}",
                        model_name=model.model_name,
                        description="Test model",
                        is_send_alert_message=True,
                        is_acct_control=False,
                        rule_config={"rules": []},
                        status="online"
                    )
                    db_session.add(model_def)
            
            db_session.flush()
            
            # 创建命中记录和告警管控记录
            hit_record = manager.create_hit_record(account_id, hit_models, indicator_data, hit_time)
            alert_records = manager.hit_record_processor(hit_record)
            created_records.extend(alert_records)
        
        db_session.commit()
        
        # 执行查询
        result = manager.get_alert_control_records(filters, pagination)
        
        # 验证分页信息
        assert result.page == pagination.page
        assert result.page_size == pagination.page_size
        assert len(result.records) <= pagination.page_size
        
        # 验证每条返回的记录都满足筛选条件
        for record_response in result.records:
            # 从数据库获取完整记录进行验证
            db_record = db_session.query(FraudHunterAlertControlRecord).filter(
                FraudHunterAlertControlRecord.id == record_response.id
            ).first()
            
            assert db_record is not None
            
            # 验证日期范围筛选
            if filters.start_date:
                assert db_record.record_date >= filters.start_date
            if filters.end_date:
                assert db_record.record_date <= filters.end_date
            
            # 验证账号筛选
            if filters.account_id:
                assert db_record.account_id == filters.account_id
            
            # 验证模型筛选
            if filters.model_id:
                assert db_record.model_id == filters.model_id
            if filters.model_name:
                assert filters.model_name in db_record.model_name
            
            # 验证状态筛选
            if filters.alert_status:
                assert db_record.alert_status == filters.alert_status
            if filters.control_status:
                assert db_record.control_status == filters.control_status
            
            # 验证搜索关键词
            if filters.search:
                search_match = (
                    filters.search in db_record.account_id or
                    filters.search in db_record.model_name or
                    (db_record.alert_message and filters.search in db_record.alert_message)
                )
                assert search_match
        
        # 验证总数计算正确性
        # 手动计算符合条件的记录数
        manual_query = db_session.query(FraudHunterAlertControlRecord)
        manual_query = manager._apply_filters(manual_query, filters)
        expected_total = manual_query.count()
        
        assert result.total == expected_total
        
        # 验证总页数计算正确性
        expected_total_pages = (expected_total + pagination.page_size - 1) // pagination.page_size
        assert result.total_pages == expected_total_pages

    @given(
        account_id=account_id_strategy,
        hit_models=hit_models_strategy,
        indicator_data=indicator_data_strategy,
        hit_time=hit_time_strategy
    )
    @settings(max_examples=100)
    def test_property_11_record_detail_data_completeness(
        self, manager, db_session, account_id, hit_models, indicator_data, hit_time
    ):
        """
        **Feature: model-execution-tracking, Property 11: 记录详情数据完整性**
        **Validates: Requirements 3.3, 4.3, 4.4**
        
        对于任何命中记录或告警管控记录，详情查询应当返回该记录的所有字段信息
        """
        # 为模型创建定义
        for model in hit_models:
            model_def = FraudHunterModelDefinition(
                id=model.model_id,
                model_code=f"MODEL_{model.model_id}",
                model_name=model.model_name,
                description="Test model",
                is_send_alert_message=True,
                is_acct_control=True,
                rule_config={"rules": []},
                status="online"
            )
            db_session.add(model_def)
        
        db_session.flush()
        
        # 创建命中记录和告警管控记录
        hit_record = manager.create_hit_record(account_id, hit_models, indicator_data, hit_time)
        alert_records = manager.hit_record_processor(hit_record)
        db_session.commit()
        
        # 获取第一条告警管控记录的详情
        alert_record = alert_records[0]
        detail_response = manager.get_alert_control_record_detail(alert_record.id)
        
        # 验证详情响应不为空
        assert detail_response is not None
        
        # 验证告警管控记录的所有字段
        record_response = detail_response.record
        assert record_response.id == alert_record.id
        assert record_response.hit_record_id == alert_record.hit_record_id
        assert record_response.account_id == alert_record.account_id
        assert record_response.record_date == alert_record.record_date
        assert record_response.model_id == alert_record.model_id
        assert record_response.model_name == alert_record.model_name
        assert record_response.alert_status == alert_record.alert_status
        assert record_response.alert_message == alert_record.alert_message
        assert record_response.alert_person == alert_record.alert_person
        assert record_response.alert_time == alert_record.alert_time
        assert record_response.control_status == alert_record.control_status
        assert record_response.control_time == alert_record.control_time
        assert record_response.control_serial_number == alert_record.control_serial_number
        assert record_response.created_at == alert_record.created_at
        assert record_response.updated_at == alert_record.updated_at
        
        # 验证关联的命中记录的所有字段
        hit_response = detail_response.hit_record
        assert hit_response.id == hit_record.id
        assert hit_response.account_id == hit_record.account_id
        assert hit_response.hit_time == hit_record.hit_time
        assert hit_response.hit_model_ids == hit_record.hit_model_ids
        assert hit_response.hit_model_names == hit_record.hit_model_names
        assert hit_response.indicator_data == hit_record.indicator_data
        assert hit_response.created_at == hit_record.created_at
        assert hit_response.updated_at == hit_record.updated_at

    @given(
        records_data=st.lists(
            st.tuples(
                account_id_strategy,
                hit_models_strategy,
                indicator_data_strategy,
                hit_time_strategy
            ),
            min_size=1,
            max_size=10
        ),
        filters=st.builds(
            AlertControlFilters,
            start_date=st.one_of(st.none(), st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))),
            end_date=st.one_of(st.none(), st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))),
            account_id=st.one_of(st.none(), account_id_strategy)
        ),
        export_format=st.sampled_from(['csv', 'excel'])
    )
    @settings(max_examples=100)
    def test_property_12_data_export_content_consistency(
        self, manager, db_session, records_data, filters, export_format
    ):
        """
        **Feature: model-execution-tracking, Property 12: 数据导出内容一致性**
        **Validates: Requirements 3.4**
        
        对于任何导出请求，导出的数据内容应当与查询结果保持一致
        """
        # 创建测试数据
        for account_id, hit_models, indicator_data, hit_time in records_data:
            # 为模型创建定义
            for model in hit_models:
                existing_model = db_session.query(FraudHunterModelDefinition).filter(
                    FraudHunterModelDefinition.id == model.model_id
                ).first()
                
                if not existing_model:
                    model_def = FraudHunterModelDefinition(
                        id=model.model_id,
                        model_code=f"MODEL_{model.model_id}",
                        model_name=model.model_name,
                        description="Test model",
                        is_send_alert_message=True,
                        is_acct_control=False,
                        rule_config={"rules": []},
                        status="online"
                    )
                    db_session.add(model_def)
            
            db_session.flush()
            
            # 创建命中记录和告警管控记录
            hit_record = manager.create_hit_record(account_id, hit_models, indicator_data, hit_time)
            manager.hit_record_processor(hit_record)
        
        db_session.commit()
        
        # 获取查询结果
        pagination = PaginationParams(page=1, page_size=1000)  # 获取所有记录
        query_result = manager.get_alert_control_records(filters, pagination)
        
        # 执行导出
        export_data = manager.export_alert_control_records(filters, export_format)
        
        # 验证导出数据不为空（如果有查询结果的话）
        if query_result.total > 0:
            assert len(export_data) > 0
        
        # 验证导出格式正确
        if export_format == 'csv':
            # CSV应该是UTF-8编码的字节数据
            assert isinstance(export_data, bytes)
            # 尝试解码验证格式
            csv_content = export_data.decode('utf-8-sig')
            assert len(csv_content) > 0
            if query_result.total > 0:
                # 应该包含表头
                assert 'ID' in csv_content
                assert '账号' in csv_content
        else:  # excel
            # Excel应该是字节数据
            assert isinstance(export_data, bytes)
            assert len(export_data) > 0
        
        # 验证导出的记录数量与查询结果一致
        # 这里我们通过手动查询来验证一致性
        manual_query = db_session.query(FraudHunterAlertControlRecord)
        manual_query = manager._apply_filters(manual_query, filters)
        expected_count = manual_query.count()
        
        # 对于CSV，我们可以计算行数来验证
        if export_format == 'csv' and expected_count > 0:
            csv_content = export_data.decode('utf-8-sig')
            lines = csv_content.strip().split('\n')
            # 减去表头行
            data_lines = len(lines) - 1
            assert data_lines == expected_count

    @given(
        records_data=st.lists(
            st.tuples(
                account_id_strategy,
                hit_models_strategy,
                indicator_data_strategy,
                hit_time_strategy
            ),
            min_size=5,
            max_size=50
        ),
        page_size=st.integers(min_value=1, max_value=10),
        page=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100)
    def test_property_13_pagination_logic_correctness(
        self, manager, db_session, records_data, page_size, page
    ):
        """
        **Feature: model-execution-tracking, Property 13: 分页逻辑正确性**
        **Validates: Requirements 3.5**
        
        对于任何分页参数，返回的记录数量应当不超过页面大小，且总记录数应当等于所有页面记录数之和
        """
        # 创建测试数据
        total_created = 0
        for account_id, hit_models, indicator_data, hit_time in records_data:
            # 为模型创建定义
            for model in hit_models:
                existing_model = db_session.query(FraudHunterModelDefinition).filter(
                    FraudHunterModelDefinition.id == model.model_id
                ).first()
                
                if not existing_model:
                    model_def = FraudHunterModelDefinition(
                        id=model.model_id,
                        model_code=f"MODEL_{model.model_id}",
                        model_name=model.model_name,
                        description="Test model",
                        is_send_alert_message=True,
                        is_acct_control=False,
                        rule_config={"rules": []},
                        status="online"
                    )
                    db_session.add(model_def)
            
            db_session.flush()
            
            # 创建命中记录和告警管控记录
            hit_record = manager.create_hit_record(account_id, hit_models, indicator_data, hit_time)
            alert_records = manager.hit_record_processor(hit_record)
            total_created += len(alert_records)
        
        db_session.commit()
        
        # 测试分页逻辑
        filters = AlertControlFilters()  # 无筛选条件，获取所有记录
        pagination = PaginationParams(page=page, page_size=page_size)
        
        result = manager.get_alert_control_records(filters, pagination)
        
        # 验证返回的记录数量不超过页面大小
        assert len(result.records) <= page_size
        
        # 验证分页信息正确
        assert result.page == page
        assert result.page_size == page_size
        assert result.total == total_created
        
        # 验证总页数计算正确
        expected_total_pages = (total_created + page_size - 1) // page_size
        assert result.total_pages == expected_total_pages
        
        # 如果请求的页面超出范围，应该返回空结果
        if page > expected_total_pages:
            assert len(result.records) == 0
        else:
            # 验证当前页的记录数量
            if page < expected_total_pages:
                # 非最后一页应该返回完整的页面大小
                assert len(result.records) == page_size
            else:
                # 最后一页可能不满页面大小
                expected_last_page_size = total_created - (page - 1) * page_size
                assert len(result.records) == expected_last_page_size
        
        # 验证所有页面记录数之和等于总记录数
        all_records = []
        current_page = 1
        while True:
            page_pagination = PaginationParams(page=current_page, page_size=page_size)
            page_result = manager.get_alert_control_records(filters, page_pagination)
            
            if not page_result.records:
                break
                
            all_records.extend(page_result.records)
            current_page += 1
            
            # 防止无限循环
            if current_page > 100:
                break
        
        # 验证所有页面的记录总数等于总记录数
        assert len(all_records) == total_created
        
        # 验证记录ID的唯一性（确保没有重复）
        record_ids = [record.id for record in all_records]
        assert len(set(record_ids)) == len(record_ids)


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