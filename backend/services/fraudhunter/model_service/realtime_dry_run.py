"""
实时预警试跑（docs/fraudhunter_offline_dual_store_plan.md 第七章阶段 12）

按指定存储后端组装并执行一次"实时模型匹配"，只返回命中结果：
- 不写执行记录、不生成命中/告警/管控记录、不发消息、不写任何表；
- 实时宽表沿用线上实时任务最近一次产出的分区（不重新加工实时指标，step1 会写 PG）；
- 离线快照按后端强制选择（不回退到其他后端）；
- SQL 由生产的 _build_model_matching_sql 生成，执行由生产的 execute_model_matching_sql 完成，
  测的是与线上完全相同的 SQL，只是表引用与方言换成目标后端；
- backend=both 时两个后端使用同一实时分区，按（目标ID, 模型）对比命中差异。

调用方负责会话的只读使用：本模块只读查询，调用方结束时 rollback（CLI/API 均如此）。
"""

import math
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from models.fraudhunter.risk_control_model import FraudHunterModelDefinition
from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot
from utils.logger import logger

BACKENDS = ('postgresql', 'duckdb')
OBJECT_WIDE_TABLES = {'dep_acct_no': 'dep_acct_wide_table', 'cust_no': 'cust_wide_table'}
TARGET_COLUMN = '目标ID'
HIT_COLUMN = 'model_hit_array'


class DryRunError(ValueError):
    """试跑参数或前置数据不满足（如模型编码不存在、无实时分区）"""


def _latest_realtime_tables(db: Session) -> Dict[str, Optional[str]]:
    """线上实时任务最近一次产出的实时宽表分区（实时快照记录：version_hash 为空）"""
    tables = {}
    for object_type, wide_table in OBJECT_WIDE_TABLES.items():
        snap = db.query(FraudHunterWideTableSnapshot).filter(and_(
            FraudHunterWideTableSnapshot.wide_table_name == f"{wide_table}_realtime",
            FraudHunterWideTableSnapshot.version_hash.is_(None),
            FraudHunterWideTableSnapshot.status == 'ready',
        )).order_by(
            desc(FraudHunterWideTableSnapshot.etl_date),
            desc(FraudHunterWideTableSnapshot.generation_time),
        ).first()
        tables[object_type] = snap.parquet_file_path if snap else None
    return tables


def _offline_snapshot(db: Session, wide_table: str, backend: str, etl_date=None):
    """指定后端的离线快照：给定 etl_date 取该日期，否则取最新（与生产同排序，不跨后端回退）"""
    from services.scheduler.jobs.realtime_indicator_job import _get_latest_offline_snapshot

    if etl_date is None:
        return _get_latest_offline_snapshot(db, wide_table, backend=backend)
    from services.fraudhunter.wide_table_service.store import query_router

    snapshots = db.query(FraudHunterWideTableSnapshot).filter(and_(
        FraudHunterWideTableSnapshot.wide_table_name == wide_table,
        FraudHunterWideTableSnapshot.status == 'ready',
        FraudHunterWideTableSnapshot.etl_date == etl_date,
    )).order_by(desc(FraudHunterWideTableSnapshot.generation_time)).all()
    return next((s for s in snapshots if query_router.snapshot_backend(s) == backend), None)


def _hit_model_ids(value) -> List[int]:
    """命中数组 → 模型ID列表（兼容 PG list、DuckDB list/ndarray、PG 数组字面量字符串）"""
    if value is None:
        return []
    if isinstance(value, str):
        inner = value.strip().strip('{}[]')
        return [int(x) for x in inner.split(',') if x.strip()]
    try:
        return [int(x) for x in list(value)]
    except TypeError:
        return []


def _normalize(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, 'item'):  # numpy 标量
        return value.item()
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def _values_equal(a, b, tolerance: float) -> bool:
    a, b = _normalize(a), _normalize(b)
    if a is None or b is None:
        return a is None and b is None
    try:
        fa, fb = float(a), float(b)
        return math.isclose(fa, fb, rel_tol=tolerance, abs_tol=tolerance)
    except (TypeError, ValueError):
        return str(a) == str(b)


