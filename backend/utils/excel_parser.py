"""
Excel文件解析工具
用于解析FineReport下载的Excel文件并转换为结构化数据
"""
import os
import pandas as pd
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger


def parse_excel_file(file_path: str) -> Dict[str, Any]:
    """
    解析Excel文件为结构化数据

    Args:
        file_path: Excel文件路径

    Returns:
        包含解析后数据的字典
    """
    logger.info(f"开始解析Excel文件: {file_path}")

    if not os.path.exists(file_path):
        logger.error(f"Excel文件不存在: {file_path}")
        raise FileNotFoundError(f"Excel文件不存在: {file_path}")

    try:
        # 获取文件信息
        file_stat = os.stat(file_path)
        file_size_mb = file_stat.st_size / (1024 * 1024)

        if file_size_mb > 50:  # 50MB限制
            logger.error(f"文件过大: {file_size_mb:.2f}MB，超过50MB限制")
            raise ValueError(f"文件过大: {file_size_mb:.2f}MB")

        # 读取Excel文件
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        logger.info(f"Excel文件包含 {len(sheet_names)} 个工作表: {sheet_names}")

        result = {
            "success": True,
            "data": {
                "file_name": os.path.basename(file_path),
                "file_size_mb": round(file_size_mb, 2),
                "sheet_count": len(sheet_names),
                "sheets": {}
            },
            "metadata": {
                "file_path": file_path,
                "processing_time": None
            }
        }

        # 解析每个工作表
        for sheet_name in sheet_names:
            logger.debug(f"解析工作表: {sheet_name}")
            sheet_data = _parse_sheet(excel_file, sheet_name)
            result["data"]["sheets"][sheet_name] = sheet_data

        logger.info(f"Excel文件解析完成: {len(sheet_names)} 个工作表")
        return result

    except Exception as e:
        logger.error(f"解析Excel文件失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


def _parse_sheet(excel_file: pd.ExcelFile, sheet_name: str) -> Dict[str, Any]:
    """
    解析单个工作表

    Args:
        excel_file: pd.ExcelFile对象
        sheet_name: 工作表名称

    Returns:
        工作表数据字典
    """
    try:
        # 读取工作表数据
        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        # 处理空值
        df = df.fillna("")

        # 获取数据
        data = df.values.tolist()

        # 尝试识别表头
        headers = None
        if len(data) > 0:
            # 第一行作为表头
            headers = [str(cell) for cell in data[0]]
            # 如果有数据行，去掉表头行
            if len(data) > 1:
                data = data[1:]

        # 推断数据类型
        data_types = {}
        if headers and len(headers) > 0:
            for i, header in enumerate(headers):
                if i < len(df.columns):
                    data_types[header] = _infer_column_type(df.iloc[:, i])

        return {
            "row_count": len(data),
            "col_count": len(headers) if headers else 0,
            "headers": headers or [],
            "data": data,
            "data_types": data_types,
            "has_header": headers is not None
        }

    except Exception as e:
        logger.error(f"解析工作表 {sheet_name} 失败: {e}")
        return {
            "row_count": 0,
            "col_count": 0,
            "headers": [],
            "data": [],
            "data_types": {},
            "error": str(e)
        }


def _infer_column_type(series: pd.Series) -> str:
    """
    推断列的数据类型

    Args:
        series: pandas Series对象

    Returns:
        数据类型字符串
    """
    try:
        # 尝试转换为数值类型
        pd.to_numeric(series, errors='ignore')
        if pd.api.types.is_numeric_dtype(series):
            return "number"

        # 尝试转换为日期类型
        pd.to_datetime(series, errors='ignore')
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"

        # 默认为字符串类型
        return "string"

    except:
        return "string"


def clean_excel_file(file_path: str) -> bool:
    """
    清理Excel文件

    Args:
        file_path: 文件路径

    Returns:
        是否删除成功
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"已删除Excel文件: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"删除Excel文件失败 {file_path}: {e}")
        return False


def ensure_download_dir(download_path: str) -> bool:
    """
    确保下载目录存在

    Args:
        download_path: 下载目录路径

    Returns:
        目录是否存在或创建成功
    """
    try:
        Path(download_path).mkdir(parents=True, exist_ok=True)
        logger.debug(f"下载目录已准备: {download_path}")
        return True
    except Exception as e:
        logger.error(f"创建下载目录失败 {download_path}: {e}")
        return False