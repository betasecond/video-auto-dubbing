# 快速启动指南

> 更新日期：2026-01-11｜适用分支：main

本文档采用 UTF-8 保存，是视频本地化自动配音系统的唯一权威快速启动说明；从环境准备到常见问题的指令均以此为准。需要更多背景可查阅 `docs/README.md` 的文档索引。

## 1. 前置要求

- Docker Engine 20.10+，Docker Compose v2（如无 v2，可使用 `docker-compose` v1）
- 至少 8GB 内存、50GB 可用磁盘；首次启动需联网拉取镜像和模型
- 默认 TTS 依赖 NVIDIA GPU（IndexTTS-2 推理）。如无 GPU，可在 `.env` 中设 `INDEXTTS_DEVICE=cpu`，性能会明显下降并需确保容器仍可启动

## 2. 获取代码

```bash
git clone <repository-url>
cd vedio
```

## 3. 一键 Docker 部署（推荐）

```bash
bash scripts/bootstrap.sh
```

脚本会：
- 如不存在 `.env`，自动复制 `env.example`；
- 预下载 IndexTTS-2 与 Moonshine ASR 模型到持久卷；
- 自动选择 `docker compose` 或 `docker-compose`；
- 执行 `up -d --build` 并展示服务状态。

在执行前请先在 `.env` 填好真实的 `GLM_API_KEY`，否则翻译步骤会失败。

## 4. 手动准备（如不使用一键脚本）

### 4.1 配置环境变量

从 `env.example` 复制到 `.env` 后，至少确认以下键：
- `GLM_API_KEY`：必填，真实 GLM 翻译密钥。
- `GLM_API_URL`、`GLM_MODEL`、`GLM_RPS`：保持默认即可，特殊配额再调整。
- `HF_ENDPOINT`：默认 `https://hf-mirror.com`，国内建议保留或替换为可用镜像。
- `MINIO_PUBLIC_ENDPOINT`：需要公网下发下载链接时填写公网 `host:9000`。
- `TTS_PORT`、`API_PORT` 等：端口冲突时重写。
- `INDEXTTS_DEVICE`：默认 `auto`（优先 GPU），无 GPU 时设为 `cpu`；`ASR_DEVICE` 默认 `cuda`/`cpu` 可按实际硬件调整。

### 4.2 下载 IndexTTS-2 模型权重（必需）

```bash
docker compose run --rm tts_service python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='IndexTeam/IndexTTS-2', local_dir='/app/models/IndexTTS-2', local_dir_use_symlinks=False)"
```

如需使用镜像站，请在命令前设置 `HF_ENDPOINT` 或在 `.env` 中配置。

### 4.3 离线分发（可选）

- 导出：`bash scripts/export_tts_model_bundle.sh`
- 导入：`bash scripts/import_tts_model_bundle.sh <bundle.tar.gz | https://...>`

详见：`docs/offline-assets.md`。

### 4.4 预拉取 Moonshine ASR 模型（可选）

```bash
docker compose run --rm asr_service python -c "import os, moonshine_onnx; moonshine_onnx.MoonshineOnnxModel(model_name=os.environ.get('ASR_MODEL_ID','moonshine/tiny')); print('Moonshine ASR model ready')"
```

## 5. 启动与验证

```bash
# 启动全部服务
docker compose up -d

# 查看状态
docker compose ps

# 查看日志（可选）
docker compose logs -f
```

服务入口（远程部署请将 `localhost` 换成服务器地址，并在 `.env` 设置 `MINIO_PUBLIC_ENDPOINT=<公网IP:9000>` 以生成可访问的下载链接）：

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| 网关/前端 | http://localhost | 通过 NGINX 访问内置 UI（`web/dist`） |
| API | http://localhost:8080 | REST 接口 `/api/v1`（端口由 `API_PORT` 控制） |
| ASR | http://localhost:8002 | Moonshine ASR（`ASR_PORT`） |
| TTS | http://localhost:8001 | 语音合成健康检查 `/health`，端口由 `TTS_PORT` 控制 |
| MinIO 控制台 | http://localhost:9001 | 对象存储管理 |
| RabbitMQ 控制台 | http://localhost:15672 | 消息队列管理 |
| PostgreSQL | localhost:5432 | 数据库 |

## 6. 真实 E2E 测试（10 秒示例）

```bash
# 生成示例视频（首次运行会拉取 ffmpeg 镜像）
bash scripts/prepare_test_video.sh

# 运行 E2E（需已配置 GLM_API_KEY）
GLM_API_KEY=你的真实Key bash scripts/e2e_test.sh
```

默认使用 `test_vedio/test_video_10s.mp4`，如需自定义：`TEST_VIDEO=... SOURCE_LANGUAGE=zh TARGET_LANGUAGE=en bash scripts/e2e_test.sh`。

## 7. 常见问题

1. **Docker 未启动**：报错 `error during connect: open //./pipe/docker_engine...`，请先启动 Docker Desktop（Windows 可执行 `Start-Service com.docker.service`），再运行 `docker version` 确认 Server 正常。
2. **端口冲突**：提示 `port is already allocated`，使用 `docker ps --format "table {{.Names}}\t{{.Ports}}"` 排查后，调整 `.env` 中的 `API_PORT`/`TTS_PORT`/`ASR_PORT` 或停止占用端口的容器。
3. **模型下载缓慢/失败**：确认网络可达 HuggingFace，或在 `.env` 中设置 `HF_ENDPOINT` 为可用镜像；必要时使用离线导入脚本。
4. **无 GPU 环境 TTS 启动失败**：默认 compose 使用 `runtime: nvidia`。无 GPU 时请将 `INDEXTTS_DEVICE=cpu` 并确保本机 Docker 支持 CPU 运行（如需，临时移除 compose 中的 `runtime` 配置后再启动）。
5. **GLM 未配置**：`GLM_API_KEY` 未填会导致翻译失败，务必在 `.env` 或执行命令时设置真实密钥。

## 8. 停止、重启与重建

```bash
# 停止但保留数据
docker compose stop

# 停止并删除容器（保留数据卷）
docker compose down

# 完全清理（含数据卷）
docker compose down -v

# 重启全部或指定服务
docker compose restart
# docker compose restart api
# docker compose restart worker

# 重新构建并启动
docker compose up -d --build
# 或仅重建指定服务
docker compose up -d --build api
```

## 9. 开发模式提示

- Go（API/Worker）：修改代码后执行 `docker compose up -d --build api` 或 `worker` 触发重建；使用 bind mount 时避免覆盖镜像内的构建产物。
- Python（TTS）：修改代码后运行 `docker compose up -d --build tts_service`；如需调试依赖，谨慎挂载 `.venv` 以防依赖失效。

## 10. 相关文档

- [文档索引](./README.md) — 架构、接口与开发规范入口
- [系统架构设计](architecture.md)
- [部署指南](deployment.md)
- [API 合同](api-contracts.md)
- [ASR 服务说明](asr-service.md)
- [TTS 服务说明](tts-service.md)
