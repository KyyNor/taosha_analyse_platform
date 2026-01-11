#!/usr/bin/env python3
"""
FraudHunter 实时交易数据模拟器
持续向 PostgreSQL realtime_oss_inct_new 表插入测试数据

用法:
    # 基本用法 (默认配置)
    python insert_realtime_test_data.py

    # 自定义配置
    python insert_realtime_test_data.py --host localhost --port 5433 --interval 2

    # 指定插入数量后退出
    python insert_realtime_test_data.py --count 100

    # 后台运行
    nohup python insert_realtime_test_data.py > realtime_data.log 2>&1 &
"""

import argparse
import random
import time
import logging
from datetime import datetime, timedelta
from typing import List
import psycopg2
from psycopg2.extras import execute_batch
from psycopg2.pool import SimpleConnectionPool

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('realtime_data_inserter.log')
    ]
)
logger = logging.getLogger(__name__)


# 测试数据池
BRANCHES = [
    ('BJ001', '北京分行'),
    ('SH002', '上海分行'),
    ('GZ003', '广州分行'),
    ('SZ004', '深圳分行'),
    ('HZ005', '杭州分行'),
]

CUSTOMERS = [
    ('CUST001', '张三', '6227001234567890'),
    ('CUST002', '李四', '6227001234567891'),
    ('CUST003', '王五', '6227001234567892'),
    ('CUST004', '赵六', '6227001234567893'),
    ('CUST005', '钱七', '6227001234567894'),
    ('CUST006', '孙八', '6227001234567895'),
    ('CUST007', '周九', '6227001234567896'),
    ('CUST008', '吴十', '6227001234567897'),
]

ACCT_TYPES = ['储蓄卡', '信用卡', '借记卡', '结算账户']
CHANNELS = ['手机银行', '网上银行', 'ATM', '柜面', 'POS', '第三方支付']
TRAN_TYPES = ['转账', '存款', '取现', '消费', '代发', '退款']
CURRENCIES = ['CNY', 'USD', 'EUR', 'HKD']

# 高风险交易模式 (用于测试风控规则)
HIGH_RISK_PATTERNS = [
    # 大额交易
    {'amount_range': (50000, 100000), 'weight': 1},
    # 频繁小额交易
    {'amount_range': (1000, 3000), 'weight': 3},
    # 正常交易
    {'amount_range': (100, 10000), 'weight': 10},
]


