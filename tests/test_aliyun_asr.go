package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"vedio/worker/internal/asr"

	"go.uber.org/zap"
)

// 测试阿里云 ASR 集成
// 使用方法:
//   export ALIYUN_ASR_API_KEY=sk-xxxxxxxxx
//   export TEST_AUDIO_URL=https://your-audio-url.wav
//   go run tests/test_aliyun_asr.go

func main() {
	// 初始化日志
	logger, err := zap.NewDevelopment()
	if err != nil {
		log.Fatal(err)
	}
	defer logger.Sync()

	// 从环境变量获取配置
	apiKey := os.Getenv("ALIYUN_ASR_API_KEY")
	if apiKey == "" {
		logger.Fatal("ALIYUN_ASR_API_KEY environment variable is required")
	}

	audioURL := os.Getenv("TEST_AUDIO_URL")
	if audioURL == "" {
		logger.Fatal("TEST_AUDIO_URL environment variable is required")
	}

	model := os.Getenv("ALIYUN_ASR_MODEL")
	if model == "" {
		model = "qwen3-asr-flash"
	}

	language := os.Getenv("ALIYUN_ASR_LANGUAGE")

	// 创建客户端配置
	cfg := asr.AliyunASRConfig{
		APIKey:         apiKey,
		Model:          model,
		EnableITN:      true,
		Language:       language,
		RequestTimeout: 60,
	}

	logger.Info("Initializing Aliyun ASR client",
		zap.String("model", cfg.Model),
		zap.String("language", cfg.Language),
		zap.Bool("enable_itn", cfg.EnableITN),
	)

	// 创建客户端
	client := asr.NewAliyunClient(cfg, logger)

	// 执行识别
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	logger.Info("Starting ASR recognition",
		zap.String("audio_url", audioURL),
	)

	startTime := time.Now()
	result, err := client.Recognize(ctx, audioURL, language)
	if err != nil {
		logger.Fatal("ASR recognition failed",
			zap.Error(err),
		)
	}
	duration := time.Since(startTime)

	// 打印结果
	logger.Info("ASR recognition completed",
		zap.Duration("duration", duration),
		zap.String("detected_language", result.Language),
		zap.Int("duration_ms", result.DurationMs),
		zap.Int("segment_count", len(result.Segments)),
	)

	fmt.Println("\n=== ASR 识别结果 ===")
	fmt.Printf("检测语言: %s\n", result.Language)
	fmt.Printf("音频时长: %d ms (%.2f 秒)\n", result.DurationMs, float64(result.DurationMs)/1000.0)
	fmt.Printf("识别耗时: %v\n", duration)
	fmt.Printf("片段数量: %d\n\n", len(result.Segments))

	for i, seg := range result.Segments {
		fmt.Printf("Segment %d:\n", i)
		fmt.Printf("  时间: %d ms - %d ms (%.2f s - %.2f s)\n",
			seg.StartMs, seg.EndMs,
			float64(seg.StartMs)/1000.0, float64(seg.EndMs)/1000.0)
		fmt.Printf("  文本: %s\n", seg.Text)
		fmt.Printf("  说话人: %s\n", seg.SpeakerID)
		if seg.Emotion != "" {
			fmt.Printf("  情绪: %s\n", seg.Emotion)
		}
		if seg.Gender != "" {
			fmt.Printf("  性别: %s\n", seg.Gender)
		}
		fmt.Println()
	}

	fmt.Println("=== 测试完成 ===")
	fmt.Println("\n注意事项:")
	fmt.Println("1. Qwen ASR 同步API不返回时间戳，所有文本被识别为单个segment")
	fmt.Println("2. 如需精确时间戳，请使用异步文件转写API (qwen3-asr-flash-filetrans)")
	fmt.Println("3. 不支持说话人分离，所有segment使用相同说话人ID")
}
