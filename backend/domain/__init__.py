"""Domain layer — 纯业务逻辑，与基础设施无关，可独立测试。"""

from .wide_table import WideTableComparator, VersionDelta

__all__ = ["WideTableComparator", "VersionDelta"]