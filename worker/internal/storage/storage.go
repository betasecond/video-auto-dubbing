package storage

import (
	"context"
	"fmt"
	"io"
	"time"

	"vedio/worker/internal/minio"

	miniosdk "github.com/minio/minio-go/v7"
)

// Service handles file storage operations.
type Service struct {
	client *minio.Client
	bucket string
}

// New creates a new storage service.
func New(client *minio.Client, bucket string) *Service {
	return &Service{
		client: client,
		bucket: bucket,
	}
}

// PutObject uploads an object to MinIO.
func (s *Service) PutObject(ctx context.Context, key string, reader io.Reader, size int64, contentType string) error {
	_, err := s.client.PutObject(
		ctx,
		s.bucket,
		key,
		reader,
		size,
		miniosdk.PutObjectOptions{
			ContentType: contentType,
		},
	)
	if err != nil {
		return fmt.Errorf("failed to put object: %w", err)
	}
	return nil
}

// GetObject retrieves an object from MinIO.
func (s *Service) GetObject(ctx context.Context, key string) (io.ReadCloser, error) {
	obj, err := s.client.GetObject(
		ctx,
		s.bucket,
		key,
		miniosdk.GetObjectOptions{},
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get object: %w", err)
	}
	return obj, nil
}

// DeleteObject deletes an object from MinIO.
func (s *Service) DeleteObject(ctx context.Context, key string) error {
	if err := s.client.RemoveObject(
		ctx,
		s.bucket,
		key,
		miniosdk.RemoveObjectOptions{},
	); err != nil {
		return fmt.Errorf("failed to delete object: %w", err)
	}
	return nil
}

