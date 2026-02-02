# 多说话人声音复刻指南

## 🎯 核心优化

### 问题
之前的方案中，每个分段都需要单独复刻声音，导致：
- ❌ 大量重复的复刻请求
- ❌ 浪费 API 配额
- ❌ 处理时间过长

### 解决方案
**voice_id 复用机制**：同一个说话人只复刻一次，所有分段共享 voice_id。

---

## 📊 工作流程

### 1. ASR 识别多说话人

```json
{
  "segments": [
    {
      "speaker_id": "speaker_0",
      "start_time_ms": 0,
      "end_time_ms": 3000,
      "text": "大家好，我是主持人。"
    },
    {
      "speaker_id": "speaker_1",
      "start_time_ms": 3000,
      "end_time_ms": 6000,
      "text": "你好，我是嘉宾。"
    },
    {
      "speaker_id": "speaker_0",
      "start_time_ms": 6000,
      "end_time_ms": 9000,
      "text": "欢迎来到我们的节目。"
    }
  ]
}
```

### 2. 按 speaker_id 分组

```python
{
  "speaker_0": [segment_1, segment_3],  # 主持人
  "speaker_1": [segment_2]              # 嘉宾
}
```

### 3. 为每个说话人复刻声音

```python
# speaker_0 的复刻流程
1. 提取 speaker_0 的所有音频片段（0-3s, 6-9s）
2. 合并成一个音频文件（6秒）
3. 调用 enroll_voice() → 获得 voice_id_0 = "vc_abc123"

# speaker_1 的复刻流程
1. 提取 speaker_1 的音频片段（3-6s）
2. 调用 enroll_voice() → 获得 voice_id_1 = "vc_def456"
```

### 4. 使用 voice_id 合成

```python
# segment_1 (speaker_0)
synthesize("大家好，我是主持人。", voice="vc_abc123")

# segment_2 (speaker_1)
synthesize("你好，我是嘉宾。", voice="vc_def456")

# segment_3 (speaker_0) - 复用 voice_id_0
synthesize("欢迎来到我们的节目。", voice="vc_abc123")
```

---

## 🔑 关键代码

### 1. Segment 模型（新增 voice_id 字段）

```python
class Segment(Base):
    # ... 其他字段

    # ASR 元数据
    speaker_id: str | None  # 说话人 ID（来自 ASR）

    # TTS 配置
    voice_id: str | None  # 声音复刻 ID（可复用）
    audio_path: str | None  # 合成的音频路径
```

### 2. VoiceService（声音复刻管理）

```python
class VoiceService:
    def enroll_speaker_from_segments(
        self,
        task_id: UUID,
        speaker_id: str,
        audio_path: str,
        segments: list[dict],
    ) -> str | None:
        """
        从分段中提取说话人音频并复刻声音

        流程:
        1. 提取该说话人的所有音频片段
        2. 合并成一个音频文件（10-20秒为佳）
        3. 调用 DashScope 声音复刻 API
        4. 返回 voice_id
        """
        # ...

    def get_or_create_voice_id(
        self,
        speaker_id: str,
        cache: dict[str, str],
        # ...
    ) -> str | None:
        """
        获取或创建 voice_id（带缓存）

        同一个任务中，同一个 speaker_id 只复刻一次
        """
        if speaker_id in cache:
            return cache[speaker_id]  # 复用

        voice_id = self.enroll_speaker_from_segments(...)
        cache[speaker_id] = voice_id
        return voice_id
```

### 3. Celery 任务（集成多说话人复刻）

```python
@celery_app.task
def synthesize_audio_task(task_id: str):
    # 1. 按 speaker_id 分组
    segments_by_speaker = defaultdict(list)
    for seg in segments:
        speaker_id = seg.speaker_id or "default"
        segments_by_speaker[speaker_id].append(seg)

    # 2. 为每个说话人复刻声音
    voice_cache = {}  # speaker_id -> voice_id
    for speaker_id, speaker_segments in segments_by_speaker.items():
        voice_id = voice_service.get_or_create_voice_id(
            speaker_id=speaker_id,
            segments=speaker_segments,
            cache=voice_cache,
        )

    # 3. 使用对应的 voice_id 合成
    for segment in segments:
        speaker_id = segment.speaker_id or "default"
        voice_id = voice_cache.get(speaker_id)

        audio = tts_client.synthesize(
            segment.translated_text,
            voice=voice_id
        )

        # 保存 voice_id 到数据库
        segment.voice_id = voice_id
        segment.audio_path = upload_to_oss(audio)
```

---

## 📈 性能对比

### 之前的方案（每分段复刻）

```
假设 100 个分段，2 个说话人：
- 复刻次数: 100 次
- 复刻时间: 100 × 10s = 1000s (约 17 分钟)
- API 调用: 100 次
```

