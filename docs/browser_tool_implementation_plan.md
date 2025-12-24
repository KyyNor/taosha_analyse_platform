# 浏览器操作工具实施计划

## 文档信息
- **创建日期**: 2025-12-23
- **版本**: v1.0
- **状态**: 待审阅

## 1. 项目概述

### 1.1 背景
在深度研究Agent（DeepAgents）系统中，当需要获取动态网页内容、执行JavaScript渲染、处理复杂交互等任务时，传统的HTTP请求无法满足需求。因此需要引入浏览器自动化能力，使Agent能够像真实用户一样操作浏览器。

### 1.2 目标
- 为主Agent提供浏览器操作能力，支持网页导航、元素交互、内容提取
- 基于browser-use库实现高级浏览器自动化
- 使用browserless作为无头浏览器服务，降低资源占用
- 设计为可插拔的Tool或SubAgent，按需调用
- 支持智能化的网页信息提取和结构化输出

### 1.3 技术选型

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 浏览器自动化框架 | browser-use | latest | 基于Playwright的智能浏览器操作库 |
| 无头浏览器服务 | browserless | v2.x | 提供Chrome/Chromium无头浏览器实例 |
| 底层驱动 | Playwright | 1.40+ | 浏览器控制协议 |
| AI集成 | LangChain | 1.0+ | Agent工具封装和编排 |
| 结构化输出 | Pydantic | 2.x | 数据模型定义和验证 |

### 1.4 核心价值
- **动态内容获取**: 处理JavaScript渲染的现代Web应用
- **复杂交互支持**: 模拟点击、滚动、表单填写等用户行为
- **智能信息提取**: 结合AI能力自动理解和提取页面核心信息
- **反爬虫绕过**: 模拟真实浏览器环境，降低被封禁风险
- **可视化调试**: 支持截图、录屏等调试功能

---

## 2. 系统架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Deep Research Agent                     │
│                     (主Agent - LangChain)                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ 调用工具
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Browser Tool / SubAgent                     │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐ │
│  │  Tool Wrapper  │  │  Browser Agent │  │  Task Router  │ │
│  │   (LangChain)  │  │  (browser-use) │  │   (规则引擎)  │ │
│  └────────┬───────┘  └────────┬───────┘  └───────┬───────┘ │
│           │                   │                   │          │
│           └───────────────────┴───────────────────┘          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ 浏览器操作
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Browserless Service                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Chrome 1   │  │  Chrome 2   │  │  Chrome N   │         │
│  │  (Session)  │  │  (Session)  │  │  (Session)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 两种实现方案对比

#### 方案A：Tool方式（推荐用于简单场景）
```python
# 直接作为LangChain Tool注册
tools = [
    browse_website,        # 简单网页浏览
    extract_content,       # 内容提取
    take_screenshot,       # 截图
    # ... 其他工具
]
```

**优点**：
- 实现简单，易于维护
- 调用开销小
- 适合单次、简单的浏览任务

**缺点**：
- 缺乏复杂任务规划能力
- 无法处理多步骤交互
- 状态管理困难

#### 方案B：SubAgent方式（推荐用于复杂场景）
```python
# 作为独立的SubAgent，具备自主决策能力
class BrowserAgent:
    def __init__(self):
        self.browser_use_agent = Agent(
            task="根据用户指令智能浏览网页",
            llm=llm,
            browser=browser,
        )

    async def execute_task(self, task_description: str):
        # SubAgent自主分解任务、执行操作
        return await self.browser_use_agent.run(task_description)
```

**优点**：
- 支持复杂的多步骤任务
- 可自主规划浏览策略
- 更强的错误恢复能力

**缺点**：
- 实现复杂度高
- 调用开销大（涉及多次LLM推理）
- 需要更多token消耗

#### 推荐架构：混合方式
```python
# 提供两层接口：
# 1. 基础Tool层 - 快速、简单操作
tools = [
    simple_browse,         # 简单浏览（直接返回内容）
    quick_screenshot,      # 快速截图
]

# 2. SubAgent层 - 复杂、智能任务
tools += [
    intelligent_browser_agent,  # 调用browser-use的智能Agent
]
```

### 2.3 数据流设计

