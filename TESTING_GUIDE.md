# 智能分块翻译 - 测试指南

**功能**: 智能分块翻译（Translation Chunking）
**版本**: 1.0
**日期**: 2026-02-09

---

## 🎯 测试目标

验证以下功能是否正常工作：

1. ✅ **基础分块** - 长视频自动分块处理
2. ✅ **上下文保持** - 块间重叠机制保持翻译连贯性
3. ✅ **边界情况** - 空段落、超长段落、单段视频的处理
4. ✅ **降级机制** - 分块失败时的单句翻译降级
5. ✅ **日志记录** - 详细的处理过程日志

---

## 📋 测试前准备

### 1. 确认服务状态

```bash
cd /Users/micago/Desktop/Project/video-auto-dubbing

# 检查服务状态
./manage.sh status

# 应看到：
# ✅ Backend (PID: xxx) - http://localhost:8000
# ✅ Worker (PID: xxx)
# ✅ Frontend (PID: xxx) - http://localhost:3000
```

### 2. 重启服务（应用最新代码）

```bash
# 重启所有服务
./manage.sh restart

# 或单独重启 worker（翻译任务执行器）
./manage.sh restart worker
```

### 3. 准备测试视频

**推荐视频类型**:

| 类型 | 时长 | 预估段落数 | 测试重点 |
|------|------|-----------|---------|
| **短视频** | 30秒-1分钟 | 10-20句 | 基础功能验证 |
| **中视频** | 3-5分钟 | 50-100句 | 分块机制验证 |
| **长视频** | 10分钟+ | 200+句 | 性能和稳定性验证 |

**视频要求**:
- 包含清晰的语音（中文或英文）
- 最好包含多个说话人（测试多说话人场景）
- MP4格式

---

## 🧪 测试步骤

### 测试 1: 短视频（基线测试）

**目标**: 验证基础功能未受影响

```bash
# 1. 打开前端
open http://localhost:3000

# 2. 上传短视频（30秒-1分钟）
#    - 源语言: 中文
#    - 目标语言: 英文
#    - 字幕模式: 外挂字幕

# 3. 监控日志
tail -f /tmp/worker.log | grep -E "(Translation|Chunk|translate_segments)"
```

**预期结果**:
```
INFO: Translating 15 segments using chunked translation
INFO: Split into 1 chunks for translation
DEBUG: Chunk 1 created: 15 segments, 800 chars
INFO: Chunk 1/1 translated successfully
INFO: Translation completed: 15 unique translations
```

**验证点**:
- ✅ 只生成1个块（短视频不需要分块）
- ✅ 所有段落都有翻译
- ✅ 任务状态: `completed`

---

### 测试 2: 中视频（分块测试）

**目标**: 验证智能分块和重叠机制

```bash
# 1. 上传中等长度视频（3-5分钟）
#    - 源语言: 中文
#    - 目标语言: 英文

# 2. 监控分块日志
tail -f /tmp/worker.log | grep -E "(Chunk|overlap)"
```

**预期结果**:
```
INFO: Translating 80 segments using chunked translation
INFO: Split into 4 chunks for translation
DEBUG: Chunk 1 created: 20 segments, 1800 chars
DEBUG: Starting new chunk with 2 overlap segments (400 chars)
DEBUG: Chunk 2 created: 21 segments, 1950 chars
DEBUG: Starting new chunk with 2 overlap segments (420 chars)
DEBUG: Chunk 3 created: 22 segments, 1980 chars
DEBUG: Starting new chunk with 2 overlap segments (440 chars)
DEBUG: Chunk 4 created: 19 segments, 1600 chars
INFO: Chunk 1/4 translated successfully
INFO: Chunk 2/4 translated successfully
INFO: Chunk 3/4 translated successfully
INFO: Chunk 4/4 translated successfully
INFO: Translation completed: 80 unique translations
```

**验证点**:
- ✅ 生成多个块（3-5个）
- ✅ 每个块包含2句重叠（除第一块）
- ✅ 所有块成功翻译
- ✅ 最终翻译数量 = 原始段落数（去重成功）

