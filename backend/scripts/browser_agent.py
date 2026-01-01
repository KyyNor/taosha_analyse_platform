#!/usr/bin/env python3
"""
Browser Agent 独立调试脚本

使用方法:
    python scripts/browser_agent.py "访问百度并搜索Python"
    python scripts/browser_agent.py "访问 https://www.python.org 查看最新版本"
    python scripts/browser_agent.py "在GitHub搜索langchain" --max-steps 20
    python scripts/browser_agent.py "访问百度首页" --screenshot

启动 Browserless (首次使用):
    docker run -d -p 3001:3000 --name browserless --shm-size 2gb browserless/chrome:latest
"""

import asyncio
import argparse
from pathlib import Path
from datetime import datetime

from browser_use import Agent
from browser_use.browser.session import BrowserSession
from browser_use.llm.openai.chat import ChatOpenAI


# ==================== 配置 ====================

BROWSERLESS_URL = "ws://localhost:3001"
LLM_MODEL = "kimi-k2-0905-preview"
LLM_BASE_URL = "https://api.moonshot.cn/v1"
LLM_API_KEY = "sk-vBFsOtdf68LR9SGmzfiEQFgl4CVvIreOu8FHjDACH7dMn3i4"

SCREENSHOT_DIR = Path("./screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 核心函数 ====================

async def run_browser_task(task: str, max_steps: int = 15, screenshot: bool = False):
    """运行浏览器任务"""

    # 初始化 LLM
    llm = ChatOpenAI(
        model=LLM_MODEL,
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        temperature=0.7,

        # Moonshot 兼容性配置
        dont_force_structured_output=True,  # 禁用 response_format，避免 Moonshot API 400 错误
        add_schema_to_system_prompt=True,   # 通过系统提示引导 JSON 输出
    )

    # 初始化浏览器会话
    browser_session = BrowserSession(cdp_url=BROWSERLESS_URL)

    # 创建 Agent
    agent = Agent(
        task=task,
        llm=llm,
        browser_session=browser_session,
        use_vision=False,  # 默认不使用视觉模式
        max_actions_per_step=10,
    )

    print(f"\n🤖 任务: {task}")
    print(f"📊 最大步数: {max_steps}")
    print(f"🔧 模型: {LLM_MODEL}")
    print("="*60)

    try:
        # 执行任务
        history = await agent.run(max_steps=max_steps)
        result = history.final_result() if hasattr(history, 'final_result') else str(history)

        print("\n✅ 任务完成!")
        print(f"📝 结果:\n{result}")

        # 截图
        if screenshot:
            await take_screenshot(browser_session)

        return result

    except Exception as e:
        print(f"\n❌ 任务失败: {e}")
        raise


async def take_screenshot(browser_session: BrowserSession):
    """截取当前页面截图"""
    try:
        if browser_session.browser and browser_session.browser.contexts:
            context = browser_session.browser.contexts[0]
            if context.pages:
                page = context.pages[0]

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = SCREENSHOT_DIR / f"screenshot_{timestamp}.png"

                await page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"\n📸 截图已保存: {screenshot_path}")

    except Exception as e:
        print(f"\n⚠️  截图失败: {e}")


# ==================== 命令行入口 ====================

def main():
    parser = argparse.ArgumentParser(
        description="Browser Agent - 自然语言控制浏览器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/browser_agent.py "访问百度并搜索Python"
  python scripts/browser_agent.py "访问 https://www.python.org 查看最新版本"
  python scripts/browser_agent.py "在GitHub搜索langchain" --max-steps 20
  python scripts/browser_agent.py "访问百度首页" --screenshot
        """
    )

    parser.add_argument(
        "task",
        help="任务描述 (自然语言)"
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=15,
        help="最大执行步数 (默认: 15)"
    )

    parser.add_argument(
        "--screenshot",
        action="store_true",
        help="任务完成后截图"
    )

    args = parser.parse_args()

    # 运行任务
    asyncio.run(run_browser_task(
        task=args.task,
        max_steps=args.max_steps,
        screenshot=args.screenshot
    ))


if __name__ == "__main__":
    main()
