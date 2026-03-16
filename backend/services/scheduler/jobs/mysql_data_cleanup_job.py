from datetime import datetime, timedelta

from sqlalchemy import or_

from models.fraudhunter.dry_run_task import FraudHunterDryRunExecution
from models.fraudhunter.model_execution_tracking import FraudHunterModelAlertControlRecord, FraudHunterModelExecution, FraudHunterModelHitRecord
from models.db_base import get_db_session
from utils.logger import logger


async def mysql_data_cleanup_job():
    """MySQL数据清理任务
    """
    try:
        # 1. 清理实时交易明细表旧分区
        await _cleanup_history_model_execution()

        await _cleanup_hisrory_dry_run()

        logger.info("MySQL数据清理任务完成")

    except Exception as e:
        logger.error(f"MySQL数据清理失败: {e}", exc_info=True)


async def _cleanup_history_model_execution():
    try:
        with get_db_session() as session:
            # 计算一个月前的时间
            max_delete_num = 50000
            cleanup_timeline = datetime.now() - timedelta(days=30)

            formatted_date = cleanup_timeline.strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"准备删除模型历史运行信息，截至日期 {formatted_date}")
            
            # 查询符合条件的alert_control_record
            alert_controls = session.query(FraudHunterModelAlertControlRecord).filter(
                FraudHunterModelAlertControlRecord.created_at < cleanup_timeline,
                FraudHunterModelAlertControlRecord.alert_status == 'duplicate',
                FraudHunterModelAlertControlRecord.control_status == 'duplicate'
            ).order_by(FraudHunterModelAlertControlRecord.created_at).limit(max_delete_num).all()
            
            # 获取关联的execution_ids
            alert_controls_ids = [record.id for record in alert_controls]

            record_ids = [record.hit_record_id for record in alert_controls]
            execution_ids = [record.execution_id for record in alert_controls]

            logger.info(f'execution_ids: {len(execution_ids)}')

            
            if alert_controls_ids:
                # 删除alert_control_record
                deleted_alert_count = session.query(FraudHunterModelAlertControlRecord).filter(
                    FraudHunterModelAlertControlRecord.id.in_(alert_controls_ids)
                ).delete(synchronize_session=False)
                logger.info(f"已删除 {deleted_alert_count} 条模型告警管控记录(fraudhunter_model_alert_control_record)")

                alert_controls_not_delete = session.query(FraudHunterModelAlertControlRecord).filter(
                    FraudHunterModelAlertControlRecord.execution_id.in_(execution_ids)
                ).all()
                alert_controls_not_delete_ids = [record.execution_id for record in alert_controls_not_delete]
                need_delete_execution_ids = list(set(execution_ids) - set(alert_controls_not_delete_ids)) 
                logger.info(f'alert_controls_not_duplicate: {len(alert_controls_not_delete_ids)}')
                logger.info(f'need_delete_execution_ids: {len(need_delete_execution_ids)}')

                # 删除关联的hit_record
                deleted_hit_count = session.query(FraudHunterModelHitRecord).filter(
                    FraudHunterModelHitRecord.id.in_(record_ids)
                ).delete(synchronize_session=False)
                logger.info(f"已删除 {deleted_hit_count} 条模型预警记录(fraudhunter_model_hit_record)")

                # 删除关联的execution
                deleted_execution_count = session.query(FraudHunterModelExecution).filter(
                    FraudHunterModelExecution.id.in_(need_delete_execution_ids)
                ).delete(synchronize_session=False)
                logger.info(f"已删除 {deleted_execution_count} 条模型运行记录(fraudhunter_model_execution)")
                

        
    except Exception as e:
        logger.error(f"删除模型历史运行信息失败: {e}", exc_info=True)


async def _cleanup_hisrory_dry_run():
    """清理实时交易明细表旧分区

    清理策略：保留指定天数内的分区，删除过期分区
    """
    try:
        with get_db_session() as session:
            cleanup_timeline = datetime.now() - timedelta(days=30)
            formatted_date = cleanup_timeline.strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"准备删除模型试运行信息，截至日期 {formatted_date}")

            deleted_dry_run_count = session.query(FraudHunterDryRunExecution).filter(
                FraudHunterDryRunExecution.created_at < cleanup_timeline,
            ).delete(synchronize_session=False)

            logger.info(f"已删除 {deleted_dry_run_count} 条模型试运行数据(fraudhunter_dryrun_execution)")
    except Exception as e:
        logger.error(f"删除模型试运行信息失败: {e}", exc_info=True)


def main():
    import asyncio
    # 使用 asyncio.run 启动协程
    asyncio.run(mysql_data_cleanup_job())

if __name__ == "__main__":
    main()