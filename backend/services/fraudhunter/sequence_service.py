"""
FraudHunter序列编码生成服务

用于生成指标和指标任务的唯一编码
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from utils.logger import logger


class SequenceManager:
    """序列计数器管理器

    使用数据库序列计数器表来生成唯一编码
    采用 SELECT FOR UPDATE 悲观锁保证并发安全
    """

    def __init__(self, db: Session):
        self.db = db

    def get_next_sequence(self, counter_type: str) -> int:
        """获取下一个序列号（线程安全）

        使用数据库悲观锁（SELECT FOR UPDATE）确保在高并发环境下
        序列号的唯一性和连续性

        Args:
            counter_type: 计数器类型
                - 'indicator_task': 指标任务计数器
                - 'indicator_{object_type}_{indicator_type}': 指标计数器

        Returns:
            下一个序列号

        Raises:
            Exception: 数据库操作失败时抛出异常
        """
        try:
            # 使用悲观锁获取并更新计数器
            # FOR UPDATE 会锁定这一行，直到事务结束
            sql = text("""
                SELECT counter_value
                FROM fraudhunter_sequence_counter
                WHERE counter_type = :counter_type
                FOR UPDATE
            """)

            result = self.db.execute(sql, {"counter_type": counter_type}).fetchone()

            if result is None:
                # 首次使用此计数器类型，创建新记录
                insert_sql = text("""
                    INSERT INTO fraudhunter_sequence_counter (counter_type, counter_value)
                    VALUES (:counter_type, 1)
                """)
                self.db.execute(insert_sql, {"counter_type": counter_type})
                self.db.flush()
                logger.info(f"创建新计数器: {counter_type} = 1")
                return 1

            # 更新计数器到下一个值
            current_value = result[0]
            next_value = current_value + 1

            update_sql = text("""
                UPDATE fraudhunter_sequence_counter
                SET counter_value = :new_value
                WHERE counter_type = :counter_type
            """)
            self.db.execute(update_sql, {
                "counter_type": counter_type,
                "new_value": next_value
            })
            self.db.flush()

            logger.debug(f"生成序列号: {counter_type} = {next_value}")
            return next_value

        except Exception as e:
            logger.error(f"序列号生成失败: {counter_type}, 错误: {str(e)}")
            raise

    def generate_task_code(self) -> str:
        """生成指标任务编码

        Returns:
            格式：i_task_00001
            - 固定前缀：i_task_
            - 序号：5位数字，补零

        Examples:
            >>> generate_task_code()
            'i_task_00001'
            >>> generate_task_code()
            'i_task_00002'
        """
        seq = self.get_next_sequence('indicator_task')
        code = f"i_task_{seq:05d}"
        logger.debug(f"生成指标任务编码: {code}")
        return code

    def generate_indicator_code(
        self,
        object_type: str,
        indicator_type: str
    ) -> str:
        """生成指标编码

        按对象类型和指标类型分类计数，不同分类独立编号

        Args:
            object_type: 对象类型
                - cust_no: 客户号
                - dep_acct_no: 存款账号
                - loan_acct_no: 贷款账号
            indicator_type: 指标类型
                - offline: 离线
                - realtime: 实时

        Returns:
            格式：i_{object_type}_{indicator_type}_00001
            - 前缀包含对象类型和指标类型
            - 序号：5位数字，补零
            - 按分类独立计数

        Examples:
            >>> generate_indicator_code('cust_no', 'offline')
            'i_cust_no_offline_00001'
            >>> generate_indicator_code('dep_acct_no', 'realtime')
            'i_dep_acct_no_realtime_00001'
            >>> generate_indicator_code('cust_no', 'offline')
            'i_cust_no_offline_00002'

        Raises:
            ValueError: 当对象类型或指标类型不合法时
        """
        # 验证参数
        valid_object_types = ['cust_no', 'dep_acct_no', 'loan_acct_no']
        valid_indicator_types = ['offline', 'realtime']

        if object_type not in valid_object_types:
            raise ValueError(
                f"不合法的对象类型: {object_type}, "
                f"必须是: {', '.join(valid_object_types)}"
            )

        if indicator_type not in valid_indicator_types:
            raise ValueError(
                f"不合法的指标类型: {indicator_type}, "
                f"必须是: {', '.join(valid_indicator_types)}"
            )

        # 生成计数器类型标识
        counter_type = f"indicator_{object_type}_{indicator_type}"
        seq = self.get_next_sequence(counter_type)

        # 生成编码
        code = f"i_{object_type}_{indicator_type}_{seq:05d}"
        logger.debug(f"生成指标编码: {code}")
        return code
