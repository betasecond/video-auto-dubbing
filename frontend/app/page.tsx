import Link from 'next/link';
import { ArrowRight, Video, Mic, Languages, Sparkles, Zap, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="relative flex-1 flex flex-col items-center justify-center text-center px-4 py-20 overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 -z-10" />
        <div className="absolute inset-0 bg-grid-slate-100 [mask-image:linear-gradient(0deg,white,rgba(255,255,255,0.6))] -z-10" />

        <div className="max-w-4xl space-y-8 relative">
          {/* Badge */}
          <div className="flex justify-center">
            <Badge variant="secondary" className="px-4 py-2 text-sm">
              <Sparkles className="w-4 h-4 mr-2" />
              Powered by 阿里云百炼平台
            </Badge>
          </div>

          {/* Main heading */}
          <h1 className="text-5xl sm:text-7xl font-black tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600">
            视频自动配音
          </h1>

          <p className="text-xl sm:text-2xl text-slate-600 max-w-3xl mx-auto font-medium">
            一键将视频翻译并配音成多种语言
          </p>

          <p className="text-lg text-slate-500 max-w-2xl mx-auto">
            利用先进的 ASR、LLM 和 TTS 技术，实现专业级的跨语言视频本地化
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Button asChild size="lg" className="text-lg px-8 py-6 rounded-full shadow-lg hover:shadow-xl transition-all">
              <Link href="/tasks/new">
                <Video className="w-5 h-5 mr-2" />
                开始配音
                <ArrowRight className="w-5 h-5 ml-2" />
              </Link>
            </Button>

            <Button asChild variant="outline" size="lg" className="text-lg px-8 py-6 rounded-full">
              <Link href="/tasks">
                我的任务
              </Link>
            </Button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-8 pt-12 max-w-2xl mx-auto">
            <div>
              <div className="text-3xl font-bold text-blue-600">8+</div>
              <div className="text-sm text-slate-600">支持语言</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-indigo-600">AI</div>
              <div className="text-sm text-slate-600">智能处理</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-purple-600">5步</div>
              <div className="text-sm text-slate-600">自动完成</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-4">
              强大的功能特性
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              基于阿里云百炼平台，提供企业级的视频配音解决方案
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            <FeatureCard
              icon={<Video className="w-8 h-8" />}
              iconColor="text-blue-600"
              iconBg="bg-blue-100"
              title="自动提取"
              description="智能分离视频音轨，精确识别语音内容和时间轴"
            />
            <FeatureCard
              icon={<Languages className="w-8 h-8" />}
              iconColor="text-indigo-600"
              iconBg="bg-indigo-100"
              title="智能翻译"
              description="Qwen3 大模型提供上下文感知的高质量翻译"
            />
            <FeatureCard
              icon={<Mic className="w-8 h-8" />}
              iconColor="text-purple-600"
              iconBg="bg-purple-100"
              title="声音复刻"
              description="CosyVoice 技术完美克隆原声，保持情感和语调"
            />
            <FeatureCard
              icon={<Zap className="w-8 h-8" />}
              iconColor="text-yellow-600"
              iconBg="bg-yellow-100"
              title="快速处理"
              description="并行任务队列，支持多视频同时处理"
            />
            <FeatureCard
              icon={<Sparkles className="w-8 h-8" />}
              iconColor="text-pink-600"
              iconBg="bg-pink-100"
              title="多说话人"
              description="自动识别并为每个说话人分配独立的声音"
            />
            <FeatureCard
              icon={<Shield className="w-8 h-8" />}
              iconColor="text-green-600"
              iconBg="bg-green-100"
              title="安全可靠"
              description="企业级安全保障，数据加密存储和传输"
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 bg-gradient-to-b from-slate-50 to-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-4">
              处理流程
            </h2>
            <p className="text-lg text-slate-600">
              五步完成专业级视频配音
            </p>
          </div>

          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {[
                { step: '1', title: '提取音频', icon: '🎬' },
                { step: '2', title: '语音识别', icon: '🎤' },
                { step: '3', title: '文本翻译', icon: '🌐' },
                { step: '4', title: '语音合成', icon: '🔊' },
                { step: '5', title: '视频合成', icon: '✨' },
              ].map((item, index) => (
                <Card key={index} className="relative">
                  <CardContent className="p-6 text-center">
                    <div className="text-4xl mb-3">{item.icon}</div>
                    <div className="text-sm font-semibold text-blue-600 mb-1">步骤 {item.step}</div>
                    <div className="text-sm font-medium text-slate-900">{item.title}</div>
                  </CardContent>
                  {index < 4 && (
                    <div className="hidden md:block absolute top-1/2 -right-2 w-4 h-0.5 bg-blue-200" />
                  )}
                </Card>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gradient-to-r from-blue-600 to-indigo-600 text-white">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            准备好开始了吗？
          </h2>
          <p className="text-xl mb-8 text-blue-100 max-w-2xl mx-auto">
            立即上传您的第一个视频，体验 AI 配音的强大能力
          </p>
          <Button asChild size="lg" variant="secondary" className="text-lg px-8 py-6 rounded-full">
            <Link href="/tasks/new">
              <Video className="w-5 h-5 mr-2" />
              免费开始
              <ArrowRight className="w-5 h-5 ml-2" />
            </Link>
          </Button>
        </div>
      </section>
    </div>
  );
}

function FeatureCard({
  icon,
  iconColor,
  iconBg,
  title,
  description
}: {
  icon: React.ReactNode;
  iconColor: string;
  iconBg: string;
  title: string;
  description: string;
}) {
  return (
    <Card className="group hover:shadow-lg transition-all duration-300 border-2 hover:border-blue-200">
      <CardContent className="p-6 space-y-4">
        <div className={`${iconBg} ${iconColor} w-14 h-14 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform`}>
          {icon}
        </div>
        <h3 className="text-xl font-bold text-slate-900">{title}</h3>
        <p className="text-slate-600 leading-relaxed">{description}</p>
      </CardContent>
    </Card>
  );
}
