-- 回滚脚本：删除 branch_no 字段
-- 警告：不可逆操作，执行前务必备份数据

-- 步骤1：删除索引
DROP INDEX IF EXISTS idx_fh_hit_branch_no ON fraudhunter_model_hit_record;
DROP INDEX IF EXISTS idx_fh_alert_branch_no ON fraudhunter_model_alert_control_record;

-- 步骤2：删除字段
ALTER TABLE fraudhunter_model_hit_record DROP COLUMN IF EXISTS branch_no;
ALTER TABLE fraudhunter_model_alert_control_record DROP COLUMN IF EXISTS branch_no;

-- 验证回滚结果
SELECT
    'fraudhunter_model_hit_record' AS table_name,
    column_name
FROM information_schema.columns
WHERE table_name = 'fraudhunter_model_hit_record'
AND column_name = 'branch_no'
UNION ALL
SELECT
    'fraudhunter_model_alert_control_record' AS table_name,
    column_name
FROM information_schema.columns
WHERE table_name = 'fraudhunter_model_alert_control_record'
AND column_name = 'branch_no';

-- 如果查询结果为空，说明回滚成功
