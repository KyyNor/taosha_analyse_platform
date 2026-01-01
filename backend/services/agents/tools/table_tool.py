"""
表格生成工具
提供生成表格数据的工具函数，支持通用数据表格展示
支持自定义列配置、排序、分页等功能
"""
import json
from typing import Dict, Any, List, Union, Optional
from langfuse import observe
from utils.logger import logger


@observe(name="create_table")
def create_table(
    data: Union[List[Dict[str, Any]], str],
    title: str = "",
    description: str = "",
    columns: Optional[List[Dict[str, Any]]] = None,
    sortable: bool = True,
    paginated: bool = False,
    page_size: int = 10,
    stripe: bool = True,
    bordered: bool = True,
    compact: bool = False,
    **kwargs
) -> str:
    """
    创建表格数据，支持通用数据表格展示

    Args:
        data: 表格数据，可以是字典列表或JSON字符串
        title: 表格标题
        description: 表格描述
        columns: 列配置列表，每个配置包含：
            - key: 字段键名
            - label: 列标题
            - type: 数据类型 (text/number/percentage/currency/date/boolean)
            - format: 格式化字符串（可选）
            - width: 列宽度（可选，如 '100px' 或 '10%'）
            - align: 对齐方式 (left/center/right)
            - sortable: 是否可排序（默认继承全局设置）
        sortable: 是否支持列排序
        paginated: 是否支持分页
        page_size: 每页显示条数
        stripe: 是否显示斑马纹
        bordered: 是否显示边框
        compact: 是否紧凑模式
        **kwargs: 其他表格参数，如：
            - highlight_column: 高亮列名
            - highlight_color: 高亮颜色
            - max_rows: 最大显示行数（不分页时）
            - show_index: 是否显示序号列
            - index_label: 序号列标题（默认"序号"）

    Returns:
        包含表格配置和数据的JSON字符串

    Examples:
        # 简单表格
        create_table(
            data=[
                {"name": "张三", "age": 25, "city": "北京"},
                {"name": "李四", "age": 30, "city": "上海"}
            ],
            title="用户列表"
        )

        # 带列配置的表格
        create_table(
            data=[
                {"product": "产品A", "sales": 10000, "rate": 0.25, "date": "2024-01-01"},
                {"product": "产品B", "sales": 15000, "rate": 0.35, "date": "2024-01-02"}
            ],
            title="销售数据",
            columns=[
                {"key": "product", "label": "产品名称", "type": "text", "width": "200px"},
                {"key": "sales", "label": "销售额", "type": "currency", "format": "¥{:.2f}"},
                {"key": "rate", "label": "占比", "type": "percentage", "format": "{:.2%}"},
                {"key": "date", "label": "日期", "type": "date"}
            ],
            sortable=True,
            stripe=True
        )
    """
    logger.info(f"开始创建表格: {title}")

    try:
        # 解析数据
        if isinstance(data, str):
            try:
                parsed_data = json.loads(data)
            except json.JSONDecodeError as e:
                return json.dumps({
                    "error": f"数据JSON格式错误: {str(e)}",
                    "title": title
                }, ensure_ascii=False)
        else:
            parsed_data = data

        # 验证数据格式
        if not isinstance(parsed_data, list):
            return json.dumps({
                "error": "数据必须是列表格式",
                "title": title,
                "data_type": type(parsed_data).__name__
            }, ensure_ascii=False)

        if len(parsed_data) == 0:
            return json.dumps({
                "error": "数据不能为空",
                "title": title
            }, ensure_ascii=False)

        # 自动推断列配置
        if columns is None:
            columns = _infer_columns(parsed_data)

        # 验证列配置
        valid_columns = []
        for col in columns:
            if not isinstance(col, dict) or "key" not in col:
                continue
            valid_columns.append(col)

        if len(valid_columns) == 0:
            return json.dumps({
                "error": "无效的列配置",
                "title": title,
                "columns": columns
            }, ensure_ascii=False)

        # 数据清洗和验证
        processed_data = []
        for item in parsed_data:
            if not isinstance(item, dict):
                continue

            processed_item = {}
            for col in valid_columns:
                key = col["key"]
                if key in item:
                    processed_item[key] = item[key]
                else:
                    processed_item[key] = None
            processed_data.append(processed_item)

        if len(processed_data) == 0:
            return json.dumps({
                "error": "没有有效的数据项",
                "title": title,
                "original_data_count": len(parsed_data)
            }, ensure_ascii=False)

        # 构建表格配置
        table_config = {
            "type": "table",
            "title": title,
            "description": description,
            "data": processed_data,
            "columns": valid_columns,
            "sortable": sortable,
            "paginated": paginated,
            "page_size": page_size,
            "stripe": stripe,
            "bordered": bordered,
            "compact": compact
        }

        # 添加可选参数
        optional_params = {
            "highlight_column", "highlight_color", "max_rows",
            "show_index", "index_label", "row_class_name", "cell_class_name"
        }

        for param in optional_params:
            if param in kwargs:
                table_config[param] = kwargs[param]

        # 设置默认值
        if "show_index" not in table_config:
            table_config["show_index"] = False

        if "index_label" not in table_config:
            table_config["index_label"] = "序号"

        if "max_rows" not in table_config and not paginated:
            table_config["max_rows"] = 50  # 默认最多显示50行

        logger.info(f"成功创建表格，包含{len(processed_data)}行数据，{len(valid_columns)}列")
        return json.dumps(table_config, ensure_ascii=False)

    except Exception as e:
        logger.error(f"创建表格时发生错误: {e}")
        return json.dumps({
            "error": f"创建表格时发生错误: {str(e)}",
            "title": title
        }, ensure_ascii=False)


def _infer_columns(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    自动推断列配置

    Args:
        data: 数据列表

    Returns:
        列配置列表
    """
    if not data or len(data) == 0:
        return []

    # 收集所有可能的字段
    all_keys = set()
    for item in data[:10]:  # 只检查前10行
        if isinstance(item, dict):
            all_keys.update(item.keys())

    columns = []
    for key in sorted(all_keys):
        # 推断数据类型
        col_type = "text"
        sample_values = []
        for item in data[:20]:
            if key in item and item[key] is not None:
                sample_values.append(item[key])
                if len(sample_values) >= 5:
                    break

        if sample_values:
            # 尝试推断类型
            first_val = sample_values[0]

            if isinstance(first_val, bool):
                col_type = "boolean"
            elif isinstance(first_val, (int, float)):
                # 检查是否是百分比（0-1之间的小数）
                if all(0 <= v <= 1 for v in sample_values if isinstance(v, (int, float))):
                    col_type = "percentage"
                else:
                    col_type = "number"
            elif isinstance(first_val, str):
                # 检查是否是日期
                if any(k in key.lower() for k in ["date", "time", "日期", "时间"]):
                    col_type = "date"
                # 检查是否是货币
                elif any(k in key.lower() for k in ["price", "amount", "cost", "sales", "金额", "价格", "销售额"]):
                    col_type = "currency"
                else:
                    col_type = "text"

        # 生成列标题
        label = key.replace("_", " ").replace("-", " ").title()
        label = label.replace("Id", "ID").replace("Url", "URL")

        columns.append({
            "key": key,
            "label": label,
            "type": col_type,
            "sortable": True,
            "align": "left" if col_type == "text" else "right"
        })

    return columns


# 导出工具函数
__all__ = ["create_table"]
