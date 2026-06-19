from pathlib import Path
from types import SimpleNamespace
import importlib.util
import sys
import types


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
_spec = importlib.util.spec_from_file_location("rule_engine_under_test", _rule_engine_path)
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


def _numeric_indicator():
    return SimpleNamespace(
        data_type="numeric",
        indicator_name="交易金额",
        indicator_type="realtime",
    )


def test_get_indicator_sql_with_cast_omits_cast_for_typed_numeric_columns():
    engine = FakeRuleEngine({"i_amt": _numeric_indicator()})

    assert (
        engine._get_indicator_sql_with_cast(
            "i_amt",
            {"i_amt": "dep_acct_realtime_indicator"},
            numeric_columns_are_typed=True,
        )
        == "COALESCE(dep_acct_realtime_indicator.i_amt, 0)"
    )


def test_get_indicator_sql_with_cast_keeps_cast_for_untyped_numeric_columns():
    engine = FakeRuleEngine({"i_amt": _numeric_indicator()})

    assert (
        engine._get_indicator_sql_with_cast(
            "i_amt",
            {"i_amt": "dep_acct_realtime_indicator"},
            numeric_columns_are_typed=False,
        )
        == "COALESCE(dep_acct_realtime_indicator.i_amt::DOUBLE PRECISION, 0)"
    )


def test_generate_sql_expression_threads_typed_numeric_flag_to_left_and_indicator_reference():
    engine = FakeRuleEngine({
        "i_amt": _numeric_indicator(),
        "i_limit": _numeric_indicator(),
    })
    rule_config = RuleConfig(**{
        "logic": "AND",
        "rules": [
            {
                "type": "condition",
                "indicator": "i_amt",
                "operator": ">",
                "value": {"type": "indicator", "indicator": "i_limit"},
            }
        ],
    })
    aliases = {
        "i_amt": "dep_acct_realtime_indicator",
        "i_limit": "dep_acct_realtime_indicator",
    }

    assert engine.generate_sql_expression(
        rule_config,
        aliases,
        numeric_columns_are_typed=True,
    ) == (
        "(COALESCE(dep_acct_realtime_indicator.i_amt, 0) > "
        "COALESCE(dep_acct_realtime_indicator.i_limit, 0))"
    )


def test_generate_sql_expression_defaults_to_existing_numeric_cast_behavior():
    engine = FakeRuleEngine({
        "i_amt": _numeric_indicator(),
        "i_limit": _numeric_indicator(),
    })
    rule_config = RuleConfig(**{
        "logic": "AND",
        "rules": [
            {
                "type": "condition",
                "indicator": "i_amt",
                "operator": ">",
                "value": {"type": "indicator", "indicator": "i_limit"},
            }
        ],
    })
    aliases = {
        "i_amt": "dep_acct_realtime_indicator",
        "i_limit": "dep_acct_realtime_indicator",
    }

    assert engine.generate_sql_expression(rule_config, aliases) == (
        "(COALESCE(dep_acct_realtime_indicator.i_amt::DOUBLE PRECISION, 0) > "
        "COALESCE(dep_acct_realtime_indicator.i_limit::DOUBLE PRECISION, 0))"
    )


def test_value_expression_helpers_use_typed_numeric_flag():
    engine = FakeRuleEngine({
        "i_amt": _numeric_indicator(),
        "i_delta": _numeric_indicator(),
    })
    rule_config = RuleConfig(**{
        "logic": "AND",
        "rules": [
            {
                "type": "condition",
                "indicator": "i_amt",
                "operator": ">",
                "value": {"type": "math_function", "function": "abs", "indicator": "i_delta"},
            },
            {
                "type": "condition",
                "indicator": "i_amt",
                "operator": "<",
                "value": {"type": "relative_calculation", "indicator": "i_delta", "operation": "add", "value": 10},
            },
        ],
    })
    aliases = {
        "i_amt": "dep_acct_realtime_indicator",
        "i_delta": "dep_acct_realtime_indicator",
    }

    assert engine.generate_sql_expression(
        rule_config,
        aliases,
        numeric_columns_are_typed=True,
    ) == (
        "(COALESCE(dep_acct_realtime_indicator.i_amt, 0) > "
        "ABS(COALESCE(dep_acct_realtime_indicator.i_delta, 0)) AND "
        "COALESCE(dep_acct_realtime_indicator.i_amt, 0) < "
        "(COALESCE(dep_acct_realtime_indicator.i_delta, 0) + 10))"
    )


def test_model_reference_rule_preserves_typed_numeric_flag_recursively():
    engine = FakeRuleEngine({"i_amt": _numeric_indicator()})
    engine._model_cache = {
        1: SimpleNamespace(
            rule_config={
                "logic": "AND",
                "rules": [
                    {
                        "type": "condition",
                        "indicator": "i_amt",
                        "operator": ">",
                        "value": {"type": "constant", "value": 100},
                    }
                ],
            }
        )
    }
    rule_config = RuleConfig(**{
        "logic": "AND",
        "rules": [{"type": "model_ref", "model_id": 1}],
    })
    aliases = {"i_amt": "dep_acct_realtime_indicator"}

    assert engine.generate_sql_expression(
        rule_config,
        aliases,
        numeric_columns_are_typed=True,
    ) == "(((COALESCE(dep_acct_realtime_indicator.i_amt, 0) > 100)))"
