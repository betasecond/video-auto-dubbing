# IndexTTS v2 集成最终总结

## 🎯 问题诊断

### 核心问题

你的远程服务器运行的是 **IndexTTS v2 FastAPI 服务**（不是 OpenAI 官方 API），但 Worker 的自动检测逻辑错误地将其识别为 Gradio 服务，导致调用失败。

### 详细问题

1. **服务类型误判**：
   - Worker 检测到 URL 包含 `.seetacloud.com` → 误判为 Gradio
   - 实际上远程运行的是 FastAPI (`api_server_v2.py`)

2. **端点不匹配**：
   - Worker 尝试：`/synthesize`, `/tts`, `/audio/speech`
   - 实际端点：`/tts_url`（IndexTTS v2 原生 API）

3. **请求格式不匹配**：
   - Worker 发送：`{"text":"...", "prompt_audio_url":"https://..."}`
   - 服务期望：`{"text":"...", "spk_audio_path":"/root/local/path.wav"}`

4. **nginx 反代问题**（待确认）：
   - 8443 端口返回 404
   - 需要检查 nginx 配置或确认服务实际端口

---

## ✅ 解决方案已实施

### 修改 1: Worker 适配 IndexTTS v2

**文件：** `worker/internal/tts/vllm_client.go`

**改动：**
1. 添加 `indexTTSV2Request` 结构体（匹配 `/tts_url` API 格式）
2. 新增 `tryIndexTTSV2Endpoint` 函数（优先调用 `/tts_url`）
3. 实现 Speaker 映射逻辑（Worker speaker_id → 远程本地音频路径）

**Speaker 映射表：**
```go
speakerMapping := map[string]string{
    "default":   "/root/index-tts-vllm/examples/voice_01.wav",
    "speaker_1": "/root/index-tts-vllm/examples/voice_01.wav",
    "speaker_2": "/root/index-tts-vllm/examples/voice_02.wav",
    "male_1":    "/root/index-tts-vllm/examples/voice_01.wav",
    "female_1":  "/root/index-tts-vllm/examples/voice_02.wav",
    // ... 等
}
```

### 修改 2: 修复自动检测逻辑

**文件：** `worker/internal/tts/client.go`

**改动：**
1. 从 `isGradioService` 中移除 `.seetacloud.com` 判断
2. 仅保留明确的 Gradio 特征（`.gradio.live`, `:7860` 等）
3. 支持显式配置 `TTS_BACKEND=gradio`（如果真的需要 Gradio）

---

## 🚧 待解决问题

### 问题：8443 端口返回 404

**测试结果：**
```bash
curl https://u861448-ej47-562de107.bjb2.seetacloud.com:8443/health
# 返回 404 Not Found（nginx 页面）
```

**可能原因：**
1. nginx 反向代理未配置 或 配置错误
2. api_server_v2.py 运行在 6006 端口，但 nginx 未转发
3. nginx 配置文件需要添加 `/tts_url`, `/health` 等路由

### 需要在远程服务器检查

请 SSH 登录远程服务器并执行：

```bash
# 1. 确认服务运行端口
ps aux | grep api_server_v2
# 应该看到: python api_server_v2.py --port 6006

# 2. 测试本地端口
curl -I http://localhost:6006/health
curl -I http://localhost:6006/tts_url

# 3. 检查 nginx 配置
cat /etc/nginx/sites-enabled/default | grep -A 20 "8443"
# 或者
cat /etc/nginx/conf.d/*.conf | grep -A 20 "8443"

# 4. 检查 nginx 日志
tail -50 /var/log/nginx/error.log
```

---

## 📋 完整部署检查清单

### 远程服务器端

- [ ] **服务运行检查**
  ```bash
  ps aux | grep api_server_v2
  # 应该看到进程 PID 9340（或其他）
  ```

- [ ] **本地端点测试**
  ```bash
  curl -o /tmp/test.wav \
    -H 'Content-Type: application/json' \
    -d '{"text":"测试","spk_audio_path":"/root/index-tts-vllm/examples/voice_01.wav"}' \
    http://localhost:6006/tts_url

  file /tmp/test.wav
  # 期望: RIFF (little-endian) data, WAVE audio
  ```

- [ ] **参考音频文件存在**
  ```bash
  ls -lh /root/index-tts-vllm/examples/voice_*.wav
  # 应该看到 voice_01.wav 到 voice_12.wav
  ```

- [ ] **nginx 配置检查**
  ```bash
  # 确认 8443 端口的 upstream 配置指向 localhost:6006
  # 确认包含 /tts_url, /health 等路由
  ```

### Worker 端

