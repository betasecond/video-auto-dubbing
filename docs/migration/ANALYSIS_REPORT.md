# 阿里云统一平台迁移 - 代码分析报告

> **生成时间**: 2026-02-02
> **分析范围**: OSS 迁移 + LLM 翻译迁移
> **状态**: ✅ 分析完成，准备实施

---

## 📊 总体评估

### 迁移可行性

| 模块 | 当前状态 | 迁移难度 | 预计工时 | 风险等级 |
|-----|---------|---------|---------|---------|
| **OSS** | 已实现基础功能 | 🟢 低 | 1.5-2天 | 🟢 低 |
| **LLM** | DashScope已实现 | 🟢 低 | 1天 | 🟢 低 |
| **ASR** | 待 API 详情 | 🟡 中 | 2天 | 🟡 中 |
| **TTS** | 需全新实现 | 🔴 高 | 3-4天 | 🟡 中 |

**结论**: OSS 和 LLM 迁移可以立即开始，风险低，收益高！

---

## 🔍 OSS 迁移分析

### 现状总结

✅ **已完成**:
- OSS 客户端基础实现 (`shared/oss/oss.go`)
- 存储抽象层 (`shared/storage/object_storage.go`)
- 存储工厂模式 (双重实现，支持降级)
- 配置系统完整

❌ **待完成**:
- 默认后端仍为 MinIO
- 缺少高级功能（分片上传、CDN、生命周期）
- 无数据迁移工具

### 关键发现

#### 1. 架构优势 ✨

**清晰的存储抽象**:
```go
type ObjectStorage interface {
    PutObject(ctx context.Context, key string, reader io.Reader, size int64, contentType string) error
    GetObject(ctx context.Context, key string) (io.ReadCloser, error)
    DeleteObject(ctx context.Context, key string) error
    PresignedGetURL(ctx context.Context, key string, expiry time.Duration) (string, error)
    ObjectExists(ctx context.Context, key string) (bool, error)
}
```

**优雅的降级机制**:
- OSS 初始化失败 → 自动降级到 MinIO
- 适合渐进式迁移

#### 2. 数据库结构优势 🎯

**重要发现**: 数据库仅存储 **对象键(key)**，不存储完整 URL！

```sql
-- tasks 表
source_video_key VARCHAR(500)  -- 仅存 "videos/xxx.mp4"
output_video_key VARCHAR(500)  -- 不存 "https://..."

-- segments 表
tts_audio_key VARCHAR(500)     -- 仅存 "audio/xxx.wav"
```

**影响**: ✅ **无需数据库迁移**！切换存储后端后，Presigned URL 会自动指向新的 OSS 地址。

#### 3. 待优化项

| 功能 | 优先级 | 工作量 | 收益 |
|-----|--------|--------|------|
| **分片上传** | P1 | 2h | 大文件上传速度提升 |
| **ObjectExists 优化** | P1 | 30min | 减少不必要的对象下载 |
| **CDN 加速** | P2 | 1h | 全球访问速度提升 |
| **生命周期管理** | P2 | 1.5h | 自动清理过期文件 |
| **重试机制** | P1 | 1h | 提高稳定性 |
| **迁移工具** | P1 | 4h | 数据平滑迁移 |

---

## 🔍 LLM 翻译迁移分析

### 现状总结

✅ **已完成**:
- DashScope 客户端完整实现
- 工厂模式支持多提供商
- 速率限制器
- 配置系统（环境变量 + 数据库）

🐛 **发现关键 Bug**:
1. **工厂默认值错误**: 默认 GLM 而非 DashScope
2. **类型约束问题**: `translateBatches` 硬编码 `*translate.Client` (GLM 类型)
3. **依赖注入缺失**: `Deps.SettingsLoader` 未定义但被引用

### 关键发现

#### 1. Bug 详情 🐛

**Bug #1: 工厂默认提供商**
```go
// worker/internal/translate/factory.go:21-24
case ProviderGLM, "":  // ❌ 默认 GLM
    // Default to GLM for backward compatibility
```

**修复**:
```go
case ProviderDashScope, "":  // ✅ 默认 DashScope
    // Default to DashScope for cost optimization
```

