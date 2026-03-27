"""
训练记录相关的Repository类 - 简化的增量训练记录系统
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, asc
from datetime import datetime
from utils.logger import logger

from .base_repository import BaseRepository
from models.training_models import TrainingRecord


class TrainingRecordRepository(BaseRepository):
    """训练记录Repository - 管理增量训练记录"""

    def __init__(self, db: Session):
        super().__init__(TrainingRecord, db)

    def get_by_resource(self, resource_type: str, resource_id: int) -> Optional[TrainingRecord]:
        """根据资源类型和ID获取训练记录"""
        try:
            return self.db.query(TrainingRecord).filter(
                and_(
                    TrainingRecord.resource_type == resource_type,
                    TrainingRecord.resource_id == resource_id
                )
            ).first()
        except Exception as e:
            logger.error(f"获取资源 {resource_type}:{resource_id} 的训练记录失败: {e}")
            return None

    def get_by_resource_type(self, resource_type: str) -> List[TrainingRecord]:
        """根据资源类型获取所有训练记录"""
        try:
            return self.db.query(TrainingRecord).filter(
                TrainingRecord.resource_type == resource_type
            ).all()
        except Exception as e:
            logger.error(f"获取资源类型 '{resource_type}' 的训练记录失败: {e}")
            return []

    def get_pending_training(self) -> List[TrainingRecord]:
        """获取待训练的记录"""
        try:
            return self.db.query(TrainingRecord).filter(
                TrainingRecord.training_status == "pending"
            ).all()
        except Exception as e:
            logger.error(f"获取待训练记录失败: {e}")
            return []

    def get_training_records(self) -> List[TrainingRecord]:
        """获取所有训练记录"""
        try:
            return self.db.query(TrainingRecord).all()
        except Exception as e:
            logger.error(f"获取所有训练记录失败: {e}")
            return []

    def get_failed_training(self, limit: int = 10) -> List[TrainingRecord]:
        """获取训练失败的记录"""
        try:
            return self.db.query(TrainingRecord).filter(
                TrainingRecord.training_status == "failed"
            ).order_by(desc(TrainingRecord.updated_at)).limit(limit).all()
        except Exception as e:
            logger.error(f"获取训练失败记录失败: {e}")
            return []

    def get_stale_training_records(self, hours: int = 24) -> List[TrainingRecord]:
        """获取超时的训练记录"""
        try:
            from datetime import timedelta
            cutoff_time = datetime.now() - timedelta(hours=hours)
            return self.db.query(TrainingRecord).filter(
                and_(
                    TrainingRecord.training_status == "training",
                    TrainingRecord.updated_at < cutoff_time
                )
            ).all()
        except Exception as e:
            logger.error(f"获取超时训练记录失败: {e}")
            return []

    def create_or_update_record(self, resource_type: str, resource_id: int,
                              last_modified: datetime = None, vector_id: str = None) -> TrainingRecord:
        """创建或更新训练记录"""
        try:
            # 查找现有记录
            record = self.get_by_resource(resource_type, resource_id)

            if record:
                # 更新现有记录
                if last_modified:
                    record.update_modified_time(last_modified)
                if vector_id:
                    record.vector_id = vector_id
                self.db.commit()
                return record
            else:
                # 创建新记录
                return self.create(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    last_modified_at=last_modified or datetime.now(),
                    vector_id=vector_id or ""
                )
        except Exception as e:
            logger.error(f"创建或更新训练记录失败 {resource_type}:{resource_id}: {e}")
            self.db.rollback()
            raise

    def mark_for_training(self, resource_type: str, resource_id: int) -> bool:
        """标记资源需要重新训练"""
        try:
            record = self.get_by_resource(resource_type, resource_id)
            if record:
                record.mark_as_training()
                self.db.commit()
                return True
            else:
                # 创建新的训练记录
                self.create(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    training_status="training"
                )
                self.db.commit()
                return True
        except Exception as e:
            logger.error(f"标记资源需要训练失败 {resource_type}:{resource_id}: {e}")
            self.db.rollback()
            return False

    def complete_training(self, resource_type: str, resource_id: int, vector_id: str = None) -> bool:
        """完成训练并更新记录"""
        try:
            record = self.get_by_resource(resource_type, resource_id)
            if record:
                record.update_training_time(vector_id)
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"完成训练记录失败 {resource_type}:{resource_id}: {e}")
            self.db.rollback()
            return False

    def fail_training(self, resource_type: str, resource_id: int) -> bool:
        """标记训练失败"""
        try:
            record = self.get_by_resource(resource_type, resource_id)
            if record:
                record.mark_as_failed()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"标记训练失败 {resource_type}:{resource_id}: {e}")
            self.db.rollback()
            return False

    def delete_record(self, resource_type: str, resource_id: int) -> bool:
        """删除训练记录"""
        try:
            record = self.get_by_resource(resource_type, resource_id)
            if record:
                self.delete(record.id)
                return True
            return False
        except Exception as e:
            logger.error(f"删除训练记录失败 {resource_type}:{resource_id}: {e}")
            return False

    def get_resources_needing_training(self, resource_type: str = None) -> List[Dict[str, Any]]:
        """获取需要训练的资源列表"""
        try:
            query = self.db.query(TrainingRecord).filter(
                TrainingRecord.training_status.in_(["pending", "failed"])
            )

            if resource_type:
                query = query.filter(TrainingRecord.resource_type == resource_type)

            records = query.all()

            return [
                {
                    "resource_type": record.resource_type,
                    "resource_id": record.resource_id,
                    "last_trained_at": record.last_trained_at,
                    "last_modified_at": record.last_modified_at,
                    "training_status": record.training_status,
                    "vector_id": record.vector_id
                }
                for record in records
            ]
        except Exception as e:
            logger.error(f"获取需要训练的资源列表失败: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """获取训练统计信息"""
        try:
            total = self.db.query(TrainingRecord).count()
            pending = self.db.query(TrainingRecord).filter(
                TrainingRecord.training_status == "pending"
            ).count()
            training = self.db.query(TrainingRecord).filter(
                TrainingRecord.training_status == "training"
            ).count()
            completed = self.db.query(TrainingRecord).filter(
                TrainingRecord.training_status == "completed"
            ).count()
            failed = self.db.query(TrainingRecord).filter(
                TrainingRecord.training_status == "failed"
            ).count()

            # 按资源类型统计
            resource_types = self.db.query(TrainingRecord.resource_type).distinct().all()
            type_stats = {}
            for rt in resource_types:
                rt_count = self.db.query(TrainingRecord).filter(
                    TrainingRecord.resource_type == rt[0]
                ).count()
                type_stats[rt[0]] = rt_count

            return {
                "total": total,
                "pending": pending,
                "training": training,
                "completed": completed,
                "failed": failed,
                "by_resource_type": type_stats
            }
        except Exception as e:
            logger.error(f"获取训练统计失败: {e}")
            return {}

    def needs_training(self, resource_type: str, resource_id: int, last_modified_time: datetime) -> bool:
        """判断资源是否需要重新训练

        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            last_modified_time: 资源的最后修改时间

        Returns:
            bool: 如果需要训练返回True
        """
        try:
            record = self.get_by_resource(resource_type, resource_id)
            if not record:
                return True  # 新资源需要训练
            return record.last_modified_at < last_modified_time
        except Exception as e:
            logger.error(f"判断资源是否需要训练失败 {resource_type}:{resource_id}: {e}")
            return True  # 出错时默认需要训练

    def update_training_time(self, resource_type: str, resource_id: int, vector_ids: list = None) -> bool:
        """更新训练时间和状态

        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            vector_ids: 向量数据库中的ID列表

        Returns:
            bool: 是否更新成功
        """
        import json as json_mod
        try:
            record = self.get_by_resource(resource_type, resource_id)
            if record:
                record.last_trained_at = datetime.now()
                record.training_status = "completed"
                if vector_ids is not None:
                    record.vector_ids = json_mod.dumps(vector_ids)
                record.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"更新训练时间失败 {resource_type}:{resource_id}: {e}")
            self.db.rollback()
            return False

    def get_vector_ids(self, resource_type: str, resource_id: int) -> List[str]:
        """获取资源的向量ID列表

        Args:
            resource_type: 资源类型
            resource_id: 资源ID

        Returns:
            List[str]: 向量ID列表
        """
        try:
            record = self.get_by_resource(resource_type, resource_id)
            if not record:
                return []

            return record.get_vector_ids()
        except Exception as e:
            logger.error(f"获取向量IDs失败 {resource_type}:{resource_id}: {e}")
            return []

    def set_vector_ids(self, resource_type: str, resource_id: int, vector_ids: List[str]) -> bool:
        """设置资源的向量ID列表

        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            vector_ids: 向量ID列表

        Returns:
            bool: 是否设置成功
        """
        import json as json_mod
        try:
            record = self.get_by_resource(resource_type, resource_id)
            if record:
                record.vector_ids = json_mod.dumps(vector_ids)
                record.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"设置向量IDs失败 {resource_type}:{resource_id}: {e}")
            self.db.rollback()
            return False

    def mark_as_training(self, resource_type: str, resource_id: int) -> bool:
        """标记资源为正在训练

        Args:
            resource_type: 资源类型
            resource_id: 资源ID

        Returns:
            bool: 是否标记成功
        """
        try:
            record = self.get_by_resource(resource_type, resource_id)
            if record:
                record.training_status = "training"
                record.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"标记为训练中失败 {resource_type}:{resource_id}: {e}")
            self.db.rollback()
            return False

    def mark_as_failed(self, resource_type: str, resource_id: int) -> bool:
        """标记资源训练失败

        Args:
            resource_type: 资源类型
            resource_id: 资源ID

        Returns:
            bool: 是否标记成功
        """
        try:
            record = self.get_by_resource(resource_type, resource_id)
            if record:
                record.training_status = "failed"
                record.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"标记为失败失败 {resource_type}:{resource_id}: {e}")
            self.db.rollback()
            return False

    def update_modified_time(self, resource_type: str, resource_id: int, modified_time: datetime) -> bool:
        """更新资源修改时间

        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            modified_time: 资源的最新修改时间

        Returns:
            bool: 是否更新成功
        """
        try:
            record = self.get_by_resource(resource_type, resource_id)
            if record:
                record.last_modified_at = modified_time
                record.updated_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"更新修改时间失败 {resource_type}:{resource_id}: {e}")
            self.db.rollback()
            return False

    def cleanup_orphaned_records(self, valid_resource_ids: Dict[str, List[int]]) -> int:
        """清理无效资源的训练记录

        Args:
            valid_resource_ids: 字典，key为资源类型，value为有效的资源ID列表

        Returns:
            int: 删除的记录数量
        """
        try:
            deleted_count = 0

            for resource_type, valid_ids in valid_resource_ids.items():
                # 删除不在有效ID列表中的记录
                orphaned = self.db.query(TrainingRecord).filter(
                    and_(
                        TrainingRecord.resource_type == resource_type,
                        ~TrainingRecord.resource_id.in_(valid_ids)
                    )
                ).all()

                for record in orphaned:
                    self.delete(record.id)
                    deleted_count += 1

            self.db.commit()
            logger.info(f"清理了 {deleted_count} 条无效的训练记录")
            return deleted_count

        except Exception as e:
            logger.error(f"清理无效训练记录失败: {e}")
            self.db.rollback()
            return 0