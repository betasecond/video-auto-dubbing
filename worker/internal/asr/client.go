package asr

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"vedio/worker/internal/config"
	"vedio/worker/internal/models"

	"go.uber.org/zap"
)

// Client handles ASR API calls to 豆包语音 (VolcEngine).
type Client struct {
	baseURL string
	client  *http.Client
	logger  *zap.Logger
}

// NewClient creates a new ASR client.
func NewClient(cfg config.VolcEngineASRConfig, logger *zap.Logger) *Client {
	return &Client{
		baseURL: "https://openspeech.bytedance.com",
		client: &http.Client{
			Timeout: 120 * time.Second, // 录音文件识别可能较慢
		},
		logger: logger,
	}
}

// Recognize performs ASR using 豆包语音 录音文件识别标准版.
// audioURL is the presigned MinIO URL accessible by the ASR service.
// apiKey is per-task API key (x-api-key header).
func (c *Client) Recognize(ctx context.Context, audioURL string, language string, apiKey string) (*models.ASRResult, error) {
	if apiKey == "" {
		return nil, fmt.Errorf("asr_api_key is required for 豆包语音 ASR")
	}

	// Step 1: Submit ASR task
	taskID, err := c.submitASRTask(ctx, audioURL, language, apiKey)
	if err != nil {
		return nil, fmt.Errorf("failed to submit ASR task: %w", err)
	}

	c.logger.Info("ASR task submitted", zap.String("task_id", taskID))

	// Step 2: Poll for result
	result, err := c.pollASRResult(ctx, taskID, apiKey)
	if err != nil {
		return nil, fmt.Errorf("failed to get ASR result: %w", err)
	}

	return result, nil
}

// submitASRTask submits audio URL to 豆包语音 and returns task ID.
func (c *Client) submitASRTask(ctx context.Context, audioURL string, language string, apiKey string) (string, error) {
	reqBody := map[string]interface{}{
		"audio": map[string]interface{}{
			"url":    audioURL,
			"format": "wav",
			"rate":   16000,
			"bits":   16,
			"channel": 1,
		},
		"user": map[string]interface{}{
			"uid": "worker",
		},
		"additions": map[string]interface{}{
			"language":  language,
			"use_itn":   "True",
			"use_punc":  "True",
		},
	}

	bodyBytes, err := json.Marshal(reqBody)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %w", err)
	}

	url := fmt.Sprintf("%s/api/v1/auc/submit", c.baseURL)
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(bodyBytes))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("x-api-key", apiKey)

	resp, err := c.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to call submit API: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("submit API returned status %d: %s", resp.StatusCode, string(body))
	}

	var apiResp struct {
		Resp struct {
			Code    int    `json:"code"`
			Message string `json:"message"`
			ID      string `json:"id"`
		} `json:"resp"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&apiResp); err != nil {
		return "", fmt.Errorf("failed to decode response: %w", err)
	}

	if apiResp.Resp.Code != 1000 {
		return "", fmt.Errorf("submit failed: code=%d, message=%s", apiResp.Resp.Code, apiResp.Resp.Message)
	}

	return apiResp.Resp.ID, nil
}

// pollASRResult polls ASR result until done or timeout.
func (c *Client) pollASRResult(ctx context.Context, taskID string, apiKey string) (*models.ASRResult, error) {
	url := fmt.Sprintf("%s/api/v1/auc/query", c.baseURL)
	maxAttempts := 60 // 最多查询 60 次（120 秒）
	pollInterval := 2 * time.Second

	for attempt := 0; attempt < maxAttempts; attempt++ {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		reqBody := map[string]interface{}{
			"id": taskID,
		}

		bodyBytes, err := json.Marshal(reqBody)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal query request: %w", err)
		}

		req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(bodyBytes))
		if err != nil {
			return nil, fmt.Errorf("failed to create query request: %w", err)
		}

		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("x-api-key", apiKey)

		resp, err := c.client.Do(req)
		if err != nil {
			c.logger.Warn("Query request failed, will retry", zap.Error(err))
			time.Sleep(pollInterval)
			continue
		}

		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			c.logger.Warn("Query API returned non-200", zap.Int("status", resp.StatusCode), zap.String("body", string(body)))
			time.Sleep(pollInterval)
			continue
		}

		var apiResp struct {
			Resp struct {
				ID      string `json:"id"`
				Code    int    `json:"code"`
				Message string `json:"message"`
				Text    string `json:"text"`
				Utterances []struct {
					Text      string `json:"text"`
					StartTime int    `json:"start_time"` // milliseconds
					EndTime   int    `json:"end_time"`   // milliseconds
				} `json:"utterances"`
			} `json:"resp"`
		}

		if err := json.NewDecoder(resp.Body).Decode(&apiResp); err != nil {
			resp.Body.Close()
			return nil, fmt.Errorf("failed to decode query response: %w", err)
		}
		resp.Body.Close()

		// Code 1000 = success, 2000 = processing, 2001 = queued
		if apiResp.Resp.Code == 1000 {
			// Success
			result := &models.ASRResult{
				Language:   "", // Will be set by caller
				DurationMs: 0,  // Calculate from last utterance
				Segments:   make([]models.ASRSegment, 0, len(apiResp.Resp.Utterances)),
			}

			for idx, utt := range apiResp.Resp.Utterances {
				result.Segments = append(result.Segments, models.ASRSegment{
					Idx:     idx,
					StartMs: utt.StartTime,
					EndMs:   utt.EndTime,
					Text:    utt.Text,
				})
				if utt.EndTime > result.DurationMs {
					result.DurationMs = utt.EndTime
				}
			}

			c.logger.Info("ASR task completed", zap.String("task_id", taskID), zap.Int("segments", len(result.Segments)))
			return result, nil
		} else if apiResp.Resp.Code == 2000 || apiResp.Resp.Code == 2001 {
			// Processing or queued, continue polling
			c.logger.Debug("ASR task not ready", zap.Int("code", apiResp.Resp.Code), zap.String("message", apiResp.Resp.Message))
			time.Sleep(pollInterval)
			continue
		} else {
			// Error
			return nil, fmt.Errorf("ASR task failed: code=%d, message=%s", apiResp.Resp.Code, apiResp.Resp.Message)
		}
	}

	return nil, fmt.Errorf("ASR polling timeout after %d attempts", maxAttempts)
}

