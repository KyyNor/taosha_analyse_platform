#!/bin/bash

# 淘沙分析平台前端启动脚本

echo "=========================================="
echo "🚀 淘沙分析平台前端启动中..."
echo "=========================================="

# 检查Node.js是否安装
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js 16+ 版本"
    exit 1
fi

# 检查npm是否安装
if ! command -v npm &> /dev/null; then
    echo "❌ npm 未安装，请先安装 npm"
    exit 1
fi

# 显示版本信息
echo "📦 Node.js 版本: $(node --version)"
echo "📦 npm 版本: $(npm --version)"

# 安装依赖
if [ ! -d "node_modules" ]; then
    echo "📥 安装依赖包..."
    npm install
else
    echo "✅ 依赖包已存在"
fi

# 启动开发服务器
echo "🌐 启动开发服务器..."
echo "🔗 访问地址: http://localhost:5173"
echo "🔗 API 地址: http://localhost:8000"
echo "=========================================="

npm run dev