-- FraudHunter PostgreSQL 数据库初始化脚本
-- 用于集成测试环境

\c fraudhunter;

-- ============================================
-- 实时交易明细表 (分区表)
-- ============================================

CREATE TABLE IF NOT EXISTS realtime_oss_inct_new (
    -- 账户信息
    acct_no varchar(255),
    acct_open_dt varchar(255),
    acct_type varchar(255),
    aorm_date varchar(255),
    branch_name varchar(255),
    branch_no varchar(255),
    busi_typ varchar(255),
    ccy_name varchar(255),
    cha_desc varchar(255),
    channel varchar(255),
    class_type varchar(255),
    cp_acct_name varchar(255),
    cp_acct_no varchar(255),
    cp_acct_type varchar(255),
    cp_bank_branch_name varchar(255),
    cp_bank_num varchar(255),
    cp_class_type varchar(255),
    cp_int_cat varchar(255),
    currency varchar(255),
    cust_name varchar(255),
    cust_type varchar(255),
    customer_no varchar(255),
    fir_branch_name varchar(255),
    fir_branch_no varchar(255),
    gl_class_code varchar(255),
    inct_01_amount decimal(18,2),
    inct_01_balance decimal(18,2),
    inct_01_tran_acct varchar(255),
    inct_20_chnnel varchar(255),
    inct_20_desc varchar(255),
    inct_20_narr varchar(255),
    inct_20_rec_no varchar(255),
    inct_20_source varchar(255),
    inma_flag varchar(255),
    int_cat varchar(255),
    jrnl_no varchar(255),
    mgr_no varchar(255),
    mst_aom_no varchar(255),
    parent_branch_name varchar(255),
    parent_branch_no varchar(255),
    peri_no varchar(255),
    prd_name varchar(255),
    rec_no varchar(255),
    rt_processing_time varchar(255),
    send_to_fh_time varchar(255),
    tran_branch varchar(255),
    tran_date date NOT NULL,
    tran_time varchar(255),
    tran_type varchar(255),
    trn_code varchar(255),

    -- 时间戳
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
) PARTITION BY RANGE (tran_date);

-- 索引
CREATE INDEX IF NOT EXISTS idx_realtime_tran_date ON realtime_oss_inct_new (tran_date);
CREATE INDEX IF NOT EXISTS idx_realtime_acct_no ON realtime_oss_inct_new (acct_no);
CREATE INDEX IF NOT EXISTS idx_realtime_created_at ON realtime_oss_inct_new (created_at);

-- 分区函数
CREATE OR REPLACE FUNCTION create_realtime_partition(p_date date)
RETURNS void AS $$
DECLARE
    partition_name text;
    start_date text;
    end_date text;
BEGIN
    partition_name := 'realtime_oss_inct_new_' || to_char(p_date, 'YYYYMMDD');
    start_date := to_char(p_date, 'YYYY-MM-DD');
    end_date := to_char(p_date + INTERVAL '1 day', 'YYYY-MM-DD');

    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I PARTITION OF realtime_oss_inct_new
        FOR VALUES FROM (%L) TO (%L)
    ', partition_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;

-- 创建今天和明天的分区
SELECT create_realtime_partition(CURRENT_DATE::date);
SELECT create_realtime_partition((CURRENT_DATE + INTERVAL '1 day')::date);

-- 完成初始化
DO $$
BEGIN
    RAISE NOTICE 'FraudHunter database initialization completed!';
END $$;
