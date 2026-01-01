# 部署指南

## Docker Compose 部署

### 前置要求

- Docker Engine 20.10+
- Docker Compose 2.0+
- 至少 8GB 可用内存
- 至少 50GB 可用磁盘空间

### 快速开始

1. **克隆项目并进入目录**
```bash
cd vedio
```

2. **配置环境变量**

本仓库提供 `env.example` 作为环境变量示例（部分环境会限制使用 dotfile，例如 `.env.example`）。

如果你的环境支持 `.env` 文件，可以将示例复制为 `.env`：

```bash
cp env.example .env
```

编辑 `.env` 文件，设置必要的配置：

```env
# 数据库配置
POSTGRES_DB=dubbing
POSTGRES_USER=dubbing
POSTGRES_PASSWORD=your_secure_password
POSTGRES_PORT=5432

# MinIO 配置
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=your_secure_password
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
MINIO_BUCKET=videos

# RabbitMQ 配置
RABBITMQ_USER=rabbitmq
RABBITMQ_PASSWORD=your_secure_password
RABBITMQ_PORT=5672
RABBITMQ_MANAGEMENT_PORT=15672

# API 服务配置
API_PORT=8080

# TTS 服务配置
TTS_PORT=8000
TTS_BACKEND=modelscope  # 或 mock（用于测试）

# ModelScope API 配置（必填）
MODELSCOPE_TOKEN=your_modelscope_token  # 从 https://modelscope.cn 获取
MODELSCOPE_MODEL_ID=IndexTeam/IndexTTS-2  # 可选，默认值
STRICT_DURATION=false  # 是否严格对齐时长（true/false）
MAX_CONCURRENT_REQUESTS=10  # 最大并发请求数
MAX_RETRIES=3  # API 调用最大重试次数

# 外部 API 配置（推荐通过前端设置页面配置，环境变量作为后备）
# 豆包语音 ASR API Key（新版，使用 x-api-key 鉴权）
ASR_API_KEY=your_asr_api_key

# 智谱 GLM 翻译 API 配置
GLM_API_KEY=your_glm_api_key
GLM_API_URL=https://open.bigmodel.cn/api/paas/v4/chat/completions
GLM_MODEL=glm-4.5

# MinIO 公网访问地址（可选，如果豆包语音需要从外网下载音频）
# 例如：minio.example.com:9000 或反向代理地址
MINIO_PUBLIC_ENDPOINT=

# 网关配置
GATEWAY_HTTP_PORT=80
GATEWAY_HTTPS_PORT=443
```

3. **启动所有服务**

```bash
docker compose up -d
```

4. **查看服务状态**

```bash
docker compose ps
```

5. **查看日志**

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f tts_service
```

### 服务访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| API 服务 | http://localhost:8080 | 后端 API |
| TTS 服务 | http://localhost:8000 | TTS 服务 |
| MinIO 控制台 | http://localhost:9001 | 对象存储管理 |
| RabbitMQ 管理 | http://localhost:15672 | 消息队列管理 |
| 网关 | http://localhost:80 | 统一入口 |

**默认账号密码**:
- MinIO: `minioadmin` / `minioadmin123` (需修改)
- RabbitMQ: `rabbitmq` / `rabbitmq123` (需修改)

### 扩展 Worker 实例

**水平扩展 worker 服务**:

```bash
# 启动 3 个 worker 实例
docker compose up -d --scale worker=3

# 查看 worker 实例
docker compose ps worker
```

**动态调整 worker 数量**:

```bash
# 增加到 5 个
docker compose up -d --scale worker=5