**翻译质量检查**:
```bash
# 下载完成的视频，检查：
# 1. 字幕是否连贯（重叠段落的翻译应一致）
# 2. 是否有缺失的翻译
# 3. 上下文是否合理（不同块之间的过渡自然）
```

---

### 测试 3: 长视频（压力测试）

**目标**: 验证系统在大规模数据下的稳定性

```bash
# 1. 上传长视频（10分钟+）

# 2. 监控内存和处理时间
tail -f /tmp/worker.log | grep -E "(Translating|completed|Failed)"
```

**预期结果**:
```
INFO: Translating 250 segments using chunked translation
INFO: Split into 13 chunks for translation
INFO: Chunk 1/13 translated successfully
INFO: Chunk 2/13 translated successfully
...
INFO: Chunk 13/13 translated successfully
INFO: Translation completed: 250 unique translations
```

**验证点**:
- ✅ 能够处理200+段落
- ✅ 分块数量合理（约10-20个块）
- ✅ 无内存溢出
- ✅ 任务最终完成（不超时）

---

### 测试 4: 边界情况

#### 4.1 空段落处理

**场景**: 视频包含无语音片段（音乐、静音等）

**预期**:
```
DEBUG: Skipping segment 5 with empty text
DEBUG: Skipping segment 12 with empty text
INFO: Chunking completed: 18 segments -> 2 chunks (skipped 2 empty)
```

**验证**: 空段落被正确跳过，不影响分块

---

#### 4.2 超长单段落

**场景**: 某个段落超过2000字符（罕见但可能）

**模拟测试**:
```bash
cd backend && source .venv/bin/activate && python -c "
from app.services.translation_chunker import TranslationChunker
from app.models.segment import Segment
from datetime import datetime
from uuid import uuid4

# 创建一个超长段落
long_seg = Segment(
    id=uuid4(),
    task_id=uuid4(),
    segment_index=0,
    start_time_ms=0,
    end_time_ms=10000,
    original_text='这是一个超长的段落' * 200,  # 2400 chars
    created_at=datetime.now(),
    updated_at=datetime.now()
)

chunks = TranslationChunker.chunk_segments([long_seg])
print(f'Chunks created: {len(chunks)}')
"
```

**预期输出**:
```
WARNING: Segment 0 exceeds max chunk size (2400 > 2000 chars)
Chunks created: 1
```

**验证**: 记录警告但仍处理

---

#### 4.3 降级机制测试

**场景**: LLM API 临时故障

**模拟**:
```python
# 修改环境变量，使用无效的 API Key
export DASHSCOPE_API_KEY="invalid_key_for_test"

# 重启 worker
./manage.sh restart worker

# 上传测试视频
```

**预期日志**:
```
ERROR: Failed to translate chunk 1: API authentication failed
WARNING: Attempting fallback translation for segment 0
WARNING: Attempting fallback translation for segment 1
...
ERROR: Fallback translation failed for segment 5: API authentication failed
INFO: Translation completed with errors: 10/15 translated
```

**验证**:
- ✅ 分块失败时尝试单句降级
- ✅ 单句失败时设置为空字符串（不阻塞任务）

**测试后恢复**:
```bash
# 恢复正确的 API Key
export DASHSCOPE_API_KEY="sk-your-real-key"
./manage.sh restart worker
```

---

## 📊 日志分析

### 关键日志指标

**分块阶段**:
```bash
# 查看分块统计
grep "Chunking completed" /tmp/worker.log | tail -5

# 示例输出：
# INFO: Chunking completed: 80 segments -> 4 chunks, avg 20.0 segments/chunk, overlap=2
```

**分析**:
- `segments` - 总段落数
- `chunks` - 块数量
- `avg X segments/chunk` - 平均每块段落数（应接近10-20）
- `overlap=2` - 重叠句数

---

**翻译阶段**:
```bash
# 查看翻译进度
grep "Chunk.*translated" /tmp/worker.log | tail -20

# 示例输出：
# INFO: Chunk 1/4 translated successfully
# INFO: Chunk 2/4 translated successfully
```

