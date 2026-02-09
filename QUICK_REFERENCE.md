# 智能分块翻译 - 快速参考

> **一页纸速查表** - 开发/测试/调试的常用命令和指标

---

## 🚀 快速启动

```bash
# 项目根目录
cd /Users/micago/Desktop/Project/video-auto-dubbing

# 启动所有服务
./manage.sh start

# 重启所有服务（应用代码更改）
./manage.sh restart

# 查看服务状态
./manage.sh status

# 查看日志
./manage.sh logs worker    # Worker 日志
./manage.sh logs backend   # Backend 日志
./manage.sh logs frontend  # Frontend 日志
```

---

## 🔍 监控分块翻译

### 实时监控

```bash
# 监控分块活动（推荐）
tail -f /tmp/worker.log | grep -E "(Translation|Chunk|translate_segments)"

# 只看关键信息
tail -f /tmp/worker.log | grep -E "(Translating.*segments|Split into.*chunks|Translation completed)"

# 监控错误
tail -f /tmp/worker.log | grep -i error
```

### 关键日志模式

**成功的分块翻译流程**:
```
INFO: Translating 80 segments using chunked translation
INFO: Split into 4 chunks for translation
INFO: Chunk 1/4 translated successfully
INFO: Chunk 2/4 translated successfully
INFO: Chunk 3/4 translated successfully
INFO: Chunk 4/4 translated successfully
INFO: Translation completed: 80 unique translations
```

**短视频（无需分块）**:
```
INFO: Translating 15 segments using chunked translation
INFO: Split into 1 chunks for translation
INFO: Chunk 1/1 translated successfully
INFO: Translation completed: 15 unique translations
```

---

## 📊 性能指标

### 预期处理时间

| 视频时长 | 段落数 | 块数 | 处理时间 |
|---------|--------|------|---------|
| 30秒-1分钟 | 10-20 | 1 | 30秒-1分钟 |
| 3-5分钟 | 50-100 | 3-5 | 2-4分钟 |
| 10分钟+ | 200+ | 10-15 | 8-12分钟 |

### 分块指标

- **MAX_CHARS_PER_CHUNK**: 2000字符
- **OVERLAP_SEGMENTS**: 2句
- **预期块大小**: 10-20个段落/块
- **重叠开销**: ~10-15%（可接受）

---

## 🧪 快速测试

### 基础功能测试

```bash
# 1. 打开前端
open http://localhost:3000

# 2. 在另一个终端监控日志
tail -f /tmp/worker.log | grep Translation

# 3. 上传测试视频
# - 源语言: 中文
# - 目标语言: 英文
# - 字幕模式: 外挂字幕

# 4. 观察日志输出
# 应看到: "Translating X segments using chunked translation"
```

### 验证分块正确性

```bash
# 查看最近的分块统计
grep "Chunking completed" /tmp/worker.log | tail -5

# 示例输出：
# INFO: Chunking completed: 80 segments -> 4 chunks, avg 20.0 segments/chunk, overlap=2
```

**健康指标**:
- ✅ `avg X segments/chunk` 在 10-25 之间
- ✅ `overlap=2`（固定值）
- ✅ `chunks` 数量合理（segments/20 左右）

---

## 🐛 故障排查

### 常见问题速查

| 症状 | 可能原因 | 快速修复 |
|------|---------|---------|
| 日志无 "chunked translation" | Worker未重启 | `./manage.sh restart worker` |
| "segments cannot be empty" | ASR失败 | 检查ASR配置和API Key |
| "Failed to translate chunk X" | LLM API问题 | 检查 `DASHSCOPE_API_KEY` |
| 翻译缺失部分段落 | 解析失败 | 查看ERROR日志，检查LLM输出格式 |
| Worker崩溃 | 内存溢出 | 检查视频是否过大（>30分钟） |

### 诊断命令

```bash
# 检查环境变量
./manage.sh logs backend | grep -i "DASHSCOPE_API_KEY"

# 检查数据库连接
./manage.sh logs backend | grep -i "database.*connected"

# 检查Celery任务注册
./manage.sh logs worker | grep "translate_segments"

# 查看最近的错误
tail -100 /tmp/worker.log | grep -i error
```

---

## 📝 代码快速定位

### 核心文件

```bash
# 分块服务（核心逻辑）
code backend/app/services/translation_chunker.py

# 翻译任务（集成点）
code backend/app/workers/tasks.py

# LLM客户端（提示词）
code backend/app/integrations/dashscope/llm_client.py
```

### 关键类和方法

