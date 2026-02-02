# 前端部署指南

视频自动配音系统前端 - 生产部署文档

## 部署方式

### 方式 1: Docker 部署（推荐）

#### 1. 构建镜像

```bash
cd frontend

# 构建生产镜像
docker build -t video-dubbing-frontend:latest .
```

#### 2. 运行容器

```bash
docker run -d \
  --name video-dubbing-frontend \
  -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://your-backend-url:8000/api/v1 \
  video-dubbing-frontend:latest
```

#### 3. 使用 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000/api/v1
    depends_on:
      - backend
    restart: unless-stopped
```

运行：
```bash
docker-compose up -d frontend
```

### 方式 2: Node.js 部署

#### 1. 安装依赖

```bash
cd frontend
npm install --production
```

#### 2. 构建应用

```bash
# 设置环境变量
export NEXT_PUBLIC_API_URL=http://your-backend-url:8000/api/v1

# 构建
npm run build
```

#### 3. 启动服务

```bash
# 生产模式
npm run start
```

#### 4. 使用 PM2（推荐）

```bash
# 安装 PM2
npm install -g pm2

# 启动应用
pm2 start npm --name "video-dubbing-frontend" -- start

# 设置开机自启
pm2 startup
pm2 save

# 查看日志
pm2 logs video-dubbing-frontend

# 重启
pm2 restart video-dubbing-frontend

# 停止
pm2 stop video-dubbing-frontend
```

### 方式 3: Vercel 部署

#### 1. 连接 GitHub

1. 访问 [Vercel Dashboard](https://vercel.com/dashboard)
2. 点击 "New Project"
3. 导入 GitHub 仓库

#### 2. 配置环境变量

在 Vercel 项目设置中添加：

```
NEXT_PUBLIC_API_URL=https://your-backend-url.com/api/v1
```

#### 3. 部署

Vercel 会自动构建和部署：
- `main` 分支自动部署到生产环境
- Pull Request 自动创建预览环境

### 方式 4: Nginx 反向代理

#### 1. Next.js 应用配置

```bash
# 构建并启动 Next.js
npm run build
npm run start -- -p 3000
```

#### 2. Nginx 配置

```nginx
# /etc/nginx/sites-available/video-dubbing

upstream nextjs_upstream {
  server localhost:3000;
}

server {
  listen 80;
  server_name your-domain.com;

  # 客户端最大上传大小
  client_max_body_size 500M;

  # Next.js 应用
  location / {
    proxy_pass http://nextjs_upstream;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  # 静态资源缓存
  location /_next/static {
    proxy_pass http://nextjs_upstream;
    add_header Cache-Control "public, max-age=31536000, immutable";
  }

  # 图片缓存
  location ~* \.(jpg|jpeg|png|gif|ico|svg|webp)$ {
    proxy_pass http://nextjs_upstream;
    add_header Cache-Control "public, max-age=86400";
  }

  # Gzip 压缩
  gzip on;
  gzip_vary on;
  gzip_proxied any;
  gzip_comp_level 6;
  gzip_types text/plain text/css text/xml text/javascript
             application/json application/javascript application/xml+rss;
}
```

#### 3. 启用配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/video-dubbing /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

#### 4. HTTPS 配置（使用 Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

## 环境变量

### 必需配置

```bash
# API 后端地址
NEXT_PUBLIC_API_URL=http://your-backend-url:8000/api/v1
```

### 可选配置

```bash
# Node 环境
NODE_ENV=production

# 端口
PORT=3000

# API 代理（如果使用 rewrites）
API_URL=http://localhost:8000
```

## 性能优化

### 1. 构建优化

```bash
# 分析包大小
npm run build
npx @next/bundle-analyzer
```

### 2. 缓存策略

在 `next.config.js` 中配置：

```javascript
module.exports = {
  // 启用 SWC 压缩
  swcMinify: true,

  // 图片优化
  images: {
    domains: ['your-oss-domain.com'],
    formats: ['image/avif', 'image/webp'],
  },

  // 压缩
  compress: true,

  // 生成 Etag
  generateEtags: true,

  // HTTP 头部
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          }
        ]
      }
    ]
  }
}
```

### 3. CDN 配置

使用 Vercel CDN 或其他 CDN 服务：

```javascript
// next.config.js
module.exports = {
  assetPrefix: process.env.CDN_URL || '',
}
```

## 监控和日志

### 1. 应用监控

使用 Sentry 进行错误监控：

```bash
npm install @sentry/nextjs
```

```javascript
// sentry.client.config.js
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 1.0,
});
```

### 2. 日志收集

使用 Winston 或 Pino：

```bash
npm install pino pino-pretty
```

### 3. 性能监控

使用 Next.js 内置的 Web Vitals：

```javascript
// pages/_app.tsx
export function reportWebVitals(metric) {
  console.log(metric)
  // 发送到分析服务
}
```

## 安全配置

### 1. 环境变量安全

- 不要在客户端代码中使用敏感信息
- 使用 `NEXT_PUBLIC_` 前缀的变量会暴露给客户端
- 敏感配置使用服务端环境变量

### 2. CSP (Content Security Policy)

```javascript
// next.config.js
const cspHeader = `
  default-src 'self';
  script-src 'self' 'unsafe-eval' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  img-src 'self' blob: data: https:;
  font-src 'self';
  connect-src 'self' ${process.env.NEXT_PUBLIC_API_URL};
  frame-ancestors 'none';
`

