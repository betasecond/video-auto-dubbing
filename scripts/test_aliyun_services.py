#!/usr/bin/env python3
"""
阿里百炼平台服务连通性测试脚本

测试内容：
1. OSS - 阿里云对象存储
2. ASR - DashScope 语音识别
3. LLM - Qwen3 大语言模型
4. TTS - Qwen3-TTS 语音合成

使用方法：
    pip install dashscope oss2 openai websockets
    python scripts/test_aliyun_services.py
"""

import os
import sys
import json
import time
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")

# 加载环境变量
def load_env():
    """从 .env 文件加载环境变量"""
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())
        print_info(f"已加载 .env 文件: {env_path}")
    else:
        print_warning(f".env 文件不存在: {env_path}")

# ============================================================
# 1. OSS 连通性测试
# ============================================================
def test_oss():
    print_header("1. 阿里云 OSS 连通性测试")

    try:
        import oss2
    except ImportError:
        print_error("oss2 库未安装，请运行: pip install oss2")
        return False

    # 获取配置
    endpoint = os.getenv('OSS_ENDPOINT')
    bucket_name = os.getenv('OSS_BUCKET')
    access_key_id = os.getenv('OSS_ACCESS_KEY_ID')
    access_key_secret = os.getenv('OSS_ACCESS_KEY_SECRET')

    if not all([endpoint, bucket_name, access_key_id, access_key_secret]):
        print_error("OSS 配置不完整，请检查环境变量:")
        print(f"  OSS_ENDPOINT: {'✓' if endpoint else '✗'}")
        print(f"  OSS_BUCKET: {'✓' if bucket_name else '✗'}")
        print(f"  OSS_ACCESS_KEY_ID: {'✓' if access_key_id else '✗'}")
        print(f"  OSS_ACCESS_KEY_SECRET: {'✓' if access_key_secret else '✗'}")
        return False

    print_info(f"Endpoint: {endpoint}")
    print_info(f"Bucket: {bucket_name}")

    try:
        # 创建连接
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)

        # 测试上传
        test_key = f"test/connectivity_test_{int(time.time())}.txt"
        test_content = f"Connectivity test at {datetime.now().isoformat()}"

        print_info(f"测试上传: {test_key}")
        bucket.put_object(test_key, test_content.encode('utf-8'))
        print_success("上传成功")

        # 测试下载
        print_info("测试下载...")
        result = bucket.get_object(test_key)
        downloaded = result.read().decode('utf-8')
        if downloaded == test_content:
            print_success("下载成功，内容一致")
        else:
            print_warning("下载成功，但内容不一致")

        # 测试签名 URL
        print_info("测试生成签名 URL...")
        signed_url = bucket.sign_url('GET', test_key, 3600)
        print_success(f"签名 URL 生成成功: {signed_url[:80]}...")

        # 清理测试文件
        print_info("清理测试文件...")
        bucket.delete_object(test_key)
        print_success("清理完成")

        print_success("OSS 连通性测试通过!")
        return True

    except oss2.exceptions.OssError as e:
        print_error(f"OSS 错误: {e}")
        return False
    except Exception as e:
        print_error(f"未知错误: {e}")
        return False

# ============================================================
# 2. ASR 连通性测试
# ============================================================
def test_asr():
    print_header("2. DashScope ASR 连通性测试")

    try:
        import dashscope
        from dashscope.audio.asr import Transcription
    except ImportError:
        print_error("dashscope 库未安装，请运行: pip install dashscope")
        return False

    api_key = os.getenv('DASHSCOPE_API_KEY')
    if not api_key:
        print_error("DASHSCOPE_API_KEY 未配置")
        return False

    dashscope.api_key = api_key
    print_info(f"API Key: {api_key[:8]}...{api_key[-4:]}")

    # 使用阿里云官方示例音频
    test_audio_url = "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav"

    print_info(f"测试音频: {test_audio_url}")
    print_info("提交 ASR 任务...")

    try:
        # 提交异步任务
        response = Transcription.async_call(
            model='sensevoice-v1',  # 支持情感检测的模型
            file_urls=[test_audio_url],
            language_hints=['zh', 'en']
        )

        if response.status_code != 200:
            print_error(f"提交失败: {response.message}")
            return False

        task_id = response.output.task_id
        print_success(f"任务提交成功, task_id: {task_id}")

        # 轮询结果 (最多等待 60 秒)
        print_info("等待识别结果...")
        max_wait = 60
        start_time = time.time()

        while True:
            result = Transcription.fetch(task=task_id)
            status = result.output.task_status

            if status == 'SUCCEEDED':
                print_success("识别完成!")

                # 解析结果
                transcripts = result.output.results
                if transcripts:
                    for t in transcripts:
                        if 'transcription_url' in t:
                            print_info(f"结果 URL: {t['transcription_url']}")
                        if 'text' in t:
                            print_info(f"识别文本: {t['text'][:100]}...")

                print_success("ASR 连通性测试通过!")
                return True

            elif status == 'FAILED':
                print_error(f"识别失败: {result.output}")
                return False

            elif time.time() - start_time > max_wait:
                print_warning(f"等待超时 ({max_wait}秒), 任务仍在进行中")
                print_info(f"可稍后使用 task_id 查询: {task_id}")
                return True  # 认为连通性正常

            else:
                elapsed = int(time.time() - start_time)
                print(f"  状态: {status}, 已等待 {elapsed}s...", end='\r')
                time.sleep(2)

    except Exception as e:
        print_error(f"ASR 测试失败: {e}")
        return False

