"""
FineReport工具包
提供FineReport报表登录和抽样功能
"""
import os
import asyncio
import json
import uuid
import sys
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger
from markitdown import DocumentConverterResult, MarkItDown
import pandas as pd

from utils.config import settings
from utils.excel_parser import ensure_download_dir


# 全局异步浏览器实例（每个worker进程一个）
_async_browser: Optional[Browser] = None
_async_context: Optional[BrowserContext] = None  # 共享登录会话的上下文


async def get_async_browser_context() -> BrowserContext:
    """获取全局异步 BrowserContext 实例，共享登录会话"""
    global _async_browser, _async_context

    if _async_context is None:
        logger.info("启动异步 Playwright 浏览器实例")
        try:
            playwright = await async_playwright().start()
            _async_browser = await playwright.chromium.launch(
                headless=settings.fine_report_browser_headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )

            # 创建共享的BrowserContext，用于session共享
            _async_context = await _async_browser.new_context()

            # 执行一次性登录
            await _login_once_async(_async_context)

            logger.info("异步 Playwright 浏览器实例已启动，登录会话已建立")
        except Exception as e:
            logger.error(f"启动异步浏览器失败: {e}", exc_info=True)
            raise

    return _async_context


async def _login_once_async(context: BrowserContext):
    """在BrowserContext级别执行一次性登录，所有Page共享会话"""
    logger.info("执行一次性登录建立共享会话")
    page = None
    try:
        page = await context.new_page()
        # 访问任意报表URL触发登录
        await page.goto("http://localhost:8075/webroot/decision", wait_until="networkidle")

        # 检查是否需要登录
        current_url = page.url
        if "login" in current_url.lower():
            logger.info("检测到需要登录，开始执行登录流程")

            # 填写登录信息
            if not settings.fine_report_user_name or not settings.fine_report_password:
                logger.error("FineReport用户名或密码未配置")
                return False

            await page.fill('input[type="text"]', settings.fine_report_user_name)
            await page.fill('input[type="password"]', settings.fine_report_password)
            await page.click('div[class*="login-button"]')

            # 等待登录完成
            try:
                await page.wait_for_url("**/decision/**", timeout=30000)
                await page.wait_for_timeout(1000)
                logger.info("一次性登录成功，会话已建立")
                return True
            except Exception:
                current_url = page.url
                if "decision" in current_url or "report" in current_url:
                    logger.info("登录成功，会话已建立")
                    return True
                else:
                    logger.error(f"登录失败，当前URL: {current_url}")
                    return False

        logger.info("无需登录，会话已就绪")
        return True

    except Exception as e:
        logger.error(f"一次性登录失败: {e}")
        return False
    finally:
        if page:
            await page.close()


async def cleanup_async_browser():
    """清理异步浏览器资源"""
    global _async_browser, _async_context
    if _async_context:
        try:
            await _async_context.close()
            logger.info("BrowserContext 已关闭")
        except Exception as e:
            logger.warning(f"关闭 BrowserContext 失败: {e}")
        _async_context = None

    if _async_browser:
        try:
            await _async_browser.close()
            logger.info("异步浏览器实例已关闭")
        except Exception as e:
            logger.warning(f"关闭异步浏览器实例失败: {e}")
        _async_browser = None


def _cleanup_browser_sync():
    """同步清理浏览器"""
    global _browser_instance
    if _browser_instance:
        try:
            logger.info("关闭 Playwright 浏览器实例")
            _browser_instance.close()
            _browser_instance = None
            logger.info("Playwright 浏览器实例已关闭")
        except Exception as e:
            logger.warning(f"关闭浏览器实例失败: {e}")
            _browser_instance = None


async def _cleanup_browser():
    """清理 Browser 实例（在线程池中运行）"""
    await asyncio.to_thread(_cleanup_browser_sync)


def _download_excel_sync(page: Page) -> str:
    """
    同步下载Excel文件并返回文件路径

    Args:
        page: Playwright页面对象

    Returns:
        Excel文件路径，失败返回None
    """
    try:
        download_path = os.path.abspath(settings.fine_report_browser_download_path)

        with page.expect_download(timeout=settings.fine_report_download_timeout) as download_info:
            # 执行JavaScript触发Excel导出
            logger.info("执行JavaScript导出Excel")
            page.evaluate('_g().exportReportToExcel("simple")')
            logger.info("已执行导出命令")

        # 等待下载完成
        logger.info("等待文件下载完成")
        download = download_info.value

        # 使用UUID生成唯一文件名
        file_name = f"report_{uuid.uuid4().hex[:8]}.xlsx"
        file_path = os.path.join(download_path, file_name)

        download.save_as(file_path)
        logger.info(f"文件已下载到: {file_path}")

        return file_path

    except Exception as e:
        logger.error(f"下载Excel文件失败: {e}")
        return None


