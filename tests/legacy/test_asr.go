package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"vedio/shared/config"
	"vedio/worker/internal/asr"

	"go.uber.org/zap"
)

func main() {
	// 创建简化的 logger
	logger, _ := zap.NewDevelopment()
	defer logger.Sync()

	// 配置火山引擎 ASR
	asrConfig := config.VolcengineASRConfig{
		AppKey:              "6087388513",
		AccessKey:           "LW8w88nLNJWmmal9CxenBYcON1q6HoGu",
		ResourceID:          "volc.bigasr.auc",
		EnableSpeakerInfo:   true,
		EnableEmotionDetect: true,
		EnableGenderDetect:  true,
		EnablePunc:          true,
		EnableITN:           true,
		PollIntervalSeconds: 2,
		PollTimeoutSeconds:  60, // 短一点方便测试
	}

	// 创建 ASR 客户端
	client := asr.NewClient(asrConfig, logger)

	// 测试连接（使用一个无效的音频URL来测试认证）
	fmt.Println("测试火山引擎 ASR 连接...")
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// 直接测试一个简单的识别请求（使用一个公开的测试音频）
	testAudioURL := "https://www.soundjay.com/misc/sounds-765.wav" // 一个测试音频文件
	fmt.Printf("使用测试音频: %s\n", testAudioURL)

	result, err := client.Recognize(ctx, testAudioURL, "zh-CN")
	if err != nil {
		fmt.Printf("❌ ASR 测试失败: %v\n", err)
		return
	}

	fmt.Println("✅ ASR 测试成功!")
	fmt.Printf("识别结果: %+v\n", result)
	fmt.Printf("识别片段数: %d\n", len(result.Segments))

	for i, segment := range result.Segments {
		fmt.Printf("片段 %d: [%dms-%dms] %s (说话人: %s, 情绪: %s, 性别: %s)\n",
			i, segment.StartMs, segment.EndMs, segment.Text,
			segment.SpeakerID, segment.Emotion, segment.Gender)
	}
}