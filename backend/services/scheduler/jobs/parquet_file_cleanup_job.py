"""
Parquet文件清理定时任务
清理过期的实时指标宽表文件和非当前版本的离线宽表文件
"""

from pathlib import Path
from datetime import date, datetime, timedelta
from typing import List, Set
import os

from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.db_base import get_db_session
from models.fraudhunter.wide_table import FraudHunterWideTableVersion, FraudHunterWideTableSnapshot
from utils.config import settings
from utils.logger import logger


async def parquet_file_cleanup_job():
    """清理Parquet文件
    
    包含两种清理策略：
    1. 实时指标宽表文件：按时间保留（默认21天）
    2. 离线宽表文件：只保留current和target版本的文件
    """
    try:
        # 1. 清理实时指标宽表文件（按时间保留）
        await _cleanup_realtime_wide_table_files()
        
        # 2. 清理离线宽表文件（按版本状态保留）
        await _cleanup_offline_wide_table_files()
        
        # 3. 清理孤立的快照记录
        await _cleanup_orphaned_snapshot_records()
        
        logger.info("Parquet文件清理任务完成")
        
    except Exception as e:
        logger.error(f"Parquet文件清理失败: {e}", exc_info=True)


async def _cleanup_realtime_wide_table_files():
    """清理实时指标宽表文件
    
    清理策略：保留指定天数内的文件，删除过期文件
    """
    try:
        # 获取实时宽表存储路径
        realtime_dir = Path(settings.fraudhunter_wide_table_storage_path) / "dep_acct_wide_table_realtime"
        
        if not realtime_dir.exists():
            logger.debug(f"实时宽表目录不存在: {realtime_dir}")
            return
        
        # 获取保留天数配置（使用与DuckDB数据清理相同的参数）
        retention_days = settings.fraudhunter_realtime_data_retention_days
        cutoff_date = date.today() - timedelta(days=retention_days)
        
        logger.info(f"开始清理实时宽表文件，保留 {retention_days} 天，截止日期: {cutoff_date}")
        
        deleted_count = 0
        deleted_size = 0
        
        # 遍历目录中的所有parquet文件
        for file_path in realtime_dir.glob("*.parquet"):
            try:
                # 从文件名提取日期：dep_acct_realtime_YYYYMMDD_HHMMSS.parquet
                file_name = file_path.stem
                if not file_name.startswith("dep_acct_realtime_"):
                    continue
                
                # 提取日期部分
                date_part = file_name.split("_")[3]  # YYYYMMDD
                if len(date_part) != 8:
                    continue
                
                file_date = datetime.strptime(date_part, "%Y%m%d").date()
                
                # 检查是否过期
                if file_date < cutoff_date:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_count += 1
                    deleted_size += file_size
                    logger.debug(f"删除过期实时宽表文件: {file_path.name}")
                    
            except Exception as e:
                logger.warning(f"处理实时宽表文件失败: {file_path.name}, error: {e}")
                continue
        
        if deleted_count > 0:
            logger.info(f"实时宽表文件清理完成: 删除 {deleted_count} 个文件，释放 {deleted_size / 1024 / 1024:.2f} MB")
        else:
            logger.debug("没有需要清理的实时宽表文件")
            
    except Exception as e:
        logger.error(f"清理实时宽表文件失败: {e}", exc_info=True)