**Bug #2: 类型约束**
```go
// worker/internal/worker/steps/translate.go:149
func (p *TranslateProcessor) translateBatches(..., client *translate.Client, ...) error
//                                                         ^^^^^^^^^^^^^^^^ 硬编码 GLM 类型
```

**修复**:
```go
func (p *TranslateProcessor) translateBatches(..., client translate.Translator, ...) error
//                                                         ^^^^^^^^^^^^^^^^^^^^ 使用接口
```

**Bug #3: 缺失依赖**
```go
// worker/internal/worker/steps/translate.go:68
effectiveCfg, err := p.deps.ConfigManager.GetEffectiveConfig(ctx, p.deps.SettingsLoader, msg)
//                                                                  ^^^^^^^^^^^^^^^^^^ 未定义
```

**修复**: 添加到 `Deps` 结构体

#### 2. 优化机会 🚀

| 优化项 | 当前状态 | 优化后 | 预期提升 |
|-------|---------|--------|---------|
| **翻译缓存** | 无缓存 | LRU缓存 | API 调用减少 30-50% |
| **批处理** | 固定批次 | 智能分组 | 吞吐量提升 2-3x |
| **并发处理** | 串行 | 并行批次 | 速度提升 2-3x |
| **自适应限流** | 固定 RPS | 动态调整 | 更好利用配额 |

#### 3. 成本分析 💰

**GLM (当前)**:
- 模型: glm-4-flash
- 费用: **免费**（限时促销）
- 限制: 5 RPS

**DashScope (目标)**:
- 模型: qwen-turbo
- 费用: ¥0.3/1M tokens (输入), ¥0.6/1M tokens (输出)
- 典型视频: ~¥0.003 (~$0.0004 USD)

**结论**: 即使付费，成本也极低。考虑保留 GLM 作为免费备选。

---

## 📋 实施计划

### Phase 1: 快速修复（2小时）

#### OSS 配置切换
- [ ] `shared/config/config.go:143` - 改为 `STORAGE_BACKEND=oss`
- [ ] `docker-compose.yml` - 注释 MinIO 服务

#### LLM Bug 修复
- [ ] `worker/internal/translate/factory.go` - 默认 DashScope
- [ ] `worker/internal/worker/steps/translate.go` - 使用接口类型
- [ ] `worker/internal/worker/steps/deps.go` - 添加 SettingsLoader
- [ ] `worker/internal/worker/worker.go` - 注入 SettingsLoader

**验证**:
```bash
cd /Users/micago/worktrees/video-dubbing/oss-default
go test ./shared/storage/... -v

cd /Users/micago/worktrees/video-dubbing/llm-default
go test ./worker/internal/translate/... -v
```

---

### Phase 2: OSS 增强（4小时）

#### 1. 分片上传
```go
// shared/oss/oss.go
func (c *Client) PutObjectMultipart(ctx context.Context, key string, reader io.Reader, size int64, contentType string) error {
    if size > DefaultPartSize {
        return c.bucket.PutObject(key, reader, oss.ContentType(contentType), oss.Routines(3))
    }
    return c.bucket.PutObject(key, reader, oss.ContentType(contentType))
}
```

#### 2. ObjectExists 优化
```go
func (c *Client) ObjectExists(ctx context.Context, key string) (bool, error) {
    _, err := c.bucket.GetObjectMeta(key)  // 使用 HeadObject
    if err != nil {
        if ossErr, ok := err.(oss.ServiceError); ok && ossErr.StatusCode == 404 {
            return false, nil
        }
        return false, err
    }
    return true, nil
}
```

#### 3. 重试机制
```go
func (c *Client) withRetry(operation func() error) error {
    maxRetries := 3
    for attempt := 0; attempt < maxRetries; attempt++ {
        err := operation()
        if err == nil || !isTransientError(err) {
            return err
        }
        time.Sleep(time.Duration(math.Pow(2, float64(attempt))) * time.Second)
    }
    return fmt.Errorf("operation failed after %d retries", maxRetries)
}
```

---

### Phase 3: LLM 缓存（4小时）

#### 实现翻译缓存
```go
// worker/internal/translate/cache.go
type TranslationCache struct {
    cache *lru.Cache[string, cacheEntry]
    mu    sync.RWMutex
    ttl   time.Duration
}

func (c *TranslationCache) Get(texts []string, sourceLang, targetLang string) ([]string, bool)
func (c *TranslationCache) Set(texts []string, translations []string, sourceLang, targetLang string)
```

