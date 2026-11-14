"""
tests/backend/modules/account_hit_count/test_account_hit_count.py
=================================================================
单元测试：账号近30天命中次数（issue #17）+ 白名单状态筛选 400 修复

被测代码：
    backend/services/fraudhunter/model_service/model_hit_alert_manager.py
        - get_account_recent_hit_counts()  批量聚合统计
        - get_alert_control_record_detail()  详情附带 recent_hit_count
    backend/api/fraudhunter/alert_control_record_routes.py
        - POST /account-hit-counts  批量端点
        - 列表/导出路由的状态校验（whitelist 不再 400）
    backend/schemas/fraudhunter/alert_control_record.py
        - AccountHitCountsRequest / AccountHitCountsResponse
        - AlertControlRecordDetailResponse.recent_hit_count

统计口径（与实现约定一致）：
    - 滚动30天窗口（含今天），按 record_date 过滤
    - 仅统计 control_status='executed'（duplicate/not_configured/whitelist 不计入）
    - 窗口内无记录返回 0；统计失败返回 null（区别于 0）

测试策略：
    ✅ 聚合口径 → SQLite 内存库真实执行 GROUP BY（无外部 IO）
    ✅ 详情字段 / 失败降级 → SQLite + patch
    ✅ 请求契约 / 路由状态校验 → Pydantic + Mock manager
"""

import asyncio
import atexit
import itertools
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

# utils.config 模块底部有全局单例，import 时要求 backend/config/config.yaml 存在（已gitignore）。
# 本地缺失时临时创建，测试结束恢复（与 pg_partition_export 测试同款兜底）。
_default_config_yaml = _backend_root / "config" / "config.yaml"
_created_default_config = False
if not _default_config_yaml.exists():
    _default_config_yaml.write_text("app:\n  name: taosha-test\n", encoding="utf-8")
    _created_default_config = True


def _cleanup_default_config():
    if _created_default_config:
        try:
            _default_config_yaml.unlink()
        except OSError:
            pass


atexit.register(_cleanup_default_config)

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from models.fraudhunter.model_execution_tracking import (  # noqa: E402
    FraudHunterModelAlertControlRecord,
    FraudHunterModelHitRecord,
)
from services.fraudhunter.model_service.model_hit_alert_manager import (  # noqa: E402
    ModelHitAlertManager,
)
from schemas.fraudhunter.alert_control_record import (  # noqa: E402
    AccountHitCountsRequest,
    AlertControlListRequest,
    AlertControlExportRequest,
)
from api.fraudhunter import alert_control_record_routes as routes  # noqa: E402


# =============================================================================
# Fixtures 与构造辅助
# =============================================================================

@pytest.fixture
def db_session():
    """SQLite 内存库，仅建命中/告警管控两张表（显式主键，避开 BigInteger 自增差异）。"""
    engine = create_engine("sqlite://")
    FraudHunterModelHitRecord.__table__.create(engine)
    FraudHunterModelAlertControlRecord.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def manager(db_session, mock_settings_fraudhunter):
    return ModelHitAlertManager(db_session)


_ids = itertools.count(1)