# 减少到 2 个
docker compose up -d --scale worker=2
```

**注意事项**:
- Worker 是无状态的，可以安全地扩展
- 每个 worker 会从同一个队列消费任务
- RabbitMQ 会自动进行负载均衡

### 服务依赖关系

```
gateway -> api -> db, minio, rabbitmq
gateway -> tts_service
worker -> db, minio, rabbitmq, tts_service
```

启动顺序由 `depends_on` 和 `healthcheck` 自动管理。

### 数据持久化

所有数据存储在 Docker volumes 中：

| Volume | 用途 | 位置 |
|--------|------|------|
| `postgres_data` | PostgreSQL 数据 | `/var/lib/postgresql/data` |
| `minio_data` | MinIO 对象存储 | `/data` |
| `rabbitmq_data` | RabbitMQ 数据 | `/var/lib/rabbitmq` |
| `tts_temp` | TTS 临时文件 | `/app/temp` |
| `api_logs` | API 服务日志 | `/app/logs` |
| `worker_logs` | Worker 服务日志 | `/app/logs` |

**备份数据**:

```bash
# 备份 PostgreSQL
docker compose exec db pg_dump -U dubbing dubbing > backup.sql

# 备份 MinIO（使用 mc 客户端）
docker compose exec minio mc mirror /data /backup
```

### 健康检查

所有服务都配置了健康检查：

```bash
# 检查所有服务健康状态
docker compose ps

# 手动检查服务健康
curl http://localhost:8080/health
curl http://localhost:8000/health
```

### 停止和清理

**停止服务**:
```bash
docker compose stop
```

**停止并删除容器**:
```bash
docker compose down
```

**停止并删除容器、网络、volumes**:
```bash
docker compose down -v
```

⚠️ **警告**: `-v` 选项会删除所有数据，包括数据库和对象存储中的数据！

### 更新服务

1. **拉取最新代码**
```bash
git pull
```

2. **重新构建镜像**
```bash
docker compose build
```

3. **重启服务**
```bash
docker compose up -d
```

**零停机更新**（推荐）:
```bash
# 先启动新容器
docker compose up -d --no-deps --build api

# 等待新容器健康后，停止旧容器
docker compose stop api
docker compose rm -f api
docker compose up -d api
```

### 生产环境建议

1. **使用 HTTPS**
   - 配置 SSL 证书
   - 修改 `gateway/nginx.conf` 启用 HTTPS
   - 将证书放在 `gateway/ssl/` 目录

2. **修改默认密码**
   - 所有服务的默认密码必须修改
   - 使用强密码策略

3. **资源限制**
   - 在 `docker-compose.yml` 中添加资源限制：
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 4G
       reservations:
         cpus: '1'
         memory: 2G
   ```

4. **日志管理**
   - 配置日志轮转
   - 使用集中式日志收集（如 ELK、Loki）

5. **监控告警**
   - 配置 Prometheus + Grafana
   - 设置关键指标告警

6. **备份策略**
   - 定期备份数据库
   - 定期备份对象存储
   - 测试恢复流程

### 故障排查

**服务无法启动**:
```bash
# 查看详细日志
docker compose logs service_name

# 检查服务健康状态
docker compose ps

# 检查端口占用
netstat -tulpn | grep :8080
```

**数据库连接失败**:
```bash
# 检查数据库是否运行
docker compose ps db

# 检查数据库日志
docker compose logs db

# 测试数据库连接
docker compose exec db psql -U dubbing -d dubbing
```

**队列消息堆积**:
```bash
# 查看 RabbitMQ 管理界面
# http://localhost:15672

# 检查队列状态
docker compose exec rabbitmq rabbitmqctl list_queues
```

**Worker 处理慢**:
```bash
# 增加 worker 实例
docker compose up -d --scale worker=5

# 检查 worker 日志
docker compose logs -f worker
```

### 性能调优

1. **数据库优化**
   - 调整 PostgreSQL 配置
   - 添加适当的索引
   - 定期 VACUUM

2. **队列优化**
   - 调整 RabbitMQ 预取数量
   - 优化消息大小
   - 使用消息压缩

3. **对象存储优化**
   - 使用 CDN 加速
   - 配置生命周期策略
   - 优化存储桶结构

4. **TTS 服务优化**
   - 调整 `MAX_CONCURRENT_REQUESTS` 避免触发 API 限流
   - 根据需求选择 `STRICT_DURATION` 模式（质量 vs 时长精确度）
   - 监控 ModelScope API 调用配额和限流情况
   - 优化批处理大小（分段合成）

