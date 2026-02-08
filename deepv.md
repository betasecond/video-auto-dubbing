# DeepV Project Context & Guidelines

> **Generated:** 2026-02-08 (Enhanced with comprehensive codebase analysis)
> **Last Updated:** 2026-02-08
> **Version:** 2.0.0

---

## 🎯 Project Overview

**DeepV (视频自动配音系统)** is a production-grade, AI-powered video localization platform that automatically translates and dubs videos into multiple languages. The system leverages Aliyun's DashScope platform for advanced AI services including:

- **ASR (Automatic Speech Recognition)** - Multi-speaker speech-to-text with emotion detection
- **LLM Translation** - Context-aware translation using Qwen models
- **Voice Cloning TTS** - Real-time voice replication using CosyVoice technology
- **Smart Audio Alignment** - Intelligent speed adjustment to match original timing

**Key Innovation**: Multi-speaker voice cloning with voice ID reuse mechanism - achieving 50x performance improvement by caching voice profiles per task.

---

## 🏗️ Technology Stack

### Backend (Python 3.11+)
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | FastAPI | 0.109+ | Async REST API server |
| **Database** | PostgreSQL | 14+ | Persistent data storage |
| **ORM** | SQLAlchemy | 2.0.25 | Database abstraction layer |
| **Migration** | Alembic | 1.13.1 | Schema version control |
| **Task Queue** | Celery | 5.3.6 | Async job processing |
| **Message Broker** | Redis | 6.2+ | Celery broker & caching |
| **Package Manager** | uv (Astral) | Latest | Fast Python dependency resolver |
| **Validation** | Pydantic | 2.6.0 | Data validation & serialization |
| **HTTP Client** | httpx | 0.26.0 | Async HTTP requests |
| **Media Processing** | FFmpeg | 4.4+ | Audio/video manipulation |

### Frontend (TypeScript)
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | Next.js | 14.1.0 | React full-stack framework (App Router) |
| **Language** | TypeScript | 5.3.3 | Type-safe JavaScript |
| **Styling** | Tailwind CSS | 3.4.1 | Utility-first CSS framework |
| **UI Components** | Radix UI | Latest | Accessible headless components |
| **UI Library** | shadcn/ui | Latest | Pre-built component collection |
| **Icons** | Lucide React | 0.312.0 | Icon library |
| **Form Handling** | React Hook Form | 7.49.3 | Form state management |
| **Validation** | Zod | 3.22.4 | Schema validation |
| **Data Fetching** | SWR | 2.4.0 | React Hooks for data fetching |
| **HTTP Client** | Axios | 1.6.5 | HTTP request library |

### External Services (Aliyun DashScope)
| Service | Model | Purpose |
|---------|-------|---------|
| **ASR** | SenseVoice-v1 | Speech recognition with speaker diarization |
| **LLM** | Qwen-Turbo | Context-aware translation |
| **TTS (System)** | CosyVoice-v1 | Preset voice synthesis (9 voices) |
| **TTS (Clone)** | Qwen3-TTS-VC-Realtime | Voice cloning & synthesis |
| **Storage** | Aliyun OSS | Object storage for media files |

---

## 📐 System Architecture

### High-Level Architecture (Layered)

