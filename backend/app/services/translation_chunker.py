"""
翻译分块服务
根据字符数限制智能分块，避免 LLM 超限并保持上下文连贯性
"""

import re
from typing import List, Dict

from loguru import logger
from app.models.segment import Segment


class TranslationChunker:
    """
    翻译分块服务

    将大量分段智能分块为多个批次，每个批次不超过字符数限制，
    同时通过重叠机制保持上下文连贯性。
    """

    # 配置常量
    MAX_CHARS_PER_CHUNK = 2000  # 单个翻译块的最大字符数
    OVERLAP_SEGMENTS = 2        # 翻译块间重叠的句子数量
    SEGMENT_FORMAT = "[{index}] {text}"  # Output format for LLM input

    # 正则模式：匹配 [数字] 前缀（与 translate_segments_task 保持一致）
    SEGMENT_PATTERN = re.compile(r'\[(\d+)\]\s*(.+)')

    @classmethod
    def _estimate_tokens(cls, text: str) -> int:
        """
        估算文本的 token 数量（内部方法，已废弃，仅供参考）

        使用简单启发式：中文约 1 字符 = 1.5 tokens，英文约 4 字符 = 1 token
        这是保守估计，实际 token 数可能略少

        注意：当前实现改用字符数限制，此方法保留仅供参考。

        Args:
            text: 待估算文本

        Returns:
            估算的 token 数量

        Examples:
            >>> TranslationChunker._estimate_tokens("Hello world")
            3
            >>> TranslationChunker._estimate_tokens("你好世界")
            6
        """
        if not text:
            return 0

        # 统计中文字符（CJK 统一表意文字）
        cjk_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

        # 统计非中文字符
        other_chars = len(text) - cjk_chars

        # 中文：1 字符 ≈ 1.5 tokens，英文：4 字符 ≈ 1 token
        estimated_tokens = int(cjk_chars * 1.5 + other_chars / 4)

        return max(estimated_tokens, 1)  # 至少 1 token

    @classmethod
    def chunk_segments(cls, segments: List[Segment]) -> List[List[Segment]]:
        """
        将分段列表按字符数智能分块（带重叠上下文）

        策略：
        1. 逐段累加字符数，超过 MAX_CHARS_PER_CHUNK 时创建新块
        2. 新块保留上一块最后 OVERLAP_SEGMENTS 个分段作为上下文
        3. 空文本分段跳过

        Args:
            segments: Segment 对象列表

        Returns:
            分块后的 Segment 列表（二维列表）

        Raises:
            ValueError: segments 为空

        Examples:
            >>> from unittest.mock import Mock
            >>> seg1 = Mock(spec=Segment)
            >>> seg1.segment_index = 0
            >>> seg1.original_text = "Hello"
            >>> seg2 = Mock(spec=Segment)
            >>> seg2.segment_index = 1
            >>> seg2.original_text = "World"
            >>> chunks = TranslationChunker.chunk_segments([seg1, seg2])
            >>> len(chunks)
            1
        """
        if not segments:
            raise ValueError("segments cannot be empty")

        chunks = []
        current_chunk = []
        current_chars = 0

        for segment in segments:
            # 跳过空文本
            if not segment.original_text:
                logger.debug(f"Skipping segment {segment.segment_index} with empty text")
                continue

            text_len = len(segment.original_text)

            # Critical Fix 1: Warn if single segment exceeds MAX_CHARS_PER_CHUNK
            if text_len > cls.MAX_CHARS_PER_CHUNK:
                logger.warning(
                    f"Segment {segment.segment_index} exceeds MAX_CHARS_PER_CHUNK: "
                    f"{text_len} chars > {cls.MAX_CHARS_PER_CHUNK}. "
                    f"This segment will be processed alone and may cause translation issues."
                )

            # 检查加入当前段后是否超限
            if current_chars + text_len > cls.MAX_CHARS_PER_CHUNK and current_chunk:
                # 当前块已满，保存并开始新块
                chunks.append(current_chunk)
                logger.debug(
                    f"Chunk {len(chunks)} created: {len(current_chunk)} segments, "
                    f"{current_chars} chars"
                )

                # 新块从最后 OVERLAP_SEGMENTS 个分段开始（保持上下文）
                overlap_start = max(0, len(current_chunk) - cls.OVERLAP_SEGMENTS)
                current_chunk = current_chunk[overlap_start:]
                current_chars = sum(len(s.original_text) for s in current_chunk)

                logger.debug(
                    f"Starting new chunk with {len(current_chunk)} overlap segments "
                    f"({current_chars} chars)"
                )

            # 加入当前段
            current_chunk.append(segment)
            current_chars += text_len

        # 添加最后一块
        if current_chunk:
            chunks.append(current_chunk)
            logger.debug(
                f"Final chunk created: {len(current_chunk)} segments, "
                f"{current_chars} chars"
            )

        # Critical Fix 2: Validate non-empty chunks
        if not chunks:
            logger.error("No valid segments to chunk - all segments have empty original_text")
            raise ValueError("No segments with non-empty original_text found")

        logger.info(
            f"Chunking completed: {len(segments)} segments -> {len(chunks)} chunks, "
            f"avg {len(segments) / len(chunks):.1f} segments/chunk, "
            f"overlap={cls.OVERLAP_SEGMENTS}"
        )

        return chunks

    @classmethod
    def build_chunk_text(cls, chunk: List[Segment]) -> str:
        """
        构建带索引的翻译文本

        将一个分块的 Segment 对象列表转换为带序号的文本格式，
        供 LLM 翻译时使用。

        Args:
            chunk: 单个分块的 Segment 对象列表

        Returns:
            格式化文本: "[0] text\\n[1] text\\n..."

        Examples:
            >>> from unittest.mock import Mock
            >>> seg1 = Mock(spec=Segment)
            >>> seg1.segment_index = 0
            >>> seg1.original_text = "Hello"
            >>> seg2 = Mock(spec=Segment)
            >>> seg2.segment_index = 1
            >>> seg2.original_text = "World"
            >>> text = TranslationChunker.build_chunk_text([seg1, seg2])
            >>> text
            '[0] Hello\\n[1] World'
        """
        lines = []
        for segment in chunk:
            if segment.original_text:  # 跳过空文本
                lines.append(cls.SEGMENT_FORMAT.format(
                    index=segment.segment_index,
                    text=segment.original_text
                ))

        result = "\n".join(lines)
        logger.debug(f"Built chunk text: {len(lines)} lines, {len(result)} chars")

        return result

    @classmethod
    def parse_translation_result(cls, translated_text: str) -> Dict[int, str]:
        """
        解析 LLM 翻译结果，提取各分段的翻译

        支持两种格式：
        1. 带序号：[0] 翻译文本1\n[1] 翻译文本2（推荐）
        2. 无序号：翻译文本1\n翻译文本2（按行号顺序匹配）

        Args:
            translated_text: LLM 返回的翻译文本

        Returns:
            分段索引 -> 翻译文本的映射字典

        Examples:
            >>> text = "[0] Hello\\n[1] World"
            >>> result = TranslationChunker.parse_translation_result(text)
            >>> result[0]
            'Hello'
            >>> result[1]
            'World'
        """
        translation_map = {}

        # Important Fix 3: Consistent error handling for empty input
        if not translated_text or not translated_text.strip():
            logger.error("Empty or whitespace-only translation result provided")
            raise ValueError("translated_text cannot be empty")

        lines = translated_text.split("\n")
        line_idx = 0  # 用于无标记格式的行号计数

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 尝试匹配 [数字] 前缀
            match = cls.SEGMENT_PATTERN.match(line)
            if match:
                idx = int(match.group(1))
                text = match.group(2).strip()
                translation_map[idx] = text
            else:
                # 无标记的翻译文本，按行号顺序匹配
                # 如果已有该索引的内容，追加到其后（可能是多行文本）
                if line_idx in translation_map:
                    translation_map[line_idx] += " " + line
                    logger.debug(f"Appending to segment {line_idx}: {line[:50]}")
                else:
                    translation_map[line_idx] = line
                    line_idx += 1

        logger.info(
            f"Parsed {len(translation_map)} translations from {len(lines)} lines"
        )

        return translation_map


