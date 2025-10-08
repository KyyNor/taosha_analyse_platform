"""
系统管理相关数据模型
"""
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from models import Base


class PermissionTypeEnum(str, Enum):
    """权限类型枚举"""
    MENU = "menu"              # 菜单权限
    DATA_THEME = "data_theme"  # 数据主题权限
    DATA_TABLE = "data_table"  # 数据表权限


class LogLevelEnum(str, Enum):
    """日志级别枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ConfigTypeEnum(str, Enum):
    """配置类型枚举"""
    SYSTEM = "system"      # 系统配置
    LLM = "llm"           # LLM配置
    DATABASE = "database"  # 数据库配置
    SECURITY = "security"  # 安全配置


class SysUser(Base):
    """系统用户表"""
    __tablename__ = "sys_user"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    username = Column(String(50), nullable=False, unique=True, comment="用户名")
    nickname = Column(String(100), comment="昵称")
    email = Column(String(100), comment="邮箱")
    phone = Column(String(20), comment="手机号")
    
    # 认证信息
    password_hash = Column(String(255), comment="密码哈希")
    salt = Column(String(32), comment="密码盐值")
    
    # 个人信息
    avatar = Column(String(500), comment="头像URL")
    gender = Column(String(10), comment="性别")
    birthday = Column(DateTime, comment="生日")
    department = Column(String(100), comment="部门")
    position = Column(String(100), comment="职位")
    
    # 状态信息
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_deleted = Column(Boolean, default=False, comment="是否删除")
    last_login_time = Column(DateTime, comment="最后登录时间")
    last_login_ip = Column(String(50), comment="最后登录IP")
    login_count = Column(Integer, default=0, comment="登录次数")
    
    # 设置信息
    settings = Column(JSON, comment="用户设置")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    created_by = Column(BigInteger, comment="创建人ID")
    updated_by = Column(BigInteger, comment="更新人ID")

    # 关联关系
    user_roles = relationship("SysUserRole", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SysUser(id={self.id}, username='{self.username}')>"


class SysRole(Base):
    """系统角色表"""
    __tablename__ = "sys_role"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    role_code = Column(String(50), nullable=False, unique=True, comment="角色编码")
    role_name = Column(String(100), nullable=False, comment="角色名称")
    role_description = Column(Text, comment="角色描述")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_system = Column(Boolean, default=False, comment="是否系统角色")
    sort_order = Column(Integer, default=0, comment="排序序号")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    created_by = Column(BigInteger, comment="创建人ID")
    updated_by = Column(BigInteger, comment="更新人ID")

    # 关联关系
    user_roles = relationship("SysUserRole", back_populates="role")
    role_permissions = relationship("SysRolePermission", back_populates="role", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SysRole(id={self.id}, role_name='{self.role_name}')>"


class SysPermission(Base):
    """系统权限表"""
    __tablename__ = "sys_permission"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    permission_code = Column(String(100), nullable=False, unique=True, comment="权限编码")
    permission_name = Column(String(200), nullable=False, comment="权限名称")
    permission_type = Column(SQLEnum(PermissionTypeEnum), nullable=False, comment="权限类型")
    permission_description = Column(Text, comment="权限描述")
    
    # 关联资源
    data_theme_id = Column(BigInteger, ForeignKey("metadata_data_theme.id"), comment="数据主题ID")
    table_id = Column(BigInteger, ForeignKey("metadata_table.id"), comment="数据表ID")
    
    # 菜单权限相关
    menu_path = Column(String(200), comment="菜单路径")
    menu_component = Column(String(200), comment="菜单组件")
    menu_icon = Column(String(100), comment="菜单图标")
    parent_id = Column(BigInteger, ForeignKey("sys_permission.id"), comment="父权限ID")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序序号")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    created_by = Column(BigInteger, comment="创建人ID")
    updated_by = Column(BigInteger, comment="更新人ID")

    # 关联关系
    role_permissions = relationship("SysRolePermission", back_populates="permission")
    data_theme = relationship("MetadataDataTheme", back_populates="permissions")
    table = relationship("MetadataTable", back_populates="permissions")
    children = relationship("SysPermission", backref="parent", remote_side=[id])
    
    def __repr__(self):
        return f"<SysPermission(id={self.id}, permission_name='{self.permission_name}')>"


class SysUserRole(Base):
    """用户角色关联表"""
    __tablename__ = "sys_user_role"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    user_id = Column(BigInteger, ForeignKey("sys_user.id"), nullable=False, comment="用户ID")
    role_id = Column(BigInteger, ForeignKey("sys_role.id"), nullable=False, comment="角色ID")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    created_by = Column(BigInteger, comment="创建人ID")

    # 关联关系
    user = relationship("SysUser", back_populates="user_roles")
    role = relationship("SysRole", back_populates="user_roles")
    
    def __repr__(self):
        return f"<SysUserRole(user_id={self.user_id}, role_id={self.role_id})>"


class SysRolePermission(Base):
    """角色权限关联表"""
    __tablename__ = "sys_role_permission"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    role_id = Column(BigInteger, ForeignKey("sys_role.id"), nullable=False, comment="角色ID")
    permission_id = Column(BigInteger, ForeignKey("sys_permission.id"), nullable=False, comment="权限ID")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    created_by = Column(BigInteger, comment="创建人ID")

    # 关联关系
    role = relationship("SysRole", back_populates="role_permissions")
    permission = relationship("SysPermission", back_populates="role_permissions")
    
    def __repr__(self):
        return f"<SysRolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"


class SysLog(Base):
    """系统日志表"""
    __tablename__ = "sys_log"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    
    # 日志基本信息
    log_level = Column(SQLEnum(LogLevelEnum), nullable=False, comment="日志级别")
    module = Column(String(100), comment="模块名称")
    operation = Column(String(200), comment="操作名称")
    message = Column(Text, comment="日志消息")
    
    # 用户信息
    user_id = Column(BigInteger, comment="用户ID")
    username = Column(String(50), comment="用户名")
    
    # 请求信息
    request_id = Column(String(64), comment="请求ID")
    request_method = Column(String(10), comment="请求方法")
    request_url = Column(String(500), comment="请求URL")
    request_params = Column(JSON, comment="请求参数")
    request_ip = Column(String(50), comment="请求IP")
    user_agent = Column(String(500), comment="用户代理")
    
    # 响应信息
    response_status = Column(Integer, comment="响应状态码")
    response_time_ms = Column(Integer, comment="响应时间(毫秒)")
    
    # 错误信息
    error_code = Column(String(50), comment="错误代码")
    error_message = Column(Text, comment="错误消息")
    stack_trace = Column(Text, comment="堆栈跟踪")
    
    # 业务信息
    business_data = Column(JSON, comment="业务数据")
    
    # 时间信息
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    
    def __repr__(self):
        return f"<SysLog(id={self.id}, log_level='{self.log_level}', operation='{self.operation}')>"


class SysConfig(Base):
    """系统配置表"""
    __tablename__ = "sys_config"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    config_key = Column(String(100), nullable=False, unique=True, comment="配置键")
    config_value = Column(Text, comment="配置值")
    config_type = Column(SQLEnum(ConfigTypeEnum), nullable=False, comment="配置类型")
    config_description = Column(Text, comment="配置描述")
    
    # 配置属性
    data_type = Column(String(20), default="string", comment="数据类型")
    is_encrypted = Column(Boolean, default=False, comment="是否加密")
    is_readonly = Column(Boolean, default=False, comment="是否只读")
    
    # 验证规则
    validation_rule = Column(String(500), comment="验证规则")
    default_value = Column(Text, comment="默认值")
    
    # 分组
    config_group = Column(String(100), comment="配置分组")
    sort_order = Column(Integer, default=0, comment="排序序号")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    created_by = Column(BigInteger, comment="创建人ID")
    updated_by = Column(BigInteger, comment="更新人ID")
    
    def __repr__(self):
        return f"<SysConfig(id={self.id}, config_key='{self.config_key}')>"


class SysTask(Base):
    """系统任务表"""
    __tablename__ = "sys_task"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    task_name = Column(String(200), nullable=False, comment="任务名称")
    task_type = Column(String(50), nullable=False, comment="任务类型")
    task_description = Column(Text, comment="任务描述")
    
    # 调度配置
    cron_expression = Column(String(100), comment="Cron表达式")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    
    # 执行信息
    last_run_time = Column(DateTime, comment="最后执行时间")
    next_run_time = Column(DateTime, comment="下次执行时间")
    run_count = Column(Integer, default=0, comment="执行次数")
    success_count = Column(Integer, default=0, comment="成功次数")
    fail_count = Column(Integer, default=0, comment="失败次数")
    
    # 任务参数
    task_params = Column(JSON, comment="任务参数")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    created_by = Column(BigInteger, comment="创建人ID")
    updated_by = Column(BigInteger, comment="更新人ID")
    
    def __repr__(self):
        return f"<SysTask(id={self.id}, task_name='{self.task_name}')>"