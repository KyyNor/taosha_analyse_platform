"""
图表生成工具
提供生成图表数据的工具函数，支持折线图、饼图和柱状图
"""
import json
from typing import Dict, Any, List, Union
from langfuse import observe
from utils.logger import logger


@observe(name="create_chart")
def create_chart(
    chart_type: str,
    data: Union[List[Dict[str, Any]], str],
    title: str = "",
    description: str = "",
    x_key: str = "name",
    y_keys: Union[List[str], str] = "value",
    **kwargs
) -> str:
    """
    创建图表数据，支持折线图、饼图和柱状图

    Args:
        chart_type: 图表类型，支持 'line'（折线图）、'pie'（饼图）、'bar'（柱状图）
        data: 图表数据，可以是字典列表或JSON字符串
        title: 图表标题
        description: 图表描述
        x_key: X轴数据字段名（用于折线图和柱状图）
        y_keys: Y轴数据字段名，可以是单个字段名或字段名列表
        **kwargs: 其他图表参数，如：
            - colors: 颜色列表
            - height: 图表高度
            - show_legend: 是否显示图例
            - show_grid: 是否显示网格（用于折线图和柱状图）
            - stacked: 是否堆叠（仅用于柱状图）
            - orientation: 方向，'vertical' 或 'horizontal'（仅用于柱状图）
            - inner_radius: 内圆半径（用于饼图环形图）
            - outer_radius: 外圆半径（用于饼图）
            - show_percentage: 是否显示百分比（用于饼图）

    Returns:
        包含图表配置和数据的JSON字符串

    Examples:
        # 折线图
        create_chart(
            chart_type="line",
            data=[{"month": "1月", "sales": 100, "profit": 30}, {"month": "2月", "sales": 150, "profit": 50}],
            title="月度销售趋势",
            x_key="month",
            y_keys=["sales", "profit"]
        )

        # 饼图
        create_chart(
            chart_type="pie",
            data=[{"name": "产品A", "value": 30}, {"name": "产品B", "value": 50}],
            title="产品销售占比"
        )

        # 柱状图
        create_chart(
            chart_type="bar",
            data=[{"city": "北京", "population": 2100}, {"city": "上海", "population": 2400}],
            title="城市人口对比",
            x_key="city",
            y_keys="population"
        )
    """
    logger.info(f"开始创建{chart_type}图表: {title}")

    try:
        # 验证图表类型
        supported_types = ["line", "pie", "bar"]
        if chart_type not in supported_types:
            return json.dumps({
                "error": f"不支持的图表类型: {chart_type}",
                "supported_types": supported_types,
                "chart_type": chart_type
            }, ensure_ascii=False)

        # 解析数据
        if isinstance(data, str):
            try:
                parsed_data = json.loads(data)
            except json.JSONDecodeError as e:
                return json.dumps({
                    "error": f"数据JSON格式错误: {str(e)}",
                    "chart_type": chart_type,
                    "title": title
                }, ensure_ascii=False)
        else:
            parsed_data = data

        # 验证数据格式
        if not isinstance(parsed_data, list):
            return json.dumps({
                "error": "数据必须是列表格式",
                "chart_type": chart_type,
                "title": title,
                "data_type": type(parsed_data).__name__
            }, ensure_ascii=False)

        if len(parsed_data) == 0:
            return json.dumps({
                "error": "数据不能为空",
                "chart_type": chart_type,
                "title": title
            }, ensure_ascii=False)

        # 标准化y_keys参数
        if isinstance(y_keys, str):
            y_keys = [y_keys]

        # 数据验证和清洗
        processed_data = []
        for item in parsed_data:
            if not isinstance(item, dict):
                continue

            # 确保必要字段存在
            processed_item = {}

            # 处理x_key
            if x_key in item:
                processed_item[x_key] = item[x_key]
            elif "name" in item:
                processed_item[x_key] = item["name"]
            else:
                # 使用索引作为默认值
                processed_item[x_key] = f"项目{len(processed_data) + 1}"

            # 处理y_keys
            for key in y_keys:
                if key in item:
                    processed_item[key] = item[key]
                elif "value" in item and key == "value":
                    processed_item[key] = item["value"]
                elif len(y_keys) == 1:  # 如果只有一个y_key，尝试使用第一个数值字段
                    for field_name, field_value in item.items():
                        if field_name != x_key and isinstance(field_value, (int, float)):
                            processed_item[key] = field_value
                            break
                    else:
                        processed_item[key] = 0  # 默认值
                else:
                    processed_item[key] = 0  # 默认值

            processed_data.append(processed_item)

        if len(processed_data) == 0:
            return json.dumps({
                "error": "没有有效的数据项",
                "chart_type": chart_type,
                "title": title,
                "original_data_count": len(parsed_data)
            }, ensure_ascii=False)

        # 验证数据类型（特别是饼图需要确保value是数值）
        if chart_type == "pie":
            for i, item in enumerate(processed_data):
                if y_keys[0] in item:
                    try:
                        processed_data[i][y_keys[0]] = float(item[y_keys[0]])
                    except (ValueError, TypeError):
                        processed_data[i][y_keys[0]] = 0

        # 构建图表配置
        chart_config = {
            "chart_type": chart_type,
            "title": title,
            "description": description,
            "data": processed_data,
            "x_key": x_key,
            "y_keys": y_keys
        }

        # 添加可选参数
        optional_params = {
            "colors", "height", "show_legend", "show_grid", "stacked",
            "orientation", "inner_radius", "outer_radius", "show_percentage",
            "start_angle", "end_angle", "label_position", "bar_radius"
        }

        for param in optional_params:
            if param in kwargs:
                chart_config[param] = kwargs[param]

        # 设置默认值
        if "colors" not in chart_config:
            chart_config["colors"] = [
                "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
                "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"
            ]

        if "height" not in chart_config:
            chart_config["height"] = 300

        if "show_legend" not in chart_config:
            chart_config["show_legend"] = True

        if "show_grid" not in chart_config and chart_type in ["line", "bar"]:
            chart_config["show_grid"] = True

        if "stacked" not in chart_config and chart_type == "bar":
            chart_config["stacked"] = False

        if "orientation" not in chart_config and chart_type == "bar":
            chart_config["orientation"] = "vertical"

        if "show_percentage" not in chart_config and chart_type == "pie":
            chart_config["show_percentage"] = True

        # 饼图特殊处理：将数据转换为标准格式
        if chart_type == "pie":
            pie_data = []
            for item in processed_data:
                pie_item = {
                    "name": item.get(x_key, ""),
                    "value": item.get(y_keys[0], 0)
                }
                pie_data.append(pie_item)
            chart_config["data"] = pie_data
            # 移除饼图不需要的参数
            chart_config.pop("x_key", None)
            chart_config.pop("y_keys", None)

        logger.info(f"成功创建{chart_type}图表，包含{len(processed_data)}个数据点")
        return json.dumps(chart_config, ensure_ascii=False)

    except Exception as e:
        logger.error(f"创建图表时发生错误: {e}")
        return json.dumps({
            "error": f"创建图表时发生错误: {str(e)}",
            "chart_type": chart_type,
            "title": title
        }, ensure_ascii=False)