def _check_fine_login_sync(page: Page) -> bool:
    """
    同步登录FineReport系统（内部使用，不暴露给大模型）

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
            page.fill('input[type="text"]', settings.fine_report_user_name)
            page.fill('input[type="password"]', settings.fine_report_password)

            # 点击登录按钮
            logger.debug("点击登录按钮")
            page.click('div[class*="login-button"]')

            # 等待登录完成，等待跳转到系统主页
            logger.info("等待登录完成...")
            try:
                page.wait_for_url("**/decision/**", timeout=30000)
                page.wait_for_timeout(2000)
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


def _get_report_sample_sync(report_url: str) -> str:
    """
    同步获取FineReport报表的抽样信息（控件清单+页面内容）

    Args:
        report_url: FineReport报表的完整URL

    Returns:
        Markdown格式的抽样信息字符串
    """
    logger.info(f"开始获取报表抽样信息: {report_url}")

    page = None
    try:
        # 获取全局 Browser 实例
        browser = _browser_instance
        if not browser:
            raise RuntimeError("Browser instance not initialized")

        # 创建新 Page（不复用）
        logger.info("创建新的浏览器页面")
        page = browser.new_page()

        # 访问报表URL
        page.goto(report_url, wait_until="networkidle")
        logger.info(f"已访问报表页面: {report_url}")

        # 等待页面加载完成
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(500)

        # 检查登录状态
        _check_fine_login_sync(page)

        # 获取控件信息
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
                    是否不可见: widget.invisible || false,
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

        widgets_result = page.evaluate(widgets_script)

        # 下载Excel文件
        file_path = _download_excel_sync(page)
        if not file_path:
            return '{"success": false, "error": "Excel下载失败"}'

        # 解析Excel文件
        logger.info("开始解析Excel文件")
        md = MarkItDown()
        sample_page_info = md.convert(file_path)

        # 生成Markdown格式的报告
        markdown_report = _generate_markdown_report(report_url, widgets_result, sample_page_info)

        logger.info("报表抽样信息获取完成")
        return markdown_report

    except Exception as e:
        logger.error(f"获取报表抽样信息时发生错误: {e}")
        return f"# 错误\n获取报表抽样信息失败: {str(e)}"

    finally:
        # 关闭页面
        if page:
            try:
                page.close()
            except Exception as e:
                logger.warning(f"关闭页面失败: {e}")


async def _filter_report_and_get_data_async(context: BrowserContext, report_url: str, control_operations: list, return_locators: dict = None, return_name: str = None) -> dict:
    """
    异步执行FineReport报表的控件操作，并返回数据内容
    使用共享的BrowserContext，避免重复登录

    Args:
        context: 共享的BrowserContext实例
        report_url: FineReport报表的完整URL
        control_operations: 控件操作列表，格式: [{'type': 'text', 'name': 'widget_name', 'value': 'new_value'}, ...]
        return_locators: 返回数据定位器，格式: {'key': 'A5'} 或 {'key': {'find_column': 'A', 'find_value': '汉口支行', 'return_column': 'C'}}
        return_name: 返回结果的键名

    Returns:
        操作结果的描述字符串，或包含数据的字典
    """
    logger.info(f"异步执行控件操作: {report_url}, 操作数量: {len(control_operations)}")

    page = None
    try:
        # 从共享context创建新页面
        logger.info("创建新的浏览器页面（共享会话）")
        page = await context.new_page()

        # 访问报表URL并等待加载完成
        await page.goto(report_url, wait_until="networkidle")
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(500)
        logger.info(f"已访问报表页面: {report_url}")

        # 执行控件操作（无需检查登录，因为context已共享登录会话）
        logger.info("开始执行控件操作")
        for operation in control_operations:
            try:
                widget_name = operation.get('name')
                widget_value = operation.get('value')

                if not widget_name:
                    logger.warning(f"操作缺少控件名称: {operation}")
                    continue
                await page.evaluate(f'_g().getParameterContainer().getWidgetByName("{widget_name}").setValue("{widget_value}")')
                logger.debug(f"控件 {widget_name} 操作成功")

            except Exception as op_error:
                error_msg = f"控件 {operation.get('name', 'unknown')} 操作失败: {str(op_error)}"
                logger.error(error_msg)

        # 提交参数并刷新页面
        logger.info("提交参数并刷新页面")
        try:
            await page.evaluate('_g().parameterCommit()')
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)
            logger.info("页面刷新完成")
        except Exception as commit_error:
            error_msg = f"参数提交失败: {str(commit_error)}"
            logger.error(error_msg)

        # 如果需要返回数据，下载Excel并提取数据
        if return_locators and return_name:
            logger.info("下载Excel并提取数据")

            # 内联异步下载Excel逻辑
            file_path = None
            try:
                download_path = os.path.abspath(settings.fine_report_browser_download_path)

                async with page.expect_download(timeout=settings.fine_report_download_timeout) as download_info:
                    await page.evaluate('_g().exportReportToExcel("simple")')
                    logger.info("已执行导出命令")

                download = await download_info.value
                file_name = f"report_{uuid.uuid4().hex[:8]}.xlsx"
                file_path = os.path.join(download_path, file_name)
                await download.save_as(file_path)
                logger.info(f"文件已下载到: {file_path}")
            except Exception as e:
                logger.error(f"下载Excel文件失败: {e}")

            if file_path:
                extracted_data = extract_data_from_excel(file_path, return_locators)
                result = {return_name: extracted_data}
            else:
                result = {}

            logger.info("控件操作和数据提取完成")
            return result
        else:
            logger.info("控件操作执行完成")
            return {}

    except Exception as e:
        logger.error(f"异步执行控件操作时发生错误: {e}")
        return {"error": f"# 错误\n执行控件操作失败: {str(e)}"}

    finally:
        if page:
            try:
                await page.close()
            except Exception as e:
                logger.warning(f"关闭页面失败: {e}")


async def get_report_sample(report_url: str) -> str:
    """
    获取FineReport报表的抽样信息（控件清单+页面内容）- 异步包装

    Args:
        report_url: FineReport报表的完整URL

    Returns:
        Markdown格式的抽样信息字符串
    """
    return await asyncio.to_thread(_get_report_sample_sync, report_url)


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
        "- **控件信息**：",
        "",
        f"{widgets_result_table}",
        "",
        "- **页面信息**：",
        "",
        f"{page_info}"
    ]

    return "\n".join(markdown_lines)


def _filter_report_and_get_data_sync(report_url: str, control_operations: list, return_locators: dict = None, return_name: str = None) -> dict:
    """
    同步执行FineReport报表的控件操作，并返回数据内容

    Args:
        report_url: FineReport报表的完整URL
        control_operations: 控件操作列表，格式: [{'type': 'text', 'name': 'widget_name', 'value': 'new_value'}, ...]
        return_locators: 返回数据定位器，格式: {'key': 'A5'} 或 {'key': {'find_column': 'A', 'find_value': '汉口支行', 'return_column': 'C'}}
        return_name: 返回结果的键名

    Returns:
        操作结果的描述字符串，或包含数据的字典
    """
    logger.info(f"开始执行控件操作: {report_url}, 操作数量: {len(control_operations)}")

    page = None
    try:
        # 获取全局 Browser 实例
        browser = _browser_instance
        if not browser:
            raise RuntimeError("Browser instance not initialized")

        # 创建新 Page（不复用）
        logger.info("创建新的浏览器页面")
        page = browser.new_page()

        # 访问报表URL
        page.goto(report_url, wait_until="networkidle")
        logger.info(f"已访问报表页面: {report_url}")

        # 等待页面加载完成
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(500)

        # 检查登录状态
        _check_fine_login_sync(page)

        # 执行控件操作
        logger.info("开始执行控件操作")

        for operation in control_operations:
            try:
                widget_name = operation.get('name')
                widget_value = operation.get('value')
                widget_type = operation.get('type', 'text')

                if not widget_name:
                    logger.warning(f"操作缺少控件名称: {operation}")
                    continue
                page.evaluate(f'_g().getParameterContainer().getWidgetByName("{widget_name}").setValue("{widget_value}")')

                logger.debug(f"控件 {widget_name} 操作成功")

            except Exception as op_error:
                error_msg = f"控件 {operation.get('name', 'unknown')} 操作失败: {str(op_error)}"
                logger.error(error_msg)

        # 提交参数并刷新页面
        logger.info("提交参数并刷新页面")
        try:
            page.evaluate('_g().parameterCommit()')
            logger.info("参数提交完成，等待页面刷新")

            # 等待页面刷新完成
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(3000)

            logger.info("页面刷新完成")

        except Exception as commit_error:
            error_msg = f"参数提交失败: {str(commit_error)}"
            logger.error(error_msg)

        # 如果需要返回数据，下载Excel并提取数据
        if return_locators and return_name:
            logger.info("下载Excel并提取数据")
            file_path = _download_excel_sync(page)

            if file_path:
                # 提取数据
                extracted_data = extract_data_from_excel(file_path, return_locators)
                result = {return_name: extracted_data}
            else:
                result = {}

            logger.info("控件操作和数据提取完成")
            return result
        else:
            logger.info("控件操作执行完成")
            return {}

    except Exception as e:
        logger.error(f"执行控件操作时发生错误: {e}")
        return {"error": f"# 错误\n执行控件操作失败: {str(e)}"}

    finally:
        # 关闭页面
        if page:
            try:
                page.close()
            except Exception as e:
                logger.warning(f"关闭页面失败: {e}")


async def filter_report_and_get_data(report_url: str, control_operations: list, return_locators: dict = None, return_name: str = None) -> dict:
    """
    执行FineReport报表的控件操作，并返回数据内容 - 异步包装

    Args:
        report_url: FineReport报表的完整URL
        control_operations: 控件操作列表，格式: [{'type': 'text', 'name': 'widget_name', 'value': 'new_value'}, ...]
        return_locators: 返回数据定位器，格式: {'key': 'A5'} 或 {'key': {'find_column': 'A', 'find_value': '汉口支行', 'return_column': 'C'}}
        return_name: 返回结果的键名

    Returns:
        操作结果的描述字符串，或包含数据的字典
    """
    return await asyncio.to_thread(_filter_report_and_get_data_sync, report_url, control_operations, return_locators, return_name)


def extract_data_from_excel(excel_path: str, locators: dict) -> dict:
    """
    从Excel中提取数据

    Args:
        excel_path: Excel文件路径
        locators: 定位器字典

    Returns:
        提取的数据字典
    """
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
    获取报表样例信息，可以获取报表的控件清单和最新的页面内容，用来了解报表，为后续的batch_filter_report_and_get_data做准备

    Args:
        report_url: FineReport报表的完整URL

    Returns:
        Markdown格式的抽样信息字符串
    """
    return _get_report_sample_sync(report_url)


