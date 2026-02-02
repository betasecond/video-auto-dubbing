"""
外部服务集成测试
测试 DashScope ASR, LLM, TTS 客户端
"""

import pytest

from app.integrations.dashscope import ASRClient, LLMClient, TTSClient
from app.integrations.oss import OSSClient


@pytest.fixture
def oss_client():
    return OSSClient()


@pytest.fixture
def asr_client():
    return ASRClient()


@pytest.fixture
def llm_client():
    return LLMClient()


@pytest.fixture
def tts_client():
    return TTSClient()


def test_asr_transcribe(asr_client: ASRClient, oss_client: OSSClient):
    """测试 ASR 语音识别"""
    # 使用官方测试音频
    test_audio_url = (
        "https://dashscope.oss-cn-beijing.aliyuncs.com/"
        "samples/audio/paraformer/hello_world_female2.wav"
    )

    # 执行识别
    result = asr_client.transcribe(test_audio_url, timeout=120)

    # 验证结果
    assert result.task_id
    assert result.segments
    assert len(result.segments) > 0
    assert result.full_text
    assert "hello" in result.full_text.lower() or "你好" in result.full_text

    # 验证分段信息
    for segment in result.segments:
        assert segment.text
        assert segment.start_time_ms >= 0
        assert segment.end_time_ms > segment.start_time_ms
        assert segment.duration_ms > 0

    print(f"\n识别结果: {result.full_text}")
    print(f"分段数: {len(result.segments)}")


def test_llm_translate(llm_client: LLMClient):
    """测试 LLM 翻译"""
    # 测试中文翻译成英文
    source_text = "你好世界，这是一个测试。"
    translation = llm_client.translate(
        text=source_text,
        source_lang="zh",
        target_lang="en",
    )

    # 验证结果
    assert translation
    assert len(translation) > 0
    assert translation != source_text
    assert "hello" in translation.lower() or "test" in translation.lower()

    print(f"\n原文: {source_text}")
    print(f"译文: {translation}")


def test_llm_translate_batch(llm_client: LLMClient):
    """测试批量翻译"""
    texts = [
        "早上好",
        "下午好",
        "晚上好",
    ]

    translations = llm_client.translate_batch(
        texts=texts,
        source_lang="zh",
        target_lang="en",
    )

    # 验证结果
    assert len(translations) == len(texts)
    for i, translation in enumerate(translations):
        assert translation
        assert translation != texts[i]
        print(f"\n{texts[i]} -> {translation}")


def test_tts_synthesize(tts_client: TTSClient):
    """测试 TTS 语音合成"""
    text = "你好，这是一个语音合成测试。"

    # 执行合成
    audio_data = tts_client.synthesize(text)

    # 验证结果
    assert audio_data
    assert len(audio_data) > 1000  # 至少有一些音频数据
    assert isinstance(audio_data, bytes)

    print(f"\n合成音频大小: {len(audio_data)} bytes")


def test_tts_list_voices(tts_client: TTSClient):
    """测试获取音色列表"""
    voices = tts_client.list_voices()

    # 验证结果
    assert voices
    assert len(voices) > 0
    assert "longxiaochun" in voices  # 默认音色

    print(f"\n可用音色: {', '.join(voices)}")


@pytest.mark.asyncio
async def test_llm_translate_async(llm_client: LLMClient):
    """测试异步翻译"""
    text = "这是异步翻译测试"

    translation = await llm_client.translate_async(
        text=text,
        source_lang="zh",
        target_lang="en",
    )

    assert translation
    assert translation != text

    print(f"\n异步翻译: {text} -> {translation}")


@pytest.mark.asyncio
async def test_llm_translate_batch_async(llm_client: LLMClient):
    """测试批量异步翻译"""
    texts = [f"测试文本{i+1}" for i in range(5)]

    translations = await llm_client.translate_batch_async(
        texts=texts,
        source_lang="zh",
        target_lang="en",
        concurrency=3,
    )

    assert len(translations) == len(texts)
    for text, translation in zip(texts, translations):
        assert translation
        print(f"\n{text} -> {translation}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
