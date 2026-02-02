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

// AliyunClient handles TTS API calls to Aliyun DashScope (Qwen-TTS).
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
		model = "qwen-tts-flash"
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

// Synthesize generates speech using Aliyun API.
func (c *AliyunClient) Synthesize(ctx context.Context, req SynthesisRequest) (io.ReadCloser, error) {
	// Qwen-TTS (Flash/Turbo) usually does not support zero-shot cloning via prompt audio.
	// If PromptAudioURL is present, we log a warning but proceed with the default/specified voice.
	if req.PromptAudioURL != "" {
		c.logger.Warn("PromptAudioURL provided but voice cloning is not supported by qwen-tts-flash. Using specified voice instead.",
			zap.String("model", c.model),
			zap.String("prompt_url", req.PromptAudioURL))
	}

	return c.synthesizeOpenAI(ctx, req)
}

func (c *AliyunClient) synthesizeOpenAI(ctx context.Context, req SynthesisRequest) (io.ReadCloser, error) {
	url := fmt.Sprintf("%s/audio/speech", c.baseURL)

	voice := c.mapSpeakerToQwenVoice(req.SpeakerID)

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

	c.logger.Info("Calling Aliyun TTS (Qwen-TTS)",
		zap.String("url", url),
		zap.String("model", c.model),
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

// mapSpeakerToQwenVoice maps system speaker IDs to valid Qwen-TTS voice IDs.
// Ref: https://help.aliyun.com/zh/model-studio/developer-reference/text-to-speech-api-details
func (c *AliyunClient) mapSpeakerToQwenVoice(speakerID string) string {
	// Qwen-TTS Voices
	// Longxiaochun is a standard safe default for many Aliyun models.
	// Other options: "Cherry" (Knowlegeable female), "Serena" (Affectionate female), "Ethan" (Warm male)
	defaultVoice := "longxiaochun"

	// If speakerID is empty or default, use defaultVoice
	if speakerID == "" || speakerID == "default" {
		return defaultVoice
	}

	// Known valid Qwen-TTS voices map (simplified list)
	// Users might pass "male_young", "female_young" from our system.
	// We need to map them to nearest Qwen equivalents.
	knownVoices := map[string]string{
		"male_young":    "Alex",   // Or other suitable male voice
		"female_young":  "Cherry", // Or "Nini"
		"male_mature":   "Ethan",
		"female_mature": "Serena",
		"longxiaochun":  "longxiaochun",
		"cherry":        "Cherry",
		"serena":        "Serena",
		"ethan":         "Ethan",
		// Add specific language variants if needed
	}

	if v, exists := knownVoices[strings.ToLower(speakerID)]; exists {
		return v
	}

	// If the user passes a specific ID (like "Nofish") that we don't map explicitly,
	// assume they know what they are doing and pass it through.
	// DashScope API will error if it's invalid, which is acceptable feedback.
	return speakerID
}