async def batch_filter_report_and_get_data(report_url: str, control_operations: list, return_locators: dict = None) -> dict:
    """
    异步批量执行FineReport报表的控件操作，支持多个值的真正并发处理
    使用共享的BrowserContext，避免重复登录，每个组合创建独立的Page

    Args:
        report_url: FineReport报表的完整URL
        control_operations: 控件操作列表，value为数组格式，如 [{'type': '控件类型', 'name': '控件名称', 'value': ['控件新值1', '控件新值1']}, ...]
        return_locators: 返回数据定位器，格式: {'key': 'A5'} 或 {'key': {'find_column': '查找的列(如A)', 'find_value': '查找的值(如汉口支行)', 'return_column': '返回的列(如C)'}}

    Returns:
        包含所有批次结果的字典
    """
    logger.info(f"开始异步批量处理控件操作: {report_url}")
    logger.info(f"控件操作列表: {json.dumps(control_operations, ensure_ascii=False)}")
    logger.info(f"返回数据定位器: {json.dumps(return_locators, ensure_ascii=False)}")

    # 第一步：获取共享的BrowserContext
    context = await get_async_browser_context()

    # 第二步：解析所有可能的值组合
    value_combinations = _generate_value_combinations(control_operations)
    total_combinations = len(value_combinations)
    logger.info(f"生成 {total_combinations} 个值组合")

    # 第三步：创建并发任务（每个组合创建独立的Page）
    tasks = []
    for i, combination in enumerate(value_combinations):
        return_name = "_".join([str(op['value']) for op in combination])
        # 创建异步任务，传入共享context
        task = _filter_report_and_get_data_async(context, report_url, combination, return_locators, return_name)
        tasks.append(task)

    # 第四步：真正并发执行所有任务（无并发数限制，发挥最大性能）
    logger.info(f"开始并发执行 {total_combinations} 个值组合")
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 第五步：整理结果
    final_result = {}
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"组合 {i + 1} 执行失败: {result}")
            continue
        if isinstance(result, dict):
            final_result.update(result)

    logger.info(f"异步批量处理完成，成功处理 {len(final_result)} 个结果")
    return final_result


