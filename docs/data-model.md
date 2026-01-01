# 数据模型设计

## 1. 数据库表结构

### 1.1 tasks 表

存储任务主记录。

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    progress INTEGER NOT NULL DEFAULT 0,  -- 0-100
    error TEXT,
    source_video_key VARCHAR(255) NOT NULL,  -- MinIO key
    source_language VARCHAR(10) NOT NULL DEFAULT 'zh',  -- 源语言代码
    target_language VARCHAR(10) NOT NULL DEFAULT 'en',  -- 目标语言代码
    output_video_key VARCHAR(255),  -- 最终输出视频 key
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
```

**状态枚举：**
- `created`: 已创建，等待处理
- `queued`: 已入队
- `running`: 处理中
- `failed`: 处理失败
- `done`: 处理完成

### 1.2 task_steps 表

存储任务步骤执行记录，用于追踪和统计。

```sql
CREATE TABLE task_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    step VARCHAR(50) NOT NULL,  -- extract_audio, asr, translate, tts, mux_video
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, running, succeeded, failed
    attempt INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    error TEXT,
    metrics_json JSONB,  -- 存储步骤相关指标，如耗时、处理量等
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_id, step, attempt)
);

CREATE INDEX idx_task_steps_task_id ON task_steps(task_id);
CREATE INDEX idx_task_steps_status ON task_steps(status);
CREATE INDEX idx_task_steps_step ON task_steps(step);
```

**步骤枚举：**
- `extract_audio`: 提取音频
- `asr`: 语音识别
- `translate`: 机器翻译
- `tts`: 语音合成
- `mux_video`: 视频合成

**状态枚举：**
- `pending`: 等待执行
- `running`: 执行中
- `succeeded`: 执行成功
- `failed`: 执行失败

### 1.3 segments 表

存储视频分段信息，包括原始文本、翻译文本、时间轴等。

```sql
CREATE TABLE segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,  -- 分段序号
    start_ms INTEGER NOT NULL,  -- 开始时间（毫秒）
    end_ms INTEGER NOT NULL,  -- 结束时间（毫秒）
    duration_ms INTEGER NOT NULL,  -- 时长（毫秒）
    src_text TEXT NOT NULL,  -- 源语言文本
    mt_text TEXT,  -- 翻译后文本
    tts_params_json JSONB,  -- TTS 参数，如 speaker_id, target_duration_ms 等
    tts_audio_key VARCHAR(255),  -- TTS 生成的音频文件 key
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_id, idx)
);

CREATE INDEX idx_segments_task_id ON segments(task_id);
CREATE INDEX idx_segments_task_id_idx ON segments(task_id, idx);
```

**tts_params_json 示例：**
```json
{
  "speaker_id": "default",
  "target_duration_ms": 1500,
  "prosody_control": {
    "speed": 1.0,
    "pitch": 1.0
  }
}
```

## 2. 对象存储（MinIO）Key 规范

### 2.1 Key 命名规则

采用层级结构：`{resource_type}/{task_id}/{filename}`

### 2.2 资源类型与 Key 示例

| 资源类型 | Key 格式 | 示例 | 说明 |
|---------|---------|------|------|
| 原始视频 | `videos/{task_id}/source.mp4` | `videos/550e8400-e29b-41d4-a716-446655440000/source.mp4` | 用户上传的原始视频 |
| 提取音频 | `audios/{task_id}/source.wav` | `audios/550e8400-e29b-41d4-a716-446655440000/source.wav` | 从视频提取的音频 |
| ASR 结果 | `asr/{task_id}/asr.json` | `asr/550e8400-e29b-41d4-a716-446655440000/asr.json` | 语音识别结果（含时间戳） |
| 字幕文件 | `subs/{task_id}/subtitles.vtt` | `subs/550e8400-e29b-41d4-a716-446655440000/subtitles.vtt` | WebVTT 格式字幕 |
| TTS 音频 | `tts/{task_id}/segment_{idx}.wav` | `tts/550e8400-e29b-41d4-a716-446655440000/segment_0.wav` | 单个分段合成音频 |
| TTS 合并音频 | `tts/{task_id}/dub.wav` | `tts/550e8400-e29b-41d4-a716-446655440000/dub.wav` | 所有分段合并后的配音音频 |
| 最终视频 | `outputs/{task_id}/final.mp4` | `outputs/550e8400-e29b-41d4-a716-446655440000/final.mp4` | 合成后的最终视频 |

### 2.3 ASR 结果 JSON 格式

```json
{
  "segments": [
    {
      "idx": 0,
      "start_ms": 0,
      "end_ms": 1500,
      "text": "你好，世界"
    },
    {
      "idx": 1,
      "start_ms": 1500,
      "end_ms": 3000,
      "text": "这是一个测试"
    }
  ],
  "language": "zh",
  "duration_ms": 3000
}
```

### 2.4 生命周期管理

**临时文件清理策略：**
- 任务完成后保留 7 天
- 任务失败后保留 3 天
- 可通过定时任务清理过期文件

**保留文件：**
- 原始视频：用户决定（可提供删除接口）
- 最终输出视频：长期保留
- 中间文件（音频、ASR JSON）：任务完成后可清理

