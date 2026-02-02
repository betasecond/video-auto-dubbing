package tts

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"vedio/shared/config"

	"go.uber.org/zap"
)

// AliyunClient handles TTS API calls to Aliyun DashScope (CosyVoice/Qwen-TTS).
type AliyunClient struct {
	apiKey  string
	baseURL string
	model   string
	client  *http.Client
	logger  *zap.Logger
}

// NewAliyunClient creates a new Aliyun TTS client.
func NewAliyunClient(cfg config.TTSConfig, logger *zap.Logger) *AliyunClient {
	baseURL := cfg.AliyunBaseURL
	if baseURL == "" {
		baseURL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
	}
	// Normalize base URL (remove trailing slash)
	baseURL = strings.TrimRight(baseURL, "/")

	model := cfg.AliyunModel
	if model == "" {
		model = "cosyvoice-v1"
	}

	return &AliyunClient{
		apiKey:  cfg.AliyunAPIKey,
		baseURL: baseURL,
		model:   model,
		client: &http.Client{
			Timeout: 600 * time.Second,
		},
		logger: logger,
	}
}

// OpenAISpeechRequest represents the standard OpenAI TTS request.
type OpenAISpeechRequest struct {
	Model          string  `json:"model"`
	Input          string  `json:"input"`
	Voice          string  `json:"voice"`
	ResponseFormat string  `json:"response_format,omitempty"`
	Speed          float64 `json:"speed,omitempty"`
}

// DashScopeNativeRequest represents the Alibaba native API request.
type DashScopeNativeRequest struct {
	Model      string                 `json:"model"`
	Input      DashScopeInput         `json:"input"`
	Parameters map[string]interface{} `json:"parameters"`
}

type DashScopeInput struct {
	Text string `json:"text"`
}

// Synthesize generates speech using Aliyun API.
func (c *AliyunClient) Synthesize(ctx context.Context, req SynthesisRequest) (io.ReadCloser, error) {
	// If PromptAudioURL is present, we try to use the Native API for voice cloning
	// Note: Direct URL cloning might require specific DashScope capabilities or file upload.
	// For now, we attempt to pass it in parameters, but fallback to standard OpenAI mode if it's empty.
	if req.PromptAudioURL != "" {
		return c.synthesizeNativeWithClone(ctx, req)
	}

	return c.synthesizeOpenAI(ctx, req)
}

func (c *AliyunClient) synthesizeOpenAI(ctx context.Context, req SynthesisRequest) (io.ReadCloser, error) {
	url := fmt.Sprintf("%s/audio/speech", c.baseURL)

	voice := req.SpeakerID
	if voice == "" || voice == "default" {
		voice = "longxiaochun" // Default high-quality voice
	}

	speed := 1.0
	if req.ProsodyControl != nil {
		if s, ok := req.ProsodyControl["speed"].(float64); ok {
			speed = s
		}
	}

	payload := OpenAISpeechRequest{
		Model:          c.model,
		Input:          req.Text,
		Voice:          voice,
		ResponseFormat: "wav",
		Speed:          speed,
	}

	if req.OutputFormat != "" {
		payload.ResponseFormat = req.OutputFormat
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)
	httpReq.Header.Set("Content-Type", "application/json")

	c.logger.Info("Calling Aliyun TTS (OpenAI Compatible)",
		zap.String("url", url),
		zap.String("voice", voice),
		zap.Int("text_len", len(req.Text)))

	resp, err := c.client.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("aliyun request failed: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, fmt.Errorf("aliyun api error (status %d): %s", resp.StatusCode, string(body))
	}

	return resp.Body, nil
}

func (c *AliyunClient) synthesizeNativeWithClone(ctx context.Context, req SynthesisRequest) (io.ReadCloser, error) {
	// Use native endpoint for advanced features like cloning
	url := "https://dashscope.aliyuncs.com/api/v1/services/audio/text-to-speech/generation"

	c.logger.Info("Attempting Aliyun Voice Cloning (Native API)",
		zap.String("prompt_audio", req.PromptAudioURL))

	params := map[string]interface{}{
		"text_type": "Plain",
		"format":    "wav",
	}

	if req.OutputFormat != "" {
		params["format"] = req.OutputFormat
	}

	if req.ProsodyControl != nil {
		if s, ok := req.ProsodyControl["speed"].(float64); ok {
			params["rate"] = s
		}
	}

	// Attempt to use prompt_audio_url for cloning.
	// Note: Actual DashScope API support for direct URL depends on the model version.
	params["prompt_audio_url"] = req.PromptAudioURL

	// Set base voice
	if req.SpeakerID != "" && req.SpeakerID != "default" {
		params["voice"] = req.SpeakerID
	} else {
		params["voice"] = "longxiaochun"
	}

	payload := DashScopeNativeRequest{
		Model: c.model,
		Input: DashScopeInput{
			Text: req.Text,
		},
		Parameters: params,
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal native request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create native request: %w", err)
	}

	httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.client.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("aliyun native request failed: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, fmt.Errorf("aliyun native api error (status %d): %s", resp.StatusCode, string(body))
	}

	// Check for JSON error response even with 200 OK (some APIs do this)
	contentType := resp.Header.Get("Content-Type")
	if strings.Contains(contentType, "application/json") {
		// It might be an error or metadata, but usually successful audio generation returns audio type.
		// However, let's return the body stream anyway, caller will fail to process audio if it's JSON.
		c.logger.Warn("Aliyun native API returned JSON content type, might be an error or metadata",
			zap.String("content_type", contentType))
	}

	return resp.Body, nil
}
