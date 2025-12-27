"""
SQL 日期条件验证脚本

测试不同方案对各种 SQL 场景的检测效果
"""

import re
from typing import Optional
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Parenthesis, Token
from sqlparse.tokens import Keyword, DML


# ==================== 方案一：简单字符串检测 ====================

def check_simple(sql: str) -> tuple[bool, str]:
    """
    简单字符串检测：检查 SQL 是否包含日期关键字
    """
    sql_upper = sql.upper()
    has_etl_date = 'ETL_DATE' in sql_upper
    has_cdate = 'CDATE' in sql_upper

    if has_etl_date or has_cdate:
        return True, "包含日期字段"
    return False, "未检测到 ETL_DATE 或 CDATE"


# ==================== 方案二：检测 WHERE 子句中的日期条件 ====================

def check_where_clause(sql: str) -> tuple[bool, str]:
    """
    检测 WHERE 子句中是否包含日期条件
    """
    sql_upper = sql.upper()

    # 查找 WHERE 关键字位置
    where_match = re.search(r'\bWHERE\b', sql_upper)
    if not where_match:
        return False, "没有 WHERE 子句"

    # 获取 WHERE 之后的内容（简化处理，不考虑子查询）
    where_content = sql_upper[where_match.end():]

    # 检查是否有日期条件
    # 匹配: ETL_DATE = 'xxx' 或 ETL_DATE='xxx' 或 CDATE = 'xxx' 等
    date_pattern = r'\b(ETL_DATE|CDATE)\s*[=<>!]'
    if re.search(date_pattern, where_content):
        return True, "WHERE 子句中包含日期条件"

    # 检查 BETWEEN 条件
    between_pattern = r'\b(ETL_DATE|CDATE)\s+BETWEEN\b'
    if re.search(between_pattern, where_content):
        return True, "WHERE 子句中包含日期 BETWEEN 条件"

    # 检查 IN 条件
    in_pattern = r'\b(ETL_DATE|CDATE)\s+IN\s*\('
    if re.search(in_pattern, where_content):
        return True, "WHERE 子句中包含日期 IN 条件"

    return False, "WHERE 子句中未找到日期条件"


# ==================== 方案三：使用 sqlparse 解析 ====================

def extract_table_names(sql: str) -> list[str]:
    """
    使用 sqlparse 提取 SQL 中的表名
    """
    tables = []
    parsed = sqlparse.parse(sql)[0]

    # 简单方法：查找 FROM 和 JOIN 后的标识符
    from_seen = False
    for token in parsed.tokens:
        if token.ttype is Keyword:
            if token.value.upper() in ('FROM', 'JOIN', 'INNER JOIN', 'LEFT JOIN',
                                        'RIGHT JOIN', 'OUTER JOIN', 'LEFT OUTER JOIN'):
                from_seen = True
            elif token.value.upper() in ('WHERE', 'GROUP', 'ORDER', 'LIMIT', 'HAVING'):
                from_seen = False
        elif from_seen:
            if isinstance(token, IdentifierList):
                for identifier in token.get_identifiers():
                    name = identifier.get_real_name()
                    if name:
                        tables.append(name)
            elif isinstance(token, Identifier):
                name = token.get_real_name()
                if name:
                    tables.append(name)
            elif token.ttype is None and str(token).strip():
                # 可能是简单的表名
                name = str(token).strip()
                if name and not name.startswith('('):
                    tables.append(name.split()[0])  # 取第一个词作为表名

    return tables


def check_with_sqlparse(sql: str) -> tuple[bool, list[str], str]:
    """
    使用 sqlparse 解析，提取表名并检测日期条件
    返回: (是否有日期条件, 表名列表, 说明)
    """
    tables = extract_table_names(sql)

    # 检查是否有日期条件（简单字符串检测）
    sql_upper = sql.upper()
    has_date_condition = bool(re.search(r'\b(ETL_DATE|CDATE)\s*[=<>!]', sql_upper) or
                              re.search(r'\b(ETL_DATE|CDATE)\s+BETWEEN\b', sql_upper) or
                              re.search(r'\b(ETL_DATE|CDATE)\s+IN\s*\(', sql_upper))

    if has_date_condition:
        return True, tables, f"检测到日期条件，涉及表: {tables}"
    else:
        return False, tables, f"未检测到日期条件，涉及表: {tables}"


