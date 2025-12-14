#!/usr/bin/env python3
"""
Kafka Canal模拟数据生成器
持续向Kafka发送模拟的Canal格式数据，支持INSERT操作

使用示例：
# 基本用法
python kafka_canal_simulator.py --topic canal-topic

# 指定Kafka服务器和数据库
python kafka_canal_simulator.py --topic canal-topic --bootstrap-servers localhost:9092 --database my_db

# 设置发送间隔和最大消息数
python kafka_canal_simulator.py --topic canal-topic --interval 2.0 --max-messages 100

# 只模拟特定表
python kafka_canal_simulator.py --topic canal-topic --tables users orders

# 列出可用表配置
python kafka_canal_simulator.py --list-tables

配置说明：
- 脚本顶部的TABLE_CONFIGS可以自定义表结构
- SENDING_RULES可以调整发送间隔、表权重等
- 支持的数据类型：int, bigint, varchar, text, timestamp, decimal, float, double, boolean, json
- 数据模板支持：列表选择、范围值、模板字符串、JSON对象

安装依赖：
pip install kafka-python
"""

import json
import random
import time
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import uuid

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 配置区域 - 可以在这里修改表结构和数据生成规则
# ============================================================================

# 表配置定义
TABLE_CONFIGS = {
    'users': {
        'name': 'users',
        'columns': {
            'id': 'int',
            'username': 'varchar(50)',
            'email': 'varchar(100)',
            'phone': 'varchar(20)',
            'status': 'int',
            'created_at': 'timestamp',
            'updated_at': 'timestamp'
        },
        'pk_names': ['id'],
        'data_templates': {
            'username': ['john_doe', 'jane_smith', 'bob_wilson', 'alice_brown', 'charlie_davis'],
            'email': ['user{}@example.com', '{}@test.com', '{}.demo@email.com'],
            'phone': ['138{}', '139{}', '186{}'],
            'status': [0, 1]  # 0: inactive, 1: active
        }
    }
}

# 发送规则配置
SENDING_RULES = {
    'default_interval': 1.0,  # 默认发送间隔（秒）
    'table_weights': {  # 表的发送权重（概率）
        'users': 0.2,
        'orders': 0.2,
        'products': 0.1,
        'logs': 0.3,
        'metrics': 0.2
    },
    'batch_size_range': (1, 10),  # 每批数据行数范围
    'time_drift': (1000, 10000),  # binlog时间戳的时间偏移范围（毫秒）
}

# ============================================================================
# 核心代码 - 一般不需要修改下面的代码
# ============================================================================

@dataclass
class TableConfig:
    """表配置"""
    name: str
    columns: Dict[str, str]  # 列名 -> 数据类型
    pk_names: List[str]  # 主键字段名
    data_templates: Dict[str, Any]  # 数据模板


@dataclass
class CanalMessage:
    """Canal消息结构"""
    data: List[Dict[str, Any]]
    database: str
    es: int  # binlog执行时间戳
    id: int
    isDdl: bool
    mysqlType: Dict[str, str]
    old: Optional[List[Dict[str, Any]]]
    pkNames: List[str]
    sql: str
    sqlType: Dict[str, int]
    table: str
    ts: int  # Canal处理时间戳
    type: str  # INSERT, UPDATE, DELETE


