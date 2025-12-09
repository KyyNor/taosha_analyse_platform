"""
Spark工具类 - 支持JDBC和PySpark两种模式

JDBC模式：通过HiveServer2 JDBC连接执行查询
PySpark模式：直接提交Spark任务执行查询并输出文件
"""

import os
import os.path
import pathlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Literal, Tuple

from retry import retry
import jaydebeapi

from .logger import logger


class SparkUtils:
    """Spark工具类 - 支持JDBC查询"""
    
    _instance = None
    conn = None
    cur = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SparkUtils, cls).__new__(cls)
        return cls._instance

    def _get_spark_connect(self):
        from utils.config import settings
        
        _jdbc_driver_jar = settings.query_engine_jdbc_driver_jar_list
        _jdbc_driver_class = settings.query_engine_spark_jdbc_driver_class
        _jdbc_url = settings.query_engine_spark_jdbc_url
        _user = settings.query_engine_spark_user_name
        _password = settings.query_engine_spark_password

        logger.info(f"准备 {_jdbc_driver_class} 连接，jdbc_url:{_jdbc_url}，jdbc_driver_jar:{_jdbc_driver_jar}")

        driver_args = {
            'user': _user,
            'password': _password
        }

        self.conn = jaydebeapi.connect(
            jclassname=_jdbc_driver_class,
            url=_jdbc_url,
            driver_args=driver_args,
            jars=_jdbc_driver_jar
        )

        self.cur = self.conn.cursor()
        logger.info(f"{_jdbc_driver_class} 数据连接已获取")
        
    def convert_java_types(self, result):
        """将 Java 类型转换为 Python 类型"""
        converted_results = []
        
        for row in result:
            converted_row = []
            for item in row:
                if hasattr(item, '__class__') and 'Double' in str(type(item)):
                    # 转换 JDouble 为 float
                    converted_row.append(float(item))
                elif hasattr(item, '__class__') and 'Long' in str(type(item)):
                    # 转换 JLong 为 int
                    converted_row.append(int(item))
                elif hasattr(item, '__class__') and 'Int' in str(type(item)):
                    # 转换 JInt 为 int
                    converted_row.append(int(item))
                else:
                    converted_row.append(item)
            converted_results.append(converted_row)
    
        return converted_results
    
    
    def query_sql(self, sql: str, params: Optional[tuple] = None,
                  return_type: Literal['dict', 'list'] = 'dict') -> List[Union[Dict[str, Any], List[Any]]]:
        """
        执行查询SQL语句（JDBC模式）

        Args:
            sql: SQL查询语句
            params: SQL参数
            return_type: 返回类型，'dict'表示返回字典列表，'list'表示返回列表列表

        Returns:
            查询结果列表
        """

        if self.conn is None:
            self._get_spark_connect()
        else:
            logger.info(f"复用已有数据连接")

        if not self.conn:
            return []

        logger.info(f"执行Spark查询SQL: {sql}")

        if params:
            logger.debug(f"SQL参数: {params}")

        # self.cur.execute(sql, params)
        self.query_sql_with_retry(sql, params)
        columns = [col[0] for col in self.cur.description]
        rows = self.cur.fetchall()
        rows = self.convert_java_types(rows)

        if return_type == 'dict':
            results = [dict(zip(columns, row)) for row in rows]
        else:
            results = rows

        logger.info(f"查询成功，返回 {len(results)} 条记录")
        return results

    @retry(tries=5, delay=5)
    def query_sql_with_retry(self, sql: str, params: Optional[tuple] = None,):
        self.cur.execute(sql, params)

    def close_spark_connect(self):
        logger.info("关闭Spark JDBC连接")
        if self.cur:
            self.cur.close()
            self.cur = None
        if self.conn:
            self.conn.close()
            self.conn = None


