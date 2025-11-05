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