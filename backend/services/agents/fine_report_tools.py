"""
FineReport工具包
提供FineReport报表登录和抽样功能
"""
import os
import time
import asyncio
import json
from typing import Optional, List
from playwright.async_api import async_playwright, Browser, BrowserContext
from loguru import logger
from markitdown import DocumentConverterResult, MarkItDown
import pandas as pd

from utils.config import settings
from utils.excel_parser import ensure_download_dir


# 全局浏览器实例（复用）
_browser_instance: Optional[Browser] = None


class BrowserSessionPool:
    """浏览器会话池管理器"""

    def __init__(self, pool_size: int = 3):
        self.pool_size = pool_size
        self.available_sessions: List[BrowserContext] = []
        self.active_sessions: dict = {}
        self._lock = asyncio.Lock()

    async def get_session(self) -> BrowserContext:
        """获取可用会话"""
        async with self._lock:
            # 优先复用现有会话
            if self.available_sessions:
                session = self.available_sessions.pop()
                logger.debug("复用现有浏览器会话")
                return session

            # 创建新会话
            if not _browser_instance:
                await self._init_browser()

            session = await _browser_instance.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            logger.debug("创建新的浏览器会话")
            return session

    async def return_session(self, session: BrowserContext):
        """归还会话到池中"""
        async with self._lock:
            if len(self.available_sessions) < self.pool_size:
                self.available_sessions.append(session)
                logger.debug("会话已归还到池中")
            else:
                await session.close()
                logger.debug("会话池已满，关闭会话")

    async def _init_browser(self):
        """初始化浏览器实例"""
        global _browser_instance
        if _browser_instance is None:
            logger.info("启动Playwright浏览器实例")
            playwright = await async_playwright().start()

            _browser_instance = await playwright.chromium.launch(
                headless=settings.fine_report_browser_headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )

    async def cleanup_all(self):
        """清理所有会话和浏览器实例"""
        global _browser_instance

        async with self._lock:
            # 关闭所有活跃会话
            for session in list(self.active_sessions.values()):
                try:
                    await session.close()
                except:
                    pass

            # 关闭所有可用会话
            for session in self.available_sessions:
                try:
                    await session.close()
                except:
                    pass

            self.available_sessions.clear()
            self.active_sessions.clear()

            # 关闭浏览器实例
            if _browser_instance:
                await _browser_instance.close()
                _browser_instance = None


# 全局会话池实例
_session_pool = BrowserSessionPool()


async def _get_browser_session() -> BrowserContext:
    """从会话池获取浏览器会话"""
    return await _session_pool.get_session()


async def _return_browser_session(session: BrowserContext):
    """归还浏览器会话到池中"""
    await _session_pool.return_session(session)


