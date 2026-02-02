"""
FFmpeg 工具类
视频/音频处理
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from loguru import logger


class FFmpegHelper:
    """FFmpeg 工具类"""

    @staticmethod
    def check_ffmpeg() -> bool:
        """检查 FFmpeg 是否已安装"""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def extract_audio(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> str:
        """
        从视频中提取音频

        Args:
            video_path: 视频文件路径
            output_path: 输出音频路径（可选，默认自动生成）
            sample_rate: 采样率（Hz）
            channels: 声道数（1=单声道，2=立体声）

        Returns:
            输出音频文件路径

        Raises:
            RuntimeError: FFmpeg 执行失败
        """
        if not output_path:
            output_path = str(
                Path(video_path).parent / f"{Path(video_path).stem}_audio.wav"
            )

        logger.info(f"Extracting audio: {video_path} -> {output_path}")

        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-vn",  # 不处理视频
            "-acodec",
            "pcm_s16le",  # PCM 16-bit
            "-ar",
            str(sample_rate),  # 采样率
            "-ac",
            str(channels),  # 声道数
            "-y",  # 覆盖输出文件
            output_path,
        ]

        try:
            subprocess.run(
                cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            logger.info(f"Audio extracted: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg extraction failed: {e.stderr.decode()}")
            raise RuntimeError(f"Audio extraction failed: {e.stderr.decode()}")

    def get_duration_ms(self, media_path: str) -> int:
        """
        获取媒体文件时长（毫秒）

        Args:
            media_path: 媒体文件路径

        Returns:
            时长（毫秒）

        Raises:
            RuntimeError: FFprobe 执行失败
        """
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            media_path,
        ]

        try:
            result = subprocess.run(
                cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            duration_sec = float(result.stdout.decode().strip())
            duration_ms = int(duration_sec * 1000)
            logger.info(f"Media duration: {duration_ms}ms ({media_path})")
            return duration_ms
        except subprocess.CalledProcessError as e:
            logger.error(f"FFprobe failed: {e.stderr.decode()}")
            raise RuntimeError(f"Failed to get duration: {e.stderr.decode()}")

    def get_audio_duration_ms(self, audio_path: str) -> int:
        """获取音频文件时长（毫秒）"""
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration_sec = float(result.stdout.strip())
            return int(duration_sec * 1000)
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")
            return 0

    def adjust_audio_speed(
        self, audio_path: str, target_duration_ms: int, output_path: Optional[str] = None
    ) -> str:
        """
        调整音频速度使其符合目标时长

        Args:
            audio_path: 输入音频路径
            target_duration_ms: 目标时长（毫秒）
            output_path: 输出路径（可选）

        Returns:
            输出音频路径
        """
        if not output_path:
            output_path = tempfile.mktemp(suffix=".wav")

        actual_duration_ms = self.get_audio_duration_ms(audio_path)

        if actual_duration_ms <= 0:
            # 无法获取时长，直接复制
            import shutil
            shutil.copy(audio_path, output_path)
            return output_path

        if actual_duration_ms <= target_duration_ms:
            # 不需要加速，直接复制
            import shutil
            shutil.copy(audio_path, output_path)
            logger.debug(f"Audio {actual_duration_ms}ms <= target {target_duration_ms}ms, no speed change")
            return output_path

        # 计算加速比例（atempo 范围 0.5-2.0，超过需要链式调用）
        speed_ratio = actual_duration_ms / target_duration_ms
        logger.info(f"Speeding up audio: {actual_duration_ms}ms -> {target_duration_ms}ms (ratio={speed_ratio:.2f})")

        # 限制最大加速比例（超过4x直接截断，因为音质已经很差了）
        MAX_SPEED_RATIO = 4.0
        if speed_ratio > MAX_SPEED_RATIO:
            logger.warning(
                f"Speed ratio {speed_ratio:.2f}x exceeds max {MAX_SPEED_RATIO}x, "
                f"will truncate instead"
            )
            # 截断到目标时长
            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-t", f"{target_duration_ms/1000}",
                "-ar", "16000",
                output_path
            ]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logger.info(f"Audio truncated: {actual_duration_ms}ms -> {target_duration_ms}ms")
                return output_path
            except subprocess.CalledProcessError as e:
                logger.error(f"Truncation failed: {e.stderr.decode()}")
                import shutil
                shutil.copy(audio_path, output_path)
                return output_path

        # 构建 atempo 滤镜链（atempo 单次范围 0.5-2.0）
        atempo_filters = []
        remaining_ratio = speed_ratio
        while remaining_ratio > 2.0:
            atempo_filters.append("atempo=2.0")
            remaining_ratio /= 2.0
        if remaining_ratio > 1.0:
            atempo_filters.append(f"atempo={remaining_ratio:.4f}")

        if not atempo_filters:
            # 不需要加速
            import shutil
            shutil.copy(audio_path, output_path)
            return output_path

        filter_str = ",".join(atempo_filters)

        cmd = [
            "ffmpeg", "-y", "-i", audio_path,
            "-filter:a", filter_str,
            "-ar", "16000",  # 统一采样率
            output_path
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            new_duration = self.get_audio_duration_ms(output_path)
            logger.info(f"Audio speed adjusted: {actual_duration_ms}ms -> {new_duration}ms")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Speed adjustment failed: {e.stderr.decode()}")
            # 失败时返回原文件
            import shutil
            shutil.copy(audio_path, output_path)
            return output_path

    def merge_audio_segments(
        self,
        segments: list[dict],
        output_path: Optional[str] = None,
        total_duration_ms: Optional[int] = None,
    ) -> str:
        """
        合并多个音频分段（按时间轴，智能加速避免重叠）

        Args:
            segments: 分段列表，每个元素包含:
                - path: 音频文件路径
                - start_ms: 开始时间（毫秒）
                - end_ms: 结束时间（毫秒）（原始分段结束时间，仅供参考）
            output_path: 输出音频路径（可选）
            total_duration_ms: 目标总时长（可选，用于补齐/静音）

        Returns:
            输出音频文件路径

        策略：
            1. 按 start_ms 排序
            2. 计算每个分段的最大可用时长（到下一个分段开始或视频结束）
            3. 如果 TTS 音频超过可用时长，加速使其刚好填满
            4. 如果不超过，保持原样
        """
        if not segments:
            raise ValueError("No segments provided")

        if not output_path:
            output_path = tempfile.mktemp(suffix=".mp3")

        logger.info(f"Merging {len(segments)} audio segments -> {output_path}")

        if total_duration_ms is None:
            total_duration_ms = max(seg.get("end_ms", 0) for seg in segments)

        # 对分段按 start_ms 排序
        sorted_segments = sorted(segments, key=lambda x: x.get("start_ms", 0))

        # 计算每个分段的最大可用时长（到下一个分段开始）
        processed_segments = []
        for i, seg in enumerate(sorted_segments):
            start_ms = seg.get("start_ms", 0)

            # 下一个分段的开始时间，或者视频结束
            if i + 1 < len(sorted_segments):
                next_start_ms = sorted_segments[i + 1].get("start_ms", total_duration_ms)
            else:
                next_start_ms = total_duration_ms

            max_available_ms = next_start_ms - start_ms

            # 获取实际音频时长
            actual_duration_ms = self.get_audio_duration_ms(seg["path"])

            # 决定是否需要加速
            if actual_duration_ms > max_available_ms and max_available_ms > 0:
                # 需要加速
                speed_factor = actual_duration_ms / max_available_ms

                # 限制最大加速倍数（例如最大 4 倍，超过则截断或接受 4 倍后依然重叠?
                # 用户要求"尽量加速缩短"，所以这里优先满足时间约束）
                # FFmpeg atempo filter range is [0.5, 100]
                if speed_factor > 100.0:
                     speed_factor = 100.0

                adjusted_path = tempfile.mktemp(suffix=".wav")
                self.adjust_audio_speed(seg["path"], speed_factor, adjusted_path)
                processed_segments.append({
                    "path": adjusted_path,
                    "start_ms": start_ms,
                    "temp": True  # 标记为临时文件，后续清理
                })
                logger.info(f"Segment {i}: {actual_duration_ms}ms -> {max_available_ms}ms (speed up {speed_factor:.2f}x)")
            else:
                processed_segments.append({
                    "path": seg["path"],
                    "start_ms": start_ms,
                    "temp": False
                })
                logger.debug(f"Segment {i}: {actual_duration_ms}ms <= {max_available_ms}ms (no change)")

        # 构建 FFmpeg 滤镜
        filters = []
        inputs = []

        for i, seg in enumerate(processed_segments):
            inputs.extend(["-i", seg["path"]])
            delay_ms = seg["start_ms"]
            filters.append(
                f"[{i}:a]aresample=16000,adelay={delay_ms}|{delay_ms}[a{i}]"
            )

        # 基准静音轨道
        filters.append(
            f"anullsrc=channel_layout=mono:sample_rate=16000:d={total_duration_ms/1000}[base]"
        )

        # 混音（不会重叠，因为已经调整过时长）
        mix_inputs = "".join([f"[a{i}]" for i in range(len(processed_segments))])
        filters.append(
            f"[base]{mix_inputs}amix=inputs={len(processed_segments)+1}:normalize=0:dropout_transition=0[mixed]"
        )

        filter_complex = ";".join(filters)

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[mixed]",
            "-t", f"{total_duration_ms/1000}",
            output_path,
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f"Audio segments merged (timeline, smart speed): {output_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg merge failed: {e.stderr.decode()}")
            raise RuntimeError(f"Audio merge failed: {e.stderr.decode()}")
        finally:
            # 清理临时文件
            for seg in processed_segments:
                if seg.get("temp") and Path(seg["path"]).exists():
                    Path(seg["path"]).unlink(missing_ok=True)

        return output_path

    def replace_audio(
        self, video_path: str, audio_path: str, output_path: Optional[str] = None
    ) -> str:
        """
        替换视频的音轨

        Args:
            video_path: 原视频文件路径
            audio_path: 新音频文件路径
            output_path: 输出视频路径（可选）

        Returns:
            输出视频文件路径

        Raises:
            RuntimeError: FFmpeg 执行失败
        """
        if not output_path:
            output_path = str(
                Path(video_path).parent / f"{Path(video_path).stem}_dubbed.mp4"
            )

        logger.info(f"Replacing audio: video={video_path}, audio={audio_path}")

        cmd = [
            "ffmpeg",
            "-i",
            video_path,  # 输入视频
            "-i",
            audio_path,  # 输入音频
            "-c:v",
            "copy",  # 复制视频流（不重新编码）
            "-c:a",
            "aac",  # 音频编码为 AAC
            "-b:a",
            "192k",  # 音频比特率
            "-map",
            "0:v:0",  # 映射第一个输入的视频流
            "-map",
            "1:a:0",  # 映射第二个输入的音频流
            "-shortest",  # 使用最短流的长度
            "-y",
            output_path,
        ]

        try:
            subprocess.run(
                cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            logger.info(f"Audio replaced: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg replace failed: {e.stderr.decode()}")
            raise RuntimeError(f"Audio replacement failed: {e.stderr.decode()}")

    def adjust_audio_speed(
        self, audio_path: str, speed_factor: float, output_path: Optional[str] = None
    ) -> str:
        """
        调整音频速度（不改变音调）

        Args:
            audio_path: 输入音频路径
            speed_factor: 速度倍数（0.5 = 慢一半，2.0 = 快一倍）
            output_path: 输出音频路径（可选）

        Returns:
            输出音频文件路径

        Raises:
            RuntimeError: FFmpeg 执行失败
        """
        if not output_path:
            output_path = tempfile.mktemp(suffix=".mp3")

        logger.info(f"Adjusting audio speed: {speed_factor}x")

        cmd = [
            "ffmpeg",
            "-i",
            audio_path,
            "-filter:a",
            f"atempo={speed_factor}",  # 时间拉伸
            "-vn",
            "-y",
            output_path,
        ]

        try:
            subprocess.run(
                cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            logger.info(f"Audio speed adjusted: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg speed adjust failed: {e.stderr.decode()}")
            raise RuntimeError(f"Audio speed adjustment failed: {e.stderr.decode()}")

    def extract_segment(
        self,
        media_path: str,
        start_ms: int,
        end_ms: int,
        output_path: Optional[str] = None,
    ) -> str:
        """
        提取媒体片段

        Args:
            media_path: 媒体文件路径
            start_ms: 开始时间（毫秒）
            end_ms: 结束时间（毫秒）
            output_path: 输出文件路径（可选）

        Returns:
            输出文件路径

        Raises:
            RuntimeError: FFmpeg 执行失败
        """
        if not output_path:
            suffix = Path(media_path).suffix
            output_path = tempfile.mktemp(suffix=suffix)

        start_sec = start_ms / 1000
        duration_sec = (end_ms - start_ms) / 1000

        cmd = [
            "ffmpeg",
            "-ss",
            str(start_sec),
            "-i",
            media_path,
            "-t",
            str(duration_sec),
            "-c",
            "copy",  # 复制编码（快速）
            "-y",
            output_path,
        ]

        try:
            subprocess.run(
                cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            logger.info(
                f"Extracted segment: {start_ms}-{end_ms}ms -> {output_path}"
            )
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg extract failed: {e.stderr.decode()}")
            raise RuntimeError(f"Segment extraction failed: {e.stderr.decode()}")
