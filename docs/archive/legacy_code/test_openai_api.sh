#!/bin/bash
# OpenAI 兼容 API 测试脚本
# 可以在本地执行，测试远程服务

BASE_URL="${BASE_URL:-https://u861448-ej47-562de107.bjb2.seetacloud.com:8443}"

echo "========================================="
echo "测试 IndexTTS OpenAI 兼容 API"
echo "Base URL: $BASE_URL"
echo "========================================="
echo ""

# Test 1: Health check
echo "[Test 1/4] Health Check ..."
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""
echo ""

# Test 2: List voices
echo "[Test 2/4] List Available Voices ..."
curl -s "$BASE_URL/v1/audio/voices" | python3 -m json.tool
echo ""
echo ""

# Test 3: OpenAI Speech API (English)
echo "[Test 3/4] OpenAI Speech API - English ..."
curl -sS -D /tmp/openai_test_en_headers.txt \
  -H 'Content-Type: application/json' \
  -H 'Accept: audio/wav' \
  -o /tmp/openai_test_en.wav \
  "$BASE_URL/v1/audio/speech" \
  --data-raw '{
    "model": "tts-1",
    "input": "Hello, this is a test of the OpenAI compatible TTS API.",
    "voice": "alloy",
    "response_format": "wav",
    "speed": 1.0
  }'

echo "Response Headers:"
head -10 /tmp/openai_test_en_headers.txt
echo ""
echo "File Info:"
file /tmp/openai_test_en.wav
ls -lh /tmp/openai_test_en.wav
echo ""
echo ""

# Test 4: OpenAI Speech API (Chinese)
echo "[Test 4/4] OpenAI Speech API - Chinese ..."
curl -sS -D /tmp/openai_test_zh_headers.txt \
  -H 'Content-Type: application/json' \
  -H 'Accept: audio/wav' \
  -o /tmp/openai_test_zh.wav \
  "$BASE_URL/v1/audio/speech" \
  --data-raw '{
    "model": "tts-1",
    "input": "你好，这是一个测试。今天天气真不错。",
    "voice": "nova",
    "response_format": "wav",
    "speed": 1.0
  }'

echo "Response Headers:"
head -10 /tmp/openai_test_zh_headers.txt
echo ""
echo "File Info:"
file /tmp/openai_test_zh.wav
ls -lh /tmp/openai_test_zh.wav
echo ""
echo ""

# Summary
echo "========================================="
echo "测试完成！"
echo ""
echo "生成的音频文件："
echo "  - /tmp/openai_test_en.wav (English)"
echo "  - /tmp/openai_test_zh.wav (Chinese)"
echo ""
echo "播放测试（如果系统支持）："
echo "  afplay /tmp/openai_test_en.wav  # macOS"
echo "  aplay /tmp/openai_test_en.wav   # Linux"
echo "========================================="
