"""
浏览器自动化工具

基于 Playwright 和 Browserless 实现的浏览器操作工具，
为 DeepAgents 提供网页浏览、内容提取、截图等能力。
"""

import re
import json
import hashlib
import asyncio
from enum import Enum
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from langfuse import observe

from utils.logger import logger
from utils.config import get_config

if TYPE_CHECKING:
    from playwright.async_api import Page, Browser


# ==================== 配置 ====================

config = get_config()

# Browserless 配置
BROWSERLESS_URL = config.get("browserless.url", "ws://localhost:3000")
BROWSERLESS_TOKEN = config.get("browserless.token", None)
DEFAULT_TIMEOUT = config.get("browserless.default_timeout", 30000)

# 截图配置
SCREENSHOT_DIR = Path(config.get("browserless.screenshot.save_path", "./screenshots"))
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# 浏览器配置
VIEWPORT_WIDTH = config.get("browserless.browser.viewport.width", 1920)
VIEWPORT_HEIGHT = config.get("browserless.browser.viewport.height", 1080)
USER_AGENT = config.get(
    "browserless.browser.user_agent",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# ==================== 安全防护 ====================

class SecurityGuard:
    """URL 安全验证"""

    # 禁止的 URL 模式
    BLOCKED_PATTERNS = [
        r'^file://',
        r'^ftp://',
        r'localhost',
        r'127\.0\.0\.1',
        r'192\.168\.',
        r'10\.',
        r'172\.(1[6-9]|2[0-9]|3[0-1])\.',
        r'0\.0\.0\.0',
        r'\[::1\]',
    ]

    @classmethod
    def validate_url(cls, url: str) -> tuple[bool, str]:
        """
        验证 URL 是否安全

        Args:
            url: 待验证的 URL

        Returns:
            (is_valid, error_message)
        """
        try:
            parsed = urlparse(url)

            # 检查协议
            if parsed.scheme not in ['http', 'https']:
                return False, f"不支持的协议: {parsed.scheme}，仅支持 http/https"

            # 检查是否有主机名
            if not parsed.netloc:
                return False, "URL 缺少主机名"

            # 检查禁止模式
            for pattern in cls.BLOCKED_PATTERNS:
                if re.search(pattern, url, re.IGNORECASE):
                    return False, f"URL 包含禁止访问的地址模式"

            return True, ""

        except Exception as e:
            return False, f"URL 解析失败: {str(e)}"


# ==================== 数据模型 ====================

class ContentType(str, Enum):
    """内容提取类型"""
    AUTO = "auto"
    TEXT = "text"
    TABLE = "table"
    STRUCTURED = "structured"


class BrowserResult(BaseModel):
    """浏览器操作结果"""
    success: bool = Field(..., description="操作是否成功")
    data: Optional[Any] = Field(None, description="提取的数据")
    error: Optional[str] = Field(None, description="错误信息")
    url: Optional[str] = Field(None, description="访问的 URL")
    title: Optional[str] = Field(None, description="页面标题")
    screenshot_path: Optional[str] = Field(None, description="截图路径")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


# ==================== 浏览器客户端 ====================

class BrowserClient:
    """Browserless/Playwright 浏览器客户端"""

    def __init__(
        self,
        browserless_url: str = BROWSERLESS_URL,
        token: Optional[str] = BROWSERLESS_TOKEN,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.browserless_url = browserless_url
        self.token = token
        self.timeout = timeout
        self._playwright = None
        self._browser: Optional["Browser"] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):  # noqa: ARG002
        await self.close()

    async def connect(self) -> "Browser":
        """连接到浏览器服务"""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        # 判断是连接远程 browserless 还是本地浏览器
        if self.browserless_url and self.browserless_url.startswith("ws"):
            # 连接到 Browserless 服务
            ws_endpoint = f"{self.browserless_url}/chromium/playwright"
            if self.token:
                ws_endpoint += f"?token={self.token}"

            logger.info(f"连接到 Browserless: {self.browserless_url}")
            self._browser = await self._playwright.chromium.connect_over_cdp(ws_endpoint)
        else:
            # 启动本地浏览器
            logger.info("启动本地 Chromium 浏览器")
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )

        return self._browser

    async def new_page(self) -> "Page":
        """创建新页面"""
        if not self._browser:
            raise RuntimeError("浏览器未连接，请先调用 connect()")

        context = await self._browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            user_agent=USER_AGENT,
        )
        page = await context.new_page()
        page.set_default_timeout(self.timeout)

        return page

    async def close(self):
        """关闭连接"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


# ==================== 内容提取器 ====================

class ContentExtractor:
    """网页内容提取器"""

    @staticmethod
    async def extract_text(page: "Page", selector: Optional[str] = None) -> str:
        """提取文本内容"""
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        if selector:
            elements = soup.select(selector)
            return "\n".join([el.get_text(strip=True) for el in elements])

        # 移除脚本和样式
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        # 获取主要内容
        main = soup.find('main') or soup.find('article') or soup.find('body')
        if main:
            return main.get_text(separator="\n", strip=True)

        return soup.get_text(separator="\n", strip=True)

    @staticmethod
    async def extract_tables(page: "Page", selector: Optional[str] = None) -> List[Dict]:
        """提取表格数据"""
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        tables = soup.select(selector) if selector else soup.find_all('table')
        result = []

        for table in tables:
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            rows = []

            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all('td')]
                if cells:
                    rows.append(cells)

            result.append({
                "headers": headers,
                "rows": rows,
            })

        return result

    @staticmethod
    async def extract_structured(page: "Page") -> Dict[str, Any]:
        """提取结构化信息"""
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # 基础信息
        title = soup.title.string if soup.title else ""
        meta_desc = soup.find("meta", {"name": "description"})
        description = meta_desc.get("content", "") if meta_desc else ""

        # 提取链接
        links = []
        for a in soup.find_all('a', href=True)[:20]:  # 限制数量
            href = a.get('href', '')
            text = a.get_text(strip=True)
            if href and text and href.startswith('http'):
                links.append({"text": text, "url": href})

        # 提取图片
        images = []
        for img in soup.find_all('img', src=True)[:10]:
            src = img.get('src', '')
            alt = img.get('alt', '')
            if src:
                images.append({"src": src, "alt": alt})

        # 主要文本
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        text = ""
        if main_content:
            for tag in main_content(['script', 'style', 'nav', 'footer']):
                tag.decompose()
            text = main_content.get_text(separator="\n", strip=True)[:5000]

        return {
            "title": title,
            "description": description,
            "text": text,
            "links": links,
            "images": images,
        }

    @classmethod
    async def extract(
        cls,
        page: "Page",
        content_type: ContentType = ContentType.AUTO,
        selector: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        根据类型提取内容

        Args:
            page: Playwright 页面对象
            content_type: 提取类型
            selector: CSS 选择器

        Returns:
            提取的内容字典
        """
        if content_type == ContentType.TEXT:
            text = await cls.extract_text(page, selector)
            return {"type": "text", "content": text}

        elif content_type == ContentType.TABLE:
            tables = await cls.extract_tables(page, selector)
            return {"type": "table", "tables": tables}

        elif content_type == ContentType.STRUCTURED:
            data = await cls.extract_structured(page)
            return {"type": "structured", **data}

        else:  # AUTO
            data = await cls.extract_structured(page)
            return {"type": "auto", **data}


