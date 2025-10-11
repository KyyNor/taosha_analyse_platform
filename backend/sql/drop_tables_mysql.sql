-- 淘沙分析平台 - MySQL 删除表脚本
-- 用于清理所有表

-- 禁用外键约束检查
SET FOREIGN_KEY_CHECKS = 0;

-- 删除表 (按依赖关系倒序)
DROP TABLE IF EXISTS user_feedback;
DROP TABLE IF EXISTS nlquery_steps;
DROP TABLE IF EXISTS nlquery_sessions;
DROP TABLE IF EXISTS glossary_aliases;
DROP TABLE IF EXISTS glossary_terms;
DROP TABLE IF EXISTS metadata_columns;
DROP TABLE IF EXISTS metadata_tables;
DROP TABLE IF EXISTS relation_field_config;

-- 重新启用外键约束检查
SET FOREIGN_KEY_CHECKS = 1;