```
┌─────────────────────────────────────────────────────────────────┐
│                      Presentation Layer                         │
│  Next.js 14 (React 18) + TypeScript + Tailwind CSS             │
│  - Task creation UI (upload form)                               │
│  - Task list & detail pages                                     │
│  - Real-time progress monitoring (SWR polling)                  │
│  - Download result interface                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↕ HTTP/REST API
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                          │
│  FastAPI (Python 3.11+)                                         │
│  - RESTful API endpoints (/api/v1/tasks, /monitoring)          │
│  - Request validation (Pydantic schemas)                        │
│  - File upload handling (multipart/form-data)                   │
│  - Task orchestration (Celery task chains)                      │
│  - Authentication & CORS middleware                             │
└─────────────────────────────────────────────────────────────────┘
                              ↕ Database & Queue
┌─────────────────────────────────────────────────────────────────┐
│                      Business Logic Layer                       │
│  Services (TaskService, StorageService, VoiceService)          │
│  - Task lifecycle management                                    │
│  - OSS file operations (upload/download/presigned URLs)        │
│  - Voice cloning with cache                                     │
│  - Segment CRUD operations                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↕ Async Tasks
┌─────────────────────────────────────────────────────────────────┐
│                      Task Processing Layer                       │
│  Celery Workers (Multi-step Pipeline)                          │
│  1. extract_audio    → FFmpeg audio extraction                  │
│  2. transcribe_audio → DashScope ASR API                        │
│  3. translate_segments → Qwen LLM batch translation             │
│  4. synthesize_audio → TTS with voice cloning                   │
│  5. mux_video        → FFmpeg audio replacement + subtitles     │
└─────────────────────────────────────────────────────────────────┘
                              ↕ External APIs & Storage
┌───────────────┬────────────────┬─────────────┬──────────────────┐
│  PostgreSQL   │     Redis      │ Aliyun OSS  │ DashScope APIs   │
│  (Tasks DB)   │ (Celery Queue) │(File Store) │ (AI Services)    │
└───────────────┴────────────────┴─────────────┴──────────────────┘
```

### Project Directory Structure

```
video-auto-dubbing/
├── backend/                   # Python FastAPI Backend
│   ├── app/
│   │   ├── main.py            # FastAPI app entry, CORS, lifespan
│   │   ├── config.py          # Settings (Pydantic BaseSettings)
│   │   ├── database.py        # SQLAlchemy engines, sessions
│   │   ├── api/               # REST API endpoints
│   │   │   ├── tasks.py       # Task CRUD endpoints
│   │   │   ├── monitoring.py  # Health check, stats, Celery inspect
│   │   │   └── deps.py        # Dependency injection (get_db, services)
│   │   ├── models/            # SQLAlchemy ORM models
│   │   │   ├── task.py        # Task model (TaskStatus, SubtitleMode)
│   │   │   └── segment.py     # Segment model (ASR results, translations)
│   │   ├── schemas/           # Pydantic validation schemas
│   │   │   ├── task.py        # TaskCreate, TaskResponse, TaskDetail
│   │   │   └── segment.py     # SegmentCreate, SegmentResponse
│   │   ├── services/          # Business logic layer
│   │   │   ├── task_service.py      # Task CRUD operations
│   │   │   ├── storage_service.py   # OSS wrapper (upload/download)
│   │   │   └── voice_service.py     # Voice cloning with cache
│   │   ├── workers/           # Celery tasks
│   │   │   ├── celery_app.py  # Celery configuration
│   │   │   └── tasks.py       # 5-step processing pipeline
│   │   ├── integrations/      # External API clients
│   │   │   ├── dashscope/
│   │   │   │   ├── asr_client.py   # ASR async polling
│   │   │   │   ├── llm_client.py   # OpenAI-compatible translation
│   │   │   │   └── tts_client.py   # TTS + voice cloning (REST/WebSocket)
│   │   │   └── oss/
│   │   │       └── client.py       # Aliyun OSS SDK wrapper
│   │   └── utils/
│   │       └── ffmpeg.py      # FFmpeg operations (extract, merge, subtitle)
│   ├── migrations/            # Alembic migration files
│   ├── scripts/               # Utility scripts
│   │   ├── check_services.py  # Service health diagnostics
│   │   └── show_asr.py        # ASR result viewer
│   ├── tests/                 # Test suite
│   └── pyproject.toml         # Project dependencies (uv)
│
├── frontend/                  # Next.js 14 Frontend
│   ├── app/                   # Next.js App Router
│   │   ├── layout.tsx         # Root layout with providers
│   │   ├── page.tsx           # Homepage (hero, features)
│   │   ├── tasks/
│   │   │   ├── page.tsx       # Task list page
│   │   │   ├── [id]/page.tsx  # Task detail page
│   │   │   └── new/page.tsx   # Create task page
│   │   └── providers.tsx      # Client-side providers
│   ├── components/
│   │   ├── upload-form.tsx    # File upload form (react-dropzone)
│   │   └── ui/                # shadcn/ui components
│   ├── lib/
│   │   ├── api.ts             # Axios client & API functions
│   │   ├── types.ts           # TypeScript interfaces
│   │   ├── utils.ts           # Helper functions (cn, formatters)
│   │   └── hooks/
│   │       └── use-tasks.ts   # SWR hooks for data fetching
│   └── package.json           # Dependencies & scripts
│
├── docs/                      # Documentation
│   ├── guide/                 # User guides
│   ├── architecture/          # Architecture docs
│   └── api/                   # API documentation
│
├── docker-compose.v2.yml      # Docker Compose configuration
└── .env                       # Environment variables (not in git)
```

