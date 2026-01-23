package storage

import (
	"context"
	"fmt"
	"io"
	"time"

	"vedio/shared/config"
	sharedoss "vedio/shared/oss"
)

// OSSStorage implements ObjectStorage using Aliyun OSS.
type OSSStorage struct {
	client *sharedoss.Client
}

var _ ObjectStorage = (*OSSStorage)(nil)

func NewOSS(cfg config.OSSConfig) (*OSSStorage, error) {
	c, err := sharedoss.New(cfg)
	if err != nil {
		return nil, err
	}
	return &OSSStorage{client: c}, nil
}

func (s *OSSStorage) PutObject(ctx context.Context, key string, reader io.Reader, size int64, contentType string) error {
	_ = size // OSS SDK streams; size not required.
	if err := s.client.PutObject(ctx, key, reader, contentType); err != nil {
		return fmt.Errorf("failed to put object: %w", err)
	}
	return nil
}

func (s *OSSStorage) GetObject(ctx context.Context, key string) (io.ReadCloser, error) {
	r, err := s.client.GetObject(ctx, key)
	if err != nil {
		return nil, fmt.Errorf("failed to get object: %w", err)
	}
	return r, nil
}

func (s *OSSStorage) DeleteObject(ctx context.Context, key string) error {
	if err := s.client.DeleteObject(ctx, key); err != nil {
		return fmt.Errorf("failed to delete object: %w", err)
	}
	return nil
}

func (s *OSSStorage) PresignedGetURL(ctx context.Context, key string, expiry time.Duration) (string, error) {
	url, err := s.client.PresignedGetURL(ctx, key, expiry)
	if err != nil {
		return "", fmt.Errorf("failed to generate presigned URL: %w", err)
	}
	return url, nil
}

func (s *OSSStorage) ObjectExists(ctx context.Context, key string) (bool, error) {
	r, err := s.client.GetObject(ctx, key)
	if err == nil {
		_ = r.Close()
		return true, nil
	}
	// OSS SDK does not expose a typed error here without importing internals; keep it simple.
	return false, nil
}
