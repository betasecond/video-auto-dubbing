# 🎤 检测到的 TTS 服务信息

## 服务类型
**Gradio IndexTTS 服务** ✅

## 服务地址
`https://u861448-ej47-562de107.bjb2.seetacloud.com:8443`

## API 端点
- **主界面**: `/` (返回 HTML Web 界面)
- **API 信息**: `/gradio_api/info` (返回 API 结构信息) ✅
- **语音合成**: `/gradio_api/call/gen_single` (主要 TTS API 端点)

## 支持功能
根据 API 信息分析，该服务支持：

1. **情感控制方式**:
   - 与音色参考音频相同
   - 使用情感参考音频
   - 使用情感向量控制
   - 使用情感描述文本控制

2. **情感类型**:
   - 喜 (joy)
   - 怒 (anger)
   - 哀 (sadness)
   - 惧 (fear)
   - 厌恶 (disgust)
   - 低落 (depression)
   - 惊喜 (surprise)
   - 平静 (calm)

3. **语音合成参数**:
   - 音色参考音频上传
   - 情感参考音频上传
   - 情感权重 (0.0-1.6)
   - 分句最大Token数 (20-600)
   - 采样参数 (top_p, top_k, temperature 等)

## 集成建议

### 1. 连接测试
✅ 使用 `/gradio_api/info` 端点进行连接测试 (返回 JSON)
❌ 不要使用 `/` 端点 (返回 HTML，会导致 JSON 解析错误)

### 2. TTS API 调用
主要 API: `POST /gradio_api/call/gen_single`

### 3. 参数映射
- **输入文本**: `text` 参数
- **音色音频**: `prompt` 参数 (文件上传)
- **情感控制**: `emo_control_method` + 相应参数

## 修复方案

更新 TTS 连接测试逻辑：
1. 优先测试 `/gradio_api/info` 端点
2. 检测到 JSON 响应说明是 Gradio API
3. 避免使用返回 HTML 的端点进行 API 测试