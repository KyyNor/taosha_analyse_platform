-- 操作会话记录表
CREATE TABLE IF NOT EXISTS operation_sessions (
    session_id VARCHAR(36) PRIMARY KEY,           -- 唯一ID (UUID)
    operation_type VARCHAR(100) NOT NULL,         -- 操作端口/接口名称
    operator VARCHAR(100),                        -- 操作人
    start_time TIMESTAMP NOT NULL,                -- 操作开始时间
    end_time TIMESTAMP,                           -- 操作完成时间
    total_duration INTEGER,                       -- 总耗时(毫秒)
    max_step_sequence INTEGER DEFAULT 0,          -- 最大次序号
    status VARCHAR(20) DEFAULT 'running',         -- 状态: running, completed, failed
    error_message TEXT,                           -- 最终错误信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 操作步骤详情表
CREATE TABLE IF NOT EXISTS operation_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(36) NOT NULL,              -- 关联session_id
    step_sequence INTEGER NOT NULL,               -- 步骤次序
    step_name VARCHAR(200) NOT NULL,              -- 流程名称/步骤名称
    input_data TEXT,                              -- 输入信息
    call_method VARCHAR(100),                     -- 调用方法类型
    output_data TEXT,                             -- 返回结果
    generated_sql TEXT,                           -- 生成的SQL(如有)
    error_message TEXT,                           -- 错误信息
    success BOOLEAN DEFAULT TRUE,                 -- 节点是否成功
    duration INTEGER,                             -- 耗时(毫秒)
    token_usage JSON,                             -- token消耗 {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    metadata JSON,                                -- 其他元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES operation_sessions(session_id)
);

-- 用户反馈表
CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_type VARCHAR(50) NOT NULL,           -- 反馈类型: session_feedback, step_feedback
    session_id VARCHAR(36) NOT NULL,              -- 关联session_id
    step_sequence INTEGER,                        -- 子流程次序(步骤反馈时需要)
    feedback_sentiment VARCHAR(20) NOT NULL,      -- 正向或负向: positive, negative, neutral
    feedback_content TEXT NOT NULL,               -- 反馈详情
    feedback_user VARCHAR(100),                   -- 反馈人
    feedback_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES operation_sessions(session_id)
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_operation_sessions_operator ON operation_sessions(operator);
CREATE INDEX IF NOT EXISTS idx_operation_sessions_operation_type ON operation_sessions(operation_type);
CREATE INDEX IF NOT EXISTS idx_operation_sessions_start_time ON operation_sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_operation_steps_session_id ON operation_steps(session_id);
CREATE INDEX IF NOT EXISTS idx_operation_steps_step_sequence ON operation_steps(session_id, step_sequence);
CREATE INDEX IF NOT EXISTS idx_user_feedback_session_id ON user_feedback(session_id);