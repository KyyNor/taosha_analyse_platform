"""
指标组管理服务
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.fraudhunter.indicator import (
    FraudHunterIndicatorGroup,
    FraudHunterIndicatorGroupHistory
)
from schemas.fraudhunter.indicator import (
    IndicatorGroupCreate,
    IndicatorGroupUpdate
)
from utils.logger import logger


class IndicatorGroupManager:
    """指标组管理服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_indicator_group(
        self,
        group_data: IndicatorGroupCreate,
        created_by: str
    ) -> FraudHunterIndicatorGroup:
        """创建指标组

        Args:
            group_data: 指标组创建数据
            created_by: 创建人

        Returns:
            创建的指标组对象

        Raises:
            ValueError: 如果指标组编码已存在
        """
        # 验证编码唯一性
        existing = self.db.query(FraudHunterIndicatorGroup).filter(
            FraudHunterIndicatorGroup.group_code == group_data.group_code
        ).first()

        if existing:
            raise ValueError(f"指标组编码已存在: {group_data.group_code}")

        # 创建指标组记录
        db_group = FraudHunterIndicatorGroup(
            **group_data.model_dump(),
            created_by=created_by,
            status='draft',
            current_version=1,
            latest_version=1
        )

        self.db.add(db_group)
        self.db.flush()  # 获取ID但不提交

        # 创建版本历史
        self._create_version_history(db_group, 'create', '初始创建', created_by)

        self.db.commit()
        self.db.refresh(db_group)

        logger.info(f"创建指标组成功: {db_group.group_code}, ID={db_group.id}")
        return db_group

    def get_indicator_group(self, group_id: int) -> Optional[FraudHunterIndicatorGroup]:
        """获取指标组

        Args:
            group_id: 指标组ID

        Returns:
            指标组对象或None
        """
        return self.db.query(FraudHunterIndicatorGroup).filter(
            FraudHunterIndicatorGroup.id == group_id
        ).first()

    def get_indicator_group_by_code(self, group_code: str) -> Optional[FraudHunterIndicatorGroup]:
        """根据编码获取指标组

        Args:
            group_code: 指标组编码

        Returns:
            指标组对象或None
        """
        return self.db.query(FraudHunterIndicatorGroup).filter(
            FraudHunterIndicatorGroup.group_code == group_code
        ).first()

    def list_indicator_groups(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        group_code: Optional[str] = None
    ) -> tuple[List[FraudHunterIndicatorGroup], int]:
        """获取指标组列表

        Args:
            page: 页码
            page_size: 每页数量
            status: 状态筛选
            group_code: 编码筛选（模糊匹配）

        Returns:
            (指标组列表, 总数)
        """
        query = self.db.query(FraudHunterIndicatorGroup)

        # 状态筛选
        if status:
            query = query.filter(FraudHunterIndicatorGroup.status == status)

        # 编码筛选（模糊匹配）
        if group_code:
            query = query.filter(FraudHunterIndicatorGroup.group_code.like(f"%{group_code}%"))

        # 总数
        total = query.count()

        # 分页
        offset = (page - 1) * page_size
        items = query.order_by(FraudHunterIndicatorGroup.created_at.desc()).offset(offset).limit(page_size).all()

        return items, total

    def update_indicator_group(
        self,
        group_id: int,
        group_data: IndicatorGroupUpdate,
        updated_by: str
    ) -> FraudHunterIndicatorGroup:
        """更新指标组

        Args:
            group_id: 指标组ID
            group_data: 更新数据
            updated_by: 更新人

        Returns:
            更新后的指标组对象

        Raises:
            ValueError: 如果指标组不存在或状态不允许更新
        """
        db_group = self.get_indicator_group(group_id)
        if not db_group:
            raise ValueError(f"指标组不存在: {group_id}")

        # 只有draft状态才允许更新逻辑内容
        if db_group.status != 'draft' and group_data.logic_content:
            raise ValueError("只有草稿状态的指标组才允许修改逻辑内容")

        # 更新字段
        update_data = group_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_group, key, value)

        db_group.updated_by = updated_by
        db_group.latest_version += 1

        # 创建版本历史
        self._create_version_history(db_group, 'update', '更新配置', updated_by)

        self.db.commit()
        self.db.refresh(db_group)

        logger.info(f"更新指标组成功: {db_group.group_code}, 新版本={db_group.latest_version}")
        return db_group

    def publish_indicator_group(
        self,
        group_id: int,
        version: int,
        updated_by: str,
        change_description: Optional[str] = None
    ) -> FraudHunterIndicatorGroup:
        """发布指标组

        Args:
            group_id: 指标组ID
            version: 要发布的版本号
            updated_by: 更新人
            change_description: 变更说明

        Returns:
            发布后的指标组对象

        Raises:
            ValueError: 如果指标组不存在或版本号无效
        """
        db_group = self.get_indicator_group(group_id)
        if not db_group:
            raise ValueError(f"指标组不存在: {group_id}")

        # 验证版本号
        if version > db_group.latest_version:
            raise ValueError(f"版本号不存在: {version}")

        # 更新发布版本
        db_group.current_version = version
        db_group.status = 'online'
        db_group.updated_by = updated_by

        # 创建版本历史
        self._create_version_history(
            db_group,
            'publish',
            change_description or f'发布版本{version}',
            updated_by
        )

        self.db.commit()
        self.db.refresh(db_group)

        logger.info(f"发布指标组成功: {db_group.group_code}, 版本: {version}")
        return db_group

    def archive_indicator_group(
        self,
        group_id: int,
        updated_by: str
    ) -> FraudHunterIndicatorGroup:
        """归档指标组

        Args:
            group_id: 指标组ID
            updated_by: 更新人

        Returns:
            归档后的指标组对象

        Raises:
            ValueError: 如果指标组不存在
        """
        db_group = self.get_indicator_group(group_id)
        if not db_group:
            raise ValueError(f"指标组不存在: {group_id}")

        db_group.status = 'archived'
        db_group.updated_by = updated_by

        # 创建版本历史
        self._create_version_history(
            db_group,
            'archive',
            '归档指标组',
            updated_by
        )

        self.db.commit()
        self.db.refresh(db_group)

        logger.info(f"归档指标组成功: {db_group.group_code}")
        return db_group

    def delete_indicator_group(self, group_id: int) -> None:
        """删除指标组（物理删除）

        Args:
            group_id: 指标组ID

        Raises:
            ValueError: 如果指标组不存在或有关联指标
        """
        db_group = self.get_indicator_group(group_id)
        if not db_group:
            raise ValueError(f"指标组不存在: {group_id}")

        # 检查是否有关联指标
        if db_group.indicators and len(db_group.indicators) > 0:
            raise ValueError(f"指标组下存在{len(db_group.indicators)}个指标，无法删除")

        self.db.delete(db_group)
        self.db.commit()

        logger.info(f"删除指标组成功: {db_group.group_code}")

    def get_version_history(
        self,
        group_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[FraudHunterIndicatorGroupHistory], int]:
        """获取指标组版本历史

        Args:
            group_id: 指标组ID
            page: 页码
            page_size: 每页数量

        Returns:
            (历史记录列表, 总数)
        """
        query = self.db.query(FraudHunterIndicatorGroupHistory).filter(
            FraudHunterIndicatorGroupHistory.group_id == group_id
        )

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(FraudHunterIndicatorGroupHistory.created_at.desc()).offset(offset).limit(page_size).all()

        return items, total

    def _create_version_history(
        self,
        group: FraudHunterIndicatorGroup,
        change_type: str,
        change_description: str,
        created_by: str
    ) -> None:
        """创建版本历史记录

        Args:
            group: 指标组对象
            change_type: 变更类型
            change_description: 变更说明
            created_by: 创建人
        """
        history = FraudHunterIndicatorGroupHistory(
            group_id=group.id,
            version=group.latest_version,
            group_code=group.group_code,
            group_name=group.group_name,
            description=group.description,
            logic_type=group.logic_type,
            logic_content=group.logic_content,
            source_tables=group.source_tables,
            output_table=group.output_table,
            output_mode=group.output_mode,
            change_type=change_type,
            change_description=change_description,
            created_by=created_by
        )

        self.db.add(history)
        # 不要在这里commit，由调用方统一提交
