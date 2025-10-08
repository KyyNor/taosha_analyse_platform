-- SQLite 数据库初始化脚本
-- 创建时间: 2024-10-08
-- 说明: 淘沙分析平台元数据库表结构

-- 1. 数据主题表
CREATE TABLE IF NOT EXISTS metadata_data_theme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_name VARCHAR(100) NOT NULL,
    theme_description TEXT,
    is_public BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER
);

-- 2. 表元数据表
CREATE TABLE IF NOT EXISTS metadata_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name_cn VARCHAR(200) NOT NULL,
    table_name_en VARCHAR(200) NOT NULL,
    data_source VARCHAR(100),
    update_method VARCHAR(20) DEFAULT 'daily',
    table_description TEXT,
    schema_name VARCHAR(100),
    table_type VARCHAR(50) DEFAULT 'table',
    row_count INTEGER,
    size_mb INTEGER,
    is_active BOOLEAN DEFAULT 1,
    is_visible BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER
);

-- 3. 字段元数据表
CREATE TABLE IF NOT EXISTS metadata_field (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id INTEGER NOT NULL,
    field_name_cn VARCHAR(200) NOT NULL,
    field_name_en VARCHAR(200) NOT NULL,
    field_type VARCHAR(20) NOT NULL,
    business_type VARCHAR(20),
    max_length INTEGER,
    precision INTEGER,
    scale INTEGER,
    is_nullable BOOLEAN DEFAULT 1,
    is_primary_key BOOLEAN DEFAULT 0,
    is_foreign_key BOOLEAN DEFAULT 0,
    default_value VARCHAR(500),
    field_description TEXT,
    business_rules TEXT,
    data_format VARCHAR(100),
    value_range VARCHAR(500),
    sample_values TEXT,
    association_id VARCHAR(100),
    foreign_table_id INTEGER,
    foreign_field_id INTEGER,
    desensitization_type VARCHAR(20) DEFAULT 'none',
    is_active BOOLEAN DEFAULT 1,
    is_indexed BOOLEAN DEFAULT 0,
    distinct_count INTEGER,
    null_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER,
    FOREIGN KEY (table_id) REFERENCES metadata_table(id)
);

-- 4. 术语表
CREATE TABLE IF NOT EXISTS metadata_glossary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term_name VARCHAR(200) NOT NULL,
    term_description TEXT NOT NULL,
    term_type VARCHAR(20) DEFAULT 'user',
    category VARCHAR(100),
    aliases TEXT,
    related_terms TEXT,
    examples TEXT,
    data_sources TEXT,
    usage_count INTEGER DEFAULT 0,
    last_used_at DATETIME,
    user_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER
);

-- 5. 表与主题关联表
CREATE TABLE IF NOT EXISTS metadata_table_theme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id INTEGER NOT NULL,
    theme_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (table_id) REFERENCES metadata_table(id),
    FOREIGN KEY (theme_id) REFERENCES metadata_data_theme(id)
);

-- 6. 表关联关系表
CREATE TABLE IF NOT EXISTS metadata_relation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_table_id INTEGER NOT NULL,
    target_table_id INTEGER NOT NULL,
    source_field_id INTEGER,
    target_field_id INTEGER,
    relation_type VARCHAR(50) NOT NULL,
    relation_name VARCHAR(200),
    relation_description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER,
    FOREIGN KEY (source_table_id) REFERENCES metadata_table(id),
    FOREIGN KEY (target_table_id) REFERENCES metadata_table(id),
    FOREIGN KEY (source_field_id) REFERENCES metadata_field(id),
    FOREIGN KEY (target_field_id) REFERENCES metadata_field(id)
);

