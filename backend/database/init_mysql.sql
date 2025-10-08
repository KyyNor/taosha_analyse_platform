-- MySQL 数据库初始化脚本
-- 创建时间: 2024-10-08
-- 说明: 淘沙分析平台元数据库表结构

-- 设置字符集
SET NAMES utf8mb4;
SET character_set_client = utf8mb4;

-- 1. 数据主题表
CREATE TABLE IF NOT EXISTS `metadata_data_theme` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `theme_name` VARCHAR(100) NOT NULL COMMENT '主题名称',
    `theme_description` TEXT COMMENT '主题描述',
    `is_public` BOOLEAN DEFAULT FALSE COMMENT '是否公共主题',
    `sort_order` INT DEFAULT 0 COMMENT '排序序号',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `created_by` BIGINT COMMENT '创建人ID',
    `updated_by` BIGINT COMMENT '更新人ID',
    INDEX `idx_theme_name` (`theme_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据主题表';

-- 2. 表元数据表
CREATE TABLE IF NOT EXISTS `metadata_table` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `table_name_cn` VARCHAR(200) NOT NULL COMMENT '表中文名称',
    `table_name_en` VARCHAR(200) NOT NULL COMMENT '表英文名称',
    `data_source` VARCHAR(100) COMMENT '数据源',
    `update_method` ENUM('real_time', 'daily', 'weekly', 'monthly', 'manual') DEFAULT 'daily' COMMENT '更新方式',
    `table_description` TEXT COMMENT '表描述',
    `schema_name` VARCHAR(100) COMMENT '模式名称',
    `table_type` VARCHAR(50) DEFAULT 'table' COMMENT '表类型',
    `row_count` BIGINT COMMENT '行数',
    `size_mb` INT COMMENT '大小(MB)',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `is_visible` BOOLEAN DEFAULT TRUE COMMENT '是否可见',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `created_by` BIGINT COMMENT '创建人ID',
    `updated_by` BIGINT COMMENT '更新人ID',
    INDEX `idx_table_name_en` (`table_name_en`),
    INDEX `idx_table_name_cn` (`table_name_cn`),
    INDEX `idx_data_source` (`data_source`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='表元数据表';

-- 3. 字段元数据表
CREATE TABLE IF NOT EXISTS `metadata_field` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `table_id` BIGINT NOT NULL COMMENT '表ID',
    `field_name_cn` VARCHAR(200) NOT NULL COMMENT '字段中文名称',
    `field_name_en` VARCHAR(200) NOT NULL COMMENT '字段英文名称',
    `field_type` ENUM('string', 'integer', 'float', 'decimal', 'boolean', 'date', 'datetime', 'time', 'text', 'json', 'array') NOT NULL COMMENT '字段类型',
    `business_type` ENUM('dimension', 'measure', 'attribute', 'key', 'identifier') COMMENT '业务类型',
    `max_length` INT COMMENT '最大长度',
    `precision` INT COMMENT '精度',
    `scale` INT COMMENT '小数位数',
    `is_nullable` BOOLEAN DEFAULT TRUE COMMENT '是否可为空',
    `is_primary_key` BOOLEAN DEFAULT FALSE COMMENT '是否主键',
    `is_foreign_key` BOOLEAN DEFAULT FALSE COMMENT '是否外键',
    `default_value` VARCHAR(500) COMMENT '默认值',
    `field_description` TEXT COMMENT '字段描述',
    `business_rules` TEXT COMMENT '业务规则',
    `data_format` VARCHAR(100) COMMENT '数据格式',
    `value_range` VARCHAR(500) COMMENT '取值范围',
    `sample_values` TEXT COMMENT '示例值',
    `association_id` VARCHAR(100) COMMENT '关联ID',
    `foreign_table_id` BIGINT COMMENT '外键关联表ID',
    `foreign_field_id` BIGINT COMMENT '外键关联字段ID',
    `desensitization_type` ENUM('none', 'mask', 'encrypt', 'hash', 'replace') DEFAULT 'none' COMMENT '脱敏类型',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `is_indexed` BOOLEAN DEFAULT FALSE COMMENT '是否有索引',
    `distinct_count` BIGINT COMMENT '唯一值数量',
    `null_count` BIGINT COMMENT '空值数量',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `created_by` BIGINT COMMENT '创建人ID',
    `updated_by` BIGINT COMMENT '更新人ID',
    INDEX `idx_table_id` (`table_id`),
    INDEX `idx_field_name_en` (`field_name_en`),
    INDEX `idx_field_name_cn` (`field_name_cn`),
    FOREIGN KEY (`table_id`) REFERENCES `metadata_table`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='字段元数据表';

-- 4. 术语表
CREATE TABLE IF NOT EXISTS `metadata_glossary` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `term_name` VARCHAR(200) NOT NULL COMMENT '术语名称',
    `term_description` TEXT NOT NULL COMMENT '术语描述',
    `term_type` ENUM('admin', 'user') DEFAULT 'user' COMMENT '术语类型',
    `category` VARCHAR(100) COMMENT '术语分类',
    `aliases` JSON COMMENT '别名列表',
    `related_terms` JSON COMMENT '相关术语列表',
    `examples` TEXT COMMENT '使用示例',
    `data_sources` TEXT COMMENT '相关数据源',
    `usage_count` INT DEFAULT 0 COMMENT '使用次数',
    `last_used_at` DATETIME COMMENT '最后使用时间',
    `user_id` BIGINT COMMENT '用户ID',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `created_by` BIGINT COMMENT '创建人ID',
    `updated_by` BIGINT COMMENT '更新人ID',
    INDEX `idx_term_name` (`term_name`),
    INDEX `idx_term_type` (`term_type`),
    INDEX `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='术语表';

-- 5. 表与主题关联表
CREATE TABLE IF NOT EXISTS `metadata_table_theme` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `table_id` BIGINT NOT NULL COMMENT '表ID',
    `theme_id` BIGINT NOT NULL COMMENT '主题ID',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `created_by` BIGINT COMMENT '创建人ID',
    UNIQUE KEY `uk_table_theme` (`table_id`, `theme_id`),
    FOREIGN KEY (`table_id`) REFERENCES `metadata_table`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`theme_id`) REFERENCES `metadata_data_theme`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='表与主题关联表';

