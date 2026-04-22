"""
tests/backend/__init__.py
tests 包的全局 conftest，为所有子模块的 import 提供统一的 sys.path 补丁。

当 pytest 运行 tests/backend/modules/*/ 时，确保 backend/ 代码可通过
`from services.xxx` 或 `from schemas.xxx` 直接导入，无需在每个测试文件内做路径 hack。
"""

import sys
from pathlib import Path

# ── 将 backend 根目录加入 sys.path（一劳永逸）────────────────────────────
_backend_root = Path(__file__).parents[1] / "backend"
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

# ── 全局 pytest plugins 配置 ──────────────────────────────────────────────
import pytest

# 让所有 test_*.py 里的 MagicMock/spy 都默认使用 utf-8
import locale
locale.setlocale(locale.LC_ALL, "en_US.UTF-8")


def pytest_collection_modifyitems(items):
    """
    自动为所有测试用例附加标记（按目录名推断）。
    例：tests/backend/modules/wide_table_sync/test_xxx.py → @pytest.mark.wt
    """
    for item in items:
        rel_path = str(item.fspath).replace(str(Path(__file__).parent.parent) + "/", "")
        for marker_prefix, marker_name in [
            ("wide_table_sync",  "wt"),
            ("realtime_indicator", "rt"),
            ("alert_notification", "alert"),
            ("province_cardbin",   "pcbin"),
            ("history_trend",      "hist"),
            ("alert_control_record_optimization", "acr"),
            ("indicator_management", "ind"),
        ]:
            if marker_prefix in rel_path:
                item.add_marker(pytest.mark._mark_key(marker_name))
                break