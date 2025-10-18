@echo off
REM 淘沙分析平台 - 测试启动脚本（Windows）

setlocal enabledelayedexpansion

REM 进入后端目录
cd /d %~dp0

REM 检查pytest是否安装
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo 错误: pytest未安装，正在安装...
    python -m pip install pytest pytest-asyncio pytest-cov pytest-mock
)

REM 解析命令行参数
set "test_type=%1"
set "coverage=%2"

if "%test_type%"=="" (
    set "test_type=all"
)

if "%coverage%"=="--cov" (
    set "cov_flag=--cov=backend --cov-report=html --cov-report=term"
) else (
    set "cov_flag="
)

REM 执行测试
echo.
echo ========================================
echo 淘沙分析平台 - 后端测试启动
echo ========================================
echo 测试类型: %test_type%
echo 覆盖率分析: !cov_flag!
echo.

if "%test_type%"=="all" (
    echo [1/1] 运行所有测试...
    python -m pytest testcases/ -v !cov_flag!
) else if "%test_type%"=="unit" (
    echo [1/1] 运行单元测试...
    python -m pytest testcases/unit/ -v !cov_flag!
) else if "%test_type%"=="integration" (
    echo [1/1] 运行集成测试...
    python -m pytest testcases/integration/ -v !cov_flag!
) else if "%test_type%"=="api" (
    echo [1/1] 运行API测试...
    python -m pytest testcases/api/ -v !cov_flag!
) else if "%test_type%"=="metadata" (
    echo [1/1] 运行元数据服务测试...
    python -m pytest testcases/unit/test_metadata_service.py testcases/integration/test_metadata_flow.py -v !cov_flag!
) else (
    echo [1/1] 运行指定的测试文件或测试用例...
    python -m pytest %test_type% -v !cov_flag!
)

echo.
echo ========================================
echo 测试完成
echo ========================================

if exist htmlcov\index.html (
    echo 覆盖率报告已生成: htmlcov\index.html
)

endlocal
