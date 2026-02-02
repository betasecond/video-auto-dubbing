# Video Dubbing Backend

视频自动配音系统后端 - Python FastAPI 重构版

## 技术栈

- **Web 框架**: FastAPI + Uvicorn
- **数据库**: PostgreSQL + SQLAlchemy 2.0
- **任务队列**: Celery + Redis
- **AI 服务**: 阿里百炼 DashScope (ASR, LLM, TTS)
- **对象存储**: 阿里云 OSS
- **依赖管理**: uv

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv (推荐)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# 或使用 pip
pip install -e .
```

### 2. 配置环境变量

```bash
cp ../.env.example .env
# 编辑 .env 填写必要配置
```

### 3. 数据库迁移

```bash
# 初始化数据库
alembic upgrade head
```

### 4. 启动服务

```bash
# 启动 API 服务
uvicorn app.main:app --reload --port 8000

# 启动 Celery Worker
celery -A workers.celery_app worker --loglevel=info
```

## 开发

### 代码格式化

```bash
black .
ruff check --fix .
```

### 类型检查

```bash
mypy .
```

### 运行测试

```bash
pytest
```

## 项目结构

```
backend/
├── app/
│   ├── api/              # API 路由
│   ├── models/           # 数据库模型
│   ├── schemas/          # Pydantic 模型
│   ├── services/         # 业务逻辑
│   ├── core/             # 核心模块
│   └── integrations/     # 外部服务集成
├── workers/
│   ├── celery_app.py     # Celery 配置
│   ├── tasks.py          # 任务定义
│   └── steps/            # 处理步骤
├── migrations/           # 数据库迁移
└── tests/                # 测试
```

## API 文档

启动服务后访问: http://localhost:8000/api/v1/docs
