# IndexTTS OpenAI 兼容 API 部署指南

## 📋 概述

本指南将帮助你在远程服务器上部署 OpenAI 兼容的 TTS API，使 Worker 能够通过标准的 `/v1/audio/speech` 端点调用 IndexTTS。

---

## 🎯 改造目标

- ✅ 在远程服务器添加 `/v1/audio/speech` 端点（OpenAI 兼容）
- ✅ 映射 11 种预定义音色到本地参考音频文件
- ✅ 支持 OpenAI 标准请求格式（model, input, voice, response_format, speed）
- ✅ 返回音频流（无需文件 URL，避免 Gradio 的下载问题）
- ✅ 保持原有 `/tts_url` 端点兼容性

---

## 📁 生成的文件

本次生成了以下文件（位于项目根目录）：

1. **api_server_v2_with_openai.py** - 完整的修改后代码（参考用）
2. **deploy_openai_api.sh** - 自动化部署脚本（推荐使用）
3. **test_openai_api.sh** - API 测试脚本
4. **remote_check.sh** - 服务器状态检查脚本
5. **remote_openai_patch.py** - 补丁代码说明（参考用）

---

## 🚀 部署步骤

### Step 1: SSH 登录远程服务器

```bash
ssh -p 41069 root@connect.bjb2.seetacloud.com
# 密码: xrQ8JU0uChe2
```

### Step 2: 下载并执行部署脚本

**方式 A：复制粘贴脚本内容**（推荐）

在远程服务器上执行以下命令：

```bash
cd /root/index-tts-vllm

# 下载部署脚本（从本地复制）
# 或者直接在服务器上创建脚本文件
cat > deploy_openai.sh << 'EOFSCRIPT'
# 这里粘贴 deploy_openai_api.sh 的全部内容
EOFSCRIPT

chmod +x deploy_openai.sh
bash deploy_openai.sh
```

**方式 B：手动逐步执行**

```bash
cd /root/index-tts-vllm

# 1. 备份原文件
cp api_server_v2.py api_server_v2.py.backup.$(date +%Y%m%d_%H%M%S)

# 2. 停止当前服务
pkill -f "python api_server_v2.py"
sleep 2

# 3. 替换文件
# 将 api_server_v2_with_openai.py 的内容复制到 api_server_v2.py

# 4. 重启服务
nohup python api_server_v2.py > /tmp/api_server_openai.log 2>&1 &

# 5. 检查进程
ps aux | grep api_server_v2
```

### Step 3: 验证部署

**在远程服务器上测试：**

```bash
# 测试 health check
curl http://localhost:6006/health

# 测试 OpenAI API
curl -o /tmp/test.wav \
  -H 'Content-Type: application/json' \
  -d '{"model":"tts-1","input":"你好世界","voice":"alloy","response_format":"wav"}' \
  http://localhost:6006/v1/audio/speech

# 检查生成的音频
file /tmp/test.wav
ls -lh /tmp/test.wav
```

**从本地测试外部访问：**

```bash
cd /Users/micago/Desktop/index/video-auto-dubbing
./test_openai_api.sh
```

---

## 🔍 新增的 API 端点

### 1. POST /v1/audio/speech

OpenAI 兼容的 TTS 合成端点。

**请求示例：**

