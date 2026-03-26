"""
元数据同步服务
用于从外部MySQL数据库同步元数据到本地元数据库
"""

import pymysql
import time
from typing import Dict, List, Any, Optional, Callable
from sqlalchemy.orm import Session
from utils.logger import logger
from utils.config import settings
from repositories.metadata_repository import MetadataTableRepository, MetadataColumnRepository
from models.metadata_models import MetadataTable, MetadataColumn


class MetadataSyncService:
    """元数据同步服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.table_repo = MetadataTableRepository(db)
        self.column_repo = MetadataColumnRepository(db)
        
        # 同步统计
        self.stats = {
            "tables_added": 0,
            "tables_removed": 0,
            "columns_added": 0,
            "columns_removed": 0,
            "columns_updated": 0,
            "errors": []
        }
    
    def is_enabled(self) -> bool:
        """检查是否启用元数据同步"""
        return settings.metadata_sync_enabled
    
    def sync_metadata(self) -> Dict[str, Any]:
        """执行元数据同步"""
        if not self.is_enabled():
            logger.info("元数据同步功能已禁用，跳过同步")
            return {"success": True, "message": "元数据同步功能已禁用"}
        
        logger.info("开始元数据同步...")
        
        try:
            # 重置统计
            self._reset_stats()
            
            # 获取源数据
            source_data = self._retry_on_failure(
                lambda: self._execute_sync_sql(),
                max_retries=settings.metadata_sync_max_retries,
                delay=settings.metadata_sync_retry_delay
            )
            source_grouped = self._group_source_data(source_data)
            
            # 获取目标数据
            target_data = self._get_target_data()
            
            # 找出需要删除的表
            tables_to_remove = []
            for table_name in target_data:
                if table_name not in source_grouped:
                    tables_to_remove.append(table_name)
            
            # 删除不存在的表
            for table_name in tables_to_remove:
                self._delete_table(target_data[table_name]["id"], table_name)
                del target_data[table_name]
            
            # 同步表
            for table_name, source_table in source_grouped.items():
                target_table = target_data.get(table_name)
                self._sync_table(table_name, source_table, target_table)
            
            # 记录同步结果
            self._log_sync_results()
            
            return {
                "success": len(self.stats["errors"]) == 0,
                "stats": self.stats
            }
            
        except Exception as e:
            error_msg = f"元数据同步失败: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "stats": self.stats
            }
    
    def _reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            "tables_added": 0,
            "tables_removed": 0,
            "columns_added": 0,
            "columns_removed": 0,
            "columns_updated": 0,
            "errors": []
        }
    
    def _retry_on_failure(self, func: Callable, max_retries: int = None, delay: float = None) -> Any:
        """失败重试机制"""
        if max_retries is None:
            max_retries = settings.metadata_sync_max_retries
        if delay is None:
            delay = settings.metadata_sync_retry_delay
            
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
                host=settings.metadata_sync_source_db_host,
                port=settings.metadata_sync_source_db_port,
                database=settings.metadata_sync_source_db_database,
                user=settings.metadata_sync_source_db_user,
                password=settings.metadata_sync_source_db_password,
                charset=settings.metadata_sync_source_db_charset,
                connect_timeout=settings.metadata_sync_source_db_connection_timeout
            )
            return connection
        except Exception as e:
            logger.error(f"连接源数据库失败: {e}")
            raise
    
    def _execute_sync_sql(self) -> List[Dict[str, Any]]:
        """执行同步SQL查询"""
        try:
            connection = self._get_source_connection()
            
            # 替换SQL中的变量
            sql = settings.metadata_sync_sql.replace(
                '${database}', settings.metadata_sync_source_db_database
            )
            
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()
            
            connection.close()
            logger.info(f"从源数据库获取到 {len(result)} 条元数据记录")
            return result
            
        except Exception as e:
            logger.error(f"执行同步SQL失败: {e}")
            raise
    
    def _normalize_name(self, name: str) -> str:
        """标准化名称（处理大小写）"""
        return name.lower() if not settings.metadata_sync_case_sensitive else name
    
    def _group_source_data(self, source_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """将源数据按表名分组"""
        grouped_data = {}
        for row in source_data:
            table_name = self._normalize_name(row['table_name'])
            if table_name not in grouped_data:
                grouped_data[table_name] = []
            grouped_data[table_name].append(row)
        return grouped_data
    
    def _get_target_data(self) -> Dict[str, Dict[str, Any]]:
        """获取目标数据库中的元数据"""
        target_data = {}
        tables = self.table_repo.get_all_with_columns()
        
        for table in tables:
            table_name = self._normalize_name(table.name)
            target_data[table_name] = {
                "id": table.id,
                "name": table.name,
                "comment": table.comment,
                "is_available": table.is_available,
                "columns": {}
            }
            
            for column in table.columns:
                column_name = self._normalize_name(column.name)
                target_data[table_name]["columns"][column_name] = {
                    "id": column.id,
                    "name": column.name,
                    "type": column.type,
                    "comment": column.comment,
                    "is_available": column.is_available,
                    "business_type": column.business_type
                }
        
        return target_data
    
    def _sync_table(self, table_name: str, source_table: List[Dict[str, Any]], target_table: Optional[Dict[str, Any]]) -> None:
        """同步单个表"""
        try:
            # 如果表不存在，创建新表
            if target_table is None:
                self._create_new_table(table_name, source_table)
                return
            
            # 同步列
            source_columns = {}
            for col in source_table:
                col_name = self._normalize_name(col['column_name'])
                source_columns[col_name] = col
            
            target_columns = target_table.get("columns", {})
            
            # 找出需要删除的列
            columns_to_remove = []
            for col_name in target_columns:
                if col_name not in source_columns:
                    columns_to_remove.append(col_name)
            
            # 删除不存在的列
            for col_name in columns_to_remove:
                self._delete_column(
                    target_table["id"], 
                    target_columns[col_name]["id"], 
                    col_name
                )
            
            # 找出需要新增和更新的列
            for col_name, source_col in source_columns.items():
                if col_name not in target_columns:
                    self._create_new_column(target_table["id"], source_col)
                else:
                    target_col = target_columns[col_name]
                    # 检查字段类型是否变化
                    if source_col['column_type'] != target_col['type']:
                        self._update_column_type(
                            target_col["id"], 
                            col_name, 
                            source_col['column_type']
                        )
            
        except Exception as e:
            error_msg = f"同步表 {table_name} 失败: {e}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
    
    def _create_new_table(self, table_name: str, source_table: List[Dict[str, Any]]) -> None:
        """创建新表"""
        try:
            # 获取表注释（使用第一条记录的表注释）
            table_comment = source_table[0].get('table_comment', '')
            
            # 创建表
            table = self.table_repo.create(
                name=table_name,
                comment=table_comment,
                is_available=1  # 设置为不可用
            )
            
            self.stats["tables_added"] += 1
            self._log_change("新增", "表", table_name, f"ID: {table.id}")
            
            # 创建列
            for source_col in source_table:
                self._create_new_column(table.id, source_col)
                
        except Exception as e:
            error_msg = f"创建新表 {table_name} 失败: {e}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
    
    def _create_new_column(self, table_id: int, source_col: Dict[str, Any]) -> None:
        """创建新列"""
        try:
            column = self.column_repo.create(
                table_id=table_id,
                name=source_col['column_name'],
                type=source_col['column_type'],
                comment=source_col.get('column_comment', ''),
                is_available=1,  # 设置为不可用
                business_type=source_col['column_type']  # 业务类型等于字段类型
            )
            
            self.stats["columns_added"] += 1
            self._log_change("新增", "列", source_col['column_name'], 
                           f"类型: {source_col['column_type']}, ID: {column.id}")
            
        except Exception as e:
            error_msg = f"创建新列 {source_col['column_name']} 失败: {e}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
    
    def _delete_column(self, table_id: int, column_id: int, column_name: str) -> None:
        """删除列"""
        try:
            self.column_repo.delete(column_id)
            self.stats["columns_removed"] += 1
            self._log_change("删除", "列", column_name, f"ID: {column_id}")
            
        except Exception as e:
            error_msg = f"删除列 {column_name} (ID: {column_id}) 失败: {e}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
    
    def _delete_table(self, table_id: int, table_name: str) -> None:
        """删除表"""
        try:
            self.table_repo.delete(table_id)
            self.stats["tables_removed"] += 1
            self._log_change("删除", "表", table_name, f"ID: {table_id}")
            
        except Exception as e:
            error_msg = f"删除表 {table_name} (ID: {table_id}) 失败: {e}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
    
    def _update_column_type(self, column_id: int, column_name: str, new_type: str) -> None:
        """更新列类型"""
        try:
            self.column_repo.update(column_id, type=new_type)
            self.stats["columns_updated"] += 1
            self._log_change("更新", "列类型", column_name, f"新类型: {new_type}, ID: {column_id}")
            
        except Exception as e:
            error_msg = f"更新列类型 {column_name} (ID: {column_id}) 失败: {e}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
    
    def _log_change(self, change_type: str, object_type: str, name: str, details: str = "") -> None:
        """记录变更日志"""
        log_message = f"元数据同步: {change_type} {object_type} '{name}'"
        if details:
            log_message += f" - {details}"
        
        if change_type in ["新增"]:
            logger.info(log_message)
        elif change_type in ["更新"]:
            logger.info(log_message)
        else:  # 删除
            logger.warning(log_message)
    
    def _log_sync_results(self) -> None:
        """记录同步结果"""
        logger.info(f"元数据同步完成: 表新增 {self.stats['tables_added']}, 表删除 {self.stats['tables_removed']}, "
                   f"列新增 {self.stats['columns_added']}, 列删除 {self.stats['columns_removed']}, "
                   f"列更新 {self.stats['columns_updated']}")
        
        if self.stats["errors"]:
            logger.error(f"同步过程中发生 {len(self.stats['errors'])} 个错误")
            for error in self.stats["errors"]:
                logger.error(error)