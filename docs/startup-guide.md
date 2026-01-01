# 启动指南

本文档记录视频本地化自动配音系统的启动流程和常见问题解决方案。

## 快速启动

### 前置要求

1. **Docker Desktop** 已安装并运行
   - Windows: 确保 `com.docker.service` 服务已启动（可能需要管理员权限）
   - 验证：运行 `docker version` 应能看到 Server 信息

2. **环境变量配置**（可选，推荐通过前端设置）
   - `ASR_API_KEY`: 豆包语音 ASR API Key
   - `GLM_API_KEY`: 智谱 GLM API Key
   - `GLM_API_URL`: GLM API 地址（默认：https://open.bigmodel.cn/api/paas/v4/chat/completions）
   - `GLM_MODEL`: GLM 模型名（默认：glm-4.5）
   - `MODELSCOPE_TOKEN`: ModelScope API Token
   - `MINIO_PUBLIC_ENDPOINT`: MinIO 公网访问地址（如果 ASR 需要从外网下载音频）

### 启动步骤

```bash
# 1. 进入项目目录
cd vedio

# 2. 启动所有服务
docker compose up -d

# 3. 查看服务状态
docker compose ps

# 4. 查看日志（可选）
docker compose logs -f
```

### 服务访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://localhost | 通过 NGINX 网关访问 |
| API 服务 | http://localhost:8080 | 后端 API |
| TTS 服务 | http://localhost:8001 | 语音合成服务（默认 8001，避免与 8000 冲突） |
| MinIO 控制台 | http://localhost:9001 | 对象存储管理 |
| RabbitMQ 管理台 | http://localhost:15672 | 消息队列管理 |
| PostgreSQL | localhost:5432 | 数据库 |

## 常见问题

### 1. Docker Engine 未运行

**症状**：
```
error during connect: open //./pipe/docker_engine: The system cannot find the file specified
```

**解决方案**：
1. 启动 Docker Desktop 应用程序
2. 以管理员身份运行 PowerShell，执行：
   ```powershell
   Start-Service com.docker.service
   ```
3. 验证：`docker version` 应显示 Server 信息

### 2. 端口冲突

**症状**：
```
Bind for 0.0.0.0:8000 failed: port is already allocated
```

**解决方案**：
- 检查占用端口的容器：`docker ps --format "table {{.Names}}\t{{.Ports}}"`
- 修改 `docker-compose.yml` 中的端口映射，或停止占用端口的容器
- TTS 服务默认使用 8001 端口以避免冲突

### 3. 构建失败：缺少 go.sum

**症状**：
```
failed to calculate checksum: "/go.sum": not found
```

**解决方案**：
- Dockerfile 已修复：在构建阶段运行 `go mod tidy` 自动生成 go.sum
- 如果本地需要，可运行：`cd api && go mod tidy` 和 `cd worker && go mod tidy`

### 4. 构建失败：Go 编译错误

**症状**：
```
"time" imported and not used
"os" imported and not used
```

**解决方案**：
- 已修复：移除了所有未使用的 import
- 如果遇到类似问题，运行 `go vet ./...` 检查

### 5. TTS 服务启动失败：找不到 uvicorn

**症状**：
```
exec: "uvicorn": executable file not found in $PATH
```

**解决方案**：
- Dockerfile 已修复：使用绝对路径 `/app/.venv/bin/uvicorn`
- 确保 `docker-compose.yml` 中没有覆盖 `/app` 的 bind mount（会覆盖虚拟环境）

### 6. TTS 健康检查失败：找不到 curl

**症状**：
```
exec: "curl": executable file not found in $PATH
```

**解决方案**：
- 已修复：健康检查改为使用 Python `urllib`，不依赖 curl
- 检查 `docker-compose.yml` 中的 healthcheck 配置

### 7. TTS 服务启动失败：缺少 MODELSCOPE_TOKEN

**症状**：
```
MODELSCOPE_TOKEN is required but not set
```

**解决方案**：
- 已修复：TTS 服务支持延迟加载，启动时不再强制要求 token
- 可以通过前端设置页面配置 token，或设置环境变量 `MODELSCOPE_TOKEN`

### 8. Debian apt 源连接失败

**症状**：
```
Failed to fetch http://deb.debian.org/... Unable to connect
```

**解决方案**：
- Dockerfile 已修复：自动将 apt 源切换为 HTTPS
- 如果仍有问题，检查网络连接或使用代理

## 验证服务运行

### 检查容器状态

```bash
docker compose ps
```

所有服务应显示 `Up (healthy)` 状态。

### 检查服务日志

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f tts_service
```

### 测试 API 端点

```bash
# 测试 API 健康检查
curl http://localhost:8080/health

# 测试 TTS 健康检查
curl http://localhost:8001/health
```

## 停止服务

```bash
# 停止所有服务（保留数据）
docker compose stop

# 停止并删除容器（保留数据卷）
docker compose down

# 停止并删除所有（包括数据卷）
docker compose down -v
```

## 重启服务

```bash
# 重启所有服务
docker compose restart

# 重启特定服务
docker compose restart api
docker compose restart worker
```

## 更新代码后重新构建

```bash
# 重新构建并启动
docker compose up -d --build

# 仅重新构建特定服务
docker compose up -d --build api
docker compose up -d --build worker
docker compose up -d --build tts_service
```

## 开发模式

如果需要修改代码并实时生效，可以：

1. **API/Worker（Go）**：
   - 修改代码后重新构建：`docker compose up -d --build api`
   - 或使用 bind mount（不推荐，可能覆盖构建产物）

2. **TTS（Python）**：
   - 修改代码后重新构建：`docker compose up -d --build tts_service`
   - 或使用 bind mount（注意不要覆盖 `.venv`）

## 故障排查

### 查看容器详细信息

```bash
docker inspect video-dubbing-api
docker inspect video-dubbing-worker
docker inspect video-dubbing-tts
```

### 进入容器调试

```bash
# 进入 API 容器
docker exec -it video-dubbing-api sh

# 进入 Worker 容器
docker exec -it video-dubbing-worker sh

# 进入 TTS 容器
docker exec -it video-dubbing-tts bash
```

### 检查网络连接

```bash
# 查看 Docker 网络
docker network ls
docker network inspect vedio_dubbing-network
```

### 检查数据卷

```bash
# 查看数据卷
docker volume ls
docker volume inspect vedio_postgres_data
docker volume inspect vedio_minio_data
```

## 性能优化

### 扩展 Worker 实例

```bash
# 启动 3 个 worker 实例
docker compose up -d --scale worker=3
```

### 资源限制

在 `docker-compose.yml` 中为服务添加资源限制：

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

## 安全建议

1. **生产环境**：
   - 修改所有默认密码
   - 使用环境变量文件（`.env`）管理敏感信息
   - 启用 HTTPS（配置 SSL 证书）
   - 限制端口暴露（仅暴露必要的端口）

2. **API Key 管理**：
   - 当前 MVP 阶段：API Key 存储在数据库（明文）
   - 生产环境：应加密存储或使用密钥管理服务

3. **网络隔离**：
   - 使用 Docker 网络隔离服务
   - 仅网关服务暴露到公网
   - 内部服务通过服务名通信

## 相关文档

- [部署指南](deployment.md)
- [架构文档](architecture.md)
- [API 接口文档](api-contracts.md)
- [TTS 服务文档](tts-service.md)