```
用户输入: "帮我查找Python官网最新版本信息"
    ↓
主Agent分析: 需要访问网页
    ↓
调用Browser Tool/SubAgent
    ↓
┌──────────────────────────────────────────┐
│ Browser Tool执行流程:                     │
│  1. 任务解析: 提取URL、目标信息           │
│  2. 浏览器启动: 连接browserless          │
│  3. 页面导航: 打开python.org             │
│  4. 智能提取: 定位版本号元素              │
│  5. 数据结构化: 转为JSON                 │
│  6. 资源清理: 关闭浏览器会话              │
└──────────────────────────────────────────┘
    ↓
返回结构化数据给主Agent
    ↓
主Agent整合信息并回复用户
```

---

## 3. 技术实现方案

### 3.1 目录结构设计

```
backend/services/agents/
├── tools/
│   ├── browser_tool.py              # 浏览器工具主入口
│   ├── browser/                     # 浏览器工具模块
│   │   ├── __init__.py
│   │   ├── browser_agent.py         # browser-use Agent封装
│   │   ├── browser_client.py        # browserless客户端
│   │   ├── content_extractor.py     # 智能内容提取器
│   │   ├── task_router.py           # 任务路由和规则引擎
│   │   ├── models.py                # Pydantic数据模型
│   │   └── utils.py                 # 工具函数
│   └── ...
├── config/
│   └── browser_config.yaml          # 浏览器工具配置
└── ...
```

### 3.2 核心模块设计

#### 3.2.1 Browser Client（浏览器客户端）

```python
# backend/services/agents/tools/browser/browser_client.py

from playwright.async_api import async_playwright, Browser, Page
from typing import Optional, Dict, Any
import httpx

class BrowserlessClient:
    """Browserless服务客户端"""

    def __init__(
        self,
        browserless_url: str = "ws://localhost:3000",
        token: Optional[str] = None,
        default_timeout: int = 30000,
    ):
        """
        初始化Browserless客户端

        Args:
            browserless_url: Browserless服务地址
            token: API Token（如果需要认证）
            default_timeout: 默认超时时间（毫秒）
        """
        self.browserless_url = browserless_url
        self.token = token
        self.default_timeout = default_timeout
        self._playwright = None
        self._browser = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()

    async def connect(self) -> Browser:
        """连接到Browserless服务"""
        self._playwright = await async_playwright().start()

        # 构建连接URL
        ws_endpoint = f"{self.browserless_url}/chromium/playwright"
        if self.token:
            ws_endpoint += f"?token={self.token}"

        # 连接到远程浏览器
        self._browser = await self._playwright.chromium.connect_over_cdp(
            ws_endpoint
        )

        return self._browser

    async def new_page(self, **kwargs) -> Page:
        """创建新页面"""
        if not self._browser:
            raise RuntimeError("Browser not connected")

        context = await self._browser.new_context(**kwargs)
        page = await context.new_page()
        page.set_default_timeout(self.default_timeout)

        return page

    async def close(self):
        """关闭连接"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
```

#### 3.2.2 Browser Agent（智能浏览器Agent）

```python
# backend/services/agents/tools/browser/browser_agent.py

from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI
from typing import Optional, Dict, Any
from .browser_client import BrowserlessClient
from .models import BrowserTask, BrowserResult

class IntelligentBrowserAgent:
    """基于browser-use的智能浏览器Agent"""

    def __init__(
        self,
        browserless_client: BrowserlessClient,
        llm: Optional[ChatOpenAI] = None,
    ):
        """
        初始化智能浏览器Agent

        Args:
            browserless_client: Browserless客户端
            llm: 语言模型（用于决策）
        """
        self.browserless_client = browserless_client
        self.llm = llm or ChatOpenAI(model="gpt-4o")
        self._agent = None

    async def initialize(self):
        """初始化browser-use Agent"""
        # 连接到browserless
        browser = await self.browserless_client.connect()

        # 配置browser-use
        browser_config = BrowserConfig(
            headless=True,
            disable_security=False,  # 生产环境应为False
        )

        # 创建browser-use Agent
        self._agent = Agent(
            task="",  # 任务将在run时指定
            llm=self.llm,
            browser=Browser(config=browser_config),
        )

    async def execute_task(
        self,
        task: BrowserTask
    ) -> BrowserResult:
        """
        执行浏览器任务

        Args:
            task: 浏览器任务描述

        Returns:
            BrowserResult: 执行结果
        """
        if not self._agent:
            await self.initialize()

        try:
            # 更新任务描述
            self._agent.task = task.instruction

            # 执行任务（browser-use会自动规划和执行）
            result = await self._agent.run(max_steps=task.max_steps)

            # 提取结果
            return BrowserResult(
                success=True,
                data=result.final_result(),
                steps=result.history(),
                metadata={
                    "total_steps": len(result.history()),
                    "task_type": task.task_type,
                }
            )

        except Exception as e:
            return BrowserResult(
                success=False,
                error=str(e),
                data=None,
            )

    async def cleanup(self):
        """清理资源"""
        await self.browserless_client.close()
```

