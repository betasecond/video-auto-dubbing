# 快速启动指南

视频自动配音系统 v2.0 - 完整启动指南

## 系统架构

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   前端       │      │   后端       │      │  Worker      │
│  Next.js    │─────▶│  FastAPI    │◀─────│  Celery     │
│  (Port 3000)│      │  (Port 8000)│      │             │
└─────────────┘      └─────────────┘      └─────────────┘
                            │                     │
                            ▼                     ▼
                     ┌─────────────┐      ┌─────────────┐
                     │  PostgreSQL │      │    Redis    │
                     │  (Port 5432)│      │  (Port 6379)│
                     └─────────────┘      └─────────────┘
```

## 环境要求

### 必需软件

- **Python**: 3.10+ (推荐使用 uv)
- **Node.js**: 18+
- **PostgreSQL**: 14+
- **Redis**: 6+
- **FFmpeg**: 4.4+

### 可选工具

- Docker & Docker Compose (容器化部署)
- Git (版本控制)

## 第一步：准备基础服务

### 方式 1: 使用 Docker Compose（推荐）

```bash
# 启动 PostgreSQL 和 Redis
docker-compose up -d postgres redis

# 检查服务状态
docker-compose ps
```

### 方式 2: 本地安装

**PostgreSQL**
```bash
# macOS
brew install postgresql@14
brew services start postgresql@14

# Ubuntu/Debian
sudo apt install postgresql-14
sudo systemctl start postgresql
```

**Redis**
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis
```

**FFmpeg**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

## 第二步：配置环境变量

### 1. 复制环境变量模板

```bash
cp .env.example .env
```

### 2. 编辑 `.env` 文件

**必须配置的参数**：

```bash
# 阿里云 OSS（必需）
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=your-bucket-name
OSS_ACCESS_KEY_ID=your-access-key-id
OSS_ACCESS_KEY_SECRET=your-access-key-secret
OSS_PUBLIC_DOMAIN=https://your-bucket.oss-cn-hangzhou.aliyuncs.com

# 阿里百炼 DashScope（必需）
DASHSCOPE_API_KEY=your-dashscope-api-key
```

**可选配置**：

```bash
# 数据库配置（默认值可用）
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dubbing
DB_USER=dubbing
DB_PASSWORD=dubbing123

# Redis 配置（默认值可用）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# TTS 模式选择
# - cosyvoice-v1: 系统音色模式（快速）
# - qwen3-tts-vc-realtime-2026-01-15: 声音复刻模式（保真）
TTS_MODEL=qwen3-tts-vc-realtime-2026-01-15
```

## 第三步：初始化数据库

```bash
cd backend

# 使用 uv 创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
uv sync

# 运行数据库迁移
alembic upgrade head
```

## 第四步：启动后端服务

### 终端 1: 启动 FastAPI

```bash
cd backend
source .venv/bin/activate

# 开发模式
uvicorn app.main:app --reload --port 8000

# 或使用脚本
./dev.sh
```

访问 API 文档: http://localhost:8000/api/v1/docs

### 终端 2: 启动 Celery Worker

```bash
cd backend
source .venv/bin/activate

# 启动 Worker
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

# 或使用脚本
./run_worker.sh
```

## 第五步：启动前端

### 终端 3: 启动 Next.js

```bash
cd frontend

# 安装依赖（首次运行）
npm install

# 启动开发服务器
npm run dev

# 或使用脚本
./dev.sh
```

访问前端: http://localhost:3000

## 验证系统

### 1. 检查后端健康状态

```bash
curl http://localhost:8000/health
# 应返回: {"status":"healthy","version":"2.0.0"}
```

### 2. 检查服务连接

```bash
curl http://localhost:8000/api/v1/monitoring/health
```

应返回：
```json
{
  "status": "healthy",
  "services": {
    "database": true,
    "redis": true,
    "ffmpeg": true
  },
  "version": "2.0.0"
}
```

### 3. 检查系统统计

```bash
curl http://localhost:8000/api/v1/monitoring/stats
```

### 4. 测试前端访问

浏览器打开: http://localhost:3000

## 使用流程

### 1. 创建配音任务

1. 访问 http://localhost:3000
2. 点击"开始配音"按钮
3. 上传视频文件（支持 MP4, AVI, MOV, MKV, FLV）
4. 选择源语言和目标语言
5. 点击"创建任务"

### 2. 监控任务进度

- 任务会自动跳转到详情页
- 进度条实时更新（每 2 秒刷新）
- 可以查看详细的处理步骤

### 3. 下载结果

