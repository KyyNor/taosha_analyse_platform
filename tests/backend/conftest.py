"""
tests/backend/conftest.py
=========================
全局 pytest fixtures，为所有后端单元测试提供统一的 Mock 依赖基础设施。

测试覆盖范围约定：
- 所有 fixture 均以 @pytest.fixture 提供，无需真实 DB/API/外部系统
- 典型的 Mock 对象：SQLAlchemy Session、requests.Session、AnalyzeDBConnector
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest

# ── 将 backend 加入 import path，方便直接从 services.* / schemas.* 导入 ──
_backend_root = Path(__file__).parents[3] / "backend"
sys.path.insert(0, str(_backend_root))


# ============================================================================
# 1. SQLAlchemy Mock Session
# ============================================================================

@pytest.fixture
def mock_db_session():
    """
    返回一个完全可控的 MagicMock[Session]，可用于：
    - 覆盖 query()/filter()/first()/all() 等返回值
    - 验证 add/commit/rollback 调用次数
    """
    session = MagicMock(name="mock_db_session")
    # 常见的链式调用默认返回空列表（列表查询）或 None（单条查询）
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    return session


# ============================================================================
# 2. 告警通知目标 Repository（用于通知合并测试）
# ============================================================================

@pytest.fixture
def mock_notify_repository(mock_db_session):
    """
    返回一个符合 INotifyTargetRepository 协议的 Fake，实现：

    - acct_assign_targets: Dict[acct_no -> List[notice_no]]
    - cust_owner_targets : Dict[cust_no -> List[notice_no]]
    """
    targets = MagicMock(name="mock_notify_repository")
    # 默认空数据，子测试中可通过 override 预设数据
    targets.lookup_acct_assign.return_value = []
    targets.lookup_cust_owner.return_value = []
    return targets


# ============================================================================
# 3. HTTP Client Mock（用于 send_alert_message Mock）
# ============================================================================

@pytest.fixture
def mock_requests_post():
    """
    Mock requests.post，注入到 ModelHitAlertManager.send_alert_message()。
    默认返回成功响应 {"respCode": "00000"}。
    """
    import requests

    with patch.object(requests, "post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"respCode": "00000", "message": "success"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        yield mock_post


# =============================================================================
# 4. Pydantic Schema 实例 Factories（避免每个测试重复构造）
# =============================================================================

@pytest.fixture
def sample_trend_request_factory():
    """提供合法的 TrendRequest 默认实例，用于 get_history_trend 校验测试。"""
    from schemas.fraudhunter.alert_control_record import TrendRequest

    def make(
        start_date: str = "2024-01-01",
        end_date: str = "2024-01-07",
        granularity: str = "day",
        model_ids=None,
    ):
        return TrendRequest(
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            model_ids=model_ids,
        )

    return make


@pytest.fixture
def sample_cardbin_request_factory():
    """提供合法的 ProvinceCardBinRequest 实例。"""
    from api.endpoint_models import ProvinceCardBinRequest

    def make(
        card_bin: str = "622202",
        bank_name: str = "中国工商银行",
        province: str = "北京市",
        city: str = "北京市",
    ):
        return ProvinceCardBinRequest(
            card_bin=card_bin,
            bank_name=bank_name,
            province=province,
            city=city,
        )

    return make


@pytest.fixture
def sample_risk_control_model_create_factory():
    """提供合法的 RiskControlModelCreate 实例。"""
    from schemas.fraudhunter.risk_control_model import RiskControlModelCreate

    def make(
        is_send_alert_message: bool = True,
        is_send_financial_manager_alert: bool = False,
        **kwargs,
    ):
        return RiskControlModelCreate(
            is_send_alert_message=is_send_alert_message,
            is_send_financial_manager_alert=is_send_financial_manager_alert,
            **kwargs,
        )

    return make


# =============================================================================
# 5. 辅助工具
# =============================================================================

def patch.object(*args, **kwargs):
    """from unittest.mock import patch（避免文件顶部重复导入）"""
    from unittest.mock import patch as _patch

    return _patch.object(*args, **kwargs)


# =============================================================================
# 6. AnalyzeDBConnector 补丁（用于实时指标半小时间隔测试）
# =============================================================================

@pytest.fixture
def mock_analyze_db_connector():
    """Mock AnalyzeDBConnector.batch_insert_copy，默认返回 0 行（不影响测试断言）。"""
    from utils.analyze_db_utils import AnalyzeDBConnector

    with patch.object(AnalyzeDBConnector, "batch_insert_copy", return_value=0) as mock:
        yield mock


# =============================================================================
# 7. Settings Mock（FraudHunter 配置读取）
# =============================================================================

@pytest.fixture
def mock_settings_fraudhunter():
    """Mock fraudhunter_* 配置项。"""
    from unittest.mock import patch

    fake_settings = MagicMock()
    fake_settings.fraudhunter_alert_control_message_api_url = (
        "http://localhost:9999/mock-wx-api"
    )
    fake_settings.fraudhunter_wide_table_analyze_db_name = "test_db"

    with patch("services.fraudhunter.model_service.model_hit_alert_manager.settings", fake_settings):
        yield fake_settings


# =============================================================================
# 8. SystemConfigManager Mock（用于告警分支通知号查询）
# =============================================================================

@pytest.fixture
def mock_system_config_manager():
    """默认返回空配置的 SystemConfigManager，测试时可覆盖。"""
    mc = MagicMock(name="mock_system_config_manager")
    mc.get_global_config.return_value = None
    mc.get_branch_config.return_value = None
    return mc