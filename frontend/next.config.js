/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,

  // API 代理配置
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/:path*',
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