### 优化后的方案（按说话人复刻）

```
假设 100 个分段，2 个说话人：
- 复刻次数: 2 次
- 复刻时间: 2 × 10s = 20s
- API 调用: 2 次

性能提升: 50× 🚀
```

---

## 🔧 配置示例

### 使用系统音色（简单）

```bash
TTS_MODEL=cosyvoice-v1
TTS_VOICE=longxiaochun
```

**特点:**
- ✅ 无需复刻，开箱即用
- ❌ 所有说话人使用相同音色

### 使用声音复刻（高级）

```bash
TTS_MODEL=qwen3-tts-vc-realtime-2026-01-15
```

**特点:**
- ✅ 自动为每个说话人复刻声音
- ✅ voice_id 自动复用
- ✅ 保留原声特征

---

## 📝 数据库 Schema

### segments 表

| 字段 | 类型 | 说明 |
|------|------|------|
| `speaker_id` | String | 说话人 ID（来自 ASR） |
| `voice_id` | String | 声音复刻 ID（vc_xxx 格式） |
| `audio_path` | String | TTS 合成的音频路径 |

**查询示例:**

```sql
-- 查看任务的所有说话人
SELECT DISTINCT speaker_id, voice_id
FROM segments
WHERE task_id = 'xxx';

-- 统计每个说话人的分段数
SELECT speaker_id, COUNT(*) as segment_count
FROM segments
WHERE task_id = 'xxx'
GROUP BY speaker_id;
```

---

## 🎯 最佳实践

### 1. 音频片段选择

为了获得最佳的声音复刻效果：
- ✅ 提取 10-20 秒的音频（不要太短或太长）
- ✅ 确保音频清晰，无噪音
- ✅ 包含多种音节和语调

### 2. 说话人识别

ASR 提供的 `speaker_id` 通常是：
- `speaker_0`, `speaker_1`, `speaker_2` 等
- 按出现顺序分配
- 同一个人的分段会有相同的 `speaker_id`

### 3. 降级策略

如果声音复刻失败：
```python
if not voice_id:
    # 降级到系统音色
    audio = tts_client.synthesize(text, voice="longxiaochun")
```

### 4. 缓存管理

voice_id 是任务级别的缓存：
```python
# 同一个任务内复用
voice_cache = {}  # speaker_id -> voice_id

# 不同任务之间不共享
# 每个任务都会重新复刻
```

---

## 🐛 故障排查

### 问题 1: 所有分段使用相同音色

**原因:** ASR 没有返回 `speaker_id`

**解决:**
```python
# 检查 ASR 响应
for sentence in asr_result.sentences:
    print(f"speaker_id: {sentence.speaker_id}")  # 应该不为 None

# 如果为 None，检查 ASR 配置
asr_client.transcribe(
    audio_path,
    enable_speaker_diarization=True  # 启用说话人分离
)
```

### 问题 2: 声音复刻失败

**原因:** 音频片段太短或质量差

**解决:**
```python
# 检查合并后的音频时长
logger.info(f"Merged audio duration: {total_duration_ms}ms")

# 建议: 至少 10 秒
if total_duration_ms < 10000:
    logger.warning("Audio too short for voice cloning")
```

### 问题 3: voice_id 未保存到数据库

**检查:**
```python
# 查看分段的 voice_id
SELECT id, speaker_id, voice_id FROM segments WHERE task_id = 'xxx';

# 应该显示: vc_xxx 格式的 ID
```

---

## 📞 API 响应示例

### GET /api/v1/tasks/{task_id}

```json
{
  "id": "task-uuid",
  "status": "completed",
  "segments": [
    {
      "segment_index": 0,
      "speaker_id": "speaker_0",
      "voice_id": "vc_abc123",
      "original_text": "大家好",
      "translated_text": "Hello everyone",
      "audio_path": "task_xxx/segments/segment_0000.mp3"
    },
    {
      "segment_index": 1,
      "speaker_id": "speaker_1",
      "voice_id": "vc_def456",
      "original_text": "你好",
      "translated_text": "Hi",
      "audio_path": "task_xxx/segments/segment_0001.mp3"
    },
    {
      "segment_index": 2,
      "speaker_id": "speaker_0",
      "voice_id": "vc_abc123",  // 复用 speaker_0 的 voice_id
      "original_text": "欢迎",
      "translated_text": "Welcome",
      "audio_path": "task_xxx/segments/segment_0002.mp3"
    }
  ]
}
```

---

## 🚀 未来优化

1. **跨任务复用 voice_id**
   - 如果用户经常使用相同的音频源
   - 可以建立 voice_id 库

2. **自动说话人聚类**
   - 使用音频指纹技术
   - 自动识别相同说话人

3. **声音质量评估**
   - 评估复刻效果
   - 自动选择最佳音频片段

---

祝您使用愉快！🎉
