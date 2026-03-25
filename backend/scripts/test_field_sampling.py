#!/usr/bin/env python
"""字段采样测试脚本"""

import sys
sys.path.insert(0, str(__file__).rsplit('/', 1)[0] + '/..')

from sqlalchemy.orm import Session
from models.db_base import get_db_session
from services.vector_store.field_value_sampler import FieldValueSampler

def test_sampling(table_id: int, table_name: str, column_name: str = None):
    """测试字段采样

    Args:
        table_id: 表 ID
        table_name: 表名 (格式：库名.表名)
        column_name: 字段名，为空则采样全部字段
    """
    print(f"\n{'='*60}")
    print(f"开始采样测试：{table_name}")
    print(f"{'='*60}\n")

    with get_db_session() as db:
        sampler = FieldValueSampler(db)

        if column_name:
            # 测试单个字段
            print(f"采样字段：{column_name}")
            result = sampler.sample_field_values(
                table_id=table_id,
                table_name=table_name,
                column_name=column_name,
                limit=20
            )
            print(f"采样类型：{result.get('sample_type')}")
            print(f"采样值：{result.get('values', [])[:10]}")
            if result.get('stats'):
                print(f"统计信息：{result['stats']}")
        else:
            # 测试整张表的所有字段
            print(f"采样子表：{table_name}")
            results = sampler.sample_table_fields(table_id=table_id, limit=20)

            for col_name, sample in results.items():
                print(f"\n[{col_name}]")
                print(f"  采样类型：{sample.get('sample_type')}")
                values = sample.get('values', [])
                print(f"  采样值 ({len(values)}个): {values[:5]}")
                if sample.get('stats'):
                    print(f"  统计信息：{sample['stats']}")
                if sample.get('min_val') or sample.get('max_val'):
                    print(f"  范围：{sample.get('min_val')} ~ {sample.get('max_val')}")

        print(f"\n{'='*60}")
        print("采样完成")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    # 修改这里进行测试
    TABLE_ID = 1  # 替换为你的表 ID
    TABLE_NAME = "nodeA_whjcbb.test_table"  # 替换为你的表名
    COLUMN_NAME = None  # 指定字段名或留空测试全部字段

    test_sampling(TABLE_ID, TABLE_NAME, COLUMN_NAME)
