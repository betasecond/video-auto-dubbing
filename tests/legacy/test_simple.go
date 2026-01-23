package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/google/uuid"
)

// 简单测试，使用无效音频URL检查认证
func main() {
	fmt.Println("🚀 测试火山引擎 ASR 认证...")

	// 凭据信息
	appKey := "6087388513"
	accessKey := "LW8w88nLNJWmmal9CxenBYcON1q6HoGu"
	resourceID := "volc.bigasr.auc"

	// 使用无效的音频URL，如果返回音频相关错误说明认证成功
	taskID, err := testAuth(appKey, accessKey, resourceID)
	if err != nil {
		fmt.Printf("认证测试结果: %v\n", err)
		// 检查是否是音频相关的错误（说明认证成功）
		if err.Error() == "submit failed: status=45000001, message=invalid parameter" ||
		   err.Error() == "submit failed: status=45000002, message=empty audio" ||
		   err.Error() == "submit failed: status=45000151, message=invalid audio format" {
			fmt.Println("✅ 认证成功! (音频相关错误属于正常)")
		} else {
			fmt.Println("❌ 认证失败或其他错误")
		}
	} else {
		fmt.Printf("✅ 任务提交成功，TaskID: %s (这表示认证通过)\n", taskID)
	}
}

func testAuth(appKey, accessKey, resourceID string) (string, error) {
	requestID := uuid.New().String()

	requestBody := map[string]interface{}{
		"user": map[string]interface{}{
			"uid": "test_user",
		},
		"audio": map[string]interface{}{
			"format": "wav",
			"url":    "http://invalid-audio-url-for-test.wav", // 故意用无效URL
		},
		"request": map[string]interface{}{
			"model_name":      "bigmodel",
			"enable_itn":      true,
			"show_utterances": true,
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
		return "", fmt.Errorf("网络错误: %v", err)
	}
	defer resp.Body.Close()

	statusCode := resp.Header.Get("X-Api-Status-Code")
	message := resp.Header.Get("X-Api-Message")

	fmt.Printf("状态码: %s, 消息: %s\n", statusCode, message)

	if statusCode != "20000000" {
		return "", fmt.Errorf("submit failed: status=%s, message=%s", statusCode, message)
	}

	return requestID, nil
}