**分析**:
- 所有块都应显示 `successfully`
- 数量应匹配分块阶段的 `chunks` 数

---

**完成阶段**:
```bash
# 查看最终统计
grep "Translation completed" /tmp/worker.log | tail -5

# 示例输出：
# INFO: Translation completed: 80 unique translations
```

**分析**:
- `unique translations` 应等于 `segments` 数（去重成功）

---

### 错误日志排查

**常见错误及解决方案**:

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `segments cannot be empty` | 所有段落都是空的 | 检查ASR是否正常工作 |
| `Failed to translate chunk X: timeout` | LLM API 超时 | 检查网络连接，增加 `TRANSLATION_TIMEOUT` |
| `API authentication failed` | API Key 无效 | 检查 `DASHSCOPE_API_KEY` 环境变量 |
| `No translation found for segment X` | 解析失败 | 检查LLM输出格式，查看原始响应 |

---

## ✅ 验收标准

### 功能性验收

- [ ] 短视频（<1分钟）正常处理，不分块
- [ ] 中视频（3-5分钟）自动分块（3-5块）
- [ ] 长视频（10分钟+）稳定处理（10-20块）
- [ ] 空段落正确跳过
- [ ] 超长单段记录警告但不中断
- [ ] 降级机制在分块失败时生效

### 质量性验收

- [ ] 翻译完整率 ≥ 99%（允许极少数段落失败）
- [ ] 上下文连贯性（人工抽查5-10个跨块边界）
- [ ] 重叠段落翻译一致性（后块覆盖前块）
- [ ] 无明显的翻译质量下降（相比分块前）

### 性能性验收

- [ ] 中视频处理时间 < 5分钟
- [ ] 长视频处理时间 < 15分钟
- [ ] Worker 内存占用 < 1GB
- [ ] 无内存泄漏（连续处理5个视频后内存稳定）

### 可观测性验收

- [ ] 日志包含分块统计信息
- [ ] 日志包含每块处理进度
- [ ] 日志包含错误详情和降级记录
- [ ] 任务状态准确反映处理进度

---

## 🐛 问题报告模板

如果测试发现问题，请提供以下信息：

```markdown
### 问题描述
简要描述问题现象

### 复现步骤
1. 上传xx类型的视频
2. 选择xx语言对
3. 观察到xx错误

### 预期行为
应该xxx

### 实际行为
实际xxx

### 环境信息
- 视频时长: X分X秒
- 段落数: X句
- 源语言: XX
- 目标语言: XX

### 相关日志
```bash
# 粘贴 /tmp/worker.log 相关片段
```

### 截图（如适用）
[粘贴截图]
```

---

## 📞 测试支持

**测试过程中遇到问题？**

1. **查看日志**: `tail -f /tmp/worker.log`
2. **检查服务**: `./manage.sh status`
3. **重启服务**: `./manage.sh restart`
4. **查看API健康**: `curl http://localhost:8000/api/v1/monitoring/health`

**联系方式**:
- 技术文档: `TRANSLATION_CHUNKING_IMPLEMENTATION_SUMMARY.md`
- 实施计划: `docs/plans/translation-chunking-plan.md`

---

## 🎉 测试完成后

**提交测试报告**:
```bash
# 1. 记录测试结果
cat > TEST_REPORT.md << EOF
# 智能分块翻译 - 测试报告

## 测试日期
$(date '+%Y-%m-%d %H:%M:%S')

## 测试结果
- [x] 短视频测试: 通过
- [x] 中视频测试: 通过
- [x] 长视频测试: 通过
- [x] 边界情况测试: 通过
- [x] 降级机制测试: 通过

## 测试数据
- 测试视频数: X
- 成功率: XX%
- 平均处理时间: X分钟

## 问题汇总
（如有问题，使用上述模板记录）

## 结论
✅ 功能就绪，可投产
EOF

# 2. 查看报告
cat TEST_REPORT.md
```

---

**祝测试顺利！** 🚀

**文档版本**: 1.0
**最后更新**: 2026-02-09
**作者**: DeepV Code AI
