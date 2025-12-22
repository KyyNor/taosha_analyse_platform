"""
代码执行工具安全测试
验证安全审计和沙箱限制功能
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from services.agents.tools.code_execution_tool import execute_code, execute_code_tool_async


def print_result(test_name: str, result_json: str):
    """打印测试结果"""
    result = json.loads(result_json)
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"{'='*60}")
    print(f"成功: {result['success']}")
    if result['success']:
        print(f"结果: {result.get('result')}")
        if result.get('stdout'):
            print(f"输出: {result['stdout']}")
    else:
        print(f"错误: {result['error']}")
    print(f"{'='*60}\n")


def test_normal_execution():
    """测试正常的数据处理代码"""
    print("\n" + "="*80)
    print("1. 正常执行测试")
    print("="*80)

    # 测试1: 简单计算
    result = execute_code("""
result = sum([1, 2, 3, 4, 5])
print(f"Sum: {result}")
""")
    print_result("简单计算", result)

    # 测试2: pandas 数据处理
    result = execute_code("""
import pandas as pd
data = [
    {"name": "Alice", "age": 25, "salary": 50000},
    {"name": "Bob", "age": 30, "salary": 60000},
    {"name": "Charlie", "age": 35, "salary": 70000}
]
df = pd.DataFrame(data)
result = {
    "mean_age": df['age'].mean(),
    "mean_salary": df['salary'].mean(),
    "count": len(df)
}
""")
    print_result("Pandas数据处理", result)

    # 测试3: numpy 计算
    result = execute_code("""
import numpy as np
arr = np.array([1, 2, 3, 4, 5])
result = {
    "mean": float(np.mean(arr)),
    "std": float(np.std(arr)),
    "sum": float(np.sum(arr))
}
""")
    print_result("Numpy计算", result)


def test_security_violations():
    """测试安全违规检测"""
    print("\n" + "="*80)
    print("2. 安全违规测试（这些应该被拦截）")
    print("="*80)

    # 测试1: 系统命令
    result = execute_code("""
import os
os.system('ls -la')
""")
    print_result("尝试执行系统命令 (os.system)", result)

    # 测试2: subprocess
    result = execute_code("""
import subprocess
subprocess.run(['whoami'])
""")
    print_result("尝试创建子进程 (subprocess)", result)

    # 测试3: eval
    result = execute_code("""
result = eval("1 + 1")
""")
    print_result("尝试使用 eval", result)

    # 测试4: 文件操作
    result = execute_code("""
with open('/etc/passwd', 'r') as f:
    result = f.read()
""")
    print_result("尝试读取系统文件 (/etc/passwd)", result)

    # 测试5: 网络请求
    result = execute_code("""
import requests
result = requests.get('https://example.com').text
""")
    print_result("尝试网络请求 (requests)", result)

    # 测试6: pickle (反序列化漏洞)
    result = execute_code("""
import pickle
data = pickle.dumps({'key': 'value'})
result = pickle.loads(data)
""")
    print_result("尝试使用 pickle", result)


def test_file_access():
    """测试受限的文件访问"""
    print("\n" + "="*80)
    print("3. 受限文件访问测试")
    print("="*80)

    # 测试1: 启用文件访问 - 写入文件
    result = execute_code("""
with safe_open(f"{WORK_DIR}/test.txt", "w") as f:
    f.write("Hello, World!")
result = "文件写入成功"
""", enable_file_access=True)
    print_result("安全文件写入", result)

    # 测试2: 启用文件访问 - 读取文件
    result = execute_code("""
with safe_open(f"{WORK_DIR}/test.txt", "r") as f:
    content = f.read()
result = f"文件内容: {content}"
""", enable_file_access=True)
    print_result("安全文件读取", result)

    # 测试3: 尝试访问工作目录外的文件
    result = execute_code("""
with safe_open("/etc/passwd", "r") as f:
    result = f.read()
""", enable_file_access=True)
    print_result("尝试访问工作目录外的文件", result)

    # 测试4: 未启用文件访问时尝试使用 safe_open
    result = execute_code("""
with safe_open(f"{WORK_DIR}/test.txt", "r") as f:
    result = f.read()
""", enable_file_access=False)
    print_result("未启用文件访问权限", result)


def test_timeout():
    """测试超时控制"""
    print("\n" + "="*80)
    print("4. 超时控制测试")
    print("="*80)

    # 测试: 无限循环（应该被超时终止）
    result = execute_code("""
import time
while True:
    time.sleep(1)
""", timeout=3)
    print_result("无限循环 (3秒超时)", result)


async def test_async_execution():
    """测试异步执行"""
    print("\n" + "="*80)
    print("5. 异步执行测试")
    print("="*80)

    # 测试异步执行
    result = await execute_code_tool_async("""
import time
time.sleep(1)
result = "异步执行完成"
""")
    print_result("异步执行", result)


def test_advanced_scenarios():
    """测试高级场景"""
    print("\n" + "="*80)
    print("6. 高级场景测试")
    print("="*80)

    # 测试1: 日期时间处理
    result = execute_code("""
from datetime import datetime, timedelta
now = datetime.now()
tomorrow = now + timedelta(days=1)
result = {
    "now": now.strftime("%Y-%m-%d %H:%M:%S"),
    "tomorrow": tomorrow.strftime("%Y-%m-%d %H:%M:%S")
}
""")
    print_result("日期时间处理", result)

    # 测试2: JSON 处理
    result = execute_code("""
import json
data = {"name": "Alice", "scores": [95, 87, 92]}
json_str = json.dumps(data, indent=2)
parsed = json.loads(json_str)
result = {
    "original": data,
    "parsed": parsed,
    "avg_score": sum(parsed["scores"]) / len(parsed["scores"])
}
""")
    print_result("JSON处理", result)

    # 测试3: 正则表达式
    result = execute_code("""
import re
text = "Email: alice@example.com, bob@test.com"
emails = re.findall(r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b', text)
result = {"emails": emails, "count": len(emails)}
""")
    print_result("正则表达式", result)

    # 测试4: 统计分析
    result = execute_code("""
import statistics
data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
result = {
    "mean": statistics.mean(data),
    "median": statistics.median(data),
    "stdev": statistics.stdev(data),
    "variance": statistics.variance(data)
}
""")
    print_result("统计分析", result)


def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("代码执行工具安全测试套件")
    print("="*80)

    # 同步测试
    test_normal_execution()
    test_security_violations()
    test_file_access()
    test_timeout()
    test_advanced_scenarios()

    # 异步测试
    print("\n运行异步测试...")
    asyncio.run(test_async_execution())

    print("\n" + "="*80)
    print("所有测试完成")
    print("="*80)


if __name__ == "__main__":
    main()
