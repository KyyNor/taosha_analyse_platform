"""
SQL验证服务
"""

import re
from typing import Dict, List
import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword
from utils.logger import logger


class SQLValidator:
    """SQL验证服务"""

    REQUIRED_FIELDS = {
        'account_id': 'STRING',
        'indicator_code': 'STRING',
        'indicator_value': 'STRING',
        'dt': 'STRING'
    }

    FORBIDDEN_KEYWORDS = [
        'DROP', 'TRUNCATE', 'DELETE', 'INSERT', 'UPDATE',
        'CREATE', 'ALTER', 'GRANT', 'REVOKE'
    ]

    def validate_sql(self, sql: str) -> Dict:
        """验证SQL语法和规范

        Args:
            sql: SQL语句

        Returns:
            验证结果字典，包含valid、errors、warnings、extracted_fields、extracted_tables
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'extracted_fields': [],
            'extracted_tables': []
        }

        try:
            # 1. 基本格式验证
            if not sql or not sql.strip():
                result['valid'] = False
                result['errors'].append("SQL不能为空")
                return result

            # 2. 禁止危险操作
            sql_upper = sql.upper()
            for keyword in self.FORBIDDEN_KEYWORDS:
                if re.search(rf'\b{keyword}\b', sql_upper):
                    result['valid'] = False
                    result['errors'].append(f"禁止使用 {keyword} 操作")

            # 3. 解析SQL
            parsed = sqlparse.parse(sql)
            if not parsed:
                result['valid'] = False
                result['errors'].append("SQL解析失败")
                return result

            statement = parsed[0]

            # 4. 必须是SELECT语句
            if statement.get_type() != 'SELECT':
                result['valid'] = False
                result['errors'].append("只支持SELECT查询")
                return result

            # 5. 提取字段和表名
            result['extracted_fields'] = self._extract_fields(statement)
            result['extracted_tables'] = self._extract_tables(statement)

            # 6. 验证必需字段
            missing_fields = []
            for field in self.REQUIRED_FIELDS.keys():
                if field not in result['extracted_fields']:
                    missing_fields.append(field)

            if missing_fields:
                result['valid'] = False
                result['errors'].append(
                    f"缺少必需字段: {', '.join(missing_fields)}"
                )

            # 7. 警告检查
            if 'SELECT *' in sql_upper:
                result['warnings'].append("建议明确指定字段而不是使用 SELECT *")

            logger.debug(f"SQL验证结果: {result}")

        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"SQL验证异常: {str(e)}")
            logger.error(f"SQL验证异常: {e}", exc_info=True)

        return result

    def _extract_fields(self, statement) -> List[str]:
        """提取SELECT字段

        Args:
            statement: sqlparse解析后的Statement对象

        Returns:
            字段名列表
        """
        fields = []
        for token in statement.tokens:
            if isinstance(token, IdentifierList):
                for identifier in token.get_identifiers():
                    field_name = str(identifier).split()[-1]
                    fields.append(field_name.lower())
            elif isinstance(token, Identifier):
                field_name = str(token).split()[-1]
                fields.append(field_name.lower())
        return fields

    def _extract_tables(self, statement) -> List[str]:
        """提取表名

        Args:
            statement: sqlparse解析后的Statement对象

        Returns:
            表名列表
        """
        tables = []
        from_seen = False
        for token in statement.tokens:
            if from_seen:
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        tables.append(str(identifier).split()[0])
                elif isinstance(token, Identifier):
                    tables.append(str(token).split()[0])
                elif token.ttype is Keyword:
                    break
            elif token.ttype is Keyword and token.value.upper() == 'FROM':
                from_seen = True
        return tables