---

## 🔄 Video Dubbing Workflow (5-Step Pipeline)

### Step 1: Extract Audio (`extract_audio_task`)

**Purpose**: Separate audio from video

**Actions:**
1. Download video from OSS to temp directory
2. Run FFmpeg: `ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav`
3. Extract video metadata (duration, resolution)
4. Upload extracted audio to OSS
5. Update task: `extracted_audio_path`, `video_duration_ms`

**Technology:** FFmpeg (PCM 16kHz mono WAV)

---

### Step 2: Transcribe Audio (`transcribe_audio_task`)

**Purpose**: Speech-to-text with speaker diarization

**Actions:**
1. Generate OSS presigned URL (1-hour expiry)
2. Submit async ASR task to DashScope:
   ```python
   Transcription.async_call(
       model="sensevoice-v1",
       file_urls=[audio_url],
       enable_speaker_diarization=True,  # Multi-speaker detection
       disfluency_removal_enabled=True   # Remove filler words
   )
   ```
3. Poll for completion (2s interval, 300s timeout)
4. Parse ASR results:
   - Extract segments with timestamps
   - Identify speakers (`speaker_id`)
   - Filter out empty/punctuation-only segments
5. Create Segment records in database

**Output:**
```json
{
  "segments": [
    {
      "speaker_id": "speaker_0",
      "start_time_ms": 0,
      "end_time_ms": 3000,
      "text": "Hello everyone",
      "emotion": "neutral",
      "confidence": 0.95
    }
  ]
}
```

**Technology:** DashScope SenseVoice (Aliyun ASR)

---

### Step 3: Translate Segments (`translate_segments_task`)

**Purpose**: Context-aware translation

**Actions:**
1. Fetch all segments for task
2. **Full-text translation** (preserving context):
   - Concatenate all segments with `[index]` markers
   - Send to Qwen LLM with custom prompt
   - Parse translated output back to individual segments
3. **Fallback**: If full-text fails, translate segment-by-segment
4. Update `translated_text` for each segment

**Example:**
```
Input:
[0] 大家好,我是主持人。
[1] 今天我们讨论人工智能。

LLM Output:
[0] Hello everyone, I'm the host.
[1] Today we're discussing artificial intelligence.
```

**Technology:** DashScope Qwen-Turbo (OpenAI-compatible API)

---

### Step 4: Synthesize Audio (`synthesize_audio_task`)

**Purpose**: Text-to-speech with voice cloning

**Actions:**
1. **Group segments by speaker_id**:
   ```python
   {
     "speaker_0": [segment_1, segment_3],
     "speaker_1": [segment_2]
   }
   ```

2. **Voice enrollment** (per speaker, cached):
   - Extract all audio clips for speaker
   - Merge into 10-20s sample
   - Call `TTSClient.enroll_voice()` → returns `voice_id` (vc_xxx)
   - Cache: `{speaker_id → voice_id}` (reuse across segments)

3. **Synthesize each segment**:
   - Use corresponding `voice_id` for TTS
   - Generate MP3 audio
   - Upload to OSS: `task_{id}/segments/segment_{index}.mp3`
   - Update segment: `voice_id`, `audio_path`

**Performance Optimization**: Voice ID reuse reduces API calls by 50x for multi-speaker videos.

**Technology:**
- **Voice Cloning**: Qwen3-TTS-VC-Realtime (WebSocket API)
- **System Voices**: CosyVoice-v1 (9 preset voices, fallback)

---

### Step 5: Mux Video (`mux_video_task`)

**Purpose**: Merge audio segments and replace video track

**Actions:**
1. Download all segment audio files
2. **Smart audio merging**:
   - Calculate time slots (avoid overlaps)
   - Apply speed adjustment if TTS audio exceeds slot (max 4x)
   - Use FFmpeg `adelay` filter to position audio on timeline
