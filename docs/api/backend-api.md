# Video Dubbing API 文档

**版本**: 2.0.0
**基础 URL**: `http://localhost:8000/api/v1`
**协议**: HTTP/HTTPS

---

## 目录

- [概述](#概述)
- [认证](#认证)
- [错误处理](#错误处理)
- [API 端点](#api-端点)
  - [任务管理](#任务管理)
  - [监控与健康检查](#监控与健康检查)
- [数据模型](#数据模型)
- [工作流程](#工作流程)
- [配置说明](#配置说明)

---

## 概述

视频自动配音系统 API 提供了基于阿里云百炼平台（DashScope）的视频配音服务，支持：

- 🎬 视频上传与处理
- 🎤 语音识别（ASR）- 支持多语言
- 🌐 文本翻译 - 基于 LLM
- 🔊 语音合成（TTS）- 支持声音复刻
- 👥 多说话人识别与处理
- 📦 阿里云 OSS 存储
- 🔄 异步任务处理（Celery）

### 技术架构

- **Web 框架**: FastAPI + Uvicorn
- **数据库**: PostgreSQL + SQLAlchemy 2.0
- **任务队列**: Celery + Redis
- **AI 服务**: 阿里百炼 DashScope (ASR, LLM, TTS)
- **对象存储**: 阿里云 OSS
- **依赖管理**: uv

---

## 认证

**当前版本**: 无需认证（开发阶段）

> ⚠️ **注意**: 生产环境应实现 API Key 或 JWT 认证机制。

---

## 错误处理

### 标准错误响应格式

```json
{
  "error": "错误类型",
  "detail": "详细错误信息"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无内容） |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## API 端点

### 基础端点

#### 1. 获取 API 信息

```http
GET /api/v1/
```

**响应示例**:
```json
{
  "message": "Video Dubbing API v2",
  "endpoints": {
    "docs": "/api/v1/docs",
    "health": "/health",
    "tasks": "/api/v1/tasks"
  }
}
```

#### 2. 健康检查

```http
GET /health
```

**响应示例**:
```json
{
  "status": "healthy",
  "version": "2.0.0"
}
```

---

### 任务管理

#### 1. 创建配音任务

```http
POST /api/v1/tasks
Content-Type: multipart/form-data
```

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `video` | File | ✅ | 视频文件（支持 mp4, avi, mov, mkv, flv） |
| `source_language` | string | ✅ | 源语言代码（zh, en, ja, ko, es, fr, de, ru） |
| `target_language` | string | ✅ | 目标语言代码 |
| `title` | string | ❌ | 任务标题（默认使用文件名） |

**cURL 示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/tasks" \
  -F "video=@/path/to/video.mp4" \
  -F "source_language=zh" \
  -F "target_language=en" \
  -F "title=我的配音任务"
```

**响应示例** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "我的配音任务",
  "source_language": "zh",
  "target_language": "en",
  "status": "pending",
  "progress": 0,
  "current_step": null,
  "error_message": null,
  "segment_count": 0,
  "created_at": "2026-02-02T10:00:00Z",
  "updated_at": "2026-02-02T10:00:00Z",
  "completed_at": null
}
```

**错误响应**:
```json
// 400 Bad Request - 无效的语言代码
{
  "error": "Invalid source_language: invalid"
}

// 400 Bad Request - 无效的文件
{
  "error": "Invalid video file"
}

// 500 Internal Server Error
{
  "error": "Failed to create task: 详细错误信息"
}
```

---

#### 2. 获取任务列表

```http
GET /api/v1/tasks?page=1&page_size=20&status=processing
```

**查询参数**:

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | integer | ❌ | 1 | 页码（从 1 开始） |
| `page_size` | integer | ❌ | 20 | 每页数量（1-100） |
| `status` | string | ❌ | null | 状态过滤（见下方状态列表） |

**任务状态列表**:
- `pending` - 等待处理
- `extracting` - 提取音频中
- `transcribing` - 语音识别中
- `translating` - 翻译中
- `synthesizing` - 语音合成中
- `muxing` - 视频合成中
- `completed` - 已完成
- `failed` - 失败

**cURL 示例**:
```bash
curl "http://localhost:8000/api/v1/tasks?page=1&page_size=10&status=completed"
```

**响应示例** (200 OK):
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "我的配音任务",
      "source_language": "zh",
      "target_language": "en",
      "status": "completed",
      "progress": 100,
      "current_step": "completed",
      "error_message": null,
      "segment_count": 15,
      "created_at": "2026-02-02T10:00:00Z",
      "updated_at": "2026-02-02T10:15:00Z",
      "completed_at": "2026-02-02T10:15:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

**错误响应**:
```json
// 400 Bad Request - 无效的分页参数
{
  "error": "Page must be >= 1"
}

// 400 Bad Request - 无效的页面大小
{
  "error": "Page size must be between 1 and 100"
}
```

---

#### 3. 获取任务详情

```http
GET /api/v1/tasks/{task_id}
```

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `task_id` | UUID | 任务 ID |

**cURL 示例**:
```bash
curl "http://localhost:8000/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000"
```

**响应示例** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "我的配音任务",
  "source_language": "zh",
  "target_language": "en",
  "status": "completed",
  "progress": 100,
  "current_step": "completed",
  "error_message": null,
  "segment_count": 2,
  "created_at": "2026-02-02T10:00:00Z",
  "updated_at": "2026-02-02T10:15:00Z",
  "completed_at": "2026-02-02T10:15:00Z",
  "video_duration_ms": 120000,
  "input_video_path": "videos/550e8400.../input.mp4",
  "extracted_audio_path": "videos/550e8400.../audio.wav",
  "output_video_path": "videos/550e8400.../output.mp4",
  "celery_task_id": "abc123-def456",
  "segments": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "segment_index": 0,
      "start_time_ms": 0,
      "end_time_ms": 5000,
      "original_text": "大家好",
      "translated_text": "Hello everyone",
      "speaker_id": "spk_0",
      "emotion": null,
      "confidence": 0.95,
      "voice_id": "vc_xxx123",
      "audio_path": "videos/550e8400.../segments/0.mp3",
      "created_at": "2026-02-02T10:05:00Z",
      "updated_at": "2026-02-02T10:10:00Z"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440002",
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "segment_index": 1,
      "start_time_ms": 5000,
      "end_time_ms": 10000,
      "original_text": "欢迎来到这里",
      "translated_text": "Welcome here",
      "speaker_id": "spk_1",
      "emotion": null,
      "confidence": 0.92,
      "voice_id": "vc_xxx456",
      "audio_path": "videos/550e8400.../segments/1.mp3",
      "created_at": "2026-02-02T10:05:00Z",
      "updated_at": "2026-02-02T10:12:00Z"
    }
  ]
}
```

**错误响应**:
```json
// 404 Not Found
{
  "error": "Task not found"
}
```

---

#### 4. 获取任务结果下载链接

```http
GET /api/v1/tasks/{task_id}/result
```

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `task_id` | UUID | 任务 ID |

**cURL 示例**:
```bash
curl "http://localhost:8000/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000/result"
```

**响应示例** (200 OK):
```json
{
  "download_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/videos/.../output.mp4?Expires=1738502400&OSSAccessKeyId=...&Signature=...",
  "expires_in": 3600
}
```

**错误响应**:
```json
// 404 Not Found - 任务不存在
{
  "error": "Task not found"
}

// 400 Bad Request - 任务未完成
{
  "error": "Task not completed yet. Current status: processing"
}

// 404 Not Found - 输出文件不存在
{
  "error": "Output video not found"
}
```

---

#### 5. 删除任务

```http
DELETE /api/v1/tasks/{task_id}
```

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `task_id` | UUID | 任务 ID |

**cURL 示例**:
```bash
curl -X DELETE "http://localhost:8000/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000"
```

**响应**: 204 No Content（无响应体）

**错误响应**:
```json
// 404 Not Found
{
  "error": "Task not found"
}
```

> ⚠️ **注意**: 删除任务会同时删除数据库记录和 OSS 上的所有相关文件（输入视频、音频、分段音频、输出视频）。

---

### 监控与健康检查

#### 1. 服务健康检查

```http
GET /api/v1/monitoring/health
```

**响应示例** (200 OK):
```json
{
  "status": "healthy",
  "services": {
    "database": true,
    "redis": true,
    "ffmpeg": true
  },
  "version": "2.0.0"
}
```

**说明**:
- `database`: PostgreSQL 数据库连接状态
- `redis`: Redis 连接状态（Celery 后端）
- `ffmpeg`: FFmpeg 工具可用性

---

#### 2. 系统统计信息

```http
GET /api/v1/monitoring/stats
```

**响应示例** (200 OK):
```json
{
  "tasks": {
    "total": 100,
    "pending": 10,
    "extracting": 2,
    "transcribing": 3,
    "translating": 1,
    "synthesizing": 2,
    "muxing": 1,
    "completed": 75,
    "failed": 6
  },
  "workers": {
    "active": 4,
    "registered": [
      "celery@worker1",
      "celery@worker2"
    ]
  }
}
```

**错误响应**:
```json
{
  "tasks": {
    "error": "数据库连接失败"
  },
  "workers": {
    "error": "无法连接到 Celery"
  }
}
```

---

#### 3. Celery 任务队列检查

```http
GET /api/v1/monitoring/celery/inspect
```

**响应示例** (200 OK):
```json
{
  "active": {
    "celery@worker1": [
      {
        "id": "abc123",
        "name": "process_video_pipeline",
        "args": ["550e8400-e29b-41d4-a716-446655440000"],
        "time_start": 1738488000.0
      }
    ]
  },
  "scheduled": {},
  "reserved": {},
  "stats": {
    "celery@worker1": {
      "pool": {
        "max-concurrency": 4,
        "processes": [1234, 1235, 1236, 1237]
      }
    }
  }
}
```

**错误响应**:
```json
{
  "error": "无法连接到 Celery"
}
```

---

## 数据模型

### Task（任务）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 任务唯一标识 |
| `title` | string \| null | 任务标题 |
| `source_language` | string | 源语言代码 |
| `target_language` | string | 目标语言代码 |
| `status` | TaskStatus | 任务状态（枚举） |
| `progress` | integer | 进度百分比（0-100） |
| `current_step` | string \| null | 当前步骤名称 |
| `error_message` | string \| null | 错误信息 |
| `segment_count` | integer | 分段数量 |
| `video_duration_ms` | integer \| null | 视频时长（毫秒） |
| `input_video_path` | string \| null | 输入视频路径（OSS） |
| `extracted_audio_path` | string \| null | 提取的音频路径 |
| `output_video_path` | string \| null | 输出视频路径 |
| `celery_task_id` | string \| null | Celery 任务 ID |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |
| `completed_at` | datetime \| null | 完成时间 |
| `segments` | Segment[] | 分段列表（仅详情接口） |

### Segment（分段）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 分段唯一标识 |
| `task_id` | UUID | 所属任务 ID |
| `segment_index` | integer | 分段索引（从 0 开始） |
| `start_time_ms` | integer | 开始时间（毫秒） |
| `end_time_ms` | integer | 结束时间（毫秒） |
| `original_text` | string \| null | 原始文本（ASR 识别结果） |
| `translated_text` | string \| null | 翻译文本 |
| `speaker_id` | string \| null | 说话人 ID（如 `spk_0`） |
| `emotion` | string \| null | 情感标签 |
| `confidence` | float \| null | 识别置信度（0-1） |
| `voice_id` | string \| null | 声音复刻 ID（如 `vc_xxx123`） |
| `audio_path` | string \| null | 合成音频路径（OSS） |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

### TaskStatus（任务状态枚举）

| 值 | 说明 |
|----|------|
| `pending` | 等待处理 |
| `extracting` | 提取音频中 |
| `transcribing` | 语音识别中 |
| `translating` | 翻译中 |
| `synthesizing` | 语音合成中 |
| `muxing` | 视频合成中 |
| `completed` | 已完成 |
| `failed` | 失败 |

---

## 工作流程

### 完整的视频配音流程

```
1️⃣ 用户上传视频
   ↓
2️⃣ 创建任务记录
   ↓
3️⃣ 上传视频到 OSS
   ↓
4️⃣ 提交 Celery 任务链
   ↓
┌──────────────────────────────────────┐
│  Celery 异步处理流程                   │
├──────────────────────────────────────┤
│  Step 1: extract_audio                │
│  - 从 OSS 下载视频                     │
│  - 使用 FFmpeg 提取音频                │
│  - 上传音频到 OSS                      │
│  - 获取视频时长                        │
│                                        │
│  Step 2: transcribe_audio              │
│  - 调用 DashScope ASR API              │
│  - 识别语音并分段                      │
│  - 创建分段记录（含说话人信息）         │
│                                        │
│  Step 3: translate_segments            │
│  - 调用 DashScope LLM API              │
│  - 翻译每个分段的文本                  │
│                                        │
│  Step 4: synthesize_audio              │
│  - 按说话人分组                        │
│  - 为每个说话人复刻声音（可选）         │
│  - 使用对应 voice_id 合成音频          │
│  - 上传分段音频到 OSS                  │
│                                        │
│  Step 5: mux_video                     │
│  - 合并所有分段音频                    │
│  - 使用 FFmpeg 替换视频音轨            │
│  - 上传最终视频到 OSS                  │
└──────────────────────────────────────┘
   ↓
5️⃣ 任务完成，可下载结果
```

### 状态转换图

```
pending → extracting → transcribing → translating → synthesizing → muxing → completed
  ↓           ↓              ↓             ↓              ↓           ↓
  └───────────┴──────────────┴─────────────┴──────────────┴───────────┴──→ failed
```

---

## 配置说明

### 环境变量配置

创建 `.env` 文件并配置以下参数：

```bash
# ==================== 应用配置 ====================
DEBUG=true
API_PREFIX=/api/v1

# ==================== 数据库配置 ====================
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dubbing
DB_USER=dubbing
DB_PASSWORD=dubbing123

# ==================== Redis 配置 ====================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# ==================== 阿里云 OSS ====================
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=your-bucket-name
OSS_ACCESS_KEY_ID=your-access-key-id
OSS_ACCESS_KEY_SECRET=your-access-key-secret
OSS_PUBLIC_DOMAIN=https://your-bucket.oss-cn-hangzhou.aliyuncs.com
OSS_PREFIX=videos/
OSS_USE_SSL=true

# ==================== 阿里百炼 DashScope ====================
DASHSCOPE_API_KEY=your-dashscope-api-key

# ASR 配置
ASR_MODEL=sensevoice-v1
ASR_LANGUAGE_HINTS=["zh", "en"]

# LLM 配置
DASHSCOPE_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_LLM_MODEL=qwen-turbo
LLM_MAX_TOKENS=2000

# TTS 配置
# 模式选择：
# - cosyvoice-v1: 系统音色模式
# - qwen3-tts-vc-realtime-2026-01-15: 声音复刻模式
TTS_MODEL=qwen3-tts-vc-realtime-2026-01-15
TTS_VOICE=longxiaochun  # 系统音色名称或 voice_id
TTS_FORMAT=mp3

# ==================== 处理配置 ====================
MAX_UPLOAD_SIZE=524288000  # 500MB
ALLOWED_VIDEO_FORMATS=["mp4", "avi", "mov", "mkv", "flv"]
WORKER_CONCURRENCY=4
TASK_TIMEOUT=3600  # 1小时

# ==================== CORS 配置 ====================
CORS_ORIGINS=["http://localhost:3000", "http://localhost"]

# ==================== 日志配置 ====================
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### 支持的语言代码

| 代码 | 语言 |
|------|------|
| `zh` | 中文 |
| `en` | 英语 |
| `ja` | 日语 |
| `ko` | 韩语 |
| `es` | 西班牙语 |
| `fr` | 法语 |
| `de` | 德语 |
| `ru` | 俄语 |

### TTS 模式说明

#### 1. 系统音色模式（cosyvoice-v1）

使用预定义的音色，无需声音复刻。

```bash
TTS_MODEL=cosyvoice-v1
TTS_VOICE=longxiaochun  # 可选音色见阿里云文档
```

**优点**:
- 快速，无需复刻过程
- 音质稳定

**缺点**:
- 所有说话人使用同一音色
- 无法保留原视频说话人特征

#### 2. 声音复刻模式（qwen3-tts-vc-realtime-2026-01-15）

根据原视频中的说话人自动复刻声音。

```bash
TTS_MODEL=qwen3-tts-vc-realtime-2026-01-15
TTS_VOICE=  # 留空或使用 voice_id
```

**优点**:
- 保留原视频说话人特征
- 支持多说话人
- 更自然的配音效果

**缺点**:
- 处理时间较长
- 需要足够的说话人音频样本

**工作流程**:
1. ASR 识别时标记每个分段的 `speaker_id`
2. 按 `speaker_id` 分组提取音频片段
3. 为每个说话人调用声音复刻 API
4. 获取 `voice_id` 并缓存
5. 使用对应 `voice_id` 合成每个分段

---

## 使用示例

### Python 示例

```python
import requests
from pathlib import Path

# API 基础 URL
BASE_URL = "http://localhost:8000/api/v1"

# 1. 创建任务
def create_task(video_path: str, source_lang: str, target_lang: str):
    url = f"{BASE_URL}/tasks"

    with open(video_path, "rb") as f:
        files = {"video": f}
        data = {
            "source_language": source_lang,
            "target_language": target_lang,
            "title": Path(video_path).stem,
        }

        response = requests.post(url, files=files, data=data)
        response.raise_for_status()

        return response.json()

# 2. 查询任务状态
def get_task(task_id: str):
    url = f"{BASE_URL}/tasks/{task_id}"
    response = requests.get(url)
    response.raise_for_status()

    return response.json()

# 3. 下载结果
def download_result(task_id: str, output_path: str):
    # 获取下载链接
    url = f"{BASE_URL}/tasks/{task_id}/result"
    response = requests.get(url)
    response.raise_for_status()

    download_url = response.json()["download_url"]

    # 下载文件
    video_response = requests.get(download_url)
    video_response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(video_response.content)

    print(f"视频已下载到: {output_path}")

# 使用示例
if __name__ == "__main__":
    # 创建任务
    task = create_task(
        video_path="./test.mp4",
        source_lang="zh",
        target_lang="en"
    )

    task_id = task["id"]
    print(f"任务已创建: {task_id}")

    # 轮询任务状态
    import time
    while True:
        task_info = get_task(task_id)
        status = task_info["status"]
        progress = task_info["progress"]

        print(f"状态: {status}, 进度: {progress}%")

        if status == "completed":
            print("任务完成！")
            break
        elif status == "failed":
            print(f"任务失败: {task_info['error_message']}")
            break

        time.sleep(5)  # 每 5 秒查询一次

    # 下载结果
    if status == "completed":
        download_result(task_id, f"./output_{task_id}.mp4")
```

### JavaScript/TypeScript 示例

```typescript
// types.ts
export interface Task {
  id: string;
  title: string | null;
  source_language: string;
  target_language: string;
  status: TaskStatus;
  progress: number;
  current_step: string | null;
  error_message: string | null;
  segment_count: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export type TaskStatus =
  | "pending"
  | "extracting"
  | "transcribing"
  | "translating"
  | "synthesizing"
  | "muxing"
  | "completed"
  | "failed";

// api.ts
const BASE_URL = "http://localhost:8000/api/v1";

export async function createTask(
  video: File,
  sourceLanguage: string,
  targetLanguage: string,
  title?: string
): Promise<Task> {
  const formData = new FormData();
  formData.append("video", video);
  formData.append("source_language", sourceLanguage);
  formData.append("target_language", targetLanguage);
  if (title) formData.append("title", title);

  const response = await fetch(`${BASE_URL}/tasks`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Failed to create task: ${response.statusText}`);
  }

  return response.json();
}

export async function getTask(taskId: string): Promise<Task> {
  const response = await fetch(`${BASE_URL}/tasks/${taskId}`);

  if (!response.ok) {
    throw new Error(`Failed to get task: ${response.statusText}`);
  }

  return response.json();
}

export async function getDownloadUrl(taskId: string): Promise<{
  download_url: string;
  expires_in: number;
}> {
  const response = await fetch(`${BASE_URL}/tasks/${taskId}/result`);

  if (!response.ok) {
    throw new Error(`Failed to get download URL: ${response.statusText}`);
  }

  return response.json();
}

// React 使用示例
import { useState } from "react";
import { createTask, getTask, getDownloadUrl } from "./api";

export function VideoUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<string>("idle");

  const handleUpload = async () => {
    if (!file) return;

    try {
      // 创建任务
      const task = await createTask(file, "zh", "en");
      setTaskId(task.id);
      setStatus(task.status);

      // 轮询状态
      const interval = setInterval(async () => {
        const updatedTask = await getTask(task.id);
        setStatus(updatedTask.status);
        setProgress(updatedTask.progress);

        if (updatedTask.status === "completed" || updatedTask.status === "failed") {
          clearInterval(interval);

          if (updatedTask.status === "completed") {
            // 获取下载链接
            const { download_url } = await getDownloadUrl(task.id);
            window.open(download_url, "_blank");
          }
        }
      }, 3000);
    } catch (error) {
      console.error("Upload failed:", error);
      setStatus("error");
    }
  };

  return (
    <div>
      <input
        type="file"
        accept="video/*"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button onClick={handleUpload} disabled={!file}>
        上传并配音
      </button>
      {taskId && (
        <div>
          <p>任务 ID: {taskId}</p>
          <p>状态: {status}</p>
          <p>进度: {progress}%</p>
        </div>
      )}
    </div>
  );
}
```

---

## 附录

### Swagger/OpenAPI 文档

在线交互式文档: http://localhost:8000/api/v1/docs

### ReDoc 文档

美化的 API 文档: http://localhost:8000/api/v1/redoc

### OpenAPI JSON

OpenAPI 规范文件: http://localhost:8000/api/v1/openapi.json

---

## 常见问题

### 1. 任务一直处于 pending 状态？

**原因**: Celery Worker 未启动或无法连接到 Redis。

**解决方案**:
```bash
# 检查 Redis 是否运行
redis-cli ping

# 启动 Celery Worker
celery -A app.workers.celery_app worker --loglevel=info
```

### 2. 任务失败，错误信息显示 "OSS 错误"？

**原因**: OSS 配置不正确或权限不足。

**解决方案**:
- 检查 `.env` 中的 OSS 配置
- 确保 Bucket 存在且有读写权限
- 检查 Access Key 是否有效

### 3. 视频上传失败？

**原因**: 文件过大或格式不支持。

**解决方案**:
- 检查文件大小（默认限制 500MB）
- 确认视频格式在支持列表中（mp4, avi, mov, mkv, flv）
- 调整 `MAX_UPLOAD_SIZE` 配置

### 4. 声音复刻效果不好？

**原因**: 音频样本质量或长度不足。

**解决方案**:
- 确保每个说话人有足够的清晰音频（建议 >3 秒）
- 背景噪音会影响复刻效果
- 可以尝试使用系统音色模式（cosyvoice-v1）

### 5. 如何查看详细日志？

**日志文件位置**:
- API 日志: `backend/logs/app.log`
- Worker 日志: `backend/worker.log`
- Celery 日志: 在 Worker 启动的终端中

**调整日志级别**:
```bash
# .env
LOG_LEVEL=DEBUG
```

---

## 更新日志

### v2.0.0 (2026-02-02)

- ✨ 完整重构为 FastAPI 架构
- ✨ 支持阿里云百炼平台（ASR, LLM, TTS）
- ✨ 支持多说话人声音复刻
- ✨ 使用 Celery 异步任务队列
- ✨ 集成阿里云 OSS 存储
- ✨ 完整的 RESTful API 设计
- 🐛 修复多个已知问题

---

## 许可证

MIT License

---

## 支持

- 📧 Email: support@example.com
- 💬 GitHub Issues: https://github.com/your-repo/issues
- 📖 文档: http://localhost:8000/api/v1/docs
