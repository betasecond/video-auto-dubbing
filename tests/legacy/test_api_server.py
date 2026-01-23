#!/usr/bin/env python3
"""
简单的测试 API 服务器，用于测试前端设置页面
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import time

class TestAPIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """处理跨域 OPTIONS 请求"""
        self.send_cors_headers()

    def do_GET(self):
        """处理 GET 请求"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/v1/settings':
            self.handle_get_settings()
        else:
            self.send_error(404, "Not Found")

    def do_PUT(self):
        """处理 PUT 请求"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/v1/settings':
            self.handle_update_settings()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """处理 POST 请求"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/v1/settings/test':
            self.handle_test_connection()
        else:
            self.send_error(404, "Not Found")

    def handle_get_settings(self):
        """返回当前设置（模拟数据）"""
        settings = {
            "asr": {
                "volcengine_app_key": "608***513",  # 已脱敏
                "volcengine_access_key": "LW8***oGu",  # 已脱敏
                "volcengine_resource_id": "volc.bigasr.auc",
                "enable_speaker_info": True,
                "enable_emotion": True,
                "enable_gender": True,
                "enable_punc": True,
                "enable_itn": True
            },
            "tts": {
                "service_url": "https://your-server:6006",
                "api_key": "",
                "backend": "vllm"
            },
            "translate": {
                "glm_api_key": "",
                "glm_api_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "glm_model": "glm-4.5"
            }
        }

        self.send_json_response({"code": 0, "data": settings})

    def handle_update_settings(self):
        """更新设置"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            settings = json.loads(post_data.decode('utf-8'))
            print(f"收到设置更新: {json.dumps(settings, indent=2, ensure_ascii=False)}")

            # 模拟保存成功
            self.send_json_response({"code": 0, "message": "设置已保存"})

        except json.JSONDecodeError as e:
            self.send_json_response({"code": 400, "message": f"JSON 解析错误: {e}"}, status=400)

    def handle_test_connection(self):
        """测试连接"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            request = json.loads(post_data.decode('utf-8'))
            service_type = request.get('type', '')

            print(f"测试连接: {service_type}")

            # 模拟连接测试
            time.sleep(1)  # 模拟网络延迟

            if service_type == 'asr':
                # 模拟火山引擎 ASR 连接测试成功
                response = {
                    "code": 0,
                    "data": {
                        "status": "connected",
                        "message": "火山引擎 ASR 连接测试成功",
                        "latency_ms": 152
                    }
                }
            elif service_type == 'tts':
                # 模拟 TTS 连接测试 - 针对用户的 index-tts-vllm 服务
                print(f"测试 TTS 连接，将使用真实的 HTTP 请求...")

                # 这里我们实际测试用户的 TTS 服务
                import urllib.request
                import urllib.error

                try:
                    # 假设从设置中获取 TTS URL (这里硬编码为演示)
                    tts_url = "https://u861448-ej47-562de107.bjb2.seetacloud.com:8443"

                    # 测试多个端点 - 优先测试 API 端点
                    test_endpoints = [
                        "/gradio_api/info",  # Gradio API 信息 (JSON)
                        "/health",           # 标准健康检查
                        "/api/health",       # API 健康检查
                        "/docs",             # FastAPI 文档
                        "/"                  # 主页 (最后测试，可能返回 HTML)
                    ]

                    for endpoint in test_endpoints:
                        test_url = tts_url + endpoint
                        try:
                            print(f"测试端点: {test_url}")
                            req = urllib.request.Request(test_url)
                            req.add_header('User-Agent', 'TTS-Test/1.0')

                            with urllib.request.urlopen(req, timeout=10) as response:
                                if response.status == 200:
                                    content = response.read().decode('utf-8')[:200]
                                    print(f"成功访问 {endpoint}: {content}")

                                    # 检测服务类型
                                    if 'gradio' in content.lower():
                                        service_type_detected = "Gradio IndexTTS"
                                    elif 'fastapi' in content.lower() or 'swagger' in content.lower():
                                        service_type_detected = "FastAPI TTS"
                                    else:
                                        service_type_detected = f"HTTP 服务 ({endpoint})"

                                    response = {
                                        "code": 0,
                                        "data": {
                                            "status": "connected",
                                            "message": f"TTS 服务连接成功 - {service_type_detected}",
                                            "latency_ms": 180
                                        }
                                    }
                                    break
                        except Exception as e:
                            print(f"端点 {endpoint} 测试失败: {e}")
                            continue
                    else:
                        # 所有端点都失败
                        response = {
                            "code": 0,
                            "data": {
                                "status": "failed",
                                "message": "TTS 服务所有端点均无法访问，请检查服务地址和网络连接"
                            }
                        }

                except Exception as e:
                    response = {
                        "code": 0,
                        "data": {
                            "status": "failed",
                            "message": f"TTS 连接测试异常: {str(e)}"
                        }
                    }
            elif service_type == 'translate':
                # 模拟翻译服务测试
                response = {
                    "code": 0,
                    "data": {
                        "status": "failed",
                        "message": "GLM API Key 未配置"
                    }
                }
            else:
                response = {
                    "code": 400,
                    "message": "未知的服务类型"
                }

            self.send_json_response(response)

        except json.JSONDecodeError as e:
            self.send_json_response({"code": 400, "message": f"JSON 解析错误: {e}"}, status=400)

    def send_cors_headers(self):
        """发送 CORS 头"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def send_json_response(self, data, status=200):
        """发送 JSON 响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

        response_text = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response_text.encode('utf-8'))

    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"{self.client_address[0]} - [{self.log_date_time_string()}] {format % args}")

if __name__ == '__main__':
    port = 8080
    server = HTTPServer(('localhost', port), TestAPIHandler)
    print(f"🚀 测试 API 服务器启动在 http://localhost:{port}")
    print("📝 支持的接口:")
    print("  GET  /api/v1/settings       - 获取设置")
    print("  PUT  /api/v1/settings       - 更新设置")
    print("  POST /api/v1/settings/test  - 测试连接")
    print("\n💡 在浏览器中打开 web/index.html 来测试前端界面")
    print("   按 Ctrl+C 停止服务器")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        server.shutdown()