3. **Subtitle generation** (if enabled):
   - Create ASS file with dual-language subtitles
   - Upload to OSS
4. **Video composition**:
   - **External subtitles**: `ffmpeg -i video -i audio -c:v copy -c:a aac -map 0:v -map 1:a output.mp4` (fast, video copy)
   - **Burned subtitles**: `ffmpeg -i video -i audio -vf "ass='subtitle.ass'" -c:v libx264 -c:a aac output.mp4` (slow, re-encode)
5. Upload final video to OSS
6. Update task status to `COMPLETED`

**Technology:** FFmpeg (audio mixing, subtitle overlay, video encoding)

---

## 🗄️ Database Schema

### Tasks Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Primary key |
| `title` | String(255) | Task title |
| `source_language` | String(10) | Source language code (zh, en, etc.) |
| `target_language` | String(10) | Target language code |
| `status` | Enum | TaskStatus (pending, extracting, transcribing, translating, synthesizing, muxing, completed, failed) |
| `current_step` | String(20) | Current processing step |
| `progress` | Integer (0-100) | Progress percentage |
| `error_message` | Text | Error details if failed |
| `subtitle_mode` | Enum | SubtitleMode (NONE, EXTERNAL, BURN) |
| `input_video_path` | String(500) | OSS path to input video |
| `extracted_audio_path` | String(500) | OSS path to extracted audio |
| `output_video_path` | String(500) | OSS path to final video |
| `subtitle_file_path` | String(500) | OSS path to subtitle file (.ass) |
| `video_duration_ms` | Integer | Video duration in milliseconds |
| `segment_count` | Integer | Number of segments |
| `celery_task_id` | String(100) | Celery task ID for tracking |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |
| `completed_at` | DateTime | Completion timestamp |

**Indexes:**
- `ix_tasks_id` (UUID)
- `ix_tasks_status` (for filtering)
- `ix_tasks_created_at` (for sorting)

### Segments Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Primary key |
| `task_id` | UUID (FK → tasks.id) | Parent task ID (CASCADE DELETE) |
| `segment_index` | Integer | Sequential index |
| `start_time_ms` | Integer | Start time in milliseconds |
| `end_time_ms` | Integer | End time in milliseconds |
| `original_text` | Text | ASR transcription |
| `translated_text` | Text | LLM translation |
| `speaker_id` | String(50) | Speaker identifier (from ASR) |
| `emotion` | String(20) | Emotion tag (from ASR) |
| `confidence` | Float | Confidence score |
| `voice_id` | String(100) | Voice cloning ID (vc_xxx) - **CACHED FOR REUSE** |
| `audio_path` | String(500) | OSS path to synthesized audio |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

**Indexes:**
- `ix_segments_id` (UUID)
- `ix_segments_task_id` (foreign key)
- `idx_task_segment` (task_id, segment_index) - UNIQUE

**Relationships:**
- 1 Task → N Segments (one-to-many)
- Cascade delete: deleting a task removes all segments

---

## 🔌 API Endpoints

### Task Management

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| POST | `/api/v1/tasks` | Create dubbing task | `multipart/form-data` (video, source_language, target_language, title?, subtitle_mode?) | `TaskResponse` |
| GET | `/api/v1/tasks` | List tasks | Query: page, page_size, status? | `TaskListResponse` |
| GET | `/api/v1/tasks/{id}` | Get task details | Path: task_id | `TaskDetail` (with segments) |
| DELETE | `/api/v1/tasks/{id}` | Delete task | Path: task_id | 204 No Content |
| GET | `/api/v1/tasks/{id}/result` | Get download URLs | Path: task_id | `{download_url, subtitle_url?, expires_in}` |
| GET | `/api/v1/tasks/{id}/subtitle` | Get subtitle URL | Path: task_id | `{subtitle_url, expires_in}` |

