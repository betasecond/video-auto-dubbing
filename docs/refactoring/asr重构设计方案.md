# ASR 重构设计方案：火山引擎大模型 ASR 集成

## 一、重构目标

将现有的本地 Moonshine ASR 服务替换为**火山引擎大模型录音文件识别 API**，实现：

1. **异步处理**：提交任务 → 轮询结果（适合长音频）
2. **说话人分离**：支持 10 人以内的说话人识别
3. **丰富元数据**：情绪检测、性别检测、语速、音量
4. **多语言支持**：中英日韩等多语言识别

---

## 二、架构变更

### 2.1 变更前后对比

```
【变更前】
Worker → HTTP → asr_service (本地 Python 服务) → Moonshine ONNX
                      ↓
               同步返回结果

【变更后】
Worker → HTTP → 火山引擎 API (云服务)
                      ↓
              1. 提交任务 (submit)
              2. 轮询结果 (query)
              3. 解析并存储
```

### 2.2 服务变更

| 组件 | 变更 |
|------|------|
| `asr_service/` | **删除** - 不再需要本地 ASR 服务 |
| `worker/internal/asr/client.go` | **重写** - 实现火山引擎客户端 |
| `worker/internal/config/config.go` | **修改** - 新增火山引擎配置 |
| `shared/config/config.go` | **修改** - 新增火山引擎配置结构 |
| `docker-compose.yml` | **修改** - 移除 asr_service |
| `segments` 表 | **修改** - 新增 speaker_id, emotion, gender 字段 |

---

## 三、火山引擎 API 集成设计

### 3.1 API 流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        Worker ASR 处理流程                       │
├─────────────────────────────────────────────────────────────────┤
│  1. 获取音频 Presigned URL (MinIO)                              │
│                        ↓                                        │
│  2. 提交任务 POST /api/v3/auc/bigmodel/submit                   │
│     - 携带音频 URL、配置参数                                      │
│     - 获取 Request-Id 作为任务标识                               │
│                        ↓                                        │
│  3. 轮询结果 POST /api/v3/auc/bigmodel/query                    │
│     - 使用 Request-Id 查询                                      │
│     - 状态码 20000001/20000002 = 处理中，继续轮询                 │
│     - 状态码 20000000 = 成功，解析结果                           │
│                        ↓                                        │
│  4. 解析结果并存储到 segments 表                                 │
│  5. 发布 translate 任务到消息队列                                │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 配置参数

```go
// VolcengineASRConfig 火山引擎 ASR 配置
type VolcengineASRConfig struct {
    AppKey       string  // X-Api-App-Key (火山控制台 APP ID)
    AccessKey    string  // X-Api-Access-Key (Access Token)
    ResourceID   string  // X-Api-Resource-Id (volc.bigasr.auc 或 volc.seedasr.auc)

    // 功能开关
    EnableSpeakerInfo     bool  // 说话人分离 (10人以内)
    EnableEmotionDetect   bool  // 情绪检测
    EnableGenderDetect    bool  // 性别检测
    EnablePunc            bool  // 标点符号
    EnableITN             bool  // 文本规范化 (数字转换等)

    // 轮询配置
    PollInterval    time.Duration  // 轮询间隔 (默认 2s)
    PollTimeout     time.Duration  // 轮询超时 (默认 15min)
}
```

### 3.3 请求参数设计

```json
{
    "user": {
        "uid": "<task_id>"
    },
    "audio": {
        "format": "wav",
        "url": "<presigned_minio_url>",
        "rate": 16000,
        "channel": 1
    },
    "request": {
        "model_name": "bigmodel",
        "model_version": "400",
        "enable_itn": true,
        "enable_punc": true,
        "enable_speaker_info": true,
        "enable_emotion_detection": true,
        "enable_gender_detection": true,
        "show_utterances": true
    }
}
```

### 3.4 响应解析

火山引擎返回格式：
```json
{
    "audio_info": {"duration": 10000},
    "result": {
        "text": "完整识别文本",
        "utterances": [
            {
                "text": "句子文本",
                "start_time": 0,
                "end_time": 1500,
                "additions": {
                    "speaker_id": "0",
                    "emotion": "neutral",
                    "gender": "male",
                    "speech_rate": 4.5
                },
                "words": [...]
            }
        ]
    }
}
```

映射到现有 `ASRSegment`：
```go
type ASRSegment struct {
    Idx       int    `json:"idx"`
    StartMs   int    `json:"start_ms"`
    EndMs     int    `json:"end_ms"`
    Text      string `json:"text"`
    // 新增字段
    SpeakerID string `json:"speaker_id,omitempty"`
    Emotion   string `json:"emotion,omitempty"`
    Gender    string `json:"gender,omitempty"`
}
```

---

## 四、代码实现计划

