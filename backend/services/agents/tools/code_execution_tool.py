"""
Python 代码执行工具（安全版本）
用于执行 Python 代码进行数据处理和分析
添加了完整的安全审计和沙箱限制
"""

import sys
import io
import traceback
import asyncio
import os
from pathlib import Path
from typing import Any, Optional
from contextlib import redirect_stdout, redirect_stderr
from langfuse import observe
from utils.logger import logger
import json


# 安全配置
ALLOWED_WORK_DIR = Path("/tmp/taosha_code_execution")  # 允许代码操作的工作目录
ALLOWED_WORK_DIR.mkdir(exist_ok=True, parents=True)


class CodeExecutionError(Exception):
    """代码执行错误"""
    pass


class SecurityViolationError(Exception):
    """安全违规错误"""
    pass


def create_safe_builtins():
    """
    创建安全的内置函数集合
    移除危险的系统操作函数

    注意：我们需要保留 __import__ 以支持 import 语句
    但会通过代码审计来阻止危险的导入
    """
    # 获取内置函数字典
    if isinstance(__builtins__, dict):
        builtins_dict = __builtins__
    else:
        builtins_dict = __builtins__.__dict__

    # 复制默认的 builtins
    safe_builtins = builtins_dict.copy()

    # 移除最危险的函数（但保留 __import__ 以支持 import 语句）
    dangerous_functions = [
        'eval', 'exec',  # 动态代码执行
        'open',  # 文件操作（我们会提供安全版本）
        'input', 'raw_input',  # 用户输入
        'exit', 'quit',  # 程序退出
        'compile',  # 编译代码
    ]

    for func in dangerous_functions:
        safe_builtins.pop(func, None)

    return safe_builtins


def create_safe_open(allowed_dir: Path):
    """
    创建安全的文件打开函数
    只允许访问指定目录下的文件
    """
    def safe_open(file, mode='r', *args, **kwargs):
        # 解析文件路径
        file_path = Path(file).resolve()
        allowed_path = allowed_dir.resolve()

        # 检查路径是否在允许的目录内
        try:
            file_path.relative_to(allowed_path)
        except ValueError:
            raise SecurityViolationError(
                f"安全违规：不允许访问目录 {allowed_dir} 外的文件: {file_path}"
            )

        # 检查模式是否安全（禁止某些危险模式）
        if any(m in mode for m in ['x', 'a']) and 'r' not in mode:
            raise SecurityViolationError(
                f"安全违规：不允许使用文件模式 '{mode}'"
            )

        # 调用真正的 open
        return open(file_path, mode, *args, **kwargs)

    return safe_open


def audit_code(code: str) -> tuple[bool, Optional[str]]:
    """
    审计代码是否包含危险操作

    Returns:
        (is_safe, error_message)
    """
    import re

    # 危险关键字检查 - 使用正则表达式避免误报
    dangerous_patterns = [
        (r'\bos\.system\b', '不允许执行系统命令'),
        (r'\bsubprocess\b', '不允许创建子进程'),
        (r'\beval\s*\(', '不允许使用 eval'),
        (r'\bexec\s*\(', '不允许使用 exec'),
        (r'(?<!safe_)(?<!def\s)open\s*\(', '请使用提供的 safe_open 函数（而不是内置 open）'),
        (r'\bsocket\b', '不允许网络操作'),
        (r'\burllib\b', '不允许网络请求'),
        (r'\brequests\b', '不允许网络请求'),
        (r'\bhttp\.client\b', '不允许网络请求'),
        (r'\bftplib\b', '不允许FTP操作'),
        (r'\btelnetlib\b', '不允许Telnet操作'),
        (r'\bpickle\b', '不允许使用 pickle（安全风险）'),
        (r'\bmarshal\b', '不允许使用 marshal（安全风险）'),
        (r'\bshelve\b', '不允许使用 shelve（安全风险）'),
        (r'\bctypes\b', '不允许使用 ctypes'),
        (r'\bsys\.exit\b', '不允许退出程序'),
    ]

    for pattern, reason in dangerous_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"安全审计失败: {reason}"

    # 检查是否尝试直接访问 __builtins__（但允许它存在于命名空间中）
    if re.search(r'\b__builtins__\s*\[', code) or re.search(r'__builtins__\s*\.', code):
        return False, "安全审计失败: 不允许直接访问 __builtins__ 对象"

    if '__globals__' in code:
        return False, "安全审计失败: 不允许访问 __globals__"

    return True, None


