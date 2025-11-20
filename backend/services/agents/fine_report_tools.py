"""
FineReport工具包
提供FineReport报表登录和抽样功能
"""
import os
import asyncio
import json
from pathlib import Path
import uuid
import sys
from typing import Optional, Dict, List, Union, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger
from markitdown import DocumentConverterResult, MarkItDown
import pandas as pd

from langfuse import observe
from utils.config import settings
from utils.excel_parser import ensure_download_dir
from services.agents.models.fine_report_models import ConditionalLocator, ControlOperation, FilterReportRequest
from langchain.tools import tool


def excel_column_to_index(column: str) -> int:
    """
    将Excel列名转换为数字索引（从0开始）

    Args:
        column: Excel列名，如 'A'=1, 'B'=2, 'AA'=27, 'AB'=28 等

    Returns:
        int: 从0开始的列索引

    Examples:
        >>> excel_column_to_index('A')
        0
        >>> excel_column_to_index('AB')
        27
    """
    if not column or not column.isalpha() or not column.isupper():
        raise ValueError(f"无效的Excel列名: {column}")

    result = 0
    for char in column:
        result = result * 26 + (ord(char) - ord('A') + 1)

    return result - 1  # 转换为从0开始的索引


# 全局异步浏览器实例（每个worker进程一个）
_async_browser: Optional[Browser] = None
_async_context: Optional[BrowserContext] = None  # 共享登录会话的上下文
_async_context_initialized: bool = False  # 标记是否已初始化
_async_context_login_attempted: bool = False  # 标记是否已尝试登录


async def get_async_browser_context() -> BrowserContext:
    """获取全局异步 BrowserContext 实例，懒加载模式"""
    global _async_browser, _async_context, _async_context_initialized, _async_context_login_attempted

    if _async_context is None:
        logger.info("首次调用：启动异步 Playwright 浏览器实例")
        try:
            playwright = await async_playwright().start()
            _async_browser = await playwright.chromium.launch(
                headless=settings.fine_report_browser_headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )

            # 创建共享的BrowserContext，用于session共享
            _async_context = await _async_browser.new_context()
            _async_context_initialized = True

            logger.info("异步 Playwright 浏览器实例已启动，等待首次使用时登录")
        except Exception as e:
            logger.error(f"启动异步浏览器失败: {e}", exc_info=True)
            raise

    return _async_context


async def _login_once_async(context: BrowserContext):
    """在BrowserContext级别执行一次性登录，所有Page共享会话"""
    global _async_context_login_attempted

    if _async_context_login_attempted:
        logger.debug("登录已尝试过，跳过重复登录")
        return True

    logger.info("执行一次性登录建立共享会话")
    _async_context_login_attempted = True

    page = None
    try:
        page = await context.new_page()
        # 访问任意报表URL触发登录
        await page.goto(settings.fine_report_login_url, wait_until="networkidle", timeout=10000)

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

            # 等待登录完成（缩短超时时间）
            try:
                await page.wait_for_url("**/decision/**", timeout=15000)
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


async def _ensure_login_async(context: BrowserContext) -> bool:
    """确保已登录，如果未登录则执行登录"""
    global _async_context_login_attempted

    if not _async_context_login_attempted:
        logger.info("首次使用：执行FineReport登录")
        return await _login_once_async(context)
    else:
        logger.debug("登录状态已就绪")
        return True


async def cleanup_async_browser():
    """清理异步浏览器资源"""
    global _async_browser, _async_context, _async_context_initialized, _async_context_login_attempted

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

    # 重置状态标记
    _async_context_initialized = False
    _async_context_login_attempted = False
    logger.info("浏览器状态已重置")


async def _download_excel(page: Page) -> str:
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


async def _check_fine_login(page: Page) -> bool:
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
                await page.wait_for_timeout(2000)
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


