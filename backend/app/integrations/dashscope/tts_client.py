"""
DashScope TTS 客户端封装
语音合成服务
"""

from typing import Optional

import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
from loguru import logger

from app.config import settings


class TTSClient:
    """DashScope TTS 客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        voice: Optional[str] = None,
        format: Optional[str] = None,
    ):
        """
        初始化 TTS 客户端

        Args:
            api_key: DashScope API Key
            model: 模型名称，如 cosyvoice-v1
            voice: 音色名称，如 longxiaochun
            format: 音频格式，如 mp3, wav, pcm
        """
        self.api_key = api_key or settings.dashscope_api_key
        self.model = model or settings.tts_model
        self.voice = voice or settings.tts_voice
        self.format = format or settings.tts_format

        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY is required")

        # 设置 API Key
        dashscope.api_key = self.api_key

        logger.info(
            f"TTS Client initialized: model={self.model}, "
            f"voice={self.voice}, format={self.format}"
        )

    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        format: Optional[str] = None,
    ) -> bytes:
        """
        语音合成（同步模式）

        Args:
            text: 待合成文本
            voice: 音色名称（可选，默认使用初始化时的配置）
            format: 音频格式（可选，默认使用初始化时的配置）

        Returns:
            音频数据（bytes）

        Raises:
            RuntimeError: 合成失败
        """
        voice = voice or self.voice
        format = format or self.format

        logger.info(
            f"Synthesizing: {len(text)} chars, "
            f"voice={voice}, format={format}"
        )

        try:
            synthesizer = SpeechSynthesizer(
                model=self.model,
                voice=voice,
            )

            # 调用合成
            audio_data = synthesizer.call(text)

            if not audio_data:
                raise RuntimeError("TTS returned empty audio")

            logger.info(f"Synthesis completed: {len(audio_data)} bytes")

            return audio_data

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            raise RuntimeError(f"Synthesis failed: {e}") from e

    def synthesize_with_duration(
        self,
        text: str,
        target_duration_ms: int,
        voice: Optional[str] = None,
        format: Optional[str] = None,
        tolerance: float = 0.1,
    ) -> bytes:
        """
        合成指定时长的音频（通过调整语速）

        Args:
            text: 待合成文本
            target_duration_ms: 目标时长（毫秒）
            voice: 音色名称（可选）
            format: 音频格式（可选）
            tolerance: 时长容差（0.1 表示 ±10%）

        Returns:
            音频数据（bytes）

        Note:
            当前 DashScope TTS 不直接支持时长控制
            这是一个占位实现，实际需要通过语速调整或后处理实现
        """
        # TODO: 实现时长控制
        # 可能的方案：
        # 1. 使用 qwen3-tts-vc-realtime 的实时模式
        # 2. 通过 ffmpeg 后处理调整语速
        # 3. 使用 librosa 等库进行音频拉伸

        logger.warning(
            f"Duration control not fully implemented. "
            f"Target: {target_duration_ms}ms, tolerance: {tolerance}"
        )

        # 暂时使用基础合成
        return self.synthesize(text, voice, format)

    def synthesize_batch(
        self,
        texts: list[str],
        voice: Optional[str] = None,
        format: Optional[str] = None,
    ) -> list[bytes]:
        """
        批量合成

        Args:
            texts: 待合成文本列表
            voice: 音色名称（可选）
            format: 音频格式（可选）

        Returns:
            音频数据列表
        """
        logger.info(f"Batch synthesizing {len(texts)} texts")

        results = []
        for i, text in enumerate(texts):
            try:
                audio = self.synthesize(text, voice, format)
                results.append(audio)
                logger.debug(f"Synthesized {i+1}/{len(texts)}")
            except Exception as e:
                logger.error(f"Failed to synthesize text {i+1}: {e}")
                # 失败时返回空音频
                results.append(b"")

        return results

    def list_voices(self) -> list[str]:
        """
        获取可用音色列表

        Returns:
            音色名称列表

        Note:
            当前返回预定义的音色列表
            实际音色列表请参考 DashScope 文档
        """
        # 预定义的系统音色（cosyvoice-v1）
        system_voices = [
            "longxiaochun",  # 龙小春
            "longyunshu",  # 龙韵书
            "longhua",  # 龙华
            "longsiqian",  # 龙思谦
            "longwan",  # 龙婉
            "longxiaoxia",  # 龙小夏
            "longjing",  # 龙靖
            "longmengchi",  # 龙梦驰
            "longshushu",  # 龙姝姝
        ]

        return system_voices


# 全局单例
_tts_client: Optional[TTSClient] = None


def get_tts_client() -> TTSClient:
    """获取 TTS 客户端单例"""
    global _tts_client
    if _tts_client is None:
        _tts_client = TTSClient()
    return _tts_client
