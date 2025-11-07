"""
FineReport工具包
提供FineReport报表登录和下载功能
"""
import os
import time
import asyncio
import json
from typing import Optional, List
from playwright.async_api import async_playwright, Browser, BrowserContext
from loguru import logger
from markitdown import MarkItDown

from utils.config import settings
from utils.excel_parser import ensure_download_dir


# 全局浏览器实例（复用）
_browser_instance: Optional[Browser] = None
_browser_context: Optional[BrowserContext] = None


async def _get_browser_context() -> BrowserContext:
    """获取浏览器上下文（复用实例）"""
    global _browser_instance, _browser_context

    if _browser_instance is None or _browser_context is None:
        logger.info("启动Playwright浏览器实例")
        playwright = await async_playwright().start()

        _browser_instance = await playwright.chromium.launch(
            headless=settings.fine_report_browser_headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']  # Linux服务器兼容
        )

        # 设置下载路径
        download_path = os.path.abspath(settings.fine_report_browser_download_path)
        ensure_download_dir(download_path)

        _browser_context = await _browser_instance.new_context(
            accept_downloads=True,
            java_script_enabled=True,
            viewport={'width': 1920, 'height': 1080}
        )

        logger.info(f"浏览器实例已启动，下载目录: {download_path}")

    return _browser_context


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

        context = await _get_browser_context()
        page = await context.new_page()

        # 设置页面超时
        page.set_default_timeout(settings.fine_report_browser_timeout)

        # 访问登录页面
        await page.goto(settings.fine_report_login_url)
        logger.info(f"已访问登录页面: {settings.fine_report_login_url}")

        # 等待页面加载
        await page.wait_for_load_state('networkidle')

        # 填写用户名
        logger.debug("查找用户名输入框")
        username_input = await page.wait_for_selector('input[type="text"]', timeout=settings.fine_report_browser_wait_timeout)
        await username_input.fill(settings.fine_report_user_name)
        logger.debug("已填写用户名")

        # 填写密码
        logger.debug("查找密码输入框")
        password_input = await page.wait_for_selector('input[type="password"]', timeout=settings.fine_report_browser_wait_timeout)
        await password_input.fill(settings.fine_report_password)
        logger.debug("已填写密码")

        # 查找并点击登录按钮
        logger.debug("查找登录按钮")
        login_button = await page.wait_for_selector('div[class*="login-button"]', timeout=settings.fine_report_browser_wait_timeout)
        await login_button.click()
        logger.info("已点击登录按钮")

        # 等待登录完成（等待页面跳转或内容变化）
        try:
            logger.debug("等待登录完成...")

            # 等待URL发生变化（不再包含login字样）
            await page.wait_for_function(
                "() => !window.location.href.toLowerCase().includes('login')",
                timeout=15000
            )


            # 检查当前URL
            current_url = page.url
            logger.info(f"登录后页面URL: {current_url}")

            logger.info("FineReport登录成功")
            await page.close()
            return True

        except Exception as wait_error:
            logger.error(f"等待登录完成超时: {wait_error} 登录失败")
            await page.close()
            return False

    except Exception as e:
        logger.error(f"登录FineReport失败: {e}")
        return False


async def download_fine_report(report_url: str) -> str:
    """
    下载FineReport报表并解析为结构化数据

    Args:
        report_url: FineReport报表的完整URL

    Returns:
        JSON格式的结构化数据字符串
    """
    logger.info(f"开始下载FineReport报表: {report_url}")
    try:
        # 第一步：确保已登录
        logger.info("检查登录状态")
        if not await _login_to_fine_report():
            error_msg = "FineReport登录失败，无法下载报表"
            logger.error(error_msg)
            return '{"success": false, "error": "' + error_msg + '"}'

        # 第二步：访问报表页面
        logger.info("访问报表页面")
        context = await _get_browser_context()
        page = await context.new_page()

        # 启用下载拦截
        logger.debug("设置下载拦截")
        download_path = os.path.abspath(settings.fine_report_browser_download_path)

        async with page.expect_download(timeout=settings.fine_report_download_timeout) as download_info:
            # 访问报表URL
            await page.goto(report_url)
            logger.info(f"已访问报表页面: {report_url}")

            # 等待页面加载完成
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)  # 额外等待确保报表完全加载

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

        # 关闭页面
        await page.close()

        # 第三步：解析Excel文件
        logger.info("开始解析Excel文件")
        start_time = time.time()

        try:
            md = MarkItDown()
            result = md.convert(file_path)   # 返回 Markdown 文本

            # 清理临时文件
            # if clean_excel_file(file_path):
                # logger.info("已清理临时Excel文件")
            
            logger.info(f"FineReport报表处理完成 {result}")

            return {
                "success": True,
                "error": "",
                "data": result
            }

        except Exception as parse_error:
            logger.error(f"解析Excel文件失败: {parse_error}")
            error_result = {
                "success": False,
                "error": f"Excel解析失败: {str(parse_error)}",
                "data": None
            }
            return json.dumps(error_result, ensure_ascii=False)

    except Exception as e:
        logger.error(f"下载FineReport报表失败: {e}")
        error_result = {
            "success": False,
            "error": f"下载失败: {str(e)}",
            "data": None
        }
        import json
        return json.dumps(error_result, ensure_ascii=False)


