-- ============================================================================
-- FraudHunter指标定义表添加对象类型字段
-- 创建时间: 2025-12-05
-- 说明: 添加 object_type 字段用于标识指标对象类型（客户号/存款账号/贷款账号）
-- ============================================================================

-- 1. 为 fraudhunter_indicator_definition 表添加 object_type 字段
ALTER TABLE fraudhunter_indicator_definition
ADD COLUMN object_type VARCHAR(32) NOT NULL DEFAULT 'cust_no'
COMMENT '对象类型：cust_no/dep_acct_no/loan_acct_no'
AFTER indicator_type;

-- 2. 为 fraudhunter_indicator_definition 表添加索引
CREATE INDEX idx_fh_indicator_object_type ON fraudhunter_indicator_definition(object_type);

-- 3. 为 fraudhunter_indicator_history 表添加 object_type 字段
ALTER TABLE fraudhunter_indicator_history
ADD COLUMN object_type VARCHAR(32)
COMMENT '对象类型'
AFTER indicator_type;

-- 4. 验证修改（可选，运行后查看输出）
-- DESCRIBE fraudhunter_indicator_definition;
-- DESCRIBE fraudhunter_indicator_history;
-- SHOW INDEX FROM fraudhunter_indicator_definition;

-- ============================================================================
-- 说明：
-- 1. fraudhunter_indicator_definition 表的 object_type 字段设置为 NOT NULL
--    并指定默认值为 'cust_no'，确保现有记录自动设置为客户号类型
-- 2. fraudhunter_indicator_history 表的 object_type 字段可以为 NULL
--    因为历史记录可能在字段添加前就已存在
-- 3. 添加了索引以提升按对象类型筛选时的查询性能
-- ============================================================================
