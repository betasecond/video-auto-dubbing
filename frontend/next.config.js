/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,

  // 优化包导入 (Rule 2.1)
  experimental: {
    optimizePackageImports: ['lucide-react', 'date-fns', 'lodash'],
  },

  // API 代理配置
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: process.env.API_URL
          ? `${process.env.API_URL}/api/v1/:path*`
          : 'http://localhost:8000/api/v1/:path*',
      },
    ];
  },

  // 图片优化
  images: {
    domains: [
      'localhost',
      'vedio-auto-tran.oss-cn-beijing.aliyuncs.com',
      // 添加你的 OSS 域名
    ],
  },

  // 输出配置
  output: 'standalone',
};

module.exports = nextConfig;
