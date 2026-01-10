-- =====================================================
-- 管理员字段迁移脚本
-- 创建时间: 2026-01-08
-- 说明: 添加 is_admin 字段到 system_entities 表
-- 注意: 管理员角色应该通过UI界面配置，不再使用硬编码
-- =====================================================

-- 步骤1: 添加字段（带默认值 FALSE）
ALTER TABLE system_entities
ADD COLUMN is_admin BOOLEAN
NOT NULL DEFAULT FALSE
COMMENT '是否为管理员实体';

-- 步骤2: 迁移现有管理员角色（如果需要）
-- 注意: 下面这步是为了向后兼容历史数据
-- 新部署应该通过权限管理UI界面配置管理员角色
-- UPDATE system_entities
-- SET is_admin = TRUE
-- WHERE code IN ('淘沙管理员', 'taosha_admin')
-- AND type = 'role';

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

-- 注意: 请通过权限管理页面（/admin/roles）配置管理员角色
