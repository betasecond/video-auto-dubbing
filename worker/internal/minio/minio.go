package minio

import (
	"context"
	"fmt"

	"vedio/worker/internal/config"

	miniosdk "github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

// Client wraps the MinIO client.
type Client struct {
	*miniosdk.Client
	bucket string
}

// New creates a new MinIO client.
func New(cfg config.MinIOConfig) (*Client, error) {
	client, err := miniosdk.New(cfg.Endpoint, &miniosdk.Options{
		Creds:  credentials.NewStaticV4(cfg.AccessKey, cfg.SecretKey, ""),
		Secure: cfg.UseSSL,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create MinIO client: %w", err)
	}

	// Check if bucket exists
	ctx := context.Background()
	exists, err := client.BucketExists(ctx, cfg.Bucket)
	if err != nil {
		return nil, fmt.Errorf("failed to check bucket existence: %w", err)
	}

	if !exists {
		return nil, fmt.Errorf("bucket %s does not exist", cfg.Bucket)
	}

	return &Client{
		Client: client,
		bucket: cfg.Bucket,
	}, nil
}

// Bucket returns the bucket name.
func (c *Client) Bucket() string {
	return c.bucket
}

