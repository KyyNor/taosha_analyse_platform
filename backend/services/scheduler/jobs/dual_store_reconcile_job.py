"""
双写对账定时任务（双存储方案阶段7）

offline_store=both 灰度期间，对同一 (宽表, 版本, 日期) 的 PG 与 duckdb 快照
做每日对账：行数 + 内容校验和（sum(hash(行拼接))，顺序无关，双方言同构），
结果落日志（运维按 [双写对账] 关键字检索）。

切换纯 duckdb 前的验收：连续 ≥1 个完整同步周期（含版本变化）对账 0 失败。
"""

from datetime import date, datetime, timedelta

from models.db_base import get_db_session
from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot
from utils.config import settings
from utils.logger import logger

# 对账回溯天数（覆盖一个完整同步周期）
RECONCILE_LOOKBACK_DAYS = 7


def _find_dual_pairs(db) -> list:
    """找出近期双后端均有 ready 快照的 (宽表, 版本, 日期) 组"""
    since = date.today() - timedelta(days=RECONCILE_LOOKBACK_DAYS)
    snapshots = db.query(FraudHunterWideTableSnapshot).filter(
        FraudHunterWideTableSnapshot.etl_date >= since,
        FraudHunterWideTableSnapshot.status == 'ready',
        FraudHunterWideTableSnapshot.version_hash.isnot(None),
    ).all()

    by_key: dict = {}
    for s in snapshots:
        by_key.setdefault(
            (s.wide_table_name, s.version_hash, s.etl_date), {}
        )[s.storage_backend] = s

    return [
        (key, backends['postgresql'], backends['duckdb'])
        for key, backends in by_key.items()
        if 'postgresql' in backends and 'duckdb' in backends
    ]


def _reconcile_pair(pg_snapshot, duck_snapshot) -> dict:
    """单组对账：PG 分区 vs Parquet 目录（行数 + 内容校验和）"""
    from services.fraudhunter.wide_table_service.store.query_router import DuckQuerySession

    date_str = pg_snapshot.etl_date.strftime('%Y-%m-%d')
    parquet_glob = (
        f"{duck_snapshot.parquet_file_path}/etl_date={date_str}/*.parquet"
    )
    parquet_relation = f"read_parquet('{parquet_glob}', hive_partitioning=false)"
    pg_relation = (
        f"(SELECT * EXCLUDE (created_at) FROM pg_rt.public.{pg_snapshot.parquet_file_path} "
        f"WHERE etl_date = DATE '{date_str}')"
    )

    with DuckQuerySession(attach_pg=True) as conn:
        columns = [
            row[0] for row in conn.conn.execute(
                f"DESCRIBE SELECT * FROM {parquet_relation}"
            ).fetchall()
        ]
        joined = ", ".join(f"{c}::VARCHAR" for c in columns)
        checksum_sql = (
            f"SELECT count(*), sum(hash(concat_ws('|', {joined}))) FROM "
        )
        parquet_count, parquet_hash = conn.conn.execute(
            checksum_sql + parquet_relation
        ).fetchone()
        pg_count, pg_hash = conn.conn.execute(
            checksum_sql + pg_relation
        ).fetchone()

    passed = (parquet_count == pg_count) and (parquet_hash == pg_hash)
    return {
        "passed": passed,
        "pg_rows": pg_count,
        "duck_rows": parquet_count,
        "pg_hash": pg_hash,
        "duck_hash": parquet_hash,
    }


async def dual_store_reconcile_job():
    """双写对账任务（both 模式灰度验收）"""
    try:
        with get_db_session() as db:
            pairs = _find_dual_pairs(db)

        if not pairs:
            logger.debug("[双写对账] 近期无双后端快照对（非both模式或灰度未覆盖），跳过")
            return

        passed = failed = 0
        for (wide_table_name, version_hash, etl_date), pg_snap, duck_snap in pairs:
            key = f"{wide_table_name} v={version_hash[:8]} d={etl_date}"
            try:
                result = _reconcile_pair(pg_snap, duck_snap)
                if result["passed"]:
                    passed += 1
                    logger.info(
                        f"[双写对账] PASS {key}: rows={result['duck_rows']} "
                        f"checksum={result['duck_hash']}"
                    )
                else:
                    failed += 1
                    logger.error(
                        f"[双写对账] FAIL {key}: "
                        f"pg_rows={result['pg_rows']} duck_rows={result['duck_rows']} "
                        f"pg_hash={result['pg_hash']} duck_hash={result['duck_hash']}"
                    )
            except Exception as e:
                failed += 1
                logger.error(f"[双写对账] ERROR {key}: {e}", exc_info=True)

        verdict = "对账通过" if failed == 0 else f"存在{failed}组不一致，禁止切换duckdb"
        logger.info(
            f"[双写对账] 汇总: 共{len(pairs)}组, 通过{passed}, 失败{failed} → {verdict}"
        )

    except Exception as e:
        logger.error(f"[双写对账] 任务失败: {e}", exc_info=True)


def main():
    import asyncio

    logger.info(f"[{datetime.now()}] 双写对账任务开始")
    asyncio.run(dual_store_reconcile_job())
    logger.info(f"[{datetime.now()}] 双写对账任务结束")


if __name__ == '__main__':
    main()
