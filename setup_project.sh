#!/bin/bash
set -e

echo "🚀 开始搭建项目骨架..."

# 创建后端目录结构
echo "📁 创建后端目录结构..."
mkdir -p backend/{app/{api,models,schemas,services,core,integrations/{dashscope,oss}},workers/{steps},migrations/versions,tests/{test_api,test_workers}}

# 创建前端目录结构
echo "📁 创建前端目录结构..."
mkdir -p frontend/{app/{tasks/{new,'[id]'},api},components/{ui},lib/hooks,public}

# 创建配置文件目录
mkdir -p configs

echo "✅ 目录结构创建完成"
echo ""
echo "📂 项目结构预览:"
tree -L 2 -d backend frontend 2>/dev/null || (
  echo "backend/"
  find backend -type d | head -20
  echo ""
  echo "frontend/"
  find frontend -type d | head -20
)

