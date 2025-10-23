@echo off
REM 淘沙分析平台 - 内网打包工具 (Windows 批处理脚本)
REM 此脚本用于在 Windows 环境下运行依赖打包工具

echo.
echo ========================================
echo   淘沙分析平台 - 内网依赖打包工具
echo ========================================
echo.

REM 检查 Python 是否可用
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo 错误: 未找到 Python，请确保 Python 已安装并添加到 PATH
    pause
    exit /b 1
)

REM 检查 UV 是否可用
uv --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo 错误: 未找到 UV，请确保 UV 已安装并添加到 PATH
    echo 安装方法: pip install uv
    pause
    exit /b 1
)

REM 检查项目结构
if not exist "..\pyproject.toml" (
    echo 错误: 未找到项目根目录，请确保从正确的位置运行此脚本
    pause
    exit /b 1
)

echo 正在开始打包依赖...
echo.

REM 运行 Python 打包脚本
python package_for_offline.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo   打包完成！
    echo ========================================
    echo.
    echo 打包文件位置: taosha-offline-package-1.0.0.tar.gz
    echo 请将此文件传输到内网环境进行部署。
    echo.
    echo 部署说明请参考: README_OFFLINE_DEPLOYMENT.md
    echo.
) else (
    echo.
    echo 错误: 打包过程中出现错误，请检查上面的错误信息
    echo.
)

pause