-- 7. 自然语言查询任务表
CREATE TABLE IF NOT EXISTS nlquery_task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(64) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    user_question TEXT NOT NULL,
    query_type VARCHAR(30) DEFAULT 'natural_language',
    selected_theme_id INTEGER,
    selected_table_ids TEXT,
    task_status VARCHAR(20) DEFAULT 'pending',
    progress_percentage INTEGER DEFAULT 0,
    current_step VARCHAR(100),
    generated_sql TEXT,
    final_sql TEXT,
    sql_validation_result TEXT,
    execution_result TEXT,
    result_row_count INTEGER,
    result_columns TEXT,
    result_data TEXT,
    error_message TEXT,
    error_code VARCHAR(50),
    error_details TEXT,
    start_time DATETIME,
    end_time DATETIME,
    duration_seconds INTEGER,
    llm_model VARCHAR(100),
    llm_tokens_used INTEGER,
    prompt_template TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 8. 查询工作流节点表
CREATE TABLE IF NOT EXISTS nlquery_workflow_node (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    node_name VARCHAR(100) NOT NULL,
    node_type VARCHAR(30) NOT NULL,
    node_order INTEGER NOT NULL,
    node_status VARCHAR(20) DEFAULT 'pending',
    start_time DATETIME,
    end_time DATETIME,
    duration_ms INTEGER,
    input_data TEXT,
    output_data TEXT,
    error_message TEXT,
    error_details TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES nlquery_task(id)
);

-- 9. 查询历史表
CREATE TABLE IF NOT EXISTS nlquery_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    task_id VARCHAR(64) NOT NULL,
    user_question TEXT NOT NULL,
    generated_sql TEXT,
    task_status VARCHAR(20) NOT NULL,
    result_row_count INTEGER,
    execution_time_ms INTEGER,
    tags TEXT,
    category VARCHAR(100),
    access_count INTEGER DEFAULT 1,
    last_accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 10. 收藏查询表
CREATE TABLE IF NOT EXISTS nlquery_favorite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    favorite_title VARCHAR(200) NOT NULL,
    favorite_description TEXT,
    user_question TEXT NOT NULL,
    generated_sql TEXT,
    folder_name VARCHAR(100),
    tags TEXT,
    usage_count INTEGER DEFAULT 0,
    last_used_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 11. 查询反馈表
CREATE TABLE IF NOT EXISTS nlquery_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    feedback_type VARCHAR(50) NOT NULL,
    rating INTEGER,
    feedback_content TEXT,
    sql_accuracy INTEGER,
    result_relevance INTEGER,
    response_speed INTEGER,
    improvement_suggestions TEXT,
    expected_result TEXT,
    is_processed BOOLEAN DEFAULT 0,
    admin_response TEXT,
    processed_at DATETIME,
    processed_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES nlquery_task(id)
);

-- 12. 查询模板表
CREATE TABLE IF NOT EXISTS nlquery_template (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_name VARCHAR(200) NOT NULL,
    template_description TEXT,
    category VARCHAR(100),
    question_template TEXT NOT NULL,
    sql_template TEXT,
    parameters TEXT,
    required_tables TEXT,
    required_themes TEXT,
    usage_count INTEGER DEFAULT 0,
    success_rate INTEGER,
    is_active BOOLEAN DEFAULT 1,
    is_public BOOLEAN DEFAULT 0,
    created_by INTEGER,
    updated_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 13. 系统用户表
CREATE TABLE IF NOT EXISTS sys_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    nickname VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    password_hash VARCHAR(255),
    salt VARCHAR(32),
    avatar VARCHAR(500),
    gender VARCHAR(10),
    birthday DATETIME,
    department VARCHAR(100),
    position VARCHAR(100),
    is_active BOOLEAN DEFAULT 1,
    is_deleted BOOLEAN DEFAULT 0,
    last_login_time DATETIME,
    last_login_ip VARCHAR(50),
    login_count INTEGER DEFAULT 0,
    settings TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER
);

