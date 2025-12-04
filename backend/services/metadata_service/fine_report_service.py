"""
FineReport报表元数据管理服务
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from repositories.fine_report_repository import FineReportRepository
from utils.logger import logger


class FineReportService:
    """FineReport报表元数据管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = FineReportRepository(db)

    def get_all_reports(
        self,
        is_available: Optional[int] = None,
        report_type: Optional[str] = None,
        department_id: Optional[int] = None,
        keyword: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取所有报表（支持多条件过滤）

        Args:
            is_available: 可用状态过滤 (0=可用, 1=不可用)
            report_type: 报表类型过滤 ('summary' or 'detail')
            department_id: 部门ID过滤
            keyword: 搜索关键词

        Returns:
            报表列表
        """
        try:
            reports = self.repo.get_filter_reports(
                is_available=is_available,
                report_type=report_type,
                department_id=department_id,
                keyword=keyword
            )
            return [self._report_to_dict(report) for report in reports]
        except Exception as e:
            logger.error(f"获取报表列表失败: {e}")
            return []

    def get_report_by_id(self, report_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取报表详情

        Args:
            report_id: 报表ID

        Returns:
            报表详情字典或None
        """
        try:
            report = self.repo.get_by_id(report_id)
            if report:
                return self._report_to_dict(report)
            return None
        except Exception as e:
            logger.error(f"获取报表详情失败: {e}")
            return None

    def get_report_by_name(self, report_name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取报表

        Args:
            report_name: 报表名称

        Returns:
            报表详情字典或None
        """
        try:
            report = self.repo.get_by_name(report_name)
            if report:
                return self._report_to_dict(report)
            return None
        except Exception as e:
            logger.error(f"根据名称获取报表失败: {e}")
            return None

    def create_report(self, report_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        创建报表

        Args:
            report_data: 报表数据字典

        Returns:
            创建的报表详情字典或None
        """
        try:
            # 检查报表名称是否已存在
            if self.repo.check_name_exists(report_data.get('report_name', '')):
                logger.error(f"报表名称已存在: {report_data.get('report_name')}")
                return None

            # 创建报表
            report = self.repo.create(**report_data)
            logger.info(f"创建报表成功: {report.report_name} (ID={report.id})")
            return self._report_to_dict(report)
        except Exception as e:
            logger.error(f"创建报表失败: {e}")
            return None

    def update_report(self, report_id: int, update_data: Dict[str, Any]) -> bool:
        """
        更新报表

        Args:
            report_id: 报表ID
            update_data: 更新数据字典

        Returns:
            是否更新成功
        """
        try:
            # 如果要更新报表名称，检查是否与其他报表重名
            if 'report_name' in update_data:
                if self.repo.check_name_exists(update_data['report_name'], exclude_id=report_id):
                    logger.error(f"报表名称已存在: {update_data['report_name']}")
                    return False

            # 执行更新
            report = self.repo.update(report_id, **update_data)
            if report:
                logger.info(f"更新报表成功: ID={report_id}")
                return True
            else:
                logger.warning(f"报表不存在: ID={report_id}")
                return False
        except Exception as e:
            logger.error(f"更新报表失败: {e}")
            return False

    def delete_report(self, report_id: int) -> bool:
        """
        删除报表

        Args:
            report_id: 报表ID

        Returns:
            是否删除成功
        """
        try:
            success = self.repo.delete(report_id)
            if success:
                logger.info(f"删除报表成功: ID={report_id}")
            else:
                logger.warning(f"报表不存在: ID={report_id}")
            return success
        except Exception as e:
            logger.error(f"删除报表失败: {e}")
            return False

    def search_reports(self, keyword: str, is_available: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        搜索报表（支持名称、描述、使用场景模糊匹配）

        Args:
            keyword: 搜索关键词
            is_available: 可用状态过滤

        Returns:
            匹配的报表列表
        """
        try:
            reports = self.repo.search_reports(keyword, is_available)
            return [self._report_to_dict(report) for report in reports]
        except Exception as e:
            logger.error(f"搜索报表失败: {e}")
            return []

    def get_reports_by_department(self, department_id: int, is_available: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        根据部门获取报表列表

        Args:
            department_id: 部门ID
            is_available: 可用状态过滤

        Returns:
            报表列表
        """
        try:
            reports = self.repo.get_by_department(department_id, is_available)
            return [self._report_to_dict(report) for report in reports]
        except Exception as e:
            logger.error(f"根据部门获取报表失败: {e}")
            return []

    def get_reports_by_type(self, report_type: str, is_available: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        根据报表类型获取报表列表

        Args:
            report_type: 报表类型 ('summary' or 'detail')
            is_available: 可用状态过滤

        Returns:
            报表列表
        """
        try:
            reports = self.repo.get_by_type(report_type, is_available)
            return [self._report_to_dict(report) for report in reports]
        except Exception as e:
            logger.error(f"根据类型获取报表失败: {e}")
            return []

    def _report_to_dict(self, report) -> Dict[str, Any]:
        """
        将报表对象转换为字典

        Args:
            report: 报表ORM对象

        Returns:
            报表字典
        """
        return {
            "id": report.id,
            "report_name": report.report_name,
            "report_cpt_path": report.report_cpt_path,
            "report_type": report.report_type,
            "report_design_address": report.report_design_address,
            "department_id": report.department_id,
            "description": report.description or "",
            "usage_scenario": report.usage_scenario or "",
            "is_available": report.is_available,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "updated_at": report.updated_at.isoformat() if report.updated_at else None
        }


# 全局服务实例
_fine_report_service: Optional[FineReportService] = None


def get_fine_report_service(db: Optional[Session] = None) -> FineReportService:
    """
    获取FineReport服务实例

    Args:
        db: 数据库会话（可选）

    Returns:
        FineReportService实例
    """
    if db:
        # 如果提供了db，直接返回新实例
        return FineReportService(db)

    global _fine_report_service
    if _fine_report_service is None:
        from models.db_base import SessionLocal
        _fine_report_service = FineReportService(SessionLocal())
    return _fine_report_service