#### 3.2.3 Content Extractor（内容提取器）

```python
# backend/services/agents/tools/browser/content_extractor.py

from playwright.async_api import Page
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from .models import ContentType, ExtractedContent

class SmartContentExtractor:
    """智能内容提取器"""

    def __init__(self, llm: Optional[Any] = None):
        """
        初始化内容提取器

        Args:
            llm: 语言模型（用于智能提取）
        """
        self.llm = llm

    async def extract(
        self,
        page: Page,
        content_type: ContentType = ContentType.AUTO,
        selector: Optional[str] = None,
    ) -> ExtractedContent:
        """
        从页面提取内容

        Args:
            page: Playwright页面对象
            content_type: 内容类型
            selector: CSS选择器（可选）

        Returns:
            ExtractedContent: 提取的内容
        """
        # 获取页面HTML
        html_content = await page.content()

        # 使用BeautifulSoup解析
        soup = BeautifulSoup(html_content, 'html.parser')

        if content_type == ContentType.TEXT:
            # 提取纯文本
            return await self._extract_text(soup, selector)

        elif content_type == ContentType.TABLE:
            # 提取表格数据
            return await self._extract_tables(soup, selector)

        elif content_type == ContentType.LIST:
            # 提取列表
            return await self._extract_lists(soup, selector)

        elif content_type == ContentType.STRUCTURED:
            # 智能结构化提取（使用LLM）
            return await self._extract_structured(page, soup)

        else:  # AUTO
            # 自动检测并提取
            return await self._extract_auto(page, soup)

    async def _extract_text(
        self,
        soup: BeautifulSoup,
        selector: Optional[str]
    ) -> ExtractedContent:
        """提取文本内容"""
        if selector:
            elements = soup.select(selector)
            text = "\n".join([el.get_text(strip=True) for el in elements])
        else:
            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text(separator="\n", strip=True)

        return ExtractedContent(
            content_type=ContentType.TEXT,
            data={"text": text},
        )

    async def _extract_tables(
        self,
        soup: BeautifulSoup,
        selector: Optional[str]
    ) -> ExtractedContent:
        """提取表格数据"""
        tables = soup.select(selector) if selector else soup.find_all('table')

        table_data = []
        for table in tables:
            # 提取表头
            headers = [th.get_text(strip=True) for th in table.find_all('th')]

            # 提取行数据
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all('td')]
                if cells:
                    rows.append(cells)

            table_data.append({
                "headers": headers,
                "rows": rows,
            })

        return ExtractedContent(
            content_type=ContentType.TABLE,
            data={"tables": table_data},
        )

    async def _extract_structured(
        self,
        page: Page,
        soup: BeautifulSoup
    ) -> ExtractedContent:
        """使用LLM进行智能结构化提取"""
        # 获取页面关键信息
        title = soup.title.string if soup.title else ""
        meta_desc = soup.find("meta", {"name": "description"})
        description = meta_desc.get("content", "") if meta_desc else ""

        # 获取主要内容区域（启发式方法）
        main_content = (
            soup.find("main") or
            soup.find("article") or
            soup.find("div", {"class": "content"}) or
            soup.body
        )

        text_content = main_content.get_text(separator="\n", strip=True) if main_content else ""

        # 使用LLM提取结构化信息
        if self.llm:
            from langchain.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import JsonOutputParser

            prompt = ChatPromptTemplate.from_template(
                """从以下网页内容中提取关键信息，以JSON格式返回：

标题: {title}
描述: {description}
内容:
{content}

请提取：
1. 主要主题
2. 关键信息点（列表形式）
3. 重要数据（如版本号、日期、数字等）
4. 相关链接

以JSON格式返回，包含以下字段：
{{
    "topic": "主题",
    "key_points": ["要点1", "要点2"],
    "important_data": {{"数据类型": "值"}},
    "links": ["链接1", "链接2"]
}}
"""
            )

            chain = prompt | self.llm | JsonOutputParser()

            structured_data = await chain.ainvoke({
                "title": title,
                "description": description,
                "content": text_content[:4000],  # 限制长度
            })

            return ExtractedContent(
                content_type=ContentType.STRUCTURED,
                data=structured_data,
            )

        # 如果没有LLM，返回基础结构
        return ExtractedContent(
            content_type=ContentType.STRUCTURED,
            data={
                "title": title,
                "description": description,
                "content": text_content[:2000],
            },
        )
```