@observe(name="get_report_sample")
async def get_report_sample(report_url: str) -> str:
    """
    获取报表样例信息，可以获取报表的控件清单和最新的页面内容，用来了解报表，为后续的batch_filter_report_and_get_data做准备

    Args:
        report_url: FineReport报表的完整URL

    Returns:
        Markdown格式的抽样信息字符串
    """
    logger.info(f"开始获取报表抽样信息: {report_url}")

    page = None
    try:
        # 获取全局 Browser 实例
        context = await get_async_browser_context()

        # 确保已登录（懒加载）
        if not await _ensure_login_async(context):
            logger.error("FineReport登录失败")
            return '{"success": false, "error": "登录失败"}'

        # 创建新 Page（不复用）
        logger.info("创建新的浏览器页面")
        page = await context.new_page()

        # 访问报表URL
        await page.goto(report_url, wait_until="networkidle")
        logger.info(f"已访问报表页面: {report_url}")

        # 等待页面加载完成
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)

        # 检查登录状态（如果登录失败或会话过期）
        current_url = page.url
        if "login" in current_url.lower():
            logger.info("检测到会话过期，尝试重新登录")
            if await _check_fine_login(page):
                # 重新访问报表URL
                await page.goto(report_url, wait_until="networkidle")
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)

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

        widgets_result = await page.evaluate(widgets_script)

        # 下载Excel文件
        file_path = await _download_excel(page)
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
        try:
            screenshot_bytes = await page.screenshot()
            output_screenshot_path = f"{settings.fine_report_browser_screenshot_path}{os.sep}report_{uuid.uuid4().hex[:8]}.png"
            await Path(output_screenshot_path).write_bytes(screenshot_bytes)
            logger.warning(f"已保存错误截图:{output_screenshot_path}")
        except Exception as e:
            pass
        return f"# 错误\n获取报表抽样信息失败: {str(e)}"

    finally:
        # 关闭页面
        if page:
            try:
                await page.close()
            except Exception as e:
                logger.warning(f"关闭页面失败: {e}")



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
        await page.wait_for_timeout(2000)
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
            file_path = await _download_excel(page)

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
        try:
            screenshot_bytes = await page.screenshot()
            output_screenshot_path = f"{settings.fine_report_browser_screenshot_path}{os.sep}report_{uuid.uuid4().hex[:8]}.png"
            await Path(output_screenshot_path).write_bytes(screenshot_bytes)
            logger.warning(f"已保存错误截图:{output_screenshot_path}")
        except Exception as e:
            pass
        return {"error": f"# 错误\n执行控件操作失败: {str(e)}"}

    finally:
        if page:
            try:
                await page.close()
            except Exception as e:
                logger.warning(f"关闭页面失败: {e}")

def extract_data_from_excel(excel_path: str, locators: Dict[str, Any]) -> Dict[str, str]:
    """
    从Excel中提取数据

    Args:
        excel_path: Excel文件路径
        locators: 定位器字典

    Returns:
        提取的数据字典

    Examples:
        >>> locators = {
        ...     'balance': {
        ...         'find_column': 'A',
        ...         'find_value': '汉口银行',
        ...         'find_value_type': 'static',
        ...         'return_column': 'C'
        ...     }
        ... }
        >>> result = extract_data_from_excel('data.xlsx', locators)
    """
    df = pd.read_excel(excel_path, header=None)
    result = {}

    for key, locator in locators.items():
        if not isinstance(locator, dict):
            logger.warning(f"定位器 '{key}' 格式不正确，已跳过。仅支持字典格式的条件查找。")
            result[key] = ""
            continue

        try:
            # 解析条件查找定位器
            find_column = locator.get('find_column', '').upper()
            find_value = str(locator.get('find_value', ''))
            return_column = locator.get('return_column', '').upper()

            # 验证必要的字段
            if not find_column or not return_column:
                logger.warning(f"定位器 '{key}' 缺少必要的列信息，已跳过")
                result[key] = ""
                continue

            # 转换Excel列名为数字索引
            find_col_idx = excel_column_to_index(find_column)
            return_col_idx = excel_column_to_index(return_column)

            # 验证列索引是否超出范围
            if find_col_idx >= len(df.columns) or return_col_idx >= len(df.columns):
                logger.warning(
                    f"定位器 '{key}' 的列索引超出范围。"
                    f"查找列 {find_column}({find_col_idx})，返回列 {return_column}({return_col_idx})，"
                    f"Excel总列数: {len(df.columns)}"
                )
                result[key] = ""
                continue

            # 执行条件查找
            found = False
            for row_idx in range(len(df)):
                cell_value = str(df.iloc[row_idx, find_col_idx])
                if find_value in cell_value:
                    value = df.iloc[row_idx, return_col_idx]
                    result[key] = str(value) if pd.notna(value) else ""
                    found = True
                    break


            if not found:
                logger.info(f"定位器 '{key}' 未找到匹配的数据: 查找列={find_column}, 查找值={find_value}")
                result[key] = ""

        except ValueError as e:
            logger.error(f"定位器 '{key}' 列名格式错误: {e}")
            result[key] = ""
        except Exception as e:
            logger.error(f"处理定位器 '{key}' 时发生未知错误: {e}", exc_info=True)
            result[key] = ""

    return result