class CanalDataGenerator:
    """Canal数据生成器"""

    def __init__(self):
        self.message_id = 1

        # MySQL类型到Java SQL类型的映射
        self.mysql_to_sql_type = {
            'int': 4,
            'bigint': -5,
            'varchar': 12,
            'text': 12,
            'timestamp': 93,
            'datetime': 93,
            'decimal': 3,
            'float': 8,
            'double': 8,
            'boolean': -7,
            'date': 91,
            'json': 12,  # JSON类型使用varchar的SQL类型
        }

        # 使用配置中的表定义
        self.table_configs = {}
        for table_name, config in TABLE_CONFIGS.items():
            self.table_configs[table_name] = TableConfig(
                name=config['name'],
                columns=config['columns'],
                pk_names=config['pk_names'],
                data_templates=config['data_templates']
            )

    def generate_row_data(self, table_config: TableConfig) -> Dict[str, Any]:
        """生成单行数据"""
        data = {}

        for col_name, col_type in table_config.columns.items():
            if col_name in table_config.data_templates:
                template = table_config.data_templates[col_name]

                if isinstance(template, list):
                    # 从列表中随机选择
                    if '{}' in str(template[0]):
                        if col_name == 'email':
                            data[col_name] = random.choice(template).format(
                                ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                            )
                        elif col_name == 'order_no':
                            data[col_name] = random.choice(template).format(
                                ''.join(random.choices('0123456789', k=8))
                            )
                        elif col_name == 'name':
                            data[col_name] = random.choice(template).format(
                                random.randint(1000, 9999)
                            )
                        else:
                            data[col_name] = random.choice(template)
                    else:
                        data[col_name] = random.choice(template)

                elif isinstance(template, tuple) and len(template) == 2:
                    # 范围值
                    min_val, max_val = template
                    if 'int' in col_type.lower():
                        data[col_name] = random.randint(int(min_val), int(max_val))
                    elif 'decimal' in col_type.lower() or 'float' in col_type.lower() or 'double' in col_type.lower():
                        data[col_name] = round(random.uniform(min_val, max_val), 2)

                elif isinstance(template, dict):
                    # JSON对象
                    json_obj = {}
                    for key, value in template.items():
                        if isinstance(value, str) and '{}' in value:
                            if key in ['ip_address', 'host']:
                                json_obj[key] = value.format(random.randint(1, 254))
                            else:
                                json_obj[key] = value.format(random.randint(1000, 9999))
                        elif isinstance(value, list):
                            json_obj[key] = random.choice(value)
                        else:
                            json_obj[key] = value
                    data[col_name] = json.dumps(json_obj)

            else:
                # 根据类型生成默认值
                if col_type.startswith('int'):
                    if 'id' in col_name.lower():
                        data[col_name] = self.message_id + random.randint(1, 10000)
                    else:
                        data[col_name] = random.randint(1, 1000)
                elif col_type.startswith('bigint'):
                    if 'id' in col_name.lower():
                        data[col_name] = self.message_id + random.randint(1, 1000000)
                    else:
                        data[col_name] = random.randint(1, 1000000)
                elif col_type.startswith('varchar') or col_type == 'text':
                    if col_name == 'phone':
                        data[col_name] = f"{random.randint(130, 199)}{random.randint(10000000, 99999999)}"
                    else:
                        data[col_name] = f"generated_{random.randint(1000, 9999)}"
                elif col_type in ['timestamp', 'datetime']:
                    # 生成最近30天内的时间戳
                    days_ago = random.randint(0, 30)
                    hours_ago = random.randint(0, 23)
                    minutes_ago = random.randint(0, 59)
                    timestamp = datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
                    data[col_name] = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                elif col_type.startswith('decimal'):
                    data[col_name] = round(random.uniform(1.0, 1000.0), 2)
                elif col_type.startswith('boolean'):
                    data[col_name] = random.choice([True, False])
                elif col_type == 'json':
                    # 生成默认JSON
                    data[col_name] = json.dumps({
                        "generated": True,
                        "value": f"default_{random.randint(100, 999)}"
                    })
                else:
                    data[col_name] = f"default_value_{random.randint(100, 999)}"

        return data

    def generate_canal_message(self, table_name: str, database_name: str = 'test_db') -> CanalMessage:
        """生成Canal格式的消息"""
        if table_name not in self.table_configs:
            raise ValueError(f"未知的表名: {table_name}")

        table_config = self.table_configs[table_name]

        # 使用配置中的批量大小范围
        min_batch, max_batch = SENDING_RULES['batch_size_range']
        row_count = random.randint(min_batch, max_batch)
        data_rows = []

        for _ in range(row_count):
            data_rows.append(self.generate_row_data(table_config))

        # 生成时间戳
        current_time = int(time.time() * 1000)
        min_drift, max_drift = SENDING_RULES['time_drift']
        binlog_time = current_time - random.randint(min_drift, max_drift)  # binlog时间稍早于处理时间

        # 构建消息
        message = CanalMessage(
            data=data_rows,
            database=database_name,
            es=binlog_time,
            id=self.message_id,
            isDdl=False,
            mysqlType=table_config.columns,
            old=None,
            pkNames=table_config.pk_names,
            sql='',
            sqlType={col: self.mysql_to_sql_type.get(col_type.split('(')[0], 12)
                    for col, col_type in table_config.columns.items()},
            table=table_name,
            ts=current_time,
            type='INSERT'
        )

        self.message_id += 1
        return message

    def get_available_tables(self) -> List[str]:
        """获取可用的表列表"""
        return list(self.table_configs.keys())


