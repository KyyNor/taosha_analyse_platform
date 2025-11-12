"""
Agent工具集合
包含热榜获取和程序员小故事等工具函数
"""
import httpx
from typing import Dict, Any, List
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from langfuse import observe
from utils.logger import logger


@observe(name="get_hotboard")
def get_hotboard(platform: str) -> str:
    """
    获取各大平台的热门榜单，支持bilibili、weibo、zhihu、douyin、v2ex、ithome平台

    Args:
        platform: 平台类型名称

    Returns:
        包含热榜数据的JSON字符串
    """
    logger.info(f"开始获取{platform}热榜")
    try:
        # 验证平台参数
        supported_platforms = ["bilibili", "weibo", "zhihu", "douyin", "v2ex", "ithome"]
        if platform not in supported_platforms:
            return json.dumps({
                "error": f"不支持的平台: {platform}",
                "supported_platforms": supported_platforms
            }, ensure_ascii=False)

        # 构建请求URL
        url = f"https://uapis.cn/api/v1/misc/hotboard?type={platform}"

        # 发送HTTP请求
        with httpx.Client(timeout=10) as client:
            response = client.get(url)
            if response.status_code != 200:
                return json.dumps({
                    "error": f"获取热榜失败: HTTP {response.status_code}",
                    "platform": platform
                }, ensure_ascii=False)

            data = response.json()

            # 提取核心数据
            items = data.get("list", [])
            platform_names = {
                "bilibili": "B站", "weibo": "微博", "zhihu": "知乎",
                "douyin": "抖音", "v2ex": "V2EX", "ithome": "IT之家"
            }
            platform_name = platform_names.get(platform, platform.upper())

            # 返回结构化数据
            result = {
                "platform": platform,
                "platform_name": platform_name,
                "total": len(items),
                "items": items[:20]  # 限制前20条，避免数据过多
            }

            logger.info(f"成功获取{platform_name}热榜，共{len(items)}条")
            return json.dumps(result, ensure_ascii=False)

    except httpx.TimeoutException:
        return json.dumps({"error": "获取热榜超时"}, ensure_ascii=False)
    except httpx.RequestError as e:
        return json.dumps({"error": f"网络请求失败: {str(e)}"}, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({"error": "响应数据格式错误"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取热榜时发生错误: {e}")
        return json.dumps({"error": f"获取热榜时发生错误: {str(e)}"}, ensure_ascii=False)


@observe(name="get_programmer_story")
def get_programmer_story() -> str:
    """
    获取程序员历史上的今天小故事

    Returns:
        包含程序员故事数据的JSON字符串
    """
    logger.info("开始获取程序员小故事")
    try:
        # 发送HTTP请求
        with httpx.Client(timeout=10) as client:
            response = client.get("https://uapis.cn/api/v1/history/programmer/today")
            if response.status_code != 200:
                return json.dumps({
                    "error": f"获取程序员小故事失败: HTTP {response.status_code}"
                }, ensure_ascii=False)

            data = response.json()

            # 检查API响应状态
            if data.get("code") != 200:
                return json.dumps({
                    "error": f"API返回错误: {data.get('message', '未知错误')}"
                }, ensure_ascii=False)

            # 提取故事数据
            events = data.get("events", [])
            if not events:
                return json.dumps({"error": "今日暂无程序员小故事"}, ensure_ascii=False)

            # 获取主要故事（第一个事件）
            story_data = events[0]

            # 返回结构化数据
            result = {
                "date": data.get("date", ""),
                "year": story_data.get("year", ""),
                "title": story_data.get("title", ""),
                "description": story_data.get("description", ""),
                "category": story_data.get("category", ""),
                "tags": story_data.get("tags", []),
                "importance": story_data.get("importance", 0)
            }

            logger.info(f"成功获取程序员小故事: {result.get('title', '无标题')}")
            return json.dumps(result, ensure_ascii=False)

    except httpx.TimeoutException:
        return json.dumps({"error": "获取程序员小故事超时"}, ensure_ascii=False)
    except httpx.RequestError as e:
        return json.dumps({"error": f"网络请求失败: {str(e)}"}, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({"error": "响应数据格式错误"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取程序员小故事时发生错误: {e}")
        return json.dumps({"error": f"获取程序员小故事时发生错误: {str(e)}"}, ensure_ascii=False)


@observe(name="get_date_range")
def get_date_range(range_type: str) -> str:
    """
    获取指定时间范围的日期列表

    Args:
        range_type: 时间范围类型，支持：
                   - "近半年"：返回最近6个月的月末日期
                   - "近一年"：返回最近12个月的月末日期
                   - "本季度"：返回当前季度的月末日期
                   - "近一个季度"：返回上个季度的月末日期
                   - "近一周"：返回最近7天的所有日期
                   - "近两周"：返回最近14天的所有日期
                   - "近一月"：返回最近30天的采样日期

    Returns:
        包含日期列表的JSON字符串
    """
    logger.info(f"开始获取时间范围: {range_type}")
    try:
        today = datetime.now()
        dates = []

        if range_type == "近半年":
            # 返回最近6个月的月末日期
            for i in range(6):
                date = today - relativedelta(months=i+1)
                # 获取该月的最后一天
                month_end = date.replace(day=1) + relativedelta(months=1) - timedelta(days=1)
                dates.append(month_end.strftime("%Y-%m-%d"))
            dates.reverse()  # 按时间正序排列

        elif range_type == "近一年":
            # 返回最近12个月的月末日期
            for i in range(12):
                date = today - relativedelta(months=i+1)
                # 获取该月的最后一天
                month_end = date.replace(day=1) + relativedelta(months=1) - timedelta(days=1)
                dates.append(month_end.strftime("%Y-%m-%d"))
            dates.reverse()  # 按时间正序排列

        elif range_type == "本季度":
            # 返回当前季度的月末日期
            current_month = today.month
            if current_month <= 3:
                # Q1: 1-3月，返回3月末
                quarter_end = today.replace(month=3, day=31)
            elif current_month <= 6:
                # Q2: 4-6月，返回6月末
                quarter_end = today.replace(month=6, day=30)
            elif current_month <= 9:
                # Q3: 7-9月，返回9月末
                quarter_end = today.replace(month=9, day=30)
            else:
                # Q4: 10-12月，返回12月末
                quarter_end = today.replace(month=12, day=31)

            dates.append(quarter_end.strftime("%Y-%m-%d"))

        elif range_type == "近一个季度":
            # 返回上个季度的月末日期
            current_month = today.month
            if current_month <= 3:
                # 当前Q1，上个季度是去年Q4
                quarter_end = today.replace(year=today.year-1, month=12, day=31)
            elif current_month <= 6:
                # 当前Q2，上个季度是Q1
                quarter_end = today.replace(month=3, day=31)
            elif current_month <= 9:
                # 当前Q3，上个季度是Q2
                quarter_end = today.replace(month=6, day=30)
            else:
                # 当前Q4，上个季度是Q3
                quarter_end = today.replace(month=9, day=30)

            dates.append(quarter_end.strftime("%Y-%m-%d"))

        elif range_type == "近一周":
            # 返回最近7天的所有日期
            for i in range(7):
                date = today - timedelta(days=i)
                dates.append(date.strftime("%Y-%m-%d"))
            dates.reverse()  # 按时间正序排列

        elif range_type == "近两周":
            # 返回最近14天的所有日期
            for i in range(14):
                date = today - timedelta(days=i)
                dates.append(date.strftime("%Y-%m-%d"))
            dates.reverse()  # 按时间正序排列

        elif range_type == "近一月":
            # 返回最近30天，采样10个日期
            days_count = 30
            sample_count = 10
            interval = days_count // sample_count

            for i in range(sample_count):
                date = today - timedelta(days=i * interval)
                dates.append(date.strftime("%Y-%m-%d"))
            dates.reverse()  # 按时间正序排列

        else:
            return json.dumps({
                "error": f"不支持的时间范围类型: {range_type}",
                "supported_types": [
                    "近半年", "近一年", "本季度", "近一个季度",
                    "近一周", "近两周", "近一月"
                ]
            }, ensure_ascii=False)

        # 构建返回结果
        result = {
            "range_type": range_type,
            "total_count": len(dates),
            "dates": dates,
            "date_format": "YYYY-MM-DD",
            "generated_at": today.strftime("%Y-%m-%d %H:%M:%S")
        }

        logger.info(f"成功生成时间范围 {range_type}，共 {len(dates)} 个日期")
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.error(f"获取时间范围时发生错误: {e}")
        return json.dumps({
            "error": f"获取时间范围时发生错误: {str(e)}"
        }, ensure_ascii=False)