# ==================== 核心工具函数 ====================

async def _browse_website_async(
    url: str,
    extract_type: str = "auto",
    selector: Optional[str] = None,
    wait_for: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> BrowserResult:
    """
    异步浏览网站并提取内容

    Args:
        url: 目标网址
        extract_type: 提取类型 (auto/text/table/structured)
        selector: CSS 选择器
        wait_for: 等待的选择器或状态
        timeout: 超时时间(毫秒)

    Returns:
        BrowserResult
    """
    # 安全检查
    is_valid, error_msg = SecurityGuard.validate_url(url)
    if not is_valid:
        return BrowserResult(success=False, error=error_msg, url=url)

    try:
        async with BrowserClient(timeout=timeout) as client:
            page = await client.new_page()

            # 导航到页面
            logger.info(f"浏览网页: {url}")
            response = await page.goto(url, wait_until="domcontentloaded")

            # 等待特定元素（如果指定）
            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=timeout)
                except Exception:
                    logger.warning(f"等待元素超时: {wait_for}")

            # 额外等待页面稳定
            await page.wait_for_load_state("networkidle", timeout=timeout)

            # 获取页面标题
            title = await page.title()

            # 提取内容
            content_type = ContentType(extract_type)
            extracted = await ContentExtractor.extract(page, content_type, selector)

            logger.info(f"成功提取内容: {url}")

            return BrowserResult(
                success=True,
                data=extracted,
                url=url,
                title=title,
                metadata={
                    "status_code": response.status if response else None,
                    "extract_type": extract_type,
                }
            )

    except Exception as e:
        logger.error(f"浏览网页失败: {url}, 错误: {e}")
        return BrowserResult(
            success=False,
            error=str(e),
            url=url,
        )


