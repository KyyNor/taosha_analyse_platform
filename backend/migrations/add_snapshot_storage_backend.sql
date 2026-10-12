-- =====================================================
-- 宽表快照存储后端字段迁移脚本
-- 创建时间: 2026-08-19
-- 说明: fraudhunter_wide_table_snapshot 表新增 storage_backend 字段，
--       标记每个快照的实际存储位置（postgresql=PG正式表 / duckdb=本地Parquet目录）
-- 背景: 离线宽表双存储方案（docs/fraudhunter_offline_dual_store_plan.md 阶段1）
-- 注意: parquet_file_path 字段语义由 storage_backend 决定——
--       postgresql 快照存PG表名（现状语义），duckdb 快照存Parquet目录绝对路径
-- =====================================================

-- 步骤1: 添加字段（存量行全部回填为 postgresql，兼容现状）
ALTER TABLE fraudhunter_wide_table_snapshot
ADD COLUMN storage_backend VARCHAR(16)
NOT NULL DEFAULT 'postgresql'
COMMENT '存储后端: postgresql/duckdb';

-- 步骤2: 验证迁移结果（期望: 仅 postgresql 一行，count = 存量快照总数）
SELECT
    storage_backend,
    COUNT(*) AS snapshot_count
FROM fraudhunter_wide_table_snapshot
GROUP BY storage_backend;
