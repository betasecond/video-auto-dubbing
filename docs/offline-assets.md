# 离线资源与大文件分发（可选）

本项目默认不在 Git 仓库内提交模型权重、安装包等大文件（体积过大、下载慢、且部分文件可能涉及第三方分发许可）。推荐通过网络按需拉取，或用“离线模型包”在团队内部/云盘分发。

## 1) 推荐：通过网络拉取模型权重

TTS（IndexTTS-2）模型权重推荐从 HuggingFace 拉取到 Docker 卷（见 `docs/startup-guide.md` 的“下载 IndexTTS-2 模型权重”）。

国内网络可结合：
- `.env`：`HF_ENDPOINT=https://hf-mirror.com`
- `.env`：`HF_HUB_CACHE=/app/models/IndexTTS-2/hf_cache`

## 2) 团队内离线分发：导出/导入 IndexTTS-2 模型包

适用场景：内网/无外网环境、或者希望一次下载后多人复用。

### 2.1 导出（在已完成模型下载的机器上）

```bash
bash scripts/export_tts_model_bundle.sh
```

生成文件位于 `artifacts/`：
- `indextts2_models_YYYYMMDD_HHMMSS.tar.gz`
- `indextts2_models_YYYYMMDD_HHMMSS.tar.gz.sha256`

将这两个文件上传到团队网盘/对象存储即可。

### 2.2 导入（在目标机器上）

```bash
# 本地文件
bash scripts/import_tts_model_bundle.sh artifacts/indextts2_models_YYYYMMDD_HHMMSS.tar.gz

# 或从 URL 导入（需要 curl/wget）
bash scripts/import_tts_model_bundle.sh https://your-file-server/indextts2_models_YYYYMMDD_HHMMSS.tar.gz
```

导入完成后模型会恢复到 TTS 容器的模型卷内（`/app/models/IndexTTS-2`），无需再次从外网下载。

## 3) Windows 离线“安装包”说明

仓库内的 `index-tts-windows/` 已作为 submodule 记录 IndexTTS2 上游代码版本；其中的模型权重与运行环境不建议直接提交到主仓库。

如确需分发 Windows 端离线包，建议：
- 仅分发模型权重与必要配置（避免分发 NVIDIA/CUDA/VS 等安装包）
- 或使用 GitHub Releases/对象存储分发压缩包，并在文档中提供下载与校验步骤
