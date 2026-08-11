r"""
tests/backend/modules/alert_control_record_optimization/test_alert_control_record_page.py
=====================================================================================
单元测试：对标文档用例 ACR 系列（告警管控记录页面优化）

背景说明（代码调研摘要）：
    改造内容：
    1. 模型列：从 text 转 Tag（Badge）展示
       - 数据层：FraudHunterModelAlertControlRecord.hit_model_ids (JSON)
       - 前端消费：TS接口类型 AlertControlRecord 已定义为 number[]（JS数组）
    2. 新增列：管控流水号 control_serial_number（数据库schema已存在，响应schema已透传）
    3. 详情按钮：白名单部门（110026、110004）可见（实现位置：未在后端发现硬编码，应在前端路由/权限层）

测试策略：
    ✅ 后端部分：控制 serial_number 透传 Schema（已确认存在，无需额外测试）
    ✅ 后端部分：hit_model_ids 的 JSON Array 序列化为 Python List（Pydantic 验证）
    ⚠️ 部门白名单可见性：目前未见后端硬编码，建议在前端权限层（menu/permisson）或路由层做 E2E 测试

文档用例编号覆盖：
    ACR-04/05: control_serial_number 已暴露在 schema → 可直接测
    ACR-01~03: Tag 展示为纯前端行为 → SKIP（除非模拟序列化消费）
    ACR-06~08: 详情按钮权限（前端/路由层）→ SKIP
"""

import sys
from pathlib import Path
from datetime import date, datetime

import pytest

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

from schemas.fraudhunter.alert_control_record import (
    AlertControlRecordResponse,
    AlertControlRecordDetailResponse,
)


