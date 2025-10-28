import os.path
import pathlib

from retry import retry

from .logger import logger
from utils.config import settings
import jaydebeapi
from typing import Dict, Any, Optional, List, Union, Literal


class SparkUtils:
    _instance = None
    conn = None
    cur = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SparkUtils, cls).__new__(cls)
        return cls._instance

    def _get_spark_connect(self):
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
                if hasattr(item, '__class__') and 'JDouble' in str(type(item)):
                    # 转换 JDouble 为 float
                    converted_row.append(float(item))
                elif hasattr(item, '__class__') and 'JLong' in str(type(item)):
                    # 转换 JLong 为 int
                    converted_row.append(int(item))
                elif hasattr(item, '__class__') and 'JInt' in str(type(item)):
                    # 转换 JInt 为 int
                    converted_row.append(int(item))
                else:
                    converted_row.append(item)
            converted_results.append(converted_row)
    
        return converted_results
    
    
    def query_sql(self, sql: str, params: Optional[tuple] = None,
                  return_type: Literal['dict', 'list'] = 'dict') -> List[Union[Dict[str, Any], List[Any]]]:
        """
        执行查询SQL语句

        Args:
            sql: SQL查询语句
            connection_name: 连接名称
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
        logger.info("关闭Spark连接")
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()


# 创建全局Spark工具实例
spark_utils = SparkUtils()