async def cleanup_browser_resources():
    """
    清理浏览器资源（内部使用）
    """
    global _browser_instance, _browser_context

    try:
        if _browser_context:
            await _browser_context.close()
            _browser_context = None
            logger.info("浏览器上下文已关闭")

        if _browser_instance:
            await _browser_instance.close()
            _browser_instance = None
            logger.info("浏览器实例已关闭")

    except Exception as e:
        logger.error(f"清理浏览器资源失败: {e}")


def download_fine_report_sync(report_url: str) -> str:
    """
    同步版本的下载函数（供Agent工具调用）

    Args:
        report_url: FineReport报表的完整URL

    Returns:
        JSON格式的结构化数据字符串
    """
    # 在新的事件循环中运行异步函数
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(download_fine_report(report_url))
    finally:
        loop.close()


async def download_multiple_reports(
    report_url: str,
    parameter_values: List[str],
    parameter_name: str = "date"
) -> str:
    """
    批量下载FineReport报表（支持多个参数值）

    Args:
        report_url: FineReport报表的完整URL
        parameter_values: 参数值列表（如日期列表）
        parameter_name: 参数名称（默认为"date"）

    Returns:
        JSON格式的批量结果字符串
    """
    logger.info(f"开始批量下载报表: {report_url}")
    logger.info(f"参数名称: {parameter_name}, 参数值数量: {len(parameter_values)}")

    if not parameter_values:
        error_result = {}
        return json.dumps(error_result, ensure_ascii=False)

    try:
        # 第一步：确保已登录
        logger.info("检查登录状态")
        if not await _login_to_fine_report():
            error_msg = "FineReport登录失败，无法批量下载报表"
            logger.error(error_msg)
            error_result = {}
            return json.dumps(error_result, ensure_ascii=False)

        # 第二步：首次访问报表，验证可访问性
        logger.info("首次访问报表，验证页面可访问性")
        context = await _get_browser_context()

        # 获取并解析 pmeter-container 的HTML内容
        logger.info("获取 pmeter-container 结构化信息")
        try:
            page = await context.new_page()
            await page.goto(report_url, wait_until="networkidle")

            # 等待页面加载完成
            await page.wait_for_timeout(500)

            # 使用FineReport内置API获取参数面板widgets信息
            logger.info("使用FineReport API获取参数面板widgets信息")

            # 执行FineReport内置API，精确提取widgets的关键字段
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

            # 执行获取widgets的脚本
            widgets_result = await page.evaluate(widgets_script)

            # 打印widgets信息到日志
            logger.info("FineReport参数面板widgets信息:")

            # 直接序列化新的简洁数据结构
            try:
                widgets_json = json.dumps(widgets_result, ensure_ascii=False, indent=2)
                logger.info(widgets_json)
            except Exception as e:
                logger.error(f"序列化widgets信息失败: {e}")
                logger.info(f"返回结果: {widgets_result}")

            await page.close()

        except Exception as e:
            logger.error(f"获取 pmeter-container 结构化信息时发生错误: {e}")

        return {}

    except Exception as e:
        logger.error(f"批量下载报表时发生错误: {e}")
        error_result = {}
        return json.dumps(error_result, ensure_ascii=False)


def download_multiple_reports_sync(
    report_url: str,
    parameter_values: List[str],
    parameter_name: str = "date"
) -> str:
    """
    同步版本的批量下载函数（供Agent工具调用）

    Args:
        report_url: FineReport报表的完整URL
        parameter_values: 参数值列表（如日期列表）
        parameter_name: 参数名称（默认为"date"）

    Returns:
        JSON格式的批量结果字符串
    """
    # 在新的事件循环中运行异步函数
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(
            download_multiple_reports(report_url, parameter_values, parameter_name)
        )
    finally:
        loop.close()


# 导出给Agent使用的工具函数
__all__ = ['download_fine_report_sync', 'download_multiple_reports_sync']

if __name__ == '__main__':
    # 测试单个报表下载
    # download_fine_report_sync("http://localhost:8075/webroot/decision/view/report?viewlet=WorkBook1.cpt")

    # 测试批量报表下载
    test_dates = ["2024-01-31", "2024-02-29", "2024-03-31"]
    result = download_multiple_reports_sync(
        "http://localhost:8075/webroot/decision/view/report?viewlet=WorkBook1.cpt",
        test_dates,
        "date"
    )
    print(result)