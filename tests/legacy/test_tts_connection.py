#!/usr/bin/env python3
"""
专门测试 TTS 服务连接的脚本
"""

import urllib.request
import urllib.error
import json
import time

def test_tts_connection(tts_url="https://u861448-ej47-562de107.bjb2.seetacloud.com:8443"):
    """测试 TTS 服务连接"""
    print(f"🧪 测试 TTS 服务: {tts_url}")

    # 测试端点列表 (按优先级排序)
    test_endpoints = [
        ("/gradio_api/info", "Gradio API 信息", True),    # 期望 JSON
        ("/health", "健康检查", True),                     # 期望 JSON
        ("/api/health", "API 健康检查", True),             # 期望 JSON
        ("/docs", "API 文档", False),                      # 期望 HTML
        ("/", "主页", False)                               # 期望 HTML
    ]

    for endpoint, description, expect_json in test_endpoints:
        test_url = tts_url + endpoint
        print(f"\n📡 测试端点: {test_url}")

        try:
            start_time = time.time()
            req = urllib.request.Request(test_url)
            req.add_header('User-Agent', 'TTS-Connection-Test/1.0')

            with urllib.request.urlopen(req, timeout=10) as response:
                latency_ms = int((time.time() - start_time) * 1000)
                content_type = response.headers.get('Content-Type', '')
                status = response.status

                print(f"  ✅ 状态: {status}")
                print(f"  📄 内容类型: {content_type}")
                print(f"  ⏱️  延迟: {latency_ms}ms")

                # 读取响应内容
                content = response.read().decode('utf-8', errors='ignore')
                content_preview = content[:300] + "..." if len(content) > 300 else content

                # 分析响应
                if expect_json and 'application/json' in content_type:
                    try:
                        data = json.loads(content)
                        print(f"  ✅ JSON 解析成功")

                        if endpoint == "/gradio_api/info":
                            if 'named_endpoints' in data:
                                print(f"  🎯 检测到 Gradio IndexTTS 服务")
                                endpoints = list(data.get('named_endpoints', {}).keys())
                                print(f"  📋 可用端点: {len(endpoints)} 个")
                                if '/gen_single' in endpoints:
                                    print(f"  🎤 语音合成端点可用: /gen_single")
                                return {
                                    "status": "connected",
                                    "message": f"Gradio IndexTTS 服务连接成功 - 检测到 {len(endpoints)} 个API端点",
                                    "latency_ms": latency_ms,
                                    "service_type": "gradio_indextts",
                                    "endpoints": endpoints[:5]  # 只显示前5个
                                }
                        else:
                            print(f"  📝 JSON 内容预览: {json.dumps(data, ensure_ascii=False)[:100]}...")
                            return {
                                "status": "connected",
                                "message": f"TTS API 服务连接成功 ({description})",
                                "latency_ms": latency_ms,
                                "service_type": "api"
                            }
                    except json.JSONDecodeError as e:
                        print(f"  ❌ JSON 解析失败: {e}")
                        if expect_json:
                            continue  # 如果期望 JSON 但解析失败，尝试下一个端点

                # HTML 响应处理
                if 'text/html' in content_type:
                    content_lower = content.lower()
                    if 'gradio' in content_lower:
                        print(f"  🎯 检测到 Gradio Web 界面")
                        return {
                            "status": "connected",
                            "message": "TTS 服务连接成功 - Gradio Web 界面可访问",
                            "latency_ms": latency_ms,
                            "service_type": "gradio_web"
                        }
                    else:
                        print(f"  📄 HTML 响应")
                        return {
                            "status": "connected",
                            "message": f"TTS Web 服务连接成功 ({description})",
                            "latency_ms": latency_ms,
                            "service_type": "web"
                        }

                # 其他成功响应
                print(f"  📝 响应预览: {content_preview}")
                return {
                    "status": "connected",
                    "message": f"TTS 服务响应正常 ({description})",
                    "latency_ms": latency_ms,
                    "service_type": "other"
                }

        except urllib.error.HTTPError as e:
            print(f"  ❌ HTTP 错误: {e.code} - {e.reason}")
            if e.code == 404:
                continue  # 404 继续尝试下一个端点
            else:
                return {
                    "status": "failed",
                    "message": f"HTTP 错误 {e.code}: {e.reason}"
                }
        except urllib.error.URLError as e:
            print(f"  ❌ URL 错误: {e.reason}")
            return {
                "status": "failed",
                "message": f"连接失败: {e.reason}"
            }
        except Exception as e:
            print(f"  ❌ 其他错误: {e}")
            continue

    return {
        "status": "failed",
        "message": "所有端点均无法访问"
    }

if __name__ == "__main__":
    result = test_tts_connection()
    print(f"\n🎯 最终结果:")
    print(f"状态: {result['status']}")
    print(f"消息: {result['message']}")
    if 'latency_ms' in result:
        print(f"延迟: {result['latency_ms']}ms")
    if 'service_type' in result:
        print(f"服务类型: {result['service_type']}")
    if 'endpoints' in result:
        print(f"API 端点: {', '.join(result['endpoints'])}")