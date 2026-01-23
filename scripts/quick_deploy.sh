#!/bin/bash
# 快速部署脚本 - Worker IndexTTS v2 集成

set -e

echo "========================================="
echo "Worker IndexTTS v2 集成 - 快速部署"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 检查配置文件
echo "步骤 1/5: 检查配置文件..."
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} 找到 .env 文件"

    # 检查 TTS 配置
    if grep -q "TTS_SERVICE_URL=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443" .env; then
        echo -e "${GREEN}✓${NC} TTS_SERVICE_URL 已配置"
    else
        echo -e "${YELLOW}⚠${NC} TTS_SERVICE_URL 需要更新"
        echo ""
        echo "请手动编辑 .env 文件，确保包含："
        echo "  TTS_SERVICE_URL=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443"
        echo "  TTS_BACKEND=vllm"
        echo ""
        read -p "已更新配置文件？(y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}✗${NC} 部署取消"
            exit 1
        fi
    fi
else
    echo -e "${RED}✗${NC} 未找到 .env 文件"
    echo "请创建 .env 文件并配置 TTS_SERVICE_URL"
    exit 1
fi
echo ""

# 2. 测试远程 API
echo "步骤 2/5: 测试远程 TTS API..."
if [ -f "test_remote_tts.sh" ]; then
    chmod +x test_remote_tts.sh
    if ./test_remote_tts.sh | grep -q "✅.*成功"; then
        echo -e "${GREEN}✓${NC} 远程 API 测试通过"
    else
        echo -e "${RED}✗${NC} 远程 API 测试失败"
        echo "请检查远程服务是否正常运行"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠${NC} 未找到测试脚本，跳过 API 测试"
fi
echo ""

# 3. 检查代码修改
echo "步骤 3/5: 验证代码修改..."
if grep -q "tryIndexTTSV2Endpoint" worker/internal/tts/vllm_client.go; then
    echo -e "${GREEN}✓${NC} vllm_client.go 已修改"
else
    echo -e "${RED}✗${NC} vllm_client.go 未修改"
    exit 1
fi

if grep -q ".gradio.live" worker/internal/tts/client.go && ! grep -q '".seetacloud.com"' worker/internal/tts/client.go; then
    echo -e "${GREEN}✓${NC} client.go 已修复"
else
    echo -e "${YELLOW}⚠${NC} client.go 可能未正确修改"
fi
echo ""

# 4. 重新编译和启动
echo "步骤 4/5: 重新编译和启动 Worker..."

if command -v docker-compose &> /dev/null; then
    echo "使用 Docker Compose..."

    # 重新构建
    echo "  构建 Worker 镜像..."
    docker-compose build worker

    # 重启服务
    echo "  重启 Worker 服务..."
    docker-compose restart worker

    # 等待启动
    sleep 3

    # 检查状态
    if docker-compose ps worker | grep -q "Up"; then
        echo -e "${GREEN}✓${NC} Worker 服务已启动"
    else
        echo -e "${RED}✗${NC} Worker 服务启动失败"
        docker-compose logs --tail=20 worker
        exit 1
    fi

elif command -v go &> /dev/null; then
    echo "使用 Go 直接编译..."

    cd worker
    go build -o worker ./cmd/worker

    if [ -f "worker" ]; then
        echo -e "${GREEN}✓${NC} Worker 编译成功"
        echo ""
        echo "请手动运行: ./worker/worker"
    else
        echo -e "${RED}✗${NC} Worker 编译失败"
        exit 1
    fi

else
    echo -e "${YELLOW}⚠${NC} 未找到 docker-compose 或 go 命令"
    echo "请手动编译和启动 Worker"
fi
echo ""

# 5. 检查日志
echo "步骤 5/5: 检查启动日志..."

if command -v docker-compose &> /dev/null; then
    echo "查看最近的日志..."
    docker-compose logs --tail=30 worker | grep -i "tts\|vllm\|client" || true

    echo ""
    echo "检查关键日志..."
    if docker-compose logs worker | grep -q "Using VLLMClient for IndexTTS API"; then
        echo -e "${GREEN}✓${NC} Worker 正在使用 VLLMClient"
    else
        echo -e "${YELLOW}⚠${NC} 未检测到 VLLMClient 日志（可能还未处理 TTS 任务）"
    fi

    if docker-compose logs worker | grep -q "Detected Gradio"; then
        echo -e "${RED}✗${NC} 错误：仍在使用 GradioClient"
        echo "请检查配置和代码修改"
    fi
fi
echo ""

# 完成
echo "========================================="
echo -e "${GREEN}部署完成！${NC}"
echo "========================================="
echo ""
echo "下一步操作："
echo "  1. 上传一个测试视频"
echo "  2. 观察 Worker 日志："
echo "     docker-compose logs -f worker | grep -i tts"
echo "  3. 验证 TTS 步骤成功完成"
echo ""
echo "期望看到的日志："
echo "  ✓ Using VLLMClient for IndexTTS API"
echo "  ✓ Trying IndexTTS v2 /tts_url"
echo "  ✓ IndexTTS v2 /tts_url success"
echo ""
echo "相关文档："
echo "  - READY_TO_DEPLOY.md（部署指南）"
echo "  - SUCCESS_SUMMARY.md（总结）"
echo "  - WORKER_INDEXTTSS_V2_INTEGRATION.md（技术文档）"
echo ""