-- 14. 系统角色表
CREATE TABLE IF NOT EXISTS sys_role (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_code VARCHAR(50) NOT NULL UNIQUE,
    role_name VARCHAR(100) NOT NULL,
    role_description TEXT,
    is_active BOOLEAN DEFAULT 1,
    is_system BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER
);

-- 15. 系统权限表
CREATE TABLE IF NOT EXISTS sys_permission (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    permission_code VARCHAR(100) NOT NULL UNIQUE,
    permission_name VARCHAR(200) NOT NULL,
    permission_type VARCHAR(20) NOT NULL,
    permission_description TEXT,
    data_theme_id INTEGER,
    table_id INTEGER,
    menu_path VARCHAR(200),
    menu_component VARCHAR(200),
    menu_icon VARCHAR(100),
    parent_id INTEGER,
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER,
    FOREIGN KEY (data_theme_id) REFERENCES metadata_data_theme(id),
    FOREIGN KEY (table_id) REFERENCES metadata_table(id),
    FOREIGN KEY (parent_id) REFERENCES sys_permission(id)
);

-- 16. 用户角色关联表
CREATE TABLE IF NOT EXISTS sys_user_role (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (user_id) REFERENCES sys_user(id),
    FOREIGN KEY (role_id) REFERENCES sys_role(id)
);

-- 17. 角色权限关联表
CREATE TABLE IF NOT EXISTS sys_role_permission (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (role_id) REFERENCES sys_role(id),
    FOREIGN KEY (permission_id) REFERENCES sys_permission(id)
);

-- 18. 系统日志表
CREATE TABLE IF NOT EXISTS sys_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_level VARCHAR(20) NOT NULL,
    module VARCHAR(100),
    operation VARCHAR(200),
    message TEXT,
    user_id INTEGER,
    username VARCHAR(50),
    request_id VARCHAR(64),
    request_method VARCHAR(10),
    request_url VARCHAR(500),
    request_params TEXT,
    request_ip VARCHAR(50),
    user_agent VARCHAR(500),
    response_status INTEGER,
    response_time_ms INTEGER,
    error_code VARCHAR(50),
    error_message TEXT,
    stack_trace TEXT,
    business_data TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 19. 系统配置表
CREATE TABLE IF NOT EXISTS sys_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    config_type VARCHAR(20) NOT NULL,
    config_description TEXT,
    data_type VARCHAR(20) DEFAULT 'string',
    is_encrypted BOOLEAN DEFAULT 0,
    is_readonly BOOLEAN DEFAULT 0,
    validation_rule VARCHAR(500),
    default_value TEXT,
    config_group VARCHAR(100),
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER
);

-- 20. 系统任务表
CREATE TABLE IF NOT EXISTS sys_task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name VARCHAR(200) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    task_description TEXT,
    cron_expression VARCHAR(100),
    is_enabled BOOLEAN DEFAULT 1,
    last_run_time DATETIME,
    next_run_time DATETIME,
    run_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    task_params TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_metadata_table_name_en ON metadata_table(table_name_en);
CREATE INDEX IF NOT EXISTS idx_metadata_field_table_id ON metadata_field(table_id);
CREATE INDEX IF NOT EXISTS idx_metadata_field_name_en ON metadata_field(field_name_en);
CREATE INDEX IF NOT EXISTS idx_nlquery_task_user_id ON nlquery_task(user_id);
CREATE INDEX IF NOT EXISTS idx_nlquery_task_status ON nlquery_task(task_status);
CREATE INDEX IF NOT EXISTS idx_nlquery_task_created_at ON nlquery_task(created_at);
CREATE INDEX IF NOT EXISTS idx_nlquery_history_user_id ON nlquery_history(user_id);
CREATE INDEX IF NOT EXISTS idx_sys_user_username ON sys_user(username);
CREATE INDEX IF NOT EXISTS idx_sys_log_created_at ON sys_log(created_at);
CREATE INDEX IF NOT EXISTS idx_sys_log_user_id ON sys_log(user_id);