async def execute_code_async(
    code: str,
    timeout: int = 30,
    enable_file_access: bool = False
) -> dict:
    """
    异步执行 Python 代码（内部实现）

    Args:
        code: Python 代码字符串
        timeout: 执行超时时间（秒）
        enable_file_access: 是否允许文件访问

    Returns:
        执行结果字典
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    # 创建安全的执行命名空间
    namespace = {
        '__builtins__': create_safe_builtins(),
        '__name__': '__main__',
    }

    # 如果允许文件访问，提供安全的 open 函数
    if enable_file_access:
        namespace['safe_open'] = create_safe_open(ALLOWED_WORK_DIR)
        namespace['WORK_DIR'] = str(ALLOWED_WORK_DIR)

    # 预加载常用库
    try:
        import pandas as pd
        namespace['pd'] = pd
        namespace['pandas'] = pd
    except ImportError:
        pass

    try:
        import numpy as np
        namespace['np'] = np
        namespace['numpy'] = np
    except ImportError:
        pass

    try:
        import datetime
        namespace['datetime'] = datetime
        namespace['timedelta'] = datetime.timedelta
    except ImportError:
        pass

    try:
        import math
        namespace['math'] = math
    except ImportError:
        pass

    try:
        import statistics
        namespace['statistics'] = statistics
    except ImportError:
        pass

    try:
        import re
        namespace['re'] = re
    except ImportError:
        pass

    try:
        import collections
        namespace['collections'] = collections
    except ImportError:
        pass

    try:
        import itertools
        namespace['itertools'] = itertools
    except ImportError:
        pass

    namespace['json'] = json

    def _execute():
        """在线程中执行代码"""
        import builtins
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # 使用原生的 compile 和 exec，不从 namespace 中获取
            compiled_code = builtins.compile(code, '<string>', 'exec')
            builtins.exec(compiled_code, namespace)
            return namespace.get('result', None)

    try:
        # 使用 asyncio.to_thread 在线程池中执行，并设置超时
        result = await asyncio.wait_for(
            asyncio.to_thread(_execute),
            timeout=timeout
        )

        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()

        # 序列化结果
        serialized_result = _serialize_result(result)

        response = {
            "success": True,
            "result": serialized_result,
            "stdout": stdout_output,
        }

        if stderr_output:
            response["stderr"] = stderr_output

        return response

    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"代码执行超时（{timeout}秒）",
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue()
        }

    except SyntaxError as e:
        return {
            "success": False,
            "error": f"语法错误: {str(e)}",
            "line": e.lineno,
            "offset": e.offset,
            "text": e.text
        }

    except SecurityViolationError as e:
        return {
            "success": False,
            "error": f"安全违规: {str(e)}",
            "traceback": traceback.format_exc(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue()
        }


@observe(name="execute_code")
def execute_code(
    code: str,
    timeout: int = 30,
    enable_file_access: bool = False
) -> str:
    """
    执行 Python 代码进行数据处理和分析（同步接口）

    Args:
        code: Python 代码字符串。代码中可以使用预加载的库：
              - pd (pandas): 数据处理
              - np (numpy): 数值计算
              - json: JSON 处理
              - datetime: 日期时间处理
              - math: 数学函数
              - statistics: 统计函数
              - re: 正则表达式
              - collections: 集合类型
              - itertools: 迭代工具

              如果需要返回结果，请将结果赋值给名为 'result' 的变量

              安全限制：
              - 禁止执行系统命令（os.system, subprocess等）
              - 禁止网络操作（socket, requests等）
              - 禁止动态代码执行（eval, exec, compile等）
              - 文件操作需要 enable_file_access=True，且仅限于工作目录

        timeout: 执行超时时间（秒），默认 30 秒

        enable_file_access: 是否允许文件访问（默认False）
                           如果启用，可以使用 safe_open() 函数访问 WORK_DIR 目录下的文件

    Returns:
        JSON 格式的执行结果字符串，包含以下字段:
        - success: bool, 是否成功
        - result: any, 代码执行结果（如果定义了 result 变量）
        - stdout: str, 标准输出内容
        - stderr: str, 标准错误内容（仅在有错误时）
        - error: str, 错误信息（仅在失败时）
        - traceback: str, 错误堆栈（仅在失败时）

    Examples:
        # 简单计算
        execute_code('''
        result = 1 + 2 + 3
        ''')
        # 返回: {"success": true, "result": 6, ...}

        # 数据处理
        execute_code('''
        import pandas as pd
        data = [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]
        df = pd.DataFrame(data)
        result = df.describe().to_dict()
        ''')

        # 文件操作（需要启用）
        execute_code('''
        with safe_open(f"{WORK_DIR}/data.txt", "w") as f:
            f.write("Hello World")
        result = "文件已写入"
        ''', enable_file_access=True)
    """
    logger.info(f"执行Python代码（安全模式）: {code[:100]}...")

    # 代码安全审计
    is_safe, audit_error = audit_code(code)
    if not is_safe:
        logger.error(f"代码安全审计失败: {audit_error}")
        return json.dumps({
            "success": False,
            "error": audit_error,
        }, ensure_ascii=False)

    # 在新的事件循环中执行异步代码
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            execute_code_async(code, timeout, enable_file_access)
        )
        loop.close()

        if result["success"]:
            logger.info("Python代码执行成功")
        else:
            logger.error(f"Python代码执行失败: {result.get('error')}")

        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"执行环境错误: {e}")
        return json.dumps({
            "success": False,
            "error": f"执行环境错误: {str(e)}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


def _serialize_result(result: Any) -> Any:
    """
    序列化执行结果，处理特殊类型

    Args:
        result: 原始结果

    Returns:
        可 JSON 序列化的结果
    """
    if result is None:
        return None

    # pandas DataFrame
    if hasattr(result, 'to_dict'):
        try:
            return result.to_dict('records')
        except:
            return str(result)

    # numpy array
    if hasattr(result, 'tolist'):
        try:
            return result.tolist()
        except:
            return str(result)

    # pandas Series
    if hasattr(result, 'to_list'):
        try:
            return result.to_list()
        except:
            return str(result)

    # 基本类型
    if isinstance(result, (str, int, float, bool, type(None))):
        return result

    # 列表和字典
    if isinstance(result, (list, tuple)):
        return [_serialize_result(item) for item in result]

    if isinstance(result, dict):
        return {str(k): _serialize_result(v) for k, v in result.items()}

    # 其他类型转为字符串
    return str(result)


# 为向后兼容提供异步接口
async def execute_code_tool_async(
    code: str,
    timeout: int = 30,
    enable_file_access: bool = False
) -> str:
    """
    异步执行 Python 代码（供 Agent 工具使用）

    这是真正的异步实现，可以直接在 FastAPI 异步路由中调用
    """
    logger.info(f"执行Python代码（异步，安全模式）: {code[:100]}...")

    # 代码安全审计
    is_safe, audit_error = audit_code(code)
    if not is_safe:
        logger.error(f"代码安全审计失败: {audit_error}")
        return json.dumps({
            "success": False,
            "error": audit_error,
        }, ensure_ascii=False)

    # 直接执行异步代码
    result = await execute_code_async(code, timeout, enable_file_access)

    if result["success"]:
        logger.info("Python代码执行成功")
    else:
        logger.error(f"Python代码执行失败: {result.get('error')}")

    return json.dumps(result, ensure_ascii=False, default=str)
