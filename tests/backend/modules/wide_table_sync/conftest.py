"""wide_table_sync 测试共用：预注册无依赖的真实 checksum 模块

被测模块（duckdb_parquet_store / dual_store_reconcile_job）以惰性
absolute import 引用 store/checksum.py；各测试用 fake 父包 +
importlib 直载被测文件，不经过真实包路径，因此这里按真实文件把
checksum 模块注册进 sys.modules（pytest 收集本目录前生效）。
"""

import importlib.util
import sys
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"

_mod_name = "services.fraudhunter.wide_table_service.store.checksum"
if _mod_name not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        _mod_name,
        _backend_root / "services" / "fraudhunter" / "wide_table_service" / "store" / "checksum.py",
    )
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_mod_name] = _module
    _spec.loader.exec_module(_module)
