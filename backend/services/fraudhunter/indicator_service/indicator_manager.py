"""
指标定义管理服务
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from models.fraudhunter.indicator import (
    FraudHunterIndicatorDefinition,
    FraudHunterIndicatorHistory,
    FraudHunterIndicatorGroup
)
from schemas.fraudhunter.indicator import (
    IndicatorCreate,
    IndicatorUpdate
)
from utils.logger import logger


class IndicatorManager:
    """指标定义管理服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_indicator(
        self,
        indicator_data: IndicatorCreate,
        created_by: str
    ) -> FraudHunterIndicatorDefinition:
        """创建指标

        Args:
            indicator_data: 指标创建数据
            created_by: 创建人

        Returns:
            创建的指标对象

        Raises:
            ValueError: 如果指标编码已存在或指标组不存在
        """
        # 验证编码唯一性
        existing = self.db.query(FraudHunterIndicatorDefinition).filter(
            FraudHunterIndicatorDefinition.indicator_code == indicator_data.indicator_code
        ).first()

        if existing:
            raise ValueError(f"指标编码已存在: {indicator_data.indicator_code}")

        # 验证指标组是否存在
        group = self.db.query(FraudHunterIndicatorGroup).filter(
            FraudHunterIndicatorGroup.id == indicator_data.indicator_group_id
        ).first()

        if not group:
            raise ValueError(f"指标组不存在: {indicator_data.indicator_group_id}")

        # 创建指标记录
        db_indicator = FraudHunterIndicatorDefinition(
            **indicator_data.model_dump(),
            created_by=created_by,
            status='draft',
            current_version=1,
            latest_version=1
        )

        self.db.add(db_indicator)
        self.db.flush()

        # 创建版本历史
        self._create_version_history(db_indicator, 'create', '初始创建', created_by)

        self.db.commit()
        self.db.refresh(db_indicator)

        logger.info(f"创建指标成功: {db_indicator.indicator_code}, ID={db_indicator.id}")
        return db_indicator

    def get_indicator(self, indicator_id: int) -> Optional[FraudHunterIndicatorDefinition]:
        """获取指标

        Args:
            indicator_id: 指标ID

        Returns:
            指标对象或None
        """
        return self.db.query(FraudHunterIndicatorDefinition).filter(
            FraudHunterIndicatorDefinition.id == indicator_id
        ).first()

    def get_indicator_by_code(self, indicator_code: str) -> Optional[FraudHunterIndicatorDefinition]:
        """根据编码获取指标

        Args:
            indicator_code: 指标编码

        Returns:
            指标对象或None
        """
        return self.db.query(FraudHunterIndicatorDefinition).filter(
            FraudHunterIndicatorDefinition.indicator_code == indicator_code
        ).first()

    def list_indicators(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        indicator_type: Optional[str] = None,
        indicator_group_id: Optional[int] = None,
        indicator_code: Optional[str] = None
    ) -> tuple[List[FraudHunterIndicatorDefinition], int]:
        """获取指标列表

        Args:
            page: 页码
            page_size: 每页数量
            status: 状态筛选
            indicator_type: 指标类型筛选
            indicator_group_id: 指标组ID筛选
            indicator_code: 编码筛选（模糊匹配）

        Returns:
            (指标列表, 总数)
        """
        query = self.db.query(FraudHunterIndicatorDefinition)

        # 状态筛选
        if status:
            query = query.filter(FraudHunterIndicatorDefinition.status == status)

        # 类型筛选
        if indicator_type:
            query = query.filter(FraudHunterIndicatorDefinition.indicator_type == indicator_type)

        # 指标组筛选
        if indicator_group_id:
            query = query.filter(FraudHunterIndicatorDefinition.indicator_group_id == indicator_group_id)

        # 编码筛选（模糊匹配）
        if indicator_code:
            query = query.filter(FraudHunterIndicatorDefinition.indicator_code.like(f"%{indicator_code}%"))

        # 总数
        total = query.count()

        # 分页
        offset = (page - 1) * page_size
        items = query.order_by(FraudHunterIndicatorDefinition.created_at.desc()).offset(offset).limit(page_size).all()

        return items, total

    def update_indicator(
        self,
        indicator_id: int,
        indicator_data: IndicatorUpdate,
        updated_by: str
    ) -> FraudHunterIndicatorDefinition:
        """更新指标

        Args:
            indicator_id: 指标ID
            indicator_data: 更新数据
            updated_by: 更新人

        Returns:
            更新后的指标对象

        Raises:
            ValueError: 如果指标不存在
        """
        db_indicator = self.get_indicator(indicator_id)
        if not db_indicator:
            raise ValueError(f"指标不存在: {indicator_id}")

        # 更新字段
        update_data = indicator_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_indicator, key, value)

        db_indicator.updated_by = updated_by
        db_indicator.latest_version += 1

        # 创建版本历史
        self._create_version_history(db_indicator, 'update', '更新配置', updated_by)

        self.db.commit()
        self.db.refresh(db_indicator)

        logger.info(f"更新指标成功: {db_indicator.indicator_code}, 新版本={db_indicator.latest_version}")
        return db_indicator

    def publish_indicator(
        self,
        indicator_id: int,
        version: int,
        updated_by: str,
        change_description: Optional[str] = None
    ) -> FraudHunterIndicatorDefinition:
        """发布指标

        Args:
            indicator_id: 指标ID
            version: 要发布的版本号
            updated_by: 更新人
            change_description: 变更说明

        Returns:
            发布后的指标对象

        Raises:
            ValueError: 如果指标不存在或版本号无效
        """
        db_indicator = self.get_indicator(indicator_id)
        if not db_indicator:
            raise ValueError(f"指标不存在: {indicator_id}")

        # 验证版本号
        if version > db_indicator.latest_version:
            raise ValueError(f"版本号不存在: {version}")

        # 更新发布版本
        db_indicator.current_version = version
        db_indicator.status = 'online'
        db_indicator.updated_by = updated_by

        # 创建版本历史
        self._create_version_history(
            db_indicator,
            'publish',
            change_description or f'发布版本{version}',
            updated_by
        )

        self.db.commit()
        self.db.refresh(db_indicator)

        logger.info(f"发布指标成功: {db_indicator.indicator_code}, 版本: {version}")
        return db_indicator

    def archive_indicator(
        self,
        indicator_id: int,
        updated_by: str
    ) -> FraudHunterIndicatorDefinition:
        """归档指标

        Args:
            indicator_id: 指标ID
            updated_by: 更新人

        Returns:
            归档后的指标对象

        Raises:
            ValueError: 如果指标不存在
        """
        db_indicator = self.get_indicator(indicator_id)
        if not db_indicator:
            raise ValueError(f"指标不存在: {indicator_id}")

        db_indicator.status = 'archived'
        db_indicator.updated_by = updated_by

        # 创建版本历史
        self._create_version_history(
            db_indicator,
            'archive',
            '归档指标',
            updated_by
        )

        self.db.commit()
        self.db.refresh(db_indicator)

        logger.info(f"归档指标成功: {db_indicator.indicator_code}")
        return db_indicator

    def delete_indicator(self, indicator_id: int) -> None:
        """删除指标（物理删除）

        Args:
            indicator_id: 指标ID

        Raises:
            ValueError: 如果指标不存在
        """
        db_indicator = self.get_indicator(indicator_id)
        if not db_indicator:
            raise ValueError(f"指标不存在: {indicator_id}")

        self.db.delete(db_indicator)
        self.db.commit()

        logger.info(f"删除指标成功: {db_indicator.indicator_code}")

    def get_version_history(
        self,
        indicator_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[FraudHunterIndicatorHistory], int]:
        """获取指标版本历史

        Args:
            indicator_id: 指标ID
            page: 页码
            page_size: 每页数量

        Returns:
            (历史记录列表, 总数)
        """
        query = self.db.query(FraudHunterIndicatorHistory).filter(
            FraudHunterIndicatorHistory.indicator_id == indicator_id
        )

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(FraudHunterIndicatorHistory.created_at.desc()).offset(offset).limit(page_size).all()

        return items, total

    def _create_version_history(
        self,
        indicator: FraudHunterIndicatorDefinition,
        change_type: str,
        change_description: str,
        created_by: str
    ) -> None:
        """创建版本历史记录

        Args:
            indicator: 指标对象
            change_type: 变更类型
            change_description: 变更说明
            created_by: 创建人
        """
        history = FraudHunterIndicatorHistory(
            indicator_id=indicator.id,
            version=indicator.latest_version,
            indicator_code=indicator.indicator_code,
            indicator_name=indicator.indicator_name,
            indicator_type=indicator.indicator_type,
            description=indicator.description,
            data_type=indicator.data_type,
            enum_values=indicator.enum_values,
            indicator_group_id=indicator.indicator_group_id,
            change_type=change_type,
            change_description=change_description,
            created_by=created_by
        )

        self.db.add(history)
        # 不要在这里commit，由调用方统一提交
