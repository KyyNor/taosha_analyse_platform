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
    term VARCHAR(255) UNIQUE NOT NULL,
    definition TEXT,
    sql_expression TEXT,
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS glossary_aliases (
    id INT PRIMARY KEY AUTO_INCREMENT,
    term_id INT NOT NULL,
    alias VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (term_id) REFERENCES glossary_terms(id) ON DELETE CASCADE
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

-- 操作会话记录表
CREATE TABLE IF NOT EXISTS operation_sessions (
    session_id VARCHAR(36) PRIMARY KEY,
    operation_type VARCHAR(100) NOT NULL,
    operator VARCHAR(100),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NULL,
    total_duration INT,
    max_step_sequence INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 操作步骤详情表
CREATE TABLE IF NOT EXISTS operation_steps (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(36) NOT NULL,
    step_sequence INT NOT NULL,
    step_name VARCHAR(200) NOT NULL,
    input_data TEXT,
    call_method VARCHAR(100),
    output_data TEXT,
    generated_sql TEXT,
    error_message TEXT,
    success BOOLEAN DEFAULT TRUE,
    duration INT,
    token_usage JSON,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES operation_sessions(session_id)
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
CREATE INDEX IF NOT EXISTS idx_operation_sessions_operator ON operation_sessions(operator);
CREATE INDEX IF NOT EXISTS idx_operation_sessions_operation_type ON operation_sessions(operation_type);
CREATE INDEX IF NOT EXISTS idx_operation_sessions_start_time ON operation_sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_operation_steps_session_id ON operation_steps(session_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_session_id ON user_feedback(session_id);

-- 术语表相关索引
CREATE INDEX IF NOT EXISTS idx_glossary_terms_term ON glossary_terms(term);
CREATE INDEX IF NOT EXISTS idx_glossary_aliases_term_id ON glossary_aliases(term_id);
CREATE INDEX IF NOT EXISTS idx_glossary_aliases_alias ON glossary_aliases(alias);

-- 元数据表相关索引
CREATE INDEX IF NOT EXISTS idx_metadata_tables_name ON metadata_tables(name);
CREATE INDEX IF NOT EXISTS idx_metadata_columns_table_name ON metadata_columns(table_name);
CREATE INDEX IF NOT EXISTS idx_metadata_columns_table_name_name ON metadata_columns(table_name, name);
CREATE INDEX IF NOT EXISTS idx_metadata_columns_relation_id ON metadata_columns(relation_id);

-- 关联字段配置索引
CREATE INDEX IF NOT EXISTS idx_relation_field_config_relation_id ON relation_field_config(relation_id);
CREATE INDEX IF NOT EXISTS idx_relation_field_config_family ON relation_field_config(relation_family, relation_subfamily);