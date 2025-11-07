"""
FineReport工具包
提供FineReport报表登录和抽样功能
"""
import os
import time
import asyncio
import json
import uuid
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


async def _download_excel(page) -> str:
    """
    下载Excel文件并返回文件路径

    Args:
        page: Playwright页面对象

    Returns:
        Excel文件路径，失败返回None
    """
    try:
        download_path = os.path.abspath(settings.fine_report_browser_download_path)

        async with page.expect_download(timeout=settings.fine_report_download_timeout) as download_info:
            # 执行JavaScript触发Excel导出
            logger.info("执行JavaScript导出Excel")
            await page.evaluate('_g().exportReportToExcel("simple")')
            logger.info("已执行导出命令")

        # 等待下载完成
        logger.info("等待文件下载完成")
        download = await download_info.value

        # 使用UUID生成唯一文件名
        file_name = f"report_{uuid.uuid4().hex[:8]}.xlsx"
        file_path = os.path.join(download_path, file_name)

        await download.save_as(file_path)
        logger.info(f"文件已下载到: {file_path}")

        return file_path

    except Exception as e:
        logger.error(f"下载Excel文件失败: {e}")
        return None


async def _check_fine_login(page) -> bool:
    """
    登录FineReport系统（内部使用，不暴露给大模型）

    Args:
        page: 当前的Playwright Page对象

    Returns:
        是否登录成功
    """
    if not settings.fine_report_user_name or not settings.fine_report_password:
        logger.error("FineReport用户名或密码未配置")
        return False

    try:
        # 检查当前是否已经在登录页面
        current_url = page.url
        if "login" in current_url.lower():
            # 如果不在登录页面，先跳转到登录页面
            logger.info("检测到需要登录，开始执行登录流程")
        
            # 填写登录信息
            logger.debug("填写登录表单")
            await page.fill('input[type="text"]', settings.fine_report_user_name)
            await page.fill('input[type="password"]', settings.fine_report_password)

            # 点击登录按钮
            logger.debug("点击登录按钮")
            await page.click('div[class*="login-button"]')

            # 等待登录完成，等待跳转到系统主页
            logger.info("等待登录完成...")
            try:
                await page.wait_for_url("**/decision/**", timeout=30000)
                await page.wait_for_timeout(1000)
                logger.info("登录成功，已跳转到系统主页")
                return True
            except Exception as wait_error:
                # 如果等待超时，检查当前URL是否已经是有效页面
                current_url = page.url
                if "decision" in current_url or "report" in current_url:
                    logger.info(f"登录成功，当前页面: {current_url}")
                    return True
                else:
                    logger.error(f"登录超时或失败，当前URL: {current_url}")
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
        # 第一步：直接访问报表页面
        logger.info("直接访问报表页面")
        session = await _get_browser_session()
        page = await session.new_page()

        # 访问报表URL
        await page.goto(report_url, wait_until="networkidle")
        logger.info(f"已访问报表页面: {report_url}")

        # 等待页面加载完成
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(500)

        # 第二步：确保登录状态
        await _check_fine_login(page)
        
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

        # 第四步：下载Excel文件
        file_path = await _download_excel(page)
        if not file_path:
            await page.close()
            await _return_browser_session(session)
            return '{"success": false, "error": "Excel下载失败"}'

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


