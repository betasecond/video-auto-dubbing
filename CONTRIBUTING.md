# Contributing Guide

Thank you for your interest in the DeepV project! This document will help you understand how to participate in development.

## Quick Start

1. **Fork the project** and clone it locally.
2. **Read the documentation**:
   - [Start Here](docs/guide/start-here.md)
   - [Backend API](docs/api/backend-api.md)
   - [Frontend Guide](docs/guide/frontend.md)
3. **Set up the development environment** (see below).
4. **Create a feature branch** and start coding.
5. **Submit a Pull Request**.

## Environment Setup

### Prerequisites

- **Python**: 3.11+ (Managed by `uv`)
- **Node.js**: 18+ (LTS)
- **Docker**: 20.10+ (For running services like Redis/PostgreSQL locally)

### Backend (Python)

We use `uv` for dependency management.

```bash
cd backend
# Install dependencies
uv sync

# Run development server
uv run uvicorn app.main:app --reload
```

### Frontend (Next.js)

We use `npm` for the frontend.

```bash
cd frontend
# Install dependencies
npm install

# Run development server
npm run dev
```

## Development Workflow

### 1. Create a Branch

```bash
# Update main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name
```

**Branch Naming Convention:**
- `feature/`: New features
- `fix/`: Bug fixes
- `refactor/`: Refactoring
- `docs/`: Documentation updates

### 2. Code Standards

- **Python**: We follow PEP 8. Use `ruff` for linting and formatting.
- **TypeScript**: We use `eslint` and `prettier`.

### 3. Running Checks

Before submitting code, please ensure all checks pass.

**Backend:**
```bash
cd backend
# Run linting
uv run ruff check .
# Run formatting
uv run ruff format .
# Run tests
uv run pytest
```

**Frontend:**
```bash
cd frontend
# Run linting
npm run lint
```

### 4. Commit Messages

Please follow the Conventional Commits specification:

```
<type>(<scope>): <subject>

<body>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.

### 5. Pull Request

1. Push your branch to remote.
2. Create a PR on GitHub.
3. Describe your changes clearly.
4. Wait for review.

## Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:
1. Description of the issue.
2. Steps to reproduce.
3. Expected behavior.
4. Actual behavior.
5. Environment details.

Thank you for your contribution!
