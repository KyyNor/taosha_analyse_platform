"""
宽表版本管理服务
"""

import hashlib
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, date
from models.fraudhunter.indicator import FraudHunterIndicatorDefinition
from models.fraudhunter.wide_table import (
    FraudHunterWideTableVersion,
    FraudHunterIndicatorRunProgress
)
from utils.logger import logger


class WideTableVersionManager:
    """宽表版本管理器"""

    # object_type到wide_table_name的映射
    OBJECT_TYPE_TO_TABLE_NAME = {
        'dep_acct_no': 'dep_acct_wide_table',
        'cust_no': 'cust_wide_table',
        'loan_acct_no': 'loan_acct_wide_table',
    }

    def __init__(self, db: Session):
        self.db = db

    def _get_wide_table_name(self, object_type: str) -> str:
        """根据object_type获取宽表名称

        Args:
            object_type: 对象类型（dep_acct_no/cust_no/loan_acct_no）

        Returns:
            宽表名称（dep_acct_wide_table/cust_wide_table/loan_acct_wide_table）
        """
        table_name = self.OBJECT_TYPE_TO_TABLE_NAME.get(object_type)
        if not table_name:
            raise ValueError(f"不支持的object_type: {object_type}")
        return table_name

    def generate_version_hash(
        self,
        online_indicators: List[FraudHunterIndicatorDefinition]
    ) -> Tuple[str, Dict[int, Dict]]:
        """生成版本号hash（完整64位SHA256）

        Args:
            online_indicators: 所有在线的离线指标列表（同一个object_type）

        Returns:
            (version_hash, indicator_metadata)
            - version_hash: SHA256 hash值（完整64位）
            - indicator_metadata: {indicator_id: {version, indicator_code, indicator_name, indicator_task_id}}
        """
        if not online_indicators:
            raise ValueError("在线指标列表不能为空")

        # 1. 按indicator_id升序排序
        sorted_indicators = sorted(online_indicators, key=lambda x: x.id)

        # 2. 拼接字符串: {id1}_{version1}#{id2}_{version2}#...
        parts = []
        indicator_metadata = {}

        for indicator in sorted_indicators:
            parts.append(f"{indicator.id}_{indicator.current_version}")
            indicator_metadata[indicator.id] = {
                "version": indicator.current_version,
                "indicator_code": indicator.indicator_code,
                "indicator_name": indicator.indicator_name,
                "indicator_type": indicator.indicator_type,
                "object_type": indicator.object_type,
                "indicator_task_id": indicator.indicator_task_id
            }

        version_string = "#".join(parts)

        # 3. 生成完整64位SHA256 hash
        version_hash = hashlib.sha256(version_string.encode('utf-8')).hexdigest()

        logger.info(
            f"生成版本号: {version_hash[:16]}..., "
            f"object_type={sorted_indicators[0].object_type}, "
            f"包含{len(sorted_indicators)}个指标"
        )
        logger.debug(f"版本字符串: {version_string}")

        return version_hash, indicator_metadata

    def get_current_online_indicators_by_object_type(
        self,
        object_type: str
    ) -> List[FraudHunterIndicatorDefinition]:
        """获取指定object_type的所有在线离线指标

        Args:
            object_type: 对象类型（dep_acct_no/cust_no/loan_acct_no）

        Returns:
            在线离线指标列表
        """
        indicators = self.db.query(FraudHunterIndicatorDefinition).filter(
            and_(
                FraudHunterIndicatorDefinition.status == 'online',
                FraudHunterIndicatorDefinition.indicator_type == 'offline',
                FraudHunterIndicatorDefinition.object_type == object_type
            )
        ).order_by(FraudHunterIndicatorDefinition.id).all()

        logger.info(f"查询到 {len(indicators)} 个object_type={object_type}的在线离线指标")
        return indicators

    def check_version_change_needed(self, object_type: str) -> bool:
        """检查指定object_type是否需要生成新版本

        对比当前在线指标集合与current版本的指标集合

        Args:
            object_type: 对象类型

        Returns:
            是否需要生成新版本
        """
        # 获取当前在线指标
        online_indicators = self.get_current_online_indicators_by_object_type(object_type)

        # 如果没有在线指标，无需创建版本
        if not online_indicators:
            logger.info(f"object_type={object_type}没有在线指标，无需创建版本")
            return False

        # 获取wide_table_name
        wide_table_name = self._get_wide_table_name(object_type)

        # 获取current版本
        current_version = self.db.query(FraudHunterWideTableVersion).filter(
            and_(
                FraudHunterWideTableVersion.wide_table_name == wide_table_name,
                FraudHunterWideTableVersion.status == 'current'
            )
        ).first()

        # 如果没有current版本，且有在线指标，需要创建
        if not current_version:
            logger.info(f"{wide_table_name}没有current版本，需要创建")
            return True

        # 生成当前在线指标的版本hash
        new_hash, _ = self.generate_version_hash(online_indicators)

        # 对比hash是否相同
        version_changed = (new_hash != current_version.version_hash)

        if version_changed:
            logger.info(
                f"检测到版本变更: {current_version.version_hash[:16]}... "
                f"-> {new_hash[:16]}..."
            )
        else:
            logger.debug(f"版本未变更: {current_version.version_hash[:16]}...")

        return version_changed

    def create_new_version(
        self,
        object_type: str,
        created_by: str = "system"
    ) -> Optional[FraudHunterWideTableVersion]:
        """为指定object_type创建新的target版本

        触发条件:
        1. 指标上线/下线
        2. 指标重新发布(版本号变更)

        流程:
        1. 检查是否有版本变更
        2. 如果已有target版本,标记为skipped
        3. 创建新的target版本

        Args:
            object_type: 对象类型（dep_acct_no/cust_no/loan_acct_no）
            created_by: 创建人

        Returns:
            新创建的版本对象,如果无需创建则返回None
        """
        # 1. 检查是否需要新版本
        if not self.check_version_change_needed(object_type):
            logger.info(f"object_type={object_type}无版本变更，无需创建新版本")
            return None

        # 2. 获取当前在线指标
        online_indicators = self.get_current_online_indicators_by_object_type(object_type)
        if not online_indicators:
            logger.warning(f"object_type={object_type}没有在线指标，无法创建版本")
            return None

        version_hash, indicator_metadata = self.generate_version_hash(online_indicators)

        # 3. 获取wide_table_name
        wide_table_name = self._get_wide_table_name(object_type)

        # 4. 检查该版本是否已存在
        existing_version = self.db.query(FraudHunterWideTableVersion).filter(
            FraudHunterWideTableVersion.version_hash == version_hash
        ).first()

        if existing_version:
            logger.warning(f"版本 {version_hash[:16]}... 已存在，状态: {existing_version.status}")
            return existing_version

        # 5. 将现有target版本标记为skipped
        existing_target = self.db.query(FraudHunterWideTableVersion).filter(
            and_(
                FraudHunterWideTableVersion.wide_table_name == wide_table_name,
                FraudHunterWideTableVersion.status == 'target'
            )
        ).first()

        if existing_target:
            existing_target.status = 'skipped'
            existing_target.skipped_at = datetime.utcnow()
            logger.info(f"将版本 {existing_target.version_hash[:16]}... 标记为skipped")

        # 6. 创建新版本
        new_version = FraudHunterWideTableVersion(
            wide_table_name=wide_table_name,
            version_hash=version_hash,
            indicator_metadata=indicator_metadata,
            status='target',
            target_at=datetime.utcnow(),
            created_by=created_by
        )

        self.db.add(new_version)
        self.db.commit()
        self.db.refresh(new_version)

        logger.info(
            f"创建新版本成功: {wide_table_name}, "
            f"version_hash={version_hash[:16]}..., "
            f"包含 {len(online_indicators)} 个指标"
        )
        return new_version

    def check_target_version_ready(
        self,
        target_version: FraudHunterWideTableVersion,
        etl_date: date
    ) -> Tuple[bool, List[Dict]]:
        """检查target版本是否可以同步为current

        检查该版本所有指标是否都有指定ETL日期的完成记录

        Args:
            target_version: 目标版本对象
            etl_date: 要检查的ETL日期

        Returns:
            (is_ready, missing_tasks)
            - is_ready: 是否准备就绪
            - missing_tasks: 未完成的任务列表
        """
        indicator_metadata = target_version.indicator_metadata

        if not indicator_metadata:
            return False, []

        missing_tasks = []

        for indicator_id, metadata in indicator_metadata.items():
            # 查询该指标在指定日期的运行进度
            indicator_task_id = metadata.get('indicator_task_id')

            if not indicator_task_id:
                missing_tasks.append({
                    "indicator_id": indicator_id,
                    "indicator_code": metadata.get('indicator_code'),
                    "reason": "未关联指标任务"
                })
                continue

            progress = self.db.query(FraudHunterIndicatorRunProgress).filter(
                and_(
                    FraudHunterIndicatorRunProgress.indicator_task_id == indicator_task_id,
                    FraudHunterIndicatorRunProgress.etl_date == etl_date,
                    FraudHunterIndicatorRunProgress.indicator_version == metadata['version']
                )
            ).first()

            if not progress:
                missing_tasks.append({
                    "indicator_id": indicator_id,
                    "indicator_code": metadata.get('indicator_code'),
                    "indicator_task_id": indicator_task_id,
                    "etl_date": str(etl_date),
                    "version": metadata['version'],
                    "reason": "未找到运行进度记录"
                })

        is_ready = len(missing_tasks) == 0

        if is_ready:
            logger.info(
                f"版本 {target_version.version_hash[:16]}... "
                f"在 {etl_date} 的所有指标已完成"
            )
        else:
            logger.warning(
                f"版本 {target_version.version_hash[:16]}... "
                f"在 {etl_date} 还有 {len(missing_tasks)} 个指标未完成"
            )

        return is_ready, missing_tasks

    def promote_target_to_current(
        self,
        target_version: FraudHunterWideTableVersion
    ) -> FraudHunterWideTableVersion:
        """将target版本提升为current

        同时将旧的current版本标记为history

        Args:
            target_version: 目标版本对象

        Returns:
            更新后的版本对象
        """
        if target_version.status != 'target':
            raise ValueError(f"只能提升status='target'的版本，当前状态: {target_version.status}")

        # 1. 将旧的current版本标记为history
        old_current = self.db.query(FraudHunterWideTableVersion).filter(
            and_(
                FraudHunterWideTableVersion.wide_table_name == target_version.wide_table_name,
                FraudHunterWideTableVersion.status == 'current'
            )
        ).first()

        if old_current:
            old_current.status = 'history'
            old_current.history_at = datetime.utcnow()
            logger.info(f"将版本 {old_current.version_hash[:16]}... 标记为history")

        # 2. 提升target为current
        target_version.status = 'current'
        target_version.current_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(target_version)

        logger.info(f"版本 {target_version.version_hash[:16]}... 已提升为current")
        return target_version
