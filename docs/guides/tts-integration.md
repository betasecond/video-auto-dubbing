# Worker 与 IndexTTS v2 集成指南

## 📋 问题分析

### 原始问题
1. **端点不匹配**：Worker 尝试 `/synthesize`, `/tts` 等端点，但 IndexTTS v2 实际端点是 `/tts_url`
2. **请求格式不匹配**：IndexTTS v2 需要 `spk_audio_path`（服务器本地路径），但 Worker 发送的是 `prompt_audio_url`（MinIO/OSS URL）
3. **错误的服务类型检测**：`.seetacloud.com` 被误判为 Gradio 服务，导致使用了 GradioClient

### IndexTTS v2 API 规范

**端点：** `POST /tts_url`

**请求体：**
```json
{
  "text": "要合成的文本",
  "spk_audio_path": "/root/index-tts-vllm/examples/voice_01.wav",
  "emo_control_method": 0,
  "emo_ref_path": null,
  "emo_weight": 1.0,
  "emo_vec": [0, 0, 0, 0, 0, 0, 0, 0],
  "emo_text": null,
  "emo_random": false,
  "max_text_tokens_per_sentence": 120
}
```

**响应：**
- Content-Type: `audio/wav`
- 音频二进制流

---

## ✅ 解决方案

### 修改 1: `worker/internal/tts/vllm_client.go`

#### 添加 IndexTTS v2 请求结构体

```go
// indexTTSV2Request represents IndexTTS v2 /tts_url API request format.
type indexTTSV2Request struct {
    Text                        string    `json:"text"`
    SpkAudioPath                string    `json:"spk_audio_path"`
    EmoControlMethod            int       `json:"emo_control_method,omitempty"`
    EmoRefPath                  string    `json:"emo_ref_path,omitempty"`
    EmoWeight                   float64   `json:"emo_weight,omitempty"`
    EmoVec                      []float64 `json:"emo_vec,omitempty"`
    EmoText                     string    `json:"emo_text,omitempty"`
    EmoRandom                   bool      `json:"emo_random,omitempty"`
    MaxTextTokensPerSentence    int       `json:"max_text_tokens_per_sentence,omitempty"`
}
```

#### 新增 `/tts_url` 端点处理函数

```go
func (c *VLLMClient) tryIndexTTSV2Endpoint(ctx context.Context, req SynthesisRequest) (io.ReadCloser, error)
```

**核心逻辑：**
1. 将 Worker 的 `SpeakerID` 映射到远程服务器的本地音频文件路径
2. 构造 IndexTTS v2 格式的请求
3. 调用 `/tts_url` 端点
4. 返回音频流

**Speaker 映射表：**
```go
speakerMapping := map[string]string{
    "default":   "/root/index-tts-vllm/examples/voice_01.wav",
    "speaker_1": "/root/index-tts-vllm/examples/voice_01.wav",
    "speaker_2": "/root/index-tts-vllm/examples/voice_02.wav",
    "male_1":    "/root/index-tts-vllm/examples/voice_01.wav",
    "female_1":  "/root/index-tts-vllm/examples/voice_02.wav",
    // ... 更多映射
}
```

#### 修改 `synthesizeNative` 函数

```go
func (c *VLLMClient) synthesizeNative(ctx context.Context, req SynthesisRequest) (io.ReadCloser, error) {
    // 优先尝试 IndexTTS v2 /tts_url
    reader, err := c.tryIndexTTSV2Endpoint(ctx, req)
    if err == nil {
        return reader, nil
    }

    // 回退到通用端点
    endpoints := []string{"/synthesize", "/tts", "/api/synthesize", "/api/tts"}
    // ...
}
```

---

### 修改 2: `worker/internal/tts/client.go`

#### 修复自动检测逻辑

**原代码问题：**
```go
gradioIndicators := []string{
    ".seetacloud.com", // ❌ 错误：会误判 FastAPI 服务
    ".gradio.live",
    // ...
}
```

**修复后：**
```go
gradioIndicators := []string{
    ".gradio.live",    // ✅ 只检测真正的 Gradio 特征
    ".gradio.app",
    "/gradio/",
    ":7860",           // Gradio 默认端口
}
```

#### 支持显式 Backend 配置

```go
// Explicit Gradio backend selection
if cfg.Backend == "gradio" {
    return NewGradioClient(cfg, logger)
}

// Default to VLLM client for IndexTTS v2 FastAPI services
return NewVLLMClient(cfg, logger)
```

---

## 🚀 部署步骤

### 1. 确认远程服务运行正常

在远程服务器上：

```bash
# 检查进程
ps aux | grep api_server_v2

# 测试端点
curl -I http://localhost:6006/tts_url
# 应该返回 405 Method Not Allowed (因为需要 POST)

# 测试实际请求
curl -o /tmp/test.wav \
  -H 'Content-Type: application/json' \
  -d '{
    "text":"测试",
    "spk_audio_path":"/root/index-tts-vllm/examples/voice_01.wav"
  }' \
  http://localhost:6006/tts_url

file /tmp/test.wav
# 应该显示: RIFF (little-endian) data, WAVE audio
```

