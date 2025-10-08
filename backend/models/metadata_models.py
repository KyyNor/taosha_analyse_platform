"""
元数据相关数据模型
"""
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from models import Base


class UpdateMethodEnum(str, Enum):
    """更新方式枚举"""
    REAL_TIME = "real_time"  # 实时
    DAILY = "daily"          # 天级
    WEEKLY = "weekly"        # 周级
    MONTHLY = "monthly"      # 月级
    MANUAL = "manual"        # 手动


class FieldTypeEnum(str, Enum):
    """字段类型枚举"""
    STRING = "string"        # 字符串
    INTEGER = "integer"      # 整数
    FLOAT = "float"          # 浮点数
    DECIMAL = "decimal"      # 小数
    BOOLEAN = "boolean"      # 布尔值
    DATE = "date"            # 日期
    DATETIME = "datetime"    # 日期时间
    TIME = "time"            # 时间
    TEXT = "text"            # 长文本
    JSON = "json"            # JSON
    ARRAY = "array"          # 数组


class BusinessTypeEnum(str, Enum):
    """业务类型枚举"""
    DIMENSION = "dimension"  # 维度
    MEASURE = "measure"      # 度量
    ATTRIBUTE = "attribute"  # 属性
    KEY = "key"              # 主键/外键
    IDENTIFIER = "identifier" # 标识符


class DesensitizationTypeEnum(str, Enum):
    """脱敏类型枚举"""
    NONE = "none"            # 不脱敏
    MASK = "mask"            # 掩码
    ENCRYPT = "encrypt"      # 加密
    HASH = "hash"            # 哈希
    REPLACE = "replace"      # 替换


class TermTypeEnum(str, Enum):
    """术语类型枚举"""
    ADMIN = "admin"          # 管理员术语
    USER = "user"            # 用户术语


class MetadataDataTheme(Base):
    """数据主题表"""
    __tablename__ = "metadata_data_theme"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    theme_name = Column(String(100), nullable=False, comment="主题名称")
    theme_description = Column(Text, comment="主题描述")
    is_public = Column(Boolean, default=False, comment="是否公共主题")
    sort_order = Column(Integer, default=0, comment="排序序号")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    created_by = Column(BigInteger, comment="创建人ID")
    updated_by = Column(BigInteger, comment="更新人ID")

    # 关联关系
    tables = relationship("MetadataTable", secondary="metadata_table_theme", back_populates="themes")
    permissions = relationship("SysPermission", back_populates="data_theme")

    def __repr__(self):
        return f"<MetadataDataTheme(id={self.id}, theme_name='{self.theme_name}')>"


class MetadataTable(Base):
    """表元数据表"""
    __tablename__ = "metadata_table"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    table_name_cn = Column(String(200), nullable=False, comment="表中文名称")
    table_name_en = Column(String(200), nullable=False, comment="表英文名称")
    data_source = Column(String(100), comment="数据源")
    update_method = Column(SQLEnum(UpdateMethodEnum), default=UpdateMethodEnum.DAILY, comment="更新方式")
    table_description = Column(Text, comment="表描述")
    
    # 扩展字段
    schema_name = Column(String(100), comment="模式名称")
    table_type = Column(String(50), default="table", comment="表类型")
    row_count = Column(BigInteger, comment="行数")
    size_mb = Column(Integer, comment="大小(MB)")
    
    # 状态和权限
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_visible = Column(Boolean, default=True, comment="是否可见")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    created_by = Column(BigInteger, comment="创建人ID")
    updated_by = Column(BigInteger, comment="更新人ID")

    # 关联关系
    fields = relationship("MetadataField", back_populates="table", cascade="all, delete-orphan")
    themes = relationship("MetadataDataTheme", secondary="metadata_table_theme", back_populates="tables")
    permissions = relationship("SysPermission", back_populates="table")

    def __repr__(self):
        return f"<MetadataTable(id={self.id}, table_name_cn='{self.table_name_cn}')>"