class PySparkService:
    """
    PySpark服务 - 使用SparkSession直接提交任务
    
    特点：
    - 单例模式，全局唯一SparkSession
    - 支持直接执行SQL并保存为Parquet
    - 可配置executor内存和核心数
    """
    
    _instance: Optional['PySparkService'] = None
    _spark = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化时不创建SparkSession，延迟到首次使用或显式初始化"""
        pass
    
    def initialize(self, force: bool = False) -> bool:
        """
        初始化SparkSession
        
        Args:
            force: 是否强制重新初始化
            
        Returns:
            是否初始化成功
        """
        if self._initialized and not force:
            logger.debug("PySpark服务已初始化，跳过")
            return True
        
        try:
            from pyspark.sql import SparkSession
            from utils.config import settings
            
            # 如果强制重新初始化，先停止现有的SparkSession
            if force and self._spark is not None:
                self.shutdown()
            
            # 获取配置
            app_name = getattr(settings, 'pyspark_app_name', 'TaoShaAnalyticsPlatform')
            master = getattr(settings, 'pyspark_master', 'local[*]')
            executor_memory = getattr(settings, 'pyspark_executor_memory', '4g')
            executor_cores = getattr(settings, 'pyspark_executor_cores', 2)
            driver_memory = getattr(settings, 'pyspark_driver_memory', '2g')
            extra_configs = getattr(settings, 'pyspark_extra_configs', {})
            
            logger.info(f"正在初始化PySpark: master={master}, "
                       f"executor_memory={executor_memory}, executor_cores={executor_cores}")
            
            # 构建SparkSession
            builder = SparkSession.builder \
                .appName(app_name) \
                .master(master) \
                .config("spark.executor.memory", executor_memory) \
                .config("spark.executor.cores", str(executor_cores)) \
                .config("spark.driver.memory", driver_memory) \
                .config("spark.sql.adaptive.enabled", "true") \
                .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
                .enableHiveSupport()
            
            # 应用额外的配置
            for key, value in extra_configs.items():
                builder = builder.config(key, value)
                logger.debug(f"应用额外配置: {key}={value}")
            
            # 创建SparkSession
            self._spark = builder.getOrCreate()
            self._initialized = True
            
            logger.info(f"PySpark初始化成功: {self._spark.sparkContext.applicationId}")
            return True
            
        except ImportError as e:
            logger.error(f"PySpark未安装: {e}")
            logger.error("请安装pyspark: pip install pyspark")
            return False
        except Exception as e:
            logger.error(f"PySpark初始化失败: {e}", exc_info=True)
            return False
    
    @property
    def spark(self):
        """获取SparkSession，如果未初始化则自动初始化"""
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("PySpark服务未初始化且初始化失败")
        return self._spark
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized and self._spark is not None
    
    def execute_sql_to_parquet(
        self,
        sql: str,
        output_path: Union[str, Path],
        mode: str = 'overwrite',
        partition_by: Optional[List[str]] = None
    ) -> Tuple[int, int, int]:
        """
        执行SQL并将结果保存为Parquet文件
        
        Args:
            sql: Spark SQL查询语句
            output_path: 输出文件路径
            mode: 写入模式 ('overwrite', 'append', 'error', 'ignore')
            partition_by: 分区字段列表
            
        Returns:
            (row_count, column_count, file_size_bytes) 元组
        """
        output_path = Path(output_path)
        
        logger.info(f"PySpark执行SQL并保存到: {output_path}")
        logger.debug(f"SQL: {sql[:500]}...")  # 只打印前500字符
        
        try:
            # 执行SQL查询
            df = self.spark.sql(sql)
            
            # 获取列数
            column_count = len(df.columns)
            
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存为Parquet（合并为单文件）
            # 使用coalesce(1)确保输出单个文件
            writer = df.coalesce(1).write.mode(mode)
            
            if partition_by:
                writer = writer.partitionBy(*partition_by)
            
            # 保存到临时目录
            temp_output = output_path.parent / f".temp_{output_path.stem}"
            writer.parquet(str(temp_output))
            
            # 找到生成的parquet文件并移动到目标位置
            parquet_files = list(temp_output.glob("*.parquet"))
            if parquet_files:
                # 移动第一个parquet文件到目标位置
                import shutil
                if output_path.exists():
                    output_path.unlink()
                shutil.move(str(parquet_files[0]), str(output_path))
                
                # 清理临时目录
                shutil.rmtree(str(temp_output), ignore_errors=True)
            else:
                raise RuntimeError(f"未找到生成的Parquet文件: {temp_output}")
            
            # 获取行数（需要重新读取或在保存前计算）
            row_count = df.count()
            
            # 获取文件大小
            file_size = output_path.stat().st_size if output_path.exists() else 0
            
            logger.info(f"PySpark保存成功: {output_path.name}, "
                       f"{row_count}行, {column_count}列, {file_size}字节")
            
            return (row_count, column_count, file_size)
            
        except Exception as e:
            logger.error(f"PySpark执行SQL失败: {e}", exc_info=True)
            # 清理可能的临时文件
            temp_output = output_path.parent / f".temp_{output_path.stem}"
            if temp_output.exists():
                import shutil
                shutil.rmtree(str(temp_output), ignore_errors=True)
            raise
    
    def execute_sql(
        self,
        sql: str,
        return_type: Literal['dict', 'list', 'dataframe'] = 'dict'
    ) -> Union[List[Dict[str, Any]], List[List[Any]], Any]:
        """
        执行SQL查询并返回结果
        
        Args:
            sql: Spark SQL查询语句
            return_type: 返回类型
                - 'dict': 返回字典列表
                - 'list': 返回列表列表
                - 'dataframe': 返回Spark DataFrame
            
        Returns:
            查询结果
        """
        logger.info(f"PySpark执行SQL查询")
        logger.debug(f"SQL: {sql[:500]}...")
        
        try:
            df = self.spark.sql(sql)
            
            if return_type == 'dataframe':
                return df
            
            # 收集结果到driver
            rows = df.collect()
            columns = df.columns
            
            if return_type == 'dict':
                results = [row.asDict() for row in rows]
            else:
                results = [list(row) for row in rows]
            
            logger.info(f"PySpark查询成功，返回 {len(results)} 条记录")
            return results
            
        except Exception as e:
            logger.error(f"PySpark查询失败: {e}", exc_info=True)
            raise
    
    def shutdown(self):
        """关闭SparkSession"""
        if self._spark is not None:
            try:
                logger.info("正在关闭PySpark SparkSession...")
                self._spark.stop()
                self._spark = None
                self._initialized = False
                logger.info("PySpark SparkSession已关闭")
            except Exception as e:
                logger.error(f"关闭PySpark失败: {e}", exc_info=True)
    
    def get_status(self) -> Dict[str, Any]:
        """获取PySpark状态信息"""
        if not self._initialized or self._spark is None:
            return {
                "initialized": False,
                "application_id": None,
                "master": None
            }
        
        try:
            sc = self._spark.sparkContext
            return {
                "initialized": True,
                "application_id": sc.applicationId,
                "master": sc.master,
                "app_name": sc.appName,
                "version": sc.version,
                "default_parallelism": sc.defaultParallelism
            }
        except Exception as e:
            return {
                "initialized": self._initialized,
                "error": str(e)
            }


# 创建全局Spark工具实例
spark_utils = SparkUtils()

# 创建全局PySpark服务实例
pyspark_service = PySparkService()