### Monitoring

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/api/v1/monitoring/health` | Health check | `{status, services: {database, redis, ffmpeg}, version}` |
| GET | `/api/v1/monitoring/stats` | System stats | `{tasks: {total, by_status}, workers: {active, registered}}` |
| GET | `/api/v1/monitoring/celery/inspect` | Celery worker status | Worker inspection data |

---

## ⚙️ Configuration & Environment Variables

### Required Environment Variables

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dubbing
DB_USER=dubbing
DB_PASSWORD=<secure-password>

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=<optional>
REDIS_DB=0

# Aliyun OSS
OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
OSS_BUCKET=your-bucket-name
OSS_ACCESS_KEY_ID=LTAI***
OSS_ACCESS_KEY_SECRET=***
OSS_PUBLIC_DOMAIN=cdn.example.com  # Optional CDN
OSS_PREFIX=videos/

# Aliyun DashScope
DASHSCOPE_API_KEY=sk-***

# ASR Settings
ASR_MODEL=sensevoice-v1
ASR_LANGUAGE_HINTS=["zh", "en"]

# LLM Settings
DASHSCOPE_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_LLM_MODEL=qwen-turbo
LLM_MAX_TOKENS=2000

# TTS Settings
TTS_MODEL=qwen3-tts-vc-realtime-2026-01-15  # or cosyvoice-v1
TTS_VOICE=longxiaochun  # System voice (cosyvoice-v1 only)
TTS_FORMAT=mp3

# Application
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost

# Worker
WORKER_CONCURRENCY=4
TASK_TIMEOUT=3600
```

### Frontend Environment

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 🚀 Development Commands

### Environment Management

**Python Package Management:**
```bash
# We use `uv` for Python package and environment management
cd backend

# Create virtual environment
uv venv

# Install dependencies
uv sync

# Install in editable mode with dev dependencies
uv pip install -e ".[dev]"

# Run scripts in the environment
uv run python scripts/check_services.py
```

### Backend Development

```bash
cd backend

# Run dev server (auto-reload)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

# Database migrations
alembic upgrade head                          # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
alembic downgrade -1                          # Rollback one version

# Run tests
pytest
pytest --cov=app tests/                       # With coverage
pytest -v -s tests/test_integrations.py       # Specific test file

# Format code
black app/
ruff app/ --fix

# Type checking
mypy app/

# Service diagnostics
python scripts/check_services.py
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run dev server (hot reload)
npm run dev

# Build for production
npm run build

# Start production server
npm run start

# Lint & type check
npm run lint
npm run type-check

# Component development
npm run storybook  # If configured
```

### Docker Compose

```bash
# Start all services
docker-compose -f docker-compose.v2.yml up -d

# View logs
docker-compose logs -f
docker-compose logs -f api       # Specific service
docker-compose logs -f worker

# Scale workers
docker-compose up -d --scale worker=8

# Restart services
docker-compose restart api worker

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

---

## 🧠 Key Patterns & Conventions

### 1. Async Database Sessions (Dependency Injection)

```python
# Using FastAPI dependency injection
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Usage in API endpoints
@router.get("/tasks/{task_id}")
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    task = await TaskService.get_task(db, task_id)
    return task
```

### 2. Celery Task Chains (Sequential Processing)

```python
# Chain tasks in sequence
pipeline = chain(
    extract_audio_task.s(task_id),
    transcribe_audio_task.s(task_id),
    translate_segments_task.s(task_id),
    synthesize_audio_task.s(task_id),
    mux_video_task.s(task_id),
).apply_async()

# Store Celery task ID for tracking
task.celery_task_id = pipeline.id
```

### 3. Voice ID Caching (Multi-speaker Optimization)

```python
# Cache structure: {speaker_id → voice_id}
voice_cache = {}

for speaker_id in speakers:
    if speaker_id in voice_cache:
        voice_id = voice_cache[speaker_id]  # Reuse existing voice ID
    else:
        voice_id = enroll_voice(speaker_id)  # Clone voice once
        voice_cache[speaker_id] = voice_id

    # Use cached voice_id for all segments of this speaker
    synthesize_segment(segment, voice_id)

# Performance: 50x faster for multi-speaker videos
```

### 4. FFmpeg Smart Speed Adjustment

```python
# Calculate speed ratio
actual_duration_ms = get_audio_duration(audio_path)
target_duration_ms = segment.end_time_ms - segment.start_time_ms
speed_ratio = actual_duration_ms / target_duration_ms

# Apply atempo filter (range 0.5-2.0, chain if >2x)
if speed_ratio > 2.0:
    # Chain multiple atempo filters
    filters = ["atempo=2.0", f"atempo={speed_ratio/2.0}"]
