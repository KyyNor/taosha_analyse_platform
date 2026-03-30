"""
浏览器自动化工具 - 基于 browser-use

使用 browser-use AI Agent 实现智能网页浏览、内容提取、截图等能力。
通过 Browserless Docker 容器执行浏览器操作。
"""

import json
import asyncio
from typing import Optional, Any
from pathlib import Path
from datetime import datetime

from pydantic import BaseModel, Field
from langfuse import observe

from browser_use import Agent
from browser_use.browser.session import BrowserSession
from browser_use.llm.openai.chat import ChatOpenAI

from utils.logger import logger
from utils.config import settings


# ==================== 配置 ====================

# 截图目录
SCREENSHOT_DIR = Path(settings.browserless_screenshot_save_path)
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Browserless 配置（支持本地 Docker 或远程服务）
BROWSERLESS_URL = settings.browserless_url
BROWSERLESS_TOKEN = settings.browserless_token

# 浏览器配置
VIEWPORT_WIDTH = settings.browserless_viewport_width
VIEWPORT_HEIGHT = settings.browserless_viewport_height


# ==================== 数据模型 ====================

class BrowserResult(BaseModel):
    """浏览器操作结果"""
    success: bool = Field(..., description="操作是否成功")
    data: Optional[Any] = Field(None, description="提取的数据")
    error: Optional[str] = Field(None, description="错误信息")
    url: Optional[str] = Field(None, description="访问的 URL")
    screenshot_path: Optional[str] = Field(None, description="截图路径")


# ==================== LLM 配置 ====================

def get_llm():
    """获取 browser-use 兼容的 LLM 实例"""
    from services.llm_service.base_llm_service import BaseLLMService

    # 获取配置
    llm_service = BaseLLMService()

    # 获取 API 配置
    api_key = llm_service.api_key
    base_url = llm_service.base_url
    model = llm_service.model_name

    # 使用 browser-use 的 ChatOpenAI（不是 LangChain 的）
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=settings.llm_temperature,

        # Moonshot/非标准 OpenAI API 兼容性配置
        dont_force_structured_output=True,  # 禁用 response_format，避免 API 400 错误
        add_schema_to_system_prompt=True,   # 通过系统提示引导 JSON 输出
    )


# ==================== 浏览器会话 ====================

def get_browser_session() -> BrowserSession:
    """获取 Browserless 会话"""
    cdp_url = BROWSERLESS_URL
    if BROWSERLESS_TOKEN:
        cdp_url = f"{BROWSERLESS_URL}?token={BROWSERLESS_TOKEN}"
    return BrowserSession(cdp_url=cdp_url)


# ==================== 核心工具函数 ====================

@observe(name="browse_website")
def browse_website(
    task: str,
    url: Optional[str] = None,
    max_steps: int = 10,
    use_vision: bool = False,
) -> str:
    """
    使用 AI Agent 智能浏览网站

    Agent 会自主规划浏览策略，执行导航、点击、提取等操作。
    通过 Browserless Docker 容器执行浏览器操作。

    Args:
        task: 任务描述（自然语言），如 "查看2025-09-30日的机构活期存款"
        url: 起始 URL（可选，Agent 可以自己搜索）
        max_steps: 最大操作步数
        use_vision: 是否使用视觉模式（默认 False，使用文本模式）

    Returns:
        JSON 格式结果，包含:
        - success: 是否成功
        - data: 提取的内容
        - url: 访问的 URL
        - error: 错误信息（仅失败时）

    Examples:
        >>> browse_website("查找 Python 官网最新版本")
        >>> browse_website("在这个页面找到价格表", url="https://example.com")
    """
    logger.info(f"开始浏览任务: {task}")

    async def _run():
        browser_session = get_browser_session()

        # 构建完整任务
        full_task = task
        if url:
            full_task = f"首先访问 {url}，然后 {task}"

        agent = Agent(
            task=full_task,
            llm=get_llm(),
            browser_session=browser_session,
            use_vision=use_vision,
            max_actions_per_step=4,
        )

        try:
            history = await agent.run(max_steps=max_steps)

            # 提取最终结果
            final_result = history.final_result() if hasattr(history, 'final_result') else str(history)

            logger.info(f"浏览任务完成: {task}")
            return BrowserResult(
                success=True,
                data=final_result,
                url=url,
            )
        except Exception as e:
            logger.error(f"浏览任务失败: {e}")
            return BrowserResult(success=False, error=str(e), url=url)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run())
        loop.close()
        return json.dumps(result.model_dump(), ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"浏览任务异常: {e}")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@observe(name="take_screenshot")