**TranslationChunker**:
```python
# 位置: backend/app/services/translation_chunker.py

class TranslationChunker:
    # 配置
    MAX_CHARS_PER_CHUNK = 2000
    OVERLAP_SEGMENTS = 2

    # 核心方法
    @classmethod
    def chunk_segments(cls, segments: List[Segment]) -> List[List[Segment]]
        """分块算法"""

    @classmethod
    def build_chunk_text(cls, chunk: List[Segment]) -> str
        """构建LLM输入"""

    @classmethod
    def parse_translation_result(cls, translated_text: str) -> Dict[int, str]
        """解析LLM输出"""
```

**集成点**:
```python
# 位置: backend/app/workers/tasks.py

@celery_app.task(name="translate_segments")
def translate_segments_task(self, previous_result, task_id: str):
    # 使用分块翻译
    chunks = TranslationChunker.chunk_segments(segments)
    for chunk in chunks:
        chunk_text = TranslationChunker.build_chunk_text(chunk)
        translated = llm_client.translate(chunk_text, ...)
        # ...
```

---

## 🔧 配置调整

### 修改分块参数

**文件**: `backend/app/services/translation_chunker.py`

```python
class TranslationChunker:
    MAX_CHARS_PER_CHUNK = 2000  # 增大→减少块数，降低API调用
    OVERLAP_SEGMENTS = 2         # 增大→更好的上下文，但更多开销
```

**修改后需重启**:
```bash
./manage.sh restart worker
```

### 修改翻译提示词

**文件**: `backend/app/integrations/dashscope/llm_client.py`

```python
def _build_system_prompt(self, source_lang: str, target_lang: str, video_duration_ms: Optional[int] = None) -> str:
    prompt = f"""你是一个专业的视频配音翻译专家。

任务：将{source_name}文本翻译成{target_name}

⚠️ 核心约束（最重要）：
- 原文朗读时长：约{video_duration_ms / 1000:.1f if video_duration_ms else '未知'} 秒
...
"""
```

**修改后需重启**:
```bash
./manage.sh restart worker
```

---

## 📈 性能优化提示

### API调用优化

**当前策略**: 智能分块（2000字符/块）

**如果要减少API调用**:
```python
# 增大块大小（需权衡Token限制）
MAX_CHARS_PER_CHUNK = 3000  # 从2000增到3000

# 减少重叠（会降低上下文质量）
OVERLAP_SEGMENTS = 1  # 从2减到1
```

**如果要提高翻译质量**:
```python
# 增加重叠（更多上下文）
OVERLAP_SEGMENTS = 3  # 从2增到3

# 降低LLM temperature（更稳定）
temperature=0.05  # 从0.1降到0.05（在llm_client.py中）
```

### 内存优化

**当前实现**: 全量加载segments到内存

**如果处理超长视频**（>1小时）:
```python
# 可考虑实现流式处理
# 修改 translate_segments_task 分批加载segments

# 伪代码:
BATCH_SIZE = 100
for offset in range(0, total_segments, BATCH_SIZE):
    segments_batch = load_segments(offset, BATCH_SIZE)
    chunks = TranslationChunker.chunk_segments(segments_batch)
    # ...
```

---

## 🎯 快速验收清单

```bash
# 复制此清单，逐项验证：

[ ] 服务健康检查通过
    curl http://localhost:8000/api/v1/monitoring/health

[ ] Worker正常运行
    ./manage.sh status | grep "Worker.*PID"

[ ] 上传短视频（<1分钟）测试基础功能
    观察日志: "Split into 1 chunks"

[ ] 上传中视频（3-5分钟）测试分块
    观察日志: "Split into 3-5 chunks"

[ ] 检查翻译完成率
    grep "Translation completed" /tmp/worker.log | tail -1
    # 应显示: "X unique translations"（X = 段落总数）

[ ] 验证翻译质量
    下载完成的视频，检查字幕连贯性

[ ] 检查错误率
    grep -i error /tmp/worker.log | wc -l
    # 应为0或极少数

[ ] 性能验收
    记录处理时间，对比预期指标表
```

---

## 📞 获取帮助

**文档**:
- 📄 实施总结: `TRANSLATION_CHUNKING_IMPLEMENTATION_SUMMARY.md`
- 📋 测试指南: `TESTING_GUIDE.md`
- 📐 系统架构: `docs/architecture/system-overview.md`

**日志位置**:
- Worker: `/tmp/worker.log`
- Backend: `/tmp/backend.log`
- Frontend: `/tmp/frontend.log`

**健康检查**:
```bash
# API健康
curl http://localhost:8000/api/v1/monitoring/health

# 系统统计
curl http://localhost:8000/api/v1/monitoring/stats

# Celery检查
curl http://localhost:8000/api/v1/monitoring/celery/inspect
```

---

**更新时间**: 2026-02-09
**版本**: 1.0
**快速参考 - 开箱即用！** 📦
