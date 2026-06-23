"""
宽表版本管理服务
"""

import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from models.fraudhunter.indicator import (
    FraudHunterIndicatorDefinition,
    FraudHunterIndicatorTask
)
from models.fraudhunter.wide_table import (
    FraudHunterWideTableVersion,
    FraudHunterWideTableSnapshot,
    FraudHunterIndicatorRunProgress
)
from utils.logger import logger

# object_type到wide_table_name的映射
OBJECT_TYPE_TO_TABLE_NAME = {
    'dep_acct_no': 'dep_acct_wide_table',
    'cust_no': 'cust_wide_table',
    'loan_acct_no': 'loan_acct_wide_table',
}

# SHA256 hash长度
HASH_FULL_LENGTH = 64
HASH_SHORT_LENGTH = 8


class WideTableVersionManager:
    """宽表版本管理器

    管理宽表版本的创建、切换和清理。
    版本状态流转: target -> current -> history
    """

    def __init__(self, db: Session) -> None:
        """初始化版本管理器

        Args:
            db: 数据库会话
        """
        self.db = db

    @staticmethod
    def get_wide_table_name(object_type: str) -> str:
        """根据object_type获取宽表名称

        Args:
            object_type: 对象类型（dep_acct_no/cust_no/loan_acct_no）

        Returns:
            宽表名称（dep_acct_wide_table/cust_wide_table/loan_acct_wide_table）

        Raises:
            ValueError: 当object_type不支持时
        """
        table_name = OBJECT_TYPE_TO_TABLE_NAME.get(object_type)
        if not table_name:
            raise ValueError(f"不支持的object_type: {object_type}")
        return table_name

    def generate_version_hash(
        self,
        online_indicators: List[FraudHunterIndicatorDefinition]
    ) -> Tuple[str, Dict[int, Dict]]:
        """生成版本号hash（SHA256取前8位）

        Args:
            online_indicators: 所有在线的离线指标列表（同一个object_type）

        Returns:
            (version_hash, indicator_metadata)
        """
        if not online_indicators:
            raise ValueError("在线指标列表不能为空")

        # 按indicator_id升序排序确保一致性
        sorted_indicators = sorted(online_indicators, key=lambda x: x.id)

        # 构建版本字符串和元数据
        parts = []
        indicator_metadata = {}

        for indicator in sorted_indicators:
            indicator_task = self.db.query(FraudHunterIndicatorTask).filter(
                FraudHunterIndicatorTask.id == indicator.indicator_task_id
            ).first()
            parts.append(f"{indicator.id}_{indicator.current_version}")
            indicator_metadata[indicator.id] = {
                "version": indicator_task.current_version,
                "indicator_code": indicator.indicator_code,
                "indicator_name": indicator.indicator_name,
                "indicator_type": indicator.indicator_type,
                "data_type": indicator.data_type,
                "object_type": indicator.object_type,
                "indicator_task_id": indicator.indicator_task_id
            }

        version_string = "#".join(parts)
        version_hash = hashlib.sha256(version_string.encode('utf-8')).hexdigest()[:HASH_SHORT_LENGTH]

        logger.info(
            f"生成版本号: {version_hash[:16]}..., "
            f"object_type={sorted_indicators[0].object_type}, "
            f"包含{len(sorted_indicators)}个指标"
        )
        logger.debug(f"版本字符串: {version_string}")

        return version_hash, indicator_metadata

    def get_online_indicators(
        self,
        object_type: str
    ) -> List[FraudHunterIndicatorDefinition]:
        """获取指定object_type的所有在线指标（离线+实时）

        Args:
            object_type: 对象类型（dep_acct_no/cust_no/loan_acct_no）

        Returns:
            在线指标列表
        """
        indicators = self.db.query(FraudHunterIndicatorDefinition).filter(
            and_(
                FraudHunterIndicatorDefinition.status == 'online',
                FraudHunterIndicatorDefinition.indicator_type.in_(['offline', 'realtime']),
                FraudHunterIndicatorDefinition.object_type == object_type
            )
        ).order_by(FraudHunterIndicatorDefinition.id).all()

        logger.info(f"查询到 {len(indicators)} 个object_type={object_type}的在线指标")
        return indicators

    def check_version_change_needed(self, object_type: str) -> bool:
        """检查指定object_type是否需要生成新版本

        对比当前在线指标集合与current版本的指标集合

        Args:
            object_type: 对象类型

        Returns:
            是否需要生成新版本
        """
        online_indicators = self.get_online_indicators(object_type)

        if not online_indicators:
            logger.info(f"object_type={object_type}没有在线指标，无需创建版本")
            return False

        wide_table_name = self.get_wide_table_name(object_type)
        current_version = self._get_version_by_status(wide_table_name, 'current')

        if not current_version:
            logger.info(f"{wide_table_name}没有current版本，需要创建")
            return True

        new_hash, _ = self.generate_version_hash(online_indicators)
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
        created_by: str
    ) -> Optional[FraudHunterWideTableVersion]:
        """为指定object_type创建新的target版本

        触发条件:
        1. 指标上线/下线
        2. 指标重新发布(版本号变更)

        Args:
            object_type: 对象类型（dep_acct_no/cust_no/loan_acct_no）
            created_by: 创建人

        Returns:
            新创建的版本对象，如果无需创建则返回None
        """
        if not self.check_version_change_needed(object_type):
            logger.info(f"object_type={object_type}无版本变更，无需创建新版本")
            return None

        online_indicators = self.get_online_indicators(object_type)
        if not online_indicators:
            logger.warning(f"object_type={object_type}没有在线指标，无法创建版本")
            return None

        version_hash, indicator_metadata = self.generate_version_hash(online_indicators)
        wide_table_name = self.get_wide_table_name(object_type)

        # 检查该版本是否已存在
        existing_version = self.db.query(FraudHunterWideTableVersion).filter(
            FraudHunterWideTableVersion.version_hash == version_hash
        ).first()

        if existing_version:
            logger.warning(f"版本 {version_hash[:16]}... 已存在，状态: {existing_version.status}")
            return existing_version

        # 将现有target版本标记为skipped
        self._skip_existing_target(wide_table_name)

        # 创建新版本
        new_version = FraudHunterWideTableVersion(
            wide_table_name=wide_table_name,
            version_hash=version_hash,
            indicator_metadata=indicator_metadata,
            status='target',
            target_at=datetime.now(),
            created_by=created_by
        )

        self.db.add(new_version)
        self.db.commit()
        self.db.refresh(new_version)

        # 自动创建PG表
        self._create_pg_table_for_version(wide_table_name, version_hash, indicator_metadata)

        logger.info(
            f"创建新版本成功: {wide_table_name}, "
            f"version_hash={version_hash[:16]}..., "
            f"包含 {len(online_indicators)} 个指标"
        )
        return new_version

    def _skip_existing_target(self, wide_table_name: str) -> None:
        """将现有target版本标记为skipped"""
        existing_target = self.db.query(FraudHunterWideTableVersion).filter(
            and_(
                FraudHunterWideTableVersion.wide_table_name == wide_table_name,
                FraudHunterWideTableVersion.status == 'target'
            )
        ).first()

        if existing_target:
            existing_target.status = 'skipped'
            existing_target.skipped_at = datetime.now()
            logger.info(f"将版本 {existing_target.version_hash[:16]}... 标记为skipped")

    def _create_pg_table_for_version(
        self,
        wide_table_name: str,
        version_hash: str,
        indicator_metadata: Dict
    ) -> None:
        from utils.analyze_db_utils import AnalyzeDBPartitionManager
        """为版本创建PG表"""
        pg_table_name = f"{wide_table_name}_{version_hash[:HASH_SHORT_LENGTH]}"
        try:
            AnalyzeDBPartitionManager.create_wide_table(
                pg_table_name, indicator_metadata
            )
            logger.info(f"创建PG表成功: {pg_table_name}")
        except Exception as e:
            logger.error(f"创建PG表失败: {pg_table_name}, error={e}")

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
        """
        indicator_metadata = target_version.indicator_metadata

        if not indicator_metadata:
            return False, []

        missing_tasks = self._check_indicators_progress(indicator_metadata, etl_date)
        is_ready = len(missing_tasks) == 0

        if is_ready:
            logger.debug(
                f"版本 {target_version.version_hash[:16]}... "
                f"在 {etl_date} 的所有指标已完成"
            )
        else:
            logger.debug(
                f"版本 {target_version.version_hash[:16]}... "
                f"在 {etl_date} 还有 {len(missing_tasks)} 个指标未完成"
            )

        return is_ready, missing_tasks

    def _check_indicators_progress(
        self,
        indicator_metadata: Dict,
        etl_date: date
    ) -> List[Dict]:
        """检查指标的运行进度（批量查询优化）"""
        missing_tasks = []

        # 先收集有 indicator_task_id 的指标，无 task_id 的直接记录缺失
        pending_items = {}  # (indicator_task_id, indicator_version) -> (indicator_id, metadata)
        for indicator_id, metadata in indicator_metadata.items():
            indicator_task_id = metadata.get('indicator_task_id')

            if not indicator_task_id:
                missing_tasks.append({
                    "indicator_id": indicator_id,
                    "indicator_code": metadata.get('indicator_code'),
                    "reason": "未关联指标任务"
                })
                continue

            pending_items[(indicator_task_id, metadata['version'])] = (indicator_id, metadata)

        # 批量查询所有需要的运行进度记录
        if pending_items:
            task_ids = [key[0] for key in pending_items.keys()]
            versions = [key[1] for key in pending_items.keys()]

            progress_records = self.db.query(
                FraudHunterIndicatorRunProgress.indicator_task_id,
                FraudHunterIndicatorRunProgress.indicator_version,
            ).filter(
                and_(
                    FraudHunterIndicatorRunProgress.indicator_task_id.in_(task_ids),
                    FraudHunterIndicatorRunProgress.etl_date == etl_date,
                    FraudHunterIndicatorRunProgress.indicator_version.in_(versions),
                )
            ).all()

            # 构建已完成的集合，用于快速查找
            completed_set = {(r.indicator_task_id, r.indicator_version) for r in progress_records}

            # 对比找出未完成的
            for (indicator_task_id, version), (indicator_id, metadata) in pending_items.items():
                if (indicator_task_id, version) not in completed_set:
                    missing_tasks.append({
                        "indicator_id": indicator_id,
                        "indicator_code": metadata.get('indicator_code'),
                        "indicator_task_id": indicator_task_id,
                        "etl_date": str(etl_date),
                        "version": version,
                        "reason": "未找到运行进度记录"
                    })

        return missing_tasks

    def promote_target_to_current(
        self,
        target_version: FraudHunterWideTableVersion,
        cleanup_history: bool = True
    ) -> FraudHunterWideTableVersion:
        """将target版本提升为current

        同时将旧的current版本标记为history，并清理历史版本

        Args:
            target_version: 目标版本对象
            cleanup_history: 是否清理历史版本（默认True）

        Returns:
            更新后的版本对象
        """
        if target_version.status != 'target':
            raise ValueError(f"只能提升status='target'的版本，当前状态: {target_version.status}")

        # 将旧的current版本标记为history
        old_current = self._get_version_by_status(target_version.wide_table_name, 'current')

        if old_current:
            old_current.status = 'history'
            old_current.history_at = datetime.now()
            logger.info(f"将版本 {old_current.version_hash[:HASH_SHORT_LENGTH]} 标记为history")

        # 提升target为current
        target_version.status = 'current'
        target_version.current_at = datetime.now()
        self.db.flush()

        # 清理历史版本
        if cleanup_history and old_current:
            deleted_count = self.cleanup_history_version(old_current)
            logger.info(f"清理历史版本完成，删除 {deleted_count} 个快照")

        self.db.commit()
        self.db.refresh(target_version)

        logger.info(f"版本 {target_version.version_hash[:HASH_SHORT_LENGTH]} 已提升为current")
        return target_version

    def check_and_promote_target(
        self,
        wide_table_name: str,
        promote_threshold: float = 0.5
    ) -> Optional[FraudHunterWideTableVersion]:
        """检查并执行target->current版本切换

        切换条件: target快照数量 >= current快照数量 * threshold
        首次创建时（无current版本），target有1个快照即可提升

        Args:
            wide_table_name: 宽表名称
            promote_threshold: 切换阈值（默认0.5，即50%）

        Returns:
            切换后的current版本，如果未切换返回None
        """
        current_version = self._get_version_by_status(wide_table_name, 'current')
        target_version = self._get_version_by_status(wide_table_name, 'target')

        if not target_version:
            logger.debug(f"{wide_table_name} 没有target版本，无需切换")
            return None

        target_count = self._count_snapshots(target_version.version_hash)
        current_count = self._count_snapshots(current_version.version_hash) if current_version else 0

        # 计算切换阈值
        threshold = current_count * promote_threshold if current_version else 1

        if target_count < threshold and target_count < 30:
            logger.info(
                f"{wide_table_name} 未满足切换条件: "
                f"target快照={target_count}, current快照={current_count}, "
                f"需要>={threshold:.0f}"
            )
            return None

        logger.info(
            f"开始版本切换: {wide_table_name}, "
            f"target({target_version.version_hash[:HASH_SHORT_LENGTH]}) -> current, "
            f"快照数量: {target_count}/{current_count}"
        )

        return self.promote_target_to_current(target_version, cleanup_history=True)

    def _count_snapshots(self, version_hash: str) -> int:
        """统计指定版本的ready快照数量"""
        if not version_hash:
            return 0
        return self.db.query(func.count(FraudHunterWideTableSnapshot.id)).filter(
            and_(
                FraudHunterWideTableSnapshot.version_hash == version_hash,
                FraudHunterWideTableSnapshot.status == 'ready'
            )
        ).scalar() or 0

    def cleanup_history_version(
        self,
        history_version: FraudHunterWideTableVersion
    ) -> int:
        """清理history版本的PG表和记录

        删除PG表并更新snapshot状态为deleted

        Args:
            history_version: 历史版本对象

        Returns:
            删除的快照数量
        """
        snapshots = self.db.query(FraudHunterWideTableSnapshot).filter(
            and_(
                FraudHunterWideTableSnapshot.version_hash == history_version.version_hash,
                FraudHunterWideTableSnapshot.status.in_(['ready', 'generating', 'failed'])
            )
        ).all()

        snapshot_count = len(snapshots)
        pg_table_name = f"{history_version.wide_table_name}_{history_version.version_hash[:HASH_SHORT_LENGTH]}"

        # 删除PG表
        try:
            from utils.analyze_db_utils import AnalyzeDBPartitionManager
            AnalyzeDBPartitionManager.drop_table(pg_table_name)
            logger.info(f"删除历史版本PG表: {pg_table_name}")
        except Exception as e:
            logger.error(f"删除PG表失败 {pg_table_name}: {e}")

        # 更新快照状态为deleted
        for snapshot in snapshots:
            snapshot.status = 'deleted'

        logger.info(
            f"清理版本 {history_version.version_hash[:HASH_SHORT_LENGTH]} 完成, "
            f"删除PG表: {pg_table_name}, 更新 {snapshot_count} 条快照记录"
        )

        return snapshot_count

    def _get_version_by_status(
        self,
        wide_table_name: str,
        status: str
    ) -> Optional[FraudHunterWideTableVersion]:
        """根据状态获取宽表版本"""
        return self.db.query(FraudHunterWideTableVersion).filter(
            and_(
                FraudHunterWideTableVersion.wide_table_name == wide_table_name,
                FraudHunterWideTableVersion.status == status
            )
        ).first()

    def get_snapshot_count(
        self,
        version_hash: str,
        status: str = 'ready'
    ) -> int:
        """获取指定版本的快照数量"""
        return self.db.query(func.count(FraudHunterWideTableSnapshot.id)).filter(
            and_(
                FraudHunterWideTableSnapshot.version_hash == version_hash,
                FraudHunterWideTableSnapshot.status == status
            )
        ).scalar() or 0
