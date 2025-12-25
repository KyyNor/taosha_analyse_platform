"""
图表生成工具
提供生成图表数据的工具函数，支持折线图、饼图、柱状图和树图
支持生成离线 HTML 图表（使用 Bokeh，不依赖 CDN）
"""
import json
import math
from datetime import datetime
from typing import Dict, Any, List, Union, Optional
from pathlib import Path
from langfuse import observe
from langchain.tools import tool, ToolRuntime
from utils.logger import logger

from services.agents.models.deep_agent_context import DataAnalysisContext

def build_tree_structure(
    data: List[Dict[str, Any]],
    name_key: str = "name",
    value_key: str = "value",
    parent_key: str = "parent"
) -> List[Dict[str, Any]]:
    """
    将扁平的父子关系数据转换为树形结构

    Args:
        data: 扁平数据列表，每个元素包含节点信息和父节点引用
        name_key: 节点名称字段
        value_key: 节点值字段
        parent_key: 父节点名称字段

    Returns:
        树形结构数据列表

    Examples:
        输入:
        [
            {"name": "分行A", "value": 4000, "parent": ""},
            {"name": "支行A1", "value": 2500, "parent": "分行A"},
            {"name": "支行A2", "value": 1500, "parent": "分行A"}
        ]

        输出:
        [
            {
                "name": "分行A",
                "value": 4000,
                "children": [
                    {"name": "支行A1", "value": 2500},
                    {"name": "支行A2", "value": 1500}
                ]
            }
        ]
    """
    # 创建节点映射
    node_map = {}
    root_nodes = []

    # 第一遍：创建所有节点
    for item in data:
        node_name = item.get(name_key, "")
        node = {
            "name": node_name,
            "value": item.get(value_key, 0)
        }
        node_map[node_name] = node

        # 复制其他字段（如果有的话）
        for key, value in item.items():
            if key not in [name_key, value_key, parent_key]:
                node[key] = value

    # 第二遍：建立父子关系
    for item in data:
        node_name = item.get(name_key, "")
        parent_name = item.get(parent_key, "")

        current_node = node_map.get(node_name)
        if not current_node:
            continue

        if not parent_name or parent_name == "":
            # 根节点
            root_nodes.append(current_node)
        else:
            # 子节点，添加到父节点的children中
            parent_node = node_map.get(parent_name)
            if parent_node:
                if "children" not in parent_node:
                    parent_node["children"] = []
                parent_node["children"].append(current_node)
            else:
                # 父节点不存在，当作根节点处理
                logger.warning(f"节点 '{node_name}' 的父节点 '{parent_name}' 不存在，将其作为根节点")
                root_nodes.append(current_node)

    return root_nodes


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
    创建图表数据，支持折线图、饼图、柱状图和树图

    Args:
        chart_type: 图表类型，支持 'line'（折线图）、'pie'（饼图）、'bar'（柱状图）、'treemap'（树图）
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
            - parent_key: 父节点字段名（用于树图）
            - name_key: 节点名称字段名（用于树图）
            - value_key: 节点值字段名（用于树图）

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

        # 树图
        create_chart(
            chart_type="treemap",
            data=[
                {"name": "分行A", "value": 4000, "parent": ""},
                {"name": "支行A1", "value": 2500, "parent": "分行A"},
                {"name": "支行A2", "value": 1500, "parent": "分行A"}
            ],
            title="各机构存款分布",
            name_key="name",
            value_key="value",
            parent_key="parent"
        )
    """
    logger.info(f"开始创建{chart_type}图表: {title}")

    try:
        # 验证图表类型
        supported_types = ["line", "pie", "bar", "treemap"]
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

        # 树图特殊处理：构建层级结构
        elif chart_type == "treemap":
            name_key = kwargs.get("name_key", "name")
            value_key = kwargs.get("value_key", "value")
            parent_key = kwargs.get("parent_key", "parent")

            # 构建树形结构
            treemap_data = build_tree_structure(parsed_data, name_key, value_key, parent_key)
            chart_config["data"] = treemap_data
            chart_config["name_key"] = name_key
            chart_config["value_key"] = value_key
            # 移除树图不需要的参数
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


@observe(name="create_chart_image")
def create_chart_image(
    chart_type: str,
    runtime: ToolRuntime["DataAnalysisContext"],
    data: Union[List[Dict[str, Any]], str],
    title: str = "",
    width: int = 800,
    height: int = 400,
    **kwargs
) -> str:
    """
    使用 Matplotlib 生成图表图片并返回文件路径

    Args:
        chart_type: 图表类型，支持 'line'（折线图）、'pie'（饼图）、'bar'（柱状图）
        data: 图表数据，可以是字典列表或JSON字符串
        title: 图表标题
        width: 图表宽度（像素）
        height: 图表高度（像素）
        **kwargs: 其他图表参数

    Returns:
        图片文件路径

    Examples:
        创建双折线图
        file_path = create_chart_image_matplotlib(
            chart_type="line",
            data=[
                {"name": "Jan", "sales": 100, "profit": 50},
                {"name": "Feb", "sales": 150, "profit": 75},
                {"name": "Mar", "sales": 200, "profit": 100}
            ],
            title="月度销售与利润",
            x_key="name",
            y_keys=["sales", "profit"]
        )
    """
    import matplotlib.pyplot as plt
    import json
    import os
    from pathlib import Path
    from datetime import datetime

    logger.info(f"开始创建{chart_type}图表: {title}")

    output_dir = Path(runtime.context.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chart_image_{timestamp}.png"
    file_path = output_dir / filename

    try:
        # 解析数据
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {e}")
                return ""

        if not isinstance(data, list):
            logger.error("数据必须是列表格式")
            return ""

        # 设置图表尺寸
        plt.figure(figsize=(width/100, height/100))

        if chart_type == "line":
            return _create_line_plot(data, title, width, height, filename, file_path, **kwargs)
        elif chart_type == "bar":
            return _create_bar_plot(data, title, width, height, filename, file_path, **kwargs)
        elif chart_type == "pie":
            return _create_pie_chart(data, title, width, height, filename, file_path, **kwargs)
        else:
            logger.error(f"不支持的图表类型: {chart_type}")
            return ""

    except Exception as e:
        logger.error(f"创建图表时发生错误: {e}")
        return ""

def _create_line_plot(data: List[Dict], title: str, width: int, height: int, filename: str, file_path: Path, **kwargs):
    """使用 Matplotlib 创建折线图"""
    import matplotlib.pyplot as plt

    x_key = kwargs.get("x_key", "name")
    y_keys = kwargs.get("y_keys", ["value"])
    colors = kwargs.get("colors", None)
    show_legend = kwargs.get("show_legend", True)
    show_grid = kwargs.get("show_grid", True)

    # 准备数据
    x_values = [item.get(x_key, "") for item in data]
    
    # 创建图表
    plt.figure(figsize=(width/100, height/100))
    
    for i, y_key in enumerate(y_keys):
        y_values = [item.get(y_key, 0) for item in data]
        
        color = None
        if colors and i < len(colors):
            color = colors[i]
            
        plt.plot(x_values, y_values, 
                label=y_key,
                color=color,
                marker='o',
                linewidth=2)
    
    # 设置标题
    plt.title(title)
    
    # 设置坐标轴旋转
    plt.xticks(rotation=45)
    
    # 设置网格
    if show_grid:
        plt.grid(True, linestyle='--', alpha=0.7)
    
    # 设置图例
    if show_legend and len(y_keys) > 0:
        plt.legend()
    
    # 保存图表
    return _save_image_chart(title, "line", width, height, filename, file_path)

def _create_bar_plot(data: List[Dict], title: str, width: int, height: int, filename: str, file_path: Path, **kwargs):
    """使用 Matplotlib 创建柱状图"""
    import matplotlib.pyplot as plt
    
    x_key = kwargs.get("x_key", "name")
    y_keys = kwargs.get("y_keys", ["value"])
    colors = kwargs.get("colors", None)
    stacked = kwargs.get("stacked", False)
    orientation = kwargs.get("orientation", "vertical")
    show_legend = kwargs.get("show_legend", True)
    show_grid = kwargs.get("show_grid", True)

    # 准备数据
    x_values = [item.get(x_key, "") for item in data]
    
    # 创建图表
    plt.figure(figsize=(width/100, height/100))
    
    if orientation == "vertical":
        # 垂直柱状图
        bar_width = 0.8
        x_positions = range(len(x_values))
        
        if stacked:
            # 堆叠柱状图
            bottom = [0] * len(data)
            for i, y_key in enumerate(y_keys):
                y_values = [item.get(y_key, 0) for item in data]
                color = colors[i] if colors and i < len(colors) else None
                plt.bar(x_positions, y_values, label=y_key, 
                       bottom=bottom, width=bar_width, color=color)
                bottom = [b + v for b, v in zip(bottom, y_values)]
        else:
            # 分组柱状图
            bar_width = 0.8 / len(y_keys)
            for i, y_key in enumerate(y_keys):
                y_values = [item.get(y_key, 0) for item in data]
                offset = (i - len(y_keys) / 2 + 0.5) * bar_width
                x_pos = [x + offset for x in x_positions]
                color = colors[i] if colors and i < len(colors) else None
                plt.bar(x_pos, y_values, label=y_key, 
                       width=bar_width * 0.9, color=color)
        
        plt.xticks(x_positions, x_values)
        plt.xticks(rotation=45)
    else:
        # 水平柱状图
        for i, y_key in enumerate(y_keys):
            y_values = [item.get(y_key, 0) for item in data]
            color = colors[i] if colors and i < len(colors) else None
            plt.barh(x_values, y_values, label=y_key, color=color)
    
    # 设置标题
    plt.title(title)
    
    # 设置网格
    if show_grid:
        plt.grid(True, linestyle='--', alpha=0.7)
    
    # 设置图例
    if show_legend and len(y_keys) > 0:
        plt.legend()
    
    # 保存图表
    return _save_image_chart(title, "bar", width, height, filename, file_path)

def _create_pie_chart(data: List[Dict], title: str, width: int, height: int, filename: str, file_path: Path, **kwargs):
    """使用 Matplotlib 创建饼图"""
    import matplotlib.pyplot as plt
    
    colors = kwargs.get("colors", None)
    show_legend = kwargs.get("show_legend", True)
    show_percentage = kwargs.get("show_percentage", True)
    
    # 准备数据
    labels = [item.get("name", f"Item {i+1}") for i, item in enumerate(data)]
    sizes = [item.get("value", 0) for item in data]
    
    # 自动计算百分比
    if show_percentage:
        def make_autopct(values):
            def my_autopct(pct):
                total = sum(values)
                val = int(round(pct*total/100.0))
                return '{p:.1f}%  ({v:d})'.format(p=pct,v=val)
            return my_autopct
        autopct = make_autopct(sizes)
    else:
        autopct = '%1.1f%%'
    
    # 创建图表
    plt.figure(figsize=(width/100, height/100))
    
    # 绘制饼图
    plt.pie(sizes, 
            labels=labels,
            colors=colors[:len(data)] if colors else None,
            autopct=autopct,
            startangle=90)
    
    # 设置标题
    plt.title(title)
    
    # 设置相等的比例
    plt.axis('equal')
    
    # 设置图例
    if show_legend:
        plt.legend(labels=labels, loc='center left', bbox_to_anchor=(1, 0.5))
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    return _save_image_chart(title, "pie", width, height, filename, file_path)

def _save_image_chart(title: str, chart_type: str, width: int, height: int, filename: str, file_path: Path) -> str:
    """保存 Matplotlib 图表并返回文件路径"""
    import matplotlib.pyplot as plt
    
    # 保存图表
    plt.savefig(file_path, dpi=100, bbox_inches='tight')
    plt.close()  # 关闭图表以释放内存
    
    return str("/analysis/" + filename)

