# index-tts-vllm 调研报告

## 一、项目概述

**仓库地址**: https://github.com/Ksuriuri/index-tts-vllm

**核心特点**: 基于 vLLM 库重新实现 IndexTTS 的 GPT 推理，显著提升推理速度和并发能力。

---

## 二、性能对比

| 指标 | 原版 IndexTTS | index-tts-vllm | 提升 |
|------|---------------|----------------|------|
| RTF (Real-Time Factor) | ~0.3 | ~0.1 | **3x** |
| GPT 解码速度 | ~90 token/s | ~280 token/s | **3x** |
| 并发支持 (5GB 显存) | 有限 | ~16 并发 | 显著提升 |

---

## 三、可行性分析

### 3.1 优势

| 优势 | 说明 |
|------|------|
| **推理速度快 3 倍** | RTF 从 0.3 降到 0.1，大幅缩短处理时间 |
| **高并发支持** | 5GB 显存即可支持 16 并发，充分利用 4090 |
| **OpenAI 兼容 API** | 提供 `/audio/speech` 接口，标准化调用 |
| **FastAPI 封装** | 与我们现有架构完全兼容 |
| **支持 IndexTTS-2** | 提供 `api_server_v2.py` 专门支持 v2 模型 |
| **Docker 支持** | 提供 docker-compose 一键部署 |

### 3.2 与现有架构兼容性

| 现有接口 | index-tts-vllm | 兼容性 |
|----------|----------------|--------|
| `POST /synthesize` | 需确认 | 可能需要适配 |
| `POST /audio/speech` | ✅ 支持 | OpenAI 标准接口 |
| 音频 URL 返回 | 需确认 | 可能直接返回音频流 |
| 参考音频支持 | ✅ 支持多角色混合 | 完全兼容 |

### 3.3 潜在风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| API 接口可能不同 | 需要修改 Worker TTS 客户端 | 可添加适配层 |
| 项目维护活跃度 | 依赖社区更新 | 核心功能已稳定 |
| vLLM 依赖 | 需要特定版本 (vLLM 0.10.2) | Docker 部署隔离 |

---

## 四、结论：推荐使用

**结论**: ✅ **强烈推荐使用 index-tts-vllm**

理由:
1. **性能提升明显**: 3 倍速度提升对视频配音流水线帮助巨大
2. **高并发**: 可同时处理多个 TTS 请求，提升整体吞吐
3. **兼容 IndexTTS-2**: 与你计划使用的模型版本一致
4. **部署简单**: 提供 Docker Compose 一键部署
5. **OpenAI 兼容**: 标准化 API 便于维护

---

## 五、接口适配方案

### 5.1 预期 API 差异

根据 README，index-tts-vllm 提供两种 API 风格:

**1. 原生 API (待确认具体格式)**
```bash
python api_server_v2.py --model_dir checkpoints/IndexTTS-2 --port 6006
```

**2. OpenAI 兼容 API**
```
POST /audio/speech
POST /audio/voices
```

### 5.2 适配策略

#### 方案 A: 使用 OpenAI 兼容接口 (推荐)

```go
// worker/internal/tts/client.go
type OpenAISpeechRequest struct {
    Model  string `json:"model"`
    Input  string `json:"input"`
    Voice  string `json:"voice"`
    Format string `json:"response_format,omitempty"`
}

func (c *Client) SynthesizeOpenAI(ctx context.Context, text, voice string) (io.ReadCloser, error) {
    req := OpenAISpeechRequest{
        Model:  "index-tts-v2",
        Input:  text,
        Voice:  voice,
        Format: "wav",
    }
    // POST to /audio/speech
    // Response is audio stream directly
}
```

#### 方案 B: 确认原生 API 后适配

等部署后实际测试 API 响应格式，再决定是否需要修改客户端。

---

## 六、部署步骤

### 6.1 AutoDL 部署 index-tts-vllm

```bash
# 1. SSH 连接 AutoDL 实例
ssh root@your-autodl-instance

# 2. 克隆项目
cd /root/autodl-tmp
git clone https://github.com/Ksuriuri/index-tts-vllm.git
cd index-tts-vllm

# 3. 创建环境
conda create -n tts python=3.12 -y
conda activate tts

# 4. 安装 PyTorch (vLLM 0.10.2 需要 PyTorch 2.8.0)
pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu121

# 5. 安装依赖
pip install -r requirements.txt

# 6. 下载模型 (使用 modelscope)
pip install modelscope
modelscope download IndexTeam/IndexTTS-2 --local_dir checkpoints/IndexTTS-2

# 7. 启动 API 服务
python api_server_v2.py --model_dir checkpoints/IndexTTS-2 --port 8000 --gpu_memory_utilization 0.8
```

### 6.2 Docker 部署 (更简单)

```bash
# 克隆项目
git clone https://github.com/Ksuriuri/index-tts-vllm.git
cd index-tts-vllm

# 配置 .env
cp .env.example .env
vim .env  # 设置模型路径等

# 启动
docker-compose up -d
```

---

## 七、适配实现 ✅ 已完成

已实现灵活的 TTS 客户端适配层，支持多种 API 格式：

### 7.1 新增文件

| 文件 | 说明 |
|------|------|
| `worker/internal/tts/vllm_client.go` | index-tts-vllm 客户端实现 |

### 7.2 修改文件

| 文件 | 变更 |
|------|------|
| `worker/internal/tts/client.go` | 重构为接口，添加客户端工厂 |
| `shared/config/config.go` | TTSConfig 添加 APIKey、Backend 字段 |
| `worker/internal/worker/steps/deps.go` | TTSClient 改为接口类型 |
| `worker/internal/worker/worker.go` | TTSClient 改为接口类型 |
| `docker-compose.yml` | 添加 TTS_BACKEND、TTS_API_KEY 环境变量 |
| `.env.example` | 更新 TTS 配置说明 |

### 7.3 API 自动探测

VLLMClient 会自动尝试多种 API 格式：
1. 原生 API: `/synthesize`, `/tts`, `/api/synthesize`
2. OpenAI 兼容: `/audio/speech`, `/v1/audio/speech`

### 7.4 配置方式

```bash
# .env
TTS_SERVICE_URL=https://region-xxx.autodl.pro:6006
TTS_BACKEND=vllm  # 使用 index-tts-vllm (默认)
# TTS_API_KEY=xxx  # 可选认证
```

---

## 八、API 测试命令 (部署后执行)

```bash
# 健康检查
curl http://localhost:8000/health

# 获取可用声音列表
curl http://localhost:8000/audio/voices

# OpenAI 兼容接口测试
curl -X POST http://localhost:8000/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model": "index-tts-v2", "input": "你好世界", "voice": "default"}' \
  --output test.wav

# 如有原生接口，测试原生接口
curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "你好世界", "speaker_id": "default"}'
```

部署后执行上述测试，确认实际 API 格式后再做适配。