def _generate_value_combinations(control_operations: list) -> list:
    """
    生成所有可能的控件操作值组合

    Args:
        control_operations: 控件操作列表，value为数组

    Returns:
        所有值组合的列表
    """
    if not control_operations:
        return []

    # 转换每个操作的value为数组
    normalized_ops = []
    for op in control_operations:
        if isinstance(op.get('value'), list):
            values = op['value']
        else:
            values = [op.get('value', '')]

        normalized_ops.append({
            'type': op.get('type', 'text'),
            'name': op.get('name'),
            'values': values
        })

    # 生成所有组合
    from itertools import product

    combination_values = list(product(*[op['values'] for op in normalized_ops]))

    combinations = []
    for values in combination_values:
        combination = []
        for i, op in enumerate(normalized_ops):
            combination.append({
                'type': op['type'],
                'name': op['name'],
                'value': values[i]
            })
        combinations.append(combination)

    return combinations


async def _execute_single_combination(report_url: str, control_operations: list, return_locators: dict, index: int) -> dict:
    """
    执行单个值组合的操作

    Args:
        report_url: FineReport报表的完整URL
        control_operations: 单个控件操作组合
        return_locators: 返回数据定位器
        index: 组合索引

    Returns:
        单个组合的结果
    """
    # 生成return_name：拼接所有操作的value
    return_name = "_".join([str(op['value']) for op in control_operations])

    try:
        logger.debug(f"执行组合 {index + 1}: {return_name}")
        _result = await filter_report_and_get_data(report_url, control_operations, return_locators, return_name)
        logger.debug(f"组合 {index + 1} 完成: {return_name}")
        return _result
    except Exception as e:
        logger.error(f"组合 {index + 1} 执行失败: {e}")
        return {return_name: {"error": str(e)}}


