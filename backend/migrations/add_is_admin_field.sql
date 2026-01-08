-- =====================================================
-- 管理员字段迁移脚本
-- 创建时间: 2026-01-08
-- 说明: 添加 is_admin 字段到 system_entities 表
-- =====================================================

-- 步骤1: 添加字段（带默认值 FALSE）
ALTER TABLE system_entities
ADD COLUMN is_admin BOOLEAN
NOT NULL DEFAULT FALSE
COMMENT '是否为管理员实体';

-- 步骤2: 迁移现有管理员角色
UPDATE system_entities
SET is_admin = TRUE
WHERE code IN ('淘沙管理员', 'taosha_admin')
AND type = 'role';

-- 步骤3: 创建索引以优化查询性能
CREATE INDEX idx_is_admin ON system_entities(is_admin);

-- 步骤4: 创建复合索引（优化管理员查询）
CREATE INDEX idx_type_is_admin ON system_entities(type, is_admin);

-- 步骤5: 验证迁移结果
SELECT
    '管理员实体统计' as description,
    type,
    COUNT(*) as count
FROM system_entities
WHERE is_admin = TRUE
GROUP BY type;

SELECT
    '预计管理员角色' as description,
    id, code, name, is_admin
FROM system_entities
WHERE code IN ('淘沙管理员', 'taosha_admin');
