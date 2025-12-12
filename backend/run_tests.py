#!/usr/bin/env python3
"""
测试运行脚本
"""

import subprocess
import sys
import os

def run_tests():
    """运行测试"""
    # 确保在backend目录下
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 运行pytest
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/fraudhunter/test_model_hit_alert_manager.py",
        "-v", "--tb=short"
    ]
    
    print("运行模型执行跟踪系统属性测试...")
    print(f"命令: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)