#### 3.2.4 Data Models（数据模型）

```python
# backend/services/agents/tools/browser/models.py

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List
from enum import Enum

class ContentType(str, Enum):
    """内容类型"""
    AUTO = "auto"
    TEXT = "text"
    TABLE = "table"
    LIST = "list"
    STRUCTURED = "structured"
    SCREENSHOT = "screenshot"

class TaskType(str, Enum):
    """任务类型"""
    SIMPLE_BROWSE = "simple_browse"        # 简单浏览
    EXTRACT_INFO = "extract_info"          # 提取信息
    INTERACT = "interact"                  # 页面交互
    MULTI_STEP = "multi_step"              # 多步骤任务

class BrowserTask(BaseModel):
    """浏览器任务定义"""
    task_type: TaskType = Field(
        ...,
        description="任务类型"
    )
    instruction: str = Field(
        ...,
        description="任务指令描述"
    )
    url: Optional[HttpUrl] = Field(
        None,
        description="目标URL（可选，某些任务可能需要搜索后确定）"
    )
    content_type: ContentType = Field(
        default=ContentType.AUTO,
        description="期望的内容类型"
    )
    selector: Optional[str] = Field(
        None,
        description="CSS选择器（用于精确定位）"
    )
    max_steps: int = Field(
        default=10,
        description="最大执行步骤数"
    )
    timeout: int = Field(
        default=30000,
        description="超时时间（毫秒）"
    )
    screenshot: bool = Field(
        default=False,
        description="是否需要截图"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="额外的元数据"
    )

class BrowserResult(BaseModel):
    """浏览器任务执行结果"""
    success: bool = Field(
        ...,
        description="任务是否成功"
    )
    data: Optional[Any] = Field(
        None,
        description="提取的数据"
    )
    error: Optional[str] = Field(
        None,
        description="错误信息（如果失败）"
    )
    steps: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="执行步骤历史"
    )
    screenshot_path: Optional[str] = Field(
        None,
        description="截图文件路径"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="执行元数据"
    )

class ExtractedContent(BaseModel):
    """提取的内容"""
    content_type: ContentType
    data: Dict[str, Any]
    url: Optional[str] = None
    timestamp: Optional[str] = None
```

#### 3.2.5 Browser Tool（主入口）