### 4.1 新增/修改文件清单

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `worker/internal/asr/volcengine_client.go` | 新增 | 火山引擎 ASR 客户端实现 |
| `worker/internal/asr/client.go` | 修改 | 改为接口定义，支持多实现 |
| `worker/internal/models/message.go` | 修改 | ASRSegment 增加 speaker_id 等字段 |
| `shared/config/config.go` | 修改 | 新增 VolcengineASRConfig |
| `worker/internal/config/config.go` | 修改 | 加载火山引擎配置 |
| `worker/internal/worker/steps/asr.go` | 修改 | 适配新的 ASR 响应格式，保存新字段 |
| `api/internal/database/migrations.go` | 修改 | segments 表增加字段 |
| `docker-compose.yml` | 修改 | 移除 asr_service，新增环境变量 |

### 4.2 接口抽象设计

```go
// worker/internal/asr/client.go

// ASRClient defines the interface for ASR services.
type ASRClient interface {
    Recognize(ctx context.Context, audioURL string, language string) (*models.ASRResult, error)
}

// 保留原有 Client 作为 MoonshineClient (可选，便于回退)
// 新增 VolcengineClient 作为新实现
```

### 4.3 火山引擎客户端实现

```go
// worker/internal/asr/volcengine_client.go

type VolcengineClient struct {
    cfg    VolcengineASRConfig
    client *http.Client
    logger *zap.Logger
}

func NewVolcengineClient(cfg VolcengineASRConfig, logger *zap.Logger) *VolcengineClient

// Recognize 实现异步提交+轮询
func (c *VolcengineClient) Recognize(ctx context.Context, audioURL string, language string) (*models.ASRResult, error) {
    // 1. Submit task
    requestID, err := c.submitTask(ctx, audioURL, language)

    // 2. Poll for result
    result, err := c.pollResult(ctx, requestID)

    // 3. Parse and return
    return c.parseResult(result)
}
```

---

## 五、数据库变更

### 5.1 segments 表新增字段

```sql
ALTER TABLE segments
ADD COLUMN IF NOT EXISTS speaker_id VARCHAR(32),
ADD COLUMN IF NOT EXISTS emotion VARCHAR(32),
ADD COLUMN IF NOT EXISTS gender VARCHAR(16);

COMMENT ON COLUMN segments.speaker_id IS '说话人标识 (火山引擎返回)';
COMMENT ON COLUMN segments.emotion IS '情绪标签: angry, happy, neutral, sad, surprise';
COMMENT ON COLUMN segments.gender IS '性别标签: male, female';
```

### 5.2 asr.go 步骤修改

```go
// 保存时增加新字段
query := `
    INSERT INTO segments (task_id, idx, start_ms, end_ms, duration_ms, src_text,
                          speaker_id, emotion, gender, created_at, updated_at)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    ON CONFLICT (task_id, idx) DO UPDATE
    SET start_ms = EXCLUDED.start_ms, end_ms = EXCLUDED.end_ms,
        duration_ms = EXCLUDED.duration_ms, src_text = EXCLUDED.src_text,
        speaker_id = EXCLUDED.speaker_id, emotion = EXCLUDED.emotion,
        gender = EXCLUDED.gender, updated_at = EXCLUDED.updated_at
`
```

---

## 六、配置管理

### 6.1 环境变量

```bash
# 火山引擎 ASR 配置
VOLCENGINE_ASR_APP_KEY=your_app_key
VOLCENGINE_ASR_ACCESS_KEY=your_access_key
VOLCENGINE_ASR_RESOURCE_ID=volc.bigasr.auc  # 或 volc.seedasr.auc (2.0模型)

# 功能开关 (可选，默认值见下)
VOLCENGINE_ASR_ENABLE_SPEAKER_INFO=true
VOLCENGINE_ASR_ENABLE_EMOTION=true
VOLCENGINE_ASR_ENABLE_GENDER=true
VOLCENGINE_ASR_ENABLE_PUNC=true
VOLCENGINE_ASR_ENABLE_ITN=true

# 轮询配置
VOLCENGINE_ASR_POLL_INTERVAL_SECONDS=2
VOLCENGINE_ASR_POLL_TIMEOUT_SECONDS=900
```

### 6.2 docker-compose.yml 变更

```yaml
services:
  # 删除 asr_service 服务定义

  worker:
    environment:
      # 删除 ASR_SERVICE_URL
      # 新增火山引擎配置
      - VOLCENGINE_ASR_APP_KEY=${VOLCENGINE_ASR_APP_KEY}
      - VOLCENGINE_ASR_ACCESS_KEY=${VOLCENGINE_ASR_ACCESS_KEY}
      - VOLCENGINE_ASR_RESOURCE_ID=volc.bigasr.auc
      - VOLCENGINE_ASR_ENABLE_SPEAKER_INFO=true
      - VOLCENGINE_ASR_ENABLE_EMOTION=true
      - VOLCENGINE_ASR_ENABLE_GENDER=true
```

---

## 七、错误处理与重试

### 7.1 火山引擎错误码处理

| 错误码 | 含义 | 处理策略 |
|--------|------|----------|
| 20000000 | 成功 | 解析结果 |
| 20000001 | 处理中 | 继续轮询 |
| 20000002 | 队列中 | 继续轮询 |
| 20000003 | 静音音频 | 返回空结果，不重试 |
| 45000001 | 参数无效 | 不重试，返回错误 |
| 45000002 | 空音频 | 不重试，返回错误 |
| 55000031 | 服务繁忙 | 指数退避重试 |
| 550xxxxx | 服务错误 | 指数退避重试 |

