package storage

import (
	"context"
	"io"
	"time"
)

// ObjectStorage defines the minimal operations used by API/worker.
type ObjectStorage interface {
	PutObject(ctx context.Context, key string, reader io.Reader, size int64, contentType string) error
	GetObject(ctx context.Context, key string) (io.ReadCloser, error)
	DeleteObject(ctx context.Context, key string) error
	PresignedGetURL(ctx context.Context, key string, expiry time.Duration) (string, error)
	ObjectExists(ctx context.Context, key string) (bool, error)
}