@observe(name="batch_filter_report_and_get_data")
async def _batch_filter_report_and_get_data_async(report_url: str, control_operations: List[Dict[str, Any]], return_locators: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    批量从帆软报表获取结构化数据

    Args:
        report_url: FineReport报表的完整URL
        control_operations: 控件操作列表，value为数组格式，如 [{'type': 'text', 'name': '控件名称', 'value': ['控件值1', '控件值2']}, ...]
        return_locators: 返回数据定位器，支持以下格式：
            - 静态查找：{'key': {'find_column': 'A', 'find_value': '汉口银行', 'find_value_type': 'static', 'return_column': 'C'}}
            - 动态查找：{'key': {'find_column': 'A', 'find_value': '控件名', 'find_value_type': 'dynamic', 'return_column': 'C'}}
            其中find_column和return_column只能传Excel列名字母（如A、B、AA等）

    Returns:
        包含所有批次结果的字典

    Examples:
        >>> # 静态查找示例
        >>> result = await batch_filter_report_and_get_data(
        ...     "http://example.com/report",
        ...     [],
        ...     {
        ...         'bank_balance': {
        ...             'find_column': 'A',
        ...             'find_value': '汉口银行',
        ...             'find_value_type': 'static',
        ...             'return_column': 'C'
        ...         }
        ...     }
        ... )
        >>>
        >>> # 动态查找示例
        >>> result = await batch_filter_report_and_get_data(
        ...     "http://example.com/report",
        ...     [{'type': 'text', 'name': 'acct_no', 'value': ['1150032', '224801']}],
        ...     {
        ...         'account_balance': {
        ...             'find_column': 'A',
        ...             'find_value': 'acct_no',  # 引用控件名
        ...             'find_value_type': 'dynamic',
        ...             'return_column': 'C'
        ...         }
        ...     }
        ... )
    """
    logger.info(f"开始异步批量处理控件操作: {report_url}")
    logger.info(f"控件操作列表: {json.dumps([c.model_dump() for c in control_operations], indent=2, ensure_ascii=False)}")
    logger.info(f"返回数据定位器: {json.dumps(return_locators.model_dump(), indent=2, ensure_ascii=False)}")

    # 第一步：获取共享的BrowserContext
    context = await get_async_browser_context()

    # 确保已登录（懒加载）
    if not await _ensure_login_async(context):
        logger.error("FineReport登录失败")
        return {"error": "登录失败，无法执行批量操作"}

    # 第二步：生成控件操作组合并预解析动态查找值
    combinations_data = _generate_value_combinations_with_parsing(control_operations, return_locators)

    total_combinations = len(combinations_data)
    logger.info(f"生成 {total_combinations} 个值组合，已预解析动态查找值")

    # 第三步：创建并发任务（每个组合创建独立的Page），限制最大并发数为5
    semaphore = asyncio.Semaphore(5)

    async def limited_execute_task(combination, task_return_name):
        """限制并发数的任务执行函数"""
        async with semaphore:
            return await _filter_report_and_get_data_async(
                context, report_url,
                combination['control_operations'],
                combination['return_locators'],
                task_return_name
            )

    tasks = []
    for combination in combinations_data:
        return_name = "_".join([str(op['value']) for op in combination['control_operations']])
        # 创建带并发限制的异步任务，传入共享context和解析后的定位器
        task = limited_execute_task(combination, return_name)
        tasks.append(task)

    # 第四步：并发执行所有任务（最大并发数限制为5）
    logger.info(f"开始并发执行 {total_combinations} 个值组合（最大并发数：5）")
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 第五步：整理结果
    final_result = {}
    success_count = 0
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"组合 {i + 1} 执行失败: {result}")
            continue
        if isinstance(result, dict):
            final_result.update(result)
            success_count += 1

    logger.info(f"异步批量处理完成，成功处理 {success_count}/{total_combinations} 个结果")
    return final_result


@tool(args_schema=FilterReportRequest)
def batch_filter_report_and_get_data(report_url: str, control_operations: List[Dict[str, Any]], return_locators: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    批量从帆软报表获取结构化数据

    Args:
        report_url: FineReport报表的完整URL
        control_operations: 控件操作列表，value为数组格式，如 [{'type': 'text', 'name': '控件名称', 'value': ['控件值1', '控件值2']}, ...]
        return_locators: 返回数据定位器，支持以下格式：
            - 静态查找：{'key': {'find_column': 'A', 'find_value': '汉口银行', 'find_value_type': 'static', 'return_column': 'C'}}
            - 动态查找：{'key': {'find_column': 'A', 'find_value': '控件名', 'find_value_type': 'dynamic', 'return_column': 'C'}}
            其中find_column和return_column只能传Excel列名字母（如A、B、AA等）

    Returns:
        包含所有批次结果的字典
    """
    import asyncio

    # 获取或创建事件循环
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # 运行异步函数
    return loop.run_until_complete(
        _batch_filter_report_and_get_data_async(
            report_url, control_operations, return_locators
        )
    )


def _generate_value_combinations_with_parsing(control_operations: List[Dict[str, Any]], return_locators: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    生成控件操作值组合并预解析动态查找值

    Args:
        control_operations: 控件操作列表
        return_locators: 返回数据定位器字典，支持动态值引用

    Returns:
        list: 组合列表，每个元素包含:
            - control_operations: 控件操作组合
            - return_locators: 解析后的定位器组合

    Examples:
        >>> control_operations = [{'type': 'text', 'name': 'acct_no', 'value': ['控件值1', '控件值2']}]
        >>> return_locators = {'key': {'find_column': 'A', 'find_value': 'acct_no', 'find_value_type': 'dynamic', 'return_column': 'C'}}
        >>> result = _generate_value_combinations_with_parsing(control_operations, return_locators)
        # 返回: [
        #   {
        #     'control_operations': [{'type': 'text', 'name': 'acct_no', 'value': '控件值1'}],
        #     'return_locators': {'key': {'find_column': 'A', 'find_value': '控件值1', 'find_value_type': 'static', 'return_column': 'C'}}
        #   },
        #   {
        #     'control_operations': [{'type': 'text', 'name': 'acct_no', 'value': '控件值2'}],
        #     'return_locators': {'key': {'find_column': 'A', 'find_value': '控件值2', 'find_value_type': 'static', 'return_column': 'C'}}
        #   }
        # ]
    """
    # 1. 生成控件操作组合
    if not control_operations:
        control_combinations = [[]]  # 一个空组合
    else:
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

        control_combinations = []
        for values in combination_values:
            combination = []
            for i, op in enumerate(normalized_ops):
                combination.append({
                    'type': op['type'],
                    'name': op['name'],
                    'value': values[i]
                })
            control_combinations.append(combination)

    # 2. 生成组合列表，每个元素包含控件操作和解析后的定位器
    result_combinations = []

    for control_combo in control_combinations:
        # 建立控件名到值的映射
        control_value_map = {}
        for op in control_combo:
            control_value_map[op['name']] = str(op['value'])

        # 解析当前组合对应的定位器
        parsed_locators = {}

        if return_locators:
            for key, locator in return_locators.items():
                if not isinstance(locator, dict):
                    # 如果不是字典格式，保持原样（向后兼容）
                    logger.warning(f"定位器 '{key}' 不是字典格式，已跳过。建议使用条件查找格式。")
                    parsed_locators[key] = locator
                    continue

                try:
                    find_column = locator.get('find_column', '').upper()
                    find_value = str(locator.get('find_value', ''))
                    find_value_type = locator.get('find_value_type', 'static')
                    return_column = locator.get('return_column', '').upper()

                    # 验证必要的字段
                    if not find_column or not return_column:
                        logger.warning(f"定位器 '{key}' 缺少必要的列信息，已跳过")
                        parsed_locators[key] = ""
                        continue

                    # 解析动态查找值
                    if find_value_type == 'dynamic':
                        # 动态值：从控件映射中获取实际值
                        actual_value = control_value_map.get(find_value, '')
                        if not actual_value:
                            logger.warning(f"定位器 '{key}' 引用的控件 '{find_value}' 未找到对应值")
                            actual_value = ""

                        # 构造解析后的定位器（静态值）
                        parsed_locators[key] = {
                            'find_column': find_column,
                            'find_value': actual_value,
                            'find_value_type': 'static',  # 解析后都为静态
                            'return_column': return_column
                        }
                    else:
                        # 静态值：直接使用原值
                        parsed_locators[key] = {
                            'find_column': find_column,
                            'find_value': find_value,
                            'find_value_type': 'static',
                            'return_column': return_column
                        }

                except Exception as e:
                    logger.error(f"解析定位器 '{key}' 时发生错误: {e}", exc_info=True)
                    parsed_locators[key] = ""

        # 添加到结果组合列表
        result_combinations.append({
            'control_operations': control_combo,
            'return_locators': parsed_locators
        })

    return result_combinations


# 导出给Agent使用的工具函数（主要使用异步版本）
__all__ = ['get_report_sample', 'batch_filter_report_and_get_data']

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
    result = batch_filter_report_and_get_data(test_url, p, locators)
    print(result)
