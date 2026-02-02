"""
声音复刻服务
管理多说话人的 voice_id 复用
"""

import tempfile
from pathlib import Path
from typing import Optional
from uuid import UUID

from loguru import logger

from app.integrations.dashscope import get_tts_client
from app.integrations.oss import get_oss_client
from app.utils.ffmpeg import FFmpegHelper


class VoiceService:
    """声音复刻服务"""

    def __init__(self):
        self.tts_client = get_tts_client()
        self.oss_client = get_oss_client()
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
                audio_clips.append({"path": clip_path})

                duration = seg["end_time_ms"] - seg["start_time_ms"]
                total_duration_ms += duration

                # 如果已经有 15-20 秒，停止提取（避免音频过长）
                if total_duration_ms >= 15000:
                    logger.info(
                        f"Collected {total_duration_ms}ms audio for speaker {speaker_id}"
                    )
                    break

            # 合并音频片段
            merged_audio = self.ffmpeg.merge_audio_segments(
                audio_clips, output_path=f"{temp_dir}/merged.wav"
            )

            logger.info(
                f"Merged audio for speaker {speaker_id}: {merged_audio}, "
                f"duration={total_duration_ms}ms"
            )

            # 上传到 OSS（可选，用于调试）
            oss_key = f"task_{task_id}/voices/speaker_{speaker_id}.wav"
            self.oss_client.upload_file(merged_audio, oss_key)

            logger.info(f"Uploaded voice sample to OSS: {oss_key}")

            # 调用声音复刻 API
            voice_id = self.tts_client.enroll_voice(
                audio_path=merged_audio, prefix=f"task_{task_id}_{speaker_id}"
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
