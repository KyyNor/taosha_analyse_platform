"""
文档解析服务 - 支持SQL文件和文本解析
"""

import os
import hashlib
from typing import Dict, Optional
from pathlib import Path
import re
from utils.logger import logger


class DocumentParserService:
    """文档解析服务"""

    # 支持的SQL文件扩展名
    SQL_EXTENSIONS = {'.sql', '.SQL'}

    # 最大文件大小（10MB）
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self):
        """初始化文档解析服务"""
        pass

    def parse_from_file(self, file_path: str) -> Dict[str, any]:
        """
        从文件路径解析文档

        Args:
            file_path: 文件路径（绝对路径或相对路径）

        Returns:
            包含解析结果的字典：
            {
                'content': 文件内容,
                'source_type': 源类型 ('sql' 或 'text'),
                'file_size': 文件大小,
                'content_hash': 内容哈希,
                'is_sql': 是否为SQL文件
            }
        """
        try:
            # 转换为绝对路径
            abs_path = os.path.abspath(file_path)

            # 安全检查：验证文件路径
            if not self._is_safe_path(abs_path):
                raise ValueError(f"不安全的文件路径: {file_path}")

            # 检查文件是否存在
            if not os.path.exists(abs_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")

            # 检查是否为文件
            if not os.path.isfile(abs_path):
                raise ValueError(f"路径不是文件: {file_path}")

            # 获取文件大小
            file_size = os.path.getsize(abs_path)

            # 检查文件大小
            if file_size > self.MAX_FILE_SIZE:
                raise ValueError(f"文件过大: {file_size} bytes (最大支持 {self.MAX_FILE_SIZE} bytes)")

            # 判断文件类型
            file_ext = Path(abs_path).suffix
            is_sql = file_ext in self.SQL_EXTENSIONS
            source_type = 'sql' if is_sql else 'text'

            # 读取文件内容
            try:
                # 尝试 UTF-8 编码
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # 尝试其他常见编码
                try:
                    with open(abs_path, 'r', encoding='gbk') as f:
                        content = f.read()
                    logger.warning(f"文件 {abs_path} 使用 GBK 编码读取")
                except Exception:
                    # 最后尝试 latin-1（不会失败）
                    with open(abs_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                    logger.warning(f"文件 {abs_path} 使用 Latin-1 编码读取")

            # 计算内容哈希
            content_hash = self._calculate_hash(content)

            # 如果是SQL文件，提取注释
            if is_sql:
                extracted_content = self._extract_sql_comments(content)
                logger.info(f"SQL文件注释提取完成: {len(extracted_content)} 字符")
            else:
                extracted_content = content

            logger.info(f"成功解析文件: {abs_path}, 大小: {file_size} bytes, 类型: {source_type}")

            return {
                'content': extracted_content,
                'raw_content': content,  # 保留原始内容
                'source_type': source_type,
                'file_size': file_size,
                'content_hash': content_hash,
                'is_sql': is_sql,
                'file_path': abs_path
            }

        except Exception as e:
            logger.error(f"解析文件失败: {file_path}, 错误: {e}")
            raise

    def parse_from_text(self, text_content: str, title: str) -> Dict[str, any]:
        """
        从文本内容解析文档

        Args:
            text_content: 文本内容
            title: 文档标题

        Returns:
            包含解析结果的字典：
            {
                'content': 文本内容,
                'source_type': 'text',
                'file_size': 内容大小,
                'content_hash': 内容哈希,
                'is_sql': False
            }
        """
        try:
            if not text_content or not text_content.strip():
                raise ValueError("文本内容为空")

            # 计算内容大小
            file_size = len(text_content.encode('utf-8'))

            # 计算内容哈希
            content_hash = self._calculate_hash(text_content)

            logger.info(f"成功解析文本: {title}, 大小: {file_size} bytes")

            return {
                'content': text_content,
                'raw_content': text_content,
                'source_type': 'text',
                'file_size': file_size,
                'content_hash': content_hash,
                'is_sql': False,
                'title': title
            }

        except Exception as e:
            logger.error(f"解析文本失败: {title}, 错误: {e}")
            raise

    def _extract_sql_comments(self, sql_content: str) -> str:
        """
        提取SQL注释

        Args:
            sql_content: SQL脚本内容

        Returns:
            提取的注释内容
        """
        try:
            # SQL注释模式：
            # 1. 单行注释: -- 或 #
            # 2. 多行注释: /* */
            # 3. 多行注释: --[[ ]]

            comments = []

            # 提取单行注释（-- 和 #）
            single_line_pattern = r'^(?:--|#)\s*(.+?)$'
            for match in re.finditer(single_line_pattern, sql_content, re.MULTILINE):
                comment = match.group(1).strip()
                if comment:
                    comments.append(comment)

            # 提取多行注释（/* */）
            multi_line_pattern = r'/\*\s*(.*?)\s*\*/'
            for match in re.finditer(multi_line_pattern, sql_content, re.DOTALL):
                comment = match.group(1).strip()
                if comment:
                    # 清理多行注释中的换行
                    comment = re.sub(r'\s+', ' ', comment)
                    comments.append(comment)

            # 提取Lua风格多行注释（--[[ ]]）
            lua_pattern = r'--\[\[\s*(.*?)\s*\]\]'
            for match in re.finditer(lua_pattern, sql_content, re.DOTALL):
                comment = match.group(1).strip()
                if comment:
                    comment = re.sub(r'\s+', ' ', comment)
                    comments.append(comment)

            # 合并所有注释
            if comments:
                extracted = '\n'.join(comments)
                logger.info(f"从SQL中提取了 {len(comments)} 条注释")
                return extracted
            else:
                # 如果没有注释，返回原始SQL内容的前2000个字符
                logger.warning("SQL文件未找到注释，返回部分原始内容")
                return sql_content[:2000] if len(sql_content) > 2000 else sql_content

        except Exception as e:
            logger.error(f"提取SQL注释失败: {e}")
            # 失败时返回原始内容的前2000个字符
            return sql_content[:2000] if len(sql_content) > 2000 else sql_content

    def _calculate_hash(self, content: str) -> str:
        """
        计算内容的MD5哈希

        Args:
            content: 内容字符串

        Returns:
            MD5哈希值（十六进制）
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _is_safe_path(self, file_path: str) -> bool:
        """
        检查文件路径是否安全（防止路径遍历攻击）

        Args:
            file_path: 文件路径

        Returns:
            是否安全
        """
        try:
            # 检查是否包含路径遍历模式
            if '..' in file_path:
                logger.warning(f"文件路径包含路径遍历字符: {file_path}")
                return False

            # 规范化路径
            normalized = os.path.normpath(file_path)

            # 检查是否为绝对路径或在允许的目录下
            # 这里可以根据实际需求添加更严格的检查
            return True

        except Exception as e:
            logger.error(f"检查文件路径安全性失败: {e}")
            return False

    def detect_source_type(self, file_path: Optional[str] = None, content: Optional[str] = None) -> str:
        """
        检测文档源类型

        Args:
            file_path: 文件路径（可选）
            content: 内容（可选）

        Returns:
            源类型：'sql', 'text', 或 'auto'
        """
        if file_path:
            file_ext = Path(file_path).suffix
            if file_ext in self.SQL_EXTENSIONS:
                return 'sql'

        if content:
            # 简单的SQL检测：检查是否包含常见SQL关键字
            sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
            content_upper = content.upper()
            if any(keyword in content_upper for keyword in sql_keywords):
                return 'sql'

        return 'text'
