"""
SQL方言适配层

双存储方案阶段4（docs/fraudhunter_offline_dual_store_plan.md）：
规则引擎生成的WHERE子句按目标执行引擎（PG / DuckDB）适配。

约束：只允许本文件出现方言分支，且仅限以下原语：
- regex_match: PG `expr ~* 'pat'`（不区分大小写正则）↔ DuckDB `regexp_matches(expr, 'pat', 'i')`
- cast_double / cast_date: 两方言均兼容 `::TYPE` 语法（DuckDB 已验证），统一实现
- quote_ident: 双引号包裹，双方言一致

其余表达式一律保持 ANSI（INTERVAL / NULLIF / array_length(x,1) 等已验证双方言可用）。
"""

from typing import Literal

DialectName = Literal['postgresql', 'duckdb']


class SqlDialect:
    """SQL方言基类（ANSI兼容实现）"""

    name: DialectName = 'postgresql'

    def regex_match(self, expr: str, pattern: str, negate: bool = False) -> str:
        raise NotImplementedError

    def cast_double(self, expr: str) -> str:
        return f"{expr}::DOUBLE PRECISION"

    def cast_date(self, expr: str) -> str:
        return f"NULLIF({expr}, '')::DATE"

    def quote_ident(self, name: str) -> str:
        return f'"{name}"'


class PostgreSqlDialect(SqlDialect):
    """PostgreSQL方言（现状默认）"""

    name = 'postgresql'

    def regex_match(self, expr: str, pattern: str, negate: bool = False) -> str:
        if negate:
            return f"not {expr} ~* '{pattern}'"
        return f"{expr} ~* '{pattern}'"


class DuckDbDialect(SqlDialect):
    """DuckDB方言"""

    name = 'duckdb'

    def regex_match(self, expr: str, pattern: str, negate: bool = False) -> str:
        matched = f"regexp_matches({expr}, '{pattern}', 'i')"
        if negate:
            return f"NOT {matched}"
        return matched


_DIALECTS = {
    'postgresql': PostgreSqlDialect(),
    'duckdb': DuckDbDialect(),
}


def get_dialect(name: str = 'postgresql') -> SqlDialect:
    """按名称获取方言实例（未知名称回退 postgresql 并告警）"""
    dialect = _DIALECTS.get((name or 'postgresql').strip().lower())
    if dialect is None:
        from utils.logger import logger
        logger.warning(f"未知SQL方言: {name}，回退 postgresql")
        return _DIALECTS['postgresql']
    return dialect
