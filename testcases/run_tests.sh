#!/bin/bash
# 淘沙分析平台 - 测试启动脚本（Linux/Mac）

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )"
cd "$SCRIPT_DIR"

# 检查pytest是否安装
if ! python -m pytest --version &> /dev/null; then
    echo "错误: pytest未安装，正在安装..."
    python -m pip install pytest pytest-asyncio pytest-cov pytest-mock
fi

# 解析命令行参数
TEST_TYPE="${1:-all}"
COVERAGE="${2:-}"

# 设置覆盖率标记
if [ "$COVERAGE" == "--cov" ]; then
    COV_FLAG="--cov=backend --cov-report=html --cov-report=term"
else
    COV_FLAG=""
fi

# 执行测试
echo ""
echo "========================================"
echo "淘沙分析平台 - 后端测试启动"
echo "========================================"
echo "测试类型: $TEST_TYPE"
echo "覆盖率分析: $COV_FLAG"
echo ""

case "$TEST_TYPE" in
    all)
        echo "[1/1] 运行所有测试..."
        python -m pytest testcases/ -v $COV_FLAG
        ;;
    unit)
        echo "[1/1] 运行单元测试..."
        python -m pytest testcases/unit/ -v $COV_FLAG
        ;;
    integration)
        echo "[1/1] 运行集成测试..."
        python -m pytest testcases/integration/ -v $COV_FLAG
        ;;
    api)
        echo "[1/1] 运行API测试..."
        python -m pytest testcases/api/ -v $COV_FLAG
        ;;
    metadata)
        echo "[1/1] 运行元数据服务测试..."
        python -m pytest testcases/unit/test_metadata_service.py testcases/integration/test_metadata_flow.py -v $COV_FLAG
        ;;
    *)
        echo "[1/1] 运行指定的测试文件或测试用例..."
        python -m pytest "$TEST_TYPE" -v $COV_FLAG
        ;;
esac

echo ""
echo "========================================"
echo "测试完成"
echo "========================================"

if [ -f htmlcov/index.html ]; then
    echo "覆盖率报告已生成: htmlcov/index.html"
fi