def _add_alert_record(
    db,
    account_id: str,
    record_date: date,
    control_status: str = "executed",
    alert_status: str = "sent",
    created_at: datetime = None,
):
    now = created_at or datetime.now()
    record = FraudHunterModelAlertControlRecord(
        id=next(_ids),
        execution_id=1,
        hit_record_id=next(_ids),
        account_id=account_id,
        record_date=record_date,
        branch_no="1100",
        hit_model_ids=[1],
        hit_model_names=["模型A"],
        alert_status=alert_status,
        control_status=control_status,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    db.commit()
    return record


def _add_hit_record(db, account_id: str, hit_time: datetime):
    record = FraudHunterModelHitRecord(
        id=next(_ids),
        execution_id=1,
        account_id=account_id,
        branch_no="1100",
        hit_time=hit_time,
        hit_model_ids=[1],
        hit_model_names=["模型A"],
        indicator_data={},
    )
    db.add(record)
    db.commit()
    return record


# =============================================================================
# PART A — 聚合口径（SQLite 真实 GROUP BY）
# =============================================================================

@pytest.mark.ahc
class TestRecentHitCountAggregation:

    def test_only_executed_counted(self, manager, db_session):
        """仅 executed 计入；duplicate/not_configured/whitelist 不计入。"""
        today = date.today()
        _add_alert_record(db_session, "ACC-A", today, control_status="executed")
        _add_alert_record(db_session, "ACC-A", today, control_status="executed")
        _add_alert_record(db_session, "ACC-A", today, control_status="duplicate")
        _add_alert_record(db_session, "ACC-A", today, control_status="not_configured")
        _add_alert_record(db_session, "ACC-A", today, control_status="whitelist",
                          alert_status="whitelist")

        counts = manager.get_account_recent_hit_counts(["ACC-A"])
        assert counts == {"ACC-A": 2}

    def test_no_history_returns_zero(self, manager, db_session):
        """无历史记录的账号返回 0（而非缺失键）。"""
        _add_alert_record(db_session, "ACC-OTHER", date.today())
        counts = manager.get_account_recent_hit_counts(["ACC-EMPTY"])
        assert counts == {"ACC-EMPTY": 0}

    def test_window_boundary_inclusive_30_days(self, manager, db_session):
        """窗口为含今天的30天：today-29 计入，today-30 不计入。"""
        today = date.today()
        _add_alert_record(db_session, "ACC-B", today - timedelta(days=29))
        _add_alert_record(db_session, "ACC-B", today - timedelta(days=30))
        _add_alert_record(db_session, "ACC-B", today)

        counts = manager.get_account_recent_hit_counts(["ACC-B"])
        assert counts == {"ACC-B": 2}

    def test_backfill_judged_by_record_date_not_created_at(self, manager, db_session):
        """补录场景：按业务日期 record_date 判定，而非入库时间 created_at。"""
        today = date.today()
        # 晚到补录：业务日期在窗口内，入库时间是现在 → 计入
        _add_alert_record(db_session, "ACC-C", today - timedelta(days=5),
                          created_at=datetime.now())
        # 历史数据重刷：业务日期在窗口外，入库时间是现在 → 不计入
        _add_alert_record(db_session, "ACC-C", today - timedelta(days=40),
                          created_at=datetime.now())

        counts = manager.get_account_recent_hit_counts(["ACC-C"])
        assert counts == {"ACC-C": 1}

    def test_batch_covers_multiple_accounts_and_dedupes_input(self, manager, db_session):
        """一次查询覆盖多账号；入参重复账号去重；无记录账号补 0。"""
        today = date.today()
        _add_alert_record(db_session, "ACC-X", today)
        _add_alert_record(db_session, "ACC-X", today - timedelta(days=1))
        _add_alert_record(db_session, "ACC-Y", today)

        counts = manager.get_account_recent_hit_counts(["ACC-X", "ACC-X", "ACC-Y", "ACC-Z"])
        assert counts == {"ACC-X": 2, "ACC-Y": 1, "ACC-Z": 0}

    def test_empty_input_returns_empty_dict(self, manager):
        assert manager.get_account_recent_hit_counts([]) == {}

    def test_current_hit_included(self, manager, db_session):
        """当前这次命中（executed）本身计入，最小显示值为 1。"""
        _add_alert_record(db_session, "ACC-NEW", date.today())
        counts = manager.get_account_recent_hit_counts(["ACC-NEW"])
        assert counts == {"ACC-NEW": 1}


# =============================================================================
# PART B — 详情接口附带 recent_hit_count
# =============================================================================

@pytest.mark.ahc
class TestDetailRecentHitCount:

    def _prepare_detail(self, db_session, account_id="ACC-D"):
        hit = _add_hit_record(db_session, account_id, datetime.now())
        alert = _add_alert_record(db_session, account_id, date.today())
        alert.hit_record_id = hit.id
        db_session.commit()
        return alert

    def test_detail_includes_recent_hit_count(self, manager, db_session):
        alert = self._prepare_detail(db_session)
        # 窗口内另有 2 次 executed 命中
        _add_alert_record(db_session, alert.account_id, date.today() - timedelta(days=3))
        _add_alert_record(db_session, alert.account_id, date.today() - timedelta(days=10))
        # 窗口外不计入
        _add_alert_record(db_session, alert.account_id, date.today() - timedelta(days=45))

        detail = manager.get_alert_control_record_detail(alert.id)
        assert detail is not None
        assert detail.recent_hit_count == 3

    def test_detail_count_failure_returns_none_not_zero(self, manager, db_session):
        """统计查询异常时 recent_hit_count 为 null，详情主体仍正常返回。"""
        alert = self._prepare_detail(db_session)
        with patch.object(
            manager, "get_account_recent_hit_counts",
            side_effect=RuntimeError("db down"),
        ):
            detail = manager.get_alert_control_record_detail(alert.id)
        assert detail is not None
        assert detail.recent_hit_count is None
        assert detail.record.id == alert.id


# =============================================================================
# PART C — 批量端点与请求契约
# =============================================================================

@pytest.mark.ahc
class TestAccountHitCountsEndpoint:

    @pytest.fixture
    def http_client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from middleware import auth_middleware
        from services.token_service import TokenService, UserInfo

        app = FastAPI()
        app.include_router(routes.router)
        app.dependency_overrides[routes.get_db] = lambda: MagicMock()
        token_service = TokenService(secret_key="account-hit-count-auth-regression-test-key")
        user = UserInfo(
            user_id="test-user", user_name="测试用户", branch_no="1100",
            branch_name="测试机构", role_id_list=["测试角色"], access_time=datetime.now(),
        )
        tokens = {
            "valid": token_service.generate_token(user),
            "expired": TokenService(
                secret_key=token_service.secret_key, token_expire_hours=-1,
            ).generate_token(user),
        }
        with (
            patch.object(auth_middleware, "get_token_service", return_value=token_service),
            patch.object(auth_middleware, "get_db_session"),
            patch.object(routes, "ModelHitAlertManager") as manager_cls,
            TestClient(app) as client,
        ):
            manager = manager_cls.return_value
            manager.get_account_recent_hit_counts.return_value = {"ACC-E": 2}
            yield client, manager_cls, tokens

    @pytest.mark.parametrize("auth", ["missing", "malformed", "invalid", "expired"])
    def test_http_rejects_unauthenticated_requests(self, http_client, auth):
        client, manager_cls, tokens = http_client
        headers = {
            "missing": {},
            "malformed": {"Authorization": "Basic invalid"},
            "invalid": {"Authorization": "Bearer invalid"},
            "expired": {"Authorization": f"Bearer {tokens['expired']}"},
        }[auth]
        response = client.post(
            "/alert-control-records/account-hit-counts",
            json={"account_ids": ["ACC-E"]}, headers=headers,
        )
        assert response.status_code == 401
        manager_cls.assert_not_called()

    def test_http_authenticated_request_returns_counts(self, http_client):
        client, manager_cls, tokens = http_client
        response = client.post(
            "/alert-control-records/account-hit-counts",
            json={"account_ids": ["ACC-E"]},
            headers={"Authorization": f"Bearer {tokens['valid']}"},
        )
        assert response.status_code == 200
        assert response.json() == {"counts": {"ACC-E": 2}}
        manager_cls.return_value.get_account_recent_hit_counts.assert_called_once_with(["ACC-E"])

    @pytest.mark.parametrize("size", [0, 501])
    def test_request_rejects_empty_or_oversized(self, size):
        with pytest.raises(ValueError):
            AccountHitCountsRequest(account_ids=["ACC"] * size)

    def test_request_accepts_up_to_500(self):
        req = AccountHitCountsRequest(account_ids=["ACC"] * 500)
        assert len(req.account_ids) == 500

    def test_endpoint_returns_counts(self, db_session, mock_settings_fraudhunter):
        _add_alert_record(db_session, "ACC-E", date.today())
        body = AccountHitCountsRequest(account_ids=["ACC-E", "ACC-NONE"])
        resp = asyncio.run(routes.get_account_hit_counts(body, db=db_session))
        assert resp.counts == {"ACC-E": 1, "ACC-NONE": 0}

    def test_endpoint_failure_returns_500(self, mock_settings_fraudhunter):
        from fastapi import HTTPException

        broken_db = MagicMock()
        broken_db.query.side_effect = RuntimeError("db down")
        body = AccountHitCountsRequest(account_ids=["ACC-E"])
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(routes.get_account_hit_counts(body, db=broken_db))
        assert exc_info.value.status_code == 500


# =============================================================================
# PART D — 白名单状态筛选不再 400（列表/导出）
# =============================================================================

@pytest.mark.ahc
class TestWhitelistStatusFilter:

    @pytest.mark.parametrize("field", ["alert_status", "control_status"])
    def test_list_accepts_whitelist(self, field):
        body = AlertControlListRequest(**{field: "whitelist"})
        with patch.object(routes, "ModelHitAlertManager") as mock_manager_cls:
            mock_manager_cls.return_value.get_alert_control_records.return_value = MagicMock()
            asyncio.run(routes.list_alert_control_records(
                body=body, current_user=MagicMock(), db=MagicMock(),
            ))
        mock_manager_cls.return_value.get_alert_control_records.assert_called_once()

    @pytest.mark.parametrize("field", ["alert_status", "control_status"])
    def test_export_accepts_whitelist(self, field):
        body = AlertControlExportRequest(**{field: "whitelist"})
        with patch.object(routes, "ModelHitAlertManager") as mock_manager_cls:
            mock_manager_cls.return_value.export_alert_control_records.return_value = b"xlsx"
            asyncio.run(routes.export_alert_control_records(
                body=body, current_user=MagicMock(), db=MagicMock(),
            ))
        mock_manager_cls.return_value.export_alert_control_records.assert_called_once()

    @pytest.mark.parametrize("field", ["alert_status", "control_status"])
    def test_invalid_status_still_rejected(self, field):
        from fastapi import HTTPException

        body = AlertControlListRequest(**{field: "bogus_status"})
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(routes.list_alert_control_records(
                body=body, current_user=MagicMock(), db=MagicMock(),
            ))
        assert exc_info.value.status_code == 400
