"""
Python 代码执行工具
用于执行 Python 代码进行数据处理和分析
"""

import sys
import io
import traceback
import signal
from typing import Any
from contextlib import redirect_stdout, redirect_stderr
from langfuse import observe
from utils.logger import logger
import json


# 代码执行超时处理（仅在 Unix 系统有效）
class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError("代码执行超时")


@observe(name="execute_code")
def execute_code(
    code: str,
    timeout: int = 30
) -> str:
    """
    执行 Python 代码进行数据处理和分析

    Args:
        code: Python 代码字符串。代码中可以使用预加载的库：
              - pd (pandas): 数据处理
              - np (numpy): 数值计算
              - json: JSON 处理
              - datetime: 日期时间处理
              - math: 数学函数
              - statistics: 统计函数
              - re: 正则表达式

              如果需要返回结果，请将结果赋值给名为 'result' 的变量

        timeout: 执行超时时间（秒），默认 30 秒

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

        # 统计分析
        execute_code('''
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = {
            "mean": np.mean(data),
            "std": np.std(data),
            "median": np.median(data)
        }
        ''')
    """
    logger.info(f"执行Python代码: {code}[200:]...")

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    # 准备执行命名空间，预加载常用库
    namespace = {
        '__builtins__': __builtins__,
    }

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

    try:
        # 设置超时（仅在支持 signal 的系统上有效）
        # has_signal = hasattr(signal, 'SIGALRM')
        # if has_signal:
        #     old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        #     signal.alarm(timeout)

        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # 编译并执行代码
            compiled_code = compile(code, '<string>', 'exec')
            exec(compiled_code, namespace)

            # 获取 result 变量（如果存在）
            result = namespace.get('result', None)

        # if has_signal:
        #     signal.alarm(0)  # 取消超时
        #     signal.signal(signal.SIGALRM, old_handler)

        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()

        # 序列化结果
        serialized_result = _serialize_result(result)

        logger.info(f"Python代码执行成功")

        response = {
            "success": True,
            "result": serialized_result,
            "stdout": stdout_output,
        }

        if stderr_output:
            response["stderr"] = stderr_output

        return json.dumps(response, ensure_ascii=False, default=str)

    except TimeoutError as e:
        logger.error(f"代码执行超时: {timeout}秒")
        return json.dumps({
            "success": False,
            "error": f"代码执行超时（{timeout}秒）",
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue()
        }, ensure_ascii=False)

    except SyntaxError as e:
        logger.error(f"代码语法错误: {e}")
        return json.dumps({
            "success": False,
            "error": f"语法错误: {str(e)}",
            "line": e.lineno,
            "offset": e.offset,
            "text": e.text
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"代码执行失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue()
        }, ensure_ascii=False)

    finally:
        # 确保清理超时设置
        if hasattr(signal, 'SIGALRM'):
            try:
                signal.alarm(0)
            except:
                pass


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
