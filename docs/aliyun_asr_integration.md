# 阿里云百炼 ASR 集成文档

## 概述

本项目现已支持阿里云百炼平台的 Qwen ASR 语音识别服务。您可以选择使用火山引擎 ASR 或阿里云 ASR 作为后端服务。

## 功能特性

### 支持的模型
- **qwen3-asr-flash** (默认): 快速同步识别，适合实时场景
- **qwen-audio-asr**: 通用音频识别
- **qwen3-asr-flash-filetrans**: 异步文件转写（带时间戳）

### 支持的语言
- 中文 (zh)
- 英文 (en)
- 粤语 (yue)
- 日语 (ja)
- 韩语 (ko)
- 等其他语言

### 音频格式
- WAV (audio/wav)
- MP3 (audio/mpeg)

## 配置说明

### 环境变量配置

在 `.env` 文件或环境变量中配置以下参数：

```bash
# ASR 后端选择 (volcengine 或 aliyun)
ASR_BACKEND=aliyun

# 阿里云百炼 ASR 配置
ALIYUN_ASR_API_KEY=sk-xxxxxxxxxxxxx           # DashScope API Key (必需)
ALIYUN_ASR_MODEL=qwen3-asr-flash               # 模型名称 (可选，默认: qwen3-asr-flash)
ALIYUN_ASR_ENABLE_ITN=true                     # 启用文本规范化 (可选，默认: true)
ALIYUN_ASR_LANGUAGE=                           # 指定语言代码 (可选，留空自动检测)
ALIYUN_ASR_REQUEST_TIMEOUT=60                  # 请求超时时间(秒) (可选，默认: 60)
```

### 获取 API Key

1. 访问 [阿里云百炼平台](https://dashscope.aliyun.com/)
2. 登录并进入控制台
3. 在 API-KEY 管理页面创建新的 API Key
4. 复制 API Key 并配置到环境变量

## API 说明

### 端点信息

- **中国大陆**: `https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`
- **国际(新加坡)**: `https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`

当前默认使用中国大陆端点。

### 请求参数

```json
{
  "model": "qwen3-asr-flash",
  "input": {
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "audio": "https://your-audio-url.wav"
          }
        ]
      }
    ]
  },
  "parameters": {
    "asr_options": {
      "language": "zh",
      "enable_itn": true
    }
  }
}
```

### 响应格式

```json
{
  "output": {
    "choices": [
      {
        "finish_reason": "stop",
        "message": {
          "role": "assistant",
          "content": [
            {
              "text": "识别的文本内容"
            }
          ],
          "annotations": [
            {
              "type": "audio_info",
              "language": "zh",
              "emotion": "neutral"
            }
          ]
        }
      }
    ]
  },
  "usage": {
    "seconds": 2
  },
  "request_id": "xxx-xxx-xxx"
}
```

## 使用示例

### 代码示例

```go
import (
    "vedio/worker/internal/asr"
    "vedio/shared/config"
)

// 创建阿里云 ASR 客户端
cfg := asr.AliyunASRConfig{
    APIKey:         "sk-xxxxxxxxxxxxx",
    Model:          "qwen3-asr-flash",
    EnableITN:      true,
    Language:       "", // 留空自动检测
    RequestTimeout: 60,
}

client := asr.NewAliyunClient(cfg, logger)

// 执行识别
result, err := client.Recognize(ctx, audioURL, "zh")
if err != nil {
    log.Fatal(err)
}

fmt.Printf("识别结果: %s\n", result.Segments[0].Text)
fmt.Printf("检测语言: %s\n", result.Language)
```

## 与火山引擎 ASR 的对比

| 特性 | 阿里云 ASR | 火山引擎 ASR |
|------|-----------|-------------|
| 调用方式 | 同步 HTTP | 异步轮询 |
| 时间戳 | ❌ 同步API无时间戳 | ✅ 支持 |
| 说话人分离 | ❌ 不支持 | ✅ 支持(最多10人) |
| 情绪检测 | ⚠️ 基础支持 | ✅ 完整支持 |
| 性别检测 | ❌ 不支持 | ✅ 支持 |
| 语言检测 | ✅ 自动检测 | ⚠️ 需要指定 |
| 文本规范化 | ✅ 支持(中英文) | ✅ 支持 |
| 响应速度 | ⚡ 快速 | ⏱️ 需轮询 |
| 集成复杂度 | 🟢 简单 | 🟡 中等 |

## 限制说明

### 当前限制

1. **无时间戳信息**: Qwen ASR 同步API不返回时间戳，所有文本被识别为单个segment
   - 如需时间戳，需使用异步文件转写API (`qwen3-asr-flash-filetrans`)
   - 或继续使用火山引擎 ASR

2. **无说话人分离**: 不支持多说话人识别
   - 系统自动设置默认说话人ID为 `speaker_1`
   - 所有segment使用相同说话人

3. **音频大小限制**: Base64编码的音频文件应小于 10MB

### 适用场景

✅ **适合使用阿里云 ASR**:
- 单说话人音频
- 不需要精确时间戳
- 追求快速响应
- 中英文为主的内容

✅ **建议使用火山引擎 ASR**:
- 多说话人场景
- 需要精确时间戳
- 需要情绪和性别检测
- 需要说话人分离

## 故障排查

### 常见错误

1. **401 Unauthorized**
   ```
   检查 ALIYUN_ASR_API_KEY 是否正确配置
   ```

2. **400 Bad Request**
   ```
   检查音频URL是否可访问
   检查音频格式是否支持 (WAV/MP3)
   ```

3. **Timeout**
   ```
   增加 ALIYUN_ASR_REQUEST_TIMEOUT 值
   检查网络连接
   ```

### 调试技巧

启用详细日志:
```bash
export LOG_LEVEL=debug
```

查看请求详情:
```go
logger.Info("Aliyun ASR request",
    zap.String("audio_url", audioURL),
    zap.String("model", cfg.Model),
)
```

## 未来改进

- [ ] 支持异步文件转写API (带时间戳)
- [ ] 支持流式识别
- [ ] 支持Base64音频输入
- [ ] 支持国际区域端点选择
- [ ] 支持更多音频格式

## 参考资料

- [阿里云百炼 Qwen ASR API 文档](https://help.aliyun.com/zh/model-studio/qwen-asr-api-reference)
- [DashScope SDK 文档](https://help.aliyun.com/zh/model-studio/developer-reference/sdk-overview)
- [API Key 管理](https://dashscope.console.aliyun.com/apiKey)

## 许可证

与项目主许可证相同。
