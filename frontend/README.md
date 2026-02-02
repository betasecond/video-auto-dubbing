# Video Dubbing Frontend

视频自动配音系统前端 - Next.js 14

## 技术栈

- **框架**: Next.js 14 (App Router)
- **UI**: Tailwind CSS + shadcn/ui
- **状态管理**: Zustand + React Query
- **表单**: React Hook Form + Zod
- **HTTP**: Axios

## 快速开始

### 1. 安装依赖

```bash
npm install
# 或
pnpm install
# 或
yarn install
```

### 2. 配置环境变量

```bash
cp .env.example .env.local
# 编辑 .env.local
```

### 3. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

## 开发

### 代码检查

```bash
npm run lint
npm run type-check
```

### 构建生产版本

```bash
npm run build
npm start
```

## 项目结构

```
frontend/
├── app/
│   ├── layout.tsx        # 根布局
│   ├── page.tsx          # 首页
│   ├── tasks/            # 任务相关页面
│   └── api/              # API Routes
├── components/
│   ├── ui/               # shadcn/ui 组件
│   └── ...               # 业务组件
├── lib/
│   ├── api.ts            # API 客户端
│   ├── utils.ts          # 工具函数
│   └── hooks/            # 自定义 Hook
└── public/               # 静态资源
```

## 页面路由

- `/` - 首页
- `/tasks` - 任务列表
- `/tasks/new` - 创建任务
- `/tasks/[id]` - 任务详情
