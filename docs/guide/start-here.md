# 🚀 开始使用 - 视频自动配音系统 v2.0

欢迎使用视频自动配音系统！这份文档将帮助你在 5 分钟内启动整个系统。

## ⚡ 快速启动（推荐）

### 前提条件

确保已安装：
- ✅ Docker & Docker Compose
- ✅ Node.js 18+
- ✅ Python 3.10+

### 三步启动

#### 1️⃣ 启动基础服务（PostgreSQL + Redis）

```bash
# 在项目根目录
docker-compose up -d postgres redis

# 等待 5-10 秒，让服务完全启动
docker-compose ps
```

#### 2️⃣ 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填写必需配置：
# - DASHSCOPE_API_KEY（阿里云百炼 API Key）
# - OSS 相关配置（如果需要）
nano .env  # 或使用你喜欢的编辑器
```

#### 3️⃣ 启动应用服务

```bash
# 终端 1: 启动后端
cd backend
uv sync                    # 安装依赖
alembic upgrade head       # 初始化数据库
./dev.sh                   # 启动 FastAPI

# 终端 2: 启动 Worker
cd backend
./run_worker.sh            # 启动 Celery Worker

# 终端 3: 启动前端
cd frontend
npm install                # 安装依赖
./dev.sh                   # 启动 Next.js
```

### ✅ 验证安装

打开浏览器：
- 前端：http://localhost:3000
- 后端 API 文档：http://localhost:8000/api/v1/docs
- 健康检查：http://localhost:8000/health

看到正常页面即成功！🎉

---

## 📚 详细文档

### 如果这是你第一次使用

👉 **阅读**: [QUICKSTART.md](QUICKSTART.md) - 完整的启动指南

包含：
- 详细的环境准备
- 服务配置说明
- 常见问题解决
- 使用流程演示

### 如果你想了解系统架构

👉 **阅读**: [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - 系统总览

包含：
- 技术架构图
- 数据模型
- 处理流程
- 性能指标

### 如果你想开发或部署

**后端开发者**:
- [backend/README.md](backend/README.md) - 后端开发指南
- [backend/API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md) - API 文档
- [backend/DEPLOYMENT.md](backend/DEPLOYMENT.md) - 后端部署指南

**前端开发者**:
- [frontend/README.md](frontend/README.md) - 前端开发指南
- [frontend/DEPLOYMENT.md](frontend/DEPLOYMENT.md) - 前端部署指南
- [FRONTEND_COMPLETED.md](FRONTEND_COMPLETED.md) - 前端功能清单

---

## 🎯 使用流程

### 第一次创建任务

1. **访问首页**
   - 打开 http://localhost:3000
   - 点击"开始配音"按钮

2. **上传视频**
   - 拖拽或点击上传视频文件
   - 支持格式：MP4, AVI, MOV, MKV, FLV
   - 最大 500MB

3. **选择语言**
   - 源语言：视频原始语言（如：中文）
   - 目标语言：配音目标语言（如：英语）

4. **提交任务**
   - 点击"创建任务"
   - 自动跳转到任务详情页

5. **监控进度**
   - 实时查看处理进度
   - 处理步骤：提取音频 → 语音识别 → 翻译 → 语音合成 → 视频合成

6. **下载结果**
   - 任务完成后，点击"下载结果"
   - 获取配音后的视频

### 处理时间参考

| 视频时长 | 预计处理时间 |
|---------|-------------|
| 1 分钟  | 2-5 分钟    |
| 5 分钟  | 8-20 分钟   |
| 10 分钟 | 15-40 分钟  |

> 💡 **提示**: 使用声音复刻模式会比系统音色模式慢一些，但效果更好。

---

## 🔧 常见问题

### 1. 后端启动失败

**症状**: `ModuleNotFoundError` 或 `ImportError`

**解决**:
```bash
cd backend
uv sync          # 重新安装依赖
source .venv/bin/activate
```

### 2. 数据库连接失败

**症状**: `could not connect to server`

**解决**:
```bash
# 检查 PostgreSQL 是否运行
docker-compose ps postgres

# 如果没运行，启动它
docker-compose up -d postgres
```

### 3. Celery Worker 无法启动

**症状**: `Error 111 connecting to localhost:6379`

**解决**:
```bash
# 检查 Redis 是否运行
docker-compose ps redis