- 任务完成后，点击"下载结果"按钮
- 获取配音后的视频文件

## 目录结构

```
video-auto-dubbing/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── models/         # 数据库模型
│   │   ├── schemas/        # Pydantic 模型
│   │   ├── services/       # 业务逻辑
│   │   ├── workers/        # Celery 任务
│   │   ├── integrations/   # 外部服务集成
│   │   └── utils/          # 工具函数
│   ├── migrations/         # 数据库迁移
│   ├── tests/              # 测试
│   └── dev.sh              # 开发启动脚本
├── frontend/                # 前端应用
│   ├── app/                # Next.js App Router
│   │   ├── tasks/          # 任务相关页面
│   │   ├── layout.tsx      # 根布局
│   │   └── page.tsx        # 首页
│   ├── lib/
│   │   └── api.ts          # API 客户端
│   ├── components/         # React 组件
│   └── dev.sh              # 开发启动脚本
├── .env                     # 环境变量
├── docker-compose.yml       # Docker 编排
└── QUICKSTART.md            # 本文档
```

## 常见问题

### 1. 后端启动失败

**问题**: `ModuleNotFoundError: No module named 'app'`

**解决**:
```bash
cd backend
uv sync
source .venv/bin/activate
```

### 2. 数据库连接失败

**问题**: `could not connect to server: Connection refused`

**解决**:
```bash
# 检查 PostgreSQL 是否运行
docker-compose ps postgres
# 或
pg_isready -h localhost -p 5432
```

### 3. Redis 连接失败

**问题**: `Error 111 connecting to localhost:6379. Connection refused`

**解决**:
```bash
# 检查 Redis 是否运行
docker-compose ps redis
# 或
redis-cli ping
```

### 4. Celery Worker 启动失败

**问题**: 无法连接到 broker

**解决**:
- 确保 Redis 正在运行
- 检查 `.env` 中的 `REDIS_HOST` 和 `REDIS_PORT`

### 5. 前端无法连接后端

**问题**: Network Error

**解决**:
- 确保后端服务在 http://localhost:8000 运行
- 检查 `frontend/.env.local` 中的 `NEXT_PUBLIC_API_URL`
- 检查浏览器控制台的 CORS 错误

### 6. OSS 上传失败

**问题**: OSS authentication failed

**解决**:
- 检查 `.env` 中的 OSS 配置
- 确保 Access Key 有效
- 确保 Bucket 存在且有写权限

### 7. TTS 合成失败

**问题**: DashScope API error

**解决**:
- 检查 `DASHSCOPE_API_KEY` 是否有效
- 确保 API Key 有 TTS 权限
- 查看后端日志获取详细错误信息

## 日志位置

```bash
# 后端日志
backend/logs/app.log
backend/backend.log

# Worker 日志
backend/worker.log

# 前端日志
frontend/frontend.log

# 实时查看日志
tail -f backend/logs/app.log
tail -f backend/worker.log
```

## 停止服务

```bash
# 停止前端（Ctrl+C）
# 停止后端（Ctrl+C）
# 停止 Worker（Ctrl+C）

# 停止 Docker 服务
docker-compose down

# 或停止所有
docker-compose down -v  # 同时删除数据卷
```

## 生产部署

### 使用 Docker Compose

```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 环境变量

生产环境需要修改：

```bash
DEBUG=false
LOG_LEVEL=WARNING
CORS_ORIGINS=["https://your-domain.com"]
```

## 性能优化建议

1. **增加 Worker 并发数**
   ```bash
   WORKER_CONCURRENCY=8  # 根据 CPU 核心数调整
   ```

2. **启用 Redis 持久化**
   ```bash
   # redis.conf
   save 900 1
   save 300 10
   ```

3. **配置 PostgreSQL 连接池**
   ```bash
   # 在数据库 URL 中添加
   ?pool_size=20&max_overflow=0
   ```

4. **使用 CDN 加速 OSS**
   - 配置阿里云 CDN
   - 更新 `OSS_PUBLIC_DOMAIN`

## 下一步

- 📖 阅读 [后端 API 文档](backend/API_DOCUMENTATION.md)
- 📖 阅读 [前端开发文档](frontend/README.md)
- 🔧 查看 [多说话人配音指南](backend/MULTI_SPEAKER_GUIDE.md)
- 🚀 查看 [部署指南](backend/DEPLOYMENT.md)

## 支持

- 📧 Email: support@example.com
- 💬 GitHub Issues: https://github.com/your-repo/issues
- 📖 API 文档: http://localhost:8000/api/v1/docs
