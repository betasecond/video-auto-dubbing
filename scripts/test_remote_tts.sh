#!/bin/bash
# 测试远程 IndexTTS v2 API 的可用性

BASE_URL="${BASE_URL:-https://u861448-ej47-562de107.bjb2.seetacloud.com:8443}"

# 跳过 SSL 证书验证（使用 -k 参数）
CURL_OPTS="-k"

echo "========================================="
echo "测试 IndexTTS v2 /tts_url 端点"
echo "Base URL: $BASE_URL"
echo "========================================="
echo ""

# Test 1: Health check
echo "[Test 1/3] Health Check ..."
HTTP_CODE=$(curl $CURL_OPTS -s -o /tmp/health.json -w "%{http_code}" "$BASE_URL/health")
echo "HTTP Status: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Health check passed"
    cat /tmp/health.json | python3 -m json.tool 2>/dev/null || cat /tmp/health.json
else
    echo "✗ Health check failed"
fi
echo ""
echo ""

# Test 2: Check endpoint availability
echo "[Test 2/3] 检查 /tts_url 端点 ..."
HTTP_CODE=$(curl $CURL_OPTS -s -o /dev/null -w "%{http_code}" -X HEAD "$BASE_URL/tts_url")
echo "HTTP Status: $HTTP_CODE"
if [ "$HTTP_CODE" = "405" ]; then
    echo "✓ 端点存在（405 = Method Not Allowed on HEAD，需要 POST）"
elif [ "$HTTP_CODE" = "404" ]; then
    echo "✗ 端点不存在（404）"
else
    echo "? 未知状态（$HTTP_CODE）"
fi
echo ""
echo ""

# Test 3: 实际 TTS 合成（使用服务器上存在的参考音频）
echo "[Test 3/3] 测试 TTS 合成 ..."

# 测试中文
echo "测试 1: 中文文本 ..."
curl $CURL_OPTS -sS -D /tmp/tts_zh_headers.txt \
  -H 'Content-Type: application/json' \
  -o /tmp/tts_zh.wav \
  "$BASE_URL/tts_url" \
  --data-raw '{
    "text": "你好，这是一个测试。今天天气真不错。",
    "spk_audio_path": "/root/index-tts-vllm/examples/voice_01.wav"
  }'

HTTP_CODE=$(head -1 /tmp/tts_zh_headers.txt | awk '{print $2}')
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    CONTENT_TYPE=$(grep -i "content-type" /tmp/tts_zh_headers.txt | cut -d: -f2 | tr -d ' \r\n')
    echo "Content-Type: $CONTENT_TYPE"

    if [ -f /tmp/tts_zh.wav ]; then
        FILE_TYPE=$(file /tmp/tts_zh.wav)
        FILE_SIZE=$(ls -lh /tmp/tts_zh.wav | awk '{print $5}')
        echo "File Type: $FILE_TYPE"
        echo "File Size: $FILE_SIZE"

        if echo "$FILE_TYPE" | grep -q "RIFF.*WAVE"; then
            echo "✓ TTS 合成成功！生成了有效的 WAV 文件"
        else
            echo "✗ 响应不是有效的音频文件"
            echo "前 100 字节："
            head -c 100 /tmp/tts_zh.wav | hexdump -C
        fi
    fi
else
    echo "✗ TTS 合成失败"
    echo "响应内容："
    cat /tmp/tts_zh.wav | python3 -m json.tool 2>/dev/null || cat /tmp/tts_zh.wav
fi

echo ""
echo ""

# 测试英文
echo "测试 2: 英文文本 ..."
curl $CURL_OPTS -sS -D /tmp/tts_en_headers.txt \
  -H 'Content-Type: application/json' \
  -o /tmp/tts_en.wav \
  "$BASE_URL/tts_url" \
  --data-raw '{
    "text": "Hello, this is a test. The weather is nice today.",
    "spk_audio_path": "/root/index-tts-vllm/examples/voice_02.wav"
  }'

HTTP_CODE=$(head -1 /tmp/tts_en_headers.txt | awk '{print $2}')
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ] && [ -f /tmp/tts_en.wav ]; then
    FILE_TYPE=$(file /tmp/tts_en.wav)
    FILE_SIZE=$(ls -lh /tmp/tts_en.wav | awk '{print $5}')
    echo "File Type: $FILE_TYPE"
    echo "File Size: $FILE_SIZE"

    if echo "$FILE_TYPE" | grep -q "RIFF.*WAVE"; then
        echo "✓ 英文 TTS 合成成功！"
    else
        echo "✗ 响应不是有效的音频文件"
    fi
fi

echo ""
echo ""

# Summary
echo "========================================="
echo "测试完成！"
echo ""
echo "生成的音频文件："
echo "  - /tmp/tts_zh.wav (中文)"
echo "  - /tmp/tts_en.wav (英文)"
echo ""
echo "播放测试（macOS）："
echo "  afplay /tmp/tts_zh.wav"
echo "  afplay /tmp/tts_en.wav"
echo ""
echo "播放测试（Linux）："
echo "  aplay /tmp/tts_zh.wav"
echo "  aplay /tmp/tts_en.wav"
echo "========================================="
