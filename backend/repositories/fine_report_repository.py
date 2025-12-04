"""
FineReport报表元数据Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from models.fine_report_models import MetadataFineReport
from repositories.base_repository import BaseRepository
from utils.logger import logger


class FineReportRepository(BaseRepository[MetadataFineReport]):
    """FineReport报表元数据仓储"""

    def __init__(self, db: Session):
        super().__init__(MetadataFineReport, db)

    def get_by_name(self, report_name: str) -> Optional[MetadataFineReport]:
        """根据报表名称获取报表"""
        try:
            return self.db.query(MetadataFineReport).filter(
                MetadataFineReport.report_name == report_name
            ).first()
        except Exception as e:
            logger.error(f"根据名称获取报表失败: {e}")
            raise

    def get_by_type(self, report_type: str, is_available: Optional[int] = None) -> List[MetadataFineReport]:
        """根据报表类型获取报表列表"""
        try:
            query = self.db.query(MetadataFineReport).filter(
                MetadataFineReport.report_type == report_type
            )
            if is_available is not None:
                query = query.filter(MetadataFineReport.is_available == is_available)
            return query.all()
        except Exception as e:
            logger.error(f"根据类型获取报表失败: {e}")
            raise

    def get_by_department(self, department_id: int, is_available: Optional[int] = None) -> List[MetadataFineReport]:
        """根据部门ID获取报表列表"""
        try:
            query = self.db.query(MetadataFineReport).filter(
                MetadataFineReport.department_id == department_id
            )
            if is_available is not None:
                query = query.filter(MetadataFineReport.is_available == is_available)
            return query.all()
        except Exception as e:
            logger.error(f"根据部门获取报表失败: {e}")
            raise

    def search_reports(self, keyword: str, is_available: Optional[int] = None) -> List[MetadataFineReport]:
        """
        搜索报表（支持名称、描述、使用场景模糊匹配）

        Args:
            keyword: 搜索关键词
            is_available: 可用状态过滤

        Returns:
            匹配的报表列表
        """
        try:
            query = self.db.query(MetadataFineReport).filter(
                or_(
                    MetadataFineReport.report_name.like(f"%{keyword}%"),
                    MetadataFineReport.description.like(f"%{keyword}%"),
                    MetadataFineReport.usage_scenario.like(f"%{keyword}%")
                )
            )
            if is_available is not None:
                query = query.filter(MetadataFineReport.is_available == is_available)
            return query.all()
        except Exception as e:
            logger.error(f"搜索报表失败: {e}")
            raise

    def get_filter_reports(
        self,
        is_available: Optional[int] = None,
        report_type: Optional[str] = None,
        department_id: Optional[int] = None,
        keyword: Optional[str] = None
    ) -> List[MetadataFineReport]:
        """
        多条件过滤获取报表列表

        Args:
            is_available: 可用状态过滤
            report_type: 报表类型过滤
            department_id: 部门ID过滤
            keyword: 搜索关键词

        Returns:
            过滤后的报表列表
        """
        try:
            query = self.db.query(MetadataFineReport)

            if is_available is not None:
                query = query.filter(MetadataFineReport.is_available == is_available)

            if report_type:
                query = query.filter(MetadataFineReport.report_type == report_type)

            if department_id is not None:
                query = query.filter(MetadataFineReport.department_id == department_id)

            if keyword:
                query = query.filter(
                    or_(
                        MetadataFineReport.report_name.like(f"%{keyword}%"),
                        MetadataFineReport.description.like(f"%{keyword}%"),
                        MetadataFineReport.usage_scenario.like(f"%{keyword}%")
                    )
                )

            return query.order_by(MetadataFineReport.updated_at.desc()).all()
        except Exception as e:
            logger.error(f"多条件过滤获取报表失败: {e}")
            raise

    def check_name_exists(self, report_name: str, exclude_id: Optional[int] = None) -> bool:
        """
        检查报表名称是否已存在

        Args:
            report_name: 报表名称
            exclude_id: 排除的报表ID（用于更新时检查）

        Returns:
            是否存在
        """
        try:
            query = self.db.query(MetadataFineReport).filter(
                MetadataFineReport.report_name == report_name
            )
            if exclude_id:
                query = query.filter(MetadataFineReport.id != exclude_id)
            return query.first() is not None
        except Exception as e:
            logger.error(f"检查报表名称是否存在失败: {e}")
            raise