async def _cleanup_offline_wide_table_files():
    """清理离线宽表文件
    
    清理策略：只保留current和target版本的文件，删除其他版本的文件
    """
    try:
        with get_db_session() as db:
            # 获取所有宽表的current和target版本
            active_versions = _get_active_versions(db)
            
            if not active_versions:
                logger.debug("没有找到活跃的宽表版本")
                return
            
            logger.info(f"找到 {len(active_versions)} 个活跃版本需要保留")
            
            # 获取宽表存储根目录
            storage_path = Path(settings.fraudhunter_wide_table_storage_path)
            
            if not storage_path.exists():
                logger.debug(f"宽表存储目录不存在: {storage_path}")
                return
            
            deleted_count = 0
            deleted_size = 0
            
            # 遍历每个宽表目录
            for wide_table_name in ['dep_acct_wide_table', 'cust_wide_table', 'loan_acct_wide_table']:
                table_dir = storage_path / wide_table_name
                
                if not table_dir.exists():
                    continue
                
                # 获取该宽表的活跃版本哈希
                table_active_hashes = active_versions.get(wide_table_name, set())
                
                logger.info(f"处理宽表目录: {wide_table_name}, 活跃版本: {len(table_active_hashes)} 个")
                
                # 遍历目录中的所有parquet文件
                for file_path in table_dir.glob("*.parquet"):
                    try:
                        # 从文件名提取版本哈希：{table_name}_{version_hash}_{date}.parquet
                        file_name = file_path.stem
                        parts = file_name.split("_")
                        
                        if len(parts) < 3:
                            continue
                        
                        # 提取版本哈希（倒数第二部分）
                        version_hash = parts[-2]
                        
                        # 检查是否为活跃版本
                        if version_hash not in table_active_hashes:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_count += 1
                            deleted_size += file_size
                            logger.debug(f"删除非活跃版本文件: {file_path.name}")
                            
                    except Exception as e:
                        logger.warning(f"处理离线宽表文件失败: {file_path.name}, error: {e}")
                        continue
            
            if deleted_count > 0:
                logger.info(f"离线宽表文件清理完成: 删除 {deleted_count} 个文件，释放 {deleted_size / 1024 / 1024:.2f} MB")
            else:
                logger.debug("没有需要清理的离线宽表文件")
                
    except Exception as e:
        logger.error(f"清理离线宽表文件失败: {e}", exc_info=True)


def _get_active_versions(db: Session) -> dict:
    """获取所有宽表的活跃版本（current和target）
    
    Args:
        db: 数据库会话
        
    Returns:
        dict: {wide_table_name: {version_hash1, version_hash2, ...}}
    """
    active_versions = {}
    
    try:
        # 查询所有current和target状态的版本
        versions = db.query(FraudHunterWideTableVersion).filter(
            FraudHunterWideTableVersion.status.in_(['current', 'target'])
        ).all()
        
        for version in versions:
            table_name = version.wide_table_name
            version_hash = version.version_hash
            
            if table_name not in active_versions:
                active_versions[table_name] = set()
            
            active_versions[table_name].add(version_hash)
            
        # 记录活跃版本信息
        for table_name, hashes in active_versions.items():
            logger.debug(f"宽表 {table_name} 的活跃版本: {[h[:8] for h in hashes]}")
            
    except Exception as e:
        logger.error(f"获取活跃版本失败: {e}", exc_info=True)
        
    return active_versions


async def _cleanup_orphaned_snapshot_records():
    """清理孤立的快照记录
    
    将对应文件已不存在的快照记录状态标记为 deleted
    """
    try:
        with get_db_session() as db:
            # 只查询ready状态的快照记录
            snapshots = db.query(FraudHunterWideTableSnapshot).filter(
                FraudHunterWideTableSnapshot.status == 'ready'
            ).all()
            
            marked_count = 0
            
            for snapshot in snapshots:
                if snapshot.parquet_file_path:
                    file_path = Path(snapshot.parquet_file_path)
                    
                    # 如果文件不存在，将状态标记为deleted
                    if not file_path.exists():
                        snapshot.status = 'deleted'
                        marked_count += 1
                        logger.debug(f"标记孤立快照记录为deleted: {snapshot.id}, 文件: {file_path.name}")
            
            if marked_count > 0:
                db.commit()
                logger.info(f"清理孤立快照记录完成: 标记 {marked_count} 条记录为deleted")
            else:
                logger.debug("没有需要标记为deleted的孤立快照记录")
                
    except Exception as e:
        logger.error(f"清理孤立快照记录失败: {e}", exc_info=True)
        db.rollback()