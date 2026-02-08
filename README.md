# 视频自动配音系统 (DeepV)

> **[English](README_EN.md) | [中文](README.md)**
>
> **更新时间：2026年2月8日** | **架构：Python (FastAPI) + Next.js** | **状态：✅ 生产就绪**

这是一个高性能的视频本地化系统，能够自动将视频配音翻译成其他语言。系统结合了先进的 ASR（语音识别）、LLM（大模型翻译）和实时声音复刻 TTS 技术，生成高质量、唇形与时间轴对齐的配音视频。

**🎉 v2.0 新特性**：
- ✅ Docker 部署完全优化，一键启动
- ✅ 硬烧录字幕默认启用，无需单独加载
- ✅ 完整的部署文档和自动化工具
- ✅ Redis/Celery 配置优化，任务处理稳定

---

## 🌟 核心特性

*   **实时声音复刻**：集成 **阿里云 Qwen3-TTS-VC**，仅需极短音频即可完美克隆原说话人音色。
*   **智能音画对齐（双层优化）**：
    *   **意译优化**：通过精心设计的 Prompt 引导 LLM 输出与原文时长相近的译文。
    *   **智能加速**：后端自动计算时间槽，对溢出的音频进行智能加速（最高 4x），确保无重叠、无截断。
*   **高质量翻译**：基于 **Qwen-Turbo** 的全上下文感知翻译，拒绝生硬机翻。
*   **现代技术栈**：
    *   **后端**：Python 3.11, FastAPI, Celery (Redis), SQLAlchemy
    *   **前端**：Next.js 14, Tailwind CSS, shadcn/ui
    *   **基础设施**：Docker Compose v2 一键部署

---

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

#### 准备工作
*   Docker Engine 20.10+
*   Docker Compose 2.0+
*   阿里云百炼 (DashScope) API Key
*   阿里云 OSS 存储桶

#### 1. 克隆与配置
```bash
git clone https://github.com/xmcaicaizi/video-auto-dubbing.git
cd video-auto-dubbing

# 复制环境变量模板（Docker专用）
cp .env.docker.example .env
```

#### 2. 配置必需的环境变量
编辑 `.env` 文件，填入以下关键配置：
```bash
# 阿里云百炼 API Key (必需)
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 阿里云 OSS 配置 (必需)
OSS_ACCESS_KEY_ID=LTAIxxxxxxxx
OSS_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxx
OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
OSS_BUCKET=your-bucket-name
OSS_PUBLIC_DOMAIN=your-bucket-name.oss-cn-beijing.aliyuncs.com

# 数据库密码 (建议修改)
DB_PASSWORD=your_secure_password
```

#### 3. 验证配置
```bash
# 运行配置检查（可选但推荐）
./check-config.sh
```

#### 4. 启动服务
```bash
# 开发/测试环境
docker-compose -f docker-compose.v2.yml up -d

# 或生产环境
docker-compose -f docker-compose.prod.yml up -d --build
```

#### 5. 初始化数据库
```bash
docker-compose -f docker-compose.v2.yml exec api alembic upgrade head
```

#### 6. 验证部署
```bash
# 自动化测试（推荐）
./docker-test.sh

# 或手动访问
# 前端: http://localhost:3000
# 后端 API: http://localhost:8000
# API 文档: http://localhost:8000/api/v1/docs
```

---

### 方式二：本地开发

#### 后端 (Python)
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# 启动 Celery Worker
uv run celery -A app.workers.celery_app worker \
  --loglevel=info --concurrency=2 \
  --queues=default,media,ai,celery &
```

#### 前端 (Next.js)
```bash
cd frontend
npm install
npm run dev
```

#### 访问服务
- 前端: http://localhost:3000
- 后端: http://localhost:8000

---

## 📚 文档中心

### 部署相关 ⭐ 推荐
*   **[DEPLOYMENT.md](DEPLOYMENT.md)**：完整的 Docker 部署指南（含故障排查）
*   **[DEPLOYMENT_READY.md](DEPLOYMENT_READY.md)**：部署就绪确认和验证步骤
*   **[DOCKER_FIXES.md](DOCKER_FIXES.md)**：Docker 配置修复详解
*   **[LOCAL_VS_DOCKER.md](LOCAL_VS_DOCKER.md)**：本地开发与 Docker 部署对比

### 项目总览
*   **[SUMMARY.md](SUMMARY.md)**：项目功能、架构和状态总结
*   **[GIT_COMMIT_SUMMARY.md](GIT_COMMIT_SUMMARY.md)**：最近的更新和修复记录

### 功能说明
*   **[SUBTITLE_DEFAULT_CHANGE.md](SUBTITLE_DEFAULT_CHANGE.md)**：字幕模式配置说明
*   **[CODE_REVIEW_SUMMARY.md](CODE_REVIEW_SUMMARY.md)**：代码审查和最佳实践

### API 文档
*   **Swagger UI**：部署后访问 http://localhost:8000/api/v1/docs
*   **在线接口**：支持在线测试所有 API 端点

---

## 🛠 开发工具

### 配置验证
```bash
# 检查 Docker 配置是否正确
./check-config.sh
```

### 自动化测试
```bash
# 测试 Docker 部署
./docker-test.sh
```

### 应用字幕默认值修改
```bash
# 应用硬烧录为默认字幕模式
./apply-subtitle-default.sh
```

### 服务管理
```bash
# 查看所有服务状态
docker-compose -f docker-compose.v2.yml ps

