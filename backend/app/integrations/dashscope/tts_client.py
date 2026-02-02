"""
DashScope TTS 客户端封装
支持两种模式：
1. 系统音色模式（cosyvoice-v1）- 使用预置音色
2. 声音复刻模式（qwen3-tts-vc-realtime-2026-01-15）- 先复刻，后合成
"""

from typing import Optional

import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat
from loguru import logger

from app.config import settings


class VoiceCloneService:
    """声音复刻服务 - 使用 REST API"""

    # 声音复刻 API URL
    CLONE_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def enroll_voice(
        self,
        audio_path: str,
        target_model: str = "qwen3-tts-vc-realtime-2026-01-15",
        prefix: str = "customvoice",
    ) -> Optional[str]:
        """
        复刻音色（使用 REST API）

        Args:
            audio_path: 音频文件路径（本地文件）或 URL
            target_model: 目标模型
            prefix: 音色前缀（仅允许数字和小写字母，小于10个字符）

        Returns:
            voice_id，失败返回 None
        """
        import base64
        import pathlib
        import requests

        try:
            logger.info(f"Enrolling voice via REST API: audio={audio_path}, model={target_model}")

            # 如果是 URL，先下载到本地
            if audio_path.startswith("http://") or audio_path.startswith("https://"):
                logger.info(f"Downloading audio from URL: {audio_path}")
                resp = requests.get(audio_path, timeout=60)
                resp.raise_for_status()
                audio_data = resp.content
                # 根据 URL 猜测 MIME 类型
                if ".wav" in audio_path.lower():
                    audio_mime_type = "audio/wav"
                elif ".mp3" in audio_path.lower():
                    audio_mime_type = "audio/mpeg"
                elif ".m4a" in audio_path.lower():
                    audio_mime_type = "audio/mp4"
                else:
                    audio_mime_type = "audio/wav"  # 默认
            else:
                # 本地文件
                file_path = pathlib.Path(audio_path)
                if not file_path.exists():
                    logger.error(f"Audio file not found: {audio_path}")
                    return None
                audio_data = file_path.read_bytes()
                suffix = file_path.suffix.lower()
                if suffix == ".wav":
                    audio_mime_type = "audio/wav"
                elif suffix == ".mp3":
                    audio_mime_type = "audio/mpeg"
                elif suffix == ".m4a":
                    audio_mime_type = "audio/mp4"
                else:
                    audio_mime_type = "audio/wav"

            # Base64 编码
            base64_str = base64.b64encode(audio_data).decode()
            data_uri = f"data:{audio_mime_type};base64,{base64_str}"

            # 清理 prefix（只允许数字和小写字母，小于10个字符）
            import re
            clean_prefix = re.sub(r'[^a-z0-9]', '', prefix.lower())[:9]
            if not clean_prefix:
                clean_prefix = "voice"

            payload = {
                "model": "qwen-voice-enrollment",  # 固定值
                "input": {
                    "action": "create",
                    "target_model": target_model,
                    "preferred_name": clean_prefix,
                    "audio": {"data": data_uri}
                }
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            logger.info(f"Sending voice enrollment request to {self.CLONE_API_URL}")
            resp = requests.post(self.CLONE_API_URL, json=payload, headers=headers, timeout=120)

            if resp.status_code != 200:
                logger.error(f"Voice enrollment failed: {resp.status_code}, {resp.text}")
                return None

            result = resp.json()
            voice_id = result.get("output", {}).get("voice")

            if voice_id:
                logger.info(f"Voice enrolled successfully: voice_id={voice_id}")
                return voice_id
            else:
                logger.error(f"Voice enrollment response missing voice_id: {result}")
                return None

        except Exception as e:
            logger.error(f"Voice enrollment error: {e}")
            return None


class TTSClient:
    """DashScope TTS 客户端"""

    # 支持的模型
    MODEL_COSYVOICE = "cosyvoice-v1"  # 系统音色
    MODEL_COSYVOICE_V2 = "cosyvoice-v2"  # 支持声音复刻
    MODEL_QWEN3_VC = "qwen3-tts-vc-realtime-2026-01-15"  # 声音复刻

    # 支持声音复刻的模型列表
    VOICE_CLONE_MODELS = ["cosyvoice-v2", "cosyvoice-v3-flash", "cosyvoice-v3-plus",
                          "qwen3-tts-vc-realtime-2026-01-15", "qwen3-tts-vc-realtime-2025-11-27"]

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
            model: 模型名称
                - cosyvoice-v1: 系统音色（默认）
                - qwen3-tts-vc-realtime-2026-01-15: 声音复刻
            voice: 音色名称或 voice_id
                - 系统音色（cosyvoice-v1）：longxiaochun, longyuan 等
                - 复刻音色（qwen3-tts-vc）：vc_xxx 格式
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

        # 声音复刻服务（支持声音复刻的模型才初始化）
        if self.model in self.VOICE_CLONE_MODELS:
            self.clone_service = VoiceCloneService(self.api_key)
        else:
            self.clone_service = None

        logger.info(
            f"TTS Client initialized: model={self.model}, "
            f"voice={self.voice}, format={self.format}"
        )

    def enroll_voice(
        self, audio_path: str, prefix: str = "custom_voice"
    ) -> Optional[str]:
        """
        复刻音色（仅适用于声音复刻模型）

        Args:
            audio_path: 音频文件路径（本地或 URL），建议 10-20 秒
            prefix: 音色前缀

        Returns:
            voice_id（如 vc_xxx），失败返回 None

        Example:
            >>> client = TTSClient(model="qwen3-tts-vc-realtime-2026-01-15")
            >>> voice_id = client.enroll_voice("sample_audio.wav")
            >>> audio = client.synthesize("你好", voice=voice_id)
        """
        if self.model not in self.VOICE_CLONE_MODELS:
            logger.warning(
                f"Voice cloning only supported for {self.VOICE_CLONE_MODELS}, "
                f"current model: {self.model}"
            )
            return None

        if not self.clone_service:
            self.clone_service = VoiceCloneService(self.api_key)

        return self.clone_service.enroll_voice(
            audio_path=audio_path, target_model=self.model, prefix=prefix
        )

    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        format: Optional[str] = None,
        auto_clone: bool = False,
        clone_audio_path: Optional[str] = None,
    ) -> bytes:
        """
        语音合成

        Args:
            text: 待合成文本
            voice: 音色名称或 voice_id（可选，覆盖初始化参数）
                - 系统音色（cosyvoice-v1）：longxiaochun, longyuan 等
                - 复刻音色（qwen3-tts-vc）：vc_xxx 格式
            format: 音频格式（可选，覆盖初始化参数）
            auto_clone: 是否自动复刻（仅限声音复刻模型）
            clone_audio_path: 复刻音频路径（仅在 auto_clone=True 时使用）

        Returns:
            音频数据（bytes）

        Raises:
            RuntimeError: 合成失败
            ValueError: 参数错误

        Example:
            # 系统音色模式
            >>> client = TTSClient(model="cosyvoice-v1")
            >>> audio = client.synthesize("你好", voice="longxiaochun")

            # 声音复刻模式（手动复刻）
            >>> client = TTSClient(model="qwen3-tts-vc-realtime-2026-01-15")
            >>> voice_id = client.enroll_voice("sample.wav")
            >>> audio = client.synthesize("你好", voice=voice_id)

            # 声音复刻模式（自动复刻）
            >>> client = TTSClient(model="qwen3-tts-vc-realtime-2026-01-15")
            >>> audio = client.synthesize(
            ...     "你好",
            ...     auto_clone=True,
            ...     clone_audio_path="sample.wav"
            ... )
        """
        voice = voice or self.voice
        format = format or self.format

        # 如果是声音复刻模型 + auto_clone
        if (
            self.model in self.VOICE_CLONE_MODELS
            and auto_clone
            and clone_audio_path
            and (not voice or not voice.startswith("vc_"))
        ):
            logger.info("Auto-cloning voice before synthesis...")
            voice = self.enroll_voice(clone_audio_path)
            if not voice:
                raise RuntimeError("Auto-clone failed, cannot synthesize")

        # 验证复刻模型必须使用 voice_id（qwen3-tts-vc 系列）
        if self.model.startswith("qwen3-tts-vc"):
            valid_prefixes = ("vc_", "qwen-tts-vc-")
            if not voice or not voice.startswith(valid_prefixes):
                raise ValueError(
                    f"Model {self.model} requires voice_id (vc_xxx or qwen-tts-vc-xxx format). "
                    f"Got: {voice}. Please call enroll_voice() first or use auto_clone=True."
                )

        logger.info(
            f"Synthesizing: text_len={len(text)}, model={self.model}, "
            f"voice={voice}, format={format}"
        )

        try:
            # 对于 qwen3-tts-vc-realtime 系列，使用 WebSocket 实时 API
            if self.model.startswith("qwen3-tts"):
                audio_data = self._synthesize_realtime(text, voice)
            else:
                # 对于 cosyvoice 等模型，使用 SpeechSynthesizer
                synthesizer = SpeechSynthesizer(
                    model=self.model,
                    voice=voice,
                )
                audio_data = synthesizer.call(text)

            if not audio_data:
                raise RuntimeError("TTS returned empty audio")

            logger.info(f"Synthesis completed: {len(audio_data)} bytes")
            return audio_data

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            raise RuntimeError(f"Synthesis failed: {e}") from e

    def _synthesize_realtime(self, text: str, voice: str) -> bytes:
        """
        使用 QwenTtsRealtime WebSocket API 进行语音合成

        Args:
            text: 待合成文本
            voice: 复刻的 voice_id

        Returns:
            PCM 音频数据（bytes）
        """
        import base64
        import threading
        from dashscope.audio.qwen_tts_realtime import (
            QwenTtsRealtime,
            QwenTtsRealtimeCallback,
            AudioFormat,
        )

        audio_chunks = []
        complete_event = threading.Event()
        error_message = None

        class SyncCallback(QwenTtsRealtimeCallback):
            def on_open(self) -> None:
                logger.debug("WebSocket connection opened")

            def on_close(self, close_status_code, close_msg) -> None:
                logger.debug(f"WebSocket closed: code={close_status_code}, msg={close_msg}")
                complete_event.set()

            def on_event(self, response: dict) -> None:
                nonlocal error_message
                try:
                    event_type = response.get("type", "")
                    if event_type == "response.audio.delta":
                        audio_b64 = response.get("delta", "")
                        if audio_b64:
                            audio_chunks.append(base64.b64decode(audio_b64))
                    elif event_type == "session.finished":
                        complete_event.set()
                    elif event_type == "error":
                        error_message = response.get("error", {}).get("message", "Unknown error")
                        complete_event.set()
                except Exception as e:
                    logger.error(f"Callback error: {e}")
                    error_message = str(e)
                    complete_event.set()

        callback = SyncCallback()

        client = QwenTtsRealtime(
            model=self.model,
            callback=callback,
            url="wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
        )

        try:
            client.connect()
            client.update_session(
                voice=voice,
                response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
                mode="server_commit",
            )

            # 发送文本
            client.append_text(text)
            client.finish()

            # 等待完成（最多 60 秒）
            if not complete_event.wait(timeout=60):
                raise RuntimeError("TTS synthesis timeout")

            if error_message:
                raise RuntimeError(f"TTS error: {error_message}")

            # 合并 PCM 音频块
            pcm_data = b"".join(audio_chunks)

            if not pcm_data:
                raise RuntimeError("No audio data received from TTS")

            # 将 PCM 转换为 MP3（使用 ffmpeg）
            import subprocess
            import tempfile

            # 临时 PCM 文件
            pcm_file = tempfile.NamedTemporaryFile(suffix=".pcm", delete=False)
            pcm_file.write(pcm_data)
            pcm_file.close()

            # 临时 MP3 文件
            mp3_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            mp3_file.close()

            try:
                # PCM -> MP3: 24kHz, mono, 16bit
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "s16le",  # 16-bit signed little-endian
                    "-ar", "24000",  # 24kHz
                    "-ac", "1",      # mono
                    "-i", pcm_file.name,
                    "-codec:a", "libmp3lame",
                    "-b:a", "128k",
                    mp3_file.name
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                # 读取 MP3 数据
                with open(mp3_file.name, "rb") as f:
                    mp3_data = f.read()

                logger.info(f"PCM->MP3 conversion: {len(pcm_data)} bytes -> {len(mp3_data)} bytes")
                return mp3_data

            finally:
                # 清理临时文件
                import os
                try:
                    os.unlink(pcm_file.name)
                    os.unlink(mp3_file.name)
                except Exception:
                    pass

        finally:
            try:
                client.close()
            except Exception:
                pass

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
            音色名称列表（系统音色）或空列表（复刻音色需要先注册）

        Note:
            - cosyvoice-v1: 返回预定义的系统音色列表
            - qwen3-tts-vc-realtime: 返回空列表（需要调用 enroll_voice）
        """
        if self.model == self.MODEL_COSYVOICE:
            # 预定义的系统音色（cosyvoice-v1）
            return [
                "longxiaochun",  # 龙小春（女声）
                "longyunshu",  # 龙韵书（女声）
                "longhua",  # 龙华（男声）
                "longsiqian",  # 龙思谦（男声）
                "longwan",  # 龙婉（女声）
                "longxiaoxia",  # 龙小夏（女声）
                "longjing",  # 龙靖（男声）
                "longmengchi",  # 龙梦驰（男声）
                "longshushu",  # 龙姝姝（女声）
            ]
        else:
            # 声音复刻模型没有预置音色
            logger.info(
                f"Model {self.model} uses voice cloning. "
                "Call enroll_voice() to create custom voices."
            )
            return []


# 全局单例
_tts_client: Optional[TTSClient] = None


def get_tts_client() -> TTSClient:
    """获取 TTS 客户端单例"""
    global _tts_client
    if _tts_client is None:
        _tts_client = TTSClient()
    return _tts_client
