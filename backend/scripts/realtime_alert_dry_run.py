#!/usr/bin/env python3
"""
实时预警试跑 CLI（docs/fraudhunter_offline_dual_store_plan.md 第七章阶段 12）

按指定存储后端组装并执行一次实时模型匹配，只打印命中结果：
不写执行记录、不生成命中/告警/管控记录、不发消息、不写任何表（数据库会话最终 rollback）。

用法示例：
    # 用 DuckDB 离线快照跑一次在线模型匹配
    python scripts/realtime_alert_dry_run.py --backend duckdb

    # PG 与 DuckDB 各跑一次并对比差异，导出命中明细与差异
    python scripts/realtime_alert_dry_run.py --backend both --models M001 M002 --output hits.csv

    # 指定离线快照日期与实时分区，打印生成的 SQL
    python scripts/realtime_alert_dry_run.py --backend both --etl-date 2026-10-09 \\
        --realtime-table dep_acct_no=dep_acct_wide_table_realtime_1a2b3c4d_202610101430 --show-sql
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import services  # noqa: E402,F401  按应用顺序初始化包（规避循环导入）
from models.db_base import SessionLocal  # noqa: E402
from services.fraudhunter.model_service.realtime_dry_run import (  # noqa: E402
    DryRunError,
    run_realtime_match_dry_run,
)


def _parse_realtime_tables(items):
    tables = {}
    for item in items or []:
        if '=' not in item:
            raise SystemExit(f"--realtime-table 格式应为 对象类型=表名: {item}")
        key, value = item.split('=', 1)
        if key not in ('dep_acct_no', 'cust_no'):
            raise SystemExit(f"--realtime-table 对象类型仅支持 dep_acct_no/cust_no: {key}")
        tables[key] = value
    return tables


def _print_backend(name, res, limit):
    print(f"\n==== {name} ====")
    for ot, snap in res['snapshots'].items():
        if snap:
            print(f"  离线快照[{ot}]: id={snap['id']} etl_date={snap['etl_date']} "
                  f"version={snap['version_hash']} backend={snap['storage_backend']}")
        else:
            print(f"  离线快照[{ot}]: 无")
    if res.get('error'):
        print(f"  ✗ {res['error']}")
        return
    print(f"  执行引擎: {res.get('engine')}  耗时: {res.get('elapsed_seconds')}s  "
          f"结果行数: {res.get('rows')}  命中(目标×模型): {res.get('hit_count')}")
    for code, count in res['per_model'].items():
        print(f"    {code}: {count}")
    if res.get('sql'):
        print("  ---- SQL ----")
        print(res['sql'])
    if res['sample']:
        print(f"  ---- 样例（前 {limit} 行）----")
        for row in res['sample']:
            print("   ", json.dumps(row, ensure_ascii=False, default=str))


def _export(output, report):
    import pandas as pd

    output = Path(output)
    rows = []
    for backend, hits in report['hits'].items():
        for (target, code), row in hits.items():
            rows.append({'backend': backend, 'target_id': target, 'model_code': code, **row})
    pd.DataFrame(rows).to_csv(output, index=False, encoding='utf-8-sig')
    print(f"\n命中明细已导出: {output}（{len(rows)} 行）")
    if report['diff'] is not None:
        diff_path = output.with_name(output.stem + '_diff.json')
        diff_path.write_text(json.dumps(report['diff'], ensure_ascii=False, indent=1, default=str),
                             encoding='utf-8')
        print(f"差异明细已导出: {diff_path}")


def main():
    parser = argparse.ArgumentParser(description='实时预警试跑（只读，不入库/不发消息/不管控）')
    parser.add_argument('--backend', required=True, choices=['postgresql', 'duckdb', 'both'])
    parser.add_argument('--models', nargs='+', help='模型编码（默认全部在线普通模型）')
    parser.add_argument('--etl-date', help='离线快照日期 YYYY-MM-DD（默认各后端最新 ready 快照）')
    parser.add_argument('--realtime-table', action='append',
                        help='覆盖实时分区，格式 对象类型=表名（可重复，默认取最近一次实时快照）')
    parser.add_argument('--limit', type=int, default=20, help='每个后端打印的样例行数')
    parser.add_argument('--tolerance', type=float, default=1e-9, help='both 对比时数值容差')
    parser.add_argument('--show-sql', action='store_true', help='打印生成的模型匹配 SQL')
    parser.add_argument('--output', help='导出命中明细 CSV（both 模式额外导出 *_diff.json）')
    args = parser.parse_args()

    etl_date = date.fromisoformat(args.etl_date) if args.etl_date else None
    db = SessionLocal()
    try:
        report = run_realtime_match_dry_run(
            db, args.backend, model_codes=args.models, etl_date=etl_date,
            realtime_tables=_parse_realtime_tables(args.realtime_table),
            limit=args.limit, show_sql=args.show_sql, tolerance=args.tolerance,
        )
    except DryRunError as e:
        print(f"试跑失败: {e}")
        sys.exit(2)
    finally:
        db.rollback()  # 只读：任何意外变更都不落库
        db.close()

    print("模型:", ", ".join(f"{m['code']}({m['name']})" for m in report['models']))
    print("实时分区:", json.dumps(report['realtime_tables'], ensure_ascii=False))
    for name, res in report['backends'].items():
        _print_backend(name, res, args.limit)

    if report['diff'] is not None:
        diff = report['diff']
        print("\n==== 对比（postgresql vs duckdb）====")
        print(f"  仅 PG 命中: {len(diff['only_postgresql'])}  仅 DuckDB 命中: {len(diff['only_duckdb'])}  "
              f"字段值不一致: {len(diff['value_mismatches'])}")
        print("  ✓ 两侧结果一致" if diff['identical'] else "  ✗ 存在差异（--output 导出明细）")
        for item in (diff['only_postgresql'] + diff['only_duckdb'])[:args.limit]:
            print("   ", item)
        for item in diff['value_mismatches'][:args.limit]:
            print("   ", json.dumps(item, ensure_ascii=False, default=str))
    for warning in report['warnings']:
        print(f"\n⚠ {warning}")

    if args.output:
        _export(args.output, report)

    has_error = any(res.get('error') for res in report['backends'].values())
    sys.exit(1 if has_error or (report['diff'] is not None and not report['diff']['identical']) else 0)


if __name__ == '__main__':
    main()
