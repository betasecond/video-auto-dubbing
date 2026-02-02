# 阿里云 ASR 集成分支说明

## 分支信息
- **分支名称**: `feature/aliyun-asr`
- **创建时间**: 2026-02-02
- **目的**: 集成阿里云百炼平台的 Qwen ASR 语音识别服务

## 主要变更

### 1. 新增文件

#### ASR 客户端
- `worker/internal/asr/aliyun_client.go` - 阿里云 ASR 客户端实现

#### 文档
- `docs/aliyun_asr_integration.md` - 阿里云 ASR 集成完整文档
- `ALIYUN_ASR_BRANCH_README.md` - 本分支说明文档

#### 测试
- `tests/test_aliyun_asr.go` - 阿里云 ASR 测试程序

### 2. 修改文件

#### 配置相关
- `shared/config/config.go`
  - 添加 `AliyunASRConfig` 结构体
  - 添加阿里云 ASR 环境变量默认值
  - 在 `ExternalConfig` 中添加 `AliyunASR` 字段

- `worker/internal/config/config.go`
  - 添加 `ASRConfig` 结构体，支持后端选择
  - 添加 `ASR_BACKEND` 环境变量配置
  - 添加 `ValidateAliyunASR` 和 `ValidateASRBackend` 验证函数
  - 添加 `AliyunASRConfig` 类型别名

- `worker/internal/config/manager.go`
  - 修改 `ValidateForASR` 以支持多后端验证

#### ASR 客户端相关
- `worker/internal/asr/client.go`
  - 添加 `ASRBackend` 类型定义
  - 添加 `NewClientWithBackend` 函数支持多后端
  - 定义 `BackendVolcengine` 和 `BackendAliyun` 常量

#### Worker 处理器
- `worker/internal/worker/steps/asr.go`
  - 添加 ASR 后端选择逻辑
  - 使用 `NewClientWithBackend` 创建客户端

## 功能特性

### 支持的 ASR 后端
1. **火山引擎 ASR** (`volcengine`) - 原有实现
   - ✅ 支持时间戳
   - ✅ 支持说话人分离
   - ✅ 支持情绪和性别检测
   - ⏱️ 异步轮询模式

2. **阿里云 ASR** (`aliyun`) - 新增
   - ⚡ 快速同步响应
   - ✅ 支持语言自动检测
   - ✅ 支持文本规范化 (ITN)
   - ❌ 同步API无时间戳
   - ❌ 不支持说话人分离

### 配置方式

#### 环境变量
```bash
# 选择 ASR 后端
ASR_BACKEND=aliyun  # 或 volcengine (默认)

# 阿里云 ASR 配置
ALIYUN_ASR_API_KEY=sk-xxxxxxxxxxxxx
ALIYUN_ASR_MODEL=qwen3-asr-flash
ALIYUN_ASR_ENABLE_ITN=true
ALIYUN_ASR_LANGUAGE=
ALIYUN_ASR_REQUEST_TIMEOUT=60
```

## 使用方法

### 1. 配置环境变量

创建或更新 `.env` 文件：

```bash
# 选择阿里云 ASR
ASR_BACKEND=aliyun

# 配置 API Key
ALIYUN_ASR_API_KEY=sk-your-api-key-here

# 可选配置
ALIYUN_ASR_MODEL=qwen3-asr-flash
ALIYUN_ASR_ENABLE_ITN=true
```

### 2. 运行测试

```bash
# 设置环境变量
export ALIYUN_ASR_API_KEY=sk-xxxxxxxxxxxxx
export TEST_AUDIO_URL=https://your-audio-file.wav

# 运行测试
go run tests/test_aliyun_asr.go
```

### 3. 在 Worker 中使用

Worker 会根据 `ASR_BACKEND` 环境变量自动选择对应的 ASR 后端：

```go
// Worker 自动根据配置创建客户端
asrBackend := asr.BackendVolcengine
if effectiveConfig.ASR.Backend == "aliyun" {
    asrBackend = asr.BackendAliyun
}

asrClient, err := asr.NewClientWithBackend(asrBackend, &effectiveConfig.BaseConfig, logger)
```

## 兼容性说明

### 向后兼容
- ✅ 保留原有火山引擎 ASR 实现
- ✅ 默认使用火山引擎 ASR (`ASR_BACKEND=volcengine`)
- ✅ 所有现有 API 和数据结构保持不变

### 数据库兼容
- ✅ 使用相同的 segments 表结构
- ✅ 阿里云 ASR 结果自动适配现有格式
- ⚠️ `speaker_id` 固定为 `speaker_1`（阿里云不支持说话人分离）
- ⚠️ 所有文本作为单个 segment 存储（阿里云同步API无时间戳）

## 后续计划

### 短期计划
- [ ] 添加单元测试
- [ ] 完善错误处理
- [ ] 添加集成测试

### 中期计划
- [ ] 支持阿里云异步文件转写API (带时间戳)
- [ ] 支持流式识别
- [ ] 支持Base64音频输入

### 长期计划
- [ ] 支持更多 ASR 服务商
- [ ] ASR 服务统一抽象层
- [ ] 性能优化和缓存策略

## 测试建议

1. **功能测试**
   ```bash
   # 测试阿里云 ASR
   ASR_BACKEND=aliyun go run tests/test_aliyun_asr.go

   # 测试火山引擎 ASR (原有)
   ASR_BACKEND=volcengine go test -v ./worker/internal/asr/...
   ```

2. **集成测试**
   - 使用真实音频文件测试
   - 测试不同语言识别
   - 测试错误处理

3. **性能测试**
   - 比较两个后端的响应时间
   - 测试并发请求处理
   - 测试长音频处理

## 注意事项

1. **API Key 安全**
   - ❌ 不要将 API Key 提交到代码仓库
   - ✅ 使用环境变量或配置文件
   - ✅ 生产环境使用密钥管理服务

2. **成本控制**
   - 了解阿里云 ASR 定价策略
   - 监控 API 调用量
   - 设置合理的超时时间

3. **错误处理**
   - 实现重试机制
   - 记录详细错误日志
   - 提供降级方案

## 合并检查清单

在合并到主分支前，请确认：

- [ ] 所有测试通过
- [ ] 文档完整准确
- [ ] 代码符合项目规范
- [ ] 添加了充分的注释
- [ ] 错误处理完善
- [ ] 向后兼容性验证
- [ ] 性能测试通过
- [ ] 安全审查完成

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。

## 参考文档

- [阿里云 ASR 集成文档](docs/aliyun_asr_integration.md)
- [阿里云百炼 API 文档](https://help.aliyun.com/zh/model-studio/qwen-asr-api-reference)
- [项目架构文档](docs/ARCHITECTURE_OVERVIEW.md)