# ==================== 方案四：综合验证（推荐） ====================

# 不需要日期条件的表白名单
DATE_EXEMPT_TABLES = {
    'hxb_dh_data_dim',
    'metadata_tables',
    'metadata_columns',
    # 可以添加更多不需要日期条件的表
}


def validate_sql_comprehensive(
    sql: str,
    table_date_fields: Optional[dict[str, list[str]]] = None
) -> tuple[bool, str]:
    """
    综合验证 SQL 日期条件

    Args:
        sql: SQL 语句
        table_date_fields: 表名 -> 日期字段列表的映射（模拟元数据）
                          如 {'orders': ['etl_date', 'cdate'], 'users': ['etl_date']}

    Returns:
        (是否通过验证, 原因说明)
    """
    # 1. 提取表名
    tables = extract_table_names(sql)
    if not tables:
        # 无法提取表名，保守通过（可能是复杂查询）
        return True, "无法提取表名，跳过验证"

    # 2. 过滤白名单表
    tables_need_date = [t for t in tables if t.lower() not in DATE_EXEMPT_TABLES]
    if not tables_need_date:
        return True, f"所有表都在白名单中: {tables}"

    # 3. 检查这些表是否有日期字段（模拟元数据查询）
    if table_date_fields:
        tables_with_date_field = []
        for t in tables_need_date:
            if t.lower() in table_date_fields or t in table_date_fields:
                tables_with_date_field.append(t)

        if not tables_with_date_field:
            return True, f"表 {tables_need_date} 没有日期字段，跳过验证"
        tables_need_date = tables_with_date_field

    # 4. 检查 SQL 是否包含日期条件
    sql_upper = sql.upper()
    date_patterns = [
        r'\b(ETL_DATE|CDATE)\s*[=<>!]',
        r'\b(ETL_DATE|CDATE)\s+BETWEEN\b',
        r'\b(ETL_DATE|CDATE)\s+IN\s*\(',
        r'\b(ETL_DATE|CDATE)\s+LIKE\b',
    ]

    for pattern in date_patterns:
        if re.search(pattern, sql_upper):
            return True, f"检测到日期条件，涉及表: {tables}"

    # 5. 未检测到日期条件
    return False, f"表 {tables_need_date} 需要 ETL_DATE 或 CDATE 条件"


# ==================== 测试用例 ====================

