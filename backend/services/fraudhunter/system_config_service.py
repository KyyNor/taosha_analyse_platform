"""
系统热配置管理服务
"""

import io
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
import pandas as pd

from models.fraudhunter.model_execution_tracking import FraudHunterSystemConfig
from schemas.fraudhunter.system_config import (
    SystemConfigCreate,
    SystemConfigUpdate,
)
from utils.logger import logger


class SystemConfigManager:
    """系统热配置管理服务"""

    def __init__(self, db: Session):
        self.db = db

    def list_configs(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        category: Optional[str] = None
    ) -> Tuple[List[FraudHunterSystemConfig], int]:
        """获取配置列表

        Args:
            page: 页码
            page_size: 每页数量
            search: 搜索关键词（配置键或描述）
            category: 分类筛选

        Returns:
            (配置列表, 总数)
        """
        query = self.db.query(FraudHunterSystemConfig)

        # 分类筛选
        if category:
            query = query.filter(FraudHunterSystemConfig.config_category == category)

        # 搜索
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    FraudHunterSystemConfig.config_key.ilike(search_pattern),
                    FraudHunterSystemConfig.config_desc.ilike(search_pattern)
                )
            )

        # 总数
        total = query.count()

        # 排序和分页
        items = query.order_by(
            FraudHunterSystemConfig.sort_order,
            FraudHunterSystemConfig.id.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return items, total

    def get_config(self, config_id: int) -> Optional[FraudHunterSystemConfig]:
        """获取单个配置

        Args:
            config_id: 配置ID

        Returns:
            配置对象，不存在则返回None
        """
        return self.db.query(FraudHunterSystemConfig).filter(
            FraudHunterSystemConfig.id == config_id
        ).first()

    def get_config_by_key(self, config_key: str) -> Optional[FraudHunterSystemConfig]:
        """根据配置键获取配置

        Args:
            config_key: 配置键

        Returns:
            配置对象，不存在则返回None
        """
        return self.db.query(FraudHunterSystemConfig).filter(
            FraudHunterSystemConfig.config_key == config_key
        ).first()

    def create_config(self, data: SystemConfigCreate) -> FraudHunterSystemConfig:
        """创建配置

        Args:
            data: 创建数据

        Returns:
            创建的配置对象

        Raises:
            ValueError: 如果配置键已存在
        """
        # 检查配置键唯一性
        existing = self.get_config_by_key(data.config_key)
        if existing:
            raise ValueError(f"配置键已存在: {data.config_key}")

        # 创建配置
        db_config = FraudHunterSystemConfig(
            config_category=data.config_category,
            config_key=data.config_key,
            config_desc=data.config_desc,
            config_type=data.config_type,
            config_value=data.config_value,
            sql_in_convert=1 if data.sql_in_convert else 0,
            sort_order=data.sort_order
        )

        self.db.add(db_config)
        self.db.commit()
        self.db.refresh(db_config)

        logger.info(f"创建系统配置成功: {db_config.config_key}, ID={db_config.id}")
        return db_config

    def update_config(
        self,
        config_id: int,
        data: SystemConfigUpdate
    ) -> FraudHunterSystemConfig:
        """更新配置

        Args:
            config_id: 配置ID
            data: 更新数据

        Returns:
            更新后的配置对象

        Raises:
            ValueError: 如果配置不存在或配置键冲突
        """
        db_config = self.get_config(config_id)
        if not db_config:
            raise ValueError(f"配置不存在: {config_id}")

        # 如果修改了配置键，检查唯一性
        if data.config_key != db_config.config_key:
            existing = self.get_config_by_key(data.config_key)
            if existing:
                raise ValueError(f"配置键已存在: {data.config_key}")

        # 更新字段
        db_config.config_category = data.config_category
        db_config.config_key = data.config_key
        db_config.config_desc = data.config_desc
        db_config.config_type = data.config_type
        db_config.config_value = data.config_value
        db_config.sql_in_convert = 1 if data.sql_in_convert else 0
        db_config.sort_order = data.sort_order

        self.db.commit()
        self.db.refresh(db_config)

        logger.info(f"更新系统配置成功: {db_config.config_key}, ID={db_config.id}")
        return db_config

    def parse_excel(self, file_content: bytes) -> Dict[str, Any]:
        """解析Excel文件，返回预览数据

        Args:
            file_content: Excel文件内容

        Returns:
            {
                'columns': ['列名1', '列名2', ...],
                'data': [{'列名1': 值1, '列名2': 值2}, ...],
                'row_count': 行数
            }

        Raises:
            ValueError: 如果文件格式错误
        """
        try:
            df = pd.read_excel(io.BytesIO(file_content))

            # 转换为字典列表
            data = df.to_dict(orient='records')

            # 处理NaN值
            for row in data:
                for key, value in row.items():
                    if pd.isna(value):
                        row[key] = None

            return {
                'columns': list(df.columns),
                'data': data,
                'row_count': len(data)
            }
        except Exception as e:
            logger.error(f"解析Excel文件失败: {e}")
            raise ValueError(f"解析Excel文件失败: {str(e)}")

    def build_sql_variable_dict(self) -> Dict[str, Any]:
        """构建SQL变量替换字典

        用于实时指标任务中的SQL变量替换。
        仅返回 config_category='sql_variable' 的配置。

        Returns:
            变量字典 {配置键: 值}
        """
        configs = self.db.query(FraudHunterSystemConfig).filter(
            FraudHunterSystemConfig.config_category == 'sql_variable'
        ).all()

        result = {}
        for c in configs:
            value = c.config_value.get('value')

            if c.config_type == 'string':
                # 简单值：直接使用
                result[c.config_key] = str(value) if value is not None else ''

            elif c.config_type == 'list':
                if c.sql_in_convert:
                    # 转换为SQL IN格式: 'a','b','c'
                    if isinstance(value, list):
                        tmp_list = [f"'{v}'" for v in value]
                        result[c.config_key] = ','.join(tmp_list)
                    else:
                        result[c.config_key] = ''
                else:
                    # 保持列表格式
                    result[c.config_key] = value if value else []

            elif c.config_type == 'json_list':
                # JSON列表：保持原样
                result[c.config_key] = value if value else []

        logger.debug(f"构建SQL变量字典完成: {list(result.keys())}")
        return result

    def get_config_value(self, config_key: str, default: Any = None) -> Any:
        """获取配置值（便捷方法）

        Args:
            config_key: 配置键
            default: 默认值

        Returns:
            配置值，不存在则返回默认值
        """
        config = self.get_config_by_key(config_key)
        if not config:
            return default
        return config.config_value.get('value', default)

    def export_json_list_as_excel(self, config_id: int) -> bytes:
        """导出配置（必须是 json_list 类型）为 Excel，直接输出 json_list.value

        Args:
            config_id: 配置ID

        Returns:
            Excel 文件字节内容

        Raises:
            ValueError: 配置不存在或非 json_list 类型
        """
        cfg = self.get_config(config_id)
        if not cfg:
            raise ValueError(f"配置不存在: {config_id}")
        raw = cfg.config_value.get("value") if isinstance(cfg.config_value, dict) else None
        if not isinstance(raw, list):
            raise ValueError("该配置不是 JSON列表 类型，无法导出")

        if not raw:
            df = pd.DataFrame()
        else:
            df = pd.DataFrame(raw)

        from utils.excel_exporter import create_excel_exporter
        exporter = create_excel_exporter()
        output = exporter.export_single_sheet(df, sheet_name=cfg.config_key[:31])
        return output.getvalue()
