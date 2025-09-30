-- 淘沙分析平台 - 删除表脚本
-- 用于清理所有表

-- SQLite 版本 (禁用外键约束)

-- 禁用外键约束
PRAGMA foreign_keys = OFF;

-- 删除表 (按依赖关系倒序)
DROP TABLE IF EXISTS user_feedback;
DROP TABLE IF EXISTS operation_steps;
DROP TABLE IF EXISTS operation_sessions;
DROP TABLE IF EXISTS glossary_aliases;
DROP TABLE IF EXISTS glossary_terms;
DROP TABLE IF EXISTS metadata_columns;
DROP TABLE IF EXISTS metadata_tables;
DROP TABLE IF EXISTS relation_field_config;

-- 重新启用外键约束
PRAGMA foreign_keys = ON;