TEST_CASES = [
    # (SQL, 期望结果, 描述)

    # 简单查询
    ("SELECT * FROM orders", False, "简单查询无条件"),
    ("SELECT * FROM orders WHERE status = 1", False, "有条件但无日期"),
    ("SELECT * FROM orders WHERE ETL_DATE = '2025-01-01'", True, "有日期条件"),
    ("SELECT * FROM orders WHERE etl_date = '2025-01-01' AND status = 1", True, "有日期条件（小写）"),
    ("SELECT * FROM orders WHERE CDATE >= '2025-01-01'", True, "CDATE 条件"),

    # 白名单表
    ("SELECT * FROM hxb_dh_data_dim", True, "白名单表不需要日期"),
    ("SELECT * FROM hxb_dh_data_dim WHERE code = 'abc'", True, "白名单表"),

    # JOIN 查询
    ("SELECT * FROM orders o JOIN users u ON o.user_id = u.id", False, "JOIN 无日期条件"),
    ("SELECT * FROM orders o JOIN users u ON o.user_id = u.id WHERE o.ETL_DATE = '2025-01-01'", True, "JOIN 有日期条件"),

    # 嵌套查询
    ("SELECT * FROM (SELECT * FROM orders) t", False, "子查询无日期"),
    ("SELECT * FROM (SELECT * FROM orders WHERE ETL_DATE = '2025-01-01') t", True, "子查询有日期"),

    # CTE
    ("WITH cte AS (SELECT * FROM orders) SELECT * FROM cte", False, "CTE 无日期"),
    ("WITH cte AS (SELECT * FROM orders WHERE ETL_DATE = '2025-01-01') SELECT * FROM cte", True, "CTE 有日期"),

    # BETWEEN
    ("SELECT * FROM orders WHERE ETL_DATE BETWEEN '2025-01-01' AND '2025-01-31'", True, "BETWEEN 条件"),

    # IN
    ("SELECT * FROM orders WHERE ETL_DATE IN ('2025-01-01', '2025-01-02')", True, "IN 条件"),

    # 复杂查询
    ("""
    SELECT a.*, b.name
    FROM orders a
    LEFT JOIN users b ON a.user_id = b.id
    WHERE a.ETL_DATE = '2025-01-01'
      AND a.status IN (1, 2, 3)
    ORDER BY a.created_at DESC
    LIMIT 100
    """, True, "复杂查询有日期"),

    # 只 SELECT 日期字段（不是条件）
    ("SELECT ETL_DATE, COUNT(*) FROM orders GROUP BY ETL_DATE", False, "SELECT 日期字段但无条件"),
]


def run_tests():
    """运行测试用例"""
    print("=" * 80)
    print("SQL 日期条件验证测试")
    print("=" * 80)

    # 模拟元数据
    mock_table_date_fields = {
        'orders': ['etl_date', 'cdate'],
        'users': ['etl_date'],
        'products': ['etl_date'],
    }

    results = {
        'simple': {'pass': 0, 'fail': 0},
        'where': {'pass': 0, 'fail': 0},
        'sqlparse': {'pass': 0, 'fail': 0},
        'comprehensive': {'pass': 0, 'fail': 0},
    }

    for sql, expected, desc in TEST_CASES:
        sql_display = sql.strip().replace('\n', ' ')[:60]
        print(f"\n测试: {desc}")
        print(f"SQL: {sql_display}...")
        print(f"期望: {'通过' if expected else '需要日期条件'}")
        print("-" * 40)

        # 方案一
        result1, msg1 = check_simple(sql)
        status1 = "✓" if result1 == expected else "✗"
        results['simple']['pass' if result1 == expected else 'fail'] += 1
        print(f"  方案一(简单): {status1} {msg1}")

        # 方案二
        result2, msg2 = check_where_clause(sql)
        status2 = "✓" if result2 == expected else "✗"
        results['where']['pass' if result2 == expected else 'fail'] += 1
        print(f"  方案二(WHERE): {status2} {msg2}")

        # 方案三
        result3, tables, msg3 = check_with_sqlparse(sql)
        status3 = "✓" if result3 == expected else "✗"
        results['sqlparse']['pass' if result3 == expected else 'fail'] += 1
        print(f"  方案三(sqlparse): {status3} {msg3}")

        # 方案四
        result4, msg4 = validate_sql_comprehensive(sql, mock_table_date_fields)
        status4 = "✓" if result4 == expected else "✗"
        results['comprehensive']['pass' if result4 == expected else 'fail'] += 1
        print(f"  方案四(综合): {status4} {msg4}")

    # 汇总
    print("\n" + "=" * 80)
    print("测试汇总")
    print("=" * 80)
    total = len(TEST_CASES)
    for name, stats in results.items():
        rate = stats['pass'] / total * 100
        print(f"  {name:15s}: {stats['pass']}/{total} 通过 ({rate:.1f}%)")

    print("\n结论:")
    best = max(results.items(), key=lambda x: x[1]['pass'])
    print(f"  最佳方案: {best[0]} ({best[1]['pass']}/{total} 通过)")


if __name__ == '__main__':
    run_tests()
