# ✅ 准备就绪 - 部署指南

## 🎉 好消息

远程 IndexTTS v2 API 已验证可用！

**测试结果：**
```
✅ URL: https://u861448-ej47-562de107.bjb2.seetacloud.com:8443
✅ 端点: /tts_url
✅ 状态: HTTP 200 OK
✅ 输出: RIFF WAVE audio, 22050 Hz, mono
✅ 文件大小: ~120KB (正常)
```

**Worker 代码已完成修改：**
- ✅ 支持 IndexTTS v2 `/tts_url` 端点
- ✅ 修复自动检测逻辑（不再误判为 Gradio）
- ✅ 实现 Speaker 映射机制

---

## 📋 部署步骤

### Step 1: 更新配置

编辑配置文件：

**如果使用环境变量（.env）：**

```bash
# 编辑 .env 文件
vi .env  # 或 nano .env

# 确保包含以下配置
TTS_SERVICE_URL=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443
TTS_BACKEND=vllm
```

**如果使用 docker-compose.yml：**

```yaml
services:
  worker:
    environment:
      - TTS_SERVICE_URL=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443
      - TTS_BACKEND=vllm
```

---

### Step 2: 重新编译 Worker（如果需要）

**方式 A: Docker Compose（推荐）**

```bash
# 重新构建 Worker 镜像
docker-compose build worker

# 重启 Worker 服务
docker-compose restart worker

# 查看日志
docker-compose logs -f worker
```

**方式 B: 直接编译**

```bash
cd worker

# 编译
go build -o worker ./cmd/worker

# 运行
./worker
```

---

### Step 3: 验证 Worker 启动日志

启动 Worker 后，应该看到：

```
INFO    Using VLLMClient for IndexTTS API
        url=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443
        backend=vllm
```

**如果看到：**
```
INFO    Detected Gradio TTS service, using GradioClient
```

说明配置有问题，请检查：
1. `TTS_BACKEND` 是否设置为 `vllm`
2. 代码是否重新编译
3. 环境变量是否生效

---

### Step 4: 运行端到端测试

1. **上传视频**
   - 通过 API 或前端上传一个测试视频

2. **查看任务进度**
   - 等待任务进入 TTS 步骤

3. **检查 Worker 日志**

期望看到：
```
DEBUG   Trying IndexTTS v2 /tts_url
        url=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443/tts_url
        speaker=default
        spk_path=/root/index-tts-vllm/examples/voice_01.wav
        text_len=50

INFO    IndexTTS v2 /tts_url success
        content_type=audio/wav
```

4. **验证结果**
   - TTS 任务成功完成
   - 生成的音频文件可以播放
   - 没有"file download 400"等错误

---

## 🧪 快速测试脚本

运行此脚本验证配置：

```bash
cd /Users/micago/Desktop/index/video-auto-dubbing

# 测试远程 API
./test_remote_tts.sh
```

期望输出：
```
✅ Health check passed
✅ 端点存在
✅ TTS 合成成功！生成了有效的 WAV 文件
```

---

## 📊 配置参考

### 完整 .env 示例

```bash
# 数据库
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dubbing
DB_USER=dubbing
DB_PASSWORD=dubbing123
DB_SSLMODE=disable

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_PUBLIC_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_USE_SSL=false
MINIO_BUCKET=videos

# RabbitMQ
RABBITMQ_URL=amqp://rabbitmq:rabbitmq123@localhost:5672/

# TTS 服务（核心配置）
TTS_SERVICE_URL=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443
TTS_BACKEND=vllm
TTS_API_KEY=

# GLM API
GLM_API_KEY=your_glm_api_key_here
GLM_API_URL=https://open.bigmodel.cn/api/paas/v4/chat/completions
GLM_MODEL=glm-4-flash
GLM_RPS=5.0

# Volcengine ASR
VOLCENGINE_ASR_APP_KEY=
VOLCENGINE_ASR_ACCESS_KEY=
VOLCENGINE_ASR_RESOURCE_ID=volc.bigasr.auc
```

---

## 🎯 验收清单

部署完成后，逐项检查：