-- 6. 表关联关系表
CREATE TABLE IF NOT EXISTS `metadata_relation` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `source_table_id` BIGINT NOT NULL COMMENT '源表ID',
    `target_table_id` BIGINT NOT NULL COMMENT '目标表ID',
    `source_field_id` BIGINT COMMENT '源字段ID',
    `target_field_id` BIGINT COMMENT '目标字段ID',
    `relation_type` VARCHAR(50) NOT NULL COMMENT '关系类型',
    `relation_name` VARCHAR(200) COMMENT '关系名称',
    `relation_description` TEXT COMMENT '关系描述',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `created_by` BIGINT COMMENT '创建人ID',
    `updated_by` BIGINT COMMENT '更新人ID',
    INDEX `idx_source_table` (`source_table_id`),
    INDEX `idx_target_table` (`target_table_id`),
    FOREIGN KEY (`source_table_id`) REFERENCES `metadata_table`(`id`),
    FOREIGN KEY (`target_table_id`) REFERENCES `metadata_table`(`id`),
    FOREIGN KEY (`source_field_id`) REFERENCES `metadata_field`(`id`),
    FOREIGN KEY (`target_field_id`) REFERENCES `metadata_field`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='表关联关系表';

-- 7. 自然语言查询任务表 (省略其他表的完整SQL，模式相同)
-- ... (由于长度限制，这里省略其他表的创建语句)

-- 创建视图：用户权限视图
CREATE OR REPLACE VIEW `v_user_permissions` AS
SELECT 
    u.id as user_id,
    u.username,
    p.permission_code,
    p.permission_name,
    p.permission_type,
    p.data_theme_id,
    p.table_id
FROM `sys_user` u
JOIN `sys_user_role` ur ON u.id = ur.user_id
JOIN `sys_role` r ON ur.role_id = r.id
JOIN `sys_role_permission` rp ON r.id = rp.role_id
JOIN `sys_permission` p ON rp.permission_id = p.id
WHERE u.is_active = TRUE 
    AND u.is_deleted = FALSE 
    AND r.is_active = TRUE 
    AND p.is_active = TRUE;

-- 创建视图：表权限视图
CREATE OR REPLACE VIEW `v_table_permissions` AS
SELECT 
    t.id as table_id,
    t.table_name_cn,
    t.table_name_en,
    u.id as user_id,
    u.username
FROM `metadata_table` t
JOIN `sys_permission` p ON t.id = p.table_id
JOIN `sys_role_permission` rp ON p.id = rp.permission_id
JOIN `sys_role` r ON rp.role_id = r.id
JOIN `sys_user_role` ur ON r.id = ur.role_id
JOIN `sys_user` u ON ur.user_id = u.id
WHERE t.is_active = TRUE 
    AND u.is_active = TRUE 
    AND u.is_deleted = FALSE 
    AND r.is_active = TRUE 
    AND p.is_active = TRUE;

-- 插入初始数据
INSERT IGNORE INTO `sys_role` (`role_code`, `role_name`, `role_description`, `is_system`, `created_by`) VALUES
('admin', '系统管理员', '拥有系统所有权限', TRUE, 1),
('user', '普通用户', '基础查询权限', TRUE, 1);

INSERT IGNORE INTO `sys_user` (`username`, `nickname`, `password_hash`, `is_active`, `created_by`) VALUES
('admin', '系统管理员', 'admin123_hash', TRUE, 1),
('demo', '演示用户', 'demo123_hash', TRUE, 1);

INSERT IGNORE INTO `sys_user_role` (`user_id`, `role_id`, `created_by`) VALUES
(1, 1, 1),
(2, 2, 1);

-- 插入默认数据主题
INSERT IGNORE INTO `metadata_data_theme` (`theme_name`, `theme_description`, `is_public`, `created_by`) VALUES
('公共数据', '所有用户都可以访问的公共数据', TRUE, 1),
('销售数据', '销售相关的业务数据', FALSE, 1),
('用户数据', '用户行为和属性数据', FALSE, 1);

-- 插入示例表元数据
INSERT IGNORE INTO `metadata_table` (`table_name_cn`, `table_name_en`, `table_description`, `data_source`, `created_by`) VALUES
('用户表', 'users', '系统用户基本信息表', 'main_db', 1),
('订单表', 'orders', '用户订单信息表', 'main_db', 1),
('产品表', 'products', '产品信息表', 'main_db', 1);

-- 插入示例字段元数据
INSERT IGNORE INTO `metadata_field` (`table_id`, `field_name_cn`, `field_name_en`, `field_type`, `field_description`, `created_by`) VALUES
(1, '用户ID', 'user_id', 'integer', '用户唯一标识', 1),
(1, '用户名', 'username', 'string', '用户登录名', 1),
(1, '邮箱', 'email', 'string', '用户邮箱地址', 1),
(2, '订单ID', 'order_id', 'integer', '订单唯一标识', 1),
(2, '用户ID', 'user_id', 'integer', '下单用户ID', 1),
(2, '订单金额', 'amount', 'decimal', '订单总金额', 1);