else:
    filters = [f"atempo={speed_ratio}"]

filter_str = ",".join(filters)
# ffmpeg -i audio.wav -filter:a "atempo=2.0,atempo=1.5" output.wav
```

### 5. Pydantic Settings Configuration

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env"],
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

settings = Settings()
```

### 6. SWR Data Fetching (Frontend)

```typescript
// Auto-revalidating hook with polling
export function useTask(taskId: string | null) {
  const { data, error, mutate } = useSWR(
    taskId ? `/tasks/${taskId}` : null,
    () => taskId ? api.getTask(taskId) : null,
    {
      refreshInterval: 2000,  // Poll every 2s
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
    }
  );

  return {
    task: data,
    isLoading: !error && !data,
    isError: error,
    mutate
  };
}
```

---

## ⚠️ Common Gotchas & Solutions

### 1. TTS Model Confusion

**Issue**: Using system voice names with voice cloning model

```python
# ❌ WRONG
client = TTSClient(model="qwen3-tts-vc-realtime-2026-01-15")
audio = client.synthesize("Hello", voice="longxiaochun")
# → ValueError: requires voice_id (vc_xxx format)

# ✅ CORRECT
client = TTSClient(model="qwen3-tts-vc-realtime-2026-01-15")
voice_id = client.enroll_voice("sample.wav")  # Returns vc_abc123
audio = client.synthesize("Hello", voice=voice_id)
```

### 2. FFmpeg Path Escaping

**Issue**: Special characters in file paths break filter syntax

```python
# Subtitle filter requires careful escaping
subtitle_path = "C:\\Users\\video\\subtitle's.ass"

# Escape for FFmpeg filter
escaped = subtitle_path.replace("\\", "/").replace(":", "\\:").replace("'", "'\\''")

# Use in filter: ass='escaped/path'
cmd = ["ffmpeg", "-i", "video.mp4", "-vf", f"ass='{escaped}'", "output.mp4"]
```

### 3. Async Event Loop in Celery

**Issue**: Celery workers need event loop management

```python
def _run_async(coro):
    """Reuse event loop across Celery tasks"""
    loop = getattr(_run_async, "_loop", None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _run_async._loop = loop
    return loop.run_until_complete(coro)

# Usage in Celery task
@celery_app.task
def process_task(task_id: str):
    return _run_async(async_function(task_id))
```

### 4. Subtitle Mode Enum Mismatch

**Frontend sends lowercase**: `subtitle_mode=external`
**Backend expects uppercase**: `SubtitleMode.EXTERNAL`

**Solution**: API endpoint converts automatically:
```python
subtitle_mode_enum = SubtitleMode(subtitle_mode.upper())
```

### 5. Audio Timeline Overlapping

**Issue**: Overlapping segments cause audio artifacts

**Solution**: Smart speed adjustment

```python
for i, segment in enumerate(segments):
    # Calculate next segment's start
    next_start = segments[i+1].start_time_ms if i+1 < len(segments) else video_duration_ms

    # Maximum time slot available
    max_slot_ms = next_start - segment.start_time_ms

    # If TTS audio exceeds slot, speed it up
    if tts_audio_duration > max_slot_ms:
        speed_ratio = tts_audio_duration / max_slot_ms
        adjust_speed(tts_audio, speed=speed_ratio)
```

---

## 🧪 Testing Strategy

### Backend Tests (`backend/tests/`)

**Structure:**
```
tests/
├── __init__.py
├── test_api/                # API endpoint tests
│   ├── test_tasks.py        # Task CRUD tests
│   └── test_monitoring.py   # Health check tests
├── test_workers/            # Celery task tests
│   └── test_pipeline.py     # Pipeline integration tests
├── test_integrations.py     # External API mocks
└── test_oss.py              # OSS client tests
```

**Testing Tools:**
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `httpx` - Async HTTP test client

**Example Test:**
```python
@pytest.mark.asyncio
async def test_create_task(client, db_session):
    with open("tests/fixtures/sample.mp4", "rb") as f:
        video_bytes = f.read()

    response = await client.post(
        "/api/v1/tasks",
        files={"video": ("test.mp4", video_bytes, "video/mp4")},
        data={
            "source_language": "zh",
            "target_language": "en",
            "title": "Test Video"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["source_language"] == "zh"
    assert data["target_language"] == "en"
```

