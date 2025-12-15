"""
实时数据消费服务
从Kafka消费实时流数据并存储到DuckDB数据库中
"""

import asyncio
import json
import time
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional

import duckdb
import pandas as pd
from kafka import KafkaConsumer

from utils.config import settings
from utils.logger import logger


class RealtimeDataConsumer:
    """实时数据消费者"""

    def __init__(self):
        """初始化消费者"""
        # DuckDB配置
        self.db_path = Path(settings.fraudhunter_realtime_data_storage_path) / "realtime_inct.duckdb"
        self.conn: Optional[duckdb.DuckDBPyConnection] = None

        # Kafka配置
        self.bootstrap_servers = settings.fraudhunter_realtime_kafka_bootstrap_servers
        self.topic = settings.fraudhunter_realtime_kafka_topic
        self.group_id = settings.fraudhunter_realtime_kafka_group_id
        self.consumer: Optional[KafkaConsumer] = None

        # 缓冲配置
        self.buffer = []
        self.buffer_size = settings.fraudhunter_realtime_writer_buffer_size
        self.flush_interval = settings.fraudhunter_realtime_writer_flush_interval

        # 运行状态
        self._running = False
        self._consume_thread = None
        self.last_flush_time = time.time()

        # 监控指标
        self.metrics = {
            'messages_consumed': 0,
            'messages_written': 0,
            'parse_errors': 0,
            'write_errors': 0,
            'last_message_time': None
        }

    async def start(self):
        """启动消费者（异步）"""
        try:
            logger.info("开始启动实时数据消费者...")

            # 1. 初始化DuckDB
            self._init_duckdb()

            # 2. 初始化Kafka消费者
            self._init_kafka_consumer()

            # 3. 在线程中启动消费循环
            self._running = True
            loop = asyncio.get_event_loop()
            self._consume_thread = loop.run_in_executor(
                None,  # 使用默认线程池
                self._consume_loop
            )

            logger.info("实时数据消费者启动成功")

        except Exception as e:
            logger.error(f"启动实时数据消费者失败: {e}", exc_info=True)
            raise

    def _init_duckdb(self):
        """初始化DuckDB数据库和表"""
        try:
            # 创建存储目录
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # 连接数据库
            self.conn = duckdb.connect(str(self.db_path))

            # 创建表（如果不存在）
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS realtime_inct (
                    acct_no VARCHAR NOT NULL,
                    txn_amt DECIMAL(18,2),
                    etl_date DATE NOT NULL,
                    event_time TIMESTAMP,
                    raw_data JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_etl_date
                ON realtime_inct(etl_date)
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_acct_no
                ON realtime_inct(acct_no)
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_time
                ON realtime_inct(event_time)
            """)

            logger.info(f"DuckDB初始化完成: {self.db_path}")

        except Exception as e:
            logger.error(f"DuckDB初始化失败: {e}", exc_info=True)
            raise

    def _init_kafka_consumer(self):
        """初始化Kafka消费者"""
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                enable_auto_commit=False,  # 手动提交offset
                auto_offset_reset=settings.fraudhunter_realtime_kafka_auto_offset_reset,
                max_poll_records=settings.fraudhunter_realtime_kafka_max_poll_records,
                session_timeout_ms=settings.fraudhunter_realtime_kafka_session_timeout_ms,
                heartbeat_interval_ms=settings.fraudhunter_realtime_kafka_heartbeat_interval_ms,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )

            logger.info(f"Kafka消费者初始化完成: topic={self.topic}, group={self.group_id}")

        except Exception as e:
            logger.error(f"Kafka消费者初始化失败: {e}", exc_info=True)
            raise

    def _consume_loop(self):
        """消费循环（在独立线程中运行）"""
        logger.info("开始消费Kafka消息...")

        while self._running:
            try:
                # 批量拉取消息
                messages = self.consumer.poll(timeout_ms=5000)

                if messages:
                    for topic_partition, records in messages.items():
                        for record in records:
                            self._handle_message(record)

                # 检查是否需要刷新缓冲区
                current_time = time.time()
                if (len(self.buffer) >= self.buffer_size or
                    current_time - self.last_flush_time >= self.flush_interval):
                    self._flush_buffer()

            except Exception as e:
                logger.error(f"消费循环异常: {e}", exc_info=True)
                time.sleep(5)  # 异常后等待5秒再重试

        # 停止前刷新剩余数据
        if self.buffer:
            self._flush_buffer()
        logger.info("消费循环已停止")

    def _handle_message(self, record):
        """处理单条消息"""
        try:
            # 解析JSON
            value = record.value

            # 提取data字段
            if 'data' not in value:
                logger.warning(f"消息缺少data字段: offset={record.offset}")
                self.metrics['parse_errors'] += 1
                return

            data = value['data']
            if isinstance(data, str):
                data = json.loads(data)

            # 如果data是数组，展开
            if isinstance(data, list):
                items = data
            else:
                items = [data]

            # 添加到缓冲区
            for item in items:
                parsed_record = {
                    'acct_no': item.get('acct_no'),
                    'txn_amt': item.get('txn_amt'),
                    'etl_date': date.today(),  # 使用当前日期
                    'event_time': datetime.now(),
                    'raw_data': json.dumps(item, ensure_ascii=False)
                }
                self.buffer.append(parsed_record)
                self.metrics['messages_consumed'] += 1

            self.metrics['last_message_time'] = datetime.now()

        except Exception as e:
            logger.error(f"解析消息失败: {e}, offset={record.offset}", exc_info=True)
            self.metrics['parse_errors'] += 1

    def _flush_buffer(self):
        """刷新缓冲区到DuckDB"""
        if not self.buffer:
            return

        try:
            # 批量插入DuckDB
            df = pd.DataFrame(self.buffer)

            # 开始事务
            self.conn.execute("BEGIN TRANSACTION")

            # 插入数据
            self.conn.execute("INSERT INTO realtime_inct SELECT * FROM df")

            # 提交事务
            self.conn.execute("COMMIT")

            # 提交Kafka offset
            self.consumer.commit()

            # 更新指标
            self.metrics['messages_written'] += len(self.buffer)
            logger.info(f"成功写入 {len(self.buffer)} 条记录到DuckDB")

            # 清空缓冲区
            self.buffer = []
            self.last_flush_time = time.time()

        except Exception as e:
            logger.error(f"刷新缓冲区失败: {e}", exc_info=True)
            self.metrics['write_errors'] += 1

            # 回滚事务
            try:
                self.conn.execute("ROLLBACK")
            except Exception as rollback_error:
                logger.error(f"回滚事务失败: {rollback_error}")

            # 不清空缓冲区，下次重试

    async def stop(self):
        """停止消费者"""
        logger.info("正在停止实时数据消费者...")
        self._running = False

        # 等待消费线程结束
        if self._consume_thread:
            try:
                await self._consume_thread
            except Exception as e:
                logger.error(f"等待消费线程结束异常: {e}", exc_info=True)

        # 关闭Kafka消费者
        if self.consumer:
            try:
                self.consumer.close()
                logger.info("Kafka消费者已关闭")
            except Exception as e:
                logger.error(f"关闭Kafka消费者失败: {e}", exc_info=True)

        # 关闭DuckDB连接
        if self.conn:
            try:
                self.conn.close()
                logger.info("DuckDB连接已关闭")
            except Exception as e:
                logger.error(f"关闭DuckDB连接失败: {e}", exc_info=True)

        logger.info("实时数据消费者已停止")

    def get_metrics(self) -> Dict:
        """获取监控指标"""
        return self.metrics.copy()
