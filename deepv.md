# DeepV Project Context & Guidelines

## Environment Management
- **Python**: We use `uv` for Python package and environment management.
  - Use `uv venv` to create virtual environments.
  - Use `uv pip install` for package installation.
  - Use `uv run` to execute scripts in the environment.

## Project Architecture
- **Backend**: Python FastAPI (`backend/`)
- **Frontend**: Next.js 14 (`frontend/`)
- **Infrastructure**: Docker Compose, PostgreSQL, Redis, Aliyun OSS
- **AI Services**: Aliyun DashScope (ASR, LLM, TTS)

## Refactoring Status (as of Feb 2026)
- Transitioning from local GPU inference to Aliyun DashScope APIs.
- Backend core implemented (FastAPI).
- Frontend integration in progress.

# 我没有让你写文档的时候不要写文档，不要写文档，不要写文档