def _explode_hits(df, model_codes: Dict[int, str]) -> Dict[tuple, dict]:
    """DataFrame → {(目标ID, 模型编码): 行字典}"""
    hits = {}
    if df is None or df.empty:
        return hits
    for record in df.to_dict('records'):
        target = _normalize(record.get(TARGET_COLUMN))
        for model_id in _hit_model_ids(record.get(HIT_COLUMN)):
            if model_id not in model_codes:  # 只统计本次试跑选中的模型
                continue
            row = {k: _normalize(v) for k, v in record.items() if k != HIT_COLUMN}
            hits[(target, model_codes[model_id])] = row
    return hits


def run_backend(db: Session, backend: str, models: list, realtime_tables: Dict[str, Optional[str]],
                etl_date=None, show_sql: bool = False) -> Dict[str, Any]:
    """单后端试跑：选快照 → 生成 SQL → 执行 → 命中统计"""
    from services.fraudhunter.wide_table_service.store import query_router
    from services.scheduler.jobs.realtime_indicator_job import (
        _build_model_matching_sql,
        execute_model_matching_sql,
    )

    snapshots = {ot: _offline_snapshot(db, wt, backend, etl_date) for ot, wt in OBJECT_WIDE_TABLES.items()}
    snapshot_info = {
        ot: None if s is None else {
            'id': s.id, 'wide_table_name': s.wide_table_name, 'etl_date': str(s.etl_date),
            'version_hash': s.version_hash, 'storage_backend': query_router.snapshot_backend(s),
            'path': s.parquet_file_path,
        }
        for ot, s in snapshots.items()
    }
    result: Dict[str, Any] = {'backend': backend, 'snapshots': snapshot_info, 'error': None}
    if snapshots['dep_acct_no'] is None:
        result['error'] = f"未找到 {backend} 后端的存款账户离线快照"
        return result

    refs, duckdb_mode = query_router.resolve_offline_table_refs(snapshots)
    sql = _build_model_matching_sql(
        db, models,
        realtime_tables.get('dep_acct_no'), realtime_tables.get('cust_no'),
        refs.get('dep_acct_no'), refs.get('cust_no'),
        duckdb_mode=duckdb_mode,
    )
    if show_sql:
        result['sql'] = sql
    started = time.perf_counter()
    try:
        df = execute_model_matching_sql(sql, duckdb_mode)
    except Exception as e:
        logger.error(f"[预警试跑] {backend} 执行失败: {e}", exc_info=True)
        result['error'] = f"执行失败: {e}"
        result['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        return result
    result['elapsed_seconds'] = round(time.perf_counter() - started, 3)
    result['engine'] = 'duckdb' if duckdb_mode else 'postgresql'
    result['dataframe'] = df
    result['rows'] = 0 if df is None else len(df)
    return result


def compare_hits(pg_hits: Dict[tuple, dict], duck_hits: Dict[tuple, dict],
                 tolerance: float = 1e-9) -> Dict[str, Any]:
    """按（目标ID, 模型编码）对比两个后端的命中：仅 PG、仅 DuckDB、字段值不一致"""
    only_pg = sorted(set(pg_hits) - set(duck_hits), key=str)
    only_duck = sorted(set(duck_hits) - set(pg_hits), key=str)
    mismatches = []
    for key in sorted(set(pg_hits) & set(duck_hits), key=str):
        pg_row, duck_row = pg_hits[key], duck_hits[key]
        for column in sorted(set(pg_row) | set(duck_row)):
            if not _values_equal(pg_row.get(column), duck_row.get(column), tolerance):
                mismatches.append({
                    'target_id': key[0], 'model_code': key[1], 'column': column,
                    'postgresql': pg_row.get(column), 'duckdb': duck_row.get(column),
                })
    return {
        'only_postgresql': [{'target_id': k[0], 'model_code': k[1]} for k in only_pg],
        'only_duckdb': [{'target_id': k[0], 'model_code': k[1]} for k in only_duck],
        'value_mismatches': mismatches,
        'identical': not only_pg and not only_duck and not mismatches,
    }


def run_realtime_match_dry_run(
    db: Session,
    backend: str,
    model_codes: Optional[List[str]] = None,
    etl_date=None,
    realtime_tables: Optional[Dict[str, str]] = None,
    limit: int = 20,
    show_sql: bool = False,
    tolerance: float = 1e-9,
) -> Dict[str, Any]:
    """实时预警试跑入口（只读）

    Args:
        backend: postgresql | duckdb | both
        model_codes: 模型编码列表；为空取全部在线普通模型
        etl_date: 离线快照日期；为空取各后端最新 ready 快照
        realtime_tables: 覆盖实时分区 {'dep_acct_no': 表名, 'cust_no': 表名}
        limit: 每个后端返回的样例行数

    Returns:
        {backends: {name: {...统计/样例...}}, diff: {...} | None, warnings: [...],
         realtime_tables: {...}, models: [...], hits: {name: {(目标ID,模型编码): 行}}}
        hits 为完整命中明细（CLI 导出 CSV 用，API 不返回）
    """
    backend = (backend or '').strip().lower()
    if backend not in BACKENDS + ('both',):
        raise DryRunError(f"backend 非法: {backend}（postgresql/duckdb/both）")

    query = db.query(FraudHunterModelDefinition).filter(
        FraudHunterModelDefinition.status == 'online',
        FraudHunterModelDefinition.model_type == 'normal',
    )
    models = query.all()
    if model_codes:
        wanted = set(model_codes)
        missing = wanted - {m.model_code for m in models}
        if missing:
            raise DryRunError(f"模型不存在或未上线: {sorted(missing)}")
        models = [m for m in models if m.model_code in wanted]
    if not models:
        raise DryRunError("没有可试跑的在线模型")
    model_codes_by_id = {m.id: m.model_code for m in models}

    rt_tables = dict(_latest_realtime_tables(db))
    rt_tables.update({k: v for k, v in (realtime_tables or {}).items() if v})
    if not rt_tables.get('dep_acct_no'):
        raise DryRunError("未找到存款账户实时宽表分区（线上实时任务尚未产出），可用 realtime_tables 指定")

    warnings = []
    backends = list(BACKENDS) if backend == 'both' else [backend]
    results, hits = {}, {}
    for name in backends:
        res = run_backend(db, name, models, rt_tables, etl_date, show_sql)
        df = res.pop('dataframe', None)
        hits[name] = _explode_hits(df, model_codes_by_id)
        res['hit_count'] = len(hits[name])
        per_model = {code: 0 for code in model_codes_by_id.values()}
        for _target, code in hits[name]:
            per_model[code] += 1
        res['per_model'] = per_model
        res['sample'] = [] if df is None or df.empty else [
            {k: _normalize(v) if k != HIT_COLUMN else _hit_model_ids(v) for k, v in r.items()}
            for r in df.head(limit).to_dict('records')
        ]
        if res.get('error'):
            warnings.append(f"{name}: {res['error']}")
        results[name] = res

    diff = None
    if backend == 'both':
        pg_snaps, duck_snaps = results['postgresql']['snapshots'], results['duckdb']['snapshots']
        for ot in OBJECT_WIDE_TABLES:
            a, b = pg_snaps.get(ot), duck_snaps.get(ot)
            if a and b and (a['etl_date'], a['version_hash']) != (b['etl_date'], b['version_hash']):
                warnings.append(
                    f"{ot} 离线快照不一致（结果不可直接比较）: postgresql={a['etl_date']}/{a['version_hash']} "
                    f"duckdb={b['etl_date']}/{b['version_hash']}"
                )
        if not results['postgresql'].get('error') and not results['duckdb'].get('error'):
            diff = compare_hits(hits['postgresql'], hits['duckdb'], tolerance)

    return {
        'backends': results,
        'diff': diff,
        'warnings': warnings,
        'realtime_tables': rt_tables,
        'models': [{'id': m.id, 'code': m.model_code, 'name': m.model_name} for m in models],
        'hits': hits,
    }
