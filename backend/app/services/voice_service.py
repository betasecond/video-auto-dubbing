"""
声音复刻服务
管理多说话人的 voice_id 复用
"""

import tempfile
from pathlib import Path
from typing import Optional
from uuid import UUID

from loguru import logger

from app.integrations.dashscope import TTSClient
from app.integrations.oss import OSSClient
from app.utils.ffmpeg import FFmpegHelper


class VoiceService:
    """声音复刻服务"""

    def __init__(self):
        self.tts_client = TTSClient()
        self.oss_client = OSSClient()
        self.ffmpeg = FFmpegHelper()

    def enroll_speaker_from_segments(
        self,
        task_id: UUID,
        speaker_id: str,
        audio_path: str,
        segments: list[dict],
    ) -> Optional[str]:
        """
        从分段中提取说话人音频并复刻声音

        Args:
            task_id: 任务 ID
            speaker_id: 说话人 ID
            audio_path: 原始音频文件路径（本地）
            segments: 该说话人的分段列表（包含 start_time_ms, end_time_ms）

        Returns:
            voice_id（如 vc_xxx），失败返回 None

        说明:
            1. 从原始音频中提取该说话人的所有片段
            2. 合并成一个音频文件（10-20秒为佳）
            3. 调用声音复刻 API
            4. 返回 voice_id
        """
        logger.info(
            f"Enrolling speaker: task_id={task_id}, speaker_id={speaker_id}, "
            f"segments={len(segments)}"
        )

        if not segments:
            logger.warning(f"No segments for speaker {speaker_id}")
            return None

        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix=f"voice_enroll_{speaker_id}_")

            # 提取说话人的所有音频片段
            audio_clips = []
            total_duration_ms = 0

            for i, seg in enumerate(segments):
                # 提取片段
                clip_path = self.ffmpeg.extract_segment(
                    audio_path,
                    seg["start_time_ms"],
                    seg["end_time_ms"],
                    output_path=f"{temp_dir}/clip_{i:04d}.wav",
                )
                # 注意：merge_audio_segments 需要 start_ms 和 end_ms 字段
                audio_clips.append({
                    "path": clip_path,
                    "start_ms": 0,  # 合并时顺序拼接，不需要时间轴
                    "end_ms": seg["end_time_ms"] - seg["start_time_ms"],
                })

                duration = seg["end_time_ms"] - seg["start_time_ms"]
                total_duration_ms += duration

                # 如果已经有 15-20 秒，停止提取（避免音频过长）
                if total_duration_ms >= 15000:
                    logger.info(
                        f"Collected {total_duration_ms}ms audio for speaker {speaker_id}"
                    )
                    break

            # 合并音频片段（顺序拼接，不按时间轴）
            # 创建 FFmpeg concat 文件列表
            concat_file = f"{temp_dir}/concat.txt"
            with open(concat_file, "w") as f:
                for clip in audio_clips:
                    f.write(f"file '{clip['path']}'\n")

            # 使用 concat demuxer 合并
            import subprocess
            merged_audio = f"{temp_dir}/merged.wav"
            cmd = [
                "ffmpeg", "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c", "copy", "-y", merged_audio
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            logger.info(
                f"Merged audio for speaker {speaker_id}: {merged_audio}, "
                f"duration={total_duration_ms}ms"
            )

            # 直接使用本地合并后的音频文件调用声音复刻 API
            # （新的 REST API 支持直接上传本地文件）
            logger.info(f"Calling voice enrollment API with local file: {merged_audio}")

            # 生成简洁的 prefix（只允许小写字母和数字，少于10字符）
            import re
            clean_prefix = re.sub(r'[^a-z0-9]', '', speaker_id.lower())[:8]
            if not clean_prefix:
                clean_prefix = "voice"

            # 调用声音复刻 API
            voice_id = self.tts_client.enroll_voice(
                audio_path=merged_audio, prefix=clean_prefix
            )

            if voice_id:
                logger.info(
                    f"Voice enrolled successfully: speaker_id={speaker_id}, "
                    f"voice_id={voice_id}"
                )
            else:
                logger.error(f"Voice enrollment failed for speaker {speaker_id}")

            # 清理临时文件
            import shutil

            shutil.rmtree(temp_dir)

            return voice_id

        except Exception as e:
            logger.error(f"Failed to enroll speaker {speaker_id}: {e}")
            return None

    def get_or_create_voice_id(
        self,
        task_id: UUID,
        speaker_id: str,
        audio_path: str,
        segments: list[dict],
        cache: dict[str, str],
    ) -> Optional[str]:
        """
        获取或创建 voice_id（带缓存）

        Args:
            task_id: 任务 ID
            speaker_id: 说话人 ID
            audio_path: 原始音频文件路径
            segments: 该说话人的分段列表
            cache: voice_id 缓存（speaker_id -> voice_id）

        Returns:
            voice_id

        说明:
            在同一个任务中，同一个 speaker_id 只复刻一次
        """
        # 检查缓存
        if speaker_id in cache:
            logger.info(f"Reusing cached voice_id for speaker {speaker_id}")
            return cache[speaker_id]

        # 复刻新声音
        voice_id = self.enroll_speaker_from_segments(
            task_id, speaker_id, audio_path, segments
        )

        if voice_id:
            cache[speaker_id] = voice_id

        return voice_id
