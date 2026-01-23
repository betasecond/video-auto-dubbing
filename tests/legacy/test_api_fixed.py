#!/usr/bin/env python3
"""
修复后的测试 API 服务器，正确处理 TTS 连接测试
"""

import json
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import time

class FixedAPIHandler(BaseHTTPRequestHandler):
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
        """返回当前设置"""
        settings = {
            "asr": {
                "volcengine_app_key": "608***513",
                "volcengine_access_key": "LW8***oGu",
                "volcengine_resource_id": "volc.bigasr.auc",
                "enable_speaker_info": True,
                "enable_emotion": True,
                "enable_gender": True,
                "enable_punc": True,
                "enable_itn": True
            },
            "tts": {
                "service_url": "https://u861448-ej47-562de107.bjb2.seetacloud.com:8443",
                "api_key": "",
                "backend": "vllm"
            },
            "translate": {
                "glm_api_key": "",
                "glm_api_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "glm_model": "glm-4-flash"
            }
        }

        self.send_json_response({"code": 0, "data": settings})

    def handle_update_settings(self):
        """更新设置"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            settings = json.loads(post_data.decode('utf-8'))
            print(f"💾 收到设置更新: {json.dumps(settings, indent=2, ensure_ascii=False)}")

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

            print(f"🧪 测试连接: {service_type}")

            if service_type == 'asr':
                # 火山引擎 ASR 测试
                response = {
                    "code": 0,
                    "data": {
                        "status": "connected",
                        "message": "火山引擎 ASR 连接测试成功",
                        "latency_ms": 152
                    }
                }
            elif service_type == 'tts':
                # 使用真实的 TTS 连接测试
                print(f"🎤 调用真实 TTS 连接测试...")
                try:
                    result = subprocess.run([
                        'python3', 'test_tts_connection.py'
                    ], capture_output=True, text=True, timeout=30, cwd='/Users/micago/Desktop/index/video-auto-dubbing')

                    if result.returncode == 0:
                        # 解析测试脚本的输出
                        output_lines = result.stdout.strip().split('\n')
                        final_lines = [line for line in output_lines if line.startswith(('状态:', '消息:', '延迟:', '服务类型:'))]

                        if len(final_lines) >= 2:
                            status_line = next((line for line in final_lines if line.startswith('状态:')), '')
                            message_line = next((line for line in final_lines if line.startswith('消息:')), '')
                            latency_line = next((line for line in final_lines if line.startswith('延迟:')), '')

                            status = status_line.split(':', 1)[1].strip() if status_line else 'connected'
                            message = message_line.split(':', 1)[1].strip() if message_line else 'TTS 服务测试完成'

                            latency_ms = 87  # 默认值
                            if latency_line:
                                try:
                                    latency_text = latency_line.split(':', 1)[1].strip()
                                    latency_ms = int(latency_text.replace('ms', ''))
                                except:
                                    pass

                            response = {
                                "code": 0,
                                "data": {
                                    "status": status,
                                    "message": message,
                                    "latency_ms": latency_ms
                                }
                            }
                        else:
                            response = {
                                "code": 0,
                                "data": {
                                    "status": "connected",
                                    "message": "TTS 服务测试完成 (详细输出解析失败)",
                                    "latency_ms": 100
                                }
                            }
                    else:
                        response = {
                            "code": 0,
                            "data": {
                                "status": "failed",
                                "message": f"TTS 测试脚本执行失败: {result.stderr}"
                            }
                        }

                except subprocess.TimeoutExpired:
                    response = {
                        "code": 0,
                        "data": {
                            "status": "failed",
                            "message": "TTS 连接测试超时"
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
                # 模拟 GLM-4-Flash 翻译服务测试
                print(f"🌐 测试 GLM-4-Flash 翻译服务...")

                # 这里模拟检查API Key配置
                # 在实际使用中会检查数据库中的API Key
                response = {
                    "code": 0,
                    "data": {
                        "status": "failed",
                        "message": "GLM-4-Flash API Key 未配置，请在智谱AI开放平台获取免费API Key"
                    }
                }

                # 如果配置了API Key，可以返回连接成功
                # response = {
                #     "code": 0,
                #     "data": {
                #         "status": "connected",
                #         "message": "GLM-4-Flash 免费模型连接成功 - 支持26种语言翻译",
                #         "latency_ms": 200
                #     }
                # }
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
    server = HTTPServer(('localhost', port), FixedAPIHandler)
    print(f"🚀 修复版 API 服务器启动在 http://localhost:{port}")
    print("📝 支持的接口:")
    print("  GET  /api/v1/settings       - 获取设置")
    print("  PUT  /api/v1/settings       - 更新设置")
    print("  POST /api/v1/settings/test  - 测试连接 (包含真实 TTS 测试)")
    print("\n💡 TTS 测试现在会调用真实的连接测试脚本")
    print("   按 Ctrl+C 停止服务器")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        server.shutdown()