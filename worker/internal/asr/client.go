package asr

import (
	"context"
	"fmt"

	"vedio/shared/config"
	"vedio/worker/internal/models"

	"go.uber.org/zap"
)

// Client defines the interface for ASR services.
type Client interface {
	Recognize(ctx context.Context, audioURL string, language string) (*models.ASRResult, error)
}

// ASRBackend represents the ASR service backend.
type ASRBackend string

const (
	BackendVolcengine ASRBackend = "volcengine"
	BackendAliyun     ASRBackend = "aliyun"
)

// NewClient creates the appropriate ASR client based on configuration.
// Deprecated: Use NewClientWithBackend instead.
func NewClient(cfg config.VolcengineASRConfig, logger *zap.Logger) Client {
	return NewVolcengineClient(cfg, logger)
}

// NewClientWithBackend creates an ASR client for the specified backend.
func NewClientWithBackend(backend ASRBackend, baseCfg *config.BaseConfig, logger *zap.Logger) (Client, error) {
	switch backend {
	case BackendVolcengine:
		return NewVolcengineClient(baseCfg.External.VolcengineASR, logger), nil
	case BackendAliyun:
		if baseCfg.External.AliyunASR.APIKey == "" {
			return nil, fmt.Errorf("ALIYUN_ASR_API_KEY is required for aliyun backend")
		}
		aliyunCfg := AliyunASRConfig{
			APIKey:         baseCfg.External.AliyunASR.APIKey,
			Model:          baseCfg.External.AliyunASR.Model,
			EnableITN:      baseCfg.External.AliyunASR.EnableITN,
			Language:       baseCfg.External.AliyunASR.Language,
			RequestTimeout: baseCfg.External.AliyunASR.RequestTimeout,
		}
		return NewAliyunClient(aliyunCfg, logger), nil
	default:
		return nil, fmt.Errorf("unsupported ASR backend: %s", backend)
	}
}