# 如果没运行，启动它
docker-compose up -d redis
```

### 4. 前端无法连接后端

**症状**: Network Error 或 CORS Error

**解决**:
```bash
# 1. 确保后端在运行
curl http://localhost:8000/health

# 2. 检查前端环境变量
cat frontend/.env.local
# 应该包含: NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# 3. 重启前端
cd frontend
npm run dev
```

### 5. 任务一直处于 pending 状态

**症状**: 任务创建后不处理

**解决**:
```bash
# 确保 Celery Worker 在运行
cd backend
./run_worker.sh

# 检查 Worker 日志
tail -f worker.log
```

### 6. OSS 上传失败

**症状**: `OSS authentication failed`

**解决**:
```bash
# 检查 .env 中的 OSS 配置
grep OSS .env

# 确保以下变量都已设置：
# OSS_ENDPOINT
# OSS_BUCKET
# OSS_ACCESS_KEY_ID
# OSS_ACCESS_KEY_SECRET
```

---

## 📞 获取帮助

### 查看日志

```bash
# 后端日志
tail -f backend/logs/app.log

# Worker 日志
tail -f backend/worker.log

# 前端日志（在浏览器控制台）
```

### 检查系统状态

```bash
# 健康检查
curl http://localhost:8000/api/v1/monitoring/health

# 系统统计
curl http://localhost:8000/api/v1/monitoring/stats

# Celery 状态
curl http://localhost:8000/api/v1/monitoring/celery/inspect
```

### 联系支持

- 📧 Email: support@example.com
- 💬 GitHub Issues: https://github.com/your-repo/issues
- 📖 在线文档: http://localhost:8000/api/v1/docs

---

## 🎓 学习资源

### 视频教程（TODO）
- [ ] 系统安装和配置
- [ ] 创建第一个任务
- [ ] 理解处理流程
- [ ] 声音复刻使用技巧

### 示例项目
- 查看 `backend/examples/` 目录
- 查看 `tests/` 目录

### API 使用示例

**Python**:
```python
import requests

# 创建任务
with open('video.mp4', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/tasks',
        files={'video': f},
        data={
            'source_language': 'zh',
            'target_language': 'en',
            'title': '测试视频'
        }
    )
    task = response.json()
    print(f"任务已创建: {task['id']}")
```

**JavaScript**:
```javascript
const formData = new FormData();
formData.append('video', fileInput.files[0]);
formData.append('source_language', 'zh');
formData.append('target_language', 'en');

const response = await fetch('http://localhost:8000/api/v1/tasks', {
  method: 'POST',
  body: formData
});

const task = await response.json();
console.log('任务已创建:', task.id);
```

---

## 🛣️ 下一步

### 新手推荐路径

1. ✅ 启动系统（你在这里）
2. 📖 阅读 [QUICKSTART.md](QUICKSTART.md)
3. 🎬 创建第一个测试任务
4. 📊 查看任务处理过程
5. 📥 下载配音结果
6. 🔍 探索 [API 文档](http://localhost:8000/api/v1/docs)

### 开发者路径

1. ✅ 启动系统
2. 🏗️ 阅读 [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)
3. 🔧 查看后端代码 `backend/app/`
4. 🎨 查看前端代码 `frontend/app/`
5. 📝 阅读 API 文档
6. 🧪 编写测试用例

### 运维路径

1. ✅ 启动系统
2. 🐳 学习 Docker Compose 配置
3. 📋 阅读部署文档
4. 🔍 配置监控和日志
5. 🔐 实施安全措施
6. 🚀 执行生产部署

---

## ✨ 特性亮点

### 1. 智能处理
- 🎯 自动说话人识别
- 🗣️ 多说话人声音复刻
- 🌐 上下文感知翻译
- ⚡ 并行任务处理

### 2. 用户友好
- 🖱️ 拖拽上传
- 📊 实时进度显示
- 🔄 自动状态刷新
- 📥 一键下载结果

### 3. 企业级
- 🔐 安全的文件存储
- 📈 完整的监控系统
- 🔧 灵活的配置选项
- 📊 详细的日志记录

---

## 🎉 开始使用吧！

现在你已经准备好了！

1. 确保所有服务都在运行
2. 访问 http://localhost:3000
3. 上传你的第一个视频
4. 体验自动配音的魔力！

**祝使用愉快！** 🚀

---

**系统版本**: 2.0.0
**文档更新**: 2026-02-02
**下一次更新**: 有新功能时会通知你 😊
