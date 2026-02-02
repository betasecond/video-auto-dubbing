#!/bin/bash

# 前端开发启动脚本

echo "🚀 启动视频配音系统前端..."

# 检查 Node.js 版本
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ 需要 Node.js 18 或更高版本"
    echo "当前版本: $(node -v)"
    exit 1
fi

# 检查依赖是否已安装
if [ ! -d "node_modules" ]; then
    echo "📦 安装依赖..."
    npm install
fi

# 检查环境变量文件
if [ ! -f ".env.local" ]; then
    echo "⚙️  创建环境变量文件..."
    cp .env.local.example .env.local
    echo "✅ 已创建 .env.local，请根据需要修改"
fi

# 启动开发服务器
echo "🌐 启动开发服务器..."
npm run dev