async def filter_report_and_get_data(report_url: str, control_operations: List[dict], return_locators: dict = None, return_name: str = None) -> str:
    """
    执行FineReport报表的控件操作，并返回数据内容

    Args:
        report_url: FineReport报表的完整URL
        control_operations: 控件操作列表，格式: [{'type': 'text', 'name': 'widget_name', 'value': 'new_value'}, ...]
        return_locators: 返回数据定位器，格式: {'key': 'A5'} 或 {'key': {'find_column': 'A', 'find_value': '汉口支行', 'return_column': 'C'}}
        return_name: 返回结果的键名

    Returns:
        操作结果的描述字符串，或包含数据的字典
    """
    logger.info(f"开始执行控件操作: {report_url}, 操作数量: {len(control_operations)}")

    try:
        # 第一步：访问报表页面
        logger.info("访问报表页面")
        session = await _get_browser_session()
        page = await session.new_page()

        # 访问报表URL
        await page.goto(report_url, wait_until="networkidle")
        logger.info(f"已访问报表页面: {report_url}")

        # 等待页面加载完成
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(500)

        # 第二步：检查是否需要登录
        await _check_fine_login(page)

        # 第三步：执行控件操作
        logger.info("开始执行控件操作")

        for operation in control_operations:
            try:
                widget_name = operation.get('name')
                widget_value = operation.get('value')
                widget_type = operation.get('type', 'text')

                if not widget_name:
                    logger.warning(f"操作缺少控件名称: {operation}")
                    continue
                await page.evaluate(f'_g().getParameterContainer().getWidgetByName("{widget_name}").setValue("{widget_value}")')

                logger.debug(f"控件 {widget_name} 操作成功")

            except Exception as op_error:
                error_msg = f"控件 {operation.get('name', 'unknown')} 操作失败: {str(op_error)}"
                logger.error(error_msg)

        # 第四步：提交参数并刷新页面
        logger.info("提交参数并刷新页面")
        try:
            await page.evaluate('_g().parameterCommit()')
            logger.info("参数提交完成，等待页面刷新")

            # 等待页面刷新完成
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)

            logger.info("页面刷新完成")

        except Exception as commit_error:
            error_msg = f"参数提交失败: {str(commit_error)}"
            logger.error(error_msg)

        # 第五步：如果需要返回数据，下载Excel并提取数据
        if return_locators and return_name:
            logger.info("下载Excel并提取数据")
            file_path = await _download_excel(page)

            if file_path:
                # 提取数据
                extracted_data = extract_data_from_excel(file_path, return_locators)
                result = {return_name: extracted_data}
            else:
                result = {}

            await page.close()
            await _return_browser_session(session)

            logger.info("控件操作和数据提取完成")
            return result
        else:
            await page.close()
            await _return_browser_session(session)

            logger.info("控件操作执行完成")
            return {}

    except Exception as e:
        logger.error(f"执行控件操作时发生错误: {e}")
        return f"# 错误\n执行控件操作失败: {str(e)}"


def extract_data_from_excel(excel_path: str, locators: dict) -> dict:
    """
    从Excel中提取数据

    Args:
        excel_path: Excel文件路径
        locators: 定位器字典

    Returns:
        提取的数据字典
    """
    import pandas as pd

    df = pd.read_excel(excel_path, header=None)
    result = {}

    for key, locator in locators.items():
        if isinstance(locator, str):
            # 固定坐标定位
            col = locator[0].upper()
            row = int(locator[1:]) - 1  # Excel行号从1开始，DataFrame从0开始
            col_idx = ord(col) - ord('A')

            if row < len(df) and col_idx < len(df.columns):
                value = df.iloc[row, col_idx]
                result[key] = str(value) if pd.notna(value) else ""
            else:
                result[key] = ""

        elif isinstance(locator, dict):
            # 条件查找定位
            find_col = locator['find_column'].upper()
            find_val = locator['find_value']
            return_col = locator['return_column'].upper()

            find_col_idx = ord(find_col) - ord('A')
            return_col_idx = ord(return_col) - ord('A')

            if find_col_idx < len(df.columns) and return_col_idx < len(df.columns):
                for row_idx in range(len(df)):
                    cell_value = str(df.iloc[row_idx, find_col_idx])
                    if find_val in cell_value:
                        value = df.iloc[row_idx, return_col_idx]
                        result[key] = str(value) if pd.notna(value) else ""
                        break
                else:
                    result[key] = ""
            else:
                result[key] = ""

    return result


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


def filter_report_and_get_data_sync(report_url: str, control_operations: List[dict], return_locators: dict = None, return_name: str = None) -> str:
    """
    同步版本执行控件操作并提取数据（供Agent工具调用）

    Args:
        report_url: FineReport报表的完整URL
        control_operations: 控件操作列表
        return_locators: 返回数据定位器，格式: {'key': 'A5'} 或 {'key': {'find_column': 'A', 'find_value': '汉口支行', 'return_column': 'C'}}
        return_name: 返回结果的键名

    Returns:
        操作结果的描述字符串，或包含数据的字典
    """
    # 在新的事件循环中运行异步函数
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(filter_report_and_get_data(report_url, control_operations, return_locators, return_name))
    finally:
        loop.close()


# 导出给Agent使用的工具函数
__all__ = ['get_report_sample_sync', 'filter_report_and_get_data_sync']


if __name__ == '__main__':
    # 测试控件操作功能
    test_url = "http://localhost:8075/webroot/decision/view/report?viewlet=WorkBook1.cpt"

    # 测试1：基本控件操作
    # p = [{'type': 'text', 'name': 'zzz', 'value': '新的值'}]
    # result = execute_control_operations_sync(test_url, p)
    # print(result)

    # 测试2：控件操作 + 数据提取
    p = [{'type': 'text', 'name': 'zzz', 'value': '新的值'}]
    # locators = {'bal': 'C3', 'avg_bal': 'D3'}
    locators = {'bal': {'find_column': 'C', 'find_value': '烦烦烦', 'return_column': 'E'}}
    result = operate_controls_and_extract_data_sync(test_url, p, locators, '2025-11-11')
    print(result)