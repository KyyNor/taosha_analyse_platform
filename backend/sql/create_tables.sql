-- 淘沙分析平台 - 数据库建表脚本
-- 支持 SQLite 和 MySQL

-- ==================== 元数据表 ====================

-- 元数据表
CREATE TABLE IF NOT EXISTS metadata_tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    comment TEXT,
    is_available INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metadata_columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    comment TEXT,
    is_available INTEGER DEFAULT 0,
    business_type TEXT DEFAULT '',
    relation_id TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (table_name) REFERENCES metadata_tables(name) ON DELETE CASCADE,
    UNIQUE(table_name, name)
);

-- ==================== 术语表 ====================

CREATE TABLE IF NOT EXISTS glossary_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    creator TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== 提示词配置表 ====================

CREATE TABLE IF NOT EXISTS prompt_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    fields TEXT NOT NULL,
    template TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== 关联字段配置表 ====================

CREATE TABLE IF NOT EXISTS relation_field_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relation_id TEXT UNIQUE NOT NULL,
    relation_family TEXT NOT NULL,
    relation_subfamily TEXT NOT NULL,
    relation_desc TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================== 操作追踪表 ====================

-- NL查询会话记录表
CREATE TABLE IF NOT EXISTS nlquery_sessions (
    task_id TEXT PRIMARY KEY,
    user_input TEXT NOT NULL,
    operator TEXT,
    flow_type TEXT DEFAULT 'fast',
    status TEXT DEFAULT 'running',
    current_step TEXT DEFAULT '初始化',
    progress INTEGER DEFAULT 0,
    created_at DATETIME NOT NULL,
    completed_at DATETIME,
    sql_query TEXT,
    execution_result TEXT,
    clear_check_details TEXT,
    is_clear INTEGER DEFAULT 0,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 5
);

-- NL查询步骤详情表
CREATE TABLE IF NOT EXISTS nlquery_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    step TEXT NOT NULL,
    input_data TEXT,
    prompt TEXT,
    model_output TEXT,
    success INTEGER DEFAULT 1,
    error TEXT,
    start_time DATETIME,
    end_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES nlquery_sessions(task_id)
);

-- 用户反馈表
CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_type TEXT NOT NULL,
    session_id TEXT NOT NULL,
    step_sequence INTEGER,
    feedback_sentiment TEXT NOT NULL,
    feedback_content TEXT NOT NULL,
    feedback_user TEXT,
    feedback_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES operation_sessions(session_id)
);

-- ==================== 索引 ====================

-- 操作追踪相关索引
CREATE INDEX IF NOT EXISTS idx_nlquery_sessions_operator ON nlquery_sessions(operator);
CREATE INDEX IF NOT EXISTS idx_nlquery_sessions_flow_type ON nlquery_sessions(flow_type);
CREATE INDEX IF NOT EXISTS idx_nlquery_sessions_status ON nlquery_sessions(status);
CREATE INDEX IF NOT EXISTS idx_nlquery_sessions_created_at ON nlquery_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_nlquery_steps_task_id ON nlquery_steps(task_id);
CREATE INDEX IF NOT EXISTS idx_nlquery_steps_step ON nlquery_steps(task_id, step);
CREATE INDEX IF NOT EXISTS idx_user_feedback_session_id ON user_feedback(session_id);

-- 术语表相关索引
CREATE INDEX IF NOT EXISTS idx_glossary_terms_name ON glossary_terms(name);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_type ON glossary_terms(type);

-- 提示词配置表相关索引
CREATE INDEX IF NOT EXISTS idx_prompt_templates_name ON prompt_templates(name);

-- 元数据表相关索引
CREATE INDEX IF NOT EXISTS idx_metadata_tables_name ON metadata_tables(name);
CREATE INDEX IF NOT EXISTS idx_metadata_columns_table_name ON metadata_columns(table_name);
CREATE INDEX IF NOT EXISTS idx_metadata_columns_table_name_name ON metadata_columns(table_name, name);
CREATE INDEX IF NOT EXISTS idx_metadata_columns_relation_id ON metadata_columns(relation_id);

-- 关联字段配置索引
CREATE INDEX IF NOT EXISTS idx_relation_field_config_relation_id ON relation_field_config(relation_id);
CREATE INDEX IF NOT EXISTS idx_relation_field_config_family ON relation_field_config(relation_family, relation_subfamily);