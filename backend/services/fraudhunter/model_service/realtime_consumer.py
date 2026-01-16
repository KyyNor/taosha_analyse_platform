"""实时数据消费服务 - 从Kafka消费并存储到PostgreSQL"""

import asyncio
import json
import time
from datetime import date, datetime, timedelta
from typing import Dict, Optional

import pandas as pd
from kafka import KafkaConsumer

from utils.config import settings
from utils.logger import logger
from utils.analyze_db_utils import AnalyzeDBConnector, AnalyzeDBPartitionManager


# 实时交易字段列表
TRANSACTION_FIELDS = [
    'acct_no', 'acct_open_dt', 'acct_type', 'aorm_date',
    'branch_name', 'branch_no', 'busi_typ', 'ccy_name', 'cha_desc', 'channel', 'class_type',
    'cp_acct_name', 'cp_acct_no', 'cp_acct_type', 'cp_bank_branch_name', 'cp_bank_num',
    'cp_class_type', 'cp_int_cat', 'currency', 'cust_name', 'cust_type', 'customer_no',
    'fir_branch_name', 'fir_branch_no', 'gl_class_code',
    'inct_01_amount', 'inct_01_balance', 'inct_01_tran_acct',
    'inct_20_chnnel', 'inct_20_desc', 'inct_20_narr', 'inct_20_rec_no', 'inct_20_source',
    'inma_flag', 'int_cat', 'jrnl_no', 'mgr_no', 'mst_aom_no',
    'parent_branch_name', 'parent_branch_no', 'peri_no', 'prd_name', 'rec_no',
    'rt_processing_time', 'send_to_fh_time', 'tran_branch', 'tran_date', 'tran_time',
    'tran_type', 'trn_code'
]


class RealtimeDataConsumer:
    """实时数据消费者"""

    def __init__(self):
        self.bootstrap_servers = settings.fraudhunter_realtime_kafka_bootstrap_servers
        self.topic = settings.fraudhunter_realtime_kafka_topic
        self.group_id = settings.fraudhunter_realtime_kafka_group_id
        self.consumer: Optional[KafkaConsumer] = None

        self.buffer = []
        self.buffer_size = settings.fraudhunter_realtime_writer_buffer_size
        self.flush_interval = settings.fraudhunter_realtime_writer_flush_interval
        self.batch_insert_size = settings.fraudhunter_realtime_writer_batch_insert_size

        self._running = False
        self._consume_thread = None
        self.last_flush_time = time.time()
        self.last_log_time = time.time()
        self.insert_cnt = 0

        self.metrics = {
            'messages_consumed': 0,
            'messages_written': 0,
            'parse_errors': 0,
            'write_errors': 0,
            'last_message_time': None
        }

    async def start(self):
        try:
            logger.info("开始启动实时数据消费者...")
            AnalyzeDBPartitionManager.create_realtime_tables()
            self._init_kafka_consumer()
            self._running = True
            loop = asyncio.get_event_loop()
            self._consume_thread = loop.run_in_executor(None, self._consume_loop)
            logger.info("实时数据消费者启动成功")
        except Exception as e:
            logger.error(f"启动实时数据消费者失败: {e}", exc_info=True)
            raise

    def _init_kafka_consumer(self):
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                enable_auto_commit=False,
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
        logger.info("开始消费Kafka消息...")
        while self._running:
            try:
                messages = self.consumer.poll(timeout_ms=5000)
                if messages:
                    for topic_partition, records in messages.items():
                        for record in records:
                            self._handle_message(record)
                current_time = time.time()
                if len(self.buffer) >= self.buffer_size or current_time - self.last_flush_time >= self.flush_interval:
                    self._flush_buffer()
            except Exception as e:
                logger.error(f"消费循环异常: {e}", exc_info=True)
                time.sleep(5)
        if self.buffer:
            self._flush_buffer()
        logger.info("消费循环已停止")

    def _handle_message(self, record):
        try:
            value = record.value
            if 'data' not in value:
                logger.warning(f"消息缺少data字段: offset={record.offset}")
                self.metrics['parse_errors'] += 1
                return

            data = value['data']
            if isinstance(data, str):
                data = json.loads(data)
            items = data if isinstance(data, list) else [data]

            for item in items:
                if item:
                    parsed_record = {field: item.get(field) for field in TRANSACTION_FIELDS}
                    self.buffer.append(parsed_record)
                    self.metrics['messages_consumed'] += 1
            self.metrics['last_message_time'] = datetime.now()
        except Exception as e:
            logger.error(f"解析消息失败: {e}, offset={record.offset}", exc_info=True)
            self.metrics['parse_errors'] += 1

    def _parse_tran_date(self, date_str) -> date:
        try:
            date_str = str(date_str)
            if len(date_str) == 8:  # YYYYMMDD
                return date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            logger.warning(f"无法解析日期: {date_str}, 使用当前日期")
            return date.today()

    def _flush_buffer(self):
        if not self.buffer:
            return

        try:
            df = pd.DataFrame(self.buffer)
            current_date = datetime.now()
            next_date = (datetime.now() + timedelta(days=1))
            
            # 确保当前日期和第二天的分区存在
            AnalyzeDBPartitionManager.ensure_partition('realtime_oss_inct_new', current_date)
            AnalyzeDBPartitionManager.ensure_partition('realtime_oss_inct_new', next_date)

            AnalyzeDBConnector.batch_insert(
                'realtime_oss_inct_new', df,
                chunksize=self.batch_insert_size,
                if_exists='append'
            )
            self.consumer.commit()
            self.metrics['messages_written'] += len(self.buffer)

            current_time = time.time()
            if current_time - self.last_log_time > 1800:
                logger.info(f"成功写入 {self.insert_cnt + len(self.buffer)} 条记录到PostgreSQL")
                self.insert_cnt = 0
                self.last_log_time = current_time
            else:
                self.insert_cnt += len(self.buffer)

            self.buffer = []
            self.last_flush_time = time.time()
        except Exception as e:
            logger.error(f"刷新缓冲区失败: {e}", exc_info=True)
            self.metrics['write_errors'] += 1

    async def stop(self):
        logger.info("正在停止实时数据消费者...")
        self._running = False
        if self._consume_thread:
            try:
                await self._consume_thread
            except Exception as e:
                logger.error(f"等待消费线程结束异常: {e}", exc_info=True)
        if self.consumer:
            try:
                self.consumer.close()
                logger.info("Kafka消费者已关闭")
            except Exception as e:
                logger.error(f"关闭Kafka消费者失败: {e}", exc_info=True)
        logger.info("实时数据消费者已停止")

    def get_metrics(self) -> Dict:
        return self.metrics.copy()