```python
# backend/services/agents/tools/browser_tool.py

from typing import Optional, Dict, Any
import json
from langfuse import observe
from utils.logger import logger
from .browser.browser_client import BrowserlessClient
from .browser.browser_agent import IntelligentBrowserAgent
from .browser.content_extractor import SmartContentExtractor
from .browser.models import BrowserTask, TaskType, ContentType
from utils.config import get_config

# 全局配置
config = get_config()
BROWSERLESS_URL = config.get("browserless.url", "ws://localhost:3000")
BROWSERLESS_TOKEN = config.get("browserless.token", None)

@observe(name="browse_website")
async def browse_website(
    url: str,
    instruction: Optional[str] = None,
    extract_type: str = "auto",
) -> str:
    """
    浏览网站并提取内容（简单模式）

    Args:
        url: 目标网址
        instruction: 可选的额外指令（例如"找到最新版本号"）
        extract_type: 提取类型，可选值: auto, text, table, list, structured

    Returns:
        包含提取内容的JSON字符串

    Examples:
        >>> browse_website("https://www.python.org", "找到最新Python版本")
        '{"success": true, "data": {"version": "3.12.0", ...}}'
    """
    logger.info(f"开始浏览网站: {url}")

    try:
        # 创建浏览器客户端
        async with BrowserlessClient(
            browserless_url=BROWSERLESS_URL,
            token=BROWSERLESS_TOKEN,
        ) as client:
            # 创建页面
            page = await client.new_page()

            # 导航到目标URL
            await page.goto(url, wait_until="networkidle")

            # 提取内容
            extractor = SmartContentExtractor()
            content_type = ContentType(extract_type)

            extracted = await extractor.extract(
                page=page,
                content_type=content_type,
            )

            # 构建结果
            result = {
                "success": True,
                "url": url,
                "content_type": extract_type,
                "data": extracted.data,
            }

            logger.info(f"成功浏览网站: {url}")
            return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.error(f"浏览网站失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "url": url,
        }, ensure_ascii=False)

@observe(name="intelligent_browse")
async def intelligent_browse(
    instruction: str,
    url: Optional[str] = None,
    max_steps: int = 10,
) -> str:
    """
    智能浏览器Agent（复杂模式）

    使用browser-use的AI Agent自主规划和执行浏览任务，适合复杂的多步骤操作。

    Args:
        instruction: 任务指令（自然语言描述）
        url: 起始URL（可选，Agent可自行搜索）
        max_steps: 最大执行步数

    Returns:
        包含执行结果的JSON字符串

    Examples:
        >>> intelligent_browse(
        ...     instruction="访问Python官网，找到最新稳定版本的发布日期和下载链接",
        ...     url="https://www.python.org"
        ... )
    """
    logger.info(f"开始智能浏览任务: {instruction}")

    try:
        # 创建浏览器客户端
        browserless_client = BrowserlessClient(
            browserless_url=BROWSERLESS_URL,
            token=BROWSERLESS_TOKEN,
        )

        # 创建智能Agent
        agent = IntelligentBrowserAgent(
            browserless_client=browserless_client,
        )

        # 构建任务
        task = BrowserTask(
            task_type=TaskType.MULTI_STEP,
            instruction=instruction,
            url=url,
            max_steps=max_steps,
        )

        # 执行任务
        result = await agent.execute_task(task)

        # 清理资源
        await agent.cleanup()

        # 返回结果
        return json.dumps({
            "success": result.success,
            "data": result.data,
            "steps": result.steps,
            "error": result.error,
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"智能浏览任务失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "instruction": instruction,
        }, ensure_ascii=False)

@observe(name="take_screenshot")
async def take_screenshot(
    url: str,
    selector: Optional[str] = None,
    full_page: bool = False,
) -> str:
    """
    网页截图工具

    Args:
        url: 目标网址
        selector: CSS选择器（截取特定元素）
        full_page: 是否截取整个页面

    Returns:
        包含截图路径的JSON字符串
    """
    logger.info(f"开始截图: {url}")

    try:
        async with BrowserlessClient(
            browserless_url=BROWSERLESS_URL,
            token=BROWSERLESS_TOKEN,
        ) as client:
            page = await client.new_page()
            await page.goto(url, wait_until="networkidle")

            # 生成截图文件名
            import hashlib
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            screenshot_path = f"screenshots/screenshot_{timestamp}_{url_hash}.png"

            # 截图
            if selector:
                element = await page.query_selector(selector)
                if element:
                    await element.screenshot(path=screenshot_path)
                else:
                    return json.dumps({
                        "success": False,
                        "error": f"Element not found: {selector}",
                    }, ensure_ascii=False)
            else:
                await page.screenshot(
                    path=screenshot_path,
                    full_page=full_page,
                )

            logger.info(f"截图成功: {screenshot_path}")
            return json.dumps({
                "success": True,
                "screenshot_path": screenshot_path,
                "url": url,
            }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"截图失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "url": url,
        }, ensure_ascii=False)
```

### 3.3 配置文件设计