def _record_payload(**overrides):
    """构造字段完整的 AlertControlRecordResponse 负载。"""
    timestamp = datetime(2024, 3, 15, 12, 0, 0)
    payload = {
        "id": 1,
        "hit_record_id": 1,
        "account_id": "ACC-TEST",
        "record_date": date(2024, 3, 15),
        "hit_model_ids": [],
        "hit_model_names": [],
        "alert_status": "pending",
        "control_status": "none",
        "control_serial_number": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    payload.update(overrides)
    return payload


def _hit_record_payload(**overrides):
    """构造字段完整的 HitRecordResponse 负载。"""
    timestamp = datetime(2024, 3, 15, 12, 0, 0)
    payload = {
        "id": 1,
        "account_id": "ACC-TEST",
        "hit_time": timestamp,
        "hit_model_ids": [],
        "hit_model_names": [],
        "indicator_data": {},
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    payload.update(overrides)
    return payload


# =============================================================================
# PART A — control_serial_number 透传验证（ACR-04、ACR-05）
# 后端确认：Schema 已正确定义，前端 TS 也已接入此字段，透传链路无虞
# =============================================================================

class TestControlSerialNumberExposure_ACR04_ACR05:
    """
    ACR-04：管控流水号列正常展示
    ACR-05：详情弹框中也显示流水号（同一 schema 的不同视图）
    """

    @pytest.fixture
    def sample_record_payload(self):
        """构建完整的 AlertControlRecordResponse 示例负载。"""
        return _record_payload(**{
            "id": 1,
            "hit_record_id": 2024001,
            "account_id": "ACC-12345",
            "record_date": date(2024, 3, 15),
            "hit_model_ids": [1, 2, 3],        # ← ACM-01/02/03 展示多个tag
            "hit_model_names": ["模型A", "模型B", "模型C"],
            "alert_status": "sent",
            "alert_message": "可疑交易预警",
            "alert_person": "admin",
            "alert_time": datetime(2024, 3, 15, 14, 0, 0),
            "control_status": "controlled",
            "control_time": datetime(2024, 3, 15, 14, 30, 0),
            "control_serial_number": "SN-20240315-0001",  # ← ACR-04/05 核心关注
            "created_at": datetime(2024, 3, 15, 0, 0, 0),
            "updated_at": datetime(2024, 3, 15, 14, 30, 0),
        })

    def test_acr_04_control_serial_number_in_schema(self, sample_record_payload):
        """
        ACR-04：响应 schema 中必须出现 control_serial_number 字段。
        这是后端透传的最低承诺，页面展示层基于此字段自行定制样式。
        """
        record = AlertControlRecordResponse(**sample_record_payload)
        assert record.control_serial_number == "SN-20240315-0001"
        # 确认在 dict 序列化中不丢字段
        serialized = record.model_dump()
        assert "control_serial_number" in serialized

    def test_acr_04_none_handling_graceful(self):
        """控制流水号为空时，不应崩溃（字段为 Optional）。"""
        minimal_payload = _record_payload(
            hit_record_id=1,
            account_id="ACC-001",
        )
        record = AlertControlRecordResponse(**minimal_payload)
        assert record.control_serial_number is None
        # 不应对序列化造成干扰
        assert "control_serial_number" in record.model_dump()

    def test_acr_05_detail_response_has_control_serial_number(self):
        """
        ACR-05：详情弹框使用的 schema 也应包含此字段。
        实际为同一 AlertControlRecordResponse（通用），此测试验证 DetailView 不遗漏。
        """
        detail_payload = {
            "record": _record_payload(
                id=2,
                hit_record_id=2,
                account_id="ACC-002",
                hit_model_ids=[5],
                hit_model_names=["模型X"],
                alert_status="sent",
                control_status="controlled",
                control_serial_number="SN-XYZ-001",
            ),
            "hit_record": _hit_record_payload(
                id=2,
                account_id="ACC-002",
                hit_model_ids=[5],
                hit_model_names=["模型X"],
            ),
        }
        detail = AlertControlRecordDetailResponse(**detail_payload)
        assert detail.record.control_serial_number == "SN-XYZ-001"
        # Detail schema 也应完整序列化
        assert "control_serial_number" in detail.record.model_dump()

    def test_control_serial_number_json_roundtrip(self):
        """
        序列化→反序列化 round-trip，确保 API 通信链路上不丢精度。
        """
        original = AlertControlRecordResponse(**_record_payload(
            id=99,
            hit_record_id=99,
            account_id="ACC-99",
            record_date=date(2024, 12, 31),
            hit_model_ids=[1],
            hit_model_names=["模型Z"],
            alert_status="sent",
            control_status="controlled",
            control_serial_number="SN-LONG-STRING-VALUE-20241231001",
        ))
        wire_data = original.model_dump(mode="json")
        rebuilt   = AlertControlRecordResponse(**wire_data)
        assert rebuilt.control_serial_number == original.control_serial_number


# =============================================================================
# PART B — hit_model_ids / hit_model_names Tag 展示的前置数据格式测试
# ACR-01、ACR-02、ACR-03 的后端支撑（前端实际负责渲染 Tag）
# =============================================================================

class TestModelIdsFieldForTagsRendering_ACR01_ACR02_ACR03:
    """
    ACR-01/02/03：模型列为 Tag/Badge 展示
    后端的职责是将 hit_model_ids 从 DB JSON Binary 反序列化为 Python List[int]。
    这由 Pydantic Schema 的 List[int] 类型声明和 ORM 的 JSON 列声明共同担保。
    """

    @pytest.mark.parametrize("model_ids,model_names,expected_tags", [
        ([1],       ["模型A"],                       1 ),
        ([1, 2],    ["模型A", "模型B"],              2 ),
        ([3, 7, 9], ["模型X", "模型Y", "模型Z"],     3 ),
        (list(range(50)), [f"模型{i}" for i in range(50)], 50),  # 50+模型（ACM-11场景近似）
        ([],        [],                              0 ),  # ACM-03: 模型数为零时的降级展示（前端显示占位符）
    ])
    def test_hit_model_ids_deserializable_as_int_array(
        self, model_ids, model_names, expected_tags
    ):
        """
        后端 Schema 必须能接受整数数组（前端才能遍历生成对应数量的 Tag）。
        此测试覆盖单标签、多标签、空标签（含降级兜底）场景。
        """
        payload = _record_payload(
            hit_model_ids=model_ids,
            hit_model_names=model_names,
        )
        record = AlertControlRecordResponse(**payload)
        assert record.hit_model_ids == model_ids
        assert len(record.hit_model_ids) == expected_tags
        assert record.hit_model_names == model_names

    def test_acr_03_zero_models_falls_back_to_placeholder_text(self):
        """
        ACR-03：当模型列为空时，前端应展示灰色占位符 `-` 而非崩溃。

        后端不直接控制前端展示，但通过确保空数组时不抛异常来间接保证此行为。
        （若后端在空数组时抛 MissingAttribute Error，那前端才真正崩溃。）
        """
        payload = _record_payload(
            hit_model_ids=[],
            hit_model_names=[],
            alert_status="none",
        )
        # 空数组不抛异常，是后端对前端的最低保障合约
        record = AlertControlRecordResponse(**payload)
        assert record.hit_model_ids == []
        assert record.hit_model_names == []


# =============================================================================
# PART C — Excel导出字段（ACR-08）的 Schema 覆盖
# 后端的职责：在 AlertControlRecordResponse（含所有字段）之上，
# Excel Exporter 工具遍历 model_dump() 所有 key，control_serial_number 已在其列
# =============================================================================

class TestExcelExportContract_ACR08:
    """ACR-08: Excel导出手动触发后，控制流水号应存在于导出文件的列头。"""

    def test_acr_08_serial_number_in_serialized_keys(self):
        """
        模拟 Exporter 读取 schema 的所有 key 生成 Excel 列头。
        control_serial_number 必须在字段列表中，这是后端对Exporter的最低合约。
        """
        record = AlertControlRecordResponse(**_record_payload(
            account_id="ACC-E2E",
            hit_model_ids=[1],
            hit_model_names=["TestModel"],
            alert_status="sent",
            control_status="controlled",
            control_serial_number="SN-FULL-STACK-EXPORT-TEST",
        ))
        exported_dict = record.model_dump()
        keys = list(exported_dict.keys())
        assert "control_serial_number" in keys, \
            f"'control_serial_number' 未出现在导出的列头列表中（现有key：{keys}）"
        assert "hit_model_ids" in keys  # 模型ID也应为导出列之一（用于导出生成Tag）
        assert "hit_model_names" in keys


# =============================================================================
# ⛔ 纯前端/路由层：部门可见性（ACR-06、ACR-07）→ SKIP
# =============================================================================

class TestDepartmentVisibilitySkipped_ACR06_ACR07:
    """
    ACR-06: 详情按钮：白名单部门（110026、110004）可见
    ACR-07: 详情按钮：非白名单部门不可见

    调研结论：
        经全面搜索 `backend/` 和 `frontend/app/(main)/fraudhunter/alert-control-records/`，
        未发现后端存在 `110026` / `110004` 的硬编码判断逻辑。
        很可能由前端的菜单权限系统（MenuPermission）或路由守卫（Route Guard）控制。

    因此该用例的测试应在 E2E 层面（Playwright）覆盖，
    具体做法：以不同部门账号登录，断言按钮 DOM 显示/hidden 状态。
    （相关 E2E 测试用例建议写在 tests/e2e/alert_control_record_permission.spec.ts 中）
    """

    @pytest.mark.skip(reason=(
        "ACR-06/07: 详情按钮的部门白名单可见性控制应在前端路由/菜单权限层实现，"
        "后端无硬编码部门判断逻辑。建议使用 Playwright E2E 测试："
        "login(user: dept=110026) → assert btn.visible();"
        "login(user: dept=999999) → assert !btn.exists()"
    ))
    def test_acr_06_white_department_can_see_detail_button(self):
        pass

    @pytest.mark.skip(reason=(
        "ACR-07: 非白名单部门的普通柜员应看不到详情按钮（按钮组件不渲染）"
    ))
    def test_acr_07_regular_teller_cannot_see_detail_button(self):
        pass
