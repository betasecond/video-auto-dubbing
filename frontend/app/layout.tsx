import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Providers from './providers'
import Link from 'next/link'
import { Video, Github, Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: '视频自动配音系统 - AI 驱动的多语言视频本地化',
  description: '基于阿里百炼平台的智能视频配音系统，支持多语言翻译、声音复刻、多说话人识别',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" className="scroll-smooth">
      <body className={inter.className}>
        <Providers>
          <div className="min-h-screen flex flex-col bg-background">
            {/* Header */}
            <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
              <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                <Link href="/" className="flex items-center gap-2 font-bold text-xl hover:opacity-80 transition-opacity">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center">
                    <Video className="w-5 h-5 text-white" />
                  </div>
                  <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
                    视频配音 AI
                  </span>
                </Link>

                <nav className="hidden md:flex items-center gap-6">
                  <Link href="/" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                    首页
                  </Link>
                  <Link href="/tasks" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                    我的任务
                  </Link>
                  <Link href="/tasks/new">
                    <Button size="sm" className="rounded-full">
                      开始配音
                    </Button>
                  </Link>
                </nav>

                {/* Mobile menu button */}
                <div className="md:hidden">
                  <Link href="/tasks/new">
                    <Button size="sm">开始</Button>
                  </Link>
                </div>
              </div>
            </header>

            {/* Main content */}
            <main className="flex-1">
              {children}
            </main>

            {/* Footer */}
            <footer className="border-t bg-slate-50">
              <div className="container mx-auto px-4 py-12">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                  {/* Brand */}
                  <div className="col-span-1 md:col-span-2">
                    <Link href="/" className="flex items-center gap-2 font-bold text-xl mb-4">
                      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center">
                        <Video className="w-5 h-5 text-white" />
                      </div>
                      <span>视频配音 AI</span>
                    </Link>
                    <p className="text-sm text-muted-foreground mb-4 max-w-sm">
                      基于阿里云百炼平台的智能视频配音系统，让跨语言视频制作变得简单高效。
                    </p>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="icon" asChild>
                        <a href="https://github.com" target="_blank" rel="noopener noreferrer">
                          <Github className="w-5 h-5" />
                        </a>
                      </Button>
                      <Button variant="ghost" size="icon" asChild>
                        <a href="mailto:support@example.com">
                          <Mail className="w-5 h-5" />
                        </a>
                      </Button>
                    </div>
                  </div>

                  {/* Links */}
                  <div>
                    <h3 className="font-semibold mb-4">产品</h3>
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      <li>
                        <Link href="/tasks/new" className="hover:text-foreground transition-colors">
                          开始配音
                        </Link>
                      </li>
                      <li>
                        <Link href="/tasks" className="hover:text-foreground transition-colors">
                          任务列表
                        </Link>
                      </li>
                    </ul>
                  </div>

                  {/* Support */}
                  <div>
                    <h3 className="font-semibold mb-4">支持</h3>
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      <li>
                        <a href="http://localhost:8000/api/v1/docs" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">
                          API 文档
                        </a>
                      </li>
                      <li>
                        <a href="mailto:support@example.com" className="hover:text-foreground transition-colors">
                          联系我们
                        </a>
                      </li>
                    </ul>
                  </div>
                </div>

                <div className="mt-8 pt-8 border-t text-center text-sm text-muted-foreground">
                  <p>© 2026 视频配音 AI. All rights reserved. Powered by 阿里云百炼平台.</p>
                </div>
              </div>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  )
}