class MetadataField(Base):
    """字段元数据表"""
    __tablename__ = "metadata_field"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    table_id = Column(BigInteger, ForeignKey("metadata_table.id"), nullable=False, comment="表ID")
    field_name_cn = Column(String(200), nullable=False, comment="字段中文名称")
    field_name_en = Column(String(200), nullable=False, comment="字段英文名称")
    field_type = Column(SQLEnum(FieldTypeEnum), nullable=False, comment="字段类型")
    business_type = Column(SQLEnum(BusinessTypeEnum), comment="业务类型")
    
    # 字段属性
    max_length = Column(Integer, comment="最大长度")
    precision = Column(Integer, comment="精度")
    scale = Column(Integer, comment="小数位数")
    is_nullable = Column(Boolean, default=True, comment="是否可为空")
    is_primary_key = Column(Boolean, default=False, comment="是否主键")
    is_foreign_key = Column(Boolean, default=False, comment="是否外键")
    default_value = Column(String(500), comment="默认值")
    
    # 业务属性
    field_description = Column(Text, comment="字段描述")
    business_rules = Column(Text, comment="业务规则")
    data_format = Column(String(100), comment="数据格式")
    value_range = Column(String(500), comment="取值范围")
    sample_values = Column(Text, comment="示例值")
    
    # 关联和脱敏
    association_id = Column(String(100), comment="关联ID")
    foreign_table_id = Column(BigInteger, comment="外键关联表ID")
    foreign_field_id = Column(BigInteger, comment="外键关联字段ID")
    desensitization_type = Column(SQLEnum(DesensitizationTypeEnum), default=DesensitizationTypeEnum.NONE, comment="脱敏类型")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_indexed = Column(Boolean, default=False, comment="是否有索引")
    
    # 统计信息
    distinct_count = Column(BigInteger, comment="唯一值数量")
    null_count = Column(BigInteger, comment="空值数量")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    created_by = Column(BigInteger, comment="创建人ID")
    updated_by = Column(BigInteger, comment="更新人ID")

    # 关联关系
    table = relationship("MetadataTable", back_populates="fields")

    def __repr__(self):
        return f"<MetadataField(id={self.id}, field_name_cn='{self.field_name_cn}')>"


class MetadataGlossary(Base):
    """术语表"""
    __tablename__ = "metadata_glossary"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    term_name = Column(String(200), nullable=False, comment="术语名称")
    term_description = Column(Text, nullable=False, comment="术语描述")
    term_type = Column(SQLEnum(TermTypeEnum), default=TermTypeEnum.USER, comment="术语类型")
    
    # 扩展信息
    category = Column(String(100), comment="术语分类")
    aliases = Column(Text, comment="别名（JSON数组）")
    related_terms = Column(Text, comment="相关术语（JSON数组）")
    examples = Column(Text, comment="使用示例")
    data_sources = Column(Text, comment="相关数据源")
    
    # 使用统计
    usage_count = Column(Integer, default=0, comment="使用次数")
    last_used_at = Column(DateTime, comment="最后使用时间")
    
    # 审计字段
    user_id = Column(BigInteger, comment="用户ID")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    created_by = Column(BigInteger, comment="创建人ID")
    updated_by = Column(BigInteger, comment="更新人ID")

    def __repr__(self):
        return f"<MetadataGlossary(id={self.id}, term_name='{self.term_name}')>"


class MetadataTableTheme(Base):
    """表与主题关联表"""
    __tablename__ = "metadata_table_theme"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    table_id = Column(BigInteger, ForeignKey("metadata_table.id"), nullable=False, comment="表ID")
    theme_id = Column(BigInteger, ForeignKey("metadata_data_theme.id"), nullable=False, comment="主题ID")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    created_by = Column(BigInteger, comment="创建人ID")

    def __repr__(self):
        return f"<MetadataTableTheme(table_id={self.table_id}, theme_id={self.theme_id})>"


class MetadataRelation(Base):
    """表关联关系表"""
    __tablename__ = "metadata_relation"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    source_table_id = Column(BigInteger, ForeignKey("metadata_table.id"), nullable=False, comment="源表ID")
    target_table_id = Column(BigInteger, ForeignKey("metadata_table.id"), nullable=False, comment="目标表ID")
    source_field_id = Column(BigInteger, ForeignKey("metadata_field.id"), comment="源字段ID")
    target_field_id = Column(BigInteger, ForeignKey("metadata_field.id"), comment="目标字段ID")
    
    relation_type = Column(String(50), nullable=False, comment="关系类型(one_to_one, one_to_many, many_to_many)")
    relation_name = Column(String(200), comment="关系名称")
    relation_description = Column(Text, comment="关系描述")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 审计字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    created_by = Column(BigInteger, comment="创建人ID")
    updated_by = Column(BigInteger, comment="更新人ID")

    def __repr__(self):
        return f"<MetadataRelation(id={self.id}, relation_type='{self.relation_type}')>"