```yaml
# backend/config/config.yaml (新增部分)

# Browserless配置
browserless:
  # Browserless服务地址
  url: "ws://localhost:3000"

  # API Token（如果需要认证）
  token: null

  # 默认超时时间（毫秒）
  default_timeout: 30000

  # 浏览器配置
  browser:
    # 是否无头模式
    headless: true

    # 视窗大小
    viewport:
      width: 1920
      height: 1080

    # User Agent
    user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # 是否禁用安全特性（仅开发环境）
    disable_security: false

  # 截图配置
  screenshot:
    # 截图保存路径
    save_path: "screenshots/"

    # 默认格式
    format: "png"

    # 图片质量（1-100）
    quality: 90

  # 内容提取配置
  extraction:
    # 是否使用LLM进行智能提取
    use_llm: true

    # 文本提取最大长度
    max_text_length: 10000

    # 表格提取最大行数
    max_table_rows: 1000
```

---

## 4. 实施步骤

### 阶段一：环境准备（1-2天）

#### 4.1 安装Browserless服务

**方式A：Docker部署（推荐）**
```bash
# 拉取browserless镜像
docker pull browserless/chrome:latest

# 启动服务
docker run -d \
  --name browserless \
  -p 3000:3000 \
  -e "MAX_CONCURRENT_SESSIONS=10" \
  -e "CONNECTION_TIMEOUT=60000" \
  -e "MAX_QUEUE_LENGTH=20" \
  browserless/chrome:latest

# 验证服务
curl http://localhost:3000/json/version
```

**方式B：本地安装**
```bash
npm install -g browserless

# 启动服务
browserless start --port 3000
```

#### 4.2 安装Python依赖

```bash
cd backend

# 安装核心依赖
uv add browser-use
uv add playwright
uv add beautifulsoup4
uv add lxml

# 安装Playwright浏览器
uv run playwright install chromium
```

#### 4.3 更新配置文件

编辑 `backend/config/config.yaml`，添加browserless配置（见3.3节）。

### 阶段二：核心模块开发（3-5天）

#### 4.4 开发BrowserlessClient
- [ ] 实现基础连接功能
- [ ] 实现异步上下文管理器
- [ ] 添加错误处理和重试机制
- [ ] 编写单元测试

#### 4.5 开发ContentExtractor
- [ ] 实现文本提取
- [ ] 实现表格提取
- [ ] 实现列表提取
- [ ] 实现LLM增强的结构化提取
- [ ] 编写测试用例

#### 4.6 开发BrowserAgent
- [ ] 集成browser-use库
- [ ] 实现任务执行逻辑
- [ ] 添加步骤追踪和日志
- [ ] 实现资源清理机制

#### 4.7 开发Tool入口函数
- [ ] 实现 `browse_website`（简单模式）
- [ ] 实现 `intelligent_browse`（智能模式）
- [ ] 实现 `take_screenshot`（截图工具）
- [ ] 添加Langfuse观测

### 阶段三：集成与测试（2-3天）

#### 4.8 集成到主Agent

编辑 `backend/services/agents/agent_service.py`：

```python
# 导入浏览器工具
from services.agents.tools.browser_tool import (
    browse_website,
    intelligent_browse,
    take_screenshot,
)

# 在 _initialize_agent 方法中添加工具
tools = [
    get_date_range,
    create_chart,
    create_comparison,
    get_metrics,
    browse_website,          # 简单浏览
    intelligent_browse,      # 智能浏览
    take_screenshot,         # 截图
]
```

#### 4.9 编写测试用例

```python
# tests/test_browser_tool.py

import pytest
from services.agents.tools.browser_tool import (
    browse_website,
    intelligent_browse,
    take_screenshot,
)

@pytest.mark.asyncio
async def test_browse_website():
    """测试简单浏览功能"""
    result = await browse_website(
        url="https://www.python.org",
        extract_type="text"
    )

    assert "success" in result
    data = json.loads(result)
    assert data["success"] is True
    assert "data" in data

@pytest.mark.asyncio
async def test_intelligent_browse():
    """测试智能浏览功能"""
    result = await intelligent_browse(
        instruction="访问Python官网，找到最新版本号",
        url="https://www.python.org"
    )

    data = json.loads(result)
    assert data["success"] is True
    assert "steps" in data

@pytest.mark.asyncio
async def test_screenshot():
    """测试截图功能"""
    result = await take_screenshot(
        url="https://www.python.org",
        full_page=False
    )

    data = json.loads(result)
    assert data["success"] is True
    assert "screenshot_path" in data
```

