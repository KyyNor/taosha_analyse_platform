"""
SQL验证服务
"""

import re
from typing import Dict
from utils.logger import logger


class SQLValidator:
    """SQL验证服务"""

    FORBIDDEN_KEYWORDS = [
        'DROP', 'TRUNCATE', 'DELETE', 'INSERT', 'UPDATE',
        'CREATE', 'ALTER', 'GRANT', 'REVOKE'
    ]

    def validate_sql(self, sql: str) -> Dict:
        """验证SQL语法和规范

        Args:
            sql: SQL语句

        Returns:
            验证结果字典，包含valid和errors
        """
        result = {
            'valid': True,
            'errors': []
        }

        try:
            # 基本格式验证
            if not sql or not sql.strip():
                result['valid'] = False
                result['errors'].append("SQL不能为空")
                return result

            # 禁止危险操作
            sql_upper = sql.upper()
            for keyword in self.FORBIDDEN_KEYWORDS:
                if re.search(rf'\b{keyword}\b', sql_upper):
                    result['valid'] = False
                    result['errors'].append(f"禁止使用 {keyword} 操作")

            logger.debug(f"SQL验证结果: {result}")

        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"SQL验证异常: {str(e)}")
            logger.error(f"SQL验证异常: {e}", exc_info=True)

        return result
