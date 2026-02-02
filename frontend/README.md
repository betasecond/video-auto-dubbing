# Video Dubbing Frontend

视频自动配音系统前端 - Next.js 14 App Router

## 技术栈

- **框架**: Next.js 14 (App Router)
- **语言**: TypeScript
- **样式**: Tailwind CSS
- **状态管理**: SWR (数据获取与缓存)
- **表单**: React Hook Form + Zod
- **UI 组件**: Radix UI + Lucide Icons
- **HTTP 客户端**: Axios

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置环境变量

```bash
cp .env.local.example .env.local
# 编辑 .env.local 设置后端 API 地址
```

### 3. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

## 项目结构

```
frontend/
├── app/
│   ├── tasks/
│   │   ├── [id]/           # 任务详情页
│   │   │   └── page.tsx
│   │   ├── new/            # 创建任务页
│   │   │   └── page.tsx
│   │   └── page.tsx        # 任务列表页
│   ├── globals.css         # 全局样式
│   ├── layout.tsx          # 根布局
│   ├── page.tsx            # 首页
│   └── providers.tsx       # 全局 Provider
├── components/
│   └── ui/                 # UI 组件库
├── lib/
│   └── api.ts              # API 客户端
├── public/                 # 静态资源
├── .env.local              # 环境变量
├── next.config.js          # Next.js 配置
├── tailwind.config.ts      # Tailwind 配置
└── tsconfig.json           # TypeScript 配置
```

## 功能特性

### 1. 首页
- 产品介绍
- 功能特点展示
- 快速导航

### 2. 创建任务页 (`/tasks/new`)
- 📤 文件上传（支持拖拽）
- 🌍 语言选择（源语言和目标语言）
- ✍️ 自定义任务标题
- ✅ 文件验证（类型、大小）
- 💡 处理流程说明

### 3. 任务列表页 (`/tasks`)
- 📋 分页任务列表
- 🔄 自动刷新（每 3 秒）
- 🔍 状态过滤（全部、进行中、已完成等）
- 📊 任务进度显示
- 🎨 状态标签（不同颜色）

### 4. 任务详情页 (`/tasks/{id}`)
- 📈 实时进度监控（自动刷新）
- 📝 完整的任务信息
- 📦 分段详情列表
- 🎤 说话人和声音复刻信息
- 📥 下载结果按钮
- 🗑️ 删除任务功能
- ⚠️ 错误提示

## API 集成

API 客户端位于 `lib/api.ts`，提供以下功能：

```typescript
// 创建任务
const task = await createTask(file, 'zh', 'en', '我的任务');

// 获取任务列表
const { items, total } = await getTasks(page, pageSize, status);

// 获取任务详情
const task = await getTask(taskId);

// 删除任务
await deleteTask(taskId);

// 获取下载链接
const { download_url } = await getDownloadUrl(taskId);

// 健康检查
const health = await checkHealth();

// 系统统计
const stats = await getStats();
```

## 数据刷新策略

使用 SWR 实现智能数据刷新：

1. **任务列表页**
   - 每 3 秒自动刷新
   - 切换标签页时重新验证

2. **任务详情页**
   - 未完成任务：每 2 秒刷新
   - 已完成/失败任务：停止自动刷新

## 开发指南

### 代码风格

```bash
# 检查代码
npm run lint

# 类型检查
npm run type-check
```

### 构建部署

```bash
# 生产构建
npm run build

# 启动生产服务器
npm run start
```

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `NEXT_PUBLIC_API_URL` | 后端 API 地址 | `http://localhost:8000/api/v1` |

## 页面路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 首页 | 产品介绍和导航 |
| `/tasks` | 任务列表 | 查看所有任务 |
| `/tasks/new` | 创建任务 | 上传视频并创建配音任务 |
| `/tasks/{id}` | 任务详情 | 查看任务进度和结果 |

## UI 组件

使用 Radix UI 作为无障碍 UI 基础：

- Dialog - 对话框
- Select - 下拉选择
- Progress - 进度条
- Toast - 消息提示（预留）
- Label - 表单标签
- Switch - 开关（预留）
- Tabs - 标签页（预留）

使用 Lucide React 图标库：

- Upload - 上传
- Download - 下载
- Trash2 - 删除
- RefreshCw - 刷新
- ArrowLeft - 返回
- Plus - 新增
- Filter - 过滤
- ... 等

## 错误处理

1. **网络错误**
   - 显示友好的错误提示
   - 提供重试按钮

2. **表单验证**
   - 实时验证文件类型和大小
   - 验证语言选择

3. **API 错误**
   - 统一的错误拦截
   - 错误消息显示

## 性能优化

1. **代码分割**
   - Next.js 自动代码分割
   - 按路由懒加载

2. **数据缓存**
   - SWR 自动缓存
   - 智能重新验证

3. **图片优化**
   - Next.js Image 组件（如需使用）

4. **字体优化**
   - 使用 Next.js Font 优化

## 待实现功能

- [ ] 用户认证
- [ ] 批量任务创建
- [ ] 任务搜索功能
- [ ] 导出任务报告
- [ ] 暗色模式
- [ ] 多语言界面
- [ ] WebSocket 实时通知
- [ ] 任务克隆功能
- [ ] 高级过滤器

## 故障排除

### 无法连接后端

1. 检查后端服务是否运行：`http://localhost:8000/health`
2. 检查 `.env.local` 中的 API 地址
3. 检查 CORS 配置

### 文件上传失败

1. 检查文件大小（最大 500MB）
2. 检查文件格式（MP4, AVI, MOV, MKV, FLV）
3. 查看浏览器控制台错误信息

### 任务状态不更新

1. 检查 Celery Worker 是否运行
2. 检查 Redis 连接
3. 查看后端日志

## 许可证

MIT License

## 支持

- 📧 Email: support@example.com
- 💬 GitHub Issues: https://github.com/your-repo/issues
- 📖 API 文档: http://localhost:8000/api/v1/docs
