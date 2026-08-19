-- =====================================================
-- 宽表快照唯一索引扩展（纳入 storage_backend）
-- 创建时间: 2026-08-19
-- 说明: both 双写模式下，同一宽表/版本/日期会同时产生
--       postgresql 与 duckdb 两条独立快照记录，
--       唯一索引必须包含 storage_backend 才能共存。
-- 前置: add_snapshot_storage_backend.sql（阶段1）
-- =====================================================

-- 步骤1: 删除原唯一索引
ALTER TABLE fraudhunter_wide_table_snapshot
DROP INDEX uk_fh_ws_table_date;

-- 步骤2: 重建唯一索引（含存储后端维度）
CREATE UNIQUE INDEX uk_fh_ws_table_date
ON fraudhunter_wide_table_snapshot (
    wide_table_name,
    version_hash,
    etl_date,
    storage_backend
);

-- 步骤3: 验证（对同一表/版本/日期应最多2行：postgresql + duckdb）
SELECT
    wide_table_name,
    version_hash,
    etl_date,
    COUNT(*) AS snapshot_rows,
    GROUP_CONCAT(storage_backend) AS backends
FROM fraudhunter_wide_table_snapshot
GROUP BY wide_table_name, version_hash, etl_date
HAVING COUNT(*) > 2;
-- 期望: 空结果集