运行测试：
```bash
cd backend
uv run pytest tests/test_browser_tool.py -v
```

#### 4.10 端到端测试

创建测试脚本 `tests/manual_test_browser.py`：

```python
import asyncio
import json
from services.agents.agent_service import AgentService

async def test_agent_with_browser():
    """测试Agent使用浏览器工具"""

    agent_service = AgentService()

    async with agent_service.lifespan():
        # 测试查询
        query = "帮我查询Python官网上最新的稳定版本是什么？"

        result_stream = agent_service.chat_stream(
            session_id="test-session",
            message=query,
        )

        async for event in result_stream:
            print(json.dumps(event, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(test_agent_with_browser())
```

运行测试：
```bash
uv run python -m tests.manual_test_browser
```

### 阶段四：优化与文档（1-2天）

#### 4.11 性能优化
- [ ] 实现浏览器连接池（复用浏览器实例）
- [ ] 添加缓存机制（相同URL短期内复用结果）
- [ ] 优化超时和重试策略
- [ ] 实现并发限流（避免过多并发请求）

#### 4.12 错误处理增强
- [ ] 完善异常捕获和友好错误信息
- [ ] 添加降级策略（browserless不可用时的备选方案）
- [ ] 实现自动重试机制
- [ ] 添加熔断器模式

#### 4.13 文档编写
- [ ] 编写API文档
- [ ] 编写使用示例
- [ ] 更新CLAUDE.md
- [ ] 创建troubleshooting指南

---

## 5. 部署方案

### 5.1 开发环境部署

```bash
# 1. 启动Browserless（Docker）
docker-compose up -d browserless

# 2. 配置环境变量
export BROWSERLESS_URL="ws://localhost:3000"

# 3. 启动后端服务
cd backend
./sbackend.sh
```

### 5.2 生产环境部署

**Docker Compose配置**：

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 后端服务
  backend:
    build: ./backend
    ports:
      - "50020:50020"
    environment:
      - BROWSERLESS_URL=ws://browserless:3000
    depends_on:
      - browserless

  # Browserless服务
  browserless:
    image: browserless/chrome:latest
    ports:
      - "3000:3000"
    environment:
      - MAX_CONCURRENT_SESSIONS=10
      - CONNECTION_TIMEOUT=60000
      - MAX_QUEUE_LENGTH=20
      - PREBOOT_CHROME=true
      - ENABLE_DEBUGGER=false
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

启动：
```bash
docker-compose up -d
```

### 5.3 监控与告警

**Prometheus配置**：
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'browserless'
    static_configs:
      - targets: ['browserless:3000']
    metrics_path: '/metrics'
```

**关键指标**：
- `browserless_concurrent_sessions` - 并发会话数
- `browserless_queue_length` - 队列长度
- `browserless_timeout_count` - 超时次数
- `browserless_error_count` - 错误次数

---

## 6. 风险与挑战

### 6.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Browserless服务不稳定 | 高 | 实现健康检查、自动重启、降级策略 |
| 浏览器资源占用高 | 中 | 实现连接池、限流、自动清理 |
| 反爬虫机制 | 中 | 模拟真实用户行为、添加延迟、轮换User-Agent |
| 网络超时 | 中 | 配置合理的超时时间、重试机制 |
| browser-use版本兼容性 | 低 | 锁定依赖版本、定期测试更新 |

### 6.2 安全风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| SSRF攻击 | 高 | URL白名单、禁止访问内网地址 |
| 恶意代码执行 | 高 | 沙箱隔离、禁用危险功能 |
| 数据泄露 | 高 | 不记录敏感信息、截图自动清理 |
| 资源滥用 | 中 | 限流、配额管理、监控告警 |

**安全加固建议**：

```python
# backend/services/agents/tools/browser/security.py

import re
from urllib.parse import urlparse
from typing import List