async def _login_to_fine_report() -> bool:
    """
    登录FineReport系统（内部使用，不暴露给大模型）

    Returns:
        是否登录成功
    """
    if not settings.fine_report_user_name or not settings.fine_report_password:
        logger.error("FineReport用户名或密码未配置")
        return False

    try:
        logger.info(f"开始登录FineReport系统: {settings.fine_report_login_url}")

        session = await _get_browser_session()
        page = await session.new_page()

        # 访问登录页面
        await page.goto(settings.fine_report_login_url, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # 检查是否已经登录
        current_url = page.url
        if "login" not in current_url.lower():
            logger.info("已经处于登录状态")
            await page.close()
            await _return_browser_session(session)
            return True

        # 填写登录信息
        logger.debug("填写登录表单")
        await page.fill('input[type="text"]', settings.fine_report_user_name)
        await page.fill('input[type="password"]', settings.fine_report_password)

        # 点击登录按钮
        logger.debug("点击登录按钮")
        await page.click('div[class*="login-button"]')

        # 等待登录完成
        await page.wait_for_url("**/decision/**", timeout=30000)
        await page.wait_for_timeout(1000)

        current_url = page.url
        if "decision" in current_url:
            logger.info("FineReport登录成功")
            await page.close()
            await _return_browser_session(session)
            return True
        else:
            logger.error(f"登录失败，当前URL: {current_url}")
            await page.close()
            await _return_browser_session(session)
            return False

    except Exception as e:
        logger.error(f"登录过程中发生错误: {e}")
        return False


async def get_report_sample(report_url: str) -> str:
    """
    获取FineReport报表的抽样信息（控件清单+页面内容）

    Args:
        report_url: FineReport报表的完整URL

    Returns:
        Markdown格式的抽样信息字符串
    """
    logger.info(f"开始获取报表抽样信息: {report_url}")

    try:
        # 第一步：确保已登录
        logger.info("检查登录状态")
        if not await _login_to_fine_report():
            error_msg = "FineReport登录失败，无法获取报表信息"
            logger.error(error_msg)
            return f"# 错误\n{error_msg}"

        # 第二步：访问报表页面
        logger.info("访问报表页面")
        session = await _get_browser_session()
        page = await session.new_page()

        # 访问报表URL
        await page.goto(report_url, wait_until="networkidle")
        logger.info(f"已访问报表页面: {report_url}")

        # 等待页面加载完成
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)

        # 第三步：获取控件信息
        logger.info("获取参数面板控件信息")
        widgets_script = """
        () => {
            const container = _g().getParameterContainer();
            const widgets = container.options.items || [];

            // 提取每个widget的关键字段
            const extractedWidgets = widgets.map(widget => {
                // 处理value字段
                let value = widget.value || '';
                if (typeof value === 'object' && value.date_milliseconds) {
                    value = `DATE:${value.date_milliseconds}`;
                }

                return {
                    控件名: widget.widgetName || '',
                    是否禁用: widget.disabled || false,
                    是否可见: widget.invisible || false,
                    控件值: value,
                    x坐标: widget.x || 0,
                    y坐标: widget.y || 0,
                    控件类型: widget.type || ''
                };
            });

            return {
                success: true,
                containerName: container.options.widgetName || 'PARA',
                totalWidgets: widgets.length,
                widgets: extractedWidgets
            };
        }
        """

        widgets_result = await page.evaluate(widgets_script)

        # 第四步：获取页面基本数据
        download_path = os.path.abspath(settings.fine_report_browser_download_path)
        
        async with page.expect_download(timeout=settings.fine_report_download_timeout) as download_info:
            # 执行JavaScript触发Excel导出
            logger.info("执行JavaScript导出Excel")
            try:
                await page.evaluate('_g().exportReportToExcel("simple")')
                logger.info("已执行导出命令")
            except Exception as js_error:
                logger.error(f"执行导出JavaScript失败: {js_error}")
                await page.close()
                return '{"success": false, "error": "执行导出命令失败: ' + str(js_error) + '"}'

        # 等待下载完成
        logger.info("等待文件下载完成")
        download = await download_info.value

        # 保存下载的文件
        file_name = download.suggested_filename or f"report_{int(time.time())}.xlsx"
        file_path = os.path.join(download_path, file_name)

        await download.save_as(file_path)
        logger.info(f"文件已下载到: {file_path}")

        # 第三步：解析Excel文件
        logger.info("开始解析Excel文件")
        md = MarkItDown()
        sample_page_info = md.convert(file_path)


        # 关闭页面，归还会话
        await page.close()
        await _return_browser_session(session)

        # 第五步：生成Markdown格式的报告
        markdown_report = _generate_markdown_report(report_url, widgets_result, sample_page_info)

        logger.info("报表抽样信息获取完成")
        return markdown_report

    except Exception as e:
        logger.error(f"获取报表抽样信息时发生错误: {e}")
        return f"# 错误\n获取报表抽样信息失败: {str(e)}"


def _generate_markdown_report(report_url: str, widgets_result: dict, page_info: DocumentConverterResult) -> str:
    """生成Markdown格式的抽样报告"""

    # 添加控件信息
    df = pd.DataFrame(widgets_result.get('widgets'))
    widgets_result_table = df.to_markdown(index=False)

    markdown_lines = [
        "# FineReport报表抽样信息",
        "",
        "## 基本信息",
        f"- **报表URL**: {report_url}",
        "",
        "- **控件信息**："
        "",
        f"{widgets_result_table}",
        "",
        "- **页面信息**："
        "",
        f"{page_info}"
    ]

    return "\n".join(markdown_lines)


def get_report_sample_sync(report_url: str) -> str:
    """
    同步版本获取报表抽样信息（供Agent工具调用）

    Args:
        report_url: FineReport报表的完整URL

    Returns:
        Markdown格式的抽样信息字符串
    """
    # 在新的事件循环中运行异步函数
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(get_report_sample(report_url))
    finally:
        loop.close()


# 导出给Agent使用的工具函数
__all__ = ['get_report_sample_sync']


if __name__ == '__main__':
    # 测试报表抽样功能
    test_url = "http://localhost:8075/webroot/decision/view/report?viewlet=WorkBook1.cpt"
    result = get_report_sample_sync(test_url)
    print(result)