# 查看日志
docker-compose -f docker-compose.v2.yml logs -f

# 重启服务
docker-compose -f docker-compose.v2.yml restart

# 停止服务
docker-compose -f docker-compose.v2.yml down
```

---

## 🐛 故障排查

### 常见问题

#### 1. 任务卡在"等待处理"
**原因**：Celery worker 未正确配置队列

**解决**：
```bash
# 检查 worker 状态
docker-compose exec worker celery -A app.workers.celery_app inspect active

# 查看 worker 日志
docker-compose logs -f worker
```

#### 2. Redis 连接失败
**原因**：密码配置不一致

**解决**：
- 确保 `.env` 中无 `REDIS_PASSWORD` 配置
- 检查 `docker-compose.v2.yml` 中 Redis 无 `--requirepass` 参数

#### 3. 数据库连接失败
**原因**：环境变量配置错误

**解决**：
```bash
# 检查环境变量
docker-compose exec api env | grep DB_

# 测试数据库连接
docker-compose exec db psql -U dubbing -d dubbing -c "SELECT 1;"
```

更多故障排查请参考：[DEPLOYMENT.md](DEPLOYMENT.md#故障排查)

---

## 📊 系统架构

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
┌──────▼──────────────────────────────────┐
│          Frontend (Next.js)              │
│          Port 3000                       │
└──────┬──────────────────────────────────┘
       │
┌──────▼──────────────────────────────────┐
│          Backend API (FastAPI)           │
│          Port 8000                       │
└──┬────┬────┬────────────────────────────┘
   │    │    │
   │    │    └──> Aliyun DashScope (ASR/LLM/TTS)
   │    │
   │    └──────> Aliyun OSS (Storage)
   │
┌──▼─────────────────────────────────────┐
│  Redis (Broker)         PostgreSQL     │
│  Port 6379              Port 5432      │
└──┬───────────────────────────────────┬─┘
   │                                   │
┌──▼──────────────────────────────────▼──┐
│       Celery Worker (Background)       │
│  Queues: default, media, ai, celery    │
└────────────────────────────────────────┘
```

---

## 🔒 安全建议

### 生产环境必做

1. **修改默认密码**
   ```bash
   DB_PASSWORD=$(openssl rand -hex 32)
   ```

2. **启用 HTTPS**
   - 使用 Let's Encrypt 获取免费证书
   - 配置 NGINX 反向代理

3. **限制端口暴露**
   - 仅暴露必要端口（80/443）
   - 数据库和 Redis 仅内网访问

4. **定期备份**
   ```bash
   # 备份数据库
   docker-compose exec db pg_dump -U dubbing dubbing > backup.sql
   ```

---

## 📈 性能优化

### 推荐配置

| 组件 | CPU | 内存 | 说明 |
|------|-----|------|------|
| API | 1 核 | 512MB | 根据并发调整 |
| Worker | 2 核 | 2GB | 视频处理需要较多资源 |
| Database | 1 核 | 512MB | 中小规模足够 |
| Redis | 0.5 核 | 256MB | 内存缓存 |

### Worker 并发调整
```bash
# .env 文件中配置
WORKER_CONCURRENCY=8  # 建议设为 CPU 核心数
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 开源协议

MIT License.

---

## 🙏 致谢

- [阿里云百炼 (DashScope)](https://dashscope.console.aliyun.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Next.js](https://nextjs.org/)
- [Celery](https://docs.celeryq.dev/)
- [FFmpeg](https://ffmpeg.org/)

---

## 📞 联系方式

- **GitHub**: https://github.com/xmcaicaizi/video-auto-dubbing
- **Issues**: https://github.com/xmcaicaizi/video-auto-dubbing/issues

---

**⭐ 如果这个项目对你有帮助，请给个 Star！**
