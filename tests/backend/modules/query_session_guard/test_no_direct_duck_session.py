"""
Issue #8 防回归守卫：业务代码禁止直接实例化 DuckQuerySession

DuckQuerySession 仅允许在 query_router（工厂/本地实现）中出现；
业务代码必须经 get_query_session() 工厂取会话，否则 remote 模式
（duck_compute.mode=remote，后端零 duckdb 依赖）会被旁路，
后端机器仍会触发本地 import duckdb。

同类守卫：DuckdbParquetStore 写路径内部使用连接属实现细节，不在此约束范围。
"""

import re
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"

# 允许出现 DuckQuerySession 字样的文件（工厂与实现所在）
ALLOWLIST = {
    Path("services/fraudhunter/wide_table_service/store/query_router.py"),
    Path("services/fraudhunter/wide_table_service/store/remote_session.py"),  # 文档注释
}

# 直接实例化模式：DuckQuerySession( ，排除注释行
_INSTANTIATE_RE = re.compile(r'^[^#]*\bDuckQuerySession\s*\(')


def _business_python_files():
    for sub in ("services", "api"):
        root = _backend_root / sub
        for p in root.rglob("*.py"):
            yield p.relative_to(_backend_root), p
    yield Path("main.py"), _backend_root / "main.py"


def test_no_direct_duck_session_instantiation():
    violations = []
    for rel, path in _business_python_files():
        if rel in ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _INSTANTIATE_RE.search(line):
                violations.append(f"{rel}:{lineno}: {line.strip()}")
    assert not violations, (
        "业务代码直接实例化 DuckQuerySession（须改用 get_query_session 工厂，"
        "否则 remote 模式下后端仍依赖本地 duckdb，Issue #8）:\n" + "\n".join(violations)
    )


def test_get_query_session_factory_exists_and_used():
    """工厂存在，且 realtime/model/reconcile 调用点均经工厂取会话"""
    router = (
        _backend_root / "services/fraudhunter/wide_table_service/store/query_router.py"
    ).read_text(encoding="utf-8")
    assert "def get_query_session(" in router

    callers = [
        _backend_root / "services/scheduler/jobs/realtime_indicator_job.py",
        _backend_root / "services/scheduler/jobs/dual_store_reconcile_job.py",
        _backend_root / "services/fraudhunter/model_service/model_executor.py",
        _backend_root / "services/fraudhunter/indicator_service/indicator_query_service.py",
    ]
    for caller in callers:
        text = caller.read_text(encoding="utf-8")
        assert "get_query_session" in text, f"{caller.name} 未使用 get_query_session 工厂"