- [ ] Worker 启动日志显示 "Using VLLMClient for IndexTTS API"
- [ ] 没有 "Detected Gradio" 日志
- [ ] TTS 任务开始时日志显示 "Trying IndexTTS v2 /tts_url"
- [ ] TTS 任务成功时日志显示 "IndexTTS v2 /tts_url success"
- [ ] 生成的音频文件可以正常播放
- [ ] 没有 Gradio 相关错误（如 "file download 400"）
- [ ] 完整视频处理流程成功（upload → extract → asr → translate → tts → merge）

---

## 🐛 常见问题排查

### 问题 1: 仍然使用 GradioClient

**症状：**
```
INFO    Detected Gradio TTS service, using GradioClient
```

**解决：**
1. 确认 `TTS_BACKEND=vllm` 已设置
2. 重新编译 Worker（`docker-compose build worker` 或 `go build`）
3. 重启 Worker
4. 检查环境变量是否生效（`docker-compose exec worker env | grep TTS`）

---

### 问题 2: TTS 任务失败，500 错误

**可能原因：**
- Speaker 映射的文件在远程服务器不存在

**检查：**
在远程服务器执行：
```bash
ls -lh /root/index-tts-vllm/examples/voice_01.wav
```

如果文件不存在，修改 Worker 代码中的 `speakerMapping`，使用实际存在的文件路径。

---

### 问题 3: SSL 证书错误

**症状：**
```
x509: certificate signed by unknown authority
```

**临时解决：**
在 Worker 代码中添加跳过证书验证（仅用于测试）：

```go
// worker/internal/tts/vllm_client.go
import (
    "crypto/tls"
    "net/http"
)

func NewVLLMClient(cfg config.TTSConfig, logger *zap.Logger) *VLLMClient {
    tr := &http.Transport{
        TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
    }
    return &VLLMClient{
        baseURL: cfg.URL,
        apiKey:  cfg.APIKey,
        client: &http.Client{
            Timeout:   600 * time.Second,
            Transport: tr,
        },
        logger: logger,
    }
}
```

**正式解决：**
安装正确的 SSL 证书，或使用 HTTP（如果可以）。

---

### 问题 4: 音频质量不佳

**调整 Speaker 映射：**

编辑 `worker/internal/tts/vllm_client.go` 的 `speakerMapping`：

```go
speakerMapping := map[string]string{
    "default":   "/root/index-tts-vllm/examples/voice_05.wav",  // 换一个音色
    "male_1":    "/root/index-tts-vllm/examples/voice_01.wav",
    "female_1":  "/root/index-tts-vllm/examples/voice_02.wav",
    // 根据实际效果调整
}
```

重新编译并测试不同的 voice 文件。

---

## 📚 相关文档

- **详细技术文档**：`WORKER_INDEXTTSS_V2_INTEGRATION.md`
- **总结文档**：`FINAL_SUMMARY.md`
- **测试脚本**：`test_remote_tts.sh`

---

## 🚀 快速启动命令

```bash
# 1. 更新配置
echo 'TTS_SERVICE_URL=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443' >> .env
echo 'TTS_BACKEND=vllm' >> .env

# 2. 重启服务（Docker Compose）
docker-compose build worker
docker-compose restart worker
docker-compose logs -f worker

# 3. 测试远程 API
./test_remote_tts.sh

# 4. 上传测试视频（通过 API 或前端）
# 然后观察日志
```

---

## ✅ 成功标志

当你看到以下日志时，说明一切正常：

```
2026-01-23 18:30:00 INFO    Using VLLMClient for IndexTTS API
                            url=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443
                            backend=vllm

2026-01-23 18:30:15 DEBUG   Trying IndexTTS v2 /tts_url
                            speaker=default
                            spk_path=/root/index-tts-vllm/examples/voice_01.wav
                            text_len=120

2026-01-23 18:30:18 INFO    IndexTTS v2 /tts_url success
                            content_type=audio/wav

2026-01-23 18:30:20 INFO    TTS segment completed
                            segment=1/5
                            duration=3.2s
```

---

**祝部署顺利！如有问题请随时反馈。** 🎉