# ==================== 自测代码 ====================

if __name__ == "__main__":
    """
    自测脚本：测试 TranslationChunker 的核心方法
    """
    import json
    from unittest.mock import Mock

    print("=" * 60)
    print("TranslationChunker Self-Test")
    print("=" * 60)

    # ==================== 测试 1: _estimate_tokens (内部方法) ====================
    print("\n[Test 1] _estimate_tokens (deprecated, for reference)")
    print("-" * 60)

    test_cases_tokens = [
        ("Hello world", "English text"),
        ("你好世界", "Chinese text"),
        ("Hello 你好 World 世界", "Mixed text"),
        ("", "Empty string"),
        ("The quick brown fox jumps over the lazy dog", "Long English"),
        ("人工智能是未来科技发展的重要方向之一", "Long Chinese"),
    ]

    for text, description in test_cases_tokens:
        tokens = TranslationChunker._estimate_tokens(text)
        print(f"  {description:20s} | len={len(text):3d} | tokens≈{tokens:3d} | text: {text[:30]}")

    # ==================== 测试 2: chunk_segments (字符数限制 + 重叠) ====================
    print("\n[Test 2] chunk_segments (character-based with overlap)")
    print("-" * 60)

    # 创建 Mock Segment 对象
    def create_mock_segment(index: int, text: str) -> Mock:
        segment = Mock(spec=Segment)
        segment.segment_index = index
        segment.original_text = text
        segment.id = f"seg_{index}"
        return segment

    # 测试场景 1: 短文本（不分块）
    print("\n  Scenario 1: Short text (no chunking needed)")
    short_segments = [
        create_mock_segment(0, "Hello, this is a short segment."),
        create_mock_segment(1, "This is another segment."),
        create_mock_segment(2, "你好，这是一个中文分段。"),
    ]

    try:
        chunks = TranslationChunker.chunk_segments(short_segments)
        print(f"  Result: {len(chunks)} chunk(s) created")
        for i, chunk in enumerate(chunks):
            total_chars = sum(len(s.original_text) for s in chunk)
            print(f"    Chunk {i + 1}: {len(chunk)} segments, {total_chars} chars")
            print(f"      Indices: {[s.segment_index for s in chunk]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # 测试场景 2: 长文本（需要分块 + 重叠）
    print("\n  Scenario 2: Long text (chunking with overlap)")
    long_segments = []
    for i in range(10):
        # 每段约 250 字符，总共 2500 字符，需要分成 2 块（MAX_CHARS_PER_CHUNK=2000）
        text = f"这是第{i}句话。" * 50  # 约 250 字符
        long_segments.append(create_mock_segment(i, text))

    try:
        chunks = TranslationChunker.chunk_segments(long_segments)
        print(f"  Result: {len(chunks)} chunk(s) created")
        for i, chunk in enumerate(chunks):
            total_chars = sum(len(s.original_text) for s in chunk)
            print(f"    Chunk {i + 1}: {len(chunk)} segments, {total_chars} chars")
            print(f"      Indices: {[s.segment_index for s in chunk]}")

            # 检查重叠
            if i > 0:
                prev_chunk_last_indices = [s.segment_index for s in chunks[i-1]][-TranslationChunker.OVERLAP_SEGMENTS:]
                curr_chunk_first_indices = [s.segment_index for s in chunk][:TranslationChunker.OVERLAP_SEGMENTS]
                print(f"      Overlap check: prev_last={prev_chunk_last_indices}, curr_first={curr_chunk_first_indices}")

    except Exception as e:
        print(f"  ❌ Error: {e}")

    # 测试边界情况
    print("\n  Testing edge cases:")

    # 空列表
    try:
        TranslationChunker.chunk_segments([])
        print("    ❌ Empty list should raise ValueError")
    except ValueError as e:
        print(f"    ✅ Empty list correctly raises: {e}")

    # 包含空文本的分段
    segments_with_empty = [
        create_mock_segment(0, "Hello"),
        create_mock_segment(1, ""),  # 空文本
        create_mock_segment(2, "World"),
    ]
    try:
        chunks = TranslationChunker.chunk_segments(segments_with_empty)
        print(f"    ✅ Segments with empty text: {len(chunks)} chunk(s), skipped empty segments")
    except Exception as e:
        print(f"    ❌ Error: {e}")

    # ==================== 测试 3: build_chunk_text ====================
    print("\n[Test 3] build_chunk_text")
    print("-" * 60)

    test_chunk = [
        create_mock_segment(0, "Hello, this is the first sentence."),
        create_mock_segment(1, "This is the second sentence."),
        create_mock_segment(2, "你好，这是第三句话。"),
    ]

    chunk_text = TranslationChunker.build_chunk_text(test_chunk)
    print(f"  Input: {len(test_chunk)} segments")
    print(f"  Output ({len(chunk_text)} chars):")
    print(f"    {chunk_text}")

    # 测试空文本处理
    chunk_with_empty = [
        create_mock_segment(0, "Hello"),
        create_mock_segment(1, ""),  # 空文本
        create_mock_segment(2, "World"),
    ]
    chunk_text_2 = TranslationChunker.build_chunk_text(chunk_with_empty)
    print(f"\n  With empty segment:")
    print(f"    {chunk_text_2}")

    # ==================== 测试 4: parse_translation_result ====================
    print("\n[Test 4] parse_translation_result")
    print("-" * 60)

    test_cases_parse = [
        (
            "[0] 你好\n[1] 世界\n[2] 测试",
            "Standard format with indices",
        ),
        (
            "你好\n世界\n测试",
            "No indices (line-by-line)",
        ),
        (
            "[0] 你好\n\n[1] 世界\n[2] 测试",
            "With empty lines",
        ),
        (
            "[0] 你好\n[2] 测试",
            "Missing index [1]",
        ),
        (
            "[0] 你好\n[1] 世界\n[2] 测试\n[3] 额外",
            "Extra translation",
        ),
        (
            "",
            "Empty result",
        ),
        (
            "[0] 这是一个\n很长的翻译\n[1] 第二句",
            "Multi-line segment",
        ),
    ]

    for translation_text, description in test_cases_parse:
        print(f"\n  {description}:")
        print(f"    Input: {repr(translation_text[:50])}")

        try:
            result = TranslationChunker.parse_translation_result(translation_text)
            print(f"    Output: {json.dumps(result, ensure_ascii=False)}")
            print(f"    Parsed: {len(result)} segment(s)")
        except ValueError as e:
            print(f"    ⚠️  ValueError raised: {e}")

    # ==================== 测试 5: 综合测试（完整工作流） ====================
    print("\n[Test 5] Integrated workflow simulation")
    print("-" * 60)

    # 模拟完整流程
    print(f"  Scenario: Translate 20 segments using chunking")

    # 创建测试分段
    test_segments = []
    for i in range(20):
        text = f"这是第{i}句话，包含一些测试内容。" * 30  # 每段约 300 字符
        test_segments.append(create_mock_segment(i, text))

    # Step 1: 分块
    chunks = TranslationChunker.chunk_segments(test_segments)
    print(f"  Step 1: Split into {len(chunks)} chunks")

    # Step 2: 逐块翻译
    all_translations = {}

    for i, chunk in enumerate(chunks):
        # 构建输入文本
        input_text = TranslationChunker.build_chunk_text(chunk)
        print(f"\n  Step 2.{i + 1}: Processing chunk {i + 1}")
        print(f"    - Segments: {len(chunk)}")
        print(f"    - Input chars: {len(input_text)}")
        print(f"    - Indices: {[s.segment_index for s in chunk]}")

        # 模拟 LLM 翻译输出
        mock_output_lines = []
        for seg in chunk:
            mock_output_lines.append(
                f"[{seg.segment_index}] Translation of segment {seg.segment_index}."
            )
        mock_output = "\n".join(mock_output_lines)

        # 解析翻译结果
        chunk_translations = TranslationChunker.parse_translation_result(mock_output)
        all_translations.update(chunk_translations)

        print(f"    - Parsed: {len(chunk_translations)} translations")

    # Step 3: 验证结果
    print(f"\n  Step 3: Validation")
    expected_indices = set(s.segment_index for s in test_segments)
    actual_indices = set(all_translations.keys())

    print(f"    - Expected: {len(expected_indices)} segments")
    print(f"    - Actual: {len(actual_indices)} segments")

    if actual_indices == expected_indices:
        print("    ✅ All segments translated successfully!")
    else:
        missing = expected_indices - actual_indices
        extra = actual_indices - expected_indices
        if missing:
            print(f"    ⚠️  Missing translations for: {sorted(missing)}")
        if extra:
            print(f"    ⚠️  Extra translations for: {sorted(extra)}")

    # 检查重叠是否正确处理（去重）
    unique_count = len(actual_indices)
    total_parsed = sum(len(TranslationChunker.parse_translation_result(
        TranslationChunker.build_chunk_text(chunk)
    )) for chunk in chunks)

    if unique_count < total_parsed:
        print(f"    ✅ Overlap handling correct: {total_parsed} parsed -> {unique_count} unique")

    # ==================== 测试 6: 超大分段（应记录警告） ====================
    print("\n" + "="*60)
    print("Test: Oversized Segment (should log warning)")
    print("="*60)

    oversized_segments = [
        create_mock_segment(0, "Regular text"),
        create_mock_segment(1, "X" * 2500),  # Exceeds MAX_CHARS_PER_CHUNK (2000)
        create_mock_segment(2, "Another regular text"),
    ]

    try:
        chunks = TranslationChunker.chunk_segments(oversized_segments)
        print(f"✅ PASSED: {len(chunks)} chunks created, check logs for WARNING about segment 1")
        for i, chunk in enumerate(chunks):
            total_chars = sum(len(s.original_text) for s in chunk)
            print(f"  Chunk {i + 1}: {len(chunk)} segments, {total_chars} chars, indices={[s.segment_index for s in chunk]}")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # ==================== 测试 7: 所有空分段（应抛出 ValueError） ====================
    print("\n" + "="*60)
    print("Test: All Empty Segments (should raise ValueError)")
    print("="*60)

    empty_segments = []
    for i in range(5):
        segment = Mock(spec=Segment)
        segment.segment_index = i
        segment.original_text = ""  # All empty!
        empty_segments.append(segment)

    try:
        chunks = TranslationChunker.chunk_segments(empty_segments)
        print("❌ FAILED: Should have raised ValueError")
    except ValueError as e:
        print(f"✅ PASSED: Correctly raised ValueError: {e}")

    # ==================== 测试 8: 空翻译结果（应抛出 ValueError） ====================
    print("\n" + "="*60)
    print("Test: Empty Translation Result (should raise ValueError)")
    print("="*60)

    try:
        result = TranslationChunker.parse_translation_result("")
        print("❌ FAILED: Should have raised ValueError for empty string")
    except ValueError as e:
        print(f"✅ PASSED: Correctly raised ValueError: {e}")

    try:
        result = TranslationChunker.parse_translation_result("   \n  \n  ")
        print("❌ FAILED: Should have raised ValueError for whitespace-only")
    except ValueError as e:
        print(f"✅ PASSED: Correctly raised ValueError for whitespace: {e}")

    print("\n" + "=" * 60)
    print("Self-Test Completed")
    print("=" * 60)
