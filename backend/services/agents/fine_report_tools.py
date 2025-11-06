"""
FineReport工具包
提供FineReport报表登录和下载功能
"""
import os
import time
import asyncio
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger

from utils.config import get_settings
from utils.excel_parser import parse_excel_file, clean_excel_file, ensure_download_dir


# 全局浏览器实例（复用）
_browser_instance: Optional[Browser] = None
_browser_context: Optional[BrowserContext] = None


async def _get_browser_context() -> BrowserContext:
    """获取浏览器上下文（复用实例）"""
    global _browser_instance, _browser_context

    settings = get_settings()

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
    settings = get_settings()

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
    settings = get_settings()

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
            result = parse_excel_file(file_path)

            # 添加处理时间信息
            if result.get("success"):
                processing_time = time.time() - start_time
                result["metadata"]["processing_time"] = round(processing_time, 2)
                logger.info(f"Excel解析完成，耗时: {processing_time:.2f}秒")

            # 转换为JSON字符串
            import json
            result_json = json.dumps(result, ensure_ascii=False, indent=2)

            # 清理临时文件
            # if clean_excel_file(file_path):
                # logger.info("已清理临时Excel文件")
            
            logger.info(f"FineReport报表处理完成 {result_json}")

            return result_json

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


# 导出给Agent使用的工具函数
__all__ = ['download_fine_report_sync']

if __name__ == '__main__':
    download_fine_report_sync("http://localhost:8075/webroot/decision/view/report?viewlet=WorkBook1.cpt")