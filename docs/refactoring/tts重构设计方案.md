# TTS 重构设计方案：远程 AutoDL IndexTTS 服务

## 一、重构目标

将本地 Docker 部署的 IndexTTS2 服务改为调用**远程 AutoDL 4090 服务器**上部署的 IndexTTS API，实现：

1. **降低本地资源需求**：无需本地 GPU
2. **灵活扩展**：可根据需求增减远程 GPU 实例
3. **成本优化**：按需使用云端算力

---

## 二、架构变更

### 2.1 变更前后对比

```
【变更前 - 本地 Docker】
Worker → HTTP → tts_service (本地 Docker, 需要 GPU)
                     ↓
              IndexTTS2 本地推理

【变更后 - 远程 AutoDL】
Worker → HTTP → AutoDL 远程服务器 (4090 GPU)
                     ↓
              IndexTTS2 远程推理
```

### 2.2 服务变更

| 组件 | 变更 |
|------|------|
| `tts_service/` | **保留代码** - 用于远程服务器部署 |
| `docker-compose.yml` | **修改** - 移除 tts_service，添加远程 URL 配置 |
| `shared/config/config.go` | **修改** - 添加远程 TTS 配置 |
| `.env.example` | **修改** - 添加远程 TTS URL |

---

## 三、远程服务部署方案

### 3.1 AutoDL 服务器配置

| 配置项 | 推荐值 |
|--------|--------|
| GPU | RTX 4090 24GB |
| 系统镜像 | PyTorch 2.1 + CUDA 12.1 |
| 内存 | 32GB+ |
| 存储 | 50GB+ (模型 + 缓存) |

### 3.2 部署步骤

```bash
# 1. SSH 连接到 AutoDL 实例
ssh root@your-autodl-instance

# 2. 克隆项目
git clone https://github.com/your-repo/video-auto-dubbing.git
cd video-auto-dubbing/tts_service

# 3. 安装依赖
pip install -e .

# 4. 下载模型 (首次)
# 模型会自动从 HuggingFace 下载到 /root/autodl-tmp/models

# 5. 配置环境变量
export TTS_HOST=0.0.0.0
export TTS_PORT=8000
export TTS_BACKEND=index_tts2
export INDEXTTS_MODEL_DIR=/root/autodl-tmp/models/IndexTTS-2
export INDEXTTS_DEVICE=cuda
export INDEXTTS_USE_FP16=true
export HF_ENDPOINT=https://hf-mirror.com

# 6. 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 7. (可选) 使用 screen/tmux 保持后台运行
screen -S tts
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# Ctrl+A+D 退出 screen
```

### 3.3 AutoDL 端口映射

AutoDL 提供自定义服务端口映射，需要在控制台配置：
1. 登录 AutoDL 控制台
2. 选择实例 → 自定义服务
3. 添加端口映射：容器端口 8000 → 公网端口 (如 6006)
4. 获取公网访问地址：`https://region-xxx.autodl.pro:port`

---

## 四、本地配置变更

### 4.1 环境变量

```bash
# 远程 TTS 服务地址 (AutoDL 公网地址)
TTS_SERVICE_URL=https://region-xxx.autodl.pro:6006

# 可选：API 密钥 (如果远程服务配置了认证)
TTS_API_KEY=your_api_key_here
```

### 4.2 docker-compose.yml 变更

```yaml
services:
  # 删除 tts_service 服务定义

  worker:
    environment:
      # TTS 改为远程地址
      TTS_SERVICE_URL: ${TTS_SERVICE_URL:-https://region-xxx.autodl.pro:6006}
```

---

## 五、代码变更

### 5.1 变更文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `shared/config/config.go` | 修改 | 移除本地 TTS 相关默认值 |
| `docker-compose.yml` | 修改 | 移除 tts_service |
| `.env.example` | 修改 | 更新 TTS 配置说明 |

### 5.2 TTS 客户端无需修改

现有 `worker/internal/tts/client.go` 已经是基于 HTTP 调用的设计，只需要修改 `TTS_SERVICE_URL` 指向远程地址即可，**无需修改代码**。

---

## 六、网络与安全

### 6.1 网络连通性

```
本地 Worker → Internet → AutoDL 公网地址 → TTS 服务
```

需要确保：
1. Worker 容器可以访问公网
2. AutoDL 实例端口已开放

### 6.2 安全建议

1. **HTTPS**：AutoDL 公网地址默认支持 HTTPS
2. **API 密钥**：可在远程服务添加简单认证
3. **IP 白名单**：如有固定出口 IP，可配置防火墙规则

### 6.3 添加简单 API 密钥认证 (可选)

远程服务添加认证中间件：

```python
# tts_service/app/main.py 添加

from fastapi import Header, HTTPException

API_KEY = os.getenv("TTS_API_KEY", "")

async def verify_api_key(x_api_key: str = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

# 在路由中添加依赖
@app.post("/synthesize", response_model=SynthesisResponse, dependencies=[Depends(verify_api_key)])
```

Worker 客户端添加 API Key 头：

```go
// worker/internal/tts/client.go
httpReq.Header.Set("X-Api-Key", c.apiKey)
```

---

## 七、故障处理

### 7.1 AutoDL 实例重启

AutoDL 实例可能因维护或欠费重启，需要：
1. 配置开机自启脚本
2. 使用 systemd 或 supervisor 管理进程

```bash
# /etc/systemd/system/tts.service
[Unit]
Description=TTS Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/video-auto-dubbing/tts_service
Environment="TTS_HOST=0.0.0.0"
Environment="TTS_PORT=8000"
Environment="TTS_BACKEND=index_tts2"
ExecStart=/root/miniconda3/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable tts
sudo systemctl start tts
```

### 7.2 健康检查

Worker 可以在调用前检查远程服务健康状态：

```bash
curl https://region-xxx.autodl.pro:6006/health
```

---

## 八、成本估算

### AutoDL 4090 实例

| 配置 | 价格 (参考) |
|------|-------------|
| RTX 4090 24GB | ~¥2-3/小时 |
| 按量计费 | 不使用可关机 |
| 包月优惠 | ~¥1500-2000/月 |

### 建议策略

1. **开发测试**：按需开机，不用即关
2. **生产环境**：包月或长期租用
3. **高并发**：多实例 + 负载均衡

---

## 九、开发步骤

### Phase 1: 远程服务部署 ⏳
- [ ] 创建 AutoDL 实例
- [ ] 部署 tts_service
- [ ] 配置端口映射
- [ ] 测试健康检查

### Phase 2: 本地配置 ⏳
- [ ] 修改 docker-compose.yml
- [ ] 更新 .env.example
- [ ] 测试连通性

### Phase 3: 验证
- [ ] 端到端测试
- [ ] 性能测试
