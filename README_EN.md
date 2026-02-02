# Video Auto Dubbing System (DeepV)

> **[English](README_EN.md) | [中文](README.md)**
>
> **Updated: Feb 2026** | **Architecture: Python (FastAPI) + Next.js**

A high-performance video localization system that automatically dubs videos into other languages. It combines advanced ASR (Speech Recognition), LLM-based Translation, and Real-time Voice Cloning TTS to produce high-quality, lip-sync-aligned dubbed videos.

---

## 🌟 Key Features

*   **Real-time Voice Cloning**: Clones the original speaker's voice using **Aliyun Qwen3-TTS-VC**.
*   **Intelligent Audio Alignment**:
    *   **Isotonic Translation**: LLM prompts ensure translated text fits the original timeframe.
    *   **Smart Acceleration**: Automatically accelerates audio (up to 4x) to fit slots without overlap.
*   **High-Quality Translation**: Context-aware full-text translation using **Qwen-Turbo**.
*   **Modern Stack**:
    *   **Backend**: Python 3.11, FastAPI, Celery (Redis), SQLAlchemy.
    *   **Frontend**: Next.js 14, Tailwind CSS, shadcn/ui.
    *   **Infrastructure**: Docker Compose v2.

---

## 🚀 Quick Start

### Prerequisites
*   Docker & Docker Compose v2
*   Aliyun DashScope API Key (for ASR, LLM, TTS)
*   Aliyun OSS (Object Storage)

### 1. Clone & Configure
```bash
git clone <repository_url> video-auto-dubbing
cd video-auto-dubbing

# Copy environment template
cp .env.example .env
```

### 2. Set Environment Variables
Edit `.env` and fill in your credentials:
```ini
# Aliyun DashScope (Required for ASR, LLM, TTS)
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# Aliyun OSS (Required for file storage)
OSS_ACCESS_KEY_ID=LTAIxxxxxxxx
OSS_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxx
OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
OSS_BUCKET=your-bucket-name
```

### 3. Start System
```bash
docker compose up -d
```
Access the dashboard at **http://localhost:3000**.

---

## 📚 Documentation

### Getting Started
*   **[Start Here](docs/guide/start-here.md)**: Main entry point and project roadmap.
*   **[Quick Start Guide](docs/guide/quickstart.md)**: Detailed setup and deployment instructions.

### Architecture & Design
*   **[System Overview](docs/architecture/system-overview.md)**: High-level architecture and component diagrams.
*   **[Optimization Report](docs/architecture/optimization.md)**: Deep dive into voice cloning and audio alignment algorithms.

### Development
*   **[Frontend Guide](docs/guide/frontend.md)**: Next.js frontend structure and features.
*   **[API Documentation](docs/api/backend-api.md)**: Backend REST API specifications.

---

## 🛠 Development

### Backend (Python)
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```

### Diagnostics
Run the integrated service check tool to verify your connections:
```bash
cd backend
python scripts/check_services.py
```

---

## 📄 License
MIT License.
