"""
rule_engine 方言模块加载缓存防回归

背景（双存储改造 review 发现）：
RuleEngine._get_dialect() 原先每次调用都按文件路径 spec_from_file_location +
exec_module 重新加载 sql_dialect.py —— 一次文件读取 + 一次模块执行。
回测按天 × 每条规则循环调用（generate_sql_expression 内多处取方言），
线上会产生大量重复 IO 与模块执行开销。

按文件路径加载这件事本身要保留（sql_dialect.py 是零依赖纯模块，走 services
包链导入会在「单测直接 exec rule_engine.py」的场景下不可用），因此修复方式是
把加载动作本身缓存起来：_load_dialect_module() 用 lru_cache 只执行一次。

本文件验证：
1. 连续取方言时模块只加载一次（缓存确实生效，不是每次重载）；
2. 缓存后返回的方言实例与行为完全不变（回归防护）。
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

_backend_root = Path(__file__).parents[4] / "backend"


def _load_rule_engine(monkeypatch):
    """按 test_rule_engine_dialect.py 的既有方式 exec rule_engine.py"""
    sys.path.insert(0, str(_backend_root))

    _indicator_module = types.ModuleType("models.fraudhunter.indicator")
    _indicator_module.FraudHunterIndicatorDefinition = type("FraudHunterIndicatorDefinition", (), {})
    _risk_model_module = types.ModuleType("models.fraudhunter.risk_control_model")
    _risk_model_module.FraudHunterModelDefinition = type("FraudHunterModelDefinition", (), {})
    monkeypatch.setitem(sys.modules, "models", types.ModuleType("models"))
    monkeypatch.setitem(sys.modules, "models.fraudhunter", types.ModuleType("models.fraudhunter"))
    monkeypatch.setitem(sys.modules, "models.fraudhunter.indicator", _indicator_module)
    monkeypatch.setitem(sys.modules, "models.fraudhunter.risk_control_model", _risk_model_module)

    # sql_dialect 在「未知方言回退」分支会惰性 import utils.logger（包链在此不可用）
    logger_module = types.ModuleType("utils.logger")
    logger_module.logger = types.SimpleNamespace(
        debug=lambda *a, **k: None, info=lambda *a, **k: None,
        warning=lambda *a, **k: None, error=lambda *a, **k: None,
    )
    monkeypatch.setitem(sys.modules, "utils.logger", logger_module)

    path = _backend_root / "services" / "fraudhunter" / "model_service" / "rule_engine.py"
    spec = importlib.util.spec_from_file_location("rule_engine_cache_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def rule_engine_cls(monkeypatch):
    return _load_rule_engine(monkeypatch).RuleEngine


class TestDialectModuleCached:
    def test_module_loaded_only_once(self, rule_engine_cls):
        """连续多次取方言 → 模块只 exec 一次（第二次起命中缓存）"""
        rule_engine_cls._load_dialect_module.cache_clear()

        rule_engine_cls._get_dialect("postgresql")
        rule_engine_cls._get_dialect("duckdb")
        rule_engine_cls._get_dialect("postgresql")

        info = rule_engine_cls._load_dialect_module.cache_info()
        assert info.misses == 1, f"方言模块被重复加载 {info.misses} 次（应为 1）"
        assert info.hits == 2

    def test_module_object_is_reused(self, rule_engine_cls):
        """模块对象同一份（不是每次新建）"""
        first = rule_engine_cls._load_dialect_module()
        second = rule_engine_cls._load_dialect_module()
        assert first is second

    def test_cached_module_still_returns_working_dialects(self, rule_engine_cls):
        """缓存不影响功能：两种方言都能取到且输出正确"""
        pg = rule_engine_cls._get_dialect("postgresql")
        dd = rule_engine_cls._get_dialect("duckdb")
        assert pg.regex_match("col", "abc") == "col ~* 'abc'"
        assert dd.regex_match("col", "abc") == "regexp_matches(col, 'abc', 'i')"
        assert rule_engine_cls._get_dialect("postgresql").name == "postgresql"
        assert rule_engine_cls._get_dialect("duckdb").name == "duckdb"

    def test_unknown_dialect_still_falls_back_to_pg(self, rule_engine_cls):
        """未知方言回退 postgresql 的行为不受缓存影响"""
        assert rule_engine_cls._get_dialect("mysql").name == "postgresql"

    def test_no_dialect_reload_in_rule_generation(self, monkeypatch):
        """回归防护：生成 SQL 的过程中不得触发模块重新加载

        模拟一次多规则回测（每条规则都取方言），断言模块加载次数仍为 1。
        """
        RuleEngine = _load_rule_engine(monkeypatch).RuleEngine
        RuleEngine._load_dialect_module.cache_clear()

        calls = {"n": 0}
        original = importlib.util.module_from_spec

        def counting_module_from_spec(spec, *args, **kwargs):
            calls["n"] += 1
            return original(spec, *args, **kwargs)

        monkeypatch.setattr(importlib.util, "module_from_spec", counting_module_from_spec)

        # 模拟一次按天 × 按规则的回测循环：每条规则按方言生成表达式
        for pattern in ("a\\d+", "b\\d+", "c\\d+", "d\\d+", "e\\d+"):
            assert RuleEngine._get_dialect("duckdb").name == "duckdb"
            assert RuleEngine._get_dialect("postgresql").name == "postgresql"

        assert calls["n"] == 1, f"多次取方言触发了 {calls['n']} 次模块加载（期望 1）"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
