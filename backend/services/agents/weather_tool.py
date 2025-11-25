"""
天气查询工具
提供基于城市名称的天气查询功能
"""
import httpx
import json
from typing import Dict, Any

from langfuse import observe
from utils.logger import logger


@observe(name="get_weather")
def get_weather(city: str) -> str:
    """
    获取指定城市的天气信息

    Args:
        city: 城市名称，如"北京"、"福州"、"上海"等

    Returns:
        包含天气数据的JSON字符串，包含以下字段：
        - province: 省份名称
        - city: 城市名称
        - adcode: 行政区划代码
        - weather: 天气状况（如"晴"、"多云"、"雨"等）
        - temperature: 当前温度（摄氏度）
        - wind_direction: 风向
        - wind_power: 风力等级
        - humidity: 湿度（百分比）
        - report_time: 数据发布时间
    """
    logger.info(f"开始查询{city}的天气")
    try:
        # 验证城市参数
        if not city or not city.strip():
            return json.dumps({
                "error": "城市名称不能为空",
                "city": city
            }, ensure_ascii=False)

        city = city.strip()

        # 构建请求URL
        url = f"https://uapis.cn/api/v1/misc/weather?city={city}"

        # 发送HTTP请求
        with httpx.Client(timeout=10) as client:
            response = client.get(url)

            if response.status_code != 200:
                return json.dumps({
                    "error": f"获取天气失败: HTTP {response.status_code}",
                    "city": city
                }, ensure_ascii=False)

            data = response.json()

            # 检查API响应状态
            if "error" in data:
                return json.dumps({
                    "error": f"API返回错误: {data.get('error', '未知错误')}",
                    "city": city
                }, ensure_ascii=False)

            # 验证必要字段
            required_fields = ["province", "city", "weather", "temperature"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                return json.dumps({
                    "error": f"API响应缺少必要字段: {', '.join(missing_fields)}",
                    "city": city,
                    "raw_data": data
                }, ensure_ascii=False)

            # 返回结构化数据
            result = {
                "province": data.get("province", ""),
                "city": data.get("city", city),
                "adcode": data.get("adcode", ""),
                "weather": data.get("weather", "未知"),
                "temperature": data.get("temperature", 0),
                "wind_direction": data.get("wind_direction", ""),
                "wind_power": data.get("wind_power", ""),
                "humidity": data.get("humidity", 0),
                "report_time": data.get("report_time", "")
            }

            logger.info(f"成功获取{city}天气: {result['weather']}, {result['temperature']}°C")
            return json.dumps(result, ensure_ascii=False)

    except httpx.TimeoutException:
        logger.error(f"查询{city}天气超时")
        return json.dumps({
            "error": "获取天气超时，请稍后重试",
            "city": city
        }, ensure_ascii=False)
    except httpx.RequestError as e:
        logger.error(f"查询{city}天气网络请求失败: {e}")
        return json.dumps({
            "error": f"网络请求失败: {str(e)}",
            "city": city
        }, ensure_ascii=False)
    except json.JSONDecodeError:
        logger.error(f"查询{city}天气响应数据格式错误")
        return json.dumps({
            "error": "响应数据格式错误",
            "city": city
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"查询{city}天气时发生未知错误: {e}")
        return json.dumps({
            "error": f"查询天气时发生错误: {str(e)}",
            "city": city
        }, ensure_ascii=False)