- [ ] **代码已更新**
  - `worker/internal/tts/vllm_client.go` 包含 `tryIndexTTSV2Endpoint`
  - `worker/internal/tts/client.go` 的 `isGradioService` 不包含 `.seetacloud.com`

- [ ] **配置正确**
  ```bash
  TTS_SERVICE_URL=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443
  TTS_BACKEND=vllm  # 或留空
  ```

- [ ] **重新编译**
  ```bash
  cd worker
  go build -o worker ./cmd/worker
  ```

- [ ] **重启服务**
  ```bash
  docker-compose restart worker
  # 或
  ./worker
  ```

---

## 🔧 nginx 配置示例（如果需要）

如果 nginx 配置缺失，可以添加类似配置：

```nginx
server {
    listen 8443 ssl;
    server_name u861448-ej47-562de107.bjb2.seetacloud.com;

    # SSL 配置（如果有证书）
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:6006;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 对于 TTS 大请求，增加超时和大小限制
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        client_max_body_size 100M;
    }
}
```

重启 nginx：
```bash
sudo nginx -t  # 测试配置
sudo systemctl reload nginx
```

---

## 🧪 测试流程

### 1. 先测试远程服务本地可用性

在远程服务器上：
```bash
curl -o /tmp/test.wav \
  -H 'Content-Type: application/json' \
  -d '{"text":"你好世界","spk_audio_path":"/root/index-tts-vllm/examples/voice_01.wav"}' \
  http://localhost:6006/tts_url

file /tmp/test.wav
ls -lh /tmp/test.wav
```

**期望结果：**
- 文件类型：RIFF WAVE audio
- 文件大小：> 50KB

### 2. 测试外部访问

在本地执行：
```bash
cd /Users/micago/Desktop/index/video-auto-dubbing
./test_remote_tts.sh
```

**期望结果：**
- Test 1: Health check 返回 200
- Test 2: /tts_url 端点返回 405（HEAD 方法）或 200（POST 方法）
- Test 3: 生成有效的 WAV 文件

### 3. Worker 端到端测试

1. 启动 Worker
2. 上传一个视频文件
3. 等待任务进入 TTS 步骤
4. 检查 Worker 日志：

**期望日志：**
```
INFO    Using VLLMClient for IndexTTS API
        url=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443

DEBUG   Trying IndexTTS v2 /tts_url
        spk_path=/root/index-tts-vllm/examples/voice_01.wav

INFO    IndexTTS v2 /tts_url success
        content_type=audio/wav
```

---

## 📞 下一步行动

### 立即执行（你需要做的）

1. **SSH 登录远程服务器**
   ```bash
   ssh -p 41069 root@connect.bjb2.seetacloud.com
   ```

2. **执行诊断脚本**
   ```bash
   # 测试本地 API
   curl -I http://localhost:6006/health
   curl -I http://localhost:6006/tts_url

   # 实际合成测试
   curl -o /tmp/test.wav \
     -H 'Content-Type: application/json' \
     -d '{"text":"测试","spk_audio_path":"/root/index-tts-vllm/examples/voice_01.wav"}' \
     http://localhost:6006/tts_url

   file /tmp/test.wav

   # 检查 nginx 配置
   cat /etc/nginx/sites-enabled/default | grep -A 30 "8443"
   ```

3. **把结果贴回来**
   - 本地 API 测试结果（是否生成有效 WAV）
   - nginx 配置内容（8443 部分）
   - 如果有错误，贴出完整的错误信息

### 我会做的（基于你的反馈）

根据你的测试结果：

- **如果本地 API 可用**：修复 nginx 配置
- **如果本地 API 不可用**：检查服务启动参数和日志
- **如果都正常**：继续 Worker 端的集成测试

---

## 📁 生成的文件总览

| 文件 | 用途 |
|------|------|
| `WORKER_INDEXTTSS_V2_INTEGRATION.md` | 详细的集成指南和技术文档 |
| `FINAL_SUMMARY.md` | 本文件（总结和检查清单） |
| `test_remote_tts.sh` | 远程 API 测试脚本 |
| `worker/internal/tts/vllm_client.go` | ✅ 已修改 |
| `worker/internal/tts/client.go` | ✅ 已修改 |

---

## 🎯 验收标准

最终成功的标志：

1. ✅ 远程服务 `http://localhost:6006/tts_url` 可用（在服务器上测试）
2. ✅ 外部访问 `https://...:8443/tts_url` 可用（nginx 配置正确）
3. ✅ Worker 日志显示使用 `IndexTTS v2 /tts_url`
4. ✅ TTS 任务成功完成，生成有效音频
5. ✅ 完整视频处理流程成功

---

**当前状态：** 🟡 等待远程服务器诊断结果
**下一步：** 执行远程服务器检查并反馈结果
