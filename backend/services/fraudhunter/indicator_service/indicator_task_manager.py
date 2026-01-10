"""
指标任务管理服务
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.fraudhunter.indicator import (
    FraudHunterIndicatorTask,
    FraudHunterIndicatorTaskHistory
)
from schemas.fraudhunter.indicator import (
    IndicatorTaskCreate,
    IndicatorTaskUpdate
)
from services.fraudhunter.sequence_service import SequenceManager
from utils.logger import logger


class IndicatorTaskManager:
    """指标任务管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.sequence_manager = SequenceManager(db)

    def create_indicator_task(
        self,
        task_data: IndicatorTaskCreate,
        created_by: str
    ) -> FraudHunterIndicatorTask:
        """创建指标任务（自动生成编码）

        Args:
            task_data: 指标任务创建数据
            created_by: 创建人

        Returns:
            创建的指标任务对象

        Raises:
            ValueError: 如果指标任务编码已存在（当手动指定编码时）
        """
        # 如果未提供编码，自动生成
        if not task_data.task_code:
            task_data.task_code = self.sequence_manager.generate_task_code()
            logger.info(f"自动生成指标任务编码: {task_data.task_code}")
        else:
            # 如果提供了编码，仍需验证唯一性
            existing = self.db.query(FraudHunterIndicatorTask).filter(
                FraudHunterIndicatorTask.task_code == task_data.task_code
            ).first()

            if existing:
                raise ValueError(f"指标任务编码已存在: {task_data.task_code}")

        # 创建指标任务记录
        db_task = FraudHunterIndicatorTask(
            **task_data.model_dump(),
            created_by=created_by,
            status='draft',
            current_version=1,
            latest_version=1
        )

        self.db.add(db_task)
        self.db.flush()  # 获取ID但不提交

        # 创建版本历史
        self._create_version_history(db_task, 'create', '初始创建', created_by)

        self.db.commit()
        self.db.refresh(db_task)

        logger.info(f"创建指标任务成功: {db_task.task_code}, ID={db_task.id}")
        return db_task

    def get_indicator_task(self, task_id: int) -> Optional[FraudHunterIndicatorTask]:
        """获取指标任务

        Args:
            task_id: 指标任务ID

        Returns:
            指标任务对象或None
        """
        return self.db.query(FraudHunterIndicatorTask).filter(
            FraudHunterIndicatorTask.id == task_id
        ).first()

    def get_indicator_task_by_code(self, task_code: str) -> Optional[FraudHunterIndicatorTask]:
        """根据编码获取指标任务

        Args:
            task_code: 指标任务编码

        Returns:
            指标任务对象或None
        """
        return self.db.query(FraudHunterIndicatorTask).filter(
            FraudHunterIndicatorTask.task_code == task_code
        ).first()

    def list_indicator_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search_query: Optional[str] = None,
        object_type: Optional[str] = None
    ) -> tuple[List[FraudHunterIndicatorTask], int]:
        """获取指标任务列表

        Args:
            page: 页码
            page_size: 每页数量
            status: 状态筛选
            search_query: 搜索关键词（模糊匹配编码和名称）
            object_type: 对象类型筛选

        Returns:
            (指标任务列表, 总数)
        """
        query = self.db.query(FraudHunterIndicatorTask)

        # 状态筛选
        if status:
            query = query.filter(FraudHunterIndicatorTask.status == status)

        # 搜索（模糊匹配编码和名称）
        if search_query:
            from sqlalchemy import or_
            search_filter = or_(
                FraudHunterIndicatorTask.task_code.like(f"%{search_query}%"),
                FraudHunterIndicatorTask.task_name.like(f"%{search_query}%")
            )
            query = query.filter(search_filter)

        # 对象类型筛选
        if object_type:
            query = query.filter(FraudHunterIndicatorTask.object_type == object_type)

        # 总数
        total = query.count()

        # 分页 - 按修改时间倒序排列
        offset = (page - 1) * page_size
        items = query.order_by(FraudHunterIndicatorTask.updated_at.desc()).offset(offset).limit(page_size).all()

        return items, total

    def update_indicator_task(
        self,
        task_id: int,
        task_data: IndicatorTaskUpdate,
        updated_by: str
    ) -> FraudHunterIndicatorTask:
        """更新指标任务

        Args:
            task_id: 指标任务ID
            task_data: 更新数据
            updated_by: 更新人

        Returns:
            更新后的指标任务对象

        Raises:
            ValueError: 如果指标任务不存在或状态不允许更新
        """
        db_task = self.get_indicator_task(task_id)
        if not db_task:
            raise ValueError(f"指标任务不存在: {task_id}")

        # 如果更新 object_type，需要验证关联指标
        if task_data.object_type and task_data.object_type != db_task.object_type:
            # 检查是否有关联指标
            if db_task.indicators:
                # 验证所有关联指标的 object_type 是否与新值一致
                mismatched = [ind for ind in db_task.indicators
                              if ind.object_type != task_data.object_type]
                if mismatched:
                    raise ValueError(
                        f"无法更新 object_type: 任务已关联 {len(mismatched)} 个不同 object_type 的指标"
                    )

        # 更新字段
        update_data = task_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_task, key, value)

        db_task.updated_by = updated_by
        db_task.latest_version += 1

        # 创建版本历史
        self._create_version_history(db_task, 'update', '更新配置', updated_by)

        # 同步更新关联指标的 latest_version
        if db_task.indicators:
            for indicator in db_task.indicators:
                indicator.latest_version += 1
                indicator.updated_by = updated_by
            logger.info(f"同步更新 {len(db_task.indicators)} 个关联指标的 latest_version")

        self.db.commit()
        self.db.refresh(db_task)

        logger.info(f"更新指标任务成功: {db_task.task_code}, 新版本={db_task.latest_version}")
        return db_task

    def delete_indicator_task(self, task_id: int) -> None:
        """删除指标任务（物理删除）

        Args:
            task_id: 指标任务ID

        Raises:
            ValueError: 如果指标任务不存在或有关联指标
        """
        db_task = self.get_indicator_task(task_id)
        if not db_task:
            raise ValueError(f"指标任务不存在: {task_id}")

        # 检查是否有关联指标
        if db_task.indicators and len(db_task.indicators) > 0:
            raise ValueError(f"指标任务下存在{len(db_task.indicators)}个指标，无法删除")

        self.db.delete(db_task)
        self.db.commit()

        logger.info(f"删除指标任务成功: {db_task.task_code}")

    def get_version_history(
        self,
        task_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[FraudHunterIndicatorTaskHistory], int]:
        """获取指标任务版本历史

        Args:
            task_id: 指标任务ID
            page: 页码
            page_size: 每页数量

        Returns:
            (历史记录列表, 总数)
        """
        query = self.db.query(FraudHunterIndicatorTaskHistory).filter(
            FraudHunterIndicatorTaskHistory.task_id == task_id
        )

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(FraudHunterIndicatorTaskHistory.created_at.desc()).offset(offset).limit(page_size).all()

        return items, total

    def _create_version_history(
        self,
        task: FraudHunterIndicatorTask,
        change_type: str,
        change_description: str,
        created_by: str
    ) -> None:
        """创建版本历史记录

        Args:
            task: 指标任务对象
            change_type: 变更类型
            change_description: 变更说明
            created_by: 创建人
        """
        history = FraudHunterIndicatorTaskHistory(
            task_id=task.id,
            version=task.latest_version,
            task_code=task.task_code,
            task_name=task.task_name,
            description=task.description,
            logic_type=task.logic_type,
            logic_content=task.logic_content,
            realtime_logic_content=task.realtime_logic_content,
            source_tables=task.source_tables,
            object_type=task.object_type,
            change_type=change_type,
            change_description=change_description,
            created_by=created_by
        )

        self.db.add(history)
        # 不要在这里commit，由调用方统一提交