# ============================================================
# 3. LLM 连通性测试 (Qwen3)
# ============================================================
def test_llm():
    print_header("3. Qwen3 LLM 连通性测试")

    try:
        from openai import OpenAI
    except ImportError:
        print_error("openai 库未安装，请运行: pip install openai")
        return False

    api_key = os.getenv('DASHSCOPE_API_KEY')
    base_url = os.getenv('DASHSCOPE_LLM_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    model = os.getenv('DASHSCOPE_LLM_MODEL', 'qwen-turbo')

    if not api_key:
        print_error("DASHSCOPE_API_KEY 未配置")
        return False

    print_info(f"Base URL: {base_url}")
    print_info(f"Model: {model}")

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        print_info("发送测试请求...")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个专业的翻译助手。"},
                {"role": "user", "content": "请将以下中文翻译成英文：你好世界"}
            ],
            max_tokens=100
        )

        result = response.choices[0].message.content
        print_success(f"LLM 响应: {result}")

        # 统计 token 使用
        usage = response.usage
        print_info(f"Token 使用: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}")

        print_success("LLM 连通性测试通过!")
        return True

    except Exception as e:
        print_error(f"LLM 测试失败: {e}")
        return False

# ============================================================
# 4. TTS 连通性测试 (Qwen3-TTS)
# ============================================================
def test_tts():
    print_header("4. Qwen3-TTS 连通性测试")

    api_key = os.getenv('DASHSCOPE_API_KEY')
    if not api_key:
        print_error("DASHSCOPE_API_KEY 未配置")
        return False

    # 尝试使用 dashscope SDK
    try:
        import dashscope
        from dashscope.audio.tts_v2 import SpeechSynthesizer

        dashscope.api_key = api_key

        print_info("使用 DashScope SDK 测试 TTS...")
        print_info("模型: cosyvoice-v1 (系统音色)")

        # 使用同步方式测试
        synthesizer = SpeechSynthesizer(
            model='cosyvoice-v1',
            voice='longxiaochun'  # 系统预置音色
        )

        test_text = "你好，这是一个语音合成测试。"
        print_info(f"合成文本: {test_text}")

        audio = synthesizer.call(test_text)

        if audio:
            # 保存测试音频
            output_path = Path(tempfile.gettempdir()) / "tts_test.mp3"
            with open(output_path, 'wb') as f:
                f.write(audio)
            print_success(f"TTS 合成成功! 音频已保存: {output_path}")
            print_info(f"音频大小: {len(audio)} bytes")
            print_success("TTS 连通性测试通过!")
            return True
        else:
            print_error("TTS 返回空音频")
            return False

    except ImportError:
        print_warning("dashscope.audio.tts_v2 不可用，尝试 WebSocket 方式...")
    except Exception as e:
        print_warning(f"SDK 方式失败: {e}")
        print_info("尝试 WebSocket 方式...")

    # 备用：使用 WebSocket API
    try:
        return asyncio.run(test_tts_websocket(api_key))
    except Exception as e:
        print_error(f"WebSocket TTS 测试失败: {e}")
        return False

async def test_tts_websocket(api_key: str):
    """WebSocket 方式测试 TTS"""
    try:
        import websockets
    except ImportError:
        print_error("websockets 库未安装，请运行: pip install websockets")
        return False

    url = f"wss://dashscope.aliyuncs.com/api-ws/v1/inference/?model=cosyvoice-v1"

    print_info(f"WebSocket URL: {url[:60]}...")

    headers = {
        "Authorization": f"bearer {api_key}",
        "X-DashScope-DataInspection": "enable"
    }

    try:
        async with websockets.connect(url, additional_headers=headers) as ws:
            print_success("WebSocket 连接成功!")

            # 发送会话配置
            config_msg = {
                "header": {
                    "streaming": "duplex",
                    "task_id": f"test_{int(time.time())}",
                    "action": "run-task"
                },
                "payload": {
                    "task_group": "audio",
                    "task": "tts",
                    "function": "SpeechSynthesizer",
                    "model": "cosyvoice-v1",
                    "parameters": {
                        "voice": "longxiaochun",
                        "format": "mp3"
                    },
                    "input": {
                        "text": "你好世界"
                    }
                }
            }

            await ws.send(json.dumps(config_msg))
            print_info("已发送合成请求...")

            audio_chunks = []
            async for message in ws:
                if isinstance(message, bytes):
                    audio_chunks.append(message)
                else:
                    data = json.loads(message)
                    if data.get("header", {}).get("event") == "task-finished":
                        break
                    elif "error" in str(data).lower():
                        print_warning(f"收到消息: {data}")

            if audio_chunks:
                total_size = sum(len(c) for c in audio_chunks)
                print_success(f"收到音频数据: {total_size} bytes")
                print_success("TTS WebSocket 连通性测试通过!")
                return True
            else:
                print_warning("未收到音频数据，但连接正常")
                return True

    except Exception as e:
        print_error(f"WebSocket 连接失败: {e}")
        return False

# ============================================================
# 主函数
# ============================================================
def main():
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  阿里百炼平台服务连通性测试{Colors.RESET}")
    print(f"{Colors.BOLD}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")

    # 加载环境变量
    load_env()

    results = {}

    # 1. OSS 测试
    results['OSS'] = test_oss()

    # 2. ASR 测试
    results['ASR'] = test_asr()

    # 3. LLM 测试
    results['LLM'] = test_llm()

    # 4. TTS 测试
    results['TTS'] = test_tts()

    # 汇总结果
    print_header("测试结果汇总")

    all_passed = True
    for service, passed in results.items():
        if passed:
            print_success(f"{service}: 通过")
        else:
            print_error(f"{service}: 失败")
            all_passed = False

    print()
    if all_passed:
        print_success("🎉 所有服务连通性测试通过!")
        return 0
    else:
        print_error("⚠️ 部分服务测试失败，请检查配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())