module.exports = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: cspHeader.replace(/\n/g, ''),
          },
        ],
      },
    ]
  },
}
```

### 3. 速率限制

在 Nginx 层面配置：

```nginx
# 限制每个 IP 的请求速率
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api {
  limit_req zone=api burst=20 nodelay;
  proxy_pass http://nextjs_upstream;
}
```

## 健康检查

创建健康检查端点：

```typescript
// app/api/health/route.ts
export async function GET() {
  return Response.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
  })
}
```

Kubernetes 健康检查配置：

```yaml
livenessProbe:
  httpGet:
    path: /api/health
    port: 3000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /api/health
    port: 3000
  initialDelaySeconds: 5
  periodSeconds: 5
```

## 回滚策略

### Docker 部署回滚

```bash
# 查看镜像历史
docker images

# 回滚到之前的版本
docker stop video-dubbing-frontend
docker run -d \
  --name video-dubbing-frontend \
  -p 3000:3000 \
  video-dubbing-frontend:previous-tag
```

### Vercel 回滚

1. 访问 Vercel Dashboard
2. 选择项目
3. 在 Deployments 中选择之前的版本
4. 点击 "Promote to Production"

### PM2 回滚

```bash
# 停止当前版本
pm2 stop video-dubbing-frontend

# 切换到之前的代码版本
git checkout previous-tag

# 重新构建和启动
npm run build
pm2 restart video-dubbing-frontend
```

## 故障排除

### 构建失败

1. 清除缓存：`rm -rf .next node_modules`
2. 重新安装：`npm install`
3. 检查 Node.js 版本：`node -v`（需要 >= 18）

### 运行时错误

1. 检查环境变量是否正确设置
2. 查看浏览器控制台错误
3. 检查后端 API 是否可访问

### 性能问题

1. 使用 Lighthouse 分析性能
2. 检查网络请求瀑布图
3. 优化大型依赖包
4. 启用代码分割

## 备份和恢复

### 配置备份

```bash
# 备份环境变量
cp .env.local .env.local.backup

# 备份 Next.js 配置
cp next.config.js next.config.js.backup
```

### 数据恢复

前端不存储持久化数据，只需恢复配置文件即可。

## 更新流程

### 零停机更新

使用 PM2 集群模式：

```bash
# 启动集群
pm2 start npm --name "video-dubbing-frontend" -i 4 -- start

# 重新加载（零停机）
pm2 reload video-dubbing-frontend
```

### 蓝绿部署

1. 部署新版本到备用环境
2. 测试新版本
3. 切换 Load Balancer 指向新版本
4. 保留旧版本用于快速回滚

## 检查清单

部署前检查：

- [ ] 所有环境变量已配置
- [ ] API 端点可访问
- [ ] 构建成功
- [ ] 静态资源正确加载
- [ ] HTTPS 配置正确
- [ ] 监控和日志已配置
- [ ] 备份策略已实施
- [ ] 回滚计划已准备

## 联系支持

- 📧 Email: support@example.com
- 💬 GitHub Issues: https://github.com/your-repo/issues
- 📖 文档: https://your-docs-site.com