#### 集成到客户端
```go
// worker/internal/translate/dashscope_client.go
func (c *DashScopeClient) Translate(...) ([]string, error) {
    // 1. Check cache
    if cached, ok := c.cache.Get(texts, sourceLang, targetLang); ok {
        return cached, nil
    }

    // 2. Call API
    results, err := c.translateBatch(...)
    if err != nil {
        return nil, err
    }

    // 3. Update cache
    c.cache.Set(texts, results, sourceLang, targetLang)
    return results, nil
}
```

---

### Phase 4: 数据迁移工具（4小时）

#### MinIO → OSS 迁移脚本
```go
// scripts/migrate_minio_to_oss.go
type MigrationConfig struct {
    SourceMinIO   config.MinIOConfig
    TargetOSS     config.OSSConfig
    Workers       int
    DryRun        bool
    SkipExisting  bool
}

func main() {
    // 1. 连接 MinIO 和 OSS
    // 2. 列举 MinIO 对象
    // 3. 并发复制到 OSS
    // 4. MD5 校验
    // 5. 生成报告
}
```

---

## 🎯 优先级排序

### 立即执行（今天）

1. **LLM Bug 修复** - 阻塞性问题，2小时
2. **OSS 配置切换** - 简单且影响大，30分钟

### 本周完成

3. **OSS 客户端增强** - 提升稳定性，4小时
4. **LLM 翻译缓存** - 显著降低成本，4小时

### 下周完成

5. **数据迁移工具** - 生产环境迁移准备，4小时
6. **批处理优化** - 性能提升，4小时

---

## 📊 预期收益

### OSS 迁移

| 指标 | 迁移前 | 迁移后 | 提升 |
|-----|--------|--------|------|
| **运维成本** | MinIO 服务器 | 按需付费 | -30% |
| **可扩展性** | 单点限制 | 无限扩展 | ∞ |
| **可用性** | 99% | 99.9% | +0.9% |
| **全球访问** | 慢 | CDN 加速 | 5-10x |

### LLM 迁移

| 指标 | 迁移前 (GLM) | 迁移后 (DashScope) | 提升 |
|-----|--------------|-------------------|------|
| **速度** | 3-5s/批次 | 1-2s/批次 | 2-3x |
| **成本** | 免费 | ¥0.003/视频 | 可忽略 |
| **缓存命中** | 0% | 30-50% | API减少50% |
| **并发** | 串行 | 并行 | 2-3x |

---

## ⚠️ 风险与缓解

### 高风险

| 风险 | 影响 | 缓解措施 | 负责人 |
|-----|------|---------|--------|
| OSS 配置错误 | 服务不可用 | 保留 MinIO 降级机制 | - |
| 数据迁移失败 | 文件丢失 | 先验证后删除，保留 MinIO 30天 | - |
| LLM API 超限 | 翻译失败 | 保留 GLM 作为备选 | - |

### 中风险

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| 缓存内存溢出 | 内存占用高 | LRU 驱逐策略，可配置大小 |
| 性能回退 | 体验下降 | 充分测试，灰度发布 |

---

## ✅ 完成标准

### OSS 迁移

- [ ] 默认存储后端为 OSS
- [ ] 分片上传支持 >100MB 文件
- [ ] ObjectExists 使用 HeadObject
- [ ] 重试机制完善
- [ ] 迁移工具可用
- [ ] 文档更新

### LLM 迁移

- [ ] DashScope 为默认提供商
- [ ] 所有类型约束修复
- [ ] 翻译缓存实现
- [ ] GLM 作为备选可用
- [ ] 性能提升 ≥20%
- [ ] 所有测试通过

---

## 📚 相关文档

- [OSS 迁移详细分析](./ALIYUN_MIGRATION_PLAN.md#phase-2-oss-迁移-3天)
- [LLM 配置指南](../guides/DASHSCOPE_LLM_SETUP.md)
- [架构概览](../ARCHITECTURE_OVERVIEW.md)

---

**生成者**: AI 子代理分析系统
**审核**: 待定
**批准**: 待定
**状态**: ✅ 准备实施
