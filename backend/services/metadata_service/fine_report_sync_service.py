"""
FineReport报表同步服务
用于从外部MySQL数据库同步FineReport报表元数据到本地数据库
"""

import pymysql
import time
from typing import Dict, List, Any, Optional, Callable
from sqlalchemy.orm import Session
from utils.logger import logger
from utils.config import settings
from repositories.fine_report_repository import FineReportRepository
from models.fine_report_models import MetadataFineReport


class FineReportSyncService:
    """FineReport报表同步服务"""

    def __init__(self, db: Session):
        self.db = db
        self.report_repo = FineReportRepository(db)

        # 同步统计
        self.stats = {
            "reports_added": 0,
            "reports_removed": 0,
            "reports_updated": 0,
            "errors": []
        }

    def is_enabled(self) -> bool:
        """检查是否启用报表同步"""
        return settings.fine_report_sync_enabled

    def sync_reports(self) -> Dict[str, Any]:
        """执行报表同步"""
        if not self.is_enabled():
            logger.info("FineReport报表同步功能已禁用，跳过同步")
            return {"success": True, "message": "FineReport报表同步功能已禁用"}

        logger.info("开始FineReport报表同步...")

        try:
            # 重置统计
            self._reset_stats()

            # 获取源数据
            source_data = self._retry_on_failure(
                lambda: self._execute_sync_sql(),
                max_retries=settings.fine_report_sync_max_retries,
                delay=settings.fine_report_sync_retry_delay
            )

            # 构建源报表字典 {report_name: report_data}
            source_reports = {}
            for row in source_data:
                report_name = self._normalize_name(row['report_name'])
                source_reports[report_name] = row

            # 获取目标数据（本地数据库中的报表）
            target_reports = self._get_target_reports()

            # 找出需要标记为removed的报表（本地有但源数据没有）
            for report_name, target_report in target_reports.items():
                if report_name not in source_reports:
                    # 如果本地报表的挂载方式不是removed，则更新为removed
                    if target_report['report_mount_type'] != 'removed':
                        self._mark_report_as_removed(target_report['id'], report_name)

            # 同步报表（新增或更新）
            for report_name, source_report in source_reports.items():
                target_report = target_reports.get(report_name)
                self._sync_report(report_name, source_report, target_report)

            # 记录同步结果
            self._log_sync_results()

            return {
                "success": len(self.stats["errors"]) == 0,
                "stats": self.stats
            }

        except Exception as e:
            error_msg = f"FineReport报表同步失败: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "stats": self.stats
            }

    def _reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            "reports_added": 0,
            "reports_removed": 0,
            "reports_updated": 0,
            "errors": []
        }

    def _retry_on_failure(self, func: Callable, max_retries: int = None, delay: float = None) -> Any:
        """失败重试机制"""
        if max_retries is None:
            max_retries = settings.fine_report_sync_max_retries
        if delay is None:
            delay = settings.fine_report_sync_retry_delay

        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"操作失败，{delay}秒后重试 (尝试 {attempt + 1}/{max_retries}): {e}")
                time.sleep(delay)

    def _get_source_connection(self) -> pymysql.Connection:
        """获取源数据库连接"""
        try:
            connection = pymysql.connect(
                host=settings.fine_report_sync_source_db_host,
                port=settings.fine_report_sync_source_db_port,
                database=settings.fine_report_sync_source_db_database,
                user=settings.fine_report_sync_source_db_user,
                password=settings.fine_report_sync_source_db_password,
                charset=settings.fine_report_sync_source_db_charset,
                connect_timeout=settings.fine_report_sync_source_db_connection_timeout
            )
            return connection
        except Exception as e:
            logger.error(f"连接FineReport源数据库失败: {e}")
            raise

    def _execute_sync_sql(self) -> List[Dict[str, Any]]:
        """执行同步SQL查询"""
        try:
            connection = self._get_source_connection()

            # 替换SQL中的变量
            sql = settings.fine_report_sync_sql.replace(
                '${database}', settings.fine_report_sync_source_db_database
            )

            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()

            connection.close()
            logger.info(f"从源数据库获取到 {len(result)} 条FineReport报表记录")
            return result

        except Exception as e:
            logger.error(f"执行FineReport同步SQL失败: {e}")
            raise

    def _normalize_name(self, name: str) -> str:
        """标准化名称（处理大小写）"""
        return name.lower() if not settings.fine_report_sync_case_sensitive else name

    def _get_target_reports(self) -> Dict[str, Dict[str, Any]]:
        """获取目标数据库中的报表"""
        target_reports = {}
        reports = self.report_repo.get_all()

        for report in reports:
            report_name = self._normalize_name(report.report_name)
            target_reports[report_name] = {
                "id": report.id,
                "report_name": report.report_name,
                "report_cpt_path": report.report_cpt_path,
                "report_type": report.report_type,
                "report_design_address": report.report_design_address,
                "report_mount_path": report.report_mount_path,
                "report_mount_type": report.report_mount_type,
                "is_available": report.is_available,
            }

        return target_reports

    def _sync_report(self, report_name: str, source_report: Dict[str, Any], target_report: Optional[Dict[str, Any]]) -> None:
        """同步单个报表"""
        try:
            # 如果报表不存在，创建新报表
            if target_report is None:
                self._create_new_report(source_report)
                return

            # 检查是否需要更新
            needs_update = False
            update_data = {}

            # 检查关键字段是否变化
            if source_report['report_cpt_path'] != target_report['report_cpt_path']:
                update_data['report_cpt_path'] = source_report['report_cpt_path']
                needs_update = True

            if source_report['report_design_address'] != target_report['report_design_address']:
                update_data['report_design_address'] = source_report['report_design_address']
                needs_update = True

            if source_report.get('report_mount_path') != target_report['report_mount_path']:
                update_data['report_mount_path'] = source_report.get('report_mount_path', '')
                needs_update = True

            # 如果源数据中存在该报表，则挂载方式应该是normal
            if target_report['report_mount_type'] != 'normal':
                update_data['report_mount_type'] = 'normal'
                needs_update = True

            if needs_update:
                self._update_report(target_report['id'], report_name, update_data)

        except Exception as e:
            error_msg = f"同步报表 {report_name} 失败: {e}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)

    def _create_new_report(self, source_report: Dict[str, Any]) -> None:
        """创建新报表"""
        try:
            report = self.report_repo.create(
                report_name=source_report['report_name'],
                report_cpt_path=source_report['report_cpt_path'],
                report_type=source_report.get('report_type', 'summary'),
                report_design_address=source_report['report_design_address'],
                report_mount_path=source_report.get('report_mount_path', ''),
                report_mount_type='normal',
                department_id=source_report.get('department_id'),
                description=source_report.get('description', ''),
                usage_scenario=source_report.get('usage_scenario', ''),
                is_available=0  # 默认可用
            )

            self.stats["reports_added"] += 1
            self._log_change("新增", "报表", source_report['report_name'], f"ID: {report.id}")

        except Exception as e:
            error_msg = f"创建新报表 {source_report['report_name']} 失败: {e}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)

    def _update_report(self, report_id: int, report_name: str, update_data: Dict[str, Any]) -> None:
        """更新报表"""
        try:
            self.report_repo.update(report_id, **update_data)
            self.stats["reports_updated"] += 1

            # 记录更新的字段
            fields = ", ".join(update_data.keys())
            self._log_change("更新", "报表", report_name, f"更新字段: {fields}, ID: {report_id}")

        except Exception as e:
            error_msg = f"更新报表 {report_name} (ID: {report_id}) 失败: {e}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)

    def _mark_report_as_removed(self, report_id: int, report_name: str) -> None:
        """标记报表为已移除"""
        try:
            self.report_repo.update(report_id, report_mount_type='removed')
            self.stats["reports_removed"] += 1
            self._log_change("标记移除", "报表", report_name, f"ID: {report_id}")

        except Exception as e:
            error_msg = f"标记报表 {report_name} (ID: {report_id}) 为已移除失败: {e}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)

    def _log_change(self, change_type: str, object_type: str, name: str, details: str = "") -> None:
        """记录变更日志"""
        log_message = f"FineReport同步: {change_type} {object_type} '{name}'"
        if details:
            log_message += f" - {details}"

        if change_type in ["新增", "更新"]:
            logger.info(log_message)
        else:  # 标记移除
            logger.warning(log_message)

    def _log_sync_results(self) -> None:
        """记录同步结果"""
        logger.info(f"FineReport报表同步完成: 报表新增 {self.stats['reports_added']}, "
                   f"报表标记移除 {self.stats['reports_removed']}, "
                   f"报表更新 {self.stats['reports_updated']}")

        if self.stats["errors"]:
            logger.error(f"同步过程中发生 {len(self.stats['errors'])} 个错误")
            for error in self.stats["errors"]:
                logger.error(error)
