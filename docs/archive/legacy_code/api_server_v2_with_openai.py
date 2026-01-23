import os
import asyncio
import io
import traceback
from fastapi import FastAPI, Request, Response, File, UploadFile, Form
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import argparse
import json
import time
import soundfile as sf
from typing import List, Optional, Union
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

from loguru import logger
logger.add("logs/api_server_v2.log", rotation="10 MB", retention=10, level="DEBUG", enqueue=True)

from indextts.infer_vllm_v2 import IndexTTS2

tts = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tts
    tts = IndexTTS2(
        model_dir=args.model_dir,
        is_fp16=args.is_fp16,
        gpu_memory_utilization=args.gpu_memory_utilization,
        qwenemo_gpu_memory_utilization=args.qwenemo_gpu_memory_utilization,
    )
    yield


app = FastAPI(lifespan=lifespan)

# Add CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, change in production for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if tts is None:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": "TTS model not initialized"
            }
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "message": "Service is running",
            "timestamp": time.time()
        }
    )


@app.post("/tts_url", responses={
    200: {"content": {"application/octet-stream": {}}},
    500: {"content": {"application/json": {}}}
})
async def tts_api_url(request: Request):
    try:
        data = await request.json()
        emo_control_method = data.get("emo_control_method", 0)
        text = data["text"]
        spk_audio_path = data["spk_audio_path"]
        emo_ref_path = data.get("emo_ref_path", None)
        emo_weight = data.get("emo_weight", 1.0)
        emo_vec = data.get("emo_vec", [0] * 8)
        emo_text = data.get("emo_text", None)
        emo_random = data.get("emo_random", False)
        max_text_tokens_per_sentence = data.get("max_text_tokens_per_sentence", 120)

        global tts
        if type(emo_control_method) is not int:
            emo_control_method = emo_control_method.value
        if emo_control_method == 0:
            emo_ref_path = None
            emo_weight = 1.0
        if emo_control_method == 1:
            emo_weight = emo_weight
        if emo_control_method == 2:
            vec = emo_vec
            vec_sum = sum(vec)
            if vec_sum > 1.5:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "error": "情感向量之和不能超过1.5，请调整后重试。"
                    }
                )
        else:
            vec = None

        # logger.info(f"Emo control mode:{emo_control_method}, vec:{vec}")
        sr, wav = await tts.infer(spk_audio_prompt=spk_audio_path, text=text,
                        output_path=None,
                        emo_audio_prompt=emo_ref_path, emo_alpha=emo_weight,
                        emo_vector=vec,
                        use_emo_text=(emo_control_method==3), emo_text=emo_text,use_random=emo_random,
                        max_text_tokens_per_sentence=int(max_text_tokens_per_sentence))

        with io.BytesIO() as wav_buffer:
            sf.write(wav_buffer, wav, sr, format='WAV')
            wav_bytes = wav_buffer.getvalue()

        return Response(content=wav_bytes, media_type="audio/wav")

    except Exception as ex:
        tb_str = ''.join(traceback.format_exception(type(ex), ex, ex.__traceback__))
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(tb_str)
            }
        )


# ============================================
# OpenAI Compatible API
# ============================================

class OpenAISpeechRequest(BaseModel):
    """OpenAI compatible speech request model"""
    model: str
    input: str
    voice: str = "alloy"
    response_format: str = "wav"
    speed: float = 1.0


# 默认 voice 到参考音频文件的映射
DEFAULT_VOICE_MAPPING = {
    "alloy": "/root/index-tts-vllm/examples/voice_01.wav",
    "echo": "/root/index-tts-vllm/examples/voice_02.wav",
    "fable": "/root/index-tts-vllm/examples/voice_03.wav",
    "onyx": "/root/index-tts-vllm/examples/voice_04.wav",
    "nova": "/root/index-tts-vllm/examples/voice_05.wav",
    "shimmer": "/root/index-tts-vllm/examples/voice_06.wav",
    "ash": "/root/index-tts-vllm/examples/voice_07.wav",
    "ballad": "/root/index-tts-vllm/examples/voice_08.wav",
    "coral": "/root/index-tts-vllm/examples/voice_09.wav",
    "sage": "/root/index-tts-vllm/examples/voice_10.wav",
    "verse": "/root/index-tts-vllm/examples/voice_11.wav",
    "default": "/root/index-tts-vllm/examples/voice_01.wav",
}


@app.post("/v1/audio/speech")
async def openai_speech_api(request: OpenAISpeechRequest):
    """
    OpenAI compatible TTS endpoint

    Request:
    {
      "model": "tts-1",
      "input": "Hello world",
      "voice": "alloy",
      "response_format": "wav",
      "speed": 1.0
    }
    """
    try:
        text = request.input
        voice = request.voice
        speed = request.speed
        response_format = request.response_format

        # 参数验证
        if not text or len(text.strip()) == 0:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "Input text is required"}
            )

        if len(text) > 4096:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "Input text exceeds 4096 characters"}
            )

        # 映射 voice
        spk_audio_path = DEFAULT_VOICE_MAPPING.get(voice, DEFAULT_VOICE_MAPPING["default"])

        logger.info(f"OpenAI API: voice={voice}, len={len(text)}, speed={speed}")

        # TTS 推理
        global tts
        sr, wav = await tts.infer(
            spk_audio_prompt=spk_audio_path,
            text=text,
            output_path=None,
            emo_audio_prompt=None,
            emo_alpha=1.0,
            emo_vector=None,
            use_emo_text=False,
            emo_text=None,
            use_random=False,
            max_text_tokens_per_sentence=120
        )

        # 生成音频
        with io.BytesIO() as audio_buffer:
            if response_format in ["wav", "pcm"]:
                sf.write(audio_buffer, wav, sr, format='WAV')
                media_type = "audio/wav"
            elif response_format == "mp3":
                logger.warning("MP3 not implemented, returning WAV")
                sf.write(audio_buffer, wav, sr, format='WAV')
                media_type = "audio/wav"
            else:
                sf.write(audio_buffer, wav, sr, format='WAV')
                media_type = "audio/wav"

            audio_bytes = audio_buffer.getvalue()

        logger.info(f"OpenAI API success: {len(audio_bytes)} bytes")

        return Response(
            content=audio_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="speech.{response_format}"',
            }
        )

    except Exception as ex:
        tb_str = ''.join(traceback.format_exception(type(ex), ex, ex.__traceback__))
        logger.error(f"OpenAI API error: {tb_str}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(tb_str)}
        )


@app.get("/v1/audio/voices")
async def list_voices():
    """List available voices"""
    voices = [
        {"id": vid, "name": vid.capitalize(), "language": "multi"}
        for vid in DEFAULT_VOICE_MAPPING.keys()
        if vid != "default"
    ]
    return JSONResponse(status_code=200, content={"voices": voices})


# ============================================
# Main Entry Point
# ============================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=6006)
    parser.add_argument("--model_dir", type=str, default="checkpoints/IndexTTS-2-vLLM", help="Model checkpoints directory")
    parser.add_argument("--is_fp16", action="store_true", default=False, help="Fp16 infer")
    parser.add_argument("--gpu_memory_utilization", type=float, default=0.25)
    parser.add_argument("--qwenemo_gpu_memory_utilization", type=float, default=0.10)
    parser.add_argument("--verbose", action="store_true", default=False, help="Enable verbose mode")
    args = parser.parse_args()

    if not os.path.exists("outputs"):
        os.makedirs("outputs")

    uvicorn.run(app=app, host=args.host, port=args.port)