class SecurityGuard:
    """安全防护"""

    # 禁止的URL模式
    BLOCKED_PATTERNS = [
        r'^file://',
        r'^ftp://',
        r'localhost',
        r'127\.0\.0\.1',
        r'192\.168\.',
        r'10\.',
        r'172\.(1[6-9]|2[0-9]|3[0-1])\.',
    ]

    # 允许的域名白名单（可选）
    ALLOWED_DOMAINS: List[str] = []

    @classmethod
    def validate_url(cls, url: str) -> bool:
        """验证URL是否安全"""
        parsed = urlparse(url)

        # 检查协议
        if parsed.scheme not in ['http', 'https']:
            return False

        # 检查禁止模式
        for pattern in cls.BLOCKED_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return False

        # 检查白名单（如果配置了）
        if cls.ALLOWED_DOMAINS:
            if parsed.netloc not in cls.ALLOWED_DOMAINS:
                return False

        return True
```

---

## 7. 成本估算

### 7.1 开发成本

| 阶段 | 工作量 | 说明 |
|------|--------|------|
| 环境准备 | 1-2天 | Docker部署、依赖安装 |
| 核心开发 | 3-5天 | 模块开发、单元测试 |
| 集成测试 | 2-3天 | Agent集成、端到端测试 |
| 优化文档 | 1-2天 | 性能优化、文档编写 |
| **总计** | **7-12天** | 约1.5-2.5周 |

### 7.2 运维成本

**资源占用（单个Browserless实例）**：
- CPU: 1-2核
- 内存: 2-4GB
- 存储: 10GB（浏览器+缓存）

**扩展性**：
- 单实例支持10-20个并发会话
- 可水平扩展（Kubernetes部署）

---

## 8. 后续扩展

### 8.1 功能增强
- [ ] 支持更多浏览器类型（Firefox、Safari）
- [ ] 添加代理支持（IP轮换）
- [ ] 实现验证码识别集成
- [ ] 支持文件下载和上传
- [ ] 添加Cookie管理和会话持久化
- [ ] 实现分布式浏览器集群

### 8.2 性能优化
- [ ] 实现智能预热（提前启动浏览器实例）
- [ ] 添加CDN缓存支持
- [ ] 实现增量提取（只获取变化部分）
- [ ] 优化LLM调用（本地模型 vs 远程API）

### 8.3 监控增强
- [ ] 实时性能指标仪表板
- [ ] 异常告警（Slack/Email通知）
- [ ] 访问日志和审计
- [ ] 成本分析和优化建议

---

## 9. 附录

### 9.1 依赖清单

```toml
# pyproject.toml (新增依赖)

[project]
dependencies = [
    # ... 现有依赖 ...
    "browser-use>=0.1.0",
    "playwright>=1.40.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest-asyncio>=0.21.0",
    "pytest-playwright>=0.4.0",
]
```

### 9.2 参考资料

- **browser-use文档**: https://github.com/gregpr07/browser-use
- **Browserless文档**: https://www.browserless.io/docs
- **Playwright文档**: https://playwright.dev/python/
- **LangChain Tools**: https://python.langchain.com/docs/modules/agents/tools/

### 9.3 示例代码仓库

可参考以下开源项目：
- **SeeAct** - Multimodal browser agent
- **WebVoyager** - Web navigation agent
- **Mind2Web** - Generalist web agent

---

## 10. 审阅检查清单

### 技术方案
- [ ] 架构设计是否合理？
- [ ] 技术选型是否符合项目需求？
- [ ] 是否考虑了可扩展性和可维护性？

### 安全性
- [ ] SSRF防护是否充分？
- [ ] 是否有资源滥用防护？
- [ ] 敏感信息处理是否安全？

### 性能
- [ ] 资源占用是否可控？
- [ ] 并发处理能力是否满足需求？
- [ ] 是否有性能优化方案？

### 实施
- [ ] 实施步骤是否清晰？
- [ ] 工作量估算是否合理？
- [ ] 是否有风险应对预案？

### 文档
- [ ] 文档是否完整？
- [ ] 示例代码是否可运行？
- [ ] 是否便于团队理解和实施？

---

**文档版本**: v1.0
**创建日期**: 2025-12-23
**作者**: Claude Code
**审阅状态**: 待审阅
