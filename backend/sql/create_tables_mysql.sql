-- 淘沙分析平台 - MySQL 数据库建表脚本

-- ==================== 元数据表 ====================

-- 元数据表
CREATE TABLE IF NOT EXISTS metadata_tables (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    comment TEXT,
    is_available INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metadata_columns (
    id INT PRIMARY KEY AUTO_INCREMENT,
    table_name VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    comment TEXT,
    is_available INT DEFAULT 0,
    business_type VARCHAR(100) DEFAULT '',
    relation_id VARCHAR(255) DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (table_name) REFERENCES metadata_tables(name) ON DELETE CASCADE,
    UNIQUE KEY unique_table_column (table_name, name)
);

-- ==================== 术语表 ====================

CREATE TABLE IF NOT EXISTS glossary_terms (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,
    content JSON NOT NULL,
    creator VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ==================== 提示词配置表 ====================

CREATE TABLE IF NOT EXISTS prompt_templates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    fields JSON NOT NULL,
    template TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ==================== 关联字段配置表 ====================

CREATE TABLE IF NOT EXISTS relation_field_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    relation_id VARCHAR(255) UNIQUE NOT NULL,
    relation_family VARCHAR(255) NOT NULL,
    relation_subfamily VARCHAR(255) NOT NULL,
    relation_desc TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ==================== 操作追踪表 ====================

-- NL查询会话记录表
CREATE TABLE IF NOT EXISTS nlquery_sessions (
    task_id VARCHAR(36) PRIMARY KEY,
    user_input TEXT NOT NULL,
    operator VARCHAR(100),
    flow_type VARCHAR(20) DEFAULT 'fast',
    status VARCHAR(20) DEFAULT 'running',
    current_step VARCHAR(200) DEFAULT '初始化',
    progress INT DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NULL,
    sql_query TEXT,
    execution_result JSON,
    clear_check_details JSON,
    is_clear BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 5
);

-- NL查询步骤详情表
CREATE TABLE IF NOT EXISTS nlquery_steps (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(36) NOT NULL,
    step VARCHAR(200) NOT NULL,
    input_data TEXT,
    prompt TEXT,
    model_output TEXT,
    success BOOLEAN DEFAULT TRUE,
    error TEXT,
    start_time TIMESTAMP NULL,
    end_time TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES nlquery_sessions(task_id)
);

-- 用户反馈表
CREATE TABLE IF NOT EXISTS user_feedback (
    id INT PRIMARY KEY AUTO_INCREMENT,
    feedback_type VARCHAR(50) NOT NULL,
    session_id VARCHAR(36) NOT NULL,
    step_sequence INT,
    feedback_sentiment VARCHAR(20) NOT NULL,
    feedback_content TEXT NOT NULL,
    feedback_user VARCHAR(100),
    feedback_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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