-- ============================================================================
-- FraudHunter序列计数器表
-- 创建时间: 2025-12-05
-- 说明: 用于指标和指标任务的编码自动生成
-- ============================================================================

-- 1. 创建序列计数器表
CREATE TABLE fraudhunter_sequence_counter (
    id INT PRIMARY KEY AUTO_INCREMENT,
    counter_type VARCHAR(64) NOT NULL UNIQUE COMMENT '计数器类型',
    counter_value INT NOT NULL DEFAULT 0 COMMENT '当前计数值',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_counter_type (counter_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='序列计数器表';

-- 2. 初始化计数器（针对已有数据）

-- 指标任务计数器
INSERT INTO fraudhunter_sequence_counter (counter_type, counter_value)
SELECT 'indicator_task', COALESCE(MAX(id), 0)
FROM fraudhunter_indicator_task;

-- 指标计数器（按分类初始化）
-- 注意：只为已存在的分类组合创建计数器
INSERT INTO fraudhunter_sequence_counter (counter_type, counter_value)
SELECT
    CONCAT('indicator_', object_type, '_', indicator_type) as counter_type,
    COALESCE(MAX(id), 0) as counter_value
FROM fraudhunter_indicator_definition
GROUP BY object_type, indicator_type;

-- 3. 验证迁移（可选，运行后查看输出）
-- SELECT * FROM fraudhunter_sequence_counter ORDER BY counter_type;

-- ============================================================================
-- 说明：
-- 1. 计数器类型格式：
--    - 指标任务: indicator_task
--    - 指标: indicator_{object_type}_{indicator_type}
--      例如: indicator_cust_no_offline, indicator_dep_acct_no_realtime
--
-- 2. 并发安全：
--    - 使用 SELECT FOR UPDATE 行级锁保证并发安全
--    - SequenceManager 服务会在事务中使用悲观锁
--
-- 3. 计数器初始化：
--    - 基于现有数据的最大ID初始化
--    - 确保新生成的编码不与已有数据冲突
--
-- 4. 编码生成格式：
--    - 指标任务: i_task_00001
--    - 指标: i_{object_type}_{indicator_type}_00001
-- ============================================================================
