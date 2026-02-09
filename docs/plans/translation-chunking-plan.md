# 智能分块翻译实施计划

## 背景

当前系统使用全文翻译保持上下文，但长视频可能超过 LLM 的 Token 限制，降级为逐句翻译会丢失上下文。需要实现智能分块翻译，既保持上下文又不超 Token 限制。

## 目标

实现智能分块翻译机制：
1. 将长文本按语义分块（不超过 Token 限制）
2. 块间保留重叠上下文（避免断裂）
3. 保持翻译一致性和连贯性
4. 替换现有的全文翻译逻辑

## 技术方案

### 架构设计
```
segments (数据库)
    ↓
TranslationChunker.chunk_segments()  # 分块
    ↓
LLMClient.translate_chunk()          # 翻译单块
    ↓
TranslationChunker.merge_results()   # 合并结果
    ↓
更新 segments.translated_text
```

### 关键参数
- `MAX_CHARS_PER_CHUNK = 2000`  # 单块最大字符数（避免超 Token）
- `OVERLAP_SEGMENTS = 2`        # 块间重叠句数（保持上下文）

## 任务清单

### Task 1: 创建分块服务类
**文件**: `backend/app/services/translation_chunker.py`

**需求**:
1. 创建 `TranslationChunker` 类
2. 实现 `chunk_segments()` 方法：
   - 输入：`List[Segment]`（segments 列表）
   - 输出：`List[List[Segment]]`（分块后的 segments）
   - 算法：
     - 按字符数累加，超过 `MAX_CHARS_PER_CHUNK` 时创建新块
     - 保留最后 `OVERLAP_SEGMENTS` 个句子作为下一块的开头
     - 空句子跳过
3. 实现 `build_chunk_text()` 方法：
   - 输入：`List[Segment]`（单个块）
   - 输出：`str`（带索引的文本，格式：`[0] text\n[1] text`）
4. 实现 `parse_translation_result()` 方法：
   - 输入：`str`（LLM 翻译结果）
   - 输出：`Dict[int, str]`（{segment_index: translated_text}）
   - 支持两种格式：
     - `[0] translated text`（标准格式）
     - 无标记的纯文本（按行号匹配）

**测试要求**:
- 测试短文本（不分块）
- 测试长文本（多块）
- 测试重叠逻辑
- 测试解析翻译结果

**依赖**:
```python
from typing import List, Dict
from app.models.segment import Segment
```

---

### Task 2: 集成到翻译任务
**文件**: `backend/app/workers/tasks.py`

**需求**:
1. 在 `translate_segments_task` 函数中替换现有逻辑
2. 使用 `TranslationChunker` 进行分块翻译：
   ```python
   from app.services.translation_chunker import TranslationChunker

   # 替换现有的全文翻译
   chunker = TranslationChunker()
   chunks = chunker.chunk_segments(segments)

   translation_map = {}
   for chunk in chunks:
       chunk_text = chunker.build_chunk_text(chunk)
       translated = llm_client.translate(
           text=chunk_text,
           source_lang=task.source_language,
           target_lang=task.target_language,
       )
       chunk_results = chunker.parse_translation_result(translated)
       translation_map.update(chunk_results)

   # 更新 segments
   for segment in segments:
       translated_text = translation_map.get(segment.segment_index, segment.original_text)
       await task_service.update_segment_translation(segment.id, translated_text)
   ```
3. 保留降级逻辑（如果分块翻译失败，降级到逐句翻译）
4. 添加日志：
   - 记录分块数量
   - 记录每个块的字符数
   - 记录翻译成功/失败

**测试要求**:
- 手动测试：上传 3-5 分钟视频，验证翻译结果

**依赖**:
- Task 1 完成

---

### Task 3: 添加单元测试
**文件**: `backend/tests/test_translation_chunker.py`

**需求**:
1. 创建测试文件
2. 测试用例：
   - `test_chunk_short_text` - 短文本不分块
   - `test_chunk_long_text` - 长文本多块
   - `test_overlap_logic` - 验证重叠逻辑
   - `test_build_chunk_text` - 验证文本构建格式
   - `test_parse_standard_format` - 解析标准格式翻译
   - `test_parse_plain_format` - 解析无标记格式
   - `test_parse_mixed_format` - 解析混合格式

**测试数据**:
```python
# 创建 Mock Segment 对象
def create_mock_segment(index: int, text: str) -> Segment:
    segment = Mock(spec=Segment)
    segment.segment_index = index
    segment.original_text = text
    segment.id = f"seg_{index}"
    return segment
```

**依赖**:
- Task 1 完成

---

### Task 4: 更新配置文件
**文件**: `backend/app/config.py`

**需求**:
1. 添加分块相关配置：
   ```python
   # 翻译分块配置
   chunk_max_chars: int = Field(
       default=2000,
       description="单个翻译块的最大字符数",
       env="TRANSLATION_CHUNK_MAX_CHARS"
   )
   chunk_overlap_segments: int = Field(
       default=2,
       description="翻译块间重叠的句子数量",
       env="TRANSLATION_CHUNK_OVERLAP_SEGMENTS"
   )
   ```
2. 在 `TranslationChunker` 中使用配置：
   ```python
   from app.config import settings

   MAX_CHARS_PER_CHUNK = settings.chunk_max_chars
   OVERLAP_SEGMENTS = settings.chunk_overlap_segments
   ```

**依赖**:
- Task 1 完成

---

### Task 5: 更新文档
**文件**: `docs/architecture/translation-chunking.md`

**需求**:
1. 创建架构文档
2. 内容包括：
   - 分块算法说明
   - 重叠机制原理
   - 配置参数说明
   - 使用示例
   - 性能对比（分块 vs 全文）

**模板**:
```markdown
# 智能分块翻译

## 概述
智能分块翻译通过将长文本按语义分块，既保持上下文又避免超 Token 限制。

## 分块算法
...

## 重叠机制
...

## 配置说明
...

## 使用示例
...
```

**依赖**:
- Task 1, 2 完成

---

## 验收标准

1. ✅ 所有单元测试通过
2. ✅ 手动测试 5 分钟视频翻译成功
3. ✅ 翻译结果保持上下文连贯性
4. ✅ 日志清晰记录分块过程
5. ✅ 文档完整且准确

## 风险与限制

### 风险
1. 重叠可能导致重复翻译（缓解：解析时去重）
2. 分块边界可能割裂语义（缓解：按句子边界分块）

### 限制
1. 不支持单句超过 `MAX_CHARS_PER_CHUNK` 的情况（极少见）
2. LLM 可能不严格遵循 `[index]` 格式（缓解：智能解析）

## 回滚方案

如果分块翻译失败，系统自动降级到原有的逐句翻译模式。