### 7.2 轮询策略

```go
const (
    defaultPollInterval = 2 * time.Second
    maxPollTimeout      = 15 * time.Minute
)

func (c *VolcengineClient) pollResult(ctx context.Context, requestID string) (*QueryResponse, error) {
    ticker := time.NewTicker(c.cfg.PollInterval)
    defer ticker.Stop()

    timeout := time.After(c.cfg.PollTimeout)

    for {
        select {
        case <-ctx.Done():
            return nil, ctx.Err()
        case <-timeout:
            return nil, fmt.Errorf("ASR polling timeout after %v", c.cfg.PollTimeout)
        case <-ticker.C:
            resp, err := c.queryTask(ctx, requestID)
            if err != nil {
                return nil, err
            }

            switch resp.StatusCode {
            case 20000000: // 成功
                return resp, nil
            case 20000001, 20000002: // 处理中
                continue
            case 20000003: // 静音
                return &QueryResponse{Result: &ASRResult{}}, nil
            default:
                return nil, fmt.Errorf("ASR failed with code %d: %s", resp.StatusCode, resp.Message)
            }
        }
    }
}
```

---

## 八、测试计划

### 8.1 单元测试

- `volcengine_client_test.go`: Mock HTTP 测试提交和轮询逻辑
- 测试各种错误码处理
- 测试轮询超时

### 8.2 集成测试

1. 准备测试音频文件 (含多说话人)
2. 验证说话人分离正确性
3. 验证时间戳精度
4. 验证情绪/性别检测

### 8.3 端到端测试

1. 上传视频 → 提取音频 → ASR → 验证 segments 表数据
2. 验证 speaker_id 正确传递到后续 TTS 步骤

---

## 九、回滚方案

保留接口抽象设计，可通过配置切换 ASR 实现：

```go
func NewASRClient(cfg *config.Config, logger *zap.Logger) asr.ASRClient {
    if cfg.Volcengine.ASR.AppKey != "" {
        return asr.NewVolcengineClient(cfg.Volcengine.ASR, logger)
    }
    // 回退到本地 Moonshine (需保留 asr_service)
    return asr.NewMoonshineClient(cfg.External.ASR, logger)
}
```

---

## 十、开发步骤

### Phase 1: 基础设施 (Day 1) ✅ 已完成
- [x] 编写设计文档
- [x] 修改 shared/config 添加火山引擎配置
- [x] 修改 worker/internal/config 加载配置
- [x] 数据库 migration 添加新字段

### Phase 2: 客户端实现 (Day 1-2) ✅ 已完成
- [x] 实现 volcengine_client.go
- [x] 重构 client.go 为接口
- [ ] 编写单元测试 (待后续补充)

### Phase 3: 步骤集成 (Day 2) ✅ 已完成
- [x] 修改 asr.go 步骤处理器
- [x] 修改 models/message.go
- [x] 更新 worker 依赖注入

### Phase 4: 清理与测试 (Day 3) ✅ 已完成
- [x] 更新 docker-compose.yml
- [x] 创建 .env.example 示例配置
- [ ] 集成测试 (需要火山引擎凭证)
- [x] 更新文档

---

## 十一、变更文件清单

### 新增文件
| 文件 | 说明 |
|------|------|
| `worker/internal/asr/volcengine_client.go` | 火山引擎 ASR 客户端实现 |
| `.env.example` | 环境变量配置示例 |
| `重构文档/asr重构设计方案.md` | 本设计文档 |

### 修改文件
| 文件 | 变更内容 |
|------|----------|
| `shared/config/config.go` | 新增 VolcengineASRConfig 结构和默认值 |
| `worker/internal/config/config.go` | 添加配置类型别名和验证函数 |
| `worker/internal/asr/client.go` | 重构为接口定义 |
| `worker/internal/models/message.go` | ASRSegment 增加 speaker_id/emotion/gender |
| `worker/internal/worker/steps/deps.go` | ASRClient 类型改为接口 |
| `worker/internal/worker/worker.go` | 更新 ASR 客户端初始化 |
| `worker/internal/worker/steps/asr.go` | 保存新增字段到数据库 |
| `api/internal/database/migrations.go` | 新增 segments 表字段迁移 |
| `docker-compose.yml` | 移除 asr_service，添加火山引擎环境变量 |

---

## 十二、使用说明

### 1. 配置火山引擎凭证

从 [火山引擎控制台](https://console.volcengine.com/speech/app) 获取：
- APP ID → `VOLCENGINE_ASR_APP_KEY`
- Access Token → `VOLCENGINE_ASR_ACCESS_KEY`

### 2. 更新 .env 文件

```bash
cp .env.example .env
# 编辑 .env 填入实际的火山引擎凭证
```

### 3. 启动服务

```bash
docker-compose up -d
```

### 4. 验证 ASR 功能

上传视频后，检查 segments 表是否包含 speaker_id、emotion、gender 字段：

```sql
SELECT idx, src_text, speaker_id, emotion, gender
FROM segments
WHERE task_id = 'your-task-id'
ORDER BY idx;
```
