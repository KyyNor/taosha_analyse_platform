"""对账 checksum 公式（PR#12 评论#3）：结构化 hash 消除拼接假阳性

旧公式 sum(hash(concat_ws('|', ...))) 的两类假阳性：
- NULL 被 concat_ws 跳过 → ('a', NULL, 'b') 与 ('a', 'b', NULL) 校验和相同；
- 字段值含 '|' → ('a|b', 'c') 与 ('a', 'b|c') 拼接结果相同。

新公式 sum(hash(c1::VARCHAR, c2::VARCHAR, ...))：变参 hash 按值结构组合，
NULL 参与哈希、字段边界天然区分；两侧关系均在 DuckDB 内执行，直接在
本地 DuckDB 上验证公式行为。
"""

import importlib.util
import sys
from pathlib import Path

import duckdb

_backend_root = Path(__file__).parents[4] / "backend"

_spec = importlib.util.spec_from_file_location(
    "checksum_for_test",
    _backend_root / "services" / "fraudhunter" / "wide_table_service" / "store" / "checksum.py",
)
checksum = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("checksum_for_test", checksum)
_spec.loader.exec_module(checksum)


def _checksum(conn, relation, columns):
    sql = checksum.build_checksum_sql(relation, columns)
    assert 'concat_ws' not in sql  # 不再依赖字符串拼接
    return conn.execute(sql).fetchone()


class TestChecksumFormula:
    def setup_method(self):
        self.conn = duckdb.connect()
        self.cols = ['c1', 'c2', 'c3']

    def teardown_method(self):
        self.conn.close()

    def test_identical_rows_same_checksum(self):
        a = _checksum(self.conn, "(SELECT 'a' AS c1, 'b' AS c2, 'c' AS c3)", self.cols)
        b = _checksum(self.conn, "(SELECT 'a' AS c1, 'b' AS c2, 'c' AS c3)", self.cols)
        assert a == b

    def test_null_position_distinguished(self):
        """('a', NULL, 'b') 与 ('a', 'b', NULL) 校验和必须不同（旧 concat_ws 下相同）"""
        a = _checksum(self.conn, "(SELECT 'a' AS c1, NULL::VARCHAR AS c2, 'b' AS c3)", self.cols)
        b = _checksum(self.conn, "(SELECT 'a' AS c1, 'b' AS c2, NULL::VARCHAR AS c3)", self.cols)
        assert a[0] == b[0] == 1
        assert a[1] != b[1]

    def test_delimiter_in_value_distinguished(self):
        """('a|b', 'c') 与 ('a', 'b|c') 校验和必须不同（旧拼接下相同）"""
        a = _checksum(self.conn, "(SELECT 'a|b' AS c1, 'c' AS c2, NULL::VARCHAR AS c3)", self.cols)
        b = _checksum(self.conn, "(SELECT 'a' AS c1, 'b|c' AS c2, NULL::VARCHAR AS c3)", self.cols)
        assert a[1] != b[1]

    def test_row_order_irrelevant(self):
        """sum 满足交换律 → 校验和与行顺序无关（顺序无关对账前提）"""
        a = _checksum(
            self.conn,
            "(SELECT * FROM (VALUES ('a', 1), ('b', 2)) t(c1, c2))",
            ['c1', 'c2'])
        b = _checksum(
            self.conn,
            "(SELECT * FROM (VALUES ('b', 2), ('a', 1)) t(c1, c2))",
            ['c1', 'c2'])
        assert a == b

    def test_type_normalization_via_varchar_cast(self):
        """同逻辑值不同物理类型（INTEGER 1 vs VARCHAR '1'）校验和一致（::VARCHAR 归一）"""
        a = _checksum(self.conn, "(SELECT 1 AS c1)", ['c1'])
        b = _checksum(self.conn, "(SELECT '1' AS c1)", ['c1'])
        assert a[1] == b[1]

    def test_empty_columns_rejected(self):
        try:
            checksum.build_checksum_sql('r', [])
            raised = False
        except ValueError:
            raised = True
        assert raised
