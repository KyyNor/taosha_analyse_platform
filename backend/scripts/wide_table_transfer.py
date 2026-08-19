#!/usr/bin/env python3
"""
离线宽表存储互转CLI（docs/fraudhunter_offline_dual_store_plan.md 阶段5）

用途：
- pg2duckdb: 把PG离线宽表指定日期转为DuckDB Parquet（存量迁移，切换存储无需从源头重同步）
- duckdb2pg: 把Parquet指定日期写回PG正式表（应急回退通道）

用法示例：
    # 迁移近30天（需与--version-hash对应版本的PG快照存在）
    python scripts/wide_table_transfer.py --wide-table cust_wide_table \
        --version-hash <完整64位hash> --backfill 30 --direction pg2duckdb

    # 指定日期重转（覆盖已有目标）
    python scripts/wide_table_transfer.py --wide-table cust_wide_table \
        --version-hash <hash> --dates 2026-08-01 2026-08-02 \
        --direction pg2duckdb --overwrite

    # 应急回退：Parquet写回PG
    python scripts/wide_table_transfer.py --wide-table cust_wide_table \
        --version-hash <hash> --dates 2026-08-01 --direction duckdb2pg
"""

import sys
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.fraudhunter.wide_table_service.transfer_service import (  # noqa: E402
    WideTableTransferService,
    resolve_etl_dates,
)
from utils.logger import logger  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description='离线宽表PG↔DuckDB Parquet互转工具')
    parser.add_argument('--wide-table', required=True,
                        help='宽表名称，如 cust_wide_table')
    parser.add_argument('--version-hash', required=True,
                        help='完整64位版本hash')
    parser.add_argument('--dates', nargs='+',
                        help='日期列表 YYYY-MM-DD（与 --backfill 二选一）')
    parser.add_argument('--backfill', type=int,
                        help='回溯天数（最近N天，与 --dates 二选一）')
    parser.add_argument('--direction', required=True, choices=['pg2duckdb', 'duckdb2pg'],
                        help='互转方向')
    parser.add_argument('--keep-source', action='store_true', default=True,
                        help='保留源侧数据（默认True；源侧清理交给现有分区清理延迟处理）')
    parser.add_argument('--overwrite', action='store_true',
                        help='目标已存在时重转（默认幂等跳过）')

    args = parser.parse_args()

    etl_dates = resolve_etl_dates(args.dates, args.backfill)
    logger.info(
        f"[互转] 开始: {args.direction} {args.wide_table} {args.version_hash[:8]} "
        f"共{len(etl_dates)}天 keep_source={args.keep_source} overwrite={args.overwrite}"
    )

    service = WideTableTransferService()
    results = service.transfer(
        wide_table_name=args.wide_table,
        version_hash=args.version_hash,
        etl_dates=etl_dates,
        direction=args.direction,
        keep_source=args.keep_source,
        overwrite=args.overwrite,
    )

    transferred = sum(1 for r in results if r['status'] == 'transferred')
    skipped = sum(1 for r in results if r['status'] == 'skipped')
    failed = sum(1 for r in results if r['status'] == 'failed')
    for r in results:
        logger.info(f"[互转] {r['etl_date']} {r['status']}: {r.get('detail', '')} "
                    f"rows={r.get('row_count', '-')}")

    logger.info(f"[互转] 完成: 成功{transferred} 跳过{skipped} 失败{failed}")
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()