```bash
curl -X POST https://u861448-ej47-562de107.bjb2.seetacloud.com:8443/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "tts-1",
    "input": "你好，这是一个测试。",
    "voice": "alloy",
    "response_format": "wav",
    "speed": 1.0
  }' \
  --output output.wav
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model | string | ✅ | 模型名称（任意值，暂未使用） |
| input | string | ✅ | 要合成的文本（最大 4096 字符） |
| voice | string | ❌ | 音色 ID（默认 "alloy"） |
| response_format | string | ❌ | 音频格式（"wav" 或 "pcm"，默认 "wav"） |
| speed | float | ❌ | 语速（暂未实现，保留参数） |

**支持的音色：**

| Voice ID | 参考音频文件 | 风格 |
|----------|-------------|------|
| alloy | voice_01.wav | 默认男声 |
| echo | voice_02.wav | 回声效果 |
| fable | voice_03.wav | 叙事风格 |
| onyx | voice_04.wav | 深沉男声 |
| nova | voice_05.wav | 活泼女声 |
| shimmer | voice_06.wav | 柔和女声 |
| ash | voice_07.wav | 中性音色 |
| ballad | voice_08.wav | 歌谣风格 |
| coral | voice_09.wav | 珊瑚音色 |
| sage | voice_10.wav | 智者音色 |
| verse | voice_11.wav | 诗歌风格 |

**响应：**

- Content-Type: `audio/wav`
- 音频二进制流（直接可播放的 WAV 文件）

---

### 2. GET /v1/audio/voices

列出所有可用的音色。

**请求示例：**

```bash
curl https://u861448-ej47-562de107.bjb2.seetacloud.com:8443/v1/audio/voices
```

**响应示例：**

```json
{
  "voices": [
    {"id": "alloy", "name": "Alloy", "language": "multi"},
    {"id": "echo", "name": "Echo", "language": "multi"},
    {"id": "nova", "name": "Nova", "language": "multi"}
  ]
}
```

---

### 3. POST /tts_url（原有端点，保持兼容）

原生 IndexTTS API 端点，保持不变。

---

## ⚙️ Worker 配置

部署完成后，更新 Worker 的环境变量：

```bash
# .env 或 docker-compose.yml
TTS_SERVICE_URL=https://u861448-ej47-562de107.bjb2.seetacloud.com:8443
TTS_BACKEND=vllm  # 保持默认，VLLMClient 会自动尝试 OpenAI 端点
```

**不需要修改 Worker 代码**，`VLLMClient` 已经支持自动 fallback：

1. 首先尝试 native API（`/synthesize`, `/tts`）
2. 失败后自动尝试 OpenAI API（`/audio/speech`, `/v1/audio/speech`）
3. 返回音频流

---

## 🐛 故障排查

### 问题 1: 服务启动失败

```bash
# 查看日志
tail -f /tmp/api_server_openai.log
tail -f /root/index-tts-vllm/logs/api_server_v2.log

# 检查端口占用
lsof -i :6006
```

### 问题 2: /v1/audio/speech 返回 404

```bash
# 确认服务已重启
ps aux | grep api_server_v2

# 测试本地端点
curl -I http://localhost:6006/v1/audio/speech
```

### 问题 3: 音频生成失败

```bash
# 检查参考音频文件是否存在
ls -lh /root/index-tts-vllm/examples/voice_*.wav

# 查看详细错误日志
tail -50 /root/index-tts-vllm/logs/api_server_v2.log
```

### 问题 4: 外部访问失败（从本地测试）

```bash
# 检查 nginx 反代配置（如果 8443 通过 nginx）
# 或者测试直连端口
curl -I https://u861448-ej47-562de107.bjb2.seetacloud.com:8443/health
```

---

## 📊 性能建议

1. **GPU 显存配置**：当前配置
   - `gpu_memory_utilization=0.25`（IndexTTS 模型）
   - `qwenemo_gpu_memory_utilization=0.10`（情感模型）

   如果 GPU 显存充足，可以调整为 0.4 和 0.15 提升性能。

2. **并发控制**：Worker 已实现并发 TTS，建议：
   - 单个任务分段并发度：3-5
   - 服务端无需额外限流

3. **音频缓存**：Worker 已实现音频缓存（存储到 MinIO/OSS），无需服务端缓存。

---

## 🔄 回滚方案

如果新版本出现问题，可以快速回滚：

```bash
cd /root/index-tts-vllm

# 停止当前服务
pkill -f "python api_server_v2.py"

# 恢复备份（使用最新的备份文件）
cp api_server_v2.py.backup.YYYYMMDD_HHMMSS api_server_v2.py

# 重启服务
nohup python api_server_v2.py > /tmp/api_server.log 2>&1 &
```

---

## ✅ 验收清单

- [ ] 远程服务器 `/v1/audio/speech` 返回 200（不是 404）
- [ ] 本地测试脚本生成有效的 WAV 文件
- [ ] Worker 能通过 OpenAI API 成功合成音频
- [ ] 端到端任务（upload → ASR → translate → TTS → merge）成功

---

## 📞 下一步

完成部署后，执行以下操作：

1. **在远程服务器运行部署脚本**
2. **在本地运行测试脚本** `./test_openai_api.sh`
3. **启动一个完整的视频处理任务**，验证 TTS 步骤
4. **查看 Worker 日志**，确认使用了 `/v1/audio/speech` 端点

---

## 📄 相关文档

- OpenAI Audio API 参考: https://platform.openai.com/docs/api-reference/audio/createSpeech
- IndexTTS 项目: https://github.com/IndexTeam/index-tts-vllm
- Worker TTS Client 代码: `worker/internal/tts/vllm_client.go`

---

**部署时间预估：** 5-10 分钟
**技术支持：** 如有问题请查看故障排查章节
