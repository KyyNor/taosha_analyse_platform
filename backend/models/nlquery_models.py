"""
自然语言查询相关数据模型
"""
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from models import Base


class TaskStatusEnum(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"        # 待处理
    RUNNING = "running"        # 运行中
    SUCCESS = "success"        # 成功
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消
    TIMEOUT = "timeout"        # 超时


class QueryTypeEnum(str, Enum):
    """查询类型枚举"""
    NATURAL_LANGUAGE = "natural_language"  # 自然语言查询
    SQL_DIRECT = "sql_direct"              # 直接SQL查询
    TEMPLATE = "template"                  # 模板查询


class NodeTypeEnum(str, Enum):
    """工作流节点类型枚举"""
    SQL_GENERATION = "sql_generation"      # SQL生成
    SQL_VALIDATION = "sql_validation"      # SQL验证
    SQL_EXECUTION = "sql_execution"        # SQL执行
    RESULT_PROCESSING = "result_processing" # 结果处理
    ERROR_HANDLING = "error_handling"      # 错误处理


class NodeStatusEnum(str, Enum):
    """节点状态枚举"""
    PENDING = "pending"        # 待执行
    RUNNING = "running"        # 执行中
    SUCCESS = "success"        # 成功
    FAILED = "failed"          # 失败
    SKIPPED = "skipped"        # 跳过


class NlqueryTask(Base):
    """自然语言查询任务表"""
    __tablename__ = "nlquery_task"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    task_id = Column(String(64), nullable=False, unique=True, comment="任务UUID")
    user_id = Column(BigInteger, nullable=False, comment="用户ID")
    
    # 查询信息
    user_question = Column(Text, nullable=False, comment="用户问题")
    query_type = Column(SQLEnum(QueryTypeEnum), default=QueryTypeEnum.NATURAL_LANGUAGE, comment="查询类型")
    selected_theme_id = Column(BigInteger, comment="选择的数据主题ID")
    selected_table_ids = Column(JSON, comment="选择的表ID列表")
    
    # 任务状态
    task_status = Column(SQLEnum(TaskStatusEnum), default=TaskStatusEnum.PENDING, comment="任务状态")
    progress_percentage = Column(Integer, default=0, comment="进度百分比")
    current_step = Column(String(100), comment="当前步骤")
    
    # SQL相关
    generated_sql = Column(Text, comment="生成的SQL")
    final_sql = Column(Text, comment="最终执行的SQL")
    sql_validation_result = Column(JSON, comment="SQL验证结果")
    
    # 执行结果
    execution_result = Column(JSON, comment="执行结果")
    result_row_count = Column(Integer, comment="结果行数")
    result_columns = Column(JSON, comment="结果列信息")
    result_data = Column(JSON, comment="结果数据（截取前100行）")
    
    # 错误信息
    error_message = Column(Text, comment="错误信息")
    error_code = Column(String(50), comment="错误代码")
    error_details = Column(JSON, comment="错误详情")
    
    # 性能信息
    start_time = Column(DateTime, comment="开始时间")
    end_time = Column(DateTime, comment="结束时间")
    duration_seconds = Column(Integer, comment="执行时长(秒)")
    
    # 模型信息
    llm_model = Column(String(100), comment="使用的LLM模型")
    llm_tokens_used = Column(Integer, comment="使用的Token数量")
    prompt_template = Column(Text, comment="使用的提示词模板")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关联关系
    workflow_nodes = relationship("NlqueryWorkflowNode", back_populates="task", cascade="all, delete-orphan")
    feedback = relationship("NlqueryFeedback", back_populates="task")

    def __repr__(self):
        return f"<NlqueryTask(id={self.id}, task_id='{self.task_id}', status='{self.task_status}')>"


class NlqueryWorkflowNode(Base):
    """查询工作流节点表"""
    __tablename__ = "nlquery_workflow_node"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    task_id = Column(BigInteger, ForeignKey("nlquery_task.id"), nullable=False, comment="任务ID")
    
    # 节点信息
    node_name = Column(String(100), nullable=False, comment="节点名称")
    node_type = Column(SQLEnum(NodeTypeEnum), nullable=False, comment="节点类型")
    node_order = Column(Integer, nullable=False, comment="节点顺序")
    
    # 节点状态
    node_status = Column(SQLEnum(NodeStatusEnum), default=NodeStatusEnum.PENDING, comment="节点状态")
    start_time = Column(DateTime, comment="开始时间")
    end_time = Column(DateTime, comment="结束时间")
    duration_ms = Column(Integer, comment="执行时长(毫秒)")
    
    # 输入输出
    input_data = Column(JSON, comment="输入数据")
    output_data = Column(JSON, comment="输出数据")
    
    # 错误信息
    error_message = Column(Text, comment="错误信息")
    error_details = Column(JSON, comment="错误详情")
    
    # 重试信息
    retry_count = Column(Integer, default=0, comment="重试次数")
    max_retries = Column(Integer, default=3, comment="最大重试次数")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关联关系
    task = relationship("NlqueryTask", back_populates="workflow_nodes")

    def __repr__(self):
        return f"<NlqueryWorkflowNode(id={self.id}, node_name='{self.node_name}', status='{self.node_status}')>"


class NlqueryHistory(Base):
    """查询历史表"""
    __tablename__ = "nlquery_history"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    user_id = Column(BigInteger, nullable=False, comment="用户ID")
    task_id = Column(String(64), nullable=False, comment="任务UUID")
    
    # 查询信息
    user_question = Column(Text, nullable=False, comment="用户问题")
    generated_sql = Column(Text, comment="生成的SQL")
    task_status = Column(SQLEnum(TaskStatusEnum), nullable=False, comment="任务状态")
    
    # 结果信息
    result_row_count = Column(Integer, comment="结果行数")
    execution_time_ms = Column(Integer, comment="执行时间(毫秒)")
    
    # 标签和分类
    tags = Column(JSON, comment="标签列表")
    category = Column(String(100), comment="查询分类")
    
    # 使用统计
    access_count = Column(Integer, default=1, comment="访问次数")
    last_accessed_at = Column(DateTime, default=func.now(), comment="最后访问时间")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<NlqueryHistory(id={self.id}, task_id='{self.task_id}', status='{self.task_status}')>"


class NlqueryFavorite(Base):
    """收藏查询表"""
    __tablename__ = "nlquery_favorite"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    user_id = Column(BigInteger, nullable=False, comment="用户ID")
    
    # 收藏信息
    favorite_title = Column(String(200), nullable=False, comment="收藏标题")
    favorite_description = Column(Text, comment="收藏描述")
    
    # 查询信息
    user_question = Column(Text, nullable=False, comment="用户问题")
    generated_sql = Column(Text, comment="生成的SQL")
    
    # 分组和标签
    folder_name = Column(String(100), comment="文件夹名称")
    tags = Column(JSON, comment="标签列表")
    
    # 使用统计
    usage_count = Column(Integer, default=0, comment="使用次数")
    last_used_at = Column(DateTime, comment="最后使用时间")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<NlqueryFavorite(id={self.id}, favorite_title='{self.favorite_title}')>"


class NlqueryFeedback(Base):
    """查询反馈表"""
    __tablename__ = "nlquery_feedback"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    task_id = Column(BigInteger, ForeignKey("nlquery_task.id"), nullable=False, comment="任务ID")
    user_id = Column(BigInteger, nullable=False, comment="用户ID")
    
    # 反馈信息
    feedback_type = Column(String(50), nullable=False, comment="反馈类型(good/bad/suggestion)")
    rating = Column(Integer, comment="评分(1-5)")
    feedback_content = Column(Text, comment="反馈内容")
    
    # 具体问题分类
    sql_accuracy = Column(Integer, comment="SQL准确性评分")
    result_relevance = Column(Integer, comment="结果相关性评分")
    response_speed = Column(Integer, comment="响应速度评分")
    
    # 改进建议
    improvement_suggestions = Column(Text, comment="改进建议")
    expected_result = Column(Text, comment="期望的结果")
    
    # 状态
    is_processed = Column(Boolean, default=False, comment="是否已处理")
    admin_response = Column(Text, comment="管理员回复")
    processed_at = Column(DateTime, comment="处理时间")
    processed_by = Column(BigInteger, comment="处理人ID")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关联关系
    task = relationship("NlqueryTask", back_populates="feedback")

    def __repr__(self):
        return f"<NlqueryFeedback(id={self.id}, feedback_type='{self.feedback_type}')>"


class NlqueryTemplate(Base):
    """查询模板表"""
    __tablename__ = "nlquery_template"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    
    # 模板信息
    template_name = Column(String(200), nullable=False, comment="模板名称")
    template_description = Column(Text, comment="模板描述")
    category = Column(String(100), comment="模板分类")
    
    # 模板内容
    question_template = Column(Text, nullable=False, comment="问题模板")
    sql_template = Column(Text, comment="SQL模板")
    
    # 参数配置
    parameters = Column(JSON, comment="模板参数配置")
    required_tables = Column(JSON, comment="需要的表列表")
    required_themes = Column(JSON, comment="需要的主题列表")
    
    # 使用统计
    usage_count = Column(Integer, default=0, comment="使用次数")
    success_rate = Column(Integer, comment="成功率(%)")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_public = Column(Boolean, default=False, comment="是否公共模板")
    
    # 审计字段
    created_by = Column(BigInteger, comment="创建人ID")
    updated_by = Column(BigInteger, comment="更新人ID")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<NlqueryTemplate(id={self.id}, template_name='{self.template_name}')>"