def take_screenshot(
    url: str,
    task: Optional[str] = None,
    full_page: bool = False,
) -> str:
    """
    截取网页截图

    如果提供 task，Agent 会先执行任务再截图。

    Args:
        url: 目标网址
        task: 截图前要执行的任务（可选）
        full_page: 是否截取整页

    Returns:
        JSON 格式结果，包含:
        - success: 是否成功
        - screenshot_path: 截图文件路径
        - url: 访问的 URL
        - error: 错误信息（仅失败时）

    Examples:
        >>> take_screenshot("https://www.python.org")
        >>> take_screenshot("https://example.com", task="点击登录按钮")
        >>> take_screenshot("https://example.com", full_page=True)
    """
    logger.info(f"开始截图: {url}")

    async def _run():
        browser_session = get_browser_session()

        # 构建任务
        screenshot_task = f"访问 {url}"
        if task:
            screenshot_task += f"，然后 {task}"

        agent = Agent(
            task=screenshot_task,
            llm=get_llm(),
            browser_session=browser_session,
            use_vision=False,
        )

        try:
            await agent.run(max_steps=5)

            # 生成截图文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = SCREENSHOT_DIR / f"screenshot_{timestamp}.png"

            # 获取当前页面截图
            if browser_session.browser and browser_session.browser.contexts:
                context = browser_session.browser.contexts[0]
                if context.pages:
                    page = context.pages[0]
                    await page.screenshot(path=str(screenshot_path), full_page=full_page)

                    logger.info(f"截图成功: {screenshot_path}")
                    return BrowserResult(
                        success=True,
                        url=url,
                        screenshot_path=str(screenshot_path),
                    )

            return BrowserResult(
                success=False,
                error="无法获取浏览器页面",
                url=url,
            )

        except Exception as e:
            logger.error(f"截图失败: {e}")
            return BrowserResult(success=False, error=str(e), url=url)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run())
        loop.close()
        return json.dumps(result.model_dump(), ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"截图异常: {e}")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# ==================== 异步接口（供内部使用）====================

async def browse_website_async(
    task: str,
    url: Optional[str] = None,
    max_steps: int = 10,
    use_vision: bool = False,
) -> str:
    """异步版本的浏览网站"""
    browser_session = get_browser_session()

    full_task = task
    if url:
        full_task = f"首先访问 {url}，然后 {task}"

    agent = Agent(
        task=full_task,
        llm=get_llm(),
        browser_session=browser_session,
        use_vision=use_vision,
        max_actions_per_step=4,
    )

    try:
        history = await agent.run(max_steps=max_steps)
        final_result = history.final_result() if hasattr(history, 'final_result') else str(history)

        result = BrowserResult(success=True, data=final_result, url=url)
    except Exception as e:
        logger.error(f"浏览任务失败: {e}")
        result = BrowserResult(success=False, error=str(e), url=url)

    return json.dumps(result.model_dump(), ensure_ascii=False, default=str)


async def take_screenshot_async(
    url: str,
    task: Optional[str] = None,
    full_page: bool = False,
) -> str:
    """异步版本的截图"""
    browser_session = get_browser_session()

    screenshot_task = f"访问 {url}"
    if task:
        screenshot_task += f"，然后 {task}"

    agent = Agent(
        task=screenshot_task,
        llm=get_llm(),
        browser_session=browser_session,
        use_vision=False,
    )

    try:
        await agent.run(max_steps=5)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = SCREENSHOT_DIR / f"screenshot_{timestamp}.png"

        if browser_session.browser and browser_session.browser.contexts:
            context = browser_session.browser.contexts[0]
            if context.pages:
                page = context.pages[0]
                await page.screenshot(path=str(screenshot_path), full_page=full_page)

                result = BrowserResult(success=True, url=url, screenshot_path=str(screenshot_path))
                return json.dumps(result.model_dump(), ensure_ascii=False, default=str)

        result = BrowserResult(success=False, error="无法获取浏览器页面", url=url)
    except Exception as e:
        logger.error(f"截图失败: {e}")
        result = BrowserResult(success=False, error=str(e), url=url)

    return json.dumps(result.model_dump(), ensure_ascii=False, default=str)
