-- 迁移脚本：为告警管控记录添加 branch_no 字段
-- 执行时间：在低峰期执行
-- 回滚方案：参见 rollback_add_branch_to_alert_records.sql

-- 步骤1：添加 branch_no 字段到 fraudhunter_model_hit_record
ALTER TABLE fraudhunter_model_hit_record
ADD COLUMN IF NOT EXISTS branch_no VARCHAR(32) COMMENT '部门编号（4位数字）';

-- 步骤2：添加索引到 fraudhunter_model_hit_record
CREATE INDEX IF NOT EXISTS idx_fh_hit_branch_no
ON fraudhunter_model_hit_record(branch_no);

-- 步骤3：添加 branch_no 字段到 fraudhunter_model_alert_control_record
ALTER TABLE fraudhunter_model_alert_control_record
ADD COLUMN IF NOT EXISTS branch_no VARCHAR(32) COMMENT '部门编号（4位数字）';

-- 步骤4：添加索引到 fraudhunter_model_alert_control_record
CREATE INDEX IF NOT EXISTS idx_fh_alert_branch_no
ON fraudhunter_model_alert_control_record(branch_no);

-- 步骤5：为历史数据填充 branch_no（可选）
-- 注意：如果历史数据无法恢复，建议保持 NULL
-- 下面的SQL会从关联的命中记录中同步branch_no
UPDATE fraudhunter_model_alert_control_record t1
INNER JOIN fraudhunter_model_hit_record t2 ON t1.hit_record_id = t2.id
SET t1.branch_no = t2.branch_no
WHERE t1.branch_no IS NULL AND t2.branch_no IS NOT NULL;

-- 验证迁移结果
SELECT
    'fraudhunter_model_hit_record' AS table_name,
    COUNT(*) AS total_records,
    COUNT(branch_no) AS records_with_branch_no,
    COUNT(*) - COUNT(branch_no) AS records_without_branch_no
FROM fraudhunter_model_hit_record
UNION ALL
SELECT
    'fraudhunter_model_alert_control_record' AS table_name,
    COUNT(*) AS total_records,
    COUNT(branch_no) AS records_with_branch_no,
    COUNT(*) - COUNT(branch_no) AS records_without_branch_no
FROM fraudhunter_model_alert_control_record;