async def _take_screenshot_async(
    url: str,
    full_page: bool = False,
    selector: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> BrowserResult:
    """
    异步截取网页截图

    Args:
        url: 目标网址
        full_page: 是否截取整个页面
        selector: 截取特定元素的选择器
        timeout: 超时时间(毫秒)

    Returns:
        BrowserResult
    """
    # 安全检查
    is_valid, error_msg = SecurityGuard.validate_url(url)
    if not is_valid:
        return BrowserResult(success=False, error=error_msg, url=url)

    try:
        async with BrowserClient(timeout=timeout) as client:
            page = await client.new_page()

            logger.info(f"截图网页: {url}")
            await page.goto(url, wait_until="networkidle")

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            screenshot_path = SCREENSHOT_DIR / f"screenshot_{timestamp}_{url_hash}.png"

            # 截图
            if selector:
                element = await page.query_selector(selector)
                if element:
                    await element.screenshot(path=str(screenshot_path))
                else:
                    return BrowserResult(
                        success=False,
                        error=f"未找到元素: {selector}",
                        url=url,
                    )
            else:
                await page.screenshot(path=str(screenshot_path), full_page=full_page)

            title = await page.title()
            logger.info(f"截图成功: {screenshot_path}")

            return BrowserResult(
                success=True,
                url=url,
                title=title,
                screenshot_path=str(screenshot_path),
            )

    except Exception as e:
        logger.error(f"截图失败: {url}, 错误: {e}")
        return BrowserResult(
            success=False,
            error=str(e),
            url=url,
        )


# ==================== 对外工具接口 ====================

@observe(name="browse_website")
def browse_website(
    url: str,
    extract_type: str = "auto",
    selector: Optional[str] = None,
    wait_for: Optional[str] = None,
) -> str:
    """
    浏览网站并提取内容

    访问指定 URL 的网页，支持 JavaScript 渲染，自动等待页面加载完成后提取内容。
    适用于获取动态网页内容、抓取表格数据、提取页面结构化信息等场景。

    Args:
        url: 目标网址，必须是 http 或 https 协议
        extract_type: 内容提取类型，可选值:
            - "auto": 自动提取结构化信息（标题、描述、正文、链接、图片）
            - "text": 仅提取纯文本内容
            - "table": 提取页面中的表格数据
            - "structured": 提取完整结构化数据
        selector: CSS 选择器，用于精确定位要提取的元素（可选）
        wait_for: 等待特定元素出现的 CSS 选择器（可选，用于动态加载的页面）

    Returns:
        JSON 格式的结果字符串，包含:
        - success: 是否成功
        - data: 提取的内容
        - url: 访问的 URL
        - title: 页面标题
        - error: 错误信息（仅失败时）

    Examples:
        # 自动提取页面信息
        >>> browse_website("https://www.python.org")

        # 仅提取文本内容
        >>> browse_website("https://example.com/article", extract_type="text")

        # 提取表格数据
        >>> browse_website("https://example.com/data", extract_type="table")

        # 提取特定元素
        >>> browse_website("https://example.com", selector=".main-content")
    """
    logger.info(f"开始浏览网站: {url}")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            _browse_website_async(url, extract_type, selector, wait_for)
        )
        loop.close()

        return json.dumps(result.model_dump(), ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"浏览网站异常: {e}")
        return json.dumps({
            "success": False,
            "error": f"执行异常: {str(e)}",
            "url": url,
        }, ensure_ascii=False)


@observe(name="take_screenshot")
def take_screenshot(
    url: str,
    full_page: bool = False,
    selector: Optional[str] = None,
) -> str:
    """
    截取网页截图

    访问指定 URL 并截取网页截图，支持截取整个页面或特定元素。
    截图会保存到服务器，并返回文件路径。

    Args:
        url: 目标网址，必须是 http 或 https 协议
        full_page: 是否截取整个页面（包括滚动区域），默认 False 只截取可视区域
        selector: CSS 选择器，用于截取特定元素（可选）

    Returns:
        JSON 格式的结果字符串，包含:
        - success: 是否成功
        - screenshot_path: 截图文件路径
        - url: 访问的 URL
        - title: 页面标题
        - error: 错误信息（仅失败时）

    Examples:
        # 截取可视区域
        >>> take_screenshot("https://www.python.org")

        # 截取整个页面
        >>> take_screenshot("https://www.python.org", full_page=True)

        # 截取特定元素
        >>> take_screenshot("https://example.com", selector="#main-content")
    """
    logger.info(f"开始截图: {url}")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            _take_screenshot_async(url, full_page, selector)
        )
        loop.close()

        return json.dumps(result.model_dump(), ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"截图异常: {e}")
        return json.dumps({
            "success": False,
            "error": f"执行异常: {str(e)}",
            "url": url,
        }, ensure_ascii=False)


# ==================== 异步接口（供内部使用）====================

async def browse_website_async(
    url: str,
    extract_type: str = "auto",
    selector: Optional[str] = None,
    wait_for: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """异步浏览网站（供内部异步调用）"""
    result = await _browse_website_async(url, extract_type, selector, wait_for, timeout)
    return json.dumps(result.model_dump(), ensure_ascii=False, default=str)


async def take_screenshot_async(
    url: str,
    full_page: bool = False,
    selector: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """异步截图（供内部异步调用）"""
    result = await _take_screenshot_async(url, full_page, selector, timeout)
    return json.dumps(result.model_dump(), ensure_ascii=False, default=str)
