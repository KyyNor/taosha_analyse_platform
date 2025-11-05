"""
Agent工具集合
包含热榜获取和程序员小故事等工具函数
"""
import httpx
from typing import Dict, Any
import json

from utils.logger import logger


def get_hotboard(platform: str) -> str:
    """
    获取各大平台的热门榜单

    Args:
        platform: 平台类型，支持: bilibili, weibo, zhihu, douyin, v2ex, ithome

    Returns:
        格式化的热榜信息
    """
    logger.info(f"开始获取{platform}热榜")
    try:
        # 验证平台参数
        supported_platforms = ["bilibili", "weibo", "zhihu", "douyin", "v2ex", "ithome"]
        if platform not in supported_platforms:
            return f"不支持的平台: {platform}。支持的平台有: {', '.join(supported_platforms)}"

        # 构建请求URL
        url = f"https://uapis.cn/api/v1/misc/hotboard?type={platform}"

        # 发送HTTP请求（同步方式）
        with httpx.Client(timeout=10) as client:
            response = client.get(url)
            if response.status_code != 200:
                return f"获取热榜失败: HTTP {response.status_code}"

            data = response.json()

            # 格式化热榜数据（API直接返回list）
            items = data.get("list", [])
            if not items:
                return f"{platform} 热榜暂无数据"

            platform_names = {
                "bilibili": "B站",
                "weibo": "微博",
                "zhihu": "知乎",
                "douyin": "抖音",
                "v2ex": "V2EX",
                "ithome": "IT之家"
            }

            platform_name = platform_names.get(platform, platform.upper())

            result = f"📊 {platform_name}热榜 Top {len(items)}\n\n"

            for i, item in enumerate(items, 1):
                title = item.get("title", "无标题")
                hot_value = item.get("hot_value", "")
                url = item.get("url", "")

                result += f"{i}. {title}"
                if hot_value:
                    result += f" 🔥 {hot_value}"
                result += "\n"

                if url:
                    result += f"   🔗 {url}\n"

                result += "\n"

            logger.info(f"成功获取{platform_name}热榜 {result}")
            return result.strip()

    except httpx.TimeoutException:
        return "获取热榜超时，请稍后重试"
    except httpx.RequestError as e:
        return f"网络请求失败: {str(e)}"
    except json.JSONDecodeError:
        return "响应数据格式错误"
    except Exception as e:
        logger.error(f"获取热榜时发生错误: {e}")
        return f"获取热榜时发生错误: {str(e)}"


def get_programmer_story() -> str:
    """
    获取程序员历史上的今天小故事

    Returns:
        格式化的程序员小故事信息
    """
    logger.info("开始获取程序员小故事")
    try:
        # 发送HTTP请求（同步方式）
        with httpx.Client(timeout=10) as client:
            response = client.get("https://uapis.cn/api/v1/history/programmer/today")
            if response.status_code != 200:
                return f"获取程序员小故事失败: HTTP {response.status_code}"

            data = response.json()

            # 解析响应数据
            if data.get("code") != 200:
                return f"API返回错误: {data.get('message', '未知错误')}"

            # 格式化故事数据
            events = data.get("events", [])
            if not events:
                return "今日暂无程序员小故事"

            # 获取第一个事件（主要故事）
            story_data = events[0]

            # 提取故事信息
            title = story_data.get("title", "无标题")
            content = story_data.get("description", "")
            date = data.get("date", "")
            year = story_data.get("year", "")
            category = story_data.get("category", "")
            tags = story_data.get("tags", [])

            result = "📚 程序员历史上的今天\n\n"

            # 添加标题
            if title:
                result += f"📖 {title}\n\n"

            # 添加日期信息
            if year:
                result += f"📅 年份: {year}年{date}\n\n"

            # 添加分类标签
            if category or tags:
                result += "🏷️ 标签: "
                if category:
                    result += f"{category}"
                if tags:
                    result += f", {', '.join(tags)}"
                result += "\n\n"

            # 添加内容
            if content:
                result += f"📝 内容:\n{content}\n\n"

            result += "💡 了解更多程序员历史，关注IT技术的发展历程！"

            logger.info(f"成功获取程序员小故事 {result}")
            return result.strip()

    except httpx.TimeoutException:
        return "获取程序员小故事超时，请稍后重试"
    except httpx.RequestError as e:
        return f"网络请求失败: {str(e)}"
    except json.JSONDecodeError:
        return "响应数据格式错误"
    except Exception as e:
        logger.error(f"获取程序员小故事时发生错误: {e}")
        return f"获取程序员小故事时发生错误: {str(e)}"