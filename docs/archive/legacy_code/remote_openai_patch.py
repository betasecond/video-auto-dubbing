"""
OpenAI Compatible TTS API Patch for api_server_v2.py
将此代码添加到现有的 api_server_v2.py 中
"""

# ============================================
# 在文件开头的 import 区域添加以下导入
# ============================================
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from typing import Optional

# ============================================
# 在 tts_api_url 函数之后，if __name__ == "__main__" 之前添加以下代码
# ============================================

class OpenAISpeechRequest(BaseModel):
    """OpenAI compatible speech request model"""
    model: str
    input: str
    voice: str = "alloy"
    response_format: str = "wav"
    speed: float = 1.0


# 默认 voice 到参考音频文件的映射
# 使用远程服务器上已有的 voice_*.wav 文件
DEFAULT_VOICE_MAPPING = {
    "alloy": "/root/index-tts-vllm/examples/voice_01.wav",      # 默认男声
    "echo": "/root/index-tts-vllm/examples/voice_02.wav",       # 回声效果
    "fable": "/root/index-tts-vllm/examples/voice_03.wav",      # 叙事风格
    "onyx": "/root/index-tts-vllm/examples/voice_04.wav",       # 深沉男声
    "nova": "/root/index-tts-vllm/examples/voice_05.wav",       # 活泼女声
    "shimmer": "/root/index-tts-vllm/examples/voice_06.wav",    # 柔和女声
    "ash": "/root/index-tts-vllm/examples/voice_07.wav",        # 中性音色
    "ballad": "/root/index-tts-vllm/examples/voice_08.wav",     # 歌谣风格
    "coral": "/root/index-tts-vllm/examples/voice_09.wav",      # 珊瑚音色
    "sage": "/root/index-tts-vllm/examples/voice_10.wav",       # 智者音色
    "verse": "/root/index-tts-vllm/examples/voice_11.wav",      # 诗歌风格
    "default": "/root/index-tts-vllm/examples/voice_01.wav",    # 默认回退
}


@app.post("/v1/audio/speech")
async def openai_speech_api(request: OpenAISpeechRequest):
    """
    OpenAI compatible TTS endpoint

    Request body:
    {
      "model": "tts-1",
      "input": "Hello world",
      "voice": "alloy",
      "response_format": "wav",
      "speed": 1.0
    }

    Returns: Audio stream (WAV format by default)
    """
    try:
        # 1. 提取参数
        text = request.input
        voice = request.voice
        speed = request.speed
        response_format = request.response_format

        # 参数验证
        if not text or len(text.strip()) == 0:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "error": "Input text is required and cannot be empty"
                }
            )

        if len(text) > 4096:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "error": "Input text exceeds maximum length of 4096 characters"
                }
            )

        # 2. 映射 voice 到 spk_audio_path
        spk_audio_path = DEFAULT_VOICE_MAPPING.get(voice, DEFAULT_VOICE_MAPPING["default"])

        logger.info(f"OpenAI Speech API request: voice={voice}, text_len={len(text)}, speed={speed}, format={response_format}")

        # 3. 调用现有的 TTS 推理逻辑
        global tts
        sr, wav = await tts.infer(
            spk_audio_prompt=spk_audio_path,
            text=text,
            output_path=None,
            emo_audio_prompt=None,  # 不使用情感控制
            emo_alpha=1.0,
            emo_vector=None,
            use_emo_text=False,
            emo_text=None,
            use_random=False,
            max_text_tokens_per_sentence=120
        )

        # 4. 根据 response_format 生成音频
        # 注意: IndexTTS 默认输出 WAV，如果需要 MP3/OPUS 需要额外转换
        with io.BytesIO() as audio_buffer:
            if response_format in ["wav", "pcm"]:
                sf.write(audio_buffer, wav, sr, format='WAV')
                media_type = "audio/wav"
            elif response_format == "mp3":
                # MP3 需要额外的编码库，这里先返回 WAV
                logger.warning("MP3 format requested but not implemented, returning WAV")
                sf.write(audio_buffer, wav, sr, format='WAV')
                media_type = "audio/wav"
            else:
                # 默认 WAV
                sf.write(audio_buffer, wav, sr, format='WAV')
                media_type = "audio/wav"

            audio_bytes = audio_buffer.getvalue()

        logger.info(f"OpenAI Speech API success: audio_size={len(audio_bytes)} bytes")

        # 5. 返回音频流
        return Response(
            content=audio_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="speech.{response_format}"',
                "X-Audio-Duration-Ms": str(int(len(wav) / sr * 1000)),
            }
        )

    except Exception as ex:
        tb_str = ''.join(traceback.format_exception(type(ex), ex, ex.__traceback__))
        logger.error(f"OpenAI Speech API error: {tb_str}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(tb_str)
            }
        )


@app.get("/v1/audio/voices")
async def list_voices():
    """
    List available voices (OpenAI compatible)
    """
    voices = [
        {"id": voice_id, "name": voice_id.capitalize(), "language": "multi"}
        for voice_id in DEFAULT_VOICE_MAPPING.keys()
        if voice_id != "default"
    ]

    return JSONResponse(
        status_code=200,
        content={
            "voices": voices
        }
    )
