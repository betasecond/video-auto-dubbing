package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/google/uuid"
)

// 简化的测试，直接调用火山引擎 API
func main() {
	fmt.Println("🚀 开始测试火山引擎 ASR 服务...")

	// 凭据信息
	appKey := "6087388513"
	accessKey := "LW8w88nLNJWmmal9CxenBYcON1q6HoGu"
	resourceID := "volc.bigasr.auc"

	// 测试提交任务
	fmt.Println("📤 提交 ASR 任务...")
	taskID, err := submitTask(appKey, accessKey, resourceID)
	if err != nil {
		fmt.Printf("❌ 提交任务失败: %v\n", err)
		return
	}

	fmt.Printf("✅ 任务提交成功，Task ID: %s\n", taskID)

	// 轮询结果
	fmt.Println("⏳ 轮询任务结果...")
	for i := 0; i < 10; i++ { // 最多轮询10次
		time.Sleep(3 * time.Second)

		status, result, err := queryTask(taskID, appKey, accessKey, resourceID)
		if err != nil {
			fmt.Printf("❌ 查询任务失败: %v\n", err)
			return
		}

		fmt.Printf("📊 查询 %d: 状态 %s\n", i+1, status)

		if status == "20000000" {
			fmt.Println("✅ ASR 识别完成!")
			fmt.Printf("🎯 结果: %+v\n", result)
			return
		} else if status != "20000001" && status != "20000002" {
			fmt.Printf("❌ 任务失败，状态: %s\n", status)
			return
		}
	}

	fmt.Println("⏰ 轮询超时")
}

func submitTask(appKey, accessKey, resourceID string) (string, error) {
	requestID := uuid.New().String()

	requestBody := map[string]interface{}{
		"user": map[string]interface{}{
			"uid": "test_user",
		},
		"audio": map[string]interface{}{
			"format": "wav",
			"url":    "https://cdn.pixabay.com/download/audio/2022/05/27/audio_c6f33f4a3a.wav", // 测试音频
		},
		"request": map[string]interface{}{
			"model_name":               "bigmodel",
			"enable_itn":               true,
			"enable_punc":              true,
			"enable_speaker_info":      true,
			"enable_emotion_detection": true,
			"enable_gender_detection":  true,
			"show_utterances":          true,
		},
	}

	jsonData, _ := json.Marshal(requestBody)

	req, err := http.NewRequest("POST", "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit", bytes.NewBuffer(jsonData))
	if err != nil {
		return "", err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Api-App-Key", appKey)
	req.Header.Set("X-Api-Access-Key", accessKey)
	req.Header.Set("X-Api-Resource-Id", resourceID)
	req.Header.Set("X-Api-Request-Id", requestID)
	req.Header.Set("X-Api-Sequence", "-1")

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	statusCode := resp.Header.Get("X-Api-Status-Code")
	message := resp.Header.Get("X-Api-Message")

	if statusCode != "20000000" {
		return "", fmt.Errorf("submit failed: status=%s, message=%s", statusCode, message)
	}

	return requestID, nil
}

func queryTask(taskID, appKey, accessKey, resourceID string) (string, interface{}, error) {
	req, err := http.NewRequest("POST", "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query", bytes.NewBuffer([]byte("{}")))
	if err != nil {
		return "", nil, err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Api-App-Key", appKey)
	req.Header.Set("X-Api-Access-Key", accessKey)
	req.Header.Set("X-Api-Resource-Id", resourceID)
	req.Header.Set("X-Api-Request-Id", taskID)

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", nil, err
	}
	defer resp.Body.Close()

	statusCode := resp.Header.Get("X-Api-Status-Code")
	message := resp.Header.Get("X-Api-Message")

	if statusCode == "20000000" {
		var result map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			return statusCode, nil, err
		}
		return statusCode, result, nil
	}

	return statusCode, message, nil
}