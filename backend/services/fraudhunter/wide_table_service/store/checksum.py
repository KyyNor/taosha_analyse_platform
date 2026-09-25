"""对账 checksum SQL 构造（同步对账 / 双写对账共用）

公式: SELECT count(*), sum(hash(c1::VARCHAR, c2::VARCHAR, ...)) FROM <relation>

设计要点（PR#12 评论#3，替代早期 concat_ws('|', ...) 拼接）:
- DuckDB 变参 hash 按值结构组合: NULL 参与哈希（concat_ws 会跳过 NULL,
  ('a', NULL, 'b') 与 ('a', 'b', NULL) 拼接结果相同造成假阳性）;
  字段边界天然区分（值本身含 '|' 时拼接会跨界碰撞）;
- 各列统一 ::VARCHAR 归一化 Parquet 与 postgres 扫描两侧的类型差异
  （同一逻辑值不同物理类型 hash 不同）;
- sum 满足交换律 → 顺序无关; 两侧关系均在 DuckDB 内执行, 无跨方言问题。
"""

from typing import Iterable


def build_checksum_sql(relation: str, columns: Iterable[str]) -> str:
    """构建行数 + 顺序无关内容校验和 SQL（sum(hash(结构化列值))）"""
    cols = list(columns)
    if not cols:
        raise ValueError("checksum 需要至少一列")
    joined = ", ".join(f"{col}::VARCHAR" for col in cols)
    return f"SELECT count(*), sum(hash({joined})) FROM {relation}"