class RealtimeDataInserter:
    """实时交易数据插入器"""

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 15433,
        database: str = 'fraudhunter',
        user: str = 'fraudhunter',
        password: str = 'fraudhunter123',
        batch_size: int = 10,
        insert_interval: float = 1.0,
        max_count: int = None,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.batch_size = batch_size
        self.insert_interval = insert_interval
        self.max_count = max_count
        self.inserted_count = 0

        # 创建连接池
        try:
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
            )
            logger.info(f"成功连接到 PostgreSQL: {host}:{port}/{database}")
        except Exception as e:
            logger.error(f"连接数据库失败: {e}")
            raise

    def generate_test_record(self) -> dict:
        """生成一条测试交易记录"""
        now = datetime.now()
        branch_no, branch_name = random.choice(BRANCHES)
        cust_id, cust_name, acct_no = random.choice(CUSTOMERS)

        # 根据权重选择交易模式
        pattern = random.choices(
            HIGH_RISK_PATTERNS,
            weights=[p['weight'] for p in HIGH_RISK_PATTERNS],
            k=1
        )[0]
        amount = random.uniform(*pattern['amount_range'])

        # 生成交易时间 (最近24小时内)
        tran_datetime = now - timedelta(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )

        return {
            'acct_no': acct_no,
            'acct_open_dt': '2023-01-01',
            'acct_type': random.choice(ACCT_TYPES),
            'aorm_date': now.strftime('%Y-%m-%d'),
            'branch_name': branch_name,
            'branch_no': branch_no,
            'busi_typ': random.choice(['个人业务', '公司业务', '同业业务']),
            'ccy_name': random.choice(CURRENCIES),
            'cha_desc': f"交易{random.randint(1000, 9999)}",
            'channel': random.choice(CHANNELS),
            'class_type': random.choice(['一类户', '二类户', '三类户']),
            'cp_acct_name': random.choice([cust_name, '对方账户', '商户A', '商户B']),
            'cp_acct_no': f"6227{random.randint(1000000000, 9999999999)}",
            'cp_acct_type': random.choice(ACCT_TYPES),
            'cp_bank_branch_name': random.choice([branch_name, '其他银行']),
            'cp_bank_num': random.choice([branch_no, 'OTHER001']),
            'cp_class_type': random.choice(['一类户', '二类户']),
            'cp_int_cat': random.choice(['对公', '对私']),
            'currency': random.choice(CURRENCIES),
            'cust_name': cust_name,
            'cust_type': random.choice(['个人', '企业', '同业']),
            'customer_no': cust_id,
            'fir_branch_name': '总行',
            'fir_branch_no': 'HEAD001',
            'gl_class_code': f"{random.randint(1000, 9999)}",
            'inct_01_amount': round(amount, 2),
            'inct_01_balance': round(random.uniform(1000, 100000), 2),
            'inct_01_tran_acct': acct_no,
            'inct_20_chnnel': random.choice(['APP', 'WEB', '柜台']),
            'inct_20_desc': random.choice(['转账汇款', '现金存款', '消费支付']),
            'inct_20_narr': f"业务描述{random.randint(100, 999)}",
            'inct_20_rec_no': f"REC{now.strftime('%Y%m%d')}{random.randint(10000, 99999)}",
            'inct_20_source': random.choice(['核心系统', 'ESB', '直连']),
            'inma_flag': random.choice(['Y', 'N']),
            'int_cat': random.choice(['活期', '定期', '理财']),
            'jrnl_no': f"JNL{random.randint(10000000, 99999999)}",
            'mgr_no': f"MGR{random.randint(100, 999)}",
            'mst_aom_no': random.choice(['AOM001', 'AOM002', 'AOM003']),
            'parent_branch_name': '总行',
            'parent_branch_no': 'HEAD001',
            'peri_no': now.strftime('%Y%m'),
            'prd_name': random.choice(['活期存款', '定期存款', '通知存款']),
            'rec_no': f"{now.strftime('%Y%m%d')}{random.randint(100000, 999999)}",
            'rt_processing_time': tran_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'send_to_fh_time': tran_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'tran_branch': branch_no,
            'tran_date': tran_datetime.date(),
            'tran_time': tran_datetime.strftime('%H:%M:%S'),
            'tran_type': random.choice(TRAN_TYPES),
            'trn_code': f"TRN{random.randint(1000, 9999)}",
            'created_at': now,
            'updated_at': now,
        }

    def insert_batch(self, records: List[dict]) -> bool:
        """批量插入数据"""
        conn = None
        try:
            conn = self.pool.getconn()
            cursor = conn.cursor()

            sql = """
                INSERT INTO realtime_oss_inct_new (
                    acct_no, acct_open_dt, acct_type, aorm_date, branch_name, branch_no,
                    busi_typ, ccy_name, cha_desc, channel, class_type,
                    cp_acct_name, cp_acct_no, cp_acct_type, cp_bank_branch_name, cp_bank_num,
                    cp_class_type, cp_int_cat, currency, cust_name, cust_type, customer_no,
                    fir_branch_name, fir_branch_no, gl_class_code,
                    inct_01_amount, inct_01_balance, inct_01_tran_acct,
                    inct_20_chnnel, inct_20_desc, inct_20_narr, inct_20_rec_no, inct_20_source,
                    inma_flag, int_cat, jrnl_no, mgr_no, mst_aom_no,
                    parent_branch_name, parent_branch_no, peri_no, prd_name, rec_no,
                    rt_processing_time, send_to_fh_time, tran_branch, tran_date, tran_time, tran_type, trn_code,
                    created_at, updated_at
                ) VALUES (
                    %(acct_no)s, %(acct_open_dt)s, %(acct_type)s, %(aorm_date)s, %(branch_name)s, %(branch_no)s,
                    %(busi_typ)s, %(ccy_name)s, %(cha_desc)s, %(channel)s, %(class_type)s,
                    %(cp_acct_name)s, %(cp_acct_no)s, %(cp_acct_type)s, %(cp_bank_branch_name)s, %(cp_bank_num)s,
                    %(cp_class_type)s, %(cp_int_cat)s, %(currency)s, %(cust_name)s, %(cust_type)s, %(customer_no)s,
                    %(fir_branch_name)s, %(fir_branch_no)s, %(gl_class_code)s,
                    %(inct_01_amount)s, %(inct_01_balance)s, %(inct_01_tran_acct)s,
                    %(inct_20_chnnel)s, %(inct_20_desc)s, %(inct_20_narr)s, %(inct_20_rec_no)s, %(inct_20_source)s,
                    %(inma_flag)s, %(int_cat)s, %(jrnl_no)s, %(mgr_no)s, %(mst_aom_no)s,
                    %(parent_branch_name)s, %(parent_branch_no)s, %(peri_no)s, %(prd_name)s, %(rec_no)s,
                    %(rt_processing_time)s, %(send_to_fh_time)s, %(tran_branch)s, %(tran_date)s, %(tran_time)s, %(tran_type)s, %(trn_code)s,
                    %(created_at)s, %(updated_at)s
                )
            """

            execute_batch(cursor, sql, records, page_size=100)
            conn.commit()

            self.inserted_count += len(records)
            logger.info(f"成功插入 {len(records)} 条记录，总计: {self.inserted_count} 条")

            return True

        except Exception as e:
            logger.error(f"插入数据失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.pool.putconn(conn)

    def check_partition_exists(self, date: datetime.date) -> bool:
        """检查分区是否存在"""
        conn = None
        try:
            conn = self.pool.getconn()
            cursor = conn.cursor()

            partition_name = f"realtime_oss_inct_new_{date.strftime('%Y%m%d')}"
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_tables
                    WHERE schemaname = 'public' AND tablename = %s
                )
            """, (partition_name,))

            return cursor.fetchone()[0]

        except Exception as e:
            logger.error(f"检查分区失败: {e}")
            return False
        finally:
            if conn:
                self.pool.putconn(conn)

    def create_partition_if_needed(self, date: datetime.date):
        """创建分区 (如果不存在)"""
        if self.check_partition_exists(date):
            return

        conn = None
        try:
            conn = self.pool.getconn()
            cursor = conn.cursor()

            partition_name = f"realtime_oss_inct_new_{date.strftime('%Y%m%d')}"
            start_date = date.strftime('%Y-%m-%d')
            end_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')

            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {partition_name}
                PARTITION OF realtime_oss_inct_new
                FOR VALUES FROM ('{start_date}') TO ('{end_date}')
            """)
            conn.commit()

            logger.info(f"创建分区: {partition_name}")

        except Exception as e:
            logger.error(f"创建分区失败: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.pool.putconn(conn)

    def run(self):
        """持续运行数据插入"""
        logger.info(f"开始插入数据，批次大小: {self.batch_size}，间隔: {self.insert_interval}秒")
        if self.max_count:
            logger.info(f"最大插入数量: {self.max_count}")

        try:
            while True:
                # 检查是否达到最大数量
                if self.max_count and self.inserted_count >= self.max_count:
                    logger.info(f"已达到最大插入数量 {self.max_count}，停止运行")
                    break

                # 生成分批数据
                batch_records = [self.generate_test_record() for _ in range(self.batch_size)]

                # 确保分区存在
                for record in batch_records:
                    self.create_partition_if_needed(record['tran_date'])

                # 插入数据
                if not self.insert_batch(batch_records):
                    logger.warning("批次插入失败，等待后重试...")
                    time.sleep(5)
                    continue

                # 检查是否需要退出
                if self.max_count and self.inserted_count >= self.max_count:
                    break

                # 等待下一批次
                time.sleep(self.insert_interval)

        except KeyboardInterrupt:
            logger.info("收到中断信号，正在停止...")
        finally:
            self.pool.closeall()
            logger.info(f"总共插入了 {self.inserted_count} 条记录")


def main():
    parser = argparse.ArgumentParser(
        description='FraudHunter 实时交易数据模拟器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--host', default='localhost', help='PostgreSQL 主机')
    parser.add_argument('--port', type=int, default=15433, help='PostgreSQL 端口')
    parser.add_argument('--database', default='fraudhunter', help='数据库名')
    parser.add_argument('--user', default='fraudhunter', help='用户名')
    parser.add_argument('--password', default='fraudhunter123', help='密码')
    parser.add_argument('--batch-size', type=int, default=10, help='每批次插入数量')
    parser.add_argument('--interval', type=float, default=1.0, help='插入间隔(秒)')
    parser.add_argument('--count', type=int, help='最大插入数量 (不指定则持续运行)')

    args = parser.parse_args()

    inserter = RealtimeDataInserter(
        host=args.host,
        port=args.port,
        database=args.database,
        user=args.user,
        password=args.password,
        batch_size=args.batch_size,
        insert_interval=args.interval,
        max_count=args.count,
    )

    inserter.run()


if __name__ == '__main__':
    main()