class KafkaCanalSimulator:
    """Kafka Canal模拟器"""

    def __init__(self, bootstrap_servers: str, topic: str, database_name: str = 'test_db'):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.database_name = database_name
        self.producer = None
        self.generator = CanalDataGenerator()

    def connect(self):
        """连接Kafka"""
        if not KAFKA_AVAILABLE:
            logger.error("kafka-python包未安装，无法连接Kafka")
            logger.error("请运行: pip install kafka-python")
            raise ImportError("kafka-python包未安装")

        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                batch_size=16384,
                linger_ms=10,
                buffer_memory=33554432
            )
            logger.info(f"成功连接到Kafka: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"连接Kafka失败: {e}")
            raise

    def send_message(self, table_name: str, message_key: Optional[str] = None) -> bool:
        """发送消息"""
        try:
            canal_message = self.generator.generate_canal_message(table_name, self.database_name)
            message_dict = asdict(canal_message)

            # 发送消息
            future = self.producer.send(
                self.topic,
                key=message_key or f"{self.database_name}.{table_name}",
                value=message_dict
            )

            # 等待发送完成
            record_metadata = future.get(timeout=10)

            logger.info(f"消息发送成功 - 表: {table_name}, "
                       f"数据行数: {len(canal_message.data)}, "
                       f"分区: {record_metadata.partition}, "
                       f"偏移量: {record_metadata.offset}")

            return True

        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    def start_simulation(self, interval: float, tables: List[str], max_messages: Optional[int] = None):
        """开始模拟"""
        logger.info(f"开始模拟 - 间隔: {interval}秒, 表: {tables}, 最大消息数: {max_messages or '无限制'}")

        message_count = 0

        try:
            while True:
                # 根据权重选择表
                table_name = self._choose_table_by_weight(tables)

                # 发送消息
                success = self.send_message(table_name)

                if success:
                    message_count += 1

                    # 检查是否达到最大消息数
                    if max_messages and message_count >= max_messages:
                        logger.info(f"达到最大消息数限制: {max_messages}")
                        break

                # 等待间隔
                if interval > 0:
                    time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("收到中断信号，停止模拟")
        finally:
            self.close()

    def _choose_table_by_weight(self, tables: List[str]) -> str:
        """根据权重选择表"""
        # 获取可用表的权重
        weights = []
        available_tables = []

        for table in tables:
            if table in SENDING_RULES['table_weights']:
                weights.append(SENDING_RULES['table_weights'][table])
                available_tables.append(table)
            else:
                # 如果没有配置权重，使用默认权重
                weights.append(1.0)
                available_tables.append(table)

        # 归一化权重
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            weights = [1.0 / len(weights)] * len(weights)

        # 根据权重随机选择
        return random.choices(available_tables, weights=weights)[0]

    def close(self):
        """关闭连接"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Kafka连接已关闭")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Kafka Canal模拟数据生成器')
    parser.add_argument('--bootstrap-servers', default='localhost:9092',
                       help='Kafka服务器地址，默认: localhost:9092')
    parser.add_argument('--topic',
                       help='Kafka主题名称（除了--list-tables外必需）')
    parser.add_argument('--database', default='test_db',
                       help='数据库名称，默认: test_db')
    parser.add_argument('--interval', type=float, default=SENDING_RULES['default_interval'],
                       help=f'发送间隔（秒），默认: {SENDING_RULES["default_interval"]}')
    parser.add_argument('--tables', nargs='+',
                       choices=list(TABLE_CONFIGS.keys()) + ['all'],
                       default=['all'],
                       help=f'要模拟的表，可选: {" ".join(TABLE_CONFIGS.keys())} all，默认: all')
    parser.add_argument('--max-messages', type=int,
                       help='最大发送消息数量，默认无限制')
    parser.add_argument('--list-tables', action='store_true',
                       help='列出可用的表配置')

    args = parser.parse_args()

    # 验证参数
    if not args.list_tables and not args.topic:
        parser.error("--topic参数是必需的（除非使用--list-tables）")

    # 初始化生成器
    generator = CanalDataGenerator()

    if args.list_tables:
        tables = generator.get_available_tables()
        print("可用的表配置:")
        for table in tables:
            config = generator.table_configs[table]
            print(f"  {table}:")
            print(f"    列: {list(config.columns.keys())}")
            print(f"    主键: {config.pk_names}")
        return

    # 确定要使用的表
    if 'all' in args.tables:
        tables = list(TABLE_CONFIGS.keys())
    else:
        tables = args.tables

    # 创建模拟器
    simulator = KafkaCanalSimulator(args.bootstrap_servers, args.topic, args.database)

    try:
        # 连接Kafka
        simulator.connect()

        # 开始模拟
        simulator.start_simulation(args.interval, tables, args.max_messages)

    except Exception as e:
        logger.error(f"模拟运行失败: {e}")
        simulator.close()


if __name__ == '__main__':
    main()