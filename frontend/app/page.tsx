import Link from 'next/link'

export default function Home() {
  return (
    <div className="space-y-8">
      <section className="text-center space-y-4">
        <h2 className="text-4xl font-bold">视频自动配音系统 v2.0</h2>
        <p className="text-xl text-muted-foreground">
          基于阿里百炼平台，一键实现视频跨语言翻译配音
        </p>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
        <FeatureCard
          title="🎤 智能语音识别"
          description="DashScope ASR，支持情感检测和说话人分离"
        />
        <FeatureCard
          title="🌍 多语言翻译"
          description="Qwen3 大模型，精准自然的跨语言翻译"
        />
        <FeatureCard
          title="🔊 语音合成"
          description="Qwen3-TTS，高质量语音合成，支持声音复刻"
        />
      </section>

      <section className="text-center mt-12">
        <Link
          href="/tasks/new"
          className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-11 px-8"
        >
          创建配音任务
        </Link>
      </section>

      <section className="mt-16 p-6 border rounded-lg bg-card">
        <h3 className="text-2xl font-semibold mb-4">快速开始</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>上传需要配音的视频文件</li>
          <li>选择源语言和目标语言</li>
          <li>等待 AI 自动处理（识别 → 翻译 → 合成）</li>
          <li>下载配音完成的视频</li>
        </ol>
      </section>
    </div>
  )
}

function FeatureCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="p-6 border rounded-lg bg-card hover:shadow-lg transition-shadow">
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  )
}