**Coverage Goals:**
- API endpoints: 80%+
- Services: 75%+
- Workers: 60%+
- Overall: 70%+

---

## 🏭 Deployment Architecture

### Docker Compose Services

```yaml
services:
  # PostgreSQL 15
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: dubbing
      POSTGRES_USER: dubbing
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dubbing"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis 7
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # FastAPI Backend
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://dubbing:${DB_PASSWORD}@db:5432/dubbing
      - REDIS_HOST=redis
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - OSS_ACCESS_KEY_ID=${OSS_ACCESS_KEY_ID}
      - OSS_ACCESS_KEY_SECRET=${OSS_ACCESS_KEY_SECRET}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # Celery Worker
  worker:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql+asyncpg://dubbing:${DB_PASSWORD}@db:5432/dubbing
      - REDIS_HOST=redis
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - OSS_ACCESS_KEY_ID=${OSS_ACCESS_KEY_ID}
      - OSS_ACCESS_KEY_SECRET=${OSS_ACCESS_KEY_SECRET}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

  # Next.js Frontend
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000/api/v1
    depends_on:
      - api
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev

volumes:
  postgres_data:
  redis_data:
```

---

## 📚 Documentation & Resources

### Project Documentation
- **[README.md](README.md)**: Project overview (Chinese)
- **[README_EN.md](README_EN.md)**: Project overview (English)
- **[docs/guide/start-here.md](docs/guide/start-here.md)**: Getting started guide
- **[docs/guide/quickstart.md](docs/guide/quickstart.md)**: Detailed deployment guide
- **[docs/architecture/system-overview.md](docs/architecture/system-overview.md)**: Architecture overview
- **[docs/architecture/optimization.md](docs/architecture/optimization.md)**: Voice cloning & alignment optimization
- **[docs/guide/frontend.md](docs/guide/frontend.md)**: Frontend development guide
- **[docs/api/backend-api.md](docs/api/backend-api.md)**: API documentation

### External Resources
- **Aliyun DashScope**: https://help.aliyun.com/zh/dashscope/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Next.js 14**: https://nextjs.org/docs
- **Celery**: https://docs.celeryq.dev/
- **SQLAlchemy 2.0**: https://docs.sqlalchemy.org/
- **shadcn/ui**: https://ui.shadcn.com/

---

## 🎓 Implementation Guidance

### For Adding New Features

**New API Endpoint:**
1. Add route in `/backend/app/api/tasks.py`
2. Create Pydantic schema in `/backend/app/schemas/`
3. Add service method in `/backend/app/services/`
4. Update frontend API client in `/frontend/lib/api.ts`
5. Add TypeScript type in `/frontend/lib/types.ts`

**New Processing Step:**
1. Add Celery task in `/backend/app/workers/tasks.py`
2. Insert into pipeline chain in task creation
3. Update task status enum if needed
4. Add progress tracking in frontend

**New External API Integration:**
1. Create client in `/backend/app/integrations/`
2. Wrap with service layer
3. Add configuration in `config.py`
4. Add unit tests

**New UI Component:**
1. Add component to `/frontend/components/`
2. Use SWR hook for data fetching
3. Update TypeScript types
4. Add to appropriate page

### For Debugging

**Backend:**
1. Check logs: `logs/app.log` (API), `logs/worker.log` (Celery)
2. Health check: `GET /api/v1/monitoring/health`
3. Celery inspect: `GET /api/v1/monitoring/celery/inspect`
4. Database: Query `tasks` and `segments` tables directly
5. Run diagnostics: `python scripts/check_services.py`

**Frontend:**
1. Browser DevTools console
2. Network tab for API requests
3. React DevTools for component state

---

## 🔐 Security Considerations

### Current Limitations
1. **No Authentication**: API is currently open (add JWT/OAuth2 for production)
2. **No Rate Limiting**: No API throttling to prevent abuse
3. **File Upload Validation**: Add virus scanning for uploaded videos
4. **CORS**: Configured for development (restrict origins in production)

