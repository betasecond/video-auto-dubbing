# ✅ 问题已解决：前端测试连接 502 错误

## 🔍 问题诊断

### 症状
- 前端点击"测试连接"按钮无反应
- 浏览器控制台报错：`Unexpected token '<', "<html> <h"... is not valid JSON`
- 实际返回的是 HTML 502 错误页面，而不是 JSON

### 根本原因
**nginx 配置未生效或需要重新加载**

详细分析：
1. API 服务运行正常（直接访问 `localhost:8080` 可用）
2. Docker 网络连通正常（gateway 可以 ping 通 api）
3. nginx 配置文件正确
4. **但 nginx 未正确应用配置**，导致请求无法转发到后端

错误日志：
```
connect() failed (111: Connection refused) while connecting to upstream,
upstream: "http://192.168.107.5:8080/api/v1/settings/test"
```

---

## ✅ 解决方案

### 执行的操作

```bash
# 1. 测试 nginx 配置
docker-compose exec gateway nginx -t

# 2. 重新加载 nginx
docker-compose exec gateway nginx -s reload
```

### 验证结果

```bash
# 测试通过 nginx 访问 API
curl -X POST http://localhost/api/v1/settings/test \
  -H "Content-Type: application/json" \
  -d '{"type": "tts"}'

# 成功响应：
{
    "code": 0,
    "data": {
        "status": "connected",
        "message": "TTS 服务连接成功",
        "latency_ms": 655
    }
}
```

---

## 📋 完整的故障排查流程

### 1. 确认服务运行状态
```bash
docker-compose ps
# 所有服务应该是 Up 状态
```

### 2. 测试 API 直接访问
```bash
curl http://localhost:8080/health
# 应该返回 {"status":"ok"}
```

### 3. 测试 nginx 代理
```bash
curl http://localhost/api/v1/settings
# 如果返回 502，说明 nginx 转发有问题
```

### 4. 检查 nginx 日志
```bash
docker-compose logs gateway --tail=50 | grep error
# 查看是否有 "Connection refused" 错误
```

### 5. 测试容器间网络
```bash
# 从 gateway 容器访问 api
docker-compose exec gateway ping -c 2 api
docker-compose exec gateway wget -O- http://api:8080/health
```

### 6. 重新加载 nginx
```bash
docker-compose exec gateway nginx -s reload
```

---

## 🎯 预防措施

### 问题场景

当以下情况发生时，可能需要重新加载 nginx：

1. **修改了 nginx 配置文件**
2. **重启了 API 或其他后端服务**
3. **Docker 网络重新创建**
4. **容器 IP 地址变化**

### 自动化解决方案

创建一个健康检查脚本：

```bash
#!/bin/bash
# nginx_health_check.sh

# 测试 nginx 代理是否正常
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health)

if [ "$HTTP_CODE" != "200" ]; then
    echo "Nginx proxy not working, reloading..."
    docker-compose exec -T gateway nginx -s reload
    echo "Nginx reloaded"
else
    echo "Nginx proxy is healthy"
fi
```

### docker-compose 配置优化

在 `docker-compose.yml` 中添加健康检查：

```yaml
services:
  gateway:
    image: nginx:alpine
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://api:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      api:
        condition: service_healthy
```

---

## 🛠️ 快速修复命令

**如果前端测试连接失败，执行以下命令：**

```bash
cd /Users/micago/Desktop/index/video-auto-dubbing

# 一键修复
docker-compose exec gateway nginx -s reload

# 验证
curl http://localhost/api/v1/settings | jq '.data.tts'
```

---

## 📊 当前系统状态

### Docker 服务
```
✅ video-dubbing-api      - Up (192.168.107.6:8080)
✅ video-dubbing-gateway  - Up (nginx proxy)
✅ video-dubbing-db       - Up
✅ video-dubbing-worker   - Up
✅ video-dubbing-minio    - Up
✅ video-dubbing-rabbitmq - Up
```

### API 端点测试
```
✅ Direct:  http://localhost:8080/api/v1/settings - OK
✅ Proxied: http://localhost/api/v1/settings - OK
✅ Test:    http://localhost/api/v1/settings/test - OK
```

### TTS 配置
```json
{
  "service_url": "https://u861448-ej47-562de107.bjb2.seetacloud.com:8443",
  "backend": "vllm",
  "api_key": ""
}
```

---

## 🎯 验收清单

- [x] nginx 配置已重新加载
- [x] 前端可以访问 API
- [x] 测试连接返回 JSON 而不是 HTML
- [x] TTS 连接测试通过
- [x] 所有 Docker 服务正常运行

---

## 📞 下一步

### 1. 刷新前端页面

打开浏览器，按 `Ctrl+F5` 强制刷新：
- http://localhost/

### 2. 测试设置功能

1. 进入 设置 > TTS 服务
2. 点击 "测试连接"
3. 应该显示 "连接成功"

### 3. 运行完整任务

上传一个测试视频，验证完整流程。

---

**状态：** ✅ 问题已解决
**原因：** nginx 配置未生效
**解决：** 重新加载 nginx 配置
**时间：** 2026-01-23 18:43