### 2. 确认参考音频文件存在

```bash
ls -lh /root/index-tts-vllm/examples/voice_*.wav
```

应该看到 voice_01.wav 到 voice_12.wav 等文件。

### 3. 更新 Worker 配置

**环境变量：**
```bash
TTS_SERVICE_URL=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443
TTS_BACKEND=vllm  # 或者留空，会自动使用 VLLMClient
```

### 4. 重新编译 Worker

```bash
cd worker
go build -o worker ./cmd/worker
```

### 5. 重启 Worker

```bash
# 如果使用 Docker Compose
docker-compose restart worker

# 或者直接运行
./worker
```

---

## 🧪 测试验证

### 测试 1: 检查日志

启动 Worker 后，应该看到类似日志：

```
INFO    Using VLLMClient for IndexTTS API
        url=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443
        backend=vllm
```

### 测试 2: 上传视频并处理

1. 上传一个视频文件
2. 查看任务进度，等待到达 TTS 步骤
3. 检查 Worker 日志：

```
DEBUG   Trying IndexTTS v2 /tts_url
        url=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443/tts_url
        speaker=default
        spk_path=/root/index-tts-vllm/examples/voice_01.wav
        text_len=50

INFO    IndexTTS v2 /tts_url success
        content_type=audio/wav
```

### 测试 3: 验证生成的音频

1. TTS 步骤完成后，下载生成的配音视频
2. 检查音频质量
3. 确认没有"文件下载 400"等 Gradio 相关错误

---

## 📊 性能优化

### Speaker 缓存（未来优化）

当前实现使用预定义的 speaker 映射表。未来可以优化为：

1. **动态上传参考音频**：
   - Worker 下载 `PromptAudioURL` 的音频文件
   - 上传到远程服务器（新增 `/upload_speaker` 端点）
   - 使用返回的路径作为 `spk_audio_path`

2. **Speaker 缓存服务**：
   - 在远程服务器维护 speaker 缓存目录
   - Worker 首次使用时上传，后续复用

---

## 🐛 故障排查

### 问题 1: 仍然使用 GradioClient

**症状：**
```
INFO    Detected Gradio TTS service, using GradioClient
```

**解决：**
1. 检查配置：`TTS_BACKEND` 应该是 `vllm` 或空
2. 确认代码已更新（`isGradioService` 函数不应包含 `.seetacloud.com`）
3. 重新编译 Worker

### 问题 2: /tts_url 返回 500 错误

**可能原因：**
- `spk_audio_path` 文件不存在
- 请求体格式错误

**检查：**
```bash
# 在远程服务器检查文件
ls -l /root/index-tts-vllm/examples/voice_01.wav

# 查看远程服务器日志
tail -f /root/index-tts-vllm/logs/api_server_v2.log
```

### 问题 3: 音频质量差

**可能原因：**
- 使用的 speaker 参考音频不合适
- 文本分段过长

**解决：**
- 调整 speaker 映射，选择更合适的 voice_*.wav
- 检查 `max_text_tokens_per_sentence` 参数（当前固定为 120）

---

## 📝 配置参考

### 完整的 .env 示例

```bash
# 数据库
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dubbing
DB_USER=dubbing
DB_PASSWORD=dubbing123

# RabbitMQ
RABBITMQ_URL=amqp://rabbitmq:rabbitmq123@localhost:5672/

# TTS 服务
TTS_SERVICE_URL=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443
TTS_BACKEND=vllm
TTS_API_KEY=  # 如果需要

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=videos
```

### Docker Compose 配置

```yaml
services:
  worker:
    build:
      context: .
      dockerfile: worker/Dockerfile
    environment:
      - TTS_SERVICE_URL=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443
      - TTS_BACKEND=vllm
    volumes:
      - ./worker:/app/worker
    depends_on:
      - rabbitmq
      - postgres
```

---

## 🎯 验收标准

- [ ] Worker 启动时日志显示 "Using VLLMClient for IndexTTS API"
- [ ] TTS 任务日志显示 "Trying IndexTTS v2 /tts_url"
- [ ] TTS 任务日志显示 "IndexTTS v2 /tts_url success"
- [ ] 没有 Gradio 相关错误（如 "file URL download 400"）
- [ ] 生成的音频文件可正常播放且质量正常
- [ ] 完整的视频处理流程成功（upload → ASR → translate → TTS → merge）

---

## 📚 相关文件

- `worker/internal/tts/vllm_client.go` - 核心修改
- `worker/internal/tts/client.go` - 自动检测修复
- IndexTTS v2 API 示例: `api_example_v2.py`
- 远程服务器代码: `/root/index-tts-vllm/api_server_v2.py`

---

## 🔄 后续优化方向

1. **动态 Speaker 管理**：支持上传自定义参考音频
2. **情感控制**：利用 IndexTTS v2 的情感控制功能
3. **性能优化**：并发调用优化、连接池
4. **监控告警**：TTS 成功率、延迟监控

---

**最后更新：** 2025-01-23
**状态：** ✅ 已实现并测试
