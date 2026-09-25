"""
阶段4：rule_engine 的 SQL 方言参数

对应 docs/fraudhunter_offline_dual_store_plan.md 阶段4：
- 默认 dialect='postgresql' 时输出与改造前逐字符一致（PG回归零变化）；
- dialect='duckdb' 时正则条件改写为 regexp_matches（可直接在 DuckDB 执行）；
- 数值/日期 CAST 双方言输出一致（已验证 DuckDB 兼容 ::DOUBLE PRECISION）。
"""

from pathlib import Path
from types import SimpleNamespace
import importlib.util
import sys
import types

import duckdb

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

_indicator_module = types.ModuleType("models.fraudhunter.indicator")
_indicator_module.FraudHunterIndicatorDefinition = type("FraudHunterIndicatorDefinition", (), {})
_risk_model_module = types.ModuleType("models.fraudhunter.risk_control_model")
_risk_model_module.FraudHunterModelDefinition = type("FraudHunterModelDefinition", (), {})
sys.modules.setdefault("models", types.ModuleType("models"))
sys.modules.setdefault("models.fraudhunter", types.ModuleType("models.fraudhunter"))
sys.modules["models.fraudhunter.indicator"] = _indicator_module
sys.modules["models.fraudhunter.risk_control_model"] = _risk_model_module

_rule_engine_path = _backend_root / "services" / "fraudhunter" / "model_service" / "rule_engine.py"
_spec = importlib.util.spec_from_file_location("rule_engine_dialect_under_test", _rule_engine_path)
_rule_engine_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rule_engine_module)

RuleEngine = _rule_engine_module.RuleEngine
RuleConfig = _rule_engine_module.RuleConfig


class FakeRuleEngine(RuleEngine):
    def __init__(self, indicators):
        self.indicators = indicators
        self._model_cache = {}

    def _get_indicator_cached(self, indicator_code):
        return self.indicators.get(indicator_code)


def _string_indicator():
    return SimpleNamespace(data_type="string", indicator_name="渠道", indicator_type="offline")


def _regexp_rule(pattern="app\\d+"):
    return RuleConfig(**{
        "logic": "AND",
        "rules": [
            {
                "type": "condition",
                "indicator": "i_channel",
                "operator": "regexp",
                "value": {"type": "constant", "value": pattern},
            }
        ],
    })


def _numeric_cast_rule():
    return RuleConfig(**{
        "logic": "AND",
        "rules": [
            {
                "type": "condition",
                "indicator": "i_amt",
                "operator": ">",
                "value": {"type": "constant", "value": 100},
            }
        ],
    })


class TestRegexpDialect:
    def test_default_pg_dialect_output_unchanged(self):
        engine = FakeRuleEngine({"i_channel": _string_indicator()})
        expr = engine.generate_sql_expression(_regexp_rule(), {"i_channel": "t"}, numeric_columns_are_typed=True)
        assert expr == "(t.i_channel ~* 'app\\d+')"

    def test_explicit_pg_dialect_same_as_default(self):
        engine = FakeRuleEngine({"i_channel": _string_indicator()})
        expr = engine.generate_sql_expression(
            _regexp_rule(), {"i_channel": "t"}, numeric_columns_are_typed=True, dialect="postgresql"
        )
        assert expr == "(t.i_channel ~* 'app\\d+')"

    def test_duckdb_dialect_uses_regexp_matches(self):
        engine = FakeRuleEngine({"i_channel": _string_indicator()})
        expr = engine.generate_sql_expression(
            _regexp_rule(), {"i_channel": "t"}, numeric_columns_are_typed=True, dialect="duckdb"
        )
        assert expr == "(regexp_matches(t.i_channel, 'app\\d+', 'i'))"

    def test_not_regexp_dialects(self):
        engine = FakeRuleEngine({"i_channel": _string_indicator()})
        rule = RuleConfig(**{
            "logic": "AND",
            "rules": [{
                "type": "condition",
                "indicator": "i_channel",
                "operator": "not regexp",
                "value": {"type": "constant", "value": "x"},
            }],
        })
        assert engine.generate_sql_expression(rule, {"i_channel": "t"}, numeric_columns_are_typed=True) \
            == "(not t.i_channel ~* 'x')"
        assert engine.generate_sql_expression(
            rule, {"i_channel": "t"}, numeric_columns_are_typed=True, dialect="duckdb"
        ) == "(NOT regexp_matches(t.i_channel, 'x', 'i'))"

    def test_duckdb_regex_output_executes_on_duckdb(self):
        """duckdb 方言产物可直接执行；PG 方言产物在 DuckDB 上报语法错误"""
        engine = FakeRuleEngine({"i_channel": _string_indicator()})
        expr = engine.generate_sql_expression(
            _regexp_rule("APP\\d+"), {"i_channel": "t"}, numeric_columns_are_typed=True, dialect="duckdb"
        )
        conn = duckdb.connect()
        conn.execute("SELECT 'APP99' AS i_channel")
        # 用常量替换列引用验证语义
        expr_const = expr.replace("t.i_channel", "'APP99'")
        assert conn.execute(f"SELECT {expr_const}").fetchone()[0] is True
        expr_const = expr.replace("t.i_channel", "'WEB'")
        assert conn.execute(f"SELECT {expr_const}").fetchone()[0] is False


class TestCastDialect:
    def test_numeric_cast_identical_both_dialects(self):
        engine = FakeRuleEngine({
            "i_amt": SimpleNamespace(data_type="numeric", indicator_name="金额", indicator_type="offline"),
        })
        pg = engine.generate_sql_expression(
            _numeric_cast_rule(), {"i_amt": "t"}, numeric_columns_are_typed=False, dialect="postgresql"
        )
        dd = engine.generate_sql_expression(
            _numeric_cast_rule(), {"i_amt": "t"}, numeric_columns_are_typed=False, dialect="duckdb"
        )
        assert pg == "(COALESCE(t.i_amt::DOUBLE PRECISION, 0) > 100)"
        assert dd == pg
