"""
指标数据获取工具
用于测试生成式UI图表功能
"""
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List
from langfuse import observe
from utils.logger import logger

@observe(name="get_metrics")
def get_metrics(metric_name: str, date_list: list) -> str:
    """
    批量获取一个指标名称和一系列日期的数据

    Args:
        metric_name: 指标名称，如"用户活跃度"、"销售额"、"转化率"等
        date_list: 日期列表，支持多种格式：
               - ["2025-01-01", "2025-01-02", "2025-01-03"]
               - ["2025-01-01", "2025-02-01", "2025-03-01"]

    Returns:
        包含指标数据的JSON字符串，格式如下：
        {
            "metric_name": "用户活跃度",
            "date_count": 30,
            "date_list": ["2025-01-01", "2025-01-02", ...],
            "generated_at": "2025-11-27 13:30:00",
            "data": [
                {"date": "2025-01-01", "value": 1234},
                {"date": "2025-01-02", "value": 1456},
                ...
            ],
            "metadata": {
                "unit": "人",
                "trend": "上升",
                "average": 1356.7,
                "max": 1890,
                "min": 890
            }
        }
    """
    logger.info(f"开始批量获取{metric_name}指标数据，日期数量: {len(date_list)}")

    try:
        if not date_list or len(date_list) == 0:
            return json.dumps({
                "error": "日期列表不能为空",
                "metric_name": metric_name
            }, ensure_ascii=False)

        # 验证日期格式并标准化
        normalized_dates = []
        for date_item in date_list:
            if isinstance(date_item, str):
                # 如果是字符串，直接使用
                normalized_dates.append(date_item)
            elif isinstance(date_item, (int, float)):
                # 如果是数字，假设是从今天开始的天数
                current_date = datetime.now()
                target_date = current_date - timedelta(days=int(date_item))
                normalized_dates.append(target_date.strftime("%Y-%m-%d"))
            else:
                # 跳过不支持的格式
                logger.warning(f"跳过不支持的日期格式: {date_item}")
                continue

        if not normalized_dates:
            return json.dumps({
                "error": "没有有效的日期数据",
                "metric_name": metric_name,
                "date_list": date_list
            }, ensure_ascii=False)

        # 确定时间范围
        start_date = min([datetime.strptime(date_str, "%Y-%m-%d") for date_str in normalized_dates])
        end_date = max([datetime.strptime(date_str, "%Y-%m-%d") for date_str in normalized_dates])
        total_days = (end_date - start_date).days + 1

        # 为每个日期生成数据点
        data_points_list = []
        for i, date_str in enumerate(normalized_dates):
            # 根据指标名称生成不同类型的随机数据
            if "活跃" in metric_name or "用户" in metric_name:
                # 用户活跃度数据 - 日活跃用户数
                base_value = random.randint(800, 1200)
                # 添加基于日期的随机波动
                random_variation = random.randint(-150, 200)
                value = max(100, int(base_value + random_variation + i * 5))

            elif "销售" in metric_name or "收入" in metric_name or "营收" in metric_name:
                # 销售额数据 - 万元
                base_value = random.randint(50, 200)
                random_variation = random.randint(-20, 30)
                value = round(base_value + random_variation / 10 + i * 2, 2)

            elif "转化" in metric_name or "率" in metric_name:
                # 转化率数据 - 百分比
                base_value = random.uniform(2.5, 8.0)
                random_variation = random.uniform(-0.8, 1.2)
                value = min(15.0, max(0.1, base_value + random_variation + i * 0.1))

            elif "性能" in metric_name or "响应" in metric_name:
                # 性能数据 - 毫秒
                base_value = random.randint(100, 500)
                # 性能优化趋势，随着时间推移有所改善
                improvement_factor = 1 + (i * 0.02)
                random_variation = random.randint(-30, 50)
                value = max(50, int(base_value * improvement_factor + random_variation))

            else:
                # 其他指标 - 随机数值
                base_value = random.randint(1000, 5000)
                # 随时间增长趋势
                growth_factor = 1 + (i * 0.025)
                random_variation = random.randint(-300, 800)
                value = max(100, int(base_value * growth_factor + random_variation))

            data_points_list.append({
                "date": date_str,
                "value": value
            })

        # 计算统计信息
        values = [item["value"] for item in data_points_list]
        max_value = max(values)
        min_value = min(values)
        avg_value = sum(values) / len(values)

        # 判断整体趋势
        if len(values) >= 2:
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]
            first_avg = sum(first_half) / len(first_half) if first_half else 0
            second_avg = sum(second_half) / len(second_half) if second_half else 0
            trend = "上升" if second_avg > first_avg else "下降" if second_avg < first_avg else "稳定"
        else:
            trend = "稳定"

        # 确定单位和描述
        unit_mapping = {
            "活跃": "人", "用户": "人",
            "销售": "万元", "收入": "万元", "营收": "万元",
            "转化": "%", "率": "%",
            "性能": "ms", "响应": "ms",
            "金额": "元", "价格": "元"
        }

        unit = unit_mapping.get(next((k for k in unit_mapping if k in metric_name), "次"))

        result = {
            "metric_name": metric_name,
            "date_count": len(normalized_dates),
            "date_list": normalized_dates,
            "date_range": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "total_days": total_days
            },
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": data_points_list,
            "metadata": {
                "unit": unit,
                "trend": trend,
                "average": round(avg_value, 2),
                "max": max_value,
                "min": min_value,
                "data_points": len(data_points_list)
            }
        }

        logger.info(f"成功批量生成{metric_name}指标数据，共{len(data_points_list)}个数据点，趋势: {trend}")
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.error(f"批量生成{metric_name}指标数据时发生错误: {e}")
        return json.dumps({
            "error": f"批量生成指标数据时发生错误: {str(e)}",
            "metric_name": metric_name,
            "date_list": date_list
        }, ensure_ascii=False)
