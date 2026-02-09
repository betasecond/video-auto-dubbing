"""
翻译分块服务
根据 token 限制智能分块，避免 LLM 超限并保持上下文连贯性
"""

import re
from typing import Optional

from loguru import logger


class TranslationChunker:
    """
    翻译分块服务

    将大量分段智能分块为多个批次，每个批次不超过 LLM token 限制，
    同时尽量保持语义完整性（避免在段落中间截断）。
    """

    # 正则模式：匹配 [数字] 前缀（与 translate_segments_task 保持一致）
    SEGMENT_PATTERN = re.compile(r'\[(\d+)\]\s*(.+)')

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """
        估算文本的 token 数量

        使用简单启发式：中文约 1 字符 = 1.5 tokens，英文约 4 字符 = 1 token
        这是保守估计，实际 token 数可能略少

        Args:
            text: 待估算文本

        Returns:
            估算的 token 数量

        Examples:
            >>> TranslationChunker.estimate_tokens("Hello world")
            3
            >>> TranslationChunker.estimate_tokens("你好世界")
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
    def chunk_segments(
        cls,
        segments: list[dict],
        max_tokens_per_chunk: int = 1500,
        reserve_tokens: int = 500,
    ) -> list[list[dict]]:
        """
        将分段列表智能分块

        策略：
        1. 逐段累加，估算当前块的 token 数
        2. 如果加入下一段会超限，则开始新块
        3. 保留 reserve_tokens 用于 system prompt 和翻译输出

        Args:
            segments: 分段列表，每个分段为 dict，需包含 'original_text' 和 'segment_index'
            max_tokens_per_chunk: 每块的最大 token 限制（默认 1500）
            reserve_tokens: 为 prompt 和输出预留的 token（默认 500）

        Returns:
            分块后的分段列表（二维列表）

        Raises:
            ValueError: segments 为空或参数无效

        Examples:
            >>> segments = [
            ...     {"segment_index": 0, "original_text": "Hello"},
            ...     {"segment_index": 1, "original_text": "World"},
            ... ]
            >>> chunks = TranslationChunker.chunk_segments(segments, max_tokens_per_chunk=100)
            >>> len(chunks)
            1
        """
        if not segments:
            raise ValueError("segments cannot be empty")

        if max_tokens_per_chunk <= reserve_tokens:
            raise ValueError(
                f"max_tokens_per_chunk ({max_tokens_per_chunk}) must be greater than "
                f"reserve_tokens ({reserve_tokens})"
            )

        # 实际可用的 token 数
        usable_tokens = max_tokens_per_chunk - reserve_tokens

        chunks = []
        current_chunk = []
        current_tokens = 0

        for segment in segments:
            original_text = segment.get("original_text", "")
            segment_index = segment.get("segment_index")

            if segment_index is None:
                logger.warning(f"Segment missing 'segment_index': {segment}")
                continue

            # 构建带序号的文本（与 LLM 输入格式一致）
            formatted_text = f"[{segment_index}] {original_text}"
            segment_tokens = cls.estimate_tokens(formatted_text)

            # 检查单个分段是否超限
            if segment_tokens > usable_tokens:
                logger.warning(
                    f"Segment {segment_index} exceeds token limit: "
                    f"{segment_tokens} > {usable_tokens}, will process separately"
                )
                # 单独成块（即使超限也要处理）
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_tokens = 0

                chunks.append([segment])
                continue

            # 检查加入当前段后是否超限
            if current_tokens + segment_tokens > usable_tokens:
                # 当前块已满，开始新块
                if current_chunk:
                    chunks.append(current_chunk)
                    logger.debug(
                        f"Chunk created: {len(current_chunk)} segments, "
                        f"~{current_tokens} tokens"
                    )

                current_chunk = [segment]
                current_tokens = segment_tokens
            else:
                # 加入当前块
                current_chunk.append(segment)
                current_tokens += segment_tokens

        # 添加最后一块
        if current_chunk:
            chunks.append(current_chunk)
            logger.debug(
                f"Final chunk created: {len(current_chunk)} segments, "
                f"~{current_tokens} tokens"
            )

        logger.info(
            f"Chunking completed: {len(segments)} segments -> {len(chunks)} chunks, "
            f"avg {len(segments) / len(chunks):.1f} segments/chunk"
        )

        return chunks

    @classmethod
    def parse_translation_result(
        cls, translation_text: str, segment_count: int
    ) -> dict[int, str]:
        """
        解析 LLM 翻译结果，提取各分段的翻译

        支持两种格式：
        1. 带序号：[0] 翻译文本1\n[1] 翻译文本2
        2. 无序号：翻译文本1\n翻译文本2（按行号匹配）

        Args:
            translation_text: LLM 返回的翻译文本
            segment_count: 期望的分段数量

        Returns:
            分段索引 -> 翻译文本的映射字典

        Examples:
            >>> text = "[0] Hello\\n[1] World"
            >>> result = TranslationChunker.parse_translation_result(text, 2)
            >>> result[0]
            'Hello'
            >>> result[1]
            'World'
        """
        translation_map = {}

        if not translation_text:
            logger.warning("Empty translation result")
            return translation_map

        lines = translation_text.split("\n")

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
                if len(translation_map) < segment_count:
                    next_idx = len(translation_map)
                    translation_map[next_idx] = line
                else:
                    # 超出预期数量，记录警告但仍保留（可能是多行文本）
                    logger.debug(f"Extra translation line (appending to last): {line[:50]}")
                    if translation_map:
                        last_idx = max(translation_map.keys())
                        translation_map[last_idx] += " " + line

        # 检查解析结果
        expected_indices = set(range(segment_count))
        parsed_indices = set(translation_map.keys())

        if parsed_indices != expected_indices:
            missing = expected_indices - parsed_indices
            extra = parsed_indices - expected_indices

            if missing:
                logger.warning(f"Missing translations for indices: {sorted(missing)}")
            if extra:
                logger.warning(f"Extra translations for indices: {sorted(extra)}")

        logger.info(
            f"Parsed {len(translation_map)}/{segment_count} translations "
            f"from {len(lines)} lines"
        )

        return translation_map


# ==================== 自测代码 ====================

if __name__ == "__main__":
    """
    自测脚本：测试 TranslationChunker 的三个核心方法
    """
    import json

    print("=" * 60)
    print("TranslationChunker Self-Test")
    print("=" * 60)

    # ==================== 测试 1: estimate_tokens ====================
    print("\n[Test 1] estimate_tokens")
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
        tokens = TranslationChunker.estimate_tokens(text)
        print(f"  {description:20s} | len={len(text):3d} | tokens≈{tokens:3d} | text: {text[:30]}")

    # ==================== 测试 2: chunk_segments ====================
    print("\n[Test 2] chunk_segments")
    print("-" * 60)

    # 创建测试分段（模拟真实数据）
    test_segments = [
        {"segment_index": 0, "original_text": "Hello, this is a short segment."},
        {"segment_index": 1, "original_text": "This is another segment."},
        {"segment_index": 2, "original_text": "你好，这是一个中文分段。"},
        {"segment_index": 3, "original_text": "这是另一个中文分段，内容稍长一些。"},
        {
            "segment_index": 4,
            "original_text": "This is a much longer segment with a lot more text to test the token limit. "
            * 10,
        },
        {"segment_index": 5, "original_text": "Final short segment."},
    ]

    print(f"  Total segments: {len(test_segments)}")
    print(f"  Max tokens per chunk: 200")
    print(f"  Reserve tokens: 50")

    try:
        chunks = TranslationChunker.chunk_segments(
            test_segments, max_tokens_per_chunk=200, reserve_tokens=50
        )

        print(f"\n  Result: {len(chunks)} chunks created")

        for i, chunk in enumerate(chunks):
            chunk_text = "\n".join(
                f"[{seg['segment_index']}] {seg['original_text'][:30]}..."
                for seg in chunk
            )
            total_tokens = sum(
                TranslationChunker.estimate_tokens(
                    f"[{seg['segment_index']}] {seg['original_text']}"
                )
                for seg in chunk
            )
            print(f"\n  Chunk {i + 1}:")
            print(f"    - Segments: {len(chunk)}")
            print(f"    - Estimated tokens: {total_tokens}")
            print(f"    - Indices: {[seg['segment_index'] for seg in chunk]}")

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

    # 无效参数
    try:
        TranslationChunker.chunk_segments(test_segments, max_tokens_per_chunk=100, reserve_tokens=100)
        print("    ❌ Invalid params should raise ValueError")
    except ValueError as e:
        print(f"    ✅ Invalid params correctly raises: {e}")

    # ==================== 测试 3: parse_translation_result ====================
    print("\n[Test 3] parse_translation_result")
    print("-" * 60)

    test_cases_parse = [
        (
            "[0] 你好\n[1] 世界\n[2] 测试",
            3,
            "Standard format with indices",
        ),
        (
            "你好\n世界\n测试",
            3,
            "No indices (line-by-line)",
        ),
        (
            "[0] 你好\n\n[1] 世界\n[2] 测试",
            3,
            "With empty lines",
        ),
        (
            "[0] 你好\n[2] 测试",
            3,
            "Missing index [1]",
        ),
        (
            "[0] 你好\n[1] 世界\n[2] 测试\n[3] 额外",
            3,
            "Extra translation",
        ),
        (
            "",
            3,
            "Empty result",
        ),
    ]

    for translation_text, segment_count, description in test_cases_parse:
        print(f"\n  {description}:")
        print(f"    Input: {repr(translation_text[:50])}")

        result = TranslationChunker.parse_translation_result(
            translation_text, segment_count
        )

        print(f"    Output: {json.dumps(result, ensure_ascii=False)}")
        print(f"    Parsed: {len(result)}/{segment_count} segments")

    # ==================== 综合测试 ====================
    print("\n[Integrated Test] Full workflow simulation")
    print("-" * 60)

    # 模拟完整流程
    segments = [
        {"segment_index": i, "original_text": f"Segment {i} with some text."}
        for i in range(20)
    ]

    print(f"  Scenario: Translate {len(segments)} segments")

    # 分块
    chunks = TranslationChunker.chunk_segments(
        segments, max_tokens_per_chunk=300, reserve_tokens=100
    )

    print(f"  Step 1: Split into {len(chunks)} chunks")

    # 模拟翻译每一块
    all_translations = {}

    for i, chunk in enumerate(chunks):
        # 构建输入
        input_text = "\n".join(
            f"[{seg['segment_index']}] {seg['original_text']}" for seg in chunk
        )

        # 模拟 LLM 输出（实际应调用 LLMClient）
        mock_output = "\n".join(
            f"[{seg['segment_index']}] 翻译{seg['segment_index']}" for seg in chunk
        )

        # 解析结果
        chunk_translations = TranslationChunker.parse_translation_result(
            mock_output, len(chunk)
        )

        all_translations.update(chunk_translations)

        print(f"  Step 2.{i + 1}: Translated chunk {i + 1} -> {len(chunk_translations)} translations")

    # 验证
    expected_count = len(segments)
    actual_count = len(all_translations)

    print(f"\n  Final result: {actual_count}/{expected_count} translations")

    if actual_count == expected_count:
        print("  ✅ All segments translated successfully!")
    else:
        missing = set(range(expected_count)) - set(all_translations.keys())
        print(f"  ⚠️  Missing translations for indices: {sorted(missing)}")

    print("\n" + "=" * 60)
    print("Self-Test Completed")
    print("=" * 60)
