# TTS服务精简计划

## 现状分析
- 当前大小：2.0M，140个Python文件，34个目录
- 最大组件：`indextts/` (1.9M) 包含完整的IndexTTS2推理代码
- API层：`app/` (60K) 包含FastAPI接口

## 精简策略

### 保留组件（用于远程部署）
1. **app/** - FastAPI应用核心
2. **pyproject.toml** - 依赖管理
3. **Dockerfile** - 容器构建
4. **README.md** - 部署说明

### 移除组件（庞大且可替代）
1. **indextts/** - 1.9M的推理代码
   - 可通过pip安装 `indextts` 或 `index-tts-vllm`
   - 不需要在源码中携带

### 替代方案
- 使用 `index-tts-vllm` 替代自带的 `indextts/`
- 简化依赖，仅保留API服务必需的包

## 执行步骤
1. 备份完整的 `indextts/` 到 `backup/`
2. 移除 `indextts/` 目录
3. 更新 `pyproject.toml` 改为外部依赖
4. 更新 `app/` 中的import路径
5. 创建简化版部署说明

## 预期收益
- 大小减少：2.0M → 0.1M (减少95%)
- 文件数：140个 → 15个左右
- 维护成本大幅降低