### Recommended Improvements
1. Implement JWT authentication
2. Add rate limiting (e.g., Redis-based)
3. Enable API key authentication for external integrations
4. Add file size limits and type validation
5. Implement request signing for OSS operations
6. Enable HTTPS/TLS in production

---

## 📊 Performance Metrics

### Key Optimizations
1. **Voice ID Reuse**: 50x faster for multi-speaker videos
2. **Async Database Operations**: Non-blocking I/O
3. **Celery Worker Scaling**: Horizontal scalability
4. **OSS CDN**: Faster global file access
5. **FFmpeg Hardware Acceleration**: GPU encoding (if available)

### Typical Processing Times (per minute of video)
- Extract Audio: 2-5s
- ASR Transcription: 10-30s
- LLM Translation: 5-15s
- Voice Cloning (first speaker): 30-60s
- Voice Cloning (cached speakers): 1-2s per segment
- Audio Synthesis: 3-10s per segment
- Video Muxing: 10-30s

**Total**: ~2-5 minutes per minute of video (varies by complexity)

---

## 🚨 Critical Rules for AI Assistants

### ⚠️ Documentation Rules
> **我没有让你写文档的时候不要写文档，不要写文档，不要写文档**
>
> **Translation**: "When I haven't asked you to write documentation, DO NOT write documentation. DO NOT write documentation. DO NOT write documentation."

**This means:**
- Only create/update documentation when explicitly requested
- Focus on code implementation, not documentation generation
- If unsure whether to document, ask the user first
- Respect this rule strictly across all interactions

### Development Priorities
1. **Code First**: Write working code before documentation
2. **Test Locally**: Verify functionality before committing
3. **Minimal Changes**: Only modify what's necessary
4. **Ask, Don't Assume**: Clarify requirements before major refactoring

---

## 🎯 Quick Reference

### Most Common Commands

```bash
# Start development environment
docker-compose up -d

# Run backend dev server
cd backend && uv run uvicorn app.main:app --reload

# Run frontend dev server
cd frontend && npm run dev

# Check system health
curl http://localhost:8000/api/v1/monitoring/health

# View logs
docker-compose logs -f worker
```

### File Modification Guide

**Add new language support:**
- `backend/app/api/tasks.py` - Update `valid_languages` set
- `frontend/lib/api.ts` - Update `SUPPORTED_LANGUAGES` array

**Add authentication:**
- `backend/app/api/deps.py` - Add `get_current_user()` dependency
- `backend/app/main.py` - Add JWT middleware
- `backend/app/models/` - Add `User` model
- `frontend/lib/api.ts` - Add Authorization header

**Add WebSocket progress updates:**
- `backend/app/main.py` - Add WebSocket route
- `backend/app/workers/tasks.py` - Emit progress events
- `frontend/lib/hooks/use-task-ws.ts` - Create WebSocket hook
- `frontend/app/tasks/[id]/page.tsx` - Replace SWR polling

---

## 📈 Refactoring Status (as of Feb 2026)

**Completed:**
- ✅ Transitioned from local GPU inference to Aliyun DashScope APIs
- ✅ Backend core implemented (FastAPI + SQLAlchemy + Celery)
- ✅ Database schema designed (tasks + segments)
- ✅ 5-step processing pipeline operational
- ✅ Voice cloning with cache optimization
- ✅ Smart audio timeline management
- ✅ Subtitle generation (external/burned)
- ✅ Frontend basic UI (Next.js + shadcn/ui)
- ✅ Docker Compose deployment setup

**In Progress:**
- 🚧 Frontend integration (task list, detail pages)
- 🚧 Real-time progress updates (WebSocket)
- 🚧 Error handling improvements
- 🚧 Test coverage expansion

**Planned:**
- 📋 Authentication & authorization
- 📋 Rate limiting & security hardening
- 📋 Monitoring & observability (Prometheus/Grafana)
- 📋 CDN integration for OSS
- 📋 Batch processing support
- 📋 Multi-language UI (i18n)

---

**Generated by DeepV Code AI Assistant**
**Last Updated:** 2026-02-08
**Project Version:** 2.0.0

## DeepV Code Added Memories
- DEEPV.md generated by /init command on 2026-02-08 (enhanced comprehensive analysis version with full codebase exploration, architecture breakdown, workflow documentation, API reference, and development guidelines)