def batch_filter_report_and_get_data_sync(report_url: str, control_operations: list, return_locators: dict = None) -> dict:
    """
    批量从帆软报表获取结构化数据

    Args:
        report_url: FineReport报表的完整URL
        control_operations: 控件操作列表，value为数组格式，如 [{'type': '控件类型', 'name': '控件名称', 'value': ['控件新值1', '控件新值1']}, ...]
        return_locators: 返回数据定位器，格式: {'key': 'A5'} 或 {'key': {'find_column': '查找的列(如A)', 'find_value': '查找的值(如汉口支行)', 'return_column': '返回的列(如C)'}}

    Returns:
        包含所有批次结果的字典
    """
    logger.info(f"开始批量处理控件操作: {report_url}")

    # 第一步：解析所有可能的值组合
    value_combinations = _generate_value_combinations(control_operations)
    total_combinations = len(value_combinations)
    logger.info(f"生成 {total_combinations} 个值组合")

    # 第二步：执行所有组合（同步串行执行，避免并发复杂度）
    final_result = {}
    for i, combination in enumerate(value_combinations):
        try:
            logger.debug(f"执行组合 {i + 1}/{total_combinations}")
            return_name = "_".join([str(op['value']) for op in combination])
            result = _filter_report_and_get_data_sync(report_url, combination, return_locators, return_name)
            if isinstance(result, dict):
                final_result.update(result)
            logger.debug(f"组合 {i + 1} 完成")
        except Exception as e:
            logger.error(f"组合 {i + 1} 执行失败: {e}")

    logger.info(f"批量处理完成，成功处理 {len(final_result)} 个结果")
    return final_result


# 导出给Agent使用的工具函数（主要使用异步版本）
__all__ = ['get_report_sample', 'batch_filter_report_and_get_data',
          'get_report_sample_sync', 'batch_filter_report_and_get_data_sync']  # 保留同步版本作为fallback


if __name__ == '__main__':
    # 测试控件操作功能
    test_url = "http://localhost:8075/webroot/decision/view/report?viewlet=WorkBook1.cpt"

    # 测试1：基本控件操作
    # p = [{'type': 'text', 'name': 'zzz', 'value': '新的值'}]
    # result = filter_report_and_get_data_sync(test_url, p)
    # print(result)

    # 测试2：批量控件操作 + 数据提取
    p = [{'type': 'text', 'name': 'zzz', 'value': ['ABC', 'DEF', 'ZZZ', 'VVV', 'VVV2', 'VV2V']}]
    # locators = {'bal': 'C3', 'avg_bal': 'D3'}
    locators = {'bal': {'find_column': 'C', 'find_value': '烦烦烦', 'return_column': 'E'}}
    result = batch_filter_report_and_get_data_sync(test_url, p, locators)
    print(result)
