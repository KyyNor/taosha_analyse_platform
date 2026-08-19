"""
离线宽表存储后端抽象接口

双存储方案阶段2（docs/fraudhunter_offline_dual_store_plan.md）：
把 sync_service 中"写存储"的动作收敛到该接口后面，PG 实现包住现有代码；
阶段3 新增 DuckDB Parquet 实现。接口以 sync_service 现有调用面为准，不发明新概念。
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import ClassVar, Tuple


class WideTableStore(ABC):
    """离线宽表存储后端

    同一宽表版本的最终数据只落在一种后端上，由快照的 storage_backend 标记：
    - postgresql: PG 正式分区表，快照引用为表名
    - duckdb:     本地 Parquet 目录，快照引用为目录绝对路径
    """

    name: ClassVar[str]

    @abstractmethod
    def ensure_table(
        self,
        table_name: str,
        indicator_metadata: dict,
        etl_date: date,
    ) -> None:
        """确保存储目标存在（PG: create_wide_table + ensure_partition）"""

    @abstractmethod
    def create_heap_table(
        self,
        table_name: str,
        indicator_metadata: dict,
        **kwargs,
    ) -> None:
        """创建轻量无分区辅助表（增量delta表 / DuckDB路径staging中转表）"""

    @abstractmethod
    def drop_table(self, table_name: str) -> None:
        """删除表"""

    @abstractmethod
    def write_pivot(
        self,
        sql: str,
        table_name: str,
        etl_date: date,
        refresh_sql: str | None = None,
    ) -> Tuple[int, int]:
        """执行 Spark PIVOT 查询并写入存储目标

        Returns:
            (row_count, column_count)
        """

    @abstractmethod
    def merge_delta_insert_select(
        self,
        dest_table: str,
        base_table: str,
        delta_table: str | None,
        target_metadata: dict,
        static_cols: list,
        inc_cols: list,
        etl_date: str,
    ) -> int:
        """增量路径：从 base 表复制 static 列、合并 delta 表新列，返回行数"""

    @abstractmethod
    def snapshot_ref(self, table_name: str, etl_date: date) -> str:
        """快照记录的存储位置引用（写入快照 parquet_file_path 字段）

        PG: 表名（现状语义不变）；DuckDB: Parquet 目录绝对路径。
        """
