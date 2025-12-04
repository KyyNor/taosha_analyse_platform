"""
双主体对比工具
提供两个主体（如两个支行、两个产品等）的指标对比功能
"""
import json
from typing import Dict, Any, List, Union
from langfuse import observe
from utils.logger import logger


@observe(name="create_comparison")
def create_comparison(
    subject_a_name: str,
    subject_b_name: str,
    metrics: Union[List[Dict[str, Any]], str],
    title: str = "",
    description: str = "",
    **kwargs
) -> str:
    """
    创建双主体对比数据

    Args:
        subject_a_name: 主体A的名称（如"汉口支行"）
        subject_b_name: 主体B的名称（如"武昌支行"）
        metrics: 指标列表，每个指标包含：
            - name: 指标名称
            - value_a: 主体A的值
            - value_b: 主体B的值
            - direction: 指标方向，'higher_is_better' 或 'lower_is_better'
            - unit: 单位（可选）
        title: 对比表标题
        description: 对比表描述
        **kwargs: 其他参数，如：
            - highlight_color: 高亮颜色（默认绿色）
            - decimal_places: 小数位数

    Returns:
        包含对比配置和数据的JSON字符串

    Examples:
        create_comparison(
            subject_a_name="汉口支行",
            subject_b_name="武昌支行",
            metrics=[
                {
                    "name": "存款余额",
                    "value_a": 1000.5,
                    "value_b": 950.3,
                    "direction": "higher_is_better",
                    "unit": "万元"
                },
                {
                    "name": "付息率",
                    "value_a": 2.5,
                    "value_b": 2.3,
                    "direction": "lower_is_better",
                    "unit": "%"
                }
            ],
            title="汉口支行 vs 武昌支行业务对比"
        )
    """
    logger.info(f"开始创建双主体对比: {subject_a_name} vs {subject_b_name}")

    try:
        # 解析指标数据
        if isinstance(metrics, str):
            try:
                parsed_metrics = json.loads(metrics)
            except json.JSONDecodeError as e:
                return json.dumps({
                    "error": f"指标数据JSON格式错误: {str(e)}",
                    "title": title
                }, ensure_ascii=False)
        else:
            parsed_metrics = metrics

        # 验证数据
        if not isinstance(parsed_metrics, list) or len(parsed_metrics) == 0:
            return json.dumps({
                "error": "指标数据必须是非空列表",
                "title": title
            }, ensure_ascii=False)

        # 验证每个指标的必需字段
        processed_metrics = []
        for idx, metric in enumerate(parsed_metrics):
            if not isinstance(metric, dict):
                logger.warning(f"指标 {idx} 不是字典类型，跳过")
                continue

            # 必需字段
            name = metric.get("name", f"指标{idx + 1}")
            value_a = metric.get("value_a")
            value_b = metric.get("value_b")
            direction = metric.get("direction", "higher_is_better")

            # 验证数值
            try:
                value_a = float(value_a) if value_a is not None else 0
                value_b = float(value_b) if value_b is not None else 0
            except (ValueError, TypeError):
                logger.warning(f"指标 '{name}' 的值无法转换为数字，使用0")
                value_a = 0
                value_b = 0

            # 验证方向
            if direction not in ["higher_is_better", "lower_is_better"]:
                logger.warning(f"指标 '{name}' 的方向 '{direction}' 无效，使用默认值 'higher_is_better'")
                direction = "higher_is_better"

            # 判断哪个值更好
            if direction == "higher_is_better":
                better = "a" if value_a > value_b else ("b" if value_b > value_a else "equal")
            else:  # lower_is_better
                better = "a" if value_a < value_b else ("b" if value_b < value_a else "equal")

            # 构建处理后的指标
            processed_metric = {
                "name": name,
                "value_a": value_a,
                "value_b": value_b,
                "direction": direction,
                "better": better,
                "unit": metric.get("unit", ""),
                "description": metric.get("description", "")
            }

            processed_metrics.append(processed_metric)

        if len(processed_metrics) == 0:
            return json.dumps({
                "error": "没有有效的指标数据",
                "title": title
            }, ensure_ascii=False)

        # 构建对比配置
        comparison_config = {
            "type": "comparison_table",
            "title": title or f"{subject_a_name} vs {subject_b_name}",
            "description": description,
            "subject_a": subject_a_name,
            "subject_b": subject_b_name,
            "metrics": processed_metrics
        }

        # 添加可选配置
        if "highlight_color" in kwargs:
            comparison_config["highlight_color"] = kwargs["highlight_color"]
        else:
            comparison_config["highlight_color"] = "#10b981"  # 默认绿色

        if "decimal_places" in kwargs:
            comparison_config["decimal_places"] = kwargs["decimal_places"]
        else:
            comparison_config["decimal_places"] = 2

        logger.info(f"成功创建双主体对比，包含{len(processed_metrics)}个指标")
        return json.dumps(comparison_config, ensure_ascii=False)

    except Exception as e:
        logger.error(f"创建双主体对比时发生错误: {e}")
        return json.dumps({
            "error": f"创建对比时发生错误: {str(e)}",
            "title": title
        }, ensure_ascii=False)
