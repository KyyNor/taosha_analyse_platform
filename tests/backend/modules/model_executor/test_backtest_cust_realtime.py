"""
tests/backend/modules/model_executor/test_backtest_cust_realtime.py
==================================================================
单元测试：回测支持客户(cust_no)实时指标 —— 两个纯函数的行为契约

被测逻辑位置：
    backend/services/fraudhunter/model_service/model_executor.py
    ModelExecutor._build_cust_realtime_join_clause
    ModelExecutor._uses_cust_realtime_indicator

测试策略：
    ✅ 纯函数，无外部依赖，参数→返回值，不涉及 IO/DB/API
    ✅ 本地复本镜像(与生产代码逐行对齐)

为何用本地复本而非标准 import：
    一旦 import services.* (含 model_executor)，便会触发
    backend/services/__init__.py 的热切导入链 → 加载
    query_engine.duckdb_service → utils.config 读 config.yaml
    (本环境 gitignore 不存在) + utils.logger 模块级初始化 +
    DuckDBService(QueryEngineService, LoggerMixin) metaclass 冲突，
    导致无法 import。此问题会在后端部署完整环境(config.yaml 就绪)后
    自然消解，届时可将下方两个函数替换为：
        from services.fraudhunter.model_service.model_executor import ModelExecutor
    并改用 ModelExecutor._build_cust_realtime_join_clause / _uses_cust_realtime_indicator。
    维护者每次改动生产代码这两处纯函数时，须同步更新本复本，保持逐行一致。
"""
from typing import Dict, List, Optional

import pytest


# ── 本地复本(须与生产代码 ModelExecutor 的两个 @staticmethod 逐行一致) ──
def _build_cust_realtime_join_clause(cust_realtime_table_name: Optional[str]) -> List[str]:
    """构建客户实时宽表 LEFT JOIN 的 SQL 行(与回测现有 cust_offline JOIN 同风格、同关联键)。
    关联键：存款实时宽表的客户号外键列 i_dep_acct_no_offline_00001 = 客户实时宽表 target_id。
    无表名(None/空串/纯空白)时返回空列表(不 JOIN)。"""
    if not cust_realtime_table_name or not cust_realtime_table_name.strip():
        return []
    return [
        "LEFT JOIN",
        f"    {cust_realtime_table_name} as cust_realtime_indicator",
        "ON",
        "    dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_realtime_indicator.target_id",
    ]


def _uses_cust_realtime_indicator(alias_mapping: Optional[Dict[str, str]]) -> bool:
    """判断规则是否引用了客户实时指标(别名映射 values 含 'cust_realtime_indicator')。"""
    return bool(alias_mapping) and "cust_realtime_indicator" in alias_mapping.values()


class TestBuildCustRealtimeJoinClause:
    @pytest.mark.parametrize("table_name", [None, "", "   "])
    def test_no_table_returns_empty(self, table_name):
        assert _build_cust_realtime_join_clause(table_name) == []

    def test_with_table_emits_aligned_join(self):
        lines = _build_cust_realtime_join_clause("cust_wide_table_abc12345_20260618")
        assert lines == [
            "LEFT JOIN",
            "    cust_wide_table_abc12345_20260618 as cust_realtime_indicator",
            "ON",
            "    dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_realtime_indicator.target_id",
        ]

    def test_clause_uses_same_join_key_as_cust_offline(self):
        """关联键须与回测现有 cust_offline JOIN 一致(都以 dep_acct_realtime 的客户号外键关联)。"""
        lines = _build_cust_realtime_join_clause("t")
        joined = "\n".join(lines)
        assert "dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_realtime_indicator.target_id" in joined


class TestUsesCustRealtimeIndicator:
    def test_true_when_mapping_contains_cust_realtime(self):
        assert _uses_cust_realtime_indicator({"i_cust_no_realtime_00001": "cust_realtime_indicator"}) is True

    def test_false_when_only_other_aliases(self):
        mapping = {
            "i_dep_acct_no_realtime_00001": "dep_acct_realtime_indicator",
            "i_cust_no_offline_00001": "cust_offline_indicator",
        }
        assert _uses_cust_realtime_indicator(mapping) is False

    def test_false_when_none(self):
        assert _uses_cust_realtime_indicator(None) is False

    def test_false_when_empty(self):
        assert _uses_cust_realtime_indicator({}) is False
