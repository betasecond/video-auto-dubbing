# 视频自动配音系统 (DeepV)

> **[English](README_EN.md) | [中文](README.md)**
>
> **更新时间：2026年2月** | **架构：Python (FastAPI) + Next.js**

这是一个高性能的视频本地化系统，能够自动将视频配音翻译成其他语言。系统结合了先进的 ASR（语音识别）、LLM（大模型翻译）和实时声音复刻 TTS 技术，生成高质量、唇形与时间轴对齐的配音视频。

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

### 准备工作
*   Docker & Docker Compose v2
*   阿里云百炼 (DashScope) API Key (用于 ASR, LLM, TTS)
*   阿里云 OSS (对象存储)

### 1. 克隆与配置
```bash
git clone <repository_url> video-auto-dubbing
cd video-auto-dubbing

# 复制环境变量模板
cp .env.example .env
```

### 2. 设置环境变量
编辑 `.env` 文件，填入你的密钥：
```ini
# 阿里云百炼 (DashScope)
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 阿里云 OSS (用于文件存储)
OSS_ACCESS_KEY_ID=LTAIxxxxxxxx
OSS_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxx
OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
OSS_BUCKET=your-bucket-name
```

### 3. 启动系统
```bash
docker compose up -d
```
启动后访问管理后台：**http://localhost:3000**

---

## 📚 文档中心

### 入门指南
*   **[新手必读](docs/guide/start-here.md)**：项目路线图与快速指引。
*   **[详细部署指南](docs/guide/quickstart.md)**：完整的安装与环境配置说明。

### 架构与设计
*   **[系统概览](docs/architecture/system-overview.md)**：高层架构图与组件说明。
*   **[核心优化报告](docs/architecture/optimization.md)**：深入解析声音复刻与音画对齐算法。

### 开发手册
*   **[前端开发指南](docs/guide/frontend.md)**：Next.js 项目结构与组件说明。
*   **[API 文档](docs/api/backend-api.md)**：后端 REST API 接口定义。

---

## 🛠 本地开发

### 后端 (Python)
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

### 前端 (Next.js)
```bash
cd frontend
npm install
npm run dev
```

### 服务诊断
运行内置的诊断工具，检查所有云服务连接状态：
```bash
cd backend
python scripts/check_services.py
```

---

## 